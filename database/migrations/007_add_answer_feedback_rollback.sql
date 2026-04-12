-- Rollback: 007_add_answer_feedback.sql
-- Date: 2026-02-26

DROP INDEX IF EXISTS idx_answer_feedback_run;
DROP INDEX IF EXISTS idx_answer_feedback_signal;
DROP INDEX IF EXISTS idx_answer_feedback_user;
DROP TABLE IF EXISTS answer_feedback;
