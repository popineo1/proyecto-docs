import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { BillingService } from '../core/services/billing.service';
import { ToastService } from '../core/services/toast.service';

@Component({
  selector: 'app-subscription-required-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="flex min-h-[70vh] items-center justify-center px-4">
      <div class="w-full max-w-lg text-center">

        <!-- Icono -->
        <div class="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-amber-50 text-4xl border border-amber-200">
          🔒
        </div>

        <h1 class="text-2xl font-semibold">Suscripción requerida</h1>
        <p class="mt-3 text-sm text-[var(--dark-gray-color)]">
          Tu suscripción ha expirado o no está activa.<br>
          Actívala para seguir usando Control Admin.
        </p>

        <!-- Beneficios -->
        <ul class="mt-6 space-y-2 text-left text-sm">
          @for (benefit of benefits; track benefit) {
            <li class="flex items-center gap-2">
              <span class="text-emerald-500">✓</span>
              {{ benefit }}
            </li>
          }
        </ul>

        <!-- CTA -->
        <button
          (click)="subscribe()"
          [disabled]="loading()"
          class="mt-8 w-full rounded-2xl bg-black py-3 text-sm font-semibold text-white transition-opacity hover:opacity-80 disabled:opacity-50"
        >
          {{ loading() ? 'Redirigiendo a pago...' : 'Activar suscripción' }}
        </button>

        <!-- Si ya pagó, puede gestionar desde el portal -->
        <button
          (click)="portal()"
          [disabled]="loading()"
          class="mt-3 w-full rounded-2xl border border-[var(--border-color)] py-3 text-sm font-medium transition-colors hover:bg-[var(--bg-gray-color)] disabled:opacity-50"
        >
          Gestionar suscripción existente
        </button>

        <p class="mt-6 text-xs text-[var(--dark-gray-color)]">
          ¿Tienes dudas?
          <a href="mailto:soporte@tuadministrativo.com" class="underline">Contáctanos</a>
        </p>
      </div>
    </div>
  `,
})
export class SubscriptionRequiredPageComponent {
  private readonly billing = inject(BillingService);
  private readonly toast = inject(ToastService);

  readonly loading = signal(false);

  readonly benefits = [
    'Procesamiento ilimitado de facturas con IA',
    'Extracción automática de datos fiscales',
    'Dashboard financiero y exportación a Excel',
    'Gestión de equipo y múltiples usuarios',
  ];

  subscribe(): void {
    this.loading.set(true);
    this.billing.startCheckout().subscribe({
      next: ({ checkout_url }) => {
        window.location.href = checkout_url;
      },
      error: () => {
        this.toast.show('No se pudo iniciar el proceso de pago. Inténtalo de nuevo.', 'error');
        this.loading.set(false);
      },
    });
  }

  portal(): void {
    this.loading.set(true);
    this.billing.openPortal().subscribe({
      next: ({ portal_url }) => {
        window.location.href = portal_url;
      },
      error: () => {
        this.toast.show('No se encontró una suscripción previa. Usa "Activar suscripción".', 'error');
        this.loading.set(false);
      },
    });
  }
}
