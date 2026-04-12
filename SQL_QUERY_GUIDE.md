# PostgreSQL Query Guide - SOD Compliance System

**Database:** compliance_db
**Connection:** `psql "postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db"`
**Last Updated:** 2026-02-16

---

## Table of Contents

1. [Schema Inspection](#schema-inspection)
2. [User & Role Queries](#user--role-queries)
3. [SOD Violation Queries](#sod-violation-queries)
4. [Exception Management](#exception-management)
5. [Sync Status & Monitoring](#sync-status--monitoring)
6. [Analytics & Reporting](#analytics--reporting)
7. [Knowledge Base Queries](#knowledge-base-queries)
8. [Performance Queries](#performance-queries)

---

## Schema Inspection

### List All Tables
```sql
-- Get all tables in the database
SELECT
    schemaname,
    tablename,
    tableowner
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

### Table Row Counts
```sql
-- Get row counts for all tables
SELECT
    schemaname,
    relname AS table_name,
    n_live_tup AS row_count
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;
```

### Table Schemas
```sql
-- Detailed schema for a specific table
SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

### Indexes
```sql
-- List all indexes
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

---

## User & Role Queries

### All Active Users
```sql
-- Get all active users with their roles
SELECT
    u.name,
    u.email,
    u.title,
    u.department,
    u.status,
    array_agg(r.role_name) AS roles,
    COUNT(DISTINCT ur.role_id) AS role_count
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE u.status = 'ACTIVE'
GROUP BY u.id, u.name, u.email, u.title, u.department, u.status
ORDER BY u.name;
```

### Users by Department
```sql
-- Get users grouped by department
SELECT
    department,
    COUNT(*) AS user_count,
    COUNT(*) FILTER (WHERE status = 'ACTIVE') AS active_users,
    COUNT(*) FILTER (WHERE status = 'INACTIVE') AS inactive_users
FROM users
GROUP BY department
ORDER BY user_count DESC;
```

### Find User by Email
```sql
-- Find specific user with all details
SELECT
    u.id,
    u.name,
    u.email,
    u.title,
    u.department,
    u.status,
    u.last_login,
    array_agg(DISTINCT r.role_name) AS roles,
    COUNT(DISTINCT v.id) AS violation_count
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
LEFT JOIN violations v ON u.id = v.user_id AND v.status = 'OPEN'
WHERE u.email = 'austin.rangel@fivetran.com'
GROUP BY u.id;
```

### Users with Multiple Roles
```sql
-- Find users with more than N roles
SELECT
    u.name,
    u.email,
    u.department,
    array_agg(r.role_name) AS roles,
    COUNT(r.id) AS role_count
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.status = 'ACTIVE'
GROUP BY u.id, u.name, u.email, u.department
HAVING COUNT(r.id) >= 2
ORDER BY role_count DESC, u.name;
```

### Users with Specific Role
```sql
-- Find all users with a specific role
SELECT
    u.name,
    u.email,
    u.title,
    u.department,
    array_agg(DISTINCT r2.role_name) AS all_roles
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
LEFT JOIN user_roles ur2 ON u.id = ur2.user_id
LEFT JOIN roles r2 ON ur2.role_id = r2.id
WHERE r.role_name = 'Fivetran - Controller'
  AND u.status = 'ACTIVE'
GROUP BY u.id, u.name, u.email, u.title, u.department
ORDER BY u.name;
```

### Users by Role Combination
```sql
-- Find users with specific role combinations
WITH user_role_combos AS (
    SELECT
        u.id,
        u.name,
        u.email,
        array_agg(r.role_name ORDER BY r.role_name) AS roles
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE u.status = 'ACTIVE'
    GROUP BY u.id, u.name, u.email
)
SELECT *
FROM user_role_combos
WHERE 'Fivetran - Controller' = ANY(roles)
  AND 'Fivetran - Billing Manager' = ANY(roles);
```

---

## SOD Violation Queries

### All Open Violations
```sql
-- Get all open SOD violations with details
SELECT
    v.id,
    u.name AS user_name,
    u.email,
    u.department,
    sr.rule_name,
    sr.category,
    v.severity,
    v.risk_score,
    v.title,
    v.detected_at,
    v.conflicting_roles
FROM violations v
JOIN users u ON v.user_id = u.id
JOIN sod_rules sr ON v.rule_id = sr.id
WHERE v.status = 'OPEN'
ORDER BY v.risk_score DESC, v.detected_at DESC;
```

### Violations by Severity
```sql
-- Count violations by severity
SELECT
    severity,
    COUNT(*) AS violation_count,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    COUNT(DISTINCT user_id) AS affected_users
FROM violations
WHERE status = 'OPEN'
GROUP BY severity
ORDER BY
    CASE severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
    END;
```

### Top Violators
```sql
-- Users with most violations
SELECT
    u.name,
    u.email,
    u.department,
    u.title,
    COUNT(v.id) AS total_violations,
    COUNT(v.id) FILTER (WHERE v.severity = 'CRITICAL') AS critical_violations,
    COUNT(v.id) FILTER (WHERE v.severity = 'HIGH') AS high_violations,
    ROUND(AVG(v.risk_score), 2) AS avg_risk_score,
    array_agg(DISTINCT r.role_name) AS roles
FROM users u
JOIN violations v ON u.id = v.user_id
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE v.status = 'OPEN'
GROUP BY u.id, u.name, u.email, u.department, u.title
ORDER BY total_violations DESC
LIMIT 20;
```

### Violations by SOD Rule
```sql
-- Count violations by SOD rule
SELECT
    sr.rule_code,
    sr.rule_name,
    sr.category,
    sr.severity,
    COUNT(v.id) AS violation_count,
    COUNT(DISTINCT v.user_id) AS affected_users
FROM sod_rules sr
LEFT JOIN violations v ON sr.id = v.rule_id AND v.status = 'OPEN'
WHERE sr.is_active = true
GROUP BY sr.id, sr.rule_code, sr.rule_name, sr.category, sr.severity
ORDER BY violation_count DESC;
```

### Violations for Specific User
```sql
-- Get all violations for a specific user
SELECT
    v.id,
    sr.rule_name,
    sr.category,
    v.severity,
    v.risk_score,
    v.title,
    v.description,
    v.conflicting_roles,
    v.conflicting_permissions,
    v.detected_at
FROM violations v
JOIN sod_rules sr ON v.rule_id = sr.id
JOIN users u ON v.user_id = u.id
WHERE u.email = 'austin.rangel@fivetran.com'
  AND v.status = 'OPEN'
ORDER BY v.risk_score DESC;
```

### Recent Violations (Last 7 Days)
```sql
-- Violations detected in the last week
SELECT
    DATE(v.detected_at) AS detection_date,
    COUNT(*) AS violations_detected,
    COUNT(DISTINCT v.user_id) AS unique_users,
    array_agg(DISTINCT v.severity) AS severity_levels
FROM violations v
WHERE v.detected_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(v.detected_at)
ORDER BY detection_date DESC;
```

---

## Exception Management

### All Active Exceptions
```sql
-- Get all approved exceptions
SELECT
    ae.exception_code,
    u.name AS user_name,
    u.email,
    u.title,
    ae.role_names,
    ae.conflict_count,
    ae.risk_score,
    ae.status,
    ae.approved_by,
    ae.approval_date,
    ae.review_date,
    ae.compensating_controls
FROM approved_exceptions ae
JOIN users u ON ae.user_id = u.id
WHERE ae.status = 'ACTIVE'
ORDER BY ae.risk_score DESC;
```

### Exceptions Pending Review
```sql
-- Exceptions that need review soon (within 30 days)
SELECT
    ae.exception_code,
    u.name AS user_name,
    u.email,
    ae.review_date,
    (ae.review_date - CURRENT_DATE) AS days_until_review,
    ae.risk_score,
    ae.role_names,
    ae.compensating_controls
FROM approved_exceptions ae
JOIN users u ON ae.user_id = u.id
WHERE ae.status = 'ACTIVE'
  AND ae.review_date <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY ae.review_date ASC;
```

### Exception History
```sql
-- Full exception history for a user
SELECT
    ae.exception_code,
    ae.status,
    ae.approval_date,
    ae.review_date,
    ae.revoked_date,
    ae.revoked_by,
    ae.revocation_reason,
    ae.risk_score,
    ae.role_names
FROM approved_exceptions ae
JOIN users u ON ae.user_id = u.id
WHERE u.email = 'austin.rangel@fivetran.com'
ORDER BY ae.approval_date DESC;
```

### Exceptions by Risk Level
```sql
-- Group exceptions by risk level
SELECT
    CASE
        WHEN risk_score < 45 THEN 'LOW'
        WHEN risk_score < 65 THEN 'MEDIUM'
        WHEN risk_score < 85 THEN 'HIGH'
        ELSE 'CRITICAL'
    END AS risk_level,
    COUNT(*) AS exception_count,
    array_agg(u.name) AS users
FROM approved_exceptions ae
JOIN users u ON ae.user_id = u.id
WHERE ae.status = 'ACTIVE'
GROUP BY risk_level
ORDER BY
    CASE risk_level
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
    END;
```

---

## Sync Status & Monitoring

### Latest Sync Status
```sql
-- Get the most recent sync for each system
SELECT
    sm.system_name,
    sm.sync_type,
    sm.status,
    sm.started_at,
    sm.completed_at,
    (sm.completed_at - sm.started_at) AS duration,
    sm.users_synced,
    sm.roles_synced,
    sm.error_message
FROM sync_metadata sm
WHERE sm.id IN (
    SELECT MAX(id)
    FROM sync_metadata
    GROUP BY system_name
)
ORDER BY sm.completed_at DESC;
```

### Sync History (Last 24 Hours)
```sql
-- All syncs in the last 24 hours
SELECT
    system_name,
    sync_type,
    status,
    started_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - started_at)) AS duration_seconds,
    users_synced,
    roles_synced
FROM sync_metadata
WHERE started_at >= NOW() - INTERVAL '24 hours'
ORDER BY started_at DESC;
```

### Sync Success Rate
```sql
-- Calculate sync success rate over time
SELECT
    DATE(started_at) AS sync_date,
    system_name,
    COUNT(*) AS total_syncs,
    COUNT(*) FILTER (WHERE status = 'SUCCESS') AS successful_syncs,
    COUNT(*) FILTER (WHERE status = 'FAILED') AS failed_syncs,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE status = 'SUCCESS') / COUNT(*),
        2
    ) AS success_rate
FROM sync_metadata
WHERE started_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(started_at), system_name
ORDER BY sync_date DESC, system_name;
```

### Failed Syncs
```sql
-- Get all failed syncs with error messages
SELECT
    id,
    system_name,
    sync_type,
    started_at,
    error_message,
    users_synced,
    roles_synced
FROM sync_metadata
WHERE status = 'FAILED'
ORDER BY started_at DESC
LIMIT 20;
```

---

## Analytics & Reporting

### Compliance Dashboard Summary
```sql
-- High-level compliance metrics
SELECT
    (SELECT COUNT(*) FROM users WHERE status = 'ACTIVE') AS active_users,
    (SELECT COUNT(*) FROM roles) AS total_roles,
    (SELECT COUNT(*) FROM violations WHERE status = 'OPEN') AS open_violations,
    (SELECT COUNT(*) FROM approved_exceptions WHERE status = 'ACTIVE') AS active_exceptions,
    (SELECT COUNT(DISTINCT user_id) FROM violations WHERE status = 'OPEN') AS users_with_violations,
    (SELECT ROUND(AVG(risk_score), 2) FROM violations WHERE status = 'OPEN') AS avg_violation_risk,
    (SELECT COUNT(*) FROM sod_rules WHERE is_active = true) AS active_sod_rules;
```

### Violations Trend (Last 30 Days)
```sql
-- Daily violation trend
SELECT
    DATE(detected_at) AS date,
    COUNT(*) AS new_violations,
    COUNT(*) FILTER (WHERE severity = 'CRITICAL') AS critical,
    COUNT(*) FILTER (WHERE severity = 'HIGH') AS high,
    COUNT(*) FILTER (WHERE severity = 'MEDIUM') AS medium
FROM violations
WHERE detected_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(detected_at)
ORDER BY date DESC;
```

### Department Risk Analysis
```sql
-- Risk analysis by department
SELECT
    u.department,
    COUNT(DISTINCT u.id) AS total_users,
    COUNT(DISTINCT CASE WHEN v.id IS NOT NULL THEN u.id END) AS users_with_violations,
    COUNT(v.id) AS total_violations,
    ROUND(AVG(v.risk_score), 2) AS avg_risk_score,
    COUNT(v.id) FILTER (WHERE v.severity = 'CRITICAL') AS critical_violations
FROM users u
LEFT JOIN violations v ON u.id = v.user_id AND v.status = 'OPEN'
WHERE u.status = 'ACTIVE'
GROUP BY u.department
ORDER BY total_violations DESC;
```

### Role Popularity
```sql
-- Most commonly assigned roles
SELECT
    r.role_name,
    COUNT(DISTINCT ur.user_id) AS user_count,
    COUNT(DISTINCT v.id) AS violation_count,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN v.id IS NOT NULL THEN ur.user_id END)
        / NULLIF(COUNT(DISTINCT ur.user_id), 0),
        2
    ) AS violation_rate
FROM roles r
LEFT JOIN user_roles ur ON r.id = ur.role_id
LEFT JOIN users u ON ur.user_id = u.id AND u.status = 'ACTIVE'
LEFT JOIN violations v ON u.id = v.user_id AND v.status = 'OPEN'
GROUP BY r.id, r.role_name
ORDER BY user_count DESC
LIMIT 20;
```

### Risk Heat Map (Department × Severity)
```sql
-- Create a risk heat map
SELECT
    u.department,
    COUNT(*) FILTER (WHERE v.severity = 'CRITICAL') AS critical,
    COUNT(*) FILTER (WHERE v.severity = 'HIGH') AS high,
    COUNT(*) FILTER (WHERE v.severity = 'MEDIUM') AS medium,
    COUNT(*) FILTER (WHERE v.severity = 'LOW') AS low,
    COUNT(*) AS total_violations,
    ROUND(AVG(v.risk_score), 2) AS avg_risk
FROM violations v
JOIN users u ON v.user_id = u.id
WHERE v.status = 'OPEN'
GROUP BY u.department
ORDER BY total_violations DESC;
```

---

## Knowledge Base Queries

### Search Knowledge Base (Vector Similarity)
```sql
-- Find similar documents using pgvector
-- Note: Requires embedding vector as input
SELECT
    kb.id,
    kb.title,
    kb.content_type,
    kb.source,
    kb.created_at,
    -- Similarity score (1 - cosine distance)
    1 - (kb.embedding <=> '[your_query_vector]'::vector) AS similarity
FROM knowledge_base kb
WHERE content_type = 'sod_rule'
ORDER BY kb.embedding <=> '[your_query_vector]'::vector
LIMIT 10;
```

### Knowledge Base Statistics
```sql
-- Get knowledge base content breakdown
SELECT
    content_type,
    COUNT(*) AS document_count,
    COUNT(DISTINCT source) AS unique_sources,
    AVG(char_length(content)) AS avg_content_length
FROM knowledge_base
GROUP BY content_type
ORDER BY document_count DESC;
```

### Recently Added Knowledge
```sql
-- Recently added knowledge base entries
SELECT
    id,
    title,
    content_type,
    source,
    created_at,
    LEFT(content, 200) AS content_preview
FROM knowledge_base
ORDER BY created_at DESC
LIMIT 20;
```

---

## Performance Queries

### Largest Tables
```sql
-- Find largest tables by size
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Slow Queries (if pg_stat_statements enabled)
```sql
-- Top 10 slowest queries
SELECT
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_time_ms,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms,
    ROUND((100 * total_exec_time / SUM(total_exec_time) OVER())::numeric, 2) AS percentage
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

### Index Usage
```sql
-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### Database Size
```sql
-- Overall database size
SELECT
    pg_size_pretty(pg_database_size('compliance_db')) AS database_size;
```

---

## Useful Utility Queries

### Active Connections
```sql
-- See active database connections
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query,
    query_start
FROM pg_stat_activity
WHERE datname = 'compliance_db'
ORDER BY query_start DESC;
```

### Current Database Info
```sql
-- Database configuration
SELECT
    name,
    setting,
    unit,
    short_desc
FROM pg_settings
WHERE name IN (
    'max_connections',
    'shared_buffers',
    'work_mem',
    'maintenance_work_mem',
    'effective_cache_size'
);
```

### Table Bloat Check
```sql
-- Estimate table bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    n_dead_tup AS dead_tuples,
    n_live_tup AS live_tuples,
    ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_percentage
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND n_live_tup > 0
ORDER BY n_dead_tup DESC;
```

---

## Quick Reference Commands

### Connect to Database
```bash
psql "postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db"
```

### Export Query Results to CSV
```bash
psql "postgresql://..." -c "COPY (SELECT * FROM users) TO STDOUT CSV HEADER" > users.csv
```

### Run Query from File
```bash
psql "postgresql://..." -f query.sql
```

### Get Table Info
```sql
\d+ users        -- Describe users table with details
\dt              -- List all tables
\di              -- List all indexes
\df              -- List all functions
```

---

## Example Investigations

### Investigation 1: Why does Austin have 249 conflicts with Controller?
```sql
-- Step 1: Get Austin's current roles
SELECT u.name, array_agg(r.role_name) AS roles
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.email = 'austin.rangel@fivetran.com'
GROUP BY u.name;
-- Result: Billing Manager, Revenue Manager

-- Step 2: Check what violations would exist with Controller added
-- (This would require running the SOD analysis, but you can check similar users)
SELECT u.name, u.email, array_agg(r.role_name) AS roles, COUNT(v.id) AS violations
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
LEFT JOIN violations v ON u.id = v.user_id AND v.status = 'OPEN'
WHERE 'Fivetran - Controller' = ANY(array_agg(r.role_name))
  AND 'Fivetran - Billing Manager' = ANY(array_agg(r.role_name))
GROUP BY u.id, u.name, u.email;
```

### Investigation 2: Find all users like Abbey Skuse (Controller + AP Manager)
```sql
-- Find users with Controller + AP Manager combination
WITH user_roles_array AS (
    SELECT
        u.id,
        u.name,
        u.email,
        u.department,
        array_agg(r.role_name) AS roles
    FROM users u
    JOIN user_roles ur ON u.id = ur.user_id
    JOIN roles r ON ur.role_id = r.id
    WHERE u.status = 'ACTIVE'
    GROUP BY u.id, u.name, u.email, u.department
)
SELECT *
FROM user_roles_array
WHERE 'Fivetran - Controller' = ANY(roles)
  AND ('Fivetran - AP Manager' = ANY(roles)
       OR 'Fivetran - Billing Manager' = ANY(roles));
```

---

**Created:** 2026-02-16
**For:** SOD Compliance System Database Analysis
**Database:** PostgreSQL 14+ with pgvector extension
