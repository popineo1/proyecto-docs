from decimal import Decimal
from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    vat_supported: Decimal  # IVA Soportado (Expenses)
    vat_charged: Decimal    # IVA Repercutido (Income)
    vat_balance: Decimal    # charged - supported
    retention_sales: Decimal # M.111 / Ventas
    retention_rent: Decimal  # M.115 / Alquiler
    average_ticket: Decimal
    documents_processed: int
    pending_reviews: int
    fixed_burn_rate: Decimal
    variable_burn_rate: Decimal
    forecast_vat: Decimal
    forecast_irpf: Decimal


class MonthlyFlowRow(BaseModel):
    month: str
    income: Decimal
    expenses: Decimal
    profit: Decimal


class TopThirdPartyRow(BaseModel):
    name: str
    amount: Decimal


class CategoryMetricRow(BaseModel):
    category_name: str
    total_amount: Decimal


class ProviderMetricRow(BaseModel):
    provider_name: str
    total_amount: Decimal


class TaxMonthlyFlowRow(BaseModel):
    month: str
    vat_charged: Decimal
    vat_supported: Decimal
    vat_balance: Decimal
    retention_sales: Decimal
    retention_rent: Decimal