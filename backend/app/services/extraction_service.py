import re
import io
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
                    
                # Búsqueda de fecha
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})", full_text)
                if date_match:
                    raw_data["date"] = date_match.group(1)

                # Búsqueda de Importes (Simpificado para la migración inicial)
                # Buscamos patrones como "Total: 123,45 €" o similares
                total_match = re.search(r"(?:Total|TOTAL|Importe Total).*?(\d+[,.]\d{2})", full_text)
                if total_match:
                    raw_data["total"] = float(total_match.group(1).replace(",", "."))

                # Intentamos extraer tablas para el desglose de IVA si existe
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            row_str = " ".join([str(cell) for cell in row if cell])
                            if "IVA" in row_str or "I.V.A." in row_str:
                                iva_match = re.search(r"(\d+[,.]\d{2})", row_str)
                                if iva_match:
                                    raw_data["vat"] = float(iva_match.group(1).replace(",", "."))

            raw_data["base"] = raw_data["total"] - raw_data["vat"]

            # 5. Normalizar resultado
            extraction.raw_output_json = raw_data
            extraction.normalized_output_json = {
                "document_type": "invoice" if "Factura" in full_text else "ticket",
                "customer_name": raw_data["supplier"], # En nuestro caso 'supplier' es quien emite
                "invoice_number": re.search(r"(?:Factura|Nº|Num).*?([A-Z0-9\-/]+)", full_text).group(1) if re.search(r"(?:Factura|Nº|Num).*?([A-Z0-9\-/]+)", full_text) else "S/N",
                "issue_date": raw_data["date"],
                "total_amount": raw_data["total"],
                "tax_amount": raw_data["vat"],
                "tax_base": raw_data["base"],
                "kind": "expense" # Por defecto asumimos gasto si es un ticket subido, o detectamos
            }

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