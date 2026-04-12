import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSliderModule } from '@angular/material/slider';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { ApiService } from '../../../core/services/api.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-thresholds',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule,
    MatCardModule, MatFormFieldModule, MatInputModule, MatSliderModule,
    MatButtonModule, MatIconModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <h2>Risk Thresholds</h2>
        <p class="subtitle">Configure risk score cutoffs for violation severity levels</p>
      </div>

      <mat-card *ngIf="form">
        <mat-card-content [formGroup]="form">
          <div class="threshold-row">
            <div class="threshold-label critical">
              <mat-icon>error</mat-icon> CRITICAL
            </div>
            <mat-form-field appearance="outline">
              <mat-label>Score ≥</mat-label>
              <input matInput type="number" formControlName="critical" min="0" max="100" />
            </mat-form-field>
            <span class="hint">Require immediate remediation</span>
          </div>
          <div class="threshold-row">
            <div class="threshold-label high">
              <mat-icon>warning</mat-icon> HIGH
            </div>
            <mat-form-field appearance="outline">
              <mat-label>Score ≥</mat-label>
              <input matInput type="number" formControlName="high" min="0" max="100" />
            </mat-form-field>
            <span class="hint">Remediate within 30 days</span>
          </div>
          <div class="threshold-row">
            <div class="threshold-label medium">
              <mat-icon>info</mat-icon> MEDIUM
            </div>
            <mat-form-field appearance="outline">
              <mat-label>Score ≥</mat-label>
              <input matInput type="number" formControlName="medium" min="0" max="100" />
            </mat-form-field>
            <span class="hint">Remediate within 90 days</span>
          </div>
          <div class="threshold-row">
            <div class="threshold-label low">
              <mat-icon>check_circle</mat-icon> LOW
            </div>
            <span class="hint-only">Score &lt; MEDIUM — document compensating controls</span>
          </div>
        </mat-card-content>
        <mat-card-actions>
          <button mat-flat-button color="primary" (click)="save()" [disabled]="form.invalid">
            Save Thresholds
          </button>
          <p class="save-note">⚠️ Changes applied in-memory. Restart MCP server to persist.</p>
        </mat-card-actions>
      </mat-card>
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 700px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .threshold-row { display: flex; align-items: center; gap: 20px; margin-bottom: 16px; }
    .threshold-label { display: flex; align-items: center; gap: 8px; width: 130px; font-weight: 700; }
    .threshold-label.critical { color: #d32f2f; }
    .threshold-label.high { color: #f57c00; }
    .threshold-label.medium { color: #f9a825; }
    .threshold-label.low { color: #388e3c; }
    mat-form-field { width: 120px; }
    .hint { color: #888; font-size: 12px; }
    .hint-only { color: #888; font-size: 12px; margin-left: 0; }
    .save-note { color: #f57c00; font-size: 12px; margin: 4px 0 0; }
  `],
})
export class ThresholdsComponent implements OnInit {
  form = this.fb.group({
    critical: [90, [Validators.required, Validators.min(0), Validators.max(100)]],
    high: [70, [Validators.required, Validators.min(0), Validators.max(100)]],
    medium: [40, [Validators.required, Validators.min(0), Validators.max(100)]],
  });

  constructor(private fb: FormBuilder, private api: ApiService, private snack: MatSnackBar, private dialog: MatDialog) {}

  ngOnInit(): void {
    this.api.getConfig().subscribe((cfg) => {
      this.form.patchValue(cfg.thresholds);
    });
  }

  save(): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Update Thresholds',
        message: `Set CRITICAL ≥ ${this.form.value.critical}, HIGH ≥ ${this.form.value.high}, MEDIUM ≥ ${this.form.value.medium}?`,
        confirmLabel: 'Save',
      },
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) return;
      this.api.updateThresholds(this.form.value as any).subscribe({
        next: () => this.snack.open('Thresholds updated', 'Dismiss', { duration: 3000 }),
        error: (e) => this.snack.open(`Error: ${e.error?.detail}`, 'Dismiss', { duration: 5000 }),
      });
    });
  }
}
