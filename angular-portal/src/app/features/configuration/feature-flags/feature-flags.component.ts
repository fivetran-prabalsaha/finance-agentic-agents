import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { ApiService } from '../../../core/services/api.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { FeatureFlagsConfig } from '../../../core/models/user.model';

interface FlagDef {
  key: keyof FeatureFlagsConfig;
  label: string;
  description: string;
  production_safe: boolean;
}

const FLAG_DEFS: FlagDef[] = [
  { key: 'use_mcp_cache', label: 'MCP Tool Cache (Redis)', description: 'Cache MCP tool calls within TTL window to reduce latency', production_safe: true },
  { key: 'use_conv_summaries', label: 'Conversation Summaries', description: 'Store Haiku-generated DM summaries in Postgres for cross-session context', production_safe: true },
  { key: 'enable_vector_search', label: 'Vector Search (pgvector)', description: 'Enable semantic search on compliance knowledge base', production_safe: true },
  { key: 'enable_historical_analysis', label: 'Historical Analysis', description: 'Include historical violation trends in risk assessments', production_safe: true },
  { key: 'enable_ml_scoring', label: 'ML Risk Scoring', description: 'Use ML model for risk scoring (experimental)', production_safe: false },
  { key: 'debug', label: 'Debug Mode', description: 'Enable verbose logging (dev/staging only)', production_safe: false },
];

@Component({
  selector: 'app-feature-flags',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatSlideToggleModule, MatButtonModule, MatIconModule],
  template: `
    <div class="page">
      <div class="page-header">
        <h2>Feature Flags</h2>
        <p class="subtitle">Toggle system features — requires CFO-level access (L5)</p>
      </div>

      <mat-card *ngIf="flags()">
        <mat-card-content>
          <div class="flag-row" *ngFor="let def of flagDefs">
            <div class="flag-info">
              <div class="flag-label">
                {{ def.label }}
                <span class="prod-warn" *ngIf="!def.production_safe">⚠️ Production impact</span>
              </div>
              <div class="flag-desc">{{ def.description }}</div>
            </div>
            <mat-slide-toggle
              [checked]="!!flags()[def.key]"
              (change)="toggle(def, $event.checked)"
              color="primary"
            ></mat-slide-toggle>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 800px; }
    .page-header h2 { margin: 0; font-size: 24px; font-weight: 700; }
    .subtitle { color: #666; margin: 4px 0 24px; }
    .flag-row { display: flex; align-items: center; justify-content: space-between; padding: 16px 0; border-bottom: 1px solid #eee; }
    .flag-info { flex: 1; }
    .flag-label { font-weight: 600; font-size: 15px; }
    .flag-desc { color: #666; font-size: 13px; margin-top: 4px; }
    .prod-warn { color: #f57c00; font-size: 12px; margin-left: 8px; font-weight: 400; }
  `],
})
export class FeatureFlagsComponent implements OnInit {
  flags = signal<Partial<FeatureFlagsConfig>>({});
  flagDefs = FLAG_DEFS;

  constructor(private api: ApiService, private snack: MatSnackBar, private dialog: MatDialog) {}

  ngOnInit(): void {
    this.api.getConfig().subscribe((cfg) => this.flags.set(cfg.feature_flags));
  }

  toggle(def: FlagDef, newValue: boolean): void {
    const warn = !def.production_safe
      ? '\n\n⚠️ This flag affects production behavior.'
      : '';
    const ref = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: `${newValue ? 'Enable' : 'Disable'} ${def.label}`,
        message: `${newValue ? 'Enable' : 'Disable'} "${def.label}"?${warn}`,
        confirmLabel: newValue ? 'Enable' : 'Disable',
      },
    });
    ref.afterClosed().subscribe((ok) => {
      if (!ok) {
        // revert toggle
        this.flags.update((f) => ({ ...f }));
        return;
      }
      const update: Partial<FeatureFlagsConfig> = { [def.key]: newValue } as any;
      this.api.updateFeatureFlags(update).subscribe({
        next: () => {
          this.flags.update((f) => ({ ...f, [def.key]: newValue }));
          this.snack.open(`${def.label} ${newValue ? 'enabled' : 'disabled'}`, 'Dismiss', { duration: 3000 });
        },
        error: (e) => this.snack.open(`Error: ${e.error?.detail}`, 'Dismiss', { duration: 5000 }),
      });
    });
  }
}
