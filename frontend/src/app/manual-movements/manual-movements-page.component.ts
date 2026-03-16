import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FinancialMovementService } from '../core/services/financial-movement.service';
import { FinancialMovement } from '../core/interfaces/financial-movement.interface';
import { ManualMovementCreateRequest } from '../core/interfaces/manual-movement.interface';

@Component({
  selector: 'app-manual-movements-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './manual-movements-page.component.html',
})
export class ManualMovementsPageComponent {
  private readonly financialMovementService = inject(FinancialMovementService);

  readonly loading = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<string | null>(null);

  readonly movements = signal<FinancialMovement[]>([]);

  readonly form = signal<ManualMovementCreateRequest>({
    movement_date: new Date().toISOString().slice(0, 10),
    movement_type: 'manual_expense',
    third_party_name: '',
    third_party_tax_id: null,
    concept: '',
    category: null,
    subcategory: null,
    business_area: 'administracion',
    net_amount: null,
    tax_amount: 0,
    withholding_amount: 0,
    total_amount: 0,
    currency: 'EUR',
    notes: null,
    needs_review: false,
  });

  constructor() {
    this.loadManualMovements();
  }

  loadManualMovements(): void {
    this.loading.set(true);
    this.error.set(null);

    this.financialMovementService.listManualMovements({ limit: 100 }).subscribe({
      next: (movements) => {
        this.movements.set(movements);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los movimientos manuales.');
        this.loading.set(false);
      },
    });
  }

  updateForm<K extends keyof ManualMovementCreateRequest>(
    key: K,
    value: ManualMovementCreateRequest[K]
  ): void {
    this.form.set({
      ...this.form(),
      [key]: value,
    });
  }

  submit(): void {
    this.saving.set(true);
    this.error.set(null);
    this.success.set(null);

    this.financialMovementService.createManualMovement(this.form()).subscribe({
      next: () => {
        this.success.set('Movimiento manual creado correctamente.');
        this.saving.set(false);

        this.form.set({
          movement_date: new Date().toISOString().slice(0, 10),
          movement_type: 'manual_expense',
          third_party_name: '',
          third_party_tax_id: null,
          concept: '',
          category: null,
          subcategory: null,
          business_area: 'administracion',
          net_amount: null,
          tax_amount: 0,
          withholding_amount: 0,
          total_amount: 0,
          currency: 'EUR',
          notes: null,
          needs_review: false,
        });

        this.loadManualMovements();
      },
      error: () => {
        this.error.set('No se pudo crear el movimiento manual.');
        this.saving.set(false);
      },
    });
  }

  toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  movementTypeLabel(type: string): string {
    switch (type) {
      case 'payroll':
        return 'Nómina';
      case 'social_security':
        return 'Seguridad social';
      case 'tax':
        return 'Impuesto';
      case 'freelance_fee':
        return 'Colaborador';
      case 'manual_income':
        return 'Ingreso manual';
      case 'manual_expense':
        return 'Gasto manual';
      default:
        return type;
    }
  }
}