from uuid import UUID
from pydantic import BaseModel


class TenantBase(BaseModel):
    name: str
    slug: str
    vertical: str | None = None


class TenantCreate(TenantBase):
    pass


class TenantResponse(TenantBase):
    id: UUID
    status: str

    class Config:
        from_attributes = True