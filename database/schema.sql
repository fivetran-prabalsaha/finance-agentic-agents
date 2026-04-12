-- NetSuite SOD Compliance Database Schema
-- PostgreSQL 16+ with pgvector extension

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users from NetSuite
CREATE TABLE users (
    user_id VARCHAR(50) PRIMARY KEY,
    internal_id INTEGER UNIQUE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    employee_id VARCHAR(50),
    department VARCHAR(255),
    subsidiary VARCHAR(100),
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_subsidiary ON users(subsidiary);

-- Roles from NetSuite
CREATE TABLE roles (
    role_id VARCHAR(50) PRIMARY KEY,
    internal_id INTEGER UNIQUE,
    role_name VARCHAR(255) NOT NULL,
    description TEXT,
    permissions TEXT[] DEFAULT '{}',
    sensitivity_level VARCHAR(20) DEFAULT 'LOW', -- LOW, MEDIUM, HIGH, CRITICAL
    is_custom BOOLEAN DEFAULT false,
    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(384),  -- For semantic search of similar roles
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_roles_sensitivity ON roles(sensitivity_level);
CREATE INDEX idx_roles_embedding ON roles USING ivfflat (embedding vector_cosine_ops);

-- User-Role assignments
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(user_id) ON DELETE CASCADE,
    role_id VARCHAR(50) REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, role_id)
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_active ON user_roles(is_active);

-- ============================================================================
-- SOD RULES & COMPLIANCE
-- ============================================================================

-- SOD Rules with vector embeddings for semantic search
CREATE TABLE sod_rules (
    rule_id VARCHAR(50) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    rule_type VARCHAR(50), -- FINANCIAL, IT_ACCESS, PROCUREMENT, CUSTOM
    conflicting_permissions JSONB NOT NULL, -- e.g., [["Create Bill", "Approve Bill"], [...]]
    severity VARCHAR(20) DEFAULT 'MEDIUM', -- CRITICAL, HIGH, MEDIUM, LOW
    regulatory_framework VARCHAR(50), -- SOX, GDPR, INTERNAL, etc.
    remediation_guidance TEXT,
    is_active BOOLEAN DEFAULT true,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    embedding vector(384),  -- Semantic search for rule matching
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_sod_rules_type ON sod_rules(rule_type);
CREATE INDEX idx_sod_rules_severity ON sod_rules(severity);
CREATE INDEX idx_sod_rules_active ON sod_rules(is_active);
CREATE INDEX idx_sod_rules_embedding ON sod_rules USING ivfflat (embedding vector_cosine_ops);

-- Violations detected by the system
CREATE TABLE violations (
    violation_id VARCHAR(50) PRIMARY KEY,
    scan_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) REFERENCES users(user_id),
    sod_rule_id VARCHAR(50) REFERENCES sod_rules(rule_id),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    conflicting_roles VARCHAR(100)[] NOT NULL,
    conflicting_permissions TEXT[] NOT NULL,
    risk_score INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
    severity VARCHAR(20) NOT NULL, -- CRITICAL, HIGH, MEDIUM, LOW
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, ACKNOWLEDGED, REMEDIATED, FALSE_POSITIVE, ACCEPTED_RISK
    business_justification TEXT,
    remediation_plan TEXT,
    assigned_to VARCHAR(255),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    embedding vector(384),  -- For finding similar past violations
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_violations_user ON violations(user_id);
CREATE INDEX idx_violations_rule ON violations(sod_rule_id);
CREATE INDEX idx_violations_status ON violations(status);
CREATE INDEX idx_violations_severity ON violations(severity);
CREATE INDEX idx_violations_detected ON violations(detected_at DESC);
CREATE INDEX idx_violations_embedding ON violations USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- AGENT LOGS & AUDIT TRAIL
-- ============================================================================

-- Compliance scan execution history
CREATE TABLE compliance_scans (
    scan_id VARCHAR(50) PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED
    scan_type VARCHAR(50) DEFAULT 'SCHEDULED', -- SCHEDULED, MANUAL, TRIGGERED
    users_scanned INTEGER DEFAULT 0,
    violations_found INTEGER DEFAULT 0,
    critical_violations INTEGER DEFAULT 0,
    high_violations INTEGER DEFAULT 0,
    medium_violations INTEGER DEFAULT 0,
    low_violations INTEGER DEFAULT 0,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_scans_started ON compliance_scans(started_at DESC);
CREATE INDEX idx_scans_status ON compliance_scans(status);

-- Agent execution logs for debugging and monitoring
CREATE TABLE agent_logs (
    log_id SERIAL PRIMARY KEY,
    agent_name VARCHAR(50) NOT NULL,
    execution_id UUID DEFAULT uuid_generate_v4(),
    scan_id VARCHAR(50) REFERENCES compliance_scans(scan_id),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'RUNNING', -- RUNNING, COMPLETED, FAILED
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    duration_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 4)
);

CREATE INDEX idx_agent_logs_agent ON agent_logs(agent_name);
CREATE INDEX idx_agent_logs_scan ON agent_logs(scan_id);
CREATE INDEX idx_agent_logs_started ON agent_logs(started_at DESC);

-- Audit trail for all significant actions
CREATE TABLE audit_trail (
    audit_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action VARCHAR(100) NOT NULL, -- USER_CREATED, RULE_UPDATED, VIOLATION_REMEDIATED, etc.
    entity_type VARCHAR(50) NOT NULL, -- USER, ROLE, VIOLATION, RULE, etc.
    entity_id VARCHAR(50) NOT NULL,
    performed_by VARCHAR(255),
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_trail_timestamp ON audit_trail(timestamp DESC);
CREATE INDEX idx_audit_trail_entity ON audit_trail(entity_type, entity_id);
CREATE INDEX idx_audit_trail_performed_by ON audit_trail(performed_by);

-- ============================================================================
-- NOTIFICATION TRACKING
-- ============================================================================

-- Notification history
CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY,
    violation_id VARCHAR(50) REFERENCES violations(violation_id),
    scan_id VARCHAR(50) REFERENCES compliance_scans(scan_id),
    notification_type VARCHAR(50) NOT NULL, -- EMAIL, SLACK, WEBHOOK
    channel VARCHAR(255), -- email address, slack channel, etc.
    subject VARCHAR(500),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'SENT', -- SENT, FAILED, PENDING
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_notifications_violation ON notifications(violation_id);
CREATE INDEX idx_notifications_sent ON notifications(sent_at DESC);
CREATE INDEX idx_notifications_status ON notifications(status);

-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: Current violations summary
CREATE VIEW current_violations_summary AS
SELECT
    v.severity,
    COUNT(*) as violation_count,
    COUNT(DISTINCT v.user_id) as affected_users,
    AVG(v.risk_score) as avg_risk_score
FROM violations v
WHERE v.status = 'OPEN'
GROUP BY v.severity;

-- View: User risk profile
CREATE VIEW user_risk_profile AS
SELECT
    u.user_id,
    u.name,
    u.email,
    COUNT(v.violation_id) as total_violations,
    COUNT(CASE WHEN v.status = 'OPEN' THEN 1 END) as open_violations,
    MAX(v.risk_score) as max_risk_score,
    ARRAY_AGG(DISTINCT r.role_name) as assigned_roles
FROM users u
LEFT JOIN violations v ON u.user_id = v.user_id
LEFT JOIN user_roles ur ON u.user_id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.role_id
WHERE u.status = 'ACTIVE' AND ur.is_active = true
GROUP BY u.user_id, u.name, u.email;

-- View: SOD rule effectiveness
CREATE VIEW sod_rule_effectiveness AS
SELECT
    sr.rule_id,
    sr.rule_name,
    sr.severity,
    COUNT(v.violation_id) as violations_detected,
    COUNT(CASE WHEN v.status = 'REMEDIATED' THEN 1 END) as violations_remediated,
    COUNT(CASE WHEN v.status = 'FALSE_POSITIVE' THEN 1 END) as false_positives,
    ROUND(
        COUNT(CASE WHEN v.status = 'FALSE_POSITIVE' THEN 1 END)::numeric /
        NULLIF(COUNT(v.violation_id), 0) * 100,
        2
    ) as false_positive_rate
FROM sod_rules sr
LEFT JOIN violations v ON sr.rule_id = v.sod_rule_id
WHERE sr.is_active = true
GROUP BY sr.rule_id, sr.rule_name, sr.severity;

-- ============================================================================
-- INITIAL DATA / SEED
-- ============================================================================

-- Insert a sample SOD rule
INSERT INTO sod_rules (rule_id, rule_name, description, rule_type, conflicting_permissions, severity, regulatory_framework)
VALUES (
    'SOD-FIN-001',
    'AP Entry vs. Approval Separation',
    'Users should not be able to both create and approve vendor bills to prevent fraud',
    'FINANCIAL',
    '{"conflicts": [["Create Bill", "Approve Bill"], ["Enter Vendor Payment", "Approve Vendor Payment"]]}',
    'CRITICAL',
    'SOX'
);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for sod_rules
CREATE TRIGGER update_sod_rules_updated_at
    BEFORE UPDATE ON sod_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to log audit trail automatically
CREATE OR REPLACE FUNCTION log_audit_trail()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_trail (action, entity_type, entity_id, performed_by, new_value)
        VALUES (
            TG_TABLE_NAME || '_CREATED',
            TG_TABLE_NAME,
            NEW.violation_id,
            current_user,
            row_to_json(NEW)
        );
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_trail (action, entity_type, entity_id, performed_by, old_value, new_value)
        VALUES (
            TG_TABLE_NAME || '_UPDATED',
            TG_TABLE_NAME,
            NEW.violation_id,
            current_user,
            row_to_json(OLD),
            row_to_json(NEW)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for violations audit
CREATE TRIGGER violations_audit_trigger
    AFTER INSERT OR UPDATE ON violations
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_trail();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'NetSuite users synchronized via RESTlet/SuiteTalk';
COMMENT ON TABLE roles IS 'NetSuite roles with permissions and vector embeddings for semantic search';
COMMENT ON TABLE sod_rules IS 'Segregation of Duties rules with vector embeddings for intelligent matching';
COMMENT ON TABLE violations IS 'Detected SOD violations with risk scoring and remediation tracking';
COMMENT ON TABLE agent_logs IS 'Execution logs for all LangChain agents in the compliance workflow';
COMMENT ON TABLE audit_trail IS 'Immutable audit log for compliance and regulatory requirements';

-- ============================================================================
-- GRANTS (adjust based on your user setup)
-- ============================================================================

-- Grant permissions to application user
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO compliance_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO compliance_user;
