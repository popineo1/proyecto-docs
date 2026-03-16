import { Injectable, signal } from '@angular/core';

export interface ToastMessage {
  id: number;
  text: string;
  type: 'success' | 'error' | 'info';
}

@Injectable({ providedIn: 'root' })
export class ToastService {

  private counter = 0;

  readonly toasts = signal<ToastMessage[]>([]);

  show(text: string, type: ToastMessage['type'] = 'info') {

    const id = ++this.counter;

    const toast: ToastMessage = { id, text, type };

    this.toasts.set([...this.toasts(), toast]);

    setTimeout(() => {
      this.remove(id);
    }, 4000);
  }

  remove(id: number) {
    this.toasts.set(this.toasts().filter(t => t.id !== id));
  }
}
