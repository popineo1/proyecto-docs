import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FinancialMovementService } from '../core/services/financial-movement.service';
import { FinancialMovement, FinancialMovementFilters } from '../core/interfaces/financial-movement.interface';
import { ToastService } from '../core/services/toast.service';


@Component({
  selector: 'app-financial-movements-page',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, DecimalPipe],
  templateUrl: './financial-movements-page.component.html',
})
export class FinancialMovementsPageComponent {
  private readonly financialMovementService = inject(FinancialMovementService);
  private readonly toast = inject(ToastService);

  readonly exporting = signal(false);

  readonly movements = signal<FinancialMovement[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly filters = signal<FinancialMovementFilters>({
    kind: null,
    status: null,
    source_type: null,
    category: null,
    third_party_name: null,
    business_area: null,
    needs_review: null,
    date_from: null,
    date_to: null,
    skip: 0,
    limit: 100,
  });

  readonly totalIncome = computed(() =>
    this.movements()
      .filter((m) => m.kind === 'income')
      .reduce((acc, item) => acc + this.toNumber(item.total_amount), 0)
  );

  readonly totalExpense = computed(() =>
    this.movements()
      .filter((m) => m.kind === 'expense')
      .reduce((acc, item) => acc + this.toNumber(item.total_amount), 0)
  );

  readonly balance = computed(() => this.totalIncome() - this.totalExpense());

  readonly pendingReviewCount = computed(() =>
    this.movements().filter((m) => m.needs_review).length
  );

  constructor() {
    this.loadMovements();
  }

  loadMovements(): void {
    this.loading.set(true);
    this.error.set(null);

    this.financialMovementService.listFinancialMovements(this.filters()).subscribe({
      next: (movements) => {
        this.movements.set(movements);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los movimientos financieros.');
        this.loading.set(false);
      },
    });
  }

  applyFilters(): void {
    const current = this.filters();
    this.filters.set({
      ...current,
      skip: 0,
    });
    this.loadMovements();
  }

  clearFilters(): void {
    this.filters.set({
      kind: null,
      status: null,
      source_type: null,
      category: null,
      third_party_name: null,
      business_area: null,
      needs_review: null,
      date_from: null,
      date_to: null,
      skip: 0,
      limit: 100,
    });
    this.loadMovements();
  }

  exportExcel(): void {
    const f = this.filters();
    this.exporting.set(true);
    this.financialMovementService.exportToExcel({
      kind: f.kind ?? undefined,
      date_from: f.date_from ?? undefined,
      date_to: f.date_to ?? undefined,
      category: f.category ?? undefined,
    }).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `movimientos_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 100);
        this.exporting.set(false);
      },
      error: () => {
        this.toast.show('Error al exportar. Inténtalo de nuevo.', 'error');
        this.exporting.set(false);
      },
    });
  }

  updateFilter<K extends keyof FinancialMovementFilters>(key: K, value: FinancialMovementFilters[K]): void {
    this.filters.set({
      ...this.filters(),
      [key]: value,
    });
  }

  toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  kindLabel(kind: string): string {
    switch (kind) {
      case 'income':
        return 'Ingreso';
      case 'expense':
        return 'Gasto';
      case 'tax':
        return 'Impuesto';
      case 'payroll':
        return 'Nómina';
      case 'social_security':
        return 'Seguridad social';
      default:
        return kind || '—';
    }
  }

  sourceLabel(source: string): string {
    switch (source) {
      case 'document':
        return 'Documento';
      case 'excel_import':
        return 'Excel';
      case 'manual':
        return 'Manual';
      case 'bank_import':
        return 'Banco';
      default:
        return source || '—';
    }
  }

  markAsReviewed(movement: FinancialMovement): void {
    this.financialMovementService.updateFinancialMovement(movement.id, { needs_review: false }).subscribe({
      next: (updated) => {
        this.movements.update((list) =>
          list.map((m) => (m.id === updated.id ? updated : m))
        );
      },
      error: () => {
        this.error.set('No se pudo marcar el movimiento como revisado.');
      },
    });
  }

  deleteMovement(id: string): void {
    if (!confirm('¿Estás seguro de que deseas archivar este movimiento?')) return;

    this.financialMovementService.updateFinancialMovement(id, { status: 'archived' }).subscribe({
      next: () => {
        this.movements.update((list) => list.filter((m) => m.id !== id));
      },
      error: () => {
        this.error.set('No se pudo archivar el movimiento.');
      },
    });
  }
}