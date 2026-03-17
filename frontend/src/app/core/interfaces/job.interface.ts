export interface JobItem {
  id: string;
  tenant_id: string;
  document_id: string;
  job_type: string;
  status: string;
  attempts: number;
  max_attempts: number;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  imported_count: number;
  duplicate_count: number;
  skipped_count: number;
  created_at: string;
  updated_at: string;
}
