import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface SubscriptionStatus {
  subscription_status: string | null;
  subscription_plan: string | null;
  subscription_period_end: string | null;
  is_active: boolean;
  stripe_customer_id: string | null;
}

@Injectable({ providedIn: 'root' })
export class BillingService {
  private readonly http = inject(HttpClient);
  private readonly api = `${environment.apiUrl}/billing`;

  getStatus(): Observable<SubscriptionStatus> {
    return this.http.get<SubscriptionStatus>(`${this.api}/status`);
  }

  startCheckout(): Observable<{ checkout_url: string }> {
    const base = window.location.origin;
    return this.http.post<{ checkout_url: string }>(`${this.api}/checkout`, {
      success_url: `${base}/billing?success=1`,
      cancel_url: `${base}/billing?canceled=1`,
    });
  }

  openPortal(): Observable<{ portal_url: string }> {
    return this.http.post<{ portal_url: string }>(`${this.api}/portal`, {
      return_url: `${window.location.origin}/billing`,
    });
  }
}
