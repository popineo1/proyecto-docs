export interface DashboardSummary {
  total_income: string;
  total_expenses: string;
  total_purchases: string;
  gross_margin: string;
  gross_margin_pct: string;
  average_ticket: string;
  documents_processed: number;
  pending_reviews: number;
}

export interface MonthlyProfitabilityRow {
  month: string;
  sales_net: string;
  sales_gross: string;
  purchases_net: string;
  purchases_gross: string;
  gross_margin_amount: string;
  gross_margin_pct: string;
  purchase_to_sales_ratio_pct: string;
}

export interface SupplierMetric {
  provider_name: string;
  total_amount: string;
}

export interface CategoryMetric {
  category_name: string;
  total_amount: string;
}