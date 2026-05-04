import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { BillingService, SubscriptionStatus } from '../core/services/billing.service';
import { ToastService } from '../core/services/toast.service';

@Component({
  selector: 'app-billing-page',
  standalone: true,
  template: `
    <div class="space-y-5">
      <!-- Header -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-5 shadow-sm">
        <p class="text-xs font-medium uppercase tracking-[0.18em] text-[var(--dark-gray-color)]">Cuenta</p>
        <h1 class="mt-2 text-2xl font-semibold">Facturación</h1>
        <p class="mt-1 text-sm text-[var(--dark-gray-color)]">
          Gestiona tu suscripción, método de pago y facturas de Stripe.
        </p>
      </div>

      <!-- Banner éxito / cancelación -->
      @if (successBanner()) {
        <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-800">
          Suscripción activada correctamente. ¡Bienvenido a Control Admin!
        </div>
      }
      @if (canceledBanner()) {
        <div class="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
          Has cancelado el proceso de pago. Puedes volver a intentarlo cuando quieras.
        </div>
      }

      <!-- Estado de la suscripción -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h2 class="text-base font-semibold">Estado de la suscripción</h2>

        @if (loading()) {
          <p class="mt-4 text-sm text-[var(--dark-gray-color)]">Cargando...</p>
        } @else if (status()) {
          <div class="mt-4 space-y-3">
            <div class="flex items-center gap-3">
              <span
                class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
                [class]="statusBadgeClass()"
              >
                {{ statusLabel() }}
              </span>
            </div>

            @if (status()!.subscription_period_end) {
              <p class="text-sm text-[var(--dark-gray-color)]">
                {{ status()!.is_active ? 'Próxima renovación:' : 'Venció el:' }}
                <span class="font-medium text-[var(--text-color)]">
                  {{ formatDate(status()!.subscription_period_end!) }}
                </span>
              </p>
            }
          </div>

          <!-- Acciones -->
          <div class="mt-6 flex flex-wrap gap-3">
            @if (status()!.is_active) {
              <!-- Portal: cancelar, cambiar tarjeta, ver facturas -->
              <button
                (click)="openPortal()"
                [disabled]="actionLoading()"
                class="rounded-2xl border border-[var(--border-color)] px-5 py-2.5 text-sm font-medium transition-colors hover:bg-[var(--bg-gray-color)] disabled:opacity-50"
              >
                {{ actionLoading() ? 'Abriendo...' : 'Gestionar suscripción' }}
              </button>
            } @else {
              <!-- Checkout: nueva suscripción -->
              <button
                (click)="startCheckout()"
                [disabled]="actionLoading()"
                class="rounded-2xl bg-black px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-80 disabled:opacity-50"
              >
                {{ actionLoading() ? 'Redirigiendo...' : 'Activar suscripción' }}
              </button>
              @if (status()!.stripe_customer_id) {
                <button
                  (click)="openPortal()"
                  [disabled]="actionLoading()"
                  class="rounded-2xl border border-[var(--border-color)] px-5 py-2.5 text-sm font-medium transition-colors hover:bg-[var(--bg-gray-color)] disabled:opacity-50"
                >
                  Gestionar suscripción existente
                </button>
              }
            }
          </div>
        }
      </div>

      <!-- Info -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-5 shadow-sm text-sm text-[var(--dark-gray-color)]">
        <p class="font-medium text-[var(--text-color)]">Sobre la facturación</p>
        <ul class="mt-2 space-y-1 list-disc list-inside">
          <li>Los pagos se procesan de forma segura a través de Stripe.</li>
          <li>Puedes cancelar en cualquier momento desde el portal de gestión.</li>
          <li>Tus facturas de Stripe están disponibles en el portal de gestión.</li>
          <li>¿Necesitas ayuda? <a href="mailto:soporte@tuadministrativo.com" class="underline">Contáctanos</a></li>
        </ul>
      </div>
    </div>
  `,
})
export class BillingPageComponent implements OnInit {
  private readonly billing = inject(BillingService);
  private readonly toast = inject(ToastService);
  private readonly route = inject(ActivatedRoute);

  readonly status = signal<SubscriptionStatus | null>(null);
  readonly loading = signal(true);
  readonly actionLoading = signal(false);
  readonly successBanner = signal(false);
  readonly canceledBanner = signal(false);

  ngOnInit(): void {
    // Banners desde query params (Stripe redirige con ?success=1 o ?canceled=1)
    this.route.queryParamMap.subscribe(params => {
      if (params.get('success')) this.successBanner.set(true);
      if (params.get('canceled')) this.canceledBanner.set(true);
    });

    this.billing.getStatus().subscribe({
      next: (s) => { this.status.set(s); this.loading.set(false); },
      error: () => { this.loading.set(false); },
    });
  }

  startCheckout(): void {
    this.actionLoading.set(true);
    this.billing.startCheckout().subscribe({
      next: ({ checkout_url }) => { window.location.href = checkout_url; },
      error: () => {
        this.toast.show('No se pudo iniciar el proceso de pago.', 'error');
        this.actionLoading.set(false);
      },
    });
  }

  openPortal(): void {
    this.actionLoading.set(true);
    this.billing.openPortal().subscribe({
      next: ({ portal_url }) => { window.location.href = portal_url; },
      error: () => {
        this.toast.show('No se pudo abrir el portal de gestión.', 'error');
        this.actionLoading.set(false);
      },
    });
  }

  statusLabel(): string {
    const map: Record<string, string> = {
      active: 'Activa',
      trialing: 'En prueba',
      past_due: 'Pago pendiente',
      canceled: 'Cancelada',
      unpaid: 'Impagada',
      incomplete: 'Incompleta',
    };
    return map[this.status()?.subscription_status ?? ''] ?? 'Sin suscripción';
  }

  statusBadgeClass(): string {
    const s = this.status()?.subscription_status;
    if (s === 'active' || s === 'trialing') return 'bg-emerald-100 text-emerald-700';
    if (s === 'past_due' || s === 'unpaid') return 'bg-amber-100 text-amber-700';
    return 'bg-gray-100 text-gray-600';
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
  }
}
