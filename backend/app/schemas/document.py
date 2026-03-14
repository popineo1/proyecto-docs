from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.job import JobResponse


class DocumentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    uploaded_by_user_id: UUID | None
    storage_key: str
    filename_original: str
    mime_type: str
    file_size: int
    checksum: str | None
    upload_status: str
    processing_status: str
    document_type: str | None
    confidence_score: float | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    message: str
    document: DocumentResponse
    job: JobResponse