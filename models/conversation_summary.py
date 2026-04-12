"""
SQLAlchemy Model — Conversation Summaries (Phase B Memory Management)

After each Slack DM exchange, Haiku generates a 2-3 sentence summary that is
stored here. On subsequent queries from the same user, the 3 most recent
non-expired summaries are injected into the system message as prior context,
replacing ~2K raw history tokens with ~150 summary tokens.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from models.database_config import Base


class ConversationSummary(Base):
    """
    Per-user conversation summaries for cross-session memory.

    Written non-blocking after each DM response via threading.Thread.
    Read at the start of each new DM to inject prior context into the
    system message before calling process_with_claude().
    """
    __tablename__ = "conversation_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who the conversation was with
    user_email = Column(String(255), nullable=False, index=True)
    channel_id = Column(String(100))          # Slack DM channel ID (D0AFAJUA16E)

    # Haiku-generated summary (≤150 tokens)
    summary = Column(Text, nullable=False)

    # Extracted topics for future Phase C semantic search
    topics = Column(ARRAY(String), default=[])  # e.g. ["austin.chen", "AP-Approver", "CRITICAL"]

    # Outcome classification
    outcome = Column(String(50))               # APPROVED | DENIED | ESCALATED | INFO | null

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)              # created_at + 90 days

    # Indexes — primary query pattern: latest N summaries per user
    __table_args__ = (
        Index("idx_conv_summaries_user_created", "user_email", "created_at"),
        Index("idx_conv_summaries_expires", "expires_at"),
    )

    def __repr__(self):
        return (
            f"<ConversationSummary(user='{self.user_email}', "
            f"outcome='{self.outcome}', created='{self.created_at}')>"
        )
