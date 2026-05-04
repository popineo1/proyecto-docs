import re
import io
import os
import base64
import logging
import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.job import Job
from app.models.document import Document


logger = logging.getLogger(__name__)


class ExtractionService:

    @staticmethod
    def run_intelligent_extraction(db: Session, job: Job):
        # 1. Obtener el documento asociado
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if not document:
            raise ValueError("Documento no encontrado para el Job")

        # 2. Iniciar la ejecución de extracción
        extraction = ExtractionRun(
            tenant_id=job.tenant_id,
            document_id=job.document_id,
            job_id=job.id,
            engine_name="antigravity-intel-v1",
            engine_version="1.0",
            started_at=datetime.utcnow(),
            status="running"
        )

        db.add(extraction)
        db.commit()
        db.refresh(extraction)

        try:
            # 3. Obtener el archivo (Local o Supabase)
            from app.core.supabase import get_supabase
            supabase = get_supabase()
            
            file_content = None
            if supabase and "/" in document.storage_key and not os.path.isabs(document.storage_key) and not document.storage_key.startswith("storage/"):
                # Probablemente en Supabase (tenant_id/uuid.ext)
                try:
                    response = supabase.storage.from_("documents").download(document.storage_key)
                    file_content = io.BytesIO(response)
                except Exception as e:
                    raise FileNotFoundError(f"No se pudo descargar de Supabase: {str(e)}")
            else:
                # Local
                file_path = Path(document.storage_key)
                if not file_path.exists():
                    raise FileNotFoundError(f"Archivo no encontrado en {file_path}")
                with open(file_path, "rb") as f:
                    file_content = io.BytesIO(f.read())

            # 4. Procesar con pdfplumber
            raw_data = {
                "supplier": "Desconocido",
                "date": None,
                "total": 0.0,
                "vat": 0.0,
                "base": 0.0,
                "items": []
            }

            with pdfplumber.open(file_content) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() or ""
                
                # Check for empty text (scanned image)
                if not full_text.strip():
                    logger.info("PDF appears to be scanned. Attempting OCR...")
                    try:
                        # Convert PDF pages to images
                        images = convert_from_bytes(file_content.getvalue(), poppler_path=None)
                        for i, image in enumerate(images):
                            logger.info(f"Processing OCR for page {i+1}...")
                            full_text += pytesseract.image_to_string(image, lang='spa') + "\n"
                    except Exception as e:
                        logger.error(f"OCR failed: {str(e)}")
                        raw_data["supplier"] = f"Error OCR: {str(e)}"

                if not full_text.strip():
                    raw_data["supplier"] = "Error: PDF vacío o no legible"
                else:
                    # 1. Búsqueda de FECHA (dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy)
                    date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", full_text)
                    if date_match:
                        raw_data["date"] = date_match.group(1).replace("-", "/").replace(".", "/")

                    # 2. Búsqueda de TOTAL (Importe, A pagar, Total)
                    # Soportamos coma y punto como decimales
                    total_match = re.search(r"(?:Total|TOTAL|Importe Total|A pagar|Importe líquido).*?(\d+[.,]\d{2})", full_text, re.IGNORECASE)
                    if total_match:
                        val = total_match.group(1).replace(",", ".")
                        raw_data["total"] = float(val)

                    # 3. Emisor y receptor
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    if lines and raw_data["supplier"] == "Desconocido":
                        raw_data["supplier"] = lines[0][:100]

                    # Emisor: primeras líneas antes de encontrar datos de cliente
                    raw_data["issuer"] = lines[0][:100] if lines else None

                    # Receptor: buscar patrones habituales de "datos del cliente"
                    receiver_match = re.search(
                        r"(?:Nombre[/]Raz[oó]n\s+Social[:\s]+"
                        r"|DATOS\s+(?:DEL\s+)?CLIENTE[:\s]*[\n\r]+Nombre[/]Raz[oó]n\s+Social[:\s]+"
                        r"|Cliente[:\s]+"
                        r"|DATOS\s+(?:DEL\s+)?CLIENTE[\s]*[\n\r]+"
                        r"|Destinatario[:\s]+"
                        r"|Facturar\s+a[:\s]+"
                        r"|Atenci[oó]n[:\s]+)"
                        r"([A-ZÁÉÍÓÚÑ\w][^\n\r]{2,80})",
                        full_text,
                        re.IGNORECASE
                    )
                    raw_data["receiver"] = receiver_match.group(1).strip()[:100] if receiver_match else None

                    # Fallback receptor: nombre propio (2-3 palabras) en la línea anterior a "NIF"
                    # Usa findall para obtener todos los matches y descartar el emisor conocido
                    if not raw_data["receiver"]:
                        before_nif_matches = re.findall(
                            r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+"
                            r"(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)[^\n\r]*[\n\r]+NIF",
                            full_text
                        )
                        issuer_norm = (raw_data.get("issuer") or "").lower()
                        for match in before_nif_matches:
                            candidate = match.strip()[:100]
                            if candidate.lower() != issuer_norm and issuer_norm not in candidate.lower():
                                raw_data["receiver"] = candidate
                                break

                    # Señal de factura emitida propia: pie con "ELABORADO POR"
                    raw_data["has_elaborado_por"] = bool(re.search(r"ELABORADO\s+POR", full_text, re.IGNORECASE))


                    # 4. Desglose de IVA (Tablas)
                    for page in pdf.pages:
                        tables = page.extract_tables()
                        for table in tables:
                            if not table: continue
                            for row in table:
                                row_str = " ".join([str(cell) for cell in row if cell]).upper()
                                if "IVA" in row_str or "I.V.A." in row_str:
                                    iva_match = re.search(r"(\d+[.,]\d{2})", row_str)
                                    if iva_match:
                                        raw_data["vat"] = float(iva_match.group(1).replace(",", "."))

            # Ajuste de base imponible
            raw_data["base"] = raw_data["total"] - raw_data["vat"]

            # 5. Normalizar resultado base (regex)
            extraction.raw_output_json = raw_data

            num_match = re.search(r"(?:Factura|Nº|Num|Número).*?([A-Z0-9\-/]{3,})", full_text, re.IGNORECASE)
            invoice_number_regex = num_match.group(1) if num_match else "S/N"

            regex_normalized = {
                "document_type": "invoice" if any(x in full_text.upper() for x in ["FACTURA", "INVOICE"]) else "ticket",
                "supplier_name": raw_data.get("issuer"),
                "receiver_name": raw_data.get("receiver"),
                "customer_name": raw_data.get("receiver") or raw_data["supplier"],
                "invoice_number": invoice_number_regex,
                "issue_date": raw_data["date"],
                "total_amount": raw_data["total"],
                "tax_amount": raw_data["vat"],
                "tax_base": raw_data["base"],
            }

            # 6. Intentar extracción IA (con fallback a regex)
            tenant_name_for_ai = None
            tenant_aliases_for_ai: list[str] = []
            try:
                from app.models.tenant import Tenant as TenantModel
                tenant_obj = db.query(TenantModel).filter(TenantModel.id == document.tenant_id).first()
                if tenant_obj:
                    tenant_name_for_ai = tenant_obj.name
                    # slug como alias adicional (ej. "tuadministrativo")
                    if tenant_obj.slug and tenant_obj.slug != tenant_obj.name:
                        tenant_aliases_for_ai.append(tenant_obj.slug)
                    # fiscal_name y tax_id si el modelo los tuviera en el futuro
                    fiscal_name = getattr(tenant_obj, "fiscal_name", None)
                    if fiscal_name:
                        tenant_aliases_for_ai.append(fiscal_name)
                    tax_id = getattr(tenant_obj, "tax_id", None)
                    if tax_id:
                        tenant_aliases_for_ai.append(tax_id)
            except Exception:
                pass

            from app.services.ai_extraction_service import AIExtractionService
            from app.core.config import settings

            ai_result = None

            # 6a. Path multimodal Gemini: enviar primera página como imagen
            # Mucho mejor que OCR+texto para PDFs escaneados o visualmente complejos
            if settings.GOOGLE_AI_KEY:
                try:
                    image_b64: str | None = None
                    mime = (document.mime_type or "").lower()

                    if "pdf" in mime:
                        file_content.seek(0)
                        pages = convert_from_bytes(file_content.read(), dpi=200, first_page=1, last_page=1)
                        if pages:
                            buf = io.BytesIO()
                            pages[0].save(buf, format="PNG")
                            image_b64 = base64.b64encode(buf.getvalue()).decode()
                            file_content.seek(0)
                    elif mime.startswith("image/"):
                        file_content.seek(0)
                        image_b64 = base64.b64encode(file_content.read()).decode()
                        file_content.seek(0)

                    if image_b64:
                        logger.info("Usando extracción multimodal Gemini para %s", document.filename_original)
                        ai_result = AIExtractionService.extract_multimodal(
                            image_b64,
                            tenant_name=tenant_name_for_ai,
                            tenant_aliases=tenant_aliases_for_ai,
                        )
                except Exception as e:
                    logger.warning("Path multimodal falló, intentando texto: %s", e)

            # 6b. Fallback: texto extraído por pdfplumber/OCR → Gemini o OpenAI
            if ai_result is None and full_text.strip():
                logger.info("Usando extracción por texto para %s", document.filename_original)
                ai_result = AIExtractionService.extract(
                    full_text,
                    tenant_name=tenant_name_for_ai,
                    tenant_aliases=tenant_aliases_for_ai,
                )

            if ai_result:
                logger.warning("[NORMALIZED] motor=ai | doc_type=%s | kind=%s | third_party=%s | total=%s | needs_review=%s",
                    ai_result.document_type, ai_result.operation_kind, ai_result.third_party_name,
                    ai_result.total_amount if ai_result.total_amount is not None else raw_data["total"],
                    ai_result.needs_review,
                )
                extraction.normalized_output_json = {
                    "document_type": ai_result.document_type,
                    "operation_kind": ai_result.operation_kind,
                    "supplier_name": ai_result.issuer_name,
                    "receiver_name": ai_result.receiver_name,
                    "customer_name": ai_result.receiver_name or ai_result.third_party_name,
                    "third_party_name": ai_result.third_party_name,
                    "issuer_tax_id": ai_result.issuer_tax_id,
                    "receiver_tax_id": ai_result.receiver_tax_id,
                    "invoice_number": ai_result.invoice_number or invoice_number_regex,
                    "issue_date": ai_result.issue_date or raw_data["date"],
                    "due_date": ai_result.due_date,
                    "total_amount": ai_result.total_amount if ai_result.total_amount is not None else raw_data["total"],
                    "tax_amount": ai_result.vat_amount if ai_result.vat_amount is not None else raw_data["vat"],
                    "tax_base": ai_result.tax_base if ai_result.tax_base is not None else raw_data["base"],
                    "vat_pct": ai_result.vat_pct,
                    "irpf_amount": ai_result.irpf_amount,
                    "irpf_pct": ai_result.irpf_pct,
                    "currency": ai_result.currency,
                    # campos fiscales enriquecidos (factura-reader)
                    "trimestre": ai_result.trimestre,
                    "es_rectificativa": ai_result.es_rectificativa,
                    "rectifica_a": ai_result.rectifica_a,
                    "inversion_sujeto_pasivo": ai_result.inversion_sujeto_pasivo,
                    "category": ai_result.category,
                    "needs_review": ai_result.needs_review,
                    "review_reason": ai_result.review_reason,
                    # señales para classifier
                    "has_elaborado_por": raw_data.get("has_elaborado_por", False),
                }
                extraction.confidence_score = ai_result.confidence_score
            else:
                logger.warning("[NORMALIZED] motor=regex_fallback | doc_type=%s | kind=(pendiente clasificador) | total=%s",
                    regex_normalized.get("document_type"), regex_normalized.get("total_amount"),
                )
                extraction.normalized_output_json = regex_normalized
                extraction.confidence_score = 0.75

            extraction.status = "completed"
            extraction.finished_at = datetime.utcnow()

        except Exception as e:
            extraction.status = "failed"
            extraction.error_message = str(e)
            extraction.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(extraction)

        return extraction