import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { FinancialEntryItem, FinancialEntryReviewRequest} from '../interfaces/financial-entry.interface';


@Injectable({ providedIn: 'root' })
export class FinancialEntriesService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/financial-entries`;

  list(): Observable<FinancialEntryItem[]> {
    return this.http.get<FinancialEntryItem[]>(this.baseUrl);
  }

  getById(entryId: string): Observable<FinancialEntryItem> {
    return this.http.get<FinancialEntryItem>(`${this.baseUrl}/${entryId}`);
  }

  review(
    entryId: string,
    payload: FinancialEntryReviewRequest,
  ): Observable<FinancialEntryItem> {
    return this.http.patch<FinancialEntryItem>(`${this.baseUrl}/${entryId}/review`, payload);
  }
}
