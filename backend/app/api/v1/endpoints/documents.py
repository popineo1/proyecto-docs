from uuid import UUID
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
from fastapi.responses import FileResponse
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


@router.post("/upload", response_model=list[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    responses = []
    for file in files:
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

            # Trigger background processing
            background_tasks.add_task(JobService.run_processing_job, db, job)

            responses.append(DocumentUploadResponse(
                message=f"Documento '{file.filename}' subido correctamente",
                document=DocumentResponse.model_validate(document),
                job=JobResponse.model_validate(job)
            ))

        except ValueError as e:
            # Optionally collect errors, but for now we skip failed files
            continue
    
    if not responses:
        raise HTTPException(status_code=400, detail="No se pudo subir ningún documento")
        
    return responses


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

@router.get("/{document_id}/file")
def get_document_file(
    document_id: UUID,
    download: bool = False,
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

    file_path = Path(document.storage_key)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el almacenamiento")

    return FileResponse(
        path=file_path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.filename_original,
        content_disposition_type="attachment" if download else "inline"
    )


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


@router.get("/{document_id}/preview")
def preview_document(
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

    return DocumentService.analyze_excel(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
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

    try:
        DocumentService.delete_document(db=db, document=document)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))