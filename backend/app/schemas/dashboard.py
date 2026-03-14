from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_expenses: float
    total_income: float
    total_vat: float
    documents_processed: int
    pending_reviews: int
