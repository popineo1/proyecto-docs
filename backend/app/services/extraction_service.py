import re
import io
import os
import pdfplumber
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.job import Job
from app.models.document import Document


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
                    raw_data["supplier"] = "Error: PDF escaneado (requiere OCR)"
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

                    # 3. Proveedor (Primera línea suele ser el emisor)
                    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
                    if lines and raw_data["supplier"] == "Desconocido":
                        raw_data["supplier"] = lines[0][:50] # Cogemos los primeros 50 caracteres

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
                "customer_name": raw_data["supplier"],
                "invoice_number": "S/N",
                "issue_date": raw_data["date"],
                "total_amount": raw_data["total"],
                "tax_amount": raw_data["vat"],
                "tax_base": raw_data["base"],
                "kind": "expense"
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