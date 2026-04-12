import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/auth/auth.service';
import { SeverityBadgeComponent } from '../../shared/components/severity-badge/severity-badge.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { Violation } from '../../core/models/user.model';

@Component({
  selector: 'app-violations',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatTableModule, MatSelectModule, MatButtonModule,
    MatIconModule, MatFormFieldModule, MatPaginatorModule,
    SeverityBadgeComponent,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <h2>Violations</h2>
        <p class="subtitle">SOD violations detected across all users</p>
      </div>

      <!-- Filters -->
      <mat-card class="filter-card">
        <mat-card-content>
          <mat-form-field appearance="outline">
            <mat-label>Severity</mat-label>
            <mat-select [(ngModel)]="filterSeverity" (ngModelChange)="loadViolations()">
              <mat-option value="">All</mat-option>
              <mat-option value="CRITICAL">Critical</mat-option>
              <mat-option value="HIGH">High</mat-option>
              <mat-option value="MEDIUM">Medium</mat-option>
              <mat-option value="LOW">Low</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Status</mat-label>
            <mat-select [(ngModel)]="filterStatus" (ngModelChange)="loadViolations()">
              <mat-option value="">All</mat-option>
              <mat-option value="OPEN">Open</mat-option>
              <mat-option value="IN_REVIEW">In Review</mat-option>
              <mat-option value="RESOLVED">Resolved</mat-option>
            </mat-select>
          </mat-form-field>
        </mat-card-content>
      </mat-card>

      <!-- Table -->
      <mat-card>
        <mat-card-content>
          <table mat-table [dataSource]="violations()" class="full-width">
            <ng-container matColumnDef="user">
              <th mat-header-cell *matHeaderCellDef>User</th>
              <td mat-cell *matCellDef="let v">
                <div>{{ v.user_name }}</div>
                <div class="sub-text">{{ v.user_email }}</div>
              </td>
            </ng-container>
            <ng-container matColumnDef="rule">
              <th mat-header-cell *matHeaderCellDef>Rule</th>
              <td mat-cell *matCellDef="let v">{{ v.rule_name }}</td>
            </ng-container>
            <ng-container matColumnDef="severity">
              <th mat-header-cell *matHeaderCellDef>Severity</th>
              <td mat-cell *matCellDef="let v">
                <app-severity-badge [severity]="v.severity"></app-severity-badge>
              </td>
            </ng-container>
            <ng-container matColumnDef="risk">
              <th mat-header-cell *matHeaderCellDef>Risk Score</th>
              <td mat-cell *matCellDef="let v">{{ v.risk_score | number:'1.0-1' }}</td>
            </ng-container>
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let v">{{ v.status }}</td>
            </ng-container>
            <ng-container matColumnDef="detected">
              <th mat-header-cell *matHeaderCellDef>Detected</th>
              <td mat-cell *matCellDef="let v">{{ v.detected_at | date:'medium' }}</td>
            </ng-container>
            <ng-container matColumnDef="actions" *ngIf="auth.hasLevel(4)">
              <th mat-header-cell *matHeaderCellDef>Actions</th>
              <td mat-cell *matCellDef="let v">
                <button mat-icon-button (click)="updateStatus(v, 'IN_REVIEW')" title="Mark In Review">
                  <mat-icon>rate_review</mat-icon>
                </button>
                <button mat-icon-button color="primary" (click)="updateStatus(v, 'RESOLVED')" title="Resolve">
                  <mat-icon>check_circle</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns"></tr>
          </table>
          <p *ngIf="violations().length === 0" class="empty-state">No violations found.</p>
        </mat-card-content>
        <mat-paginator
          [length]="total()"
          [pageSize]="25"
          [pageSizeOptions]="[10, 25, 50, 100]"
          (page)="onPage($event)"
        ></mat-paginator>
      </mat-card>
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 1200px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .filter-card { margin-bottom: 16px; }
    .filter-card mat-card-content { display: flex; gap: 16px; flex-wrap: wrap; padding-bottom: 0; }
    .full-width { width: 100%; }
    .sub-text { font-size: 11px; color: #888; }
    .empty-state { text-align: center; color: #999; padding: 32px; }
  `],
})
export class ViolationsComponent implements OnInit {
  violations = signal<Violation[]>([]);
  total = signal(0);
  filterSeverity = '';
  filterStatus = '';
  pageSize = 25;
  pageIndex = 0;

  get displayedColumns(): string[] {
    const base = ['user', 'rule', 'severity', 'risk', 'status', 'detected'];
    return this.auth.hasLevel(4) ? [...base, 'actions'] : base;
  }

  constructor(private api: ApiService, public auth: AuthService, private dialog: MatDialog) {}

  ngOnInit(): void { this.loadViolations(); }

  loadViolations(): void {
    this.api.getViolations({
      severity: this.filterSeverity || undefined,
      status_filter: this.filterStatus || undefined,
      limit: this.pageSize,
      offset: this.pageIndex * this.pageSize,
    }).subscribe((res) => {
      this.violations.set(res.violations);
      this.total.set(res.total);
    });
  }

  onPage(e: PageEvent): void {
    this.pageSize = e.pageSize;
    this.pageIndex = e.pageIndex;
    this.loadViolations();
  }

  updateStatus(v: Violation, newStatus: string): void {
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: `Mark as ${newStatus}`,
        message: `Mark violation for "${v.user_name}" (${v.rule_name}) as ${newStatus}?`,
        confirmLabel: 'Yes',
      },
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) return;
      this.api.updateViolationStatus(v.id, newStatus).subscribe(() => this.loadViolations());
    });
  }
}
