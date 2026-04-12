-- Rollback: Remove conversation_summaries table
-- Date: 2026-02-24
-- Reverses: 006_add_conversation_summaries.sql

DROP INDEX IF EXISTS idx_conv_summaries_user_created;
DROP INDEX IF EXISTS idx_conv_summaries_expires;
DROP TABLE IF EXISTS conversation_summaries;
