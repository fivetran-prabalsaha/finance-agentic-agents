export interface User {
  email: string;
  name: string;
  level: number;        // 3=Director, 4=Controller/VP, 5=CFO
  level_label: string;
  roles: string[];
  job_title?: string;
  department?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SystemHealth {
  timestamp: string;
  mcp_server: string;
  integrations: Record<string, IntegrationHealth>;
}

export interface IntegrationHealth {
  status: 'healthy' | 'configured' | 'not_configured' | 'error';
  detail?: string;
  port?: number;
  account_id?: string;
  domain?: string;
  channel?: string;
}

export interface Config {
  llm: LlmConfig;
  thresholds: ThresholdConfig;
  scheduling: SchedulingConfig;
  notifications: NotificationConfig;
  integrations: IntegrationConfig;
  mcp_server: McpConfig;
  feature_flags: FeatureFlagsConfig;
}

export interface LlmConfig {
  fast_model: string;
  reasoning_model: string;
  anthropic_api_key_last4: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  max_retries: number;
  embedding_provider: string;
  pgvector_dimension: number;
}

export interface ThresholdConfig {
  critical: number;
  high: number;
  medium: number;
}

export interface SchedulingConfig {
  scan_interval_hours: number;
  scan_timezone: string;
  full_sync_cron: string;
  incremental_sync_hours: number;
  redis_cache_ttl_seconds: number;
  mcp_cache_ttl_seconds: number;
}

export interface NotificationConfig {
  notify_critical_immediately: boolean;
  notify_high_daily: boolean;
  notify_medium_weekly: boolean;
  notify_low_weekly: boolean;
  slack_channel: string;
  slack_webhook_masked: string;
  sendgrid_from_email: string;
}

export interface IntegrationConfig {
  netsuite: Record<string, any>;
  okta: Record<string, any>;
  slack: Record<string, any>;
}

export interface McpConfig {
  host: string;
  port: number;
  protocol_version: string;
}

export interface FeatureFlagsConfig {
  enable_vector_search: boolean;
  enable_historical_analysis: boolean;
  enable_ml_scoring: boolean;
  use_mcp_cache: boolean;
  use_conv_summaries: boolean;
  debug: boolean;
}

export interface Violation {
  id: string;
  user_name: string;
  user_email: string;
  rule_name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  risk_score: number;
  status: string;
  detected_at: string;
}

export interface SodRule {
  id: string;
  rule_code: string;
  rule_name: string;
  description: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  is_active: boolean;
  conflicting_permissions: any;
}

export interface ApprovedExceptionSummary {
  exception_id: string;
  exception_code: string;
  user_name: string;
  user_email: string;
  job_title?: string;
  role_names: string[];
  conflict_count: number;
  risk_score: number;
  status: string;
  approved_by: string;
  approved_date: string;
  review_frequency?: string;
  next_review_date?: string;
  expires_at?: string;
}

export interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  entity_type: string;
  entity_id: string;
  action: string;
  changes: Record<string, any>;
}
