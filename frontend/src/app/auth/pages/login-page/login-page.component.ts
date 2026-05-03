import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { AuthStateService } from '../../../core/services/auth-state.service';
import { TenantStateService } from '../../../core/services/tenant-state.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login-page.component.html',
})
export class LoginPageComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly authState = inject(AuthStateService);
  private readonly tenantState = inject(TenantStateService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showPassword = signal(false);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.error.set(null);
    this.loading.set(true);

    this.authService
      .login(this.form.getRawValue())
      .pipe(
        finalize(() => this.loading.set(false)),
      )
      .subscribe({
        next: (res) => {
          this.authState.setToken(res.access_token);
          this.authState.setRefreshToken(res.refresh_token);

          this.authService.me().subscribe({
            next: (user) => {
              this.authState.setUser(user);

              this.authService.getMyTenants().subscribe({
                next: (tenants) => {
                  this.tenantState.setTenants(tenants);

                  this.toast.show('Sesión iniciada correctamente.', 'success');

                  if (!tenants.length) {
                    this.toast.show('No tienes tenants disponibles.', 'info');
                    this.router.navigateByUrl('/select-tenant');
                    return;
                  }

                  if (tenants.length === 1) {
                    this.tenantState.setActiveTenant(tenants[0]);
                    this.router.navigateByUrl('/dashboard');
                    return;
                  }

                  this.router.navigateByUrl('/select-tenant');
                },
                error: (err) => {
                  console.error('Error cargando tenants:', err);

                  this.toast.show(
                    'Sesión iniciada, pero no se pudieron cargar los tenants.',
                    'info',
                  );

                  this.router.navigateByUrl('/select-tenant');
                },
              });
            },
            error: (err) => {
              console.error('Error cargando usuario:', err);

              this.authState.logout();
              this.tenantState.clear();

              this.error.set('No se ha podido cargar el usuario.');
              this.toast.show('No se ha podido cargar el usuario.', 'error');
            },
          });
        },
        error: (err) => {
          console.error('Error en login:', err);

          this.authState.logout();
          this.tenantState.clear();

          const detail = err?.error?.detail;

          let message = 'Credenciales inválidas.';

          if (typeof detail === 'string') {
            message = detail;
          } else if (Array.isArray(detail)) {
            message = detail
              .map((item: any) => item?.msg)
              .filter(Boolean)
              .join(', ');
          } else if (typeof err?.error?.message === 'string') {
            message = err.error.message;
          }

          this.error.set(message);
          this.toast.show(message, 'error');
        },
      });
  }
}
