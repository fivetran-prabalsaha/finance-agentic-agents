-- Migration: Add exception management tables
-- Date: 2026-02-13
-- Purpose: Store approved SOD exceptions with compensating controls, track effectiveness, and enable precedent-based recommendations
-- Related: EXCEPTION_CONTROLS_PLAN.md, Phase 1 implementation

-- =============================================================================
-- 1. CREATE ENUMS
-- =============================================================================

-- Exception status enum
CREATE TYPE exception_status AS ENUM (
    'ACTIVE',           -- Exception is currently active
    'VIOLATED',         -- Controls failed, violation occurred
    'REMEDIATED',       -- Access removed, exception closed
    'EXPIRED',          -- Time-based expiration reached
    'REVOKED'           -- Manually revoked by compliance
);

-- Implementation status enum for controls
CREATE TYPE implementation_status AS ENUM (
    'PLANNED',          -- Control planned but not started
    'IN_PROGRESS',      -- Implementation underway
    'IMPLEMENTED',      -- Technical implementation complete
    'ACTIVE',           -- Control active and operational
    'FAILED',           -- Implementation failed
    'DEACTIVATED'       -- Control turned off
);

-- Remediation status enum
CREATE TYPE remediation_status AS ENUM (
    'OPEN',             -- Newly detected, needs action
    'IN_PROGRESS',      -- Remediation work ongoing
    'RESOLVED',         -- Successfully remediated
    'ACCEPTED_RISK'     -- Risk accepted, no remediation
);

-- Review outcome enum
CREATE TYPE review_outcome AS ENUM (
    'APPROVED_CONTINUE',    -- Continue with current controls
    'APPROVED_MODIFY',      -- Continue with modified controls
    'REVOKED',              -- Revoke exception, remove access
    'ESCALATED'             -- Escalate to higher authority
);

-- =============================================================================
-- 2. CREATE COMPENSATING_CONTROLS TABLE (if not exists)
-- =============================================================================

CREATE TABLE IF NOT EXISTS compensating_controls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    control_type VARCHAR(100),  -- e.g., "Preventive", "Detective", "Corrective"

    -- Effectiveness Metrics
    risk_reduction_percentage INTEGER CHECK (risk_reduction_percentage >= 0 AND risk_reduction_percentage <= 100),
    implementation_time_hours INTEGER,
    annual_cost_estimate DECIMAL(10, 2),

    -- Applicability
    severity_levels TEXT[],  -- Which severity levels this applies to

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for compensating_controls
CREATE INDEX IF NOT EXISTS idx_compensating_controls_control_id ON compensating_controls(control_id);
CREATE INDEX IF NOT EXISTS idx_compensating_controls_active ON compensating_controls(is_active);
CREATE INDEX IF NOT EXISTS idx_compensating_controls_type ON compensating_controls(control_type);

-- Comments for compensating_controls
COMMENT ON TABLE compensating_controls IS 'Library of compensating controls that can be applied to mitigate SOD risks';
COMMENT ON COLUMN compensating_controls.control_id IS 'Unique identifier for the control (e.g., CC-001)';
COMMENT ON COLUMN compensating_controls.risk_reduction_percentage IS 'Estimated risk reduction percentage when this control is applied';
COMMENT ON COLUMN compensating_controls.annual_cost_estimate IS 'Estimated annual cost to maintain this control';
COMMENT ON COLUMN compensating_controls.severity_levels IS 'Array of severity levels this control is appropriate for (CRITICAL, HIGH, MEDIUM, LOW)';

-- =============================================================================
-- 3. CREATE APPROVED_EXCEPTIONS TABLE
-- =============================================================================

CREATE TABLE approved_exceptions (
    -- Identity
    exception_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exception_code VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "EXC-2026-001"

    -- User/Request Info
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_name VARCHAR(255) NOT NULL,
    user_email VARCHAR(255),
    job_title VARCHAR(255),
    department VARCHAR(255),

    -- Role Combination (stored as arrays for easy matching)
    role_ids INTEGER[] NOT NULL,
    role_names TEXT[] NOT NULL,

    -- Violation Details
    conflict_count INTEGER NOT NULL,
    critical_conflicts INTEGER DEFAULT 0,
    high_conflicts INTEGER DEFAULT 0,
    medium_conflicts INTEGER DEFAULT 0,
    low_conflicts INTEGER DEFAULT 0,
    risk_score DECIMAL(5, 2) CHECK (risk_score >= 0 AND risk_score <= 100),

    -- Business Context
    business_justification TEXT NOT NULL,
    request_reason TEXT,
    ticket_reference VARCHAR(100),

    -- Approval Info
    approved_by VARCHAR(255) NOT NULL,
    approved_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approval_authority VARCHAR(100),  -- e.g., "CFO", "Audit Committee"

    -- Review Schedule
    review_frequency VARCHAR(50),  -- e.g., "Monthly", "Quarterly", "Annual"
    next_review_date DATE,
    last_review_date DATE,

    -- Status
    status exception_status NOT NULL DEFAULT 'ACTIVE',
    status_reason TEXT,
    status_updated_date TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- Optional: auto-expire after N months

    -- Audit trail
    audit_trail JSONB DEFAULT '[]'::jsonb
);

