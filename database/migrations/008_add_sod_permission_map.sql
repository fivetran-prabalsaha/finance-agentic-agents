-- Migration: 008_add_sod_permission_map
-- Purpose: Rosetta stone mapping abstract SOD rule permission names
--          to actual NetSuite permission_name values and the minimum
--          level at which each side of a conflict is "active".
--          Used by the role risk matrix analysis job.
-- Rollback: 008_add_sod_permission_map_rollback.sql

CREATE TABLE IF NOT EXISTS sod_permission_map (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Which SOD rule and which pair within that rule this row belongs to
    rule_id         UUID NOT NULL REFERENCES sod_rules(id) ON DELETE CASCADE,
    conflict_index  INTEGER NOT NULL,   -- 0-based index of pair within the rule

    -- Which side of the conflict pair (left=maker/actor, right=checker/approver)
    side            TEXT NOT NULL CHECK (side IN ('left', 'right')),

    -- Abstract name as stored in sod_rules.conflicting_permissions
    abstract_name   TEXT NOT NULL,

    -- Actual NetSuite permission_name as it appears in roles.permissions[].permission_name
    -- NULL means this permission is not present in any Fivetran role (rule cannot fire)
    ns_permission   TEXT,

    -- Minimum level at which this permission makes its holder an active party
    -- in the conflict. Anything below this level is safe (View-only = not a risk source,
    -- except for audit-trail independence rules where View is specifically the problem).
    min_level       TEXT NOT NULL CHECK (min_level IN ('View', 'Create', 'Edit', 'Full')),

    -- Human-readable note explaining the conflict logic
    note            TEXT,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (rule_id, conflict_index, side)
);

CREATE INDEX IF NOT EXISTS idx_sod_perm_map_rule
    ON sod_permission_map (rule_id);

CREATE INDEX IF NOT EXISTS idx_sod_perm_map_ns_perm
    ON sod_permission_map (ns_permission)
    WHERE ns_permission IS NOT NULL;

COMMENT ON TABLE sod_permission_map IS
    'Maps each abstract SOD rule permission name (e.g. "Create Bill") to the actual '
    'NetSuite permission_name stored in roles.permissions (e.g. "Bills") plus the '
    'minimum level at which that permission activates as a conflict source. '
    'Populated by scripts/build_role_risk_matrix.py. '
    'Used by the role pair conflict analysis to evaluate (permission, level) pairs '
    'rather than raw permission names, preventing false positives from View-only access.';

COMMENT ON COLUMN sod_permission_map.min_level IS
    'Minimum NetSuite permission level that makes this side of the conflict active. '
    'Level hierarchy: None < View < Create < Edit < Full. '
    'Most maker/checker rules require Edit (can actually create or approve). '
    'Audit-log independence rules use View (having any visibility is the risk). '
    'Script deploy rules require Full (actual production push).';
