from datetime import datetime
import time

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.job import Job
from app.models.tenant import Tenant
from app.services.extraction_service import ExtractionService
from app.services.financial_entry_service import FinancialEntryService


class JobService:
    @staticmethod
    def create_document_processing_job(
        db: Session,
        document: Document,
        current_tenant: Tenant
    ) -> Job:
        job = Job(
            tenant_id=current_tenant.id,
            document_id=document.id,
            job_type="document_processing",
            status="pending",
            attempts=0,
            max_attempts=3,
            scheduled_at=None,
            started_at=None,
            finished_at=None,
            error_message=None
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def list_jobs_by_document(
        db: Session,
        tenant_id: str,
        document_id: str
    ):
        return (
            db.query(Job)
            .filter(
                Job.tenant_id == tenant_id,
                Job.document_id == document_id
            )
            .order_by(Job.created_at.desc())
            .all()
        )

    @staticmethod
    def get_job_by_id(db: Session, tenant_id: str, job_id: str) -> Job | None:
        return (
            db.query(Job)
            .filter(
                Job.id == job_id,
                Job.tenant_id == tenant_id
            )
            .first()
        )

    @staticmethod
    def run_mock_job(db: Session, job: Job) -> Job:

        job.status = "running"
        job.started_at = datetime.utcnow()

        db.commit()
        db.refresh(job)

        time.sleep(1)

        extraction = ExtractionService.create_mock_extraction(db, job)

        FinancialEntryService.create_from_extraction(db, extraction)

        # marcar documento como procesado
        document = db.query(Document).filter(Document.id == job.document_id).first()

        if document:
            document.processing_status = "processed"
            db.commit()

        job.status = "completed"
        job.finished_at = datetime.utcnow()

        db.commit()
        db.refresh(job)

        return job