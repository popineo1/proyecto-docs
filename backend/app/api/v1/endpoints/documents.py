from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentUploadResponse
from app.schemas.job import JobResponse
from app.services.document_service import DocumentService
from app.services.job_service import JobService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    try:
        document = await DocumentService.save_uploaded_document(
            db=db,
            file=file,
            current_user=current_user,
            current_tenant=current_tenant
        )

        job = JobService.create_document_processing_job(
            db=db,
            document=document,
            current_tenant=current_tenant
        )

        return DocumentUploadResponse(
            message="Documento subido correctamente",
            document=DocumentResponse.model_validate(document),
            job=JobResponse.model_validate(job)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    return DocumentService.list_documents_by_tenant(db, str(current_tenant.id))


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    document = DocumentService.get_document_by_id(
        db=db,
        tenant_id=str(current_tenant.id),
        document_id=str(document_id)
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    return document


@router.get("/{document_id}/jobs", response_model=list[JobResponse])
def get_document_jobs(
    document_id: UUID,
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    document = DocumentService.get_document_by_id(
        db=db,
        tenant_id=str(current_tenant.id),
        document_id=str(document_id)
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    jobs = JobService.list_jobs_by_document(
        db=db,
        tenant_id=str(current_tenant.id),
        document_id=str(document_id)
    )

    return jobs