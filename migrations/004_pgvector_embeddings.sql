-- Migration 004: pgvector Embeddings and Phase 3 (Learning Loop)
--
-- This migration:
-- 1. Enables pgvector extension
-- 2. Adds vector embedding columns to existing tables
-- 3. Creates vector indexes for similarity search
-- 4. Creates violation_exemptions table for Phase 3
-- 5. Sets up learning and refinement infrastructure

-- ============================================
-- 1. Enable pgvector Extension
-- ============================================

-- Note: This requires superuser privileges. If you get a permission error,
-- ask your DBA to run: CREATE EXTENSION IF NOT EXISTS vector;
-- Or run as superuser: psql -c "CREATE EXTENSION IF NOT EXISTS vector;" -d compliance_db

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 2. Add Embedding Columns to Existing Tables
-- ============================================

-- Add embedding to roles table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='roles' AND column_name='embedding'
    ) THEN
        ALTER TABLE roles ADD COLUMN embedding vector(384);
    ELSE
        -- If exists as String, convert to vector
        ALTER TABLE roles ALTER COLUMN embedding TYPE vector(384) USING NULL;
    END IF;
END $$;

-- Add embedding to sod_rules table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='sod_rules' AND column_name='embedding'
    ) THEN
        ALTER TABLE sod_rules ADD COLUMN embedding vector(384);
    ELSE
        -- If exists as String, convert to vector
        ALTER TABLE sod_rules ALTER COLUMN embedding TYPE vector(384) USING NULL;
    END IF;
END $$;

-- Add embedding to violations table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='violations' AND column_name='embedding'
    ) THEN
        ALTER TABLE violations ADD COLUMN embedding vector(384);
    ELSE
        -- If exists as String, convert to vector
        ALTER TABLE violations ALTER COLUMN embedding TYPE vector(384) USING NULL;
    END IF;
END $$;

-- ============================================
-- 3. Create Vector Indexes for Similarity Search
-- ============================================

-- Index for roles similarity search (IVFFlat index)
CREATE INDEX IF NOT EXISTS idx_roles_embedding
ON roles USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for SOD rules similarity search
CREATE INDEX IF NOT EXISTS idx_sod_rules_embedding
ON sod_rules USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- Index for violations similarity search
CREATE INDEX IF NOT EXISTS idx_violations_embedding
ON violations USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================
-- 4. Create Violation Exemptions Table (Phase 3)
-- ============================================

-- Exemption status enum
DO $$ BEGIN
    CREATE TYPE exemption_status AS ENUM (
        'PENDING',
        'APPROVED',
        'REJECTED',
        'EXPIRED',
        'REVOKED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Violation exemptions table
CREATE TABLE IF NOT EXISTS violation_exemptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- References
    violation_id UUID REFERENCES violations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    rule_id UUID REFERENCES sod_rules(id) ON DELETE SET NULL,

    -- Exemption details
    reason VARCHAR(500) NOT NULL,
    rationale TEXT NOT NULL,
    business_justification TEXT,
    compensating_controls TEXT,

    -- Approval workflow
    status exemption_status NOT NULL DEFAULT 'PENDING',
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),

    approved_by VARCHAR(255),
    approved_at TIMESTAMP,
    approval_notes TEXT,

    rejected_by VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,

    -- Expiration and review
    expires_at TIMESTAMP,
    last_reviewed_at TIMESTAMP,
    next_review_date TIMESTAMP,
    auto_approved BOOLEAN DEFAULT FALSE,

    -- Risk assessment
    risk_score FLOAT,
    risk_acceptance_level VARCHAR(50),

    -- Embedding for similarity search (Phase 3: Learn from approved exemptions)
    embedding vector(384),

    -- Audit trail
    exemption_metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for exemptions
CREATE INDEX IF NOT EXISTS idx_exemption_status ON violation_exemptions(status);
CREATE INDEX IF NOT EXISTS idx_exemption_user ON violation_exemptions(user_id);
CREATE INDEX IF NOT EXISTS idx_exemption_rule ON violation_exemptions(rule_id);
CREATE INDEX IF NOT EXISTS idx_exemption_requested_at ON violation_exemptions(requested_at);
CREATE INDEX IF NOT EXISTS idx_exemption_next_review ON violation_exemptions(next_review_date);

