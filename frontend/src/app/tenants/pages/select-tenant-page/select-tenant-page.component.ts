import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { TenantStateService } from '../../../core/services/tenant-state.service';


@Component({
  selector: 'app-select-tenant-page',
  standalone: true,
  templateUrl: './select-tenant-page.component.html',
})
export class SelectTenantPageComponent {
  private readonly tenantState = inject(TenantStateService);
  private readonly router = inject(Router);

  readonly tenants = this.tenantState.tenants;

  selectTenant(tenantId: string): void {
    const tenant = this.tenants().find((item) => item.tenant_id === tenantId) ?? null;
    this.tenantState.setActiveTenant(tenant);
    this.router.navigateByUrl('/dashboard');
  }
}