-- Indexes for approved_exceptions
CREATE INDEX idx_approved_exceptions_user ON approved_exceptions(user_id);
CREATE INDEX idx_approved_exceptions_code ON approved_exceptions(exception_code);
CREATE INDEX idx_approved_exceptions_status ON approved_exceptions(status);
CREATE INDEX idx_approved_exceptions_date ON approved_exceptions(approved_date DESC);
CREATE INDEX idx_approved_exceptions_next_review ON approved_exceptions(next_review_date) WHERE status = 'ACTIVE';
CREATE INDEX idx_approved_exceptions_role_ids ON approved_exceptions USING GIN(role_ids);
CREATE INDEX idx_approved_exceptions_role_names ON approved_exceptions USING GIN(role_names);

-- Full-text search index for searching by user name, roles, justification
CREATE INDEX idx_approved_exceptions_search ON approved_exceptions USING GIN(
    to_tsvector('english',
        COALESCE(user_name, '') || ' ' ||
        COALESCE(array_to_string(role_names, ' '), '') || ' ' ||
        COALESCE(business_justification, '')
    )
);

-- Comments for approved_exceptions
COMMENT ON TABLE approved_exceptions IS 'Master table for approved SOD exceptions with compensating controls';
COMMENT ON COLUMN approved_exceptions.exception_id IS 'Unique UUID for the exception';
COMMENT ON COLUMN approved_exceptions.exception_code IS 'Human-readable exception code (e.g., EXC-2026-001)';
COMMENT ON COLUMN approved_exceptions.role_ids IS 'Array of NetSuite role internal IDs that were granted';
COMMENT ON COLUMN approved_exceptions.role_names IS 'Array of NetSuite role names for easy searching';
COMMENT ON COLUMN approved_exceptions.business_justification IS 'Business reason for approving this exception';
COMMENT ON COLUMN approved_exceptions.audit_trail IS 'JSONB array of all status changes and significant events';

-- =============================================================================
-- 4. CREATE EXCEPTION_CONTROLS TABLE
-- =============================================================================

CREATE TABLE exception_controls (
    exception_control_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id) ON DELETE CASCADE,
    control_id UUID NOT NULL REFERENCES compensating_controls(id),

    -- Implementation Details
    implementation_date DATE,
    implementation_status implementation_status DEFAULT 'PLANNED',

    -- Cost Tracking (actual vs estimated)
    estimated_annual_cost DECIMAL(10, 2),
    actual_annual_cost DECIMAL(10, 2),
    implementation_cost DECIMAL(10, 2),

    -- Effectiveness Tracking
    risk_reduction_percentage INTEGER,  -- From control definition
    effectiveness_score DECIMAL(5, 2) CHECK (effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100)),
    violations_prevented INTEGER DEFAULT 0,
    violations_occurred INTEGER DEFAULT 0,

    -- Notes
    implementation_notes TEXT,
    effectiveness_notes TEXT,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique control per exception
    UNIQUE(exception_id, control_id)
);

-- Indexes for exception_controls
CREATE INDEX idx_exception_controls_exception ON exception_controls(exception_id);
CREATE INDEX idx_exception_controls_control ON exception_controls(control_id);
CREATE INDEX idx_exception_controls_status ON exception_controls(implementation_status);

-- Comments for exception_controls
COMMENT ON TABLE exception_controls IS 'Many-to-many relationship between exceptions and compensating controls';
COMMENT ON COLUMN exception_controls.effectiveness_score IS 'Actual effectiveness 0-100 based on violations prevented vs occurred';
COMMENT ON COLUMN exception_controls.violations_prevented IS 'Estimated number of violations this control prevented';
COMMENT ON COLUMN exception_controls.violations_occurred IS 'Number of violations that occurred despite this control';

-- =============================================================================
-- 5. CREATE EXCEPTION_VIOLATIONS TABLE
-- =============================================================================

