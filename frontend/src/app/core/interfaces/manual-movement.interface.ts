export interface ManualMovementCreateRequest {
  movement_date: string;
  movement_type: string;

  third_party_name: string;
  third_party_tax_id?: string | null;
  concept: string;

  category?: string | null;
  subcategory?: string | null;
  business_area?: string | null;

  net_amount?: number | null;
  tax_amount?: number | null;
  withholding_amount?: number | null;
  total_amount: number;

  currency?: string;
  notes?: string | null;
  needs_review?: boolean;
}