import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTabsModule } from '@angular/material/tabs';
import { ApiService } from '../../core/services/api.service';
import { ApprovedExceptionSummary } from '../../core/models/user.model';

@Component({
  selector: 'app-exceptions',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatCardModule, MatTableModule, MatSelectModule, MatButtonModule,
    MatIconModule, MatFormFieldModule, MatChipsModule, MatBadgeModule, MatTabsModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <h2>Approved Exceptions</h2>
        <p class="subtitle">SOD exceptions with active compensating controls</p>
      </div>

      <!-- Stats cards -->
      <div class="stats-row" *ngIf="stats()">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value">{{ stats().total_exceptions }}</div>
            <div class="stat-label">Total Exceptions</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-value">{{ '$' + ((stats().total_annual_cost / 1000) | number:'1.0-0') + 'K' }}</div>
            <div class="stat-label">Annual Control Cost</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="stat-card warn" *ngIf="dueCount() > 0">
          <mat-card-content>
            <div class="stat-value">{{ dueCount() }}</div>
            <div class="stat-label">Due for Review</div>
          </mat-card-content>
        </mat-card>
      </div>

      <mat-tab-group>
        <!-- All Exceptions Tab -->
        <mat-tab label="All Exceptions">
          <div class="tab-content">
            <mat-form-field appearance="outline">
              <mat-label>Status</mat-label>
              <mat-select [(ngModel)]="filterStatus" (ngModelChange)="loadExceptions()">
                <mat-option value="">All</mat-option>
                <mat-option value="ACTIVE">Active</mat-option>
                <mat-option value="VIOLATED">Violated</mat-option>
                <mat-option value="EXPIRED">Expired</mat-option>
                <mat-option value="REVOKED">Revoked</mat-option>
              </mat-select>
            </mat-form-field>

            <table mat-table [dataSource]="exceptions()" class="full-width">
              <ng-container matColumnDef="code">
                <th mat-header-cell *matHeaderCellDef>Code</th>
                <td mat-cell *matCellDef="let e">
                  <strong>{{ e.exception_code }}</strong>
                </td>
              </ng-container>
              <ng-container matColumnDef="user">
                <th mat-header-cell *matHeaderCellDef>User</th>
                <td mat-cell *matCellDef="let e">
                  <div>{{ e.user_name }}</div>
                  <div class="sub-text">{{ e.job_title }}</div>
                </td>
              </ng-container>
              <ng-container matColumnDef="roles">
                <th mat-header-cell *matHeaderCellDef>Roles</th>
                <td mat-cell *matCellDef="let e">
                  <span *ngFor="let r of e.role_names" class="role-chip">{{ r }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="risk">
                <th mat-header-cell *matHeaderCellDef>Risk</th>
                <td mat-cell *matCellDef="let e">{{ e.risk_score | number:'1.0-1' }}</td>
              </ng-container>
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef>Status</th>
                <td mat-cell *matCellDef="let e">
                  <span [class]="'status-chip status-' + e.status.toLowerCase()">{{ e.status }}</span>
                </td>
              </ng-container>
              <ng-container matColumnDef="review">
                <th mat-header-cell *matHeaderCellDef>Next Review</th>
                <td mat-cell *matCellDef="let e">{{ e.next_review_date | date:'mediumDate' }}</td>
              </ng-container>
              <ng-container matColumnDef="expires">
                <th mat-header-cell *matHeaderCellDef>Expires</th>
                <td mat-cell *matCellDef="let e">{{ e.expires_at | date:'mediumDate' }}</td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="['code','user','roles','risk','status','review','expires']"></tr>
              <tr mat-row *matRowDef="let row; columns: ['code','user','roles','risk','status','review','expires']"></tr>
            </table>
            <p *ngIf="exceptions().length === 0" class="empty-state">No exceptions found.</p>
          </div>
        </mat-tab>

        <!-- Due for Review Tab -->
        <mat-tab>
          <ng-template mat-tab-label>
            Due for Review
            <span class="badge" *ngIf="dueCount() > 0">&nbsp;{{ dueCount() }}</span>
          </ng-template>
          <div class="tab-content">
            <table mat-table [dataSource]="dueExceptions()" class="full-width">
              <ng-container matColumnDef="code">
                <th mat-header-cell *matHeaderCellDef>Code</th>
                <td mat-cell *matCellDef="let e"><strong>{{ e.exception_code }}</strong></td>
              </ng-container>
              <ng-container matColumnDef="user">
                <th mat-header-cell *matHeaderCellDef>User</th>
                <td mat-cell *matCellDef="let e">{{ e.user_name }}</td>
              </ng-container>
              <ng-container matColumnDef="roles">
                <th mat-header-cell *matHeaderCellDef>Roles</th>
                <td mat-cell *matCellDef="let e">{{ e.role_names?.join(', ') }}</td>
              </ng-container>
              <ng-container matColumnDef="overdue">
                <th mat-header-cell *matHeaderCellDef>Review Due</th>
                <td mat-cell *matCellDef="let e">
                  <span class="overdue">{{ e.next_review_date | date:'mediumDate' }}</span>
                </td>
              </ng-container>
              <tr mat-header-row *matHeaderRowDef="['code','user','roles','overdue']"></tr>
              <tr mat-row *matRowDef="let row; columns: ['code','user','roles','overdue']"></tr>
            </table>
            <p *ngIf="dueExceptions().length === 0" class="empty-state">No exceptions due for review. ✅</p>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 1200px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .stats-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
    .stat-card { flex: 1 1 180px; }
    .stat-card mat-card-content { text-align: center; padding: 20px; }
    .stat-value { font-size: 32px; font-weight: 700; }
    .stat-label { color: #666; font-size: 13px; }
    .stat-card.warn .stat-value { color: #f57c00; }
    .tab-content { padding: 16px 0; }
    .full-width { width: 100%; }
    .sub-text { font-size: 11px; color: #888; }
    .role-chip { background: #e3f2fd; color: #1565c0; border-radius: 12px; padding: 2px 8px; font-size: 11px; margin: 2px; display: inline-block; }
    .status-chip { border-radius: 12px; padding: 2px 10px; font-size: 12px; font-weight: 600; }
    .status-active { background: #e8f5e9; color: #2e7d32; }
    .status-violated { background: #ffebee; color: #c62828; }
    .status-expired, .status-revoked { background: #eeeeee; color: #616161; }
    .overdue { color: #d32f2f; font-weight: 600; }
    .badge { background: #f44336; color: white; border-radius: 10px; padding: 0 6px; font-size: 11px; margin-left: 4px; }
    .empty-state { text-align: center; color: #999; padding: 32px; }
  `],
})
export class ExceptionsComponent implements OnInit {
  exceptions = signal<ApprovedExceptionSummary[]>([]);
  dueExceptions = signal<any[]>([]);
  stats = signal<any>({});
  dueCount = signal(0);
  filterStatus = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.loadExceptions();
    this.loadDueReview();
  }

  loadExceptions(): void {
    this.api.getExceptions({ status_filter: this.filterStatus || undefined }).subscribe((res) => {
      this.exceptions.set(res.exceptions);
      this.stats.set(res.stats);
    });
  }

  loadDueReview(): void {
    this.api.getExceptionsDueReview().subscribe((res) => {
      this.dueCount.set(res.total_due);
      this.dueExceptions.set(res.exceptions);
    });
  }
}
