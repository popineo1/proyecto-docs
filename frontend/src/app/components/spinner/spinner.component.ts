import { Component } from '@angular/core';

@Component({
  selector: 'app-spinner',
  standalone: true,
  template: `
  <div class="flex justify-center py-10">
    <div class="h-8 w-8 animate-spin rounded-full border-4 border-[var(--primary-color)] border-t-transparent"></div>
  </div>
  `,
})
export class SpinnerComponent {}
