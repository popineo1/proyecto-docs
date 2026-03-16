export interface FinancialEntryItem {
  id: string;
  tenant_id: string;
  document_id: string;
  extraction_run_id: string | null;
  kind: string;
  issue_date: string | null;
  supplier_or_customer: string | null;
  tax_base: number | null;
  tax_amount: number | null;
  total_amount: number | null;
  currency: string;
  category: string | null;
  status_review: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialEntryReviewRequest {
  status_review: string;
  supplier_or_customer?: string | null;
  issue_date?: string | null;
  tax_base?: number | null;
  tax_amount?: number | null;
  total_amount?: number | null;
  category?: string | null;
}
