import { CommonModule, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { ChartConfiguration } from 'chart.js';
import { ToastService } from '../../../core/services/toast.service';

import {
  CategoryMetric,
  DashboardSummary,
  MonthlyFlowRow,
  TaxMonthlyFlowRow,
  ThirdPartyMetric,
} from '../../../core/interfaces/dashboard.interface';
import { DashboardService, PeriodParams } from '../../../core/services/dashboard.service';
import { ChartComponent } from '../../../shared/components/chart/chart.component';

export type DashboardTab = 'overview' | 'income' | 'expenses' | 'taxes' | 'third-parties';
export type PeriodKey = 'all' | 'year' | 'year_prev' | 'q1' | 'q2' | 'q3' | 'q4' | 'month';

export interface PeriodOption {
  key: PeriodKey;
  label: string;
}

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [CommonModule, DecimalPipe, ChartComponent],
  templateUrl: './dashboard-page.component.html',
})
export class DashboardPageComponent {
  private readonly dashboardService = inject(DashboardService);
  private readonly toast = inject(ToastService);

  readonly activeTab = signal<DashboardTab>('overview');
  readonly activePeriod = signal<PeriodKey>('all');

  readonly periodOptions: PeriodOption[] = (() => {
    const now = new Date();
    const y = now.getFullYear();
    return [
      { key: 'all', label: 'Todo' },
      { key: 'year', label: `${y}` },
      { key: 'year_prev', label: `${y - 1}` },
      { key: 'q1', label: `Q1 ${y}` },
      { key: 'q2', label: `Q2 ${y}` },
      { key: 'q3', label: `Q3 ${y}` },
      { key: 'q4', label: `Q4 ${y}` },
      { key: 'month', label: new Date(y, now.getMonth(), 1).toLocaleString('es', { month: 'long', year: 'numeric' }) },
    ];
  })();
  
  readonly summary = signal<DashboardSummary | null>(null);
  readonly monthlyFlow = signal<MonthlyFlowRow[]>([]);
  readonly topSuppliers = signal<ThirdPartyMetric[]>([]);
  readonly topCustomers = signal<ThirdPartyMetric[]>([]);
  readonly categoryExpenses = signal<CategoryMetric[]>([]);
  readonly categoryIncomes = signal<CategoryMetric[]>([]);
  readonly taxMonthlyFlow = signal<TaxMonthlyFlowRow[]>([]);

  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly exporting = signal(false);

