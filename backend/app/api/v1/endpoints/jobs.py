from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.models.job import Job
from app.models.tenant import Tenant
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/{job_id}/run-mock")
def run_job_mock(
    job_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    job = JobService.get_job_by_id(
        db=db,
        tenant_id=str(current_tenant.id),
        job_id=str(job_id),
    )

    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")

    job = JobService.run_mock_job(db, job)

    return {
        "message": "Job ejecutado correctamente",
        "job_id": str(job.id),
        "status": job.status,
    }