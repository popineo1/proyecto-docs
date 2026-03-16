import { CanMatchFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthStateService } from '../services/auth-state.service';
import { TenantStateService } from '../services/tenant-state.service';

export const guestGuard: CanMatchFn = () => {
  const authState = inject(AuthStateService);
  const tenantState = inject(TenantStateService);
  const router = inject(Router);

  if (!authState.isAuthenticated()) return true;

  if (tenantState.activeTenantId()) {
    return router.createUrlTree(['/dashboard']);
  }

  return router.createUrlTree(['/select-tenant']);
};
