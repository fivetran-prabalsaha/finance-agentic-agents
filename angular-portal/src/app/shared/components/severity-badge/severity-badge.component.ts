import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';

@Component({
  selector: 'app-severity-badge',
  standalone: true,
  imports: [CommonModule, MatChipsModule],
  template: `
    <mat-chip [class]="'severity-' + (severity | lowercase)">
      {{ severity }}
    </mat-chip>
  `,
  styles: [`
    mat-chip { font-weight: 600; font-size: 11px; }
    .severity-critical { background: #d32f2f !important; color: white !important; }
    .severity-high     { background: #f57c00 !important; color: white !important; }
    .severity-medium   { background: #fbc02d !important; color: #333 !important; }
    .severity-low      { background: #388e3c !important; color: white !important; }
  `],
})
export class SeverityBadgeComponent {
  @Input() severity: string = 'LOW';
}