-- Vector index for exemption similarity search
CREATE INDEX IF NOT EXISTS idx_exemptions_embedding
ON violation_exemptions USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- ============================================
-- 5. Create Helper Functions for Vector Operations
-- ============================================

-- Function to find similar rules using cosine similarity
CREATE OR REPLACE FUNCTION find_similar_rules(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.5,
    result_limit INT DEFAULT 5
)
RETURNS TABLE (
    rule_id UUID,
    rule_name VARCHAR,
    description TEXT,
    severity VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sr.id,
        sr.rule_name,
        sr.description,
        sr.severity::VARCHAR,
        1 - (sr.embedding <=> query_embedding) AS similarity
    FROM sod_rules sr
    WHERE sr.embedding IS NOT NULL
        AND (1 - (sr.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY sr.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar violations
CREATE OR REPLACE FUNCTION find_similar_violations(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.5,
    result_limit INT DEFAULT 5
)
RETURNS TABLE (
    violation_id UUID,
    title VARCHAR,
    description TEXT,
    severity VARCHAR,
    detected_at TIMESTAMP,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.id,
        v.title,
        v.description,
        v.severity::VARCHAR,
        v.detected_at,
        1 - (v.embedding <=> query_embedding) AS similarity
    FROM violations v
    WHERE v.embedding IS NOT NULL
        AND (1 - (v.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY v.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar exemptions (for Phase 3 learning)
CREATE OR REPLACE FUNCTION find_similar_exemptions(
    query_embedding vector(384),
    similarity_threshold FLOAT DEFAULT 0.5,
    result_limit INT DEFAULT 5
)
RETURNS TABLE (
    exemption_id UUID,
    reason VARCHAR,
    rationale TEXT,
    status VARCHAR,
    approved_at TIMESTAMP,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ve.id,
        ve.reason,
        ve.rationale,
        ve.status::VARCHAR,
        ve.approved_at,
        1 - (ve.embedding <=> query_embedding) AS similarity
    FROM violation_exemptions ve
    WHERE ve.embedding IS NOT NULL
        AND ve.status = 'APPROVED'
        AND (1 - (ve.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY ve.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. Create View for Ground Truth (Phase 1)
-- ============================================

CREATE OR REPLACE VIEW ground_truth_knowledge AS
SELECT
    'rule' AS source_type,
    sr.id AS source_id,
    sr.rule_name AS title,
    sr.description,
    sr.severity::VARCHAR AS severity,
    sr.embedding,
    sr.created_at
FROM sod_rules sr
WHERE sr.embedding IS NOT NULL AND sr.is_active = TRUE

UNION ALL

SELECT
    'exemption' AS source_type,
    ve.id AS source_id,
    ve.reason AS title,
    ve.rationale AS description,
    ve.risk_acceptance_level AS severity,
    ve.embedding,
    ve.approved_at AS created_at
FROM violation_exemptions ve
WHERE ve.embedding IS NOT NULL AND ve.status = 'APPROVED';

COMMENT ON VIEW ground_truth_knowledge IS
'Combined view of rules and approved exemptions for context-aware SOD analysis';

-- ============================================
-- 7. Create Trigger for Exemption Updates
-- ============================================

CREATE OR REPLACE FUNCTION update_exemption_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER exemption_updated_at_trigger
    BEFORE UPDATE ON violation_exemptions
    FOR EACH ROW
    EXECUTE FUNCTION update_exemption_timestamp();

-- ============================================
-- 8. Migration Metadata
-- ============================================

-- Track migration version
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version, description)
VALUES (
    '004',
    'pgvector embeddings and Phase 3 learning loop infrastructure'
) ON CONFLICT (version) DO NOTHING;

-- ============================================
-- Migration Complete
-- ============================================

-- Verify pgvector is working
DO $$
DECLARE
    test_vector vector(384);
BEGIN
    test_vector := ARRAY(SELECT random() FROM generate_series(1, 384))::vector(384);
    RAISE NOTICE 'pgvector migration completed successfully. Test vector created with dimension: %',
        vector_dims(test_vector);
END $$;
