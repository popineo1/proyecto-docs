import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthStateService } from '../services/auth-state.service';

export const adminGuard = () => {
  const authState = inject(AuthStateService);
  const router = inject(Router);
  const user = authState.user();

  if (user && user.is_superuser) {
    return true;
  }
  
  return router.createUrlTree(['/dashboard']);
};
