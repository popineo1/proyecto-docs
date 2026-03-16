import { CommonModule, DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FinancialMovementService } from '../core/services/financial-movement.service';
import { FinancialMovement, FinancialMovementFilters } from '../core/interfaces/financial-movement.interface';


@Component({
  selector: 'app-financial-movements-page',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe],
  templateUrl: './financial-movements-page.component.html',
})
export class FinancialMovementsPageComponent {
  private readonly financialMovementService = inject(FinancialMovementService);

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
}