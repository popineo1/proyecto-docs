export interface DocumentItem {
  id: string;
  tenant_id: string;
  uploaded_by_user_id: string;
  storage_key: string;
  filename_original: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  upload_status: string;
  processing_status: string;
  document_type: string | null;
  confidence_score: number | null;
  error_message: string | null;
  movements_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentItem;
  job: any;
}
