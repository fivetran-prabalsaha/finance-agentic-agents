"""
SQLAlchemy Model — Answer Feedback (Phase feedback loop)

Human scores captured via Slack Block Kit buttons on every bot response.
Written non-blocking to Postgres and to LangSmith (create_feedback) after
each button click. Negative feedback also busts the Redis MCP cache.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from models.database_config import Base


class AnswerFeedback(Base):
    """
    Human feedback on a single bot answer.

    Written non-blocking via threading.Thread after a Slack button click.
    run_id links back to the LangSmith slack_compliance_query trace so scores
    appear in the Feedback tab alongside the 3 automated evaluators.
    """
    __tablename__ = "answer_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # LangSmith trace linkage
    run_id = Column(String(100))                 # slack_compliance_query run ID

    # Who gave the feedback
    user_email = Column(String(255), nullable=False, index=True)
    channel_id = Column(String(100))             # Slack channel / DM ID
    message_ts = Column(String(50))              # Slack message timestamp

    # Truncated previews for quick inspection
    query_preview  = Column(Text)                # first 200 chars of user query
    answer_preview = Column(Text)                # first 200 chars of bot answer

    # Human signal: POSITIVE | NEGATIVE | PARTIAL | UNCLEAR
    signal     = Column(String(20), nullable=False)
    correction = Column(Text)                    # Phase B: free-text from modal

    # Which MCP tool drove the answer
    tool_called = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_answer_feedback_user",   "user_email", "created_at"),
        Index("idx_answer_feedback_signal", "signal",     "created_at"),
        Index("idx_answer_feedback_run",    "run_id"),
    )

    def __repr__(self):
        return (
            f"<AnswerFeedback(user='{self.user_email}', "
            f"signal='{self.signal}', run='{self.run_id}')>"
        )
