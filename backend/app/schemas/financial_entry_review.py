from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FinancialEntryReviewRequest(BaseModel):
    status_review: str
    supplier_or_customer: str | None = None
    issue_date: date | None = None
    tax_base: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    category: str | None = None
