import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FinancialMovementService } from '../core/services/financial-movement.service';
import { FinancialMovement } from '../core/interfaces/financial-movement.interface';

@Component({
  selector: 'app-review-inbox-page',
  standalone: true,
  imports: [CommonModule, FormsModule, DatePipe, DecimalPipe],
  templateUrl: './review-inbox-page.component.html',
})
export class ReviewInboxPageComponent {
  private readonly service = inject(FinancialMovementService);

  readonly movements = signal<FinancialMovement[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly selectedLevel = signal<'low' | 'medium' | null>(null);
  readonly expandedId = signal<string | null>(null);

  readonly lowCount = computed(() => this.movements().filter(m => m.confidence_level === 'low').length);
  readonly mediumCount = computed(() => this.movements().filter(m => m.confidence_level === 'medium').length);

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.service.getReviewInbox({
      confidence_level: this.selectedLevel() ?? undefined,
      limit: 200,
    }).subscribe({
      next: (data) => {
        this.movements.set(data);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la bandeja de revisión.');
        this.loading.set(false);
      }
    });
  }

  filterBy(level: 'low' | 'medium' | null): void {
    this.selectedLevel.set(level);
    this.load();
  }

  toggleExpand(id: string): void {
    this.expandedId.set(this.expandedId() === id ? null : id);
  }

  markAsReviewed(movement: FinancialMovement): void {
    this.service.updateFinancialMovement(movement.id, { needs_review: false }).subscribe({
      next: () => {
        this.movements.update(list => list.filter(m => m.id !== movement.id));
      },
      error: () => {
        this.error.set('No se pudo marcar el movimiento como revisado.');
      }
    });
  }

  parseInferenceLog(log: string | null): string[] {
    if (!log) return [];
    try {
      return JSON.parse(log);
    } catch {
      return [log];
    }
  }

  parseFlags(flags: string | null): string[] {
    if (!flags) return [];
    return flags.split(',').map(f => f.trim()).filter(Boolean);
  }

  toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }

  kindLabel(kind: string): string {
    const map: Record<string, string> = {
      income: 'Ingreso', expense: 'Gasto', tax: 'Impuesto',
      payroll: 'Nómina', social_security: 'Seg. Social',
    };
    return map[kind] ?? kind;
  }

  flagLabel(flag: string): string {
    const map: Record<string, string> = {
      inferred_vat: 'IVA inferido',
      missing_tax_columns: 'Sin columnas de IVA',
      math_inconsistency: 'Inconsistencia matemática',
      default_category: 'Categoría por defecto',
    };
    return map[flag] ?? flag;
  }

  confidenceBadgeClass(level: string | null): string {
    if (level === 'low') return 'badge-low';
    if (level === 'medium') return 'badge-medium';
    return 'badge-high';
  }

  confidenceLabel(level: string | null): string {
    if (level === 'low') return 'Baja';
    if (level === 'medium') return 'Media';
    return 'Alta';
  }
}
