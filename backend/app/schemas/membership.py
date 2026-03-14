from uuid import UUID
from pydantic import BaseModel


class UserTenantResponse(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    role: str
    status: str