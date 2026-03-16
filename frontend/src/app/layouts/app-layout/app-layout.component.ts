import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthStateService } from '../../core/services/auth-state.service';
import { TenantStateService } from '../../core/services/tenant-state.service';

@Component({
  selector: 'app-app-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app-layout.component.html',
})
export class AppLayoutComponent {
  private readonly authState = inject(AuthStateService);
  private readonly tenantState = inject(TenantStateService);
  private readonly router = inject(Router);

  readonly user = this.authState.user;
  readonly activeTenant = this.tenantState.activeTenant;
  readonly hasTenant = computed(() => !!this.tenantState.activeTenantId());
  readonly mobileMenuOpen = signal(false);

  toggleMobileMenu(): void {
    this.mobileMenuOpen.set(!this.mobileMenuOpen());
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }

  logout(): void {
    this.authState.logout();
    this.tenantState.clear();
    this.mobileMenuOpen.set(false);
    this.router.navigateByUrl('/auth/login');
  }
}