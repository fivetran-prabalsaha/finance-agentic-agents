-- Migration: Add answer_feedback table
-- Date: 2026-02-26
-- Purpose: Phase feedback loop — capture human scores on bot answers via Slack
--          Block Kit buttons. Scores written back to LangSmith (human_rating)
--          alongside 3 automated evaluators. Negative feedback busts Redis cache.
-- Rollback: 007_add_answer_feedback_rollback.sql

-- =============================================================================
-- 1. CREATE TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS answer_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- LangSmith trace ID — used to write score back via create_feedback()
    run_id          TEXT,

    -- Who submitted the feedback
    user_email      TEXT NOT NULL,
    channel_id      TEXT,                       -- Slack channel/DM ID
    message_ts      TEXT,                       -- Slack message timestamp (stable identifier)

    -- Truncated previews for quick inspection without joining to logs
    query_preview   TEXT,                       -- first 200 chars of user query
    answer_preview  TEXT,                       -- first 200 chars of bot answer

    -- Human signal
    signal          TEXT NOT NULL CHECK (signal IN ('POSITIVE', 'NEGATIVE', 'PARTIAL', 'UNCLEAR')),
    correction      TEXT,                       -- Phase B: free-text correction from modal

    -- Which MCP tool produced the primary data in this answer
    tool_called     TEXT,

    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- 2. INDEXES
-- =============================================================================

-- Primary query: latest N feedback rows per user
CREATE INDEX IF NOT EXISTS idx_answer_feedback_user
    ON answer_feedback (user_email, created_at DESC);

-- Drift alerting: rolling negative rate per signal type
CREATE INDEX IF NOT EXISTS idx_answer_feedback_signal
    ON answer_feedback (signal, created_at DESC);

-- LangSmith cross-reference lookup
CREATE INDEX IF NOT EXISTS idx_answer_feedback_run
    ON answer_feedback (run_id)
    WHERE run_id IS NOT NULL;

-- =============================================================================
-- 3. COMMENTS
-- =============================================================================

COMMENT ON TABLE answer_feedback IS
    'Human feedback on compliance bot answers captured via Slack Block Kit buttons. '
    'Scores (POSITIVE=1.0, NEGATIVE=0.0, PARTIAL=0.5) written back to LangSmith '
    'create_feedback() so human ratings appear alongside automated evaluators. '
    'Negative feedback triggers Redis cache bust for violation data.';

COMMENT ON COLUMN answer_feedback.run_id IS
    'LangSmith trace ID from slack_compliance_query run. '
    'Used with langsmith.Client().create_feedback() to post human_rating score.';

COMMENT ON COLUMN answer_feedback.signal IS
    'POSITIVE: answer was correct. '
    'NEGATIVE: answer was wrong (also triggers Redis cache bust). '
    'PARTIAL: answer was partially correct. '
    'UNCLEAR: answer was ambiguous or confusing.';

COMMENT ON COLUMN answer_feedback.correction IS
    'Phase B: free-text correction submitted via Slack modal on NEGATIVE signal. '
    'Written to LangSmith as create_feedback(comment=correction). '
    'Phase C: stored as pgvector embedding for few-shot injection.';

COMMENT ON COLUMN answer_feedback.tool_called IS
    'MCP tool that produced the primary data in the answer '
    '(e.g. get_user_violations, analyze_access_request). '
    'Enables per-tool accuracy tracking.';
