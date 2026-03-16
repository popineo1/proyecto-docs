import { Component, computed, input, output } from '@angular/core';
import { NgClass } from '@angular/common';

type PopupWidth = 'sm' | 'default' | 'lg' | 'xl';
type PopupHeight = 'sm' | 'default' | 'lg' | 'xl';

@Component({
  selector: 'popup-container',
  standalone: true,
  imports: [NgClass],
  templateUrl: './popup-container.component.html',
})
export class PopupContainerComponent {
  show = input.required<boolean>();
  popupTitle = input<string>('');
  popupSubtitle = input<string>('');
  showCloseButton = input<boolean>(true);
  closeOnBackdrop = input<boolean>(true);

  widthSize = input<PopupWidth>('default');
  heightSize = input<PopupHeight>('default');

  close = output<void>();

  widthCls = computed(() => {
    switch (this.widthSize()) {
      case 'sm':
        return 'w-full max-w-md';
      case 'lg':
        return 'w-full max-w-4xl';
      case 'xl':
        return 'w-full max-w-6xl';
      default:
        return 'w-full max-w-3xl';
    }
  });

  heightCls = computed(() => {
    switch (this.heightSize()) {
      case 'sm':
        return 'max-h-[60vh]';
      case 'lg':
        return 'max-h-[85vh]';
      case 'xl':
        return 'max-h-[95vh]';
      default:
        return 'max-h-[75vh]';
    }
  });

  onBackdropClick(): void {
    if (this.closeOnBackdrop()) {
      this.close.emit();
    }
  }

  onCloseClick(): void {
    this.close.emit();
  }
}