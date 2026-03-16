import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import {
  CategoryMetric,
  DashboardSummary,
  MonthlyProfitabilityRow,
  SupplierMetric,
} from '../../../core/interfaces/dashboard.interface';
import { DashboardService } from '../../../core/services/dashboard.service';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard-page.component.html',
})
export class DashboardPageComponent {
  private readonly dashboardService = inject(DashboardService);

  readonly summary = signal<DashboardSummary | null>(null);
  readonly monthlyProfitability = signal<MonthlyProfitabilityRow[]>([]);
  readonly topSuppliers = signal<SupplierMetric[]>([]);
  readonly categoryExpenses = signal<CategoryMetric[]>([]);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  readonly hasNegativeMargin = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.gross_margin) < 0;
  });

  readonly hasPositiveMargin = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.gross_margin) > 0;
  });

  readonly maxMonthlyValue = computed(() => {
    const rows = this.monthlyProfitability();
    if (!rows.length) return 0;

    return Math.max(
      ...rows.flatMap((row) => [
        this.toNumber(row.sales_gross),
        this.toNumber(row.purchases_gross),
        Math.abs(this.toNumber(row.gross_margin_amount)),
      ])
    );
  });

  readonly maxSupplierValue = computed(() => {
    const rows = this.topSuppliers();
    if (!rows.length) return 0;
    return Math.max(...rows.map((row) => this.toNumber(row.total_amount)));
  });

  readonly maxCategoryValue = computed(() => {
    const rows = this.categoryExpenses();
    if (!rows.length) return 0;
    return Math.max(...rows.map((row) => this.toNumber(row.total_amount)));
  });

  readonly quickHeadline = computed(() => {
    const data = this.summary();
    if (!data) return '';

    const income = this.toNumber(data.total_income);
    const expenses = this.toNumber(data.total_expenses);
    const margin = this.toNumber(data.gross_margin);

    if (income <= 0) {
      return 'Todavía no hay ingresos suficientes para evaluar la rentabilidad del negocio.';
    }

    if (margin < 0) {
      return 'El negocio ya genera ingresos, pero el margen actual sigue siendo negativo.';
    }

    if (expenses <= 0) {
      return 'Hay ingresos registrados y prácticamente no hay gastos consolidados.';
    }

    return 'El negocio presenta una estructura financiera más equilibrada y ya genera margen positivo.';
  });

  constructor() {
    this.loadDashboard();
  }

  loadDashboard(): void {
    this.loading.set(true);
    this.error.set(null);

    forkJoin({
      summary: this.dashboardService.getOverview(),
      monthly: this.dashboardService.getMonthlyProfitability(),
      suppliers: this.dashboardService.getTopSuppliers(),
      categories: this.dashboardService.getExpensesByCategory(),
    }).subscribe({
      next: ({ summary, monthly, suppliers, categories }) => {
        this.summary.set(summary);
        this.monthlyProfitability.set(monthly);
        this.topSuppliers.set(suppliers);
        this.categoryExpenses.set(categories);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el dashboard.');
        this.loading.set(false);
      },
    });
  }

  toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  toPercent(value: string | number | null | undefined): number {
    return this.toNumber(value) * 100;
  }

  absNumber(value: string | number | null | undefined): number {
    return Math.abs(this.toNumber(value));
  }

  barWidth(value: string | number, max: number): string {
    const numeric = this.toNumber(value);
    if (max <= 0) return '0%';
    return `${Math.max((numeric / max) * 100, 4)}%`;
  }

  monthLabel(month: string): string {
    const [year, monthNum] = month.split('-');
    const names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const idx = Number(monthNum) - 1;
    return idx >= 0 && idx < names.length ? `${names[idx]} ${year}` : month;
  }
}