CREATE TABLE exception_violations (
    violation_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id),

    -- Violation Details
    violation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    violation_type VARCHAR(100),  -- What rule was violated
    severity VARCHAR(20),  -- CRITICAL, HIGH, MEDIUM, LOW

    -- Description
    description TEXT NOT NULL,
    root_cause TEXT,

    -- Which control failed?
    failed_control_id UUID REFERENCES compensating_controls(id),
    failure_reason TEXT,

    -- Detection
    detected_by VARCHAR(255),  -- System or person who detected
    detection_method VARCHAR(100),  -- e.g., "Audit", "Automated monitoring"

    -- Remediation
    remediation_action TEXT,
    remediation_status remediation_status DEFAULT 'OPEN',
    remediated_date TIMESTAMP,
    remediated_by VARCHAR(255),

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for exception_violations
CREATE INDEX idx_exception_violations_exception ON exception_violations(exception_id);
CREATE INDEX idx_exception_violations_date ON exception_violations(violation_date DESC);
CREATE INDEX idx_exception_violations_status ON exception_violations(remediation_status);
CREATE INDEX idx_exception_violations_severity ON exception_violations(severity);

-- Comments for exception_violations
COMMENT ON TABLE exception_violations IS 'Tracks when approved exceptions are violated (control failures)';
COMMENT ON COLUMN exception_violations.failed_control_id IS 'Which compensating control failed to prevent this violation';
COMMENT ON COLUMN exception_violations.detection_method IS 'How was this violation discovered (audit, monitoring, etc.)';

-- =============================================================================
-- 6. CREATE EXCEPTION_REVIEWS TABLE
-- =============================================================================

CREATE TABLE exception_reviews (
    review_id SERIAL PRIMARY KEY,
    exception_id UUID NOT NULL REFERENCES approved_exceptions(exception_id),

    -- Review Details
    review_date DATE NOT NULL,
    reviewer_name VARCHAR(255) NOT NULL,
    review_type VARCHAR(50),  -- e.g., "Scheduled", "Ad-hoc", "Audit-triggered"

    -- Review Outcome
    outcome review_outcome NOT NULL,

    -- Findings
    controls_effective BOOLEAN,
    violations_found BOOLEAN,
    findings TEXT,
    recommendations TEXT,

    -- Next Review
    next_review_date DATE,

    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for exception_reviews
CREATE INDEX idx_exception_reviews_exception ON exception_reviews(exception_id);
CREATE INDEX idx_exception_reviews_date ON exception_reviews(review_date DESC);
CREATE INDEX idx_exception_reviews_outcome ON exception_reviews(outcome);

-- Comments for exception_reviews
COMMENT ON TABLE exception_reviews IS 'Periodic reviews of approved exceptions to ensure controls remain effective';
COMMENT ON COLUMN exception_reviews.review_type IS 'Type of review (Scheduled, Ad-hoc, Audit-triggered)';
COMMENT ON COLUMN exception_reviews.outcome IS 'Result of review (APPROVED_CONTINUE, APPROVED_MODIFY, REVOKED, ESCALATED)';

-- =============================================================================
-- 7. CREATE TRIGGERS FOR UPDATED_AT
-- =============================================================================

-- Trigger function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to approved_exceptions
CREATE TRIGGER update_approved_exceptions_updated_at
    BEFORE UPDATE ON approved_exceptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to exception_controls
CREATE TRIGGER update_exception_controls_updated_at
    BEFORE UPDATE ON exception_controls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to exception_violations
CREATE TRIGGER update_exception_violations_updated_at
    BEFORE UPDATE ON exception_violations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 8. CREATE HELPER FUNCTIONS
-- =============================================================================

-- Function to generate next exception code
CREATE OR REPLACE FUNCTION generate_exception_code()
RETURNS VARCHAR(50) AS $$
DECLARE
    next_number INTEGER;
    year_prefix VARCHAR(4);
    exception_code VARCHAR(50);
BEGIN
    year_prefix := TO_CHAR(CURRENT_DATE, 'YYYY');

    -- Get next sequence number for this year
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(exception_code FROM 'EXC-' || year_prefix || '-([0-9]+)') AS INTEGER)
    ), 0) + 1
    INTO next_number
    FROM approved_exceptions
    WHERE exception_code LIKE 'EXC-' || year_prefix || '-%';

    -- Format: EXC-2026-001
    exception_code := 'EXC-' || year_prefix || '-' || LPAD(next_number::TEXT, 3, '0');

    RETURN exception_code;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION generate_exception_code() IS 'Generates next sequential exception code (e.g., EXC-2026-001)';

-- Function to calculate combined risk reduction from multiple controls
CREATE OR REPLACE FUNCTION calculate_combined_risk_reduction(exception_id_param UUID)
RETURNS DECIMAL(5, 2) AS $$
DECLARE
    combined_reduction DECIMAL(5, 2);
