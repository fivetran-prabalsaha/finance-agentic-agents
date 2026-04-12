"""
Exemption Repository - Data access layer for violation exemptions

Handles CRUD operations and queries for the ViolationExemption model
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.database import ExemptionStatus, ViolationExemption

logger = logging.getLogger(__name__)


class ExemptionRepository:
    """Repository for managing violation exemptions"""

    def __init__(self, session: Session):
        """
        Initialize Exemption Repository

        Args:
            session: SQLAlchemy database session
        """
        self.session = session

    def create_exemption(
        self,
        violation_id: str,
        user_id: str,
        rule_id: str,
        reason: str,
        rationale: str,
        requested_by: str,
        business_justification: str | None = None,
        compensating_controls: str | None = None,
        embedding: list[float] | None = None
    ) -> ViolationExemption:
        """
        Create a new exemption request

        Args:
            violation_id: UUID of the violation
            user_id: UUID of the user
            rule_id: UUID of the SOD rule
            reason: Short summary of exemption
            rationale: Detailed business justification
            requested_by: Email/name of requester
            business_justification: Business case
            compensating_controls: Mitigation measures
            embedding: Vector embedding for similarity search

        Returns:
            Created ViolationExemption instance
        """
        exemption = ViolationExemption(
            violation_id=violation_id,
            user_id=user_id,
            rule_id=rule_id,
            reason=reason,
            rationale=rationale,
            requested_by=requested_by,
            business_justification=business_justification,
            compensating_controls=compensating_controls,
            status=ExemptionStatus.PENDING,
            embedding=embedding
        )

        self.session.add(exemption)
        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Created exemption request: {exemption.id}")
        return exemption

    def approve_exemption(
        self,
        exemption_id: str,
        approved_by: str,
        approval_notes: str | None = None,
        expires_in_days: int = 365
    ) -> ViolationExemption:
        """
        Approve an exemption request

        Args:
            exemption_id: UUID of the exemption
            approved_by: Email/name of approver
            approval_notes: Optional notes
            expires_in_days: Days until exemption expires (default 1 year)

        Returns:
            Updated ViolationExemption instance
        """
        exemption = self.session.query(ViolationExemption).filter(
            ViolationExemption.id == exemption_id
        ).first()

        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found")

        if exemption.status != ExemptionStatus.PENDING:
            raise ValueError(f"Exemption {exemption_id} is not in PENDING status")

        exemption.status = ExemptionStatus.APPROVED
        exemption.approved_by = approved_by
        exemption.approved_at = datetime.utcnow()
        exemption.approval_notes = approval_notes
        exemption.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        exemption.next_review_date = datetime.utcnow() + timedelta(days=expires_in_days // 2)

        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Approved exemption: {exemption_id} by {approved_by}")
        return exemption

    def reject_exemption(
        self,
        exemption_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> ViolationExemption:
        """
        Reject an exemption request

        Args:
            exemption_id: UUID of the exemption
            rejected_by: Email/name of rejector
            rejection_reason: Reason for rejection

        Returns:
            Updated ViolationExemption instance
        """
        exemption = self.session.query(ViolationExemption).filter(
            ViolationExemption.id == exemption_id
        ).first()

        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found")

        exemption.status = ExemptionStatus.REJECTED
        exemption.rejected_by = rejected_by
        exemption.rejected_at = datetime.utcnow()
        exemption.rejection_reason = rejection_reason

        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Rejected exemption: {exemption_id} by {rejected_by}")
        return exemption

    def get_exemption_by_id(self, exemption_id: str) -> ViolationExemption | None:
        """Get exemption by ID"""
        return self.session.query(ViolationExemption).filter(
            ViolationExemption.id == exemption_id
        ).first()

    def get_exemptions_by_user(
        self,
        user_id: str,
        status: ExemptionStatus | None = None
    ) -> list[ViolationExemption]:
        """
        Get exemptions for a specific user

        Args:
            user_id: UUID of the user
            status: Optional status filter

        Returns:
            List of ViolationExemption instances
        """
        query = self.session.query(ViolationExemption).filter(
            ViolationExemption.user_id == user_id
        )

        if status:
            query = query.filter(ViolationExemption.status == status)

        return query.order_by(desc(ViolationExemption.requested_at)).all()

    def get_exemptions_by_rule(
        self,
        rule_id: str,
        status: ExemptionStatus | None = None
    ) -> list[ViolationExemption]:
        """
        Get exemptions for a specific rule

        Args:
            rule_id: UUID of the SOD rule
            status: Optional status filter

        Returns:
            List of ViolationExemption instances
        """
        query = self.session.query(ViolationExemption).filter(
            ViolationExemption.rule_id == rule_id
        )

        if status:
            query = query.filter(ViolationExemption.status == status)

        return query.order_by(desc(ViolationExemption.requested_at)).all()

    def get_pending_exemptions(self) -> list[ViolationExemption]:
        """Get all pending exemption requests"""
        return self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.PENDING
        ).order_by(ViolationExemption.requested_at).all()

    def get_approved_exemptions(self) -> list[ViolationExemption]:
        """Get all approved exemptions"""
        return self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.APPROVED
        ).order_by(desc(ViolationExemption.approved_at)).all()

    def get_exemptions_needing_review(self) -> list[ViolationExemption]:
        """Get exemptions that need periodic review"""
        return self.session.query(ViolationExemption).filter(
            and_(
                ViolationExemption.status == ExemptionStatus.APPROVED,
                ViolationExemption.next_review_date <= datetime.utcnow()
            )
        ).order_by(ViolationExemption.next_review_date).all()

    def get_expiring_exemptions(self, days: int = 30) -> list[ViolationExemption]:
        """
        Get exemptions expiring within specified days

        Args:
            days: Number of days to look ahead

        Returns:
            List of expiring exemptions
        """
        cutoff_date = datetime.utcnow() + timedelta(days=days)

        return self.session.query(ViolationExemption).filter(
            and_(
                ViolationExemption.status == ExemptionStatus.APPROVED,
                ViolationExemption.expires_at <= cutoff_date
            )
        ).order_by(ViolationExemption.expires_at).all()

    def expire_exemption(self, exemption_id: str) -> ViolationExemption:
        """Mark an exemption as expired"""
        exemption = self.get_exemption_by_id(exemption_id)

        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found")

        exemption.status = ExemptionStatus.EXPIRED
        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Expired exemption: {exemption_id}")
        return exemption

    def revoke_exemption(
        self,
        exemption_id: str,
        revoked_by: str,
        reason: str
    ) -> ViolationExemption:
        """
        Revoke an approved exemption

        Args:
            exemption_id: UUID of the exemption
            revoked_by: Email/name of person revoking
            reason: Reason for revocation

        Returns:
            Updated ViolationExemption instance
        """
        exemption = self.get_exemption_by_id(exemption_id)

        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found")

        if exemption.status != ExemptionStatus.APPROVED:
            raise ValueError("Can only revoke APPROVED exemptions")

        exemption.status = ExemptionStatus.REVOKED
        exemption.exemption_metadata = exemption.exemption_metadata or {}
        exemption.exemption_metadata['revoked_by'] = revoked_by
        exemption.exemption_metadata['revoked_at'] = datetime.utcnow().isoformat()
        exemption.exemption_metadata['revocation_reason'] = reason

        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Revoked exemption: {exemption_id} by {revoked_by}")
        return exemption

    def update_exemption_embedding(
        self,
        exemption_id: str,
        embedding: list[float]
    ) -> ViolationExemption:
        """
        Update exemption embedding (for Phase 3: Learning Loop)

        Args:
            exemption_id: UUID of the exemption
            embedding: Vector embedding

        Returns:
            Updated ViolationExemption instance
        """
        exemption = self.get_exemption_by_id(exemption_id)

        if not exemption:
            raise ValueError(f"Exemption {exemption_id} not found")

        exemption.embedding = embedding
        self.session.commit()
        self.session.refresh(exemption)

        logger.info(f"Updated embedding for exemption: {exemption_id}")
        return exemption

    def get_exemption_stats(self) -> dict[str, Any]:
        """Get exemption statistics"""
        total = self.session.query(ViolationExemption).count()
        pending = self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.PENDING
        ).count()
        approved = self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.APPROVED
        ).count()
        rejected = self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.REJECTED
        ).count()
        expired = self.session.query(ViolationExemption).filter(
            ViolationExemption.status == ExemptionStatus.EXPIRED
        ).count()

        return {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'expired': expired,
            'approval_rate': (approved / total * 100) if total > 0 else 0
        }


# Factory function
def create_exemption_repository(session: Session) -> ExemptionRepository:
    """Create a configured Exemption Repository instance"""
    return ExemptionRepository(session=session)
