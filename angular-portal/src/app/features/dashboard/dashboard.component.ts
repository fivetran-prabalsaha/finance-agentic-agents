import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/auth/auth.service';
import { StatusIndicatorComponent } from '../../shared/components/status-indicator/status-indicator.component';
import { SeverityBadgeComponent } from '../../shared/components/severity-badge/severity-badge.component';
import { SystemHealth, Violation, ApprovedExceptionSummary } from '../../core/models/user.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule, RouterModule,
    MatCardModule, MatIconModule, MatButtonModule, MatProgressBarModule,
    MatChipsModule, MatTableModule,
    StatusIndicatorComponent, SeverityBadgeComponent,
  ],
  template: `
    <div class="dashboard">

      <!-- Header -->
      <div class="page-header">
        <h2>Dashboard</h2>
        <p class="subtitle">SOD Compliance System — System Overview</p>
      </div>

      <!-- System Health -->
      <h3 class="section-title">System Health</h3>
      <div class="health-grid" *ngIf="health()">
        <mat-card *ngFor="let entry of healthEntries()" class="health-card">
          <mat-card-content>
            <app-status-indicator
              [status]="entry.status"
              [label]="entry.name"
            ></app-status-indicator>
            <p class="health-detail" *ngIf="entry.detail">{{ entry.detail }}</p>
          </mat-card-content>
        </mat-card>
      </div>
      <mat-progress-bar mode="indeterminate" *ngIf="loadingHealth()"></mat-progress-bar>

      <!-- Metrics Row -->
      <h3 class="section-title">Violations Summary</h3>
      <div class="metrics-grid">
        <mat-card class="metric-card critical">
          <mat-card-content>
            <mat-icon>error</mat-icon>
            <div class="metric-value">{{ violationCounts().critical }}</div>
            <div class="metric-label">Critical</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="metric-card high">
          <mat-card-content>
            <mat-icon>warning</mat-icon>
            <div class="metric-value">{{ violationCounts().high }}</div>
            <div class="metric-label">High</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="metric-card medium">
          <mat-card-content>
            <mat-icon>info</mat-icon>
            <div class="metric-value">{{ violationCounts().medium }}</div>
            <div class="metric-label">Medium</div>
          </mat-card-content>
        </mat-card>
        <mat-card class="metric-card low">
          <mat-card-content>
            <mat-icon>check_circle</mat-icon>
            <div class="metric-value">{{ violationCounts().low }}</div>
            <div class="metric-label">Low</div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Exceptions due for review alert -->
      <mat-card class="alert-card" *ngIf="dueReview() > 0">
        <mat-card-content>
          <mat-icon color="warn">notifications_active</mat-icon>
          <strong>{{ dueReview() }} exception(s) due for review.</strong>
          <a routerLink="/exceptions" mat-button color="warn">View &rarr;</a>
        </mat-card-content>
      </mat-card>

      <!-- Recent Violations -->
      <h3 class="section-title">Recent Violations</h3>
      <mat-card>
        <mat-card-content>
          <table mat-table [dataSource]="recentViolations()" class="full-width">
            <ng-container matColumnDef="user">
              <th mat-header-cell *matHeaderCellDef>User</th>
              <td mat-cell *matCellDef="let v">{{ v.user_name }}</td>
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
              <th mat-header-cell *matHeaderCellDef>Risk</th>
              <td mat-cell *matCellDef="let v">{{ v.risk_score | number:'1.0-1' }}</td>
            </ng-container>
            <ng-container matColumnDef="detected">
              <th mat-header-cell *matHeaderCellDef>Detected</th>
              <td mat-cell *matCellDef="let v">{{ v.detected_at | date:'short' }}</td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="['user','rule','severity','risk','detected']"></tr>
            <tr mat-row *matRowDef="let row; columns: ['user','rule','severity','risk','detected']"></tr>
          </table>
          <p *ngIf="recentViolations().length === 0" class="empty-state">No violations found.</p>
        </mat-card-content>
        <mat-card-actions>
          <a routerLink="/violations" mat-button color="primary">View All Violations</a>
        </mat-card-actions>
      </mat-card>

    </div>
  `,
  styles: [`
    .dashboard { padding: 24px; max-width: 1200px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .section-title { margin: 24px 0 12px; font-size: 16px; font-weight: 600; color: #444; }

    .health-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 8px; }
    .health-card { flex: 1 1 160px; }
    .health-detail { font-size: 11px; color: #888; margin: 4px 0 0; }

    .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
    .metric-card mat-card-content {
      display: flex; flex-direction: column; align-items: center;
      padding: 20px 16px;
    }
    .metric-card mat-icon { font-size: 32px; width: 32px; height: 32px; }
    .metric-value { font-size: 36px; font-weight: 700; margin: 8px 0 4px; }
    .metric-label { font-size: 13px; color: #555; }
    .metric-card.critical mat-icon, .metric-card.critical .metric-value { color: #d32f2f; }
    .metric-card.high mat-icon, .metric-card.high .metric-value { color: #f57c00; }
    .metric-card.medium mat-icon, .metric-card.medium .metric-value { color: #f9a825; }
    .metric-card.low mat-icon, .metric-card.low .metric-value { color: #388e3c; }

    .alert-card mat-card-content {
      display: flex; align-items: center; gap: 12px;
      background: #fff3e0; padding: 12px 16px;
    }
    .alert-card { margin: 0 0 24px; border-left: 4px solid #f57c00; }

    .full-width { width: 100%; }
    .empty-state { color: #999; text-align: center; padding: 24px; }
  `],
})
export class DashboardComponent implements OnInit {
  health = signal<SystemHealth | null>(null);
  loadingHealth = signal(true);
  recentViolations = signal<Violation[]>([]);
  dueReview = signal(0);
  violationCounts = signal({ critical: 0, high: 0, medium: 0, low: 0 });

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.loadHealth();
    this.loadViolations();
    this.loadDueReview();
  }

  healthEntries(): Array<{ name: string; status: string; detail?: string }> {
    const h = this.health();
    if (!h) return [];
    return Object.entries(h.integrations).map(([name, info]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1).replace('_', ' '),
      status: info.status,
      detail: info.detail ?? info.domain ?? info.channel,
    }));
  }

  private loadHealth(): void {
    this.api.getSystemHealth().subscribe({
      next: (h) => { this.health.set(h); this.loadingHealth.set(false); },
      error: () => this.loadingHealth.set(false),
    });
  }

  private loadViolations(): void {
    this.api.getViolations({ limit: 10 }).subscribe({
      next: (res) => {
        this.recentViolations.set(res.violations);
        const counts = { critical: 0, high: 0, medium: 0, low: 0 };
        for (const v of res.violations) {
          const s = v.severity.toLowerCase() as keyof typeof counts;
          if (s in counts) counts[s]++;
        }
        this.violationCounts.set(counts);
      },
    });
  }

  private loadDueReview(): void {
    this.api.getExceptionsDueReview().subscribe({
      next: (res) => this.dueReview.set(res.total_due),
    });
  }
}
