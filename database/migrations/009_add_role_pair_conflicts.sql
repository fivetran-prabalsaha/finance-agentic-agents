-- Migration: 009_add_role_pair_conflicts
-- Purpose: Stores the precomputed role × role conflict matrix.
--          One row per (role_a, role_b, rule, permission_a, permission_b) conflict.
--          Covers both intra-role (role_a = role_b) and cross-role pairs.
--          Populated by scripts/build_role_risk_matrix.py.
-- Rollback: 009_add_role_pair_conflicts_rollback.sql

CREATE TABLE IF NOT EXISTS role_pair_conflicts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- The two roles involved. role_a_id <= role_b_id alphabetically (normalised)
    -- so every pair is stored exactly once. For intra-role: role_a_id = role_b_id.
    role_a_id               VARCHAR(100) NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    role_b_id               VARCHAR(100) NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,

    -- Human-readable names (denormalised for fast display)
    role_a_name             TEXT NOT NULL,
    role_b_name             TEXT NOT NULL,

    -- Which SOD rule fires
    rule_id                 UUID NOT NULL REFERENCES sod_rules(id) ON DELETE CASCADE,
    rule_name               TEXT NOT NULL,
    severity                violationseverity NOT NULL,

    -- Exact permission and level on each side that triggers the conflict
    role_a_permission       TEXT NOT NULL,   -- e.g. "Bills"
    role_a_level            TEXT NOT NULL,   -- e.g. "Edit"
    role_b_permission       TEXT NOT NULL,   -- e.g. "Vendor Bill Approval"
    role_b_level            TEXT NOT NULL,   -- e.g. "Full"

    -- Whether this is an intra-role conflict (same role on both sides)
    is_intra_role           BOOLEAN NOT NULL DEFAULT FALSE,

    -- Human-readable summary for direct display
    conflict_description    TEXT,

    analyzed_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Unique constraint: one record per directional permission-pair per rule per role-pair
    UNIQUE (role_a_id, role_b_id, rule_id, role_a_permission, role_b_permission)
);

-- Fast lookups by individual role (either side)
CREATE INDEX IF NOT EXISTS idx_rpc_role_a
    ON role_pair_conflicts (role_a_id, severity);

CREATE INDEX IF NOT EXISTS idx_rpc_role_b
    ON role_pair_conflicts (role_b_id, severity);

-- Pair lookup (both directions)
CREATE INDEX IF NOT EXISTS idx_rpc_pair
    ON role_pair_conflicts (role_a_id, role_b_id);

CREATE INDEX IF NOT EXISTS idx_rpc_severity
    ON role_pair_conflicts (severity, is_intra_role);

COMMENT ON TABLE role_pair_conflicts IS
    'Precomputed SOD conflict matrix for all Fivetran role pairs. '
    'Each row represents one specific (permission, level) conflict between two roles '
    'under one SOD rule. A pair may have multiple rows (multiple rules firing, or '
    'multiple permission pairs within one rule). '
    'Intra-role rows (role_a = role_b) capture permissions dangerous within a '
    'single role. Cross-role rows capture conflicts that only emerge when two roles '
    'are combined. Populated by scripts/build_role_risk_matrix.py. '
    'Refreshed on every NetSuite sync or on-demand via trigger_manual_sync.';

COMMENT ON COLUMN role_pair_conflicts.role_a_id IS
    'Alphabetically first role in the pair (normalised to prevent duplicate rows). '
    'For intra-role conflicts this equals role_b_id.';
