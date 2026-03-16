import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { TenantStateService } from '../services/tenant-state.service';

const EXCLUDED_PATHS = ['/auth/login', '/auth/register', '/auth/me', '/auth/me/tenants'];

export const tenantInterceptor: HttpInterceptorFn = (req, next) => {
  const tenantState = inject(TenantStateService);
  const tenantId = tenantState.activeTenantId();

  const isExcluded = EXCLUDED_PATHS.some((path) => req.url.includes(path));

  if (!tenantId || isExcluded) {
    return next(req);
  }

  const cloned = req.clone({
    setHeaders: {
      'X-Tenant-Id': tenantId,
    },
  });

  return next(cloned);
};
