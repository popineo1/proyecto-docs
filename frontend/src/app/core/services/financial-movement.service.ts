import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import {
  FinancialMovement,
  FinancialMovementFilters,
} from '../interfaces/financial-movement.interface';
import { ManualMovementCreateRequest } from '../interfaces/manual-movement.interface';

@Injectable({
  providedIn: 'root',
})
export class FinancialMovementService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  listFinancialMovements(filters: FinancialMovementFilters = {}): Observable<FinancialMovement[]> {
    let params = new HttpParams();

    if (filters.kind) params = params.set('kind', filters.kind);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.source_type) params = params.set('source_type', filters.source_type);
    if (filters.category) params = params.set('category', filters.category);
    if (filters.third_party_name) params = params.set('third_party_name', filters.third_party_name);
    if (filters.business_area) params = params.set('business_area', filters.business_area);
    if (filters.needs_review !== null && filters.needs_review !== undefined) {
      params = params.set('needs_review', String(filters.needs_review));
    }
    if (filters.date_from) params = params.set('date_from', filters.date_from);
    if (filters.date_to) params = params.set('date_to', filters.date_to);
    if (filters.skip !== undefined) params = params.set('skip', String(filters.skip));
    if (filters.limit !== undefined) params = params.set('limit', String(filters.limit));

    return this.http.get<FinancialMovement[]>(`${this.baseUrl}/financial-movements`, { params });
  }

  getFinancialMovementById(id: string): Observable<FinancialMovement> {
    return this.http.get<FinancialMovement>(`${this.baseUrl}/financial-movements/${id}`);
  }

  updateFinancialMovement(id: string, payload: Partial<FinancialMovement>): Observable<FinancialMovement> {
    return this.http.patch<FinancialMovement>(`${this.baseUrl}/financial-movements/${id}`, payload);
  }

  createManualMovement(payload: ManualMovementCreateRequest): Observable<FinancialMovement> {
    return this.http.post<FinancialMovement>(`${this.baseUrl}/manual-movements`, payload);
  }

  listManualMovements(params?: {
    category?: string | null;
    third_party_name?: string | null;
    skip?: number;
    limit?: number;
  }): Observable<FinancialMovement[]> {
    let httpParams = new HttpParams();

    if (params?.category) httpParams = httpParams.set('category', params.category);
    if (params?.third_party_name) httpParams = httpParams.set('third_party_name', params.third_party_name);
    if (params?.skip !== undefined) httpParams = httpParams.set('skip', String(params.skip));
    if (params?.limit !== undefined) httpParams = httpParams.set('limit', String(params.limit));

    return this.http.get<FinancialMovement[]>(`${this.baseUrl}/manual-movements`, {
      params: httpParams,
    });
  }

  exportToExcel(filters: Pick<FinancialMovementFilters, 'kind' | 'date_from' | 'date_to' | 'category'> = {}): Observable<Blob> {
    let params = new HttpParams();
    if (filters.kind) params = params.set('kind', filters.kind);
    if (filters.date_from) params = params.set('date_from', filters.date_from);
    if (filters.date_to) params = params.set('date_to', filters.date_to);
    if (filters.category) params = params.set('category', filters.category);

    return this.http.get(`${this.baseUrl}/financial-movements/export`, {
      params,
      responseType: 'blob',
    });
  }

  getReviewInbox(params?: {
    confidence_level?: 'low' | 'medium' | null;
    skip?: number;
    limit?: number;
  }): Observable<FinancialMovement[]> {
    let httpParams = new HttpParams();

    if (params?.confidence_level) httpParams = httpParams.set('confidence_level', params.confidence_level);
    if (params?.skip !== undefined) httpParams = httpParams.set('skip', String(params.skip));
    if (params?.limit !== undefined) httpParams = httpParams.set('limit', String(params.limit));

    return this.http.get<FinancialMovement[]>(`${this.baseUrl}/financial-movements/review-inbox`, {
      params: httpParams,
    });
  }
}