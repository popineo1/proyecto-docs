import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import {
  CategoryMetric,
  DashboardSummary,
  MonthlyProfitabilityRow,
  SupplierMetric,
} from '../interfaces/dashboard.interface';

@Injectable({
  providedIn: 'root',
})
export class DashboardService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = 'http://127.0.0.1:8000/api/v1';

  getOverview(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>(`${this.baseUrl}/analytics/overview`);
  }

  getMonthlyProfitability(): Observable<MonthlyProfitabilityRow[]> {
    return this.http.get<MonthlyProfitabilityRow[]>(`${this.baseUrl}/analytics/monthly-profitability`);
  }

  getTopSuppliers(limit = 5): Observable<SupplierMetric[]> {
    return this.http.get<SupplierMetric[]>(`${this.baseUrl}/analytics/top-suppliers?limit=${limit}`);
  }

  getExpensesByCategory(limit = 6): Observable<CategoryMetric[]> {
    return this.http.get<CategoryMetric[]>(`${this.baseUrl}/analytics/expenses-by-category?limit=${limit}`);
  }
}