import { Injectable, computed, signal } from '@angular/core';
import { StorageService } from './storage.service';
import { UserTenant } from '../interfaces/tenant.interface';


const TENANTS_KEY = 'docs_tenants';
const ACTIVE_TENANT_KEY = 'docs_active_tenant';

@Injectable({ providedIn: 'root' })
export class TenantStateService {
  private readonly tenantsSignal = signal<UserTenant[]>([]);
  private readonly activeTenantSignal = signal<UserTenant | null>(null);

  readonly tenants = computed(() => this.tenantsSignal());
  readonly activeTenant = computed(() => this.activeTenantSignal());
  readonly activeTenantId = computed(() => this.activeTenantSignal()?.tenant_id ?? null);

  constructor(private storage: StorageService) {
    const savedTenants = this.storage.get<UserTenant[]>(TENANTS_KEY) ?? [];
    const savedActive = this.storage.get<UserTenant>(ACTIVE_TENANT_KEY);

    this.tenantsSignal.set(savedTenants);
    if (savedActive) this.activeTenantSignal.set(savedActive);
  }

  setTenants(tenants: UserTenant[]): void {
    this.tenantsSignal.set(tenants);
    this.storage.set(TENANTS_KEY, tenants);
  }

  setActiveTenant(tenant: UserTenant | null): void {
    this.activeTenantSignal.set(tenant);

    if (tenant) this.storage.set(ACTIVE_TENANT_KEY, tenant);
    else this.storage.remove(ACTIVE_TENANT_KEY);
  }

  clear(): void {
    this.tenantsSignal.set([]);
    this.activeTenantSignal.set(null);
    this.storage.remove(TENANTS_KEY);
    this.storage.remove(ACTIVE_TENANT_KEY);
  }
}
