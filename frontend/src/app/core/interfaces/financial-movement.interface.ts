export interface FinancialMovement {
  id: string;
  tenant_id: string;

  movement_date: string | null;
  kind: string;
  status: string;
  source_type: string;

  source_document_id: string | null;
  source_financial_entry_id: string | null;
  source_purchase_entry_id: string | null;
  source_reference: string | null;

  third_party_name: string | null;
  third_party_tax_id: string | null;

  concept: string | null;
  category: string | null;
  subcategory: string | null;
  business_area: string | null;

  net_amount: string | null;
  tax_amount: string | null;
  withholding_amount: string | null;
  total_amount: string | null;

  currency: string;
  document_type: string | null;
  confidence_score: string | null;
  confidence_level: 'high' | 'medium' | 'low' | null;
  confidence_flags: string | null;
  source_raw_data: string | null;
  inference_log: string | null;
  needs_review: boolean;
  notes: string | null;

  fingerprint: string | null;
  source_data: string | null;

  created_at: string;
  updated_at: string;
}

export interface FinancialMovementFilters {
  kind?: string | null;
  status?: string | null;
  source_type?: string | null;
  category?: string | null;
  third_party_name?: string | null;
  business_area?: string | null;
  needs_review?: boolean | null;
  date_from?: string | null;
  date_to?: string | null;
  skip?: number;
  limit?: number;
}