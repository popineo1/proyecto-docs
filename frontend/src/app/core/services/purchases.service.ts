import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface PurchaseEntry {
  id: string;
  tenant_id: string;
  provider_name: string;
  issue_date: string | null;
  order_date: string | null;
  net_amount: number;
  tax_amount: number;
  total_amount: number;
  currency: string;
  category: string | null;
  subcategory: string | null;
  notes: string | null;
  source_type: string;
  status: string;
  month_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface PurchaseImportResult {
  batch_id: string;
  filename_original: string;
  rows_detected: number;
  rows_imported: number;
  rows_skipped: number;
  status: string;
  error_message: string | null;
}

@Injectable({ providedIn: 'root' })
export class PurchasesService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/purchases`;

  list(skip = 0, limit = 50): Observable<PurchaseEntry[]> {
    const params = new HttpParams()
      .set('skip', skip)
      .set('limit', limit);
    return this.http.get<PurchaseEntry[]>(this.base, { params });
  }

  importExcel(file: File): Observable<PurchaseImportResult> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<PurchaseImportResult>(`${this.base}/import`, form);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }
}
