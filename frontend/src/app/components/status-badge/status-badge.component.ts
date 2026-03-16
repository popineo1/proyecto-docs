import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './status-badge.component.html',
})
export class StatusBadgeComponent {

  @Input() status: string | null = null;

  get classes(): string {
    const value = (this.status || '').toLowerCase();

    if (['processed', 'completed', 'approved'].includes(value)) {
      return 'bg-green-100 text-green-700 border-green-200';
    }

    if (['pending', 'running'].includes(value)) {
      return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    }

    if (['error', 'failed', 'rejected'].includes(value)) {
      return 'bg-red-100 text-red-700 border-red-200';
    }

    if (['review'].includes(value)) {
      return 'bg-blue-100 text-blue-700 border-blue-200';
    }

    return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}
