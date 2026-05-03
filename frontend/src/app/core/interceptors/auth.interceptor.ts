import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthStateService } from '../services/auth-state.service';
import { AuthService } from '../services/auth.service';

const addBearer = (req: HttpRequest<unknown>, token: string) =>
  req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authState = inject(AuthStateService);
  const authService = inject(AuthService);
  const router = inject(Router);

  const token = authState.token();
  const outgoing = token ? addBearer(req, token) : req;

  return next(outgoing).pipe(
    catchError((err: HttpErrorResponse) => {
      // Solo intentar refresh en 401, y no para las rutas de auth en sí
      if (err.status !== 401 || req.url.includes('/auth/')) {
        return throwError(() => err);
      }

      const refreshToken = authState.getRefreshToken();
      if (!refreshToken) {
        authState.logout();
        router.navigate(['/auth/login']);
        return throwError(() => err);
      }

      return authService.refresh(refreshToken).pipe(
        switchMap((tokens) => {
          authState.setToken(tokens.access_token);
          authState.setRefreshToken(tokens.refresh_token);
          return next(addBearer(req, tokens.access_token));
        }),
        catchError((refreshErr) => {
          authState.logout();
          router.navigate(['/auth/login']);
          return throwError(() => refreshErr);
        })
      );
    })
  );
};
