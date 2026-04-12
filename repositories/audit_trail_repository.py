"""
Audit Trail Repository

Handles database operations for AuditTrail records, which log all significant
compliance events (violation create/update/resolve, exception approvals, etc.)
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import AuditTrail

logger = logging.getLogger(__name__)


class AuditTrailRepository:
    """Repository for AuditTrail operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        performed_by: str,
        details: dict[str, Any] | None = None,
        user_id: uuid.UUID | None = None,
        violation_id: uuid.UUID | None = None
    ) -> AuditTrail:
        """
        Create an audit trail record.

        Args:
            action: Action taken (e.g., 'violation_created', 'violation_resolved', 'exception_approved')
            entity_type: Type of entity affected (e.g., 'violation', 'exception', 'user')
            entity_id: ID of the entity
            performed_by: Who or what performed the action (user email or 'system')
            details: Optional dict with additional context
            user_id: Optional user UUID if the event involves a user
            violation_id: Optional violation UUID if the event involves a violation

        Returns:
            Created AuditTrail record
        """
        try:
            record = AuditTrail(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                performed_by=performed_by,
                details=details or {},
                user_id=user_id,
                violation_id=violation_id,
                created_at=datetime.utcnow()
            )
            self.session.add(record)
            self.session.flush()
            logger.debug(f"Audit trail: {action} on {entity_type}/{entity_id} by {performed_by}")
            return record
        except Exception as e:
            logger.error(f"Error creating audit trail record: {str(e)}")
            self.session.rollback()
            raise

    def get_for_entity(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 50
    ) -> list[AuditTrail]:
        """Get audit trail records for a specific entity."""
        try:
            return (
                self.session.query(AuditTrail)
                .filter(
                    AuditTrail.entity_type == entity_type,
                    AuditTrail.entity_id == entity_id
                )
                .order_by(desc(AuditTrail.created_at))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching audit trail for {entity_type}/{entity_id}: {str(e)}")
            return []

    def get_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 100
    ) -> list[AuditTrail]:
        """Get all audit trail records for a user."""
        try:
            return (
                self.session.query(AuditTrail)
                .filter(AuditTrail.user_id == user_id)
                .order_by(desc(AuditTrail.created_at))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching audit trail for user {user_id}: {str(e)}")
            return []

    def get_recent(self, limit: int = 100) -> list[AuditTrail]:
        """Get the most recent audit trail records across all entities."""
        try:
            return (
                self.session.query(AuditTrail)
                .order_by(desc(AuditTrail.created_at))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Error fetching recent audit trail: {str(e)}")
            return []
