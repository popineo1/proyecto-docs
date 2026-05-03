import { CommonModule, DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { environment } from '../../environments/environment';
import { Invitation, InvitationsService } from '../../core/services/invitations.service';
import { ToastService } from '../../core/services/toast.service';

@Component({
  selector: 'app-members-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  template: `
    <div class="space-y-6">
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h1 class="text-2xl font-semibold">Miembros del equipo</h1>
        <p class="mt-1 text-sm text-[var(--dark-gray-color)]">Invita a colaboradores a tu empresa. Recibirán un enlace para crear su cuenta.</p>
      </div>

      <!-- Invitar -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h2 class="text-lg font-semibold mb-4">Invitar a alguien</h2>
        <form [formGroup]="form" (ngSubmit)="invite()" class="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="flex-1">
            <label class="block text-sm font-medium mb-1">Email</label>
            <input formControlName="email" type="email" placeholder="correo@empresa.com"
              class="w-full rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="w-40">
            <label class="block text-sm font-medium mb-1">Rol</label>
            <select formControlName="role"
              class="w-full rounded-xl border border-[var(--border-color)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="member">Miembro</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <button type="submit" [disabled]="form.invalid || sending()"
            class="rounded-xl bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60">
            {{ sending() ? 'Enviando...' : 'Invitar' }}
          </button>
        </form>
      </div>

      <!-- Lista invitaciones -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h2 class="text-lg font-semibold mb-4">Invitaciones enviadas</h2>

        @if (loading()) {
          <p class="text-sm text-[var(--dark-gray-color)]">Cargando...</p>
        } @else if (!invitations().length) {
          <p class="text-sm text-[var(--dark-gray-color)]">No hay invitaciones todavía.</p>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-[var(--border-color)] text-left text-xs font-medium uppercase text-[var(--dark-gray-color)]">
                  <th class="pb-3 pr-4">Email</th>
                  <th class="pb-3 pr-4">Rol</th>
                  <th class="pb-3 pr-4">Estado</th>
                  <th class="pb-3 pr-4">Expira</th>
                  <th class="pb-3 pr-4">Enlace</th>
                  <th class="pb-3"></th>
                </tr>
              </thead>
              <tbody>
                @for (inv of invitations(); track inv.id) {
                  <tr class="border-b border-[var(--border-color)] last:border-0">
                    <td class="py-3 pr-4 font-medium">{{ inv.email }}</td>
                    <td class="py-3 pr-4 capitalize">{{ inv.role }}</td>
                    <td class="py-3 pr-4">
                      <span class="rounded-full px-2 py-0.5 text-xs font-medium"
                        [class]="statusClass(inv.status)">
                        {{ statusLabel(inv.status) }}
                      </span>
                    </td>
                    <td class="py-3 pr-4 text-[var(--dark-gray-color)]">{{ inv.expires_at | date:'dd/MM/yyyy' }}</td>
                    <td class="py-3 pr-4">
                      @if (inv.status === 'pending') {
                        <button (click)="copyLink(inv.token)"
                          class="text-blue-600 hover:underline text-xs">
                          Copiar enlace
                        </button>
                      }
                    </td>
                    <td class="py-3">
                      @if (inv.status === 'pending') {
                        <button (click)="cancel(inv.id)"
                          class="text-red-500 hover:underline text-xs">
                          Cancelar
                        </button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </div>
  `,
})
export class MembersPageComponent {
  private readonly svc = inject(InvitationsService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);

  readonly invitations = signal<Invitation[]>([]);
  readonly loading = signal(true);
  readonly sending = signal(false);

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    role: ['member'],
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.svc.list().subscribe({
      next: (list) => { this.invitations.set(list); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  invite(): void {
    if (this.form.invalid) return;
    this.sending.set(true);
    const { email, role } = this.form.getRawValue();
    this.svc.create(email, role).subscribe({
      next: (inv) => {
        this.invitations.update((list) => [inv, ...list]);
        this.form.reset({ email: '', role: 'member' });
        this.toast.show('Invitación creada. Copia el enlace y compártelo.', 'success');
        this.sending.set(false);
      },
      error: (err) => {
        this.toast.show(err?.error?.detail || 'Error al crear la invitación.', 'error');
        this.sending.set(false);
      },
    });
  }

  cancel(id: string): void {
    this.svc.cancel(id).subscribe({
      next: () => {
        this.invitations.update((list) => list.map((i) => i.id === id ? { ...i, status: 'cancelled' } : i));
        this.toast.show('Invitación cancelada.', 'info');
      },
      error: () => this.toast.show('Error al cancelar.', 'error'),
    });
  }

  copyLink(token: string): void {
    const link = `${window.location.origin}/join/${token}`;
    navigator.clipboard.writeText(link).then(() => {
      this.toast.show('Enlace copiado al portapapeles.', 'success');
    });
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = { pending: 'Pendiente', accepted: 'Aceptada', cancelled: 'Cancelada' };
    return labels[status] ?? status;
  }

  statusClass(status: string): string {
    if (status === 'accepted') return 'bg-emerald-100 text-emerald-700';
    if (status === 'cancelled') return 'bg-red-100 text-red-700';
    return 'bg-yellow-100 text-yellow-700';
  }
}
