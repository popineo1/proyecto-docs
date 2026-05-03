import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: string;
  token: string;
  expires_at: string;
  created_at: string;
  invited_by_name: string | null;
}

export interface InvitationInfo {
  email: string;
  role: string;
  tenant_name: string;
  expires_at: string;
}

@Injectable({ providedIn: 'root' })
export class InvitationsService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/invitations`;

  list(): Observable<Invitation[]> {
    return this.http.get<Invitation[]>(this.base);
  }

  create(email: string, role: string): Observable<Invitation> {
    return this.http.post<Invitation>(this.base, { email, role });
  }

  cancel(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  getInfo(token: string): Observable<InvitationInfo> {
    return this.http.get<InvitationInfo>(`${this.base}/${token}/info`);
  }

  accept(token: string, full_name: string, password: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.base}/${token}/accept`, { full_name, password });
  }
}