  readonly hasNegativeProfit = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.margin_cash ?? data.net_profit) < 0;
  });

  readonly hasPositiveProfit = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.margin_cash ?? data.net_profit) > 0;
  });

  readonly hasNegativeBase = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.margin_base) < 0;
  });

  readonly hasPositiveBase = computed(() => {
    const data = this.summary();
    if (!data) return false;
    return this.toNumber(data.margin_base) > 0;
  });

  readonly vatState = computed((): 'pagar' | 'compensar' | 'neutro' => {
    const data = this.summary();
    if (!data) return 'neutro';
    const balance = this.toNumber(data.vat_balance);
    if (balance > 0) return 'pagar';
    if (balance < 0) return 'compensar';
    return 'neutro';
  });

  readonly totalRetentions = computed(() => {
    const data = this.summary();
    if (!data) return 0;
    return this.toNumber(data.retention_sales) + this.toNumber(data.retention_rent);
  });

  readonly maxMonthlyValue = computed(() => {
    const rows = this.monthlyFlow();
    if (!rows.length) return 0;
    return Math.max(
      ...rows.flatMap((row) => [
        this.toNumber(row.income),
        this.toNumber(row.expenses),
      ])
    );
  });

  readonly maxTaxValue = computed(() => {
    const rows = this.taxMonthlyFlow();
    if (!rows.length) return 0;
    return Math.max(
      ...rows.flatMap((row) => [
        this.toNumber(row.vat_charged),
        this.toNumber(row.vat_supported),
      ])
    );
  });

  readonly maxSupplierValue = computed(() => {
    const rows = this.topSuppliers();
    if (!rows.length) return 0;
    return Math.max(...rows.map((row) => this.toNumber(row.amount)));
  });

  readonly maxCustomerValue = computed(() => {
    const rows = this.topCustomers();
    if (!rows.length) return 0;
    return Math.max(...rows.map((row) => this.toNumber(row.amount)));
  });

  readonly quickHeadline = computed(() => {
    const data = this.summary();
    if (!data) return '';

    const income = this.toNumber(data.total_income);
    const profit = this.toNumber(data.net_profit);

    if (income <= 0) {
      return 'Todavía no hay ingresos suficientes para evaluar el rendimiento financiero.';
    }

    if (profit < 0) {
      return 'El flujo de caja ya registra ingresos, pero el resultado neto actual es negativo.';
    }

    return 'El negocio presenta un resultado financiero positivo con margen de beneficio consolidado.';
  });

  readonly incomeVsExpenseChart = computed<ChartConfiguration['data']>(() => {
    const rows = this.monthlyFlow();
    return {
      labels: rows.map(r => this.monthLabel(r.month)),
      datasets: [
        {
          label: 'Ingresos',
          data: rows.map(r => this.toNumber(r.income)),
          backgroundColor: '#10b981',
          borderRadius: 6,
        },
        {
          label: 'Gastos',
          data: rows.map(r => this.toNumber(r.expenses)),
          backgroundColor: '#f43f5e',
          borderRadius: 6,
        }
      ]
    };
  });

  readonly categoryExpensesChart = computed<ChartConfiguration['data']>(() => {
    const cats = this.categoryExpenses();
    return {
      labels: cats.map(c => c.category_name || 'Sin categoría'),
      datasets: [{
        data: cats.map(c => this.toNumber(c.total_amount)),
        backgroundColor: ['#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e', '#f97316', '#eab308']
      }]
    };
  });

  readonly categoryIncomesChart = computed<ChartConfiguration['data']>(() => {
    const cats = this.categoryIncomes();
    return {
      labels: cats.map(c => c.category_name || 'Sin categoría'),
      datasets: [{
        data: cats.map(c => this.toNumber(c.total_amount)),
        backgroundColor: ['#10b981', '#34d399', '#6ee7b7', '#a7f3d0', '#059669', '#065f46']
      }]
    };
  });

  readonly taxFlowChart = computed<ChartConfiguration['data']>(() => {
    const rows = this.taxMonthlyFlow();
    return {
      labels: rows.map(r => this.monthLabel(r.month)),
      datasets: [
        {
          label: 'IVA Repercutido',
          data: rows.map(r => this.toNumber(r.vat_charged)),
          borderColor: '#10b981',
          backgroundColor: '#10b98122',
          fill: true,
          tension: 0.4
        },
        {
          label: 'IVA Soportado',
          data: rows.map(r => this.toNumber(r.vat_supported)),
          borderColor: '#f43f5e',
          backgroundColor: '#f43f5e22',
          fill: true,
          tension: 0.4
        }
      ]
    };
  });

  constructor() {
    this.loadDashboard();
  }

  exportExcel(): void {
    const period = this.buildPeriodParams(this.activePeriod());
    this.exporting.set(true);
    this.dashboardService.exportDashboard(period).subscribe({
      next: (blob) => {
        // Si el servidor devolvió un error, el blob puede contener JSON de error
        if (blob.type === 'application/json' || blob.size === 0) {
          this.toast.show('Error al generar el Excel. Inténtalo de nuevo.', 'error');
          this.exporting.set(false);
          return;
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dashboard_${this.activePeriod()}_${new Date().toISOString().slice(0, 10)}.xlsx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 100);
        this.exporting.set(false);
      },
      error: (err) => {
        // Con responseType:'blob', el error body llega como Blob — leerlo para mostrar el detalle
        if (err?.error instanceof Blob) {
          err.error.text().then((text: string) => {
            try {
              const json = JSON.parse(text);
              this.toast.show(json?.detail || 'Error al exportar el dashboard.', 'error');
            } catch {
              this.toast.show(`Error ${err.status}: ${text || 'Error al exportar.'}`, 'error');
            }
          });
        } else {
          this.toast.show(err?.error?.detail || 'Error al exportar el dashboard.', 'error');
        }
        this.exporting.set(false);
      },
    });
  }

  setTab(tab: DashboardTab): void {
    this.activeTab.set(tab);
  }

  setPeriod(period: PeriodKey): void {
    this.activePeriod.set(period);
    this.loadDashboard();
  }

  buildPeriodParams(key: PeriodKey): PeriodParams {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth() + 1;
    const pad = (n: number) => String(n).padStart(2, '0');
    const fmt = (yr: number, mo: number, day: number) => `${yr}-${pad(mo)}-${pad(day)}`;
    const lastDay = (yr: number, mo: number) => new Date(yr, mo, 0).getDate();

    switch (key) {
      case 'year':      return { date_from: fmt(y, 1, 1), date_to: fmt(y, 12, 31) };
      case 'year_prev': return { date_from: fmt(y - 1, 1, 1), date_to: fmt(y - 1, 12, 31) };
      case 'q1':        return { date_from: fmt(y, 1, 1), date_to: fmt(y, 3, 31) };
      case 'q2':        return { date_from: fmt(y, 4, 1), date_to: fmt(y, 6, 30) };
      case 'q3':        return { date_from: fmt(y, 7, 1), date_to: fmt(y, 9, 30) };
      case 'q4':        return { date_from: fmt(y, 10, 1), date_to: fmt(y, 12, 31) };
      case 'month':     return { date_from: fmt(y, m, 1), date_to: fmt(y, m, lastDay(y, m)) };
      default:          return {};
    }
  }

  loadDashboard(): void {
    this.loading.set(true);
    this.error.set(null);

    const period = this.buildPeriodParams(this.activePeriod());

    forkJoin({
      summary: this.dashboardService.getOverview(period),
      monthly: this.dashboardService.getMonthlyFlow(period),
      suppliers: this.dashboardService.getTopSuppliers(5, period),
      customers: this.dashboardService.getTopCustomers(5, period),
      expensesByCat: this.dashboardService.getExpensesByCategory(6, period),
      incomeByCat: this.dashboardService.getIncomeByCategory(6, period),
      taxFlow: this.dashboardService.getTaxMonthlyFlow(period),
    }).subscribe({
      next: (data) => {
        this.summary.set(data.summary);
        this.monthlyFlow.set(data.monthly);
        this.topSuppliers.set(data.suppliers);
        this.topCustomers.set(data.customers);
        this.categoryExpenses.set(data.expensesByCat);
        this.categoryIncomes.set(data.incomeByCat);
        this.taxMonthlyFlow.set(data.taxFlow);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el dashboard financiero.');
        this.loading.set(false);
      },
    });
  }

  toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
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
    if (!month) return '';
    const parts = month.split('-');
    if (parts.length < 2) return month;
    const [year, monthNum] = parts;
    const names = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const idx = Number(monthNum) - 1;
    return idx >= 0 && idx < names.length ? `${names[idx]} ${year}` : month;
  }
}