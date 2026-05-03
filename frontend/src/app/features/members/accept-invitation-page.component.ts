import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { InvitationInfo, InvitationsService } from '../../core/services/invitations.service';

@Component({
  selector: 'app-accept-invitation-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div class="w-full max-w-md rounded-3xl bg-white shadow-lg p-8">

        @if (loading()) {
          <p class="text-center text-sm text-gray-500">Verificando invitación...</p>
        } @else if (error()) {
          <div class="text-center">
            <p class="text-2xl font-bold text-red-600 mb-2">Invitación no válida</p>
            <p class="text-sm text-gray-500">{{ error() }}</p>
            <a href="/auth/login" class="mt-4 inline-block text-blue-600 hover:underline text-sm">Ir al inicio de sesión</a>
          </div>
        } @else if (done()) {
          <div class="text-center">
            <p class="text-2xl font-bold text-emerald-600 mb-2">¡Bienvenido!</p>
            <p class="text-sm text-gray-500 mb-4">Tu cuenta ha sido creada correctamente en <strong>{{ info()?.tenant_name }}</strong>.</p>
            <a href="/auth/login" class="inline-block rounded-xl bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Iniciar sesión
            </a>
          </div>
        } @else {
          <div>
            <p class="text-xs font-medium uppercase tracking-widest text-gray-400 mb-1">Invitación a</p>
            <h1 class="text-2xl font-bold mb-1">{{ info()?.tenant_name }}</h1>
            <p class="text-sm text-gray-500 mb-6">Estás siendo invitado como <strong>{{ info()?.role }}</strong> con el email <strong>{{ info()?.email }}</strong>.</p>

            <form [formGroup]="form" (ngSubmit)="submit()" class="space-y-4">
              <div>
                <label class="block text-sm font-medium mb-1">Tu nombre completo</label>
                <input formControlName="full_name" type="text" placeholder="Juan García"
                  class="w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Contraseña</label>
                <input formControlName="password" type="password" placeholder="Mínimo 6 caracteres"
                  class="w-full rounded-xl border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              @if (submitError()) {
                <p class="text-sm text-red-600">{{ submitError() }}</p>
              }
              <button type="submit" [disabled]="form.invalid || submitting()"
                class="w-full rounded-xl bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
                {{ submitting() ? 'Creando cuenta...' : 'Crear cuenta y unirse' }}
              </button>
            </form>
          </div>
        }
      </div>
    </div>
  `,
})
export class AcceptInvitationPageComponent {
  private readonly svc = inject(InvitationsService);
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly done = signal(false);
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);
  readonly info = signal<InvitationInfo | null>(null);

  private token = '';

  readonly form = this.fb.nonNullable.group({
    full_name: ['', Validators.required],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  constructor() {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    if (!this.token) {
      this.error.set('Token de invitación no encontrado.');
      this.loading.set(false);
      return;
    }

    this.svc.getInfo(this.token).subscribe({
      next: (info) => { this.info.set(info); this.loading.set(false); },
      error: () => { this.error.set('Esta invitación no es válida o ha expirado.'); this.loading.set(false); },
    });
  }

  submit(): void {
    if (this.form.invalid) return;
    this.submitting.set(true);
    this.submitError.set(null);
    const { full_name, password } = this.form.getRawValue();
    this.svc.accept(this.token, full_name, password).subscribe({
      next: () => { this.done.set(true); this.submitting.set(false); },
      error: (err) => {
        this.submitError.set(err?.error?.detail || 'Error al crear la cuenta.');
        this.submitting.set(false);
      },
    });
  }
}
