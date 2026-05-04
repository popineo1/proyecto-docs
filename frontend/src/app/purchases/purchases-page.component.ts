import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';
import { PurchaseEntry, PurchaseImportResult, PurchasesService } from '../core/services/purchases.service';
import { ToastService } from '../core/services/toast.service';

@Component({
  selector: 'app-purchases-page',
  standalone: true,
  imports: [CommonModule, DatePipe, DecimalPipe],
  template: `
    <div class="space-y-6">

      <!-- Header -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h1 class="text-2xl font-semibold">Compras</h1>
        <p class="mt-1 text-sm text-[var(--dark-gray-color)]">
          Importa y consulta los registros de compras desde un Excel. Cada fila del Excel se convierte en un registro de compra.
        </p>
      </div>

      <!-- Import -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <h2 class="text-lg font-semibold mb-4">Importar desde Excel</h2>
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
          <label
            class="cursor-pointer rounded-xl border-2 border-dashed border-[var(--border-color)] px-6 py-4 text-sm text-[var(--dark-gray-color)] hover:border-blue-400 transition-colors"
          >
            <input
              type="file"
              accept=".xlsx,.xls"
              class="hidden"
              (change)="onFileSelected($event)"
            />
            @if (selectedFile()) {
              <span class="text-[var(--text-color)] font-medium">{{ selectedFile()!.name }}</span>
            } @else {
              <span>Seleccionar archivo Excel (.xlsx)</span>
            }
          </label>
          <button
            [disabled]="!selectedFile() || importing()"
            (click)="importFile()"
            class="rounded-xl bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {{ importing() ? 'Importando...' : 'Importar' }}
          </button>
        </div>

        @if (importResult()) {
          <div class="mt-4 rounded-xl border border-[var(--border-color)] bg-[var(--bg-gray-color)] p-4 text-sm">
            <p class="font-medium mb-1">Resultado de importación</p>
            <ul class="text-[var(--dark-gray-color)] space-y-0.5">
              <li>Filas detectadas: <strong>{{ importResult()!.rows_detected }}</strong></li>
              <li>Importadas: <strong class="text-emerald-600">{{ importResult()!.rows_imported }}</strong></li>
              <li>Omitidas (duplicadas): <strong class="text-yellow-600">{{ importResult()!.rows_skipped }}</strong></li>
            </ul>
          </div>
        }
      </div>

      <!-- Table -->
      <div class="rounded-3xl border border-[var(--border-color)] bg-[var(--bright-bg-color)] p-6 shadow-sm">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">Registros de compras</h2>
          <span class="text-xs text-[var(--dark-gray-color)]">{{ purchases().length }} registros</span>
        </div>

        @if (loading()) {
          <p class="text-sm text-[var(--dark-gray-color)]">Cargando...</p>
        } @else if (!purchases().length) {
          <p class="text-sm text-[var(--dark-gray-color)]">No hay compras registradas. Importa un Excel para empezar.</p>
        } @else {
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-[var(--border-color)] text-left text-xs font-medium uppercase text-[var(--dark-gray-color)]">
                  <th class="pb-3 pr-4">Proveedor</th>
                  <th class="pb-3 pr-4">Fecha</th>
                  <th class="pb-3 pr-4">Categoría</th>
                  <th class="pb-3 pr-4 text-right">Base (€)</th>
                  <th class="pb-3 pr-4 text-right">IVA (€)</th>
                  <th class="pb-3 text-right">Total (€)</th>
                </tr>
              </thead>
              <tbody>
                @for (p of purchases(); track p.id) {
                  <tr class="border-b border-[var(--border-color)] last:border-0 hover:bg-[var(--muted-hover-color)]">
                    <td class="py-3 pr-4 font-medium">{{ p.provider_name }}</td>
                    <td class="py-3 pr-4 text-[var(--dark-gray-color)]">
                      {{ (p.issue_date || p.order_date) | date:'dd/MM/yyyy' }}
                    </td>
                    <td class="py-3 pr-4 text-[var(--dark-gray-color)]">{{ p.category || '—' }}</td>
                    <td class="py-3 pr-4 text-right tabular-nums">{{ p.net_amount | number:'1.2-2' }}</td>
                    <td class="py-3 pr-4 text-right tabular-nums">{{ p.tax_amount | number:'1.2-2' }}</td>
                    <td class="py-3 text-right tabular-nums font-semibold">{{ p.total_amount | number:'1.2-2' }}</td>
                  </tr>
                }
              </tbody>
              <tfoot>
                <tr class="border-t-2 border-[var(--border-color)]">
                  <td colspan="5" class="pt-3 pr-4 text-right text-xs font-medium uppercase text-[var(--dark-gray-color)]">Total</td>
                  <td class="pt-3 text-right tabular-nums font-bold">
                    {{ totalAmount() | number:'1.2-2' }} €
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          @if (purchases().length >= limit()) {
            <div class="mt-4 flex justify-center">
              <button
                (click)="loadMore()"
                [disabled]="loadingMore()"
                class="rounded-xl border border-[var(--border-color)] px-5 py-2 text-sm hover:bg-[var(--muted-hover-color)] disabled:opacity-60"
              >
                {{ loadingMore() ? 'Cargando...' : 'Cargar más' }}
              </button>
            </div>
          }
        }
      </div>

    </div>
  `,
})
export class PurchasesPageComponent {
  private readonly svc = inject(PurchasesService);
  private readonly toast = inject(ToastService);

  readonly purchases = signal<PurchaseEntry[]>([]);
  readonly loading = signal(true);
  readonly loadingMore = signal(false);
  readonly importing = signal(false);
  readonly selectedFile = signal<File | null>(null);
  readonly importResult = signal<PurchaseImportResult | null>(null);

  readonly limit = signal(50);
  private skip = 0;

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.skip = 0;
    this.svc.list(0, this.limit()).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (list) => { this.purchases.set(list); this.skip = list.length; },
      error: () => this.toast.show('Error al cargar las compras.', 'error'),
    });
  }

  loadMore(): void {
    this.loadingMore.set(true);
    this.svc.list(this.skip, this.limit()).pipe(finalize(() => this.loadingMore.set(false))).subscribe({
      next: (list) => {
        this.purchases.update((prev) => [...prev, ...list]);
        this.skip += list.length;
      },
      error: () => this.toast.show('Error al cargar más registros.', 'error'),
    });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    this.importResult.set(null);
  }

  importFile(): void {
    const file = this.selectedFile();
    if (!file) return;
    this.importing.set(true);
    this.svc.importExcel(file).pipe(finalize(() => this.importing.set(false))).subscribe({
      next: (result) => {
        this.importResult.set(result);
        this.selectedFile.set(null);
        this.toast.show(`Importación completada: ${result.rows_imported} registros añadidos.`, 'success');
        this.load();
      },
      error: (err) => this.toast.show(err?.error?.detail || 'Error al importar el archivo.', 'error'),
    });
  }

  totalAmount(): number {
    return this.purchases().reduce((sum, p) => sum + Number(p.total_amount), 0);
  }
}
