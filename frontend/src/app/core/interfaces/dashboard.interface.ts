export interface DashboardSummary {
  total_income: string;
  total_expenses: string;
  net_profit: string;
  vat_supported: string;
  vat_charged: string;
  vat_balance: string;
  retention_sales: string;
  retention_rent: string;
  average_ticket: string;
  documents_processed: number;
  pending_reviews: number;
  fixed_burn_rate: string;
  variable_burn_rate: string;
  forecast_vat: string;
  forecast_irpf: string;
}

export interface MonthlyFlowRow {
  month: string;
  income: string;
  expenses: string;
  profit: string;
}

export interface ThirdPartyMetric {
  name: string;
  amount: string;
}

export interface CategoryMetric {
  category_name: string;
  total_amount: string;
}

export interface TaxMonthlyFlowRow {
  month: string;
  vat_charged: string;
  vat_supported: string;
  vat_balance: string;
  retention_sales: string;
  retention_rent: string;
}