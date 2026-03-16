import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  template: `
  <div class="rounded-2xl border border-dashed border-[var(--border-color)] px-6 py-12 text-center text-[var(--dark-gray-color)]">
    <p class="font-medium text-lg">{{ title }}</p>
    <p class="mt-2 text-sm">{{ description }}</p>
  </div>
  `,
})
export class EmptyStateComponent {

  @Input() title = 'No hay datos';
  @Input() description = '';
}
