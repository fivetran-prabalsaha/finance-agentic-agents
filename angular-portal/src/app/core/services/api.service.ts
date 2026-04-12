import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Config, SystemHealth, Violation, SodRule,
  ApprovedExceptionSummary, AuditEntry, ThresholdConfig,
  FeatureFlagsConfig, LlmConfig, NotificationConfig, SchedulingConfig,
} from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ---- System ----

  getSystemHealth(): Observable<SystemHealth> {
    return this.http.get<SystemHealth>(`${this.base}/admin/system-health`);
  }

  // ---- Config ----

  getConfig(): Observable<Config> {
    return this.http.get<Config>(`${this.base}/admin/config`);
  }

  updateThresholds(data: Partial<ThresholdConfig>): Observable<any> {
    return this.http.patch(`${this.base}/admin/config/thresholds`, data);
  }

  updateNotifications(data: Partial<NotificationConfig>): Observable<any> {
    return this.http.patch(`${this.base}/admin/config/notifications`, data);
  }

  updateScheduling(data: Partial<SchedulingConfig>): Observable<any> {
    return this.http.patch(`${this.base}/admin/config/scheduling`, data);
  }

  updateFeatureFlags(data: Partial<FeatureFlagsConfig>): Observable<any> {
    return this.http.patch(`${this.base}/admin/config/feature-flags`, data);
  }

  updateLlmConfig(data: Partial<LlmConfig>): Observable<any> {
    return this.http.patch(`${this.base}/admin/config/llm`, data);
  }

  testConnection(integration: string): Observable<any> {
    return this.http.post(`${this.base}/admin/config/test-connection`, { integration });
  }

  // ---- SOD Rules ----

  getSodRules(): Observable<{ total: number; rules: SodRule[] }> {
    return this.http.get<{ total: number; rules: SodRule[] }>(`${this.base}/admin/sod-rules`);
  }

  updateSodRule(id: string, data: Partial<SodRule>): Observable<any> {
    return this.http.patch(`${this.base}/admin/sod-rules/${id}`, data);
  }

  // ---- Violations ----

  getViolations(params: {
    severity?: string;
    status_filter?: string;
    department?: string;
    limit?: number;
    offset?: number;
  } = {}): Observable<{ total: number; violations: Violation[] }> {
    let httpParams = new HttpParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) httpParams = httpParams.set(k, String(v));
    }
    return this.http.get<{ total: number; violations: Violation[] }>(
      `${this.base}/admin/violations`,
      { params: httpParams },
    );
  }

  updateViolationStatus(id: string, newStatus: string, notes?: string): Observable<any> {
    return this.http.patch(`${this.base}/admin/violations/${id}/status`, { new_status: newStatus, notes });
  }

  // ---- Exceptions ----

  getExceptions(params: { status_filter?: string; limit?: number; offset?: number } = {}): Observable<{
    total: number;
    stats: any;
    exceptions: ApprovedExceptionSummary[];
  }> {
    let httpParams = new HttpParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) httpParams = httpParams.set(k, String(v));
    }
    return this.http.get<any>(`${this.base}/admin/exceptions`, { params: httpParams });
  }

  getExceptionsDueReview(): Observable<{ total_due: number; exceptions: any[] }> {
    return this.http.get<any>(`${this.base}/admin/exceptions/due-review`);
  }

  // ---- Audit Trail ----

  getAuditTrail(limit = 100, offset = 0): Observable<{ total: number; entries: AuditEntry[] }> {
    return this.http.get<any>(`${this.base}/admin/audit-trail`, {
      params: new HttpParams().set('limit', limit).set('offset', offset),
    });
  }

  // ---- Token Analytics ----

  getTokenAnalytics(days = 30): Observable<any> {
    return this.http.get(`${this.base}/admin/token-analytics`, {
      params: new HttpParams().set('days', days),
    });
  }
}
