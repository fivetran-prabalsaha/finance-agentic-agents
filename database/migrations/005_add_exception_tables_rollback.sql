-- Rollback Migration: Remove exception management tables
-- Date: 2026-02-13
-- Purpose: Rollback for 005_add_exception_tables.sql
-- WARNING: This will delete all exception data permanently!

-- =============================================================================
-- ROLLBACK PROCEDURE
-- =============================================================================

-- Drop views
DROP VIEW IF EXISTS v_exception_effectiveness_dashboard CASCADE;
DROP VIEW IF EXISTS v_active_exceptions_summary CASCADE;

-- Drop helper functions
DROP FUNCTION IF EXISTS calculate_control_effectiveness(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS calculate_combined_risk_reduction(UUID) CASCADE;
DROP FUNCTION IF EXISTS generate_exception_code() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop tables (in reverse dependency order)
DROP TABLE IF EXISTS exception_reviews CASCADE;
DROP TABLE IF EXISTS exception_violations CASCADE;
DROP TABLE IF EXISTS exception_controls CASCADE;
DROP TABLE IF EXISTS approved_exceptions CASCADE;
DROP TABLE IF EXISTS compensating_controls CASCADE;

-- Drop enums
DROP TYPE IF EXISTS review_outcome CASCADE;
DROP TYPE IF EXISTS remediation_status CASCADE;
DROP TYPE IF EXISTS implementation_status CASCADE;
DROP TYPE IF EXISTS exception_status CASCADE;

-- Log rollback completion
DO $$
BEGIN
    RAISE NOTICE 'Rollback 005_add_exception_tables_rollback.sql completed';
    RAISE NOTICE 'All exception management tables, functions, and views removed';
    RAISE WARNING 'All exception data has been permanently deleted';
END $$;
