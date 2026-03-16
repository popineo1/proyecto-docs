import { CanMatchFn, Router, UrlSegment } from '@angular/router';
import { inject } from '@angular/core';
import { AuthStateService } from '../services/auth-state.service';
import { TenantStateService } from '../services/tenant-state.service';

export const authGuard: CanMatchFn = (_route, segments: UrlSegment[]) => {
  const authState = inject(AuthStateService);
  const tenantState = inject(TenantStateService);
  const router = inject(Router);

  if (!authState.isAuthenticated()) {
    return router.createUrlTree(['/auth/login']);
  }

  const requestedPath = segments.map((segment) => segment.path).join('/');
  const tenantOptionalRoutes = ['select-tenant'];

  if (!tenantState.activeTenantId() && !tenantOptionalRoutes.includes(requestedPath)) {
    return router.createUrlTree(['/select-tenant']);
  }

  return true;
};
