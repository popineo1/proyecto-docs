from datetime import datetime
from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.job import Job


class ExtractionService:

    @staticmethod
    def create_mock_extraction(db: Session, job: Job):

        extraction = ExtractionRun(
            tenant_id=job.tenant_id,
            document_id=job.document_id,
            job_id=job.id,
            engine_name="mock-engine",
            engine_version="1.0",
            started_at=datetime.utcnow(),
            status="running"
        )

        db.add(extraction)
        db.commit()
        db.refresh(extraction)

        # Resultado simulado de IA
        extraction.raw_output_json = {
            "supplier": "ACME SL",
            "invoice_number": "FAC-2026-001",
            "date": "2026-03-14",
            "total": 159.95,
            "vat": 21
        }

        extraction.normalized_output_json = {
            "document_type": "invoice",
            "supplier_name": "ACME SL",
            "invoice_number": "FAC-2026-001",
            "issue_date": "2026-03-14",
            "total_amount": 159.95,
            "vat_rate": 21
        }

        extraction.confidence_score = 0.92
        extraction.status = "completed"
        extraction.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(extraction)

        return extraction