import { CommonModule, DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { finalize } from 'rxjs';
import { FinancialEntriesService } from '../../core/services/financial-entries.service';
import { FinancialEntryItem, FinancialEntryReviewRequest } from '../../core/interfaces/financial-entry.interface';
import { ToastService } from '../../core/services/toast.service';

@Component({
  selector: 'app-financial-entries-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, DatePipe],
  templateUrl: './financial-entries-page.component.html',
})
export class FinancialEntriesPageComponent {
  private readonly service = inject(FinancialEntriesService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);

  readonly entries = signal<FinancialEntryItem[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly search = signal('');
  readonly selectedEntry = signal<FinancialEntryItem | null>(null);
  readonly savingReview = signal(false);
  readonly reviewError = signal<string | null>(null);

  readonly categoryOptions = [
    { value: 'invoice', label: 'Factura' },
    { value: 'receipt', label: 'Recibo' },
    { value: 'ticket', label: 'Ticket' },
    { value: 'expense', label: 'Gasto' },
    { value: 'income', label: 'Ingreso' },
  ];

  readonly filteredEntries = computed(() => {
    const term = this.search().trim().toLowerCase();
    if (!term) return this.entries();

    return this.entries().filter((entry) =>
      [
        entry.supplier_or_customer ?? '',
        entry.category ?? '',
        entry.kind,
        entry.status_review,
        entry.currency,
      ].some((value) => value.toLowerCase().includes(term)),
    );
  });

  readonly reviewForm = this.fb.group({
    status_review: ['', Validators.required],
    supplier_or_customer: [''],
    issue_date: [''],
    tax_base: [null as number | null],
    tax_amount: [null as number | null],
    total_amount: [null as number | null],
    category: [''],
  });

  constructor() {
    this.loadEntries();
  }

  loadEntries(): void {
    this.loading.set(true);
    this.error.set(null);

    this.service.list()
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (entries) => this.entries.set(entries),
        error: (err) => {
          this.error.set(err?.error?.detail || 'No se pudieron cargar los registros.');
        },
      });
  }

  setSearch(value: string): void {
    this.search.set(value);
  }

  openReview(entry: FinancialEntryItem): void {
    this.selectedEntry.set(entry);
    this.reviewError.set(null);

    this.reviewForm.patchValue({
      status_review: entry.status_review,
      supplier_or_customer: entry.supplier_or_customer ?? '',
      issue_date: entry.issue_date ?? '',
      tax_base: entry.tax_base,
      tax_amount: entry.tax_amount,
      total_amount: entry.total_amount,
      category: entry.category ?? '',
    });
  }

  closeReview(): void {
    this.selectedEntry.set(null);
    this.reviewError.set(null);
    this.reviewForm.reset();
  }

  submitReview(): void {
    const entry = this.selectedEntry();
    if (!entry) return;

    if (this.reviewForm.invalid) {
      this.reviewForm.markAllAsTouched();
      return;
    }

    const raw = this.reviewForm.getRawValue();

    const payload: FinancialEntryReviewRequest = {
      status_review: raw.status_review || 'pending',
      supplier_or_customer: raw.supplier_or_customer || null,
      issue_date: raw.issue_date || null,
      tax_base: raw.tax_base,
      tax_amount: raw.tax_amount,
      total_amount: raw.total_amount,
      category: raw.category || null,
    };

    this.savingReview.set(true);
    this.reviewError.set(null);

    this.service.review(entry.id, payload)
      .pipe(finalize(() => this.savingReview.set(false)))
      .subscribe({
        next: (updated) => {
          this.entries.set(
            this.entries().map((item) => item.id === updated.id ? updated : item),
          );
          this.toast.show('Revisión guardada correctamente.', 'success');
          this.closeReview();
        },
        error: (err) => {
          this.reviewError.set(err?.error?.detail || 'No se pudo guardar la revisión.');
        },
      });
  }

  getReviewStatusClasses(status: string): string {
    const value = (status || '').toLowerCase();

    if (value === 'approved') return 'bg-green-100 text-green-700 border-green-200';
    if (value === 'rejected') return 'bg-red-100 text-red-700 border-red-200';
    if (value === 'pending') return 'bg-yellow-100 text-yellow-700 border-yellow-200';

    return 'bg-slate-100 text-slate-700 border-slate-200';
  }

  getReviewStatusLabel(status: string | null | undefined): string {
    const value = (status || '').toLowerCase();

    switch (value) {
      case 'pending':
        return 'Pendiente';
      case 'approved':
        return 'Aprobado';
      case 'rejected':
        return 'Rechazado';
      default:
        return status || '-';
    }
  }

  getCategoryLabel(category: string | null | undefined): string {
    const value = (category || '').trim().toLowerCase();

    switch (value) {
      case 'invoice':
        return 'Factura';
      case 'receipt':
        return 'Recibo';
      case 'ticket':
        return 'Ticket';
      case 'expense':
        return 'Gasto';
      case 'income':
        return 'Ingreso';
      default:
        return category || '-';
    }
  }

  getKindLabel(kind: string | null | undefined): string {
    const value = (kind || '').trim().toLowerCase();

    switch (value) {
      case 'expense':
        return 'Gasto';
      case 'income':
        return 'Ingreso';
      default:
        return kind || '-';
    }
  }
}