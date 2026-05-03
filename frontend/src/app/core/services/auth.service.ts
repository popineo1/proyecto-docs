import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { LoginRequest, MeResponse, RegisterRequest,  TokenResponse,} from '../interfaces/auth.interface';
import { UserTenant } from '../interfaces/tenant.interface';



@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/auth`;

  login(payload: LoginRequest): Observable<TokenResponse> {
    const body = new URLSearchParams();
    body.set('username', payload.email);
    body.set('password', payload.password);

    return this.http.post<TokenResponse>(
      `${this.baseUrl}/login`,
      body.toString(),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      },
    );
  }

  register(payload: RegisterRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/register`, payload);
  }

  refresh(refreshToken: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/refresh`, { refresh_token: refreshToken });
  }

  me(): Observable<MeResponse> {
    return this.http.get<MeResponse>(`${this.baseUrl}/me`);
  }

  getMyTenants(): Observable<UserTenant[]> {
    return this.http.get<UserTenant[]>(`${this.baseUrl}/me/tenants`);
  }
}
