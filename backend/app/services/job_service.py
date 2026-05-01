from datetime import datetime
import time

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.job import Job
from app.models.tenant import Tenant
from app.services.excel_processing_service import ExcelProcessingService
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
    def run_processing_job(db: Session, job: Job) -> Job:
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        try:
            document = db.query(Document).filter(Document.id == job.document_id).first()
            if not document:
                raise ValueError("Documento no encontrado")

            document.processing_status = "processing"
            document.error_message = None
            db.commit()

            # Routing based on MIME type
            if document.mime_type in [
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel"
            ]:
                # 1. Real Excel Processing
                metrics = ExcelProcessingService.process_document(
                    db, 
                    job.tenant_id, 
                    document.id, 
                    document.storage_key
                )
                
                # Store metrics in job record
                job.imported_count = metrics.get("imported", 0)
                job.duplicate_count = metrics.get("duplicates", 0)
                job.skipped_count = metrics.get("skipped", 0)
            else:
                # 2. Use Intelligent Extraction for PDFs/Images
                extraction = ExtractionService.run_intelligent_extraction(db, job)
                FinancialEntryService.create_from_extraction(db, extraction)

            document.processing_status = "processed"
            job.status = "completed"
            job.finished_at = datetime.utcnow()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            if document:
                document.processing_status = "failed"
                document.error_message = str(e)
        
        db.commit()
        db.refresh(job)
        return job