BEGIN
    -- Formula: 1 - ((1 - r1) * (1 - r2) * ... * (1 - rn))
    -- Where r1, r2, ... rn are risk reductions as decimals (e.g., 0.80 for 80%)
    SELECT (1 - EXP(SUM(LN(1 - risk_reduction_percentage / 100.0)))) * 100
    INTO combined_reduction
    FROM exception_controls
    WHERE exception_id = exception_id_param
      AND implementation_status IN ('IMPLEMENTED', 'ACTIVE')
      AND risk_reduction_percentage IS NOT NULL;

    RETURN COALESCE(combined_reduction, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_combined_risk_reduction(UUID) IS 'Calculates combined risk reduction percentage from multiple controls (non-additive formula)';

-- Function to calculate control effectiveness score
CREATE OR REPLACE FUNCTION calculate_control_effectiveness(control_id_param INTEGER)
RETURNS DECIMAL(5, 2) AS $$
DECLARE
    total_prevented INTEGER;
    total_occurred INTEGER;
    effectiveness DECIMAL(5, 2);
BEGIN
    SELECT
        COALESCE(SUM(violations_prevented), 0),
        COALESCE(SUM(violations_occurred), 0)
    INTO total_prevented, total_occurred
    FROM exception_controls
    WHERE exception_control_id = control_id_param;

    -- Effectiveness = prevented / (prevented + occurred)
    IF (total_prevented + total_occurred) > 0 THEN
        effectiveness := (total_prevented::DECIMAL / (total_prevented + total_occurred)) * 100;
    ELSE
        effectiveness := NULL;  -- No data yet
    END IF;

    RETURN effectiveness;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_control_effectiveness(INTEGER) IS 'Calculates effectiveness score for a control based on violations prevented vs occurred';

-- =============================================================================
-- 9. CREATE VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View: Active exceptions summary
CREATE OR REPLACE VIEW v_active_exceptions_summary AS
SELECT
    ae.exception_id,
    ae.exception_code,
    ae.user_name,
    ae.job_title,
    ae.department,
    ae.role_names,
    ae.conflict_count,
    ae.risk_score,
    ae.approved_by,
    ae.approved_date,
    ae.next_review_date,
    ae.status,
    -- Count of controls
    COUNT(ec.exception_control_id) AS control_count,
    -- Total estimated cost
    COALESCE(SUM(ec.estimated_annual_cost), 0) AS total_annual_cost,
    -- Combined risk reduction
    calculate_combined_risk_reduction(ae.exception_id) AS combined_risk_reduction,
    -- Violation count
    (SELECT COUNT(*) FROM exception_violations ev WHERE ev.exception_id = ae.exception_id) AS violation_count
FROM approved_exceptions ae
LEFT JOIN exception_controls ec ON ae.exception_id = ec.exception_id
WHERE ae.status = 'ACTIVE'
GROUP BY ae.exception_id, ae.exception_code, ae.user_name, ae.job_title, ae.department,
         ae.role_names, ae.conflict_count, ae.risk_score, ae.approved_by, ae.approved_date,
         ae.next_review_date, ae.status;

COMMENT ON VIEW v_active_exceptions_summary IS 'Summary of all active exceptions with control counts, costs, and effectiveness';

-- View: Exception effectiveness dashboard
CREATE OR REPLACE VIEW v_exception_effectiveness_dashboard AS
SELECT
    status,
    COUNT(*) AS exception_count,
    COALESCE(SUM(
        (SELECT SUM(ec.estimated_annual_cost)
         FROM exception_controls ec
         WHERE ec.exception_id = ae.exception_id)
    ), 0) AS total_annual_cost,
    ROUND(AVG(risk_score), 2) AS avg_risk_score,
    ROUND(AVG(
        COALESCE(calculate_combined_risk_reduction(exception_id), 0)
    ), 2) AS avg_risk_reduction
FROM approved_exceptions ae
GROUP BY status;

COMMENT ON VIEW v_exception_effectiveness_dashboard IS 'Dashboard statistics on exceptions grouped by status';

-- =============================================================================
-- 10. GRANT PERMISSIONS (adjust role name as needed)
-- =============================================================================

-- Grant permissions on tables (uncomment and adjust role name)
-- GRANT SELECT, INSERT, UPDATE ON approved_exceptions TO compliance_user;
-- GRANT SELECT, INSERT, UPDATE ON exception_controls TO compliance_user;
-- GRANT SELECT, INSERT, UPDATE ON exception_violations TO compliance_user;
-- GRANT SELECT, INSERT, UPDATE ON exception_reviews TO compliance_user;
-- GRANT SELECT ON v_active_exceptions_summary TO compliance_user;
-- GRANT SELECT ON v_exception_effectiveness_dashboard TO compliance_user;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 005_add_exception_tables.sql completed successfully';
    RAISE NOTICE 'Created 4 tables: approved_exceptions, exception_controls, exception_violations, exception_reviews';
    RAISE NOTICE 'Created 4 enums: exception_status, implementation_status, remediation_status, review_outcome';
    RAISE NOTICE 'Created 3 helper functions: generate_exception_code, calculate_combined_risk_reduction, calculate_control_effectiveness';
    RAISE NOTICE 'Created 2 views: v_active_exceptions_summary, v_exception_effectiveness_dashboard';
END $$;
