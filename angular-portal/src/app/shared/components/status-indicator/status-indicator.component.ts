import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-status-indicator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span class="dot" [class]="'dot-' + status"></span>
    <span class="label">{{ label ?? status }}</span>
  `,
  styles: [`
    :host { display: inline-flex; align-items: center; gap: 6px; }
    .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
    .dot-healthy, .dot-ok, .dot-configured { background: #4caf50; }
    .dot-error, .dot-violated { background: #f44336; }
    .dot-not_configured, .dot-unknown { background: #9e9e9e; }
    .dot-warning { background: #ff9800; }
    .label { font-size: 13px; }
  `],
})
export class StatusIndicatorComponent {
  @Input() status: string = 'unknown';
  @Input() label?: string;
}
