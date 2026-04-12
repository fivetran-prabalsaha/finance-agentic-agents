import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/auth/auth.service';
import { SeverityBadgeComponent } from '../../shared/components/severity-badge/severity-badge.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { SodRule } from '../../core/models/user.model';

@Component({
  selector: 'app-sod-rules',
  standalone: true,
  imports: [
    CommonModule, ReactiveFormsModule,
    MatCardModule, MatTableModule, MatButtonModule, MatIconModule,
    MatFormFieldModule, MatInputModule, MatSelectModule, MatSlideToggleModule,
    MatExpansionModule, SeverityBadgeComponent,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <h2>SOD Rules</h2>
        <p class="subtitle">{{ rules().length }} active segregation-of-duties rules</p>
      </div>

      <mat-accordion>
        <mat-expansion-panel *ngFor="let rule of rules()">
          <mat-expansion-panel-header>
            <mat-panel-title>
              <strong>{{ rule.rule_code }}</strong>&nbsp;&mdash;&nbsp;{{ rule.rule_name }}
            </mat-panel-title>
            <mat-panel-description>
              <app-severity-badge [severity]="rule.severity"></app-severity-badge>
              &nbsp;
              <span [class]="rule.is_active ? 'active-chip' : 'inactive-chip'">
                {{ rule.is_active ? 'Active' : 'Inactive' }}
              </span>
            </mat-panel-description>
          </mat-expansion-panel-header>

          <!-- Read-only content -->
          <div class="rule-detail">
            <p><strong>Category:</strong> {{ rule.category }}</p>
            <p><strong>Description:</strong> {{ rule.description }}</p>
            <p><strong>Conflicting Permissions:</strong>
              <code>{{ rule.conflicting_permissions | json }}</code>
            </p>

            <!-- Edit form — L4+ only -->
            <div class="edit-section" *ngIf="auth.hasLevel(4)">
              <mat-form-field appearance="outline">
                <mat-label>Severity</mat-label>
                <mat-select [value]="rule.severity" #severitySelect>
                  <mat-option value="CRITICAL">Critical</mat-option>
                  <mat-option value="HIGH">High</mat-option>
                  <mat-option value="MEDIUM">Medium</mat-option>
                  <mat-option value="LOW">Low</mat-option>
                </mat-select>
              </mat-form-field>

              <mat-slide-toggle
                [checked]="rule.is_active"
                #activeToggle
                color="primary"
              >Active</mat-slide-toggle>

              <button
                mat-flat-button
                color="primary"
                (click)="saveRule(rule, severitySelect.value, activeToggle.checked)"
              >Save Changes</button>
            </div>
          </div>
        </mat-expansion-panel>
      </mat-accordion>

      <p *ngIf="rules().length === 0" class="empty-state">Loading SOD rules...</p>
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 1000px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .rule-detail { padding: 8px 0 16px; }
    .rule-detail p { margin: 8px 0; }
    code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
    .edit-section { display: flex; align-items: center; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
    .active-chip { background: #e8f5e9; color: #2e7d32; border-radius: 12px; padding: 2px 10px; font-size: 12px; }
    .inactive-chip { background: #eeeeee; color: #616161; border-radius: 12px; padding: 2px 10px; font-size: 12px; }
    .empty-state { text-align: center; color: #999; padding: 32px; }
  `],
})
export class SodRulesComponent implements OnInit {
  rules = signal<SodRule[]>([]);

  constructor(private api: ApiService, public auth: AuthService, private dialog: MatDialog, private snack: MatSnackBar) {}

  ngOnInit(): void {
    this.api.getSodRules().subscribe((res) => this.rules.set(res.rules));
  }

  saveRule(rule: SodRule, severity: string, isActive: boolean): void {
    const changes: string[] = [];
    if (severity !== rule.severity) changes.push(`severity ${rule.severity} → ${severity}`);
    if (isActive !== rule.is_active) changes.push(`active: ${rule.is_active} → ${isActive}`);
    if (changes.length === 0) return;

    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: 'Update SOD Rule',
        message: `Update rule ${rule.rule_code}: ${changes.join(', ')}?`,
        confirmLabel: 'Update',
      },
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) return;
      this.api.updateSodRule(rule.id, { severity: severity as SodRule['severity'], is_active: isActive }).subscribe({
        next: () => {
          this.snack.open('Rule updated', 'Dismiss', { duration: 3000 });
          this.api.getSodRules().subscribe((res) => this.rules.set(res.rules));
        },
        error: (e) => this.snack.open(`Error: ${e.error?.detail}`, 'Dismiss', { duration: 5000 }),
      });
    });
  }
}
