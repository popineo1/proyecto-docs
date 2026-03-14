from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class FinancialEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    document_id: UUID
    extraction_run_id: UUID | None
    kind: str
    issue_date: date | None
    supplier_or_customer: str | None
    tax_base: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    currency: str
    category: str | None
    status_review: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
