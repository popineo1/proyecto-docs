from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class FinancialMovementBase(BaseModel):
    movement_date: date | None = None
    kind: str
    status: str = "proposed"
    source_type: str

    source_document_id: UUID | None = None
    source_financial_entry_id: UUID | None = None
    source_purchase_entry_id: UUID | None = None
    source_reference: str | None = None

    third_party_name: str | None = None
    third_party_tax_id: str | None = None

    concept: str | None = None
    category: str | None = None
    subcategory: str | None = None
    business_area: str | None = None

    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    withholding_amount: Decimal | None = None
    total_amount: Decimal | None = None

    currency: str = "EUR"

    document_type: str | None = None
    needs_review: bool = True
    fingerprint: str | None = None
    source_data: dict | str | None = None

    notes: str | None = None


class FinancialMovementCreate(FinancialMovementBase):
    pass


class FinancialMovementUpdate(BaseModel):
    movement_date: date | None = None
    kind: str | None = None
    status: str | None = None
    source_type: str | None = None

    third_party_name: str | None = None
    third_party_tax_id: str | None = None

    concept: str | None = None
    category: str | None = None
    subcategory: str | None = None
    business_area: str | None = None

    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    withholding_amount: Decimal | None = None
    total_amount: Decimal | None = None

    currency: str | None = None

    document_type: str | None = None
    confidence_score: Decimal | None = None
    needs_review: bool | None = None

    notes: str | None = None


class FinancialMovementResponse(FinancialMovementBase):
    id: UUID
    tenant_id: UUID
    confidence_score: Decimal | None = None
    confidence_level: str | None = None
    confidence_flags: str | None = None
    source_raw_data: str | None = None
    inference_log: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True