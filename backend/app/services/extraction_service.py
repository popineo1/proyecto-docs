import re
import io
import os
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

            # 5. Normalizar resultado
            extraction.raw_output_json = raw_data
            extraction.normalized_output_json = {
                "document_type": "invoice" if any(x in full_text.upper() for x in ["FACTURA", "INVOICE"]) else "ticket",
                "supplier_name": raw_data.get("issuer"),
                "receiver_name": raw_data.get("receiver"),
                "customer_name": raw_data.get("receiver") or raw_data["supplier"],
                "invoice_number": "S/N",
                "issue_date": raw_data["date"],
                "total_amount": raw_data["total"],
                "tax_amount": raw_data["vat"],
                "tax_base": raw_data["base"],
            }

            # Intento de número de factura
            num_match = re.search(r"(?:Factura|Nº|Num|Número).*?([A-Z0-9\-/]{3,})", full_text, re.IGNORECASE)
            if num_match:
                extraction.normalized_output_json["invoice_number"] = num_match.group(1)

            extraction.confidence_score = 0.85
            extraction.status = "completed"
            extraction.finished_at = datetime.utcnow()

        except Exception as e:
            extraction.status = "failed"
            extraction.error_message = str(e)
            extraction.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(extraction)

        return extraction