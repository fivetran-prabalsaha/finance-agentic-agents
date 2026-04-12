"""
Violation Repository - CRUD operations for SOD violations

Handles all database operations for Violation model
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, joinedload

from models.database import Violation, ViolationSeverity, ViolationStatus

logger = logging.getLogger(__name__)


class ViolationRepository:
    """Repository for Violation data access"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_violation(self, violation_data: dict[str, Any]) -> Violation:
        """
        Create a new violation

        Args:
            violation_data: Dictionary with violation fields (including optional 'embedding')

        Returns:
            Created Violation object
        """
        violation = Violation(
            user_id=violation_data['user_id'],
            rule_id=violation_data['rule_id'],
            scan_id=violation_data.get('scan_id'),
            severity=ViolationSeverity[violation_data['severity']],
            status=ViolationStatus[violation_data.get('status', 'OPEN')],
            risk_score=violation_data.get('risk_score', 0.0),
            title=violation_data['title'],
            description=violation_data.get('description'),
            conflicting_roles=violation_data.get('conflicting_roles', []),
            conflicting_permissions=violation_data.get('conflicting_permissions', []),
            embedding=violation_data.get('embedding'),  # NEW: Support for pgvector embeddings
            violation_metadata=violation_data.get('violation_metadata', {})
        )

        self.session.add(violation)
        self.session.commit()
        self.session.refresh(violation)

        logger.info(f"Created violation: {violation.title} (severity: {violation.severity}, embedded: {violation.embedding is not None})")
        return violation

    def get_violation_by_id(self, violation_id: str) -> Violation | None:
        """
        Get violation by UUID

        Args:
            violation_id: Violation UUID

        Returns:
            Violation object or None
        """
        return (
            self.session.query(Violation)
            .filter(Violation.id == violation_id)
            .options(
                joinedload(Violation.user),
                joinedload(Violation.rule)
            )
            .first()
        )

    def get_violations_by_user(
        self,
        user_id: str,
        status: ViolationStatus | None = None
    ) -> list[Violation]:
        """
        Get all violations for a user

        Args:
            user_id: User UUID
            status: Filter by status

        Returns:
            List of Violation objects
        """
        query = (
            self.session.query(Violation)
            .filter(Violation.user_id == user_id)
            .options(joinedload(Violation.rule))
        )

        if status:
            query = query.filter(Violation.status == status)

        return query.order_by(desc(Violation.detected_at)).all()

    def get_open_violations(
        self,
        severity: ViolationSeverity | None = None,
        min_risk_score: float = 0.0,
        limit: int = 100
    ) -> list[Violation]:
        """
        Get open violations with optional filters

        Args:
            severity: Filter by severity
            min_risk_score: Minimum risk score
            limit: Maximum results

        Returns:
            List of Violation objects
        """
        query = (
            self.session.query(Violation)
            .filter(Violation.status == ViolationStatus.OPEN)
            .options(
                joinedload(Violation.user),
                joinedload(Violation.rule)
            )
        )

        if severity:
            query = query.filter(Violation.severity == severity)

        if min_risk_score > 0:
            query = query.filter(Violation.risk_score >= min_risk_score)

        return query.order_by(desc(Violation.risk_score)).limit(limit).all()

    def get_critical_violations(self, limit: int = 50) -> list[Violation]:
        """
        Get critical open violations

        Args:
            limit: Maximum results

        Returns:
            List of Violation objects
        """
        return self.get_open_violations(
            severity=ViolationSeverity.CRITICAL,
            limit=limit
        )

    def resolve_violation(
        self,
        violation_id: str,
        resolved_by: str,
        resolution_notes: str | None = None,
        status: ViolationStatus = ViolationStatus.RESOLVED
    ) -> Violation | None:
        """
        Resolve a violation

        Args:
            violation_id: Violation UUID
            resolved_by: Who resolved it
            resolution_notes: Notes about resolution
            status: New status (RESOLVED, ACCEPTED_RISK, FALSE_POSITIVE)

        Returns:
            Updated Violation object
        """
        violation = self.get_violation_by_id(violation_id)

        if not violation:
            logger.error(f"Violation not found: {violation_id}")
            return None

        violation.status = status
        violation.resolved_at = datetime.utcnow()
        violation.resolved_by = resolved_by
        violation.resolution_notes = resolution_notes

        self.session.commit()
        self.session.refresh(violation)

        logger.info(f"Resolved violation {violation_id} with status {status}")
        return violation

    def bulk_create_violations(self, violations_data: list[dict[str, Any]]) -> int:
        """
        Bulk create violations

        Args:
            violations_data: List of violation data dictionaries

        Returns:
            Number of violations created
        """
        count = 0
        for violation_data in violations_data:
            try:
                self.create_violation(violation_data)
                count += 1
            except Exception as e:
                logger.error(f"Error creating violation: {str(e)}")
                self.session.rollback()

        logger.info(f"Bulk created {count}/{len(violations_data)} violations")
        return count

    def get_violations_by_scan(self, scan_id: str) -> list[Violation]:
        """
        Get all violations from a specific scan

        Args:
            scan_id: ComplianceScan UUID

        Returns:
            List of Violation objects
        """
        return (
            self.session.query(Violation)
            .filter(Violation.scan_id == scan_id)
            .options(
                joinedload(Violation.user),
                joinedload(Violation.rule)
            )
            .order_by(desc(Violation.risk_score))
            .all()
        )

    def get_violation_summary(self) -> dict[str, Any]:
        """
        Get summary statistics for violations

        Returns:
            Dictionary with violation counts by severity and status
        """
        summary = {
            'total': self.session.query(Violation).count(),
            'open': self.session.query(Violation).filter(Violation.status == ViolationStatus.OPEN).count(),
            'by_severity': {},
            'by_status': {}
        }

        # Count by severity
        for severity in ViolationSeverity:
            count = (
                self.session.query(Violation)
                .filter(and_(
                    Violation.severity == severity,
                    Violation.status == ViolationStatus.OPEN
                ))
                .count()
            )
            summary['by_severity'][severity.value] = count

        # Count by status
        for status in ViolationStatus:
            count = self.session.query(Violation).filter(Violation.status == status).count()
            summary['by_status'][status.value] = count

        return summary

    def delete_violation(self, violation_id: str):
        """
        Delete a violation

        Args:
            violation_id: Violation UUID to delete
        """
        violation = self.get_violation_by_id(violation_id)
        if violation:
            self.session.delete(violation)
            self.session.commit()
            logger.info(f"Deleted violation: {violation_id}")

    def get_high_risk_violations(
        self,
        min_risk_score: float = 70.0,
        status: ViolationStatus = ViolationStatus.OPEN
    ) -> list[Violation]:
        """
        Get high-risk violations

        Args:
            min_risk_score: Minimum risk score (default 70)
            status: Filter by status

        Returns:
            List of Violation objects
        """
        return (
            self.session.query(Violation)
            .filter(and_(
                Violation.status == status,
                Violation.risk_score >= min_risk_score
            ))
            .options(
                joinedload(Violation.user),
                joinedload(Violation.rule)
            )
            .order_by(desc(Violation.risk_score))
            .all()
        )

    def get_violations_by_rule(self, rule_id: str) -> list[Violation]:
        """
        Get all violations for a specific SOD rule

        Args:
            rule_id: SODRule UUID

        Returns:
            List of Violation objects
        """
        return (
            self.session.query(Violation)
            .filter(Violation.rule_id == rule_id)
            .options(joinedload(Violation.user))
            .order_by(desc(Violation.detected_at))
            .all()
        )

    def update_risk_score(self, violation_id: str, new_risk_score: float) -> Violation | None:
        """
        Update the risk score of a violation

        Args:
            violation_id: Violation UUID
            new_risk_score: New risk score (0-100)

        Returns:
            Updated Violation object
        """
        violation = self.get_violation_by_id(violation_id)

        if not violation:
            return None

        violation.risk_score = new_risk_score
        self.session.commit()
        self.session.refresh(violation)

        logger.info(f"Updated risk score for violation {violation_id}: {new_risk_score}")
        return violation

    def update_embedding(self, violation_id: str, embedding: list[float]) -> Violation | None:
        """
        Update the embedding of a violation (Step 8: Violation Embedding)

        Args:
            violation_id: Violation UUID
            embedding: Vector embedding

        Returns:
            Updated Violation object
        """
        violation = self.get_violation_by_id(violation_id)

        if not violation:
            return None

        violation.embedding = embedding
        self.session.commit()
        self.session.refresh(violation)

        logger.info(f"Updated embedding for violation {violation_id}")
        return violation

    def get_violations_without_embeddings(self, limit: int = 100) -> list[Violation]:
        """
        Get violations that don't have embeddings yet (for backfilling)

        Args:
            limit: Maximum number of violations to return

        Returns:
            List of Violation objects without embeddings
        """
        return (
            self.session.query(Violation)
            .filter(Violation.embedding.is_(None))
            .limit(limit)
            .all()
        )
