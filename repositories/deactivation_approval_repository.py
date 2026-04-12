"""
Deactivation Approval Repository

Data access layer for user deactivation approval workflow
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from models.database import ApprovalStatus, DeactivationApproval, ExecutionMethod, ExecutionStatus

logger = logging.getLogger(__name__)


class DeactivationApprovalRepository:
    """Repository for deactivation approval operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_approval_request(self, request_data: dict[str, Any]) -> DeactivationApproval:
        """Create a new deactivation approval request"""
        # Calculate expiration (default 48 hours)
        expires_in_hours = request_data.get('expires_in_hours', 48)
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        approval = DeactivationApproval(
            request_id=request_data['request_id'],
            user_ids=request_data['user_ids'],
            user_count=len(request_data['user_ids']),
            requested_by=request_data['requested_by'],
            expires_at=expires_at,
            approval_metadata=request_data.get('approval_metadata')
        )

        self.session.add(approval)
        self.session.commit()
        self.session.refresh(approval)

        logger.info(f"Created approval request {approval.request_id} for {approval.user_count} users")
        return approval

    def get_approval_by_id(self, approval_id: str) -> DeactivationApproval | None:
        """Get approval by UUID"""
        return self.session.query(DeactivationApproval).filter(
            DeactivationApproval.id == approval_id
        ).first()

    def get_approval_by_request_id(self, request_id: str) -> DeactivationApproval | None:
        """Get approval by request ID"""
        return self.session.query(DeactivationApproval).filter(
            DeactivationApproval.request_id == request_id
        ).first()

    def get_pending_approvals(self, limit: int | None = None) -> list[DeactivationApproval]:
        """Get all pending approval requests"""
        query = self.session.query(DeactivationApproval).filter(
            and_(
                DeactivationApproval.status == ApprovalStatus.PENDING,
                DeactivationApproval.expires_at > datetime.utcnow()
            )
        ).order_by(desc(DeactivationApproval.requested_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_approvals_by_status(
        self,
        status: ApprovalStatus,
        limit: int | None = None
    ) -> list[DeactivationApproval]:
        """Get approvals by status"""
        query = self.session.query(DeactivationApproval).filter(
            DeactivationApproval.status == status
        ).order_by(desc(DeactivationApproval.requested_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_approved_pending_execution(self) -> list[DeactivationApproval]:
        """Get approved requests that haven't been executed yet"""
        return self.session.query(DeactivationApproval).filter(
            and_(
                DeactivationApproval.status == ApprovalStatus.APPROVED,
                or_(
                    DeactivationApproval.execution_status is None,
                    DeactivationApproval.execution_status == ExecutionStatus.NOT_STARTED
                )
            )
        ).order_by(DeactivationApproval.approved_at).all()

    def get_expired_approvals(self) -> list[DeactivationApproval]:
        """Get approvals that have expired"""
        return self.session.query(DeactivationApproval).filter(
            and_(
                DeactivationApproval.status == ApprovalStatus.PENDING,
                DeactivationApproval.expires_at <= datetime.utcnow()
            )
        ).all()

    def approve_request(
        self,
        request_id: str,
        approved_by: str,
        execution_method: ExecutionMethod | None = None
    ) -> DeactivationApproval | None:
        """Approve a deactivation request"""
        approval = self.get_approval_by_request_id(request_id)

        if approval and approval.status == ApprovalStatus.PENDING:
            approval.status = ApprovalStatus.APPROVED
            approval.approved_by = approved_by
            approval.approved_at = datetime.utcnow()
            approval.execution_status = ExecutionStatus.NOT_STARTED

            if execution_method:
                approval.execution_method = execution_method
            else:
                # Auto-select method based on user count
                approval.execution_method = (
                    ExecutionMethod.MAPREDUCE if approval.user_count > 100
                    else ExecutionMethod.RESTLET
                )

            self.session.commit()
            self.session.refresh(approval)
            logger.info(f"Approved request {request_id} by {approved_by}")
            return approval

        return None

    def reject_request(
        self,
        request_id: str,
        rejected_by: str,
        rejection_reason: str
    ) -> DeactivationApproval | None:
        """Reject a deactivation request"""
        approval = self.get_approval_by_request_id(request_id)

        if approval and approval.status == ApprovalStatus.PENDING:
            approval.status = ApprovalStatus.REJECTED
            approval.rejected_by = rejected_by
            approval.rejected_at = datetime.utcnow()
            approval.rejection_reason = rejection_reason

            self.session.commit()
            self.session.refresh(approval)
            logger.info(f"Rejected request {request_id} by {rejected_by}: {rejection_reason}")
            return approval

        return None

    def expire_old_approvals(self) -> int:
        """Mark expired pending approvals as EXPIRED"""
        expired_approvals = self.get_expired_approvals()
        count = 0

        for approval in expired_approvals:
            approval.status = ApprovalStatus.EXPIRED
            count += 1

        if count > 0:
            self.session.commit()
            logger.info(f"Marked {count} approval requests as expired")

        return count

    def start_execution(
        self,
        request_id: str,
        execution_method: ExecutionMethod
    ) -> DeactivationApproval | None:
        """Mark approval execution as started"""
        approval = self.get_approval_by_request_id(request_id)

        if approval and approval.status == ApprovalStatus.APPROVED:
            approval.execution_status = ExecutionStatus.IN_PROGRESS
            approval.execution_method = execution_method
            approval.execution_started_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(approval)
            logger.info(f"Started execution for request {request_id} using {execution_method}")
            return approval

        return None

    def complete_execution(
        self,
        request_id: str,
        users_deactivated: int,
        users_failed: int,
        execution_errors: list[dict] | None = None
    ) -> DeactivationApproval | None:
        """Mark approval execution as completed"""
        approval = self.get_approval_by_request_id(request_id)

        if approval:
            approval.execution_status = (
                ExecutionStatus.COMPLETED if users_failed == 0
                else ExecutionStatus.PARTIAL if users_deactivated > 0
                else ExecutionStatus.FAILED
            )
            approval.execution_completed_at = datetime.utcnow()
            approval.users_deactivated = users_deactivated
            approval.users_failed = users_failed

            if execution_errors:
                approval.execution_errors = execution_errors

            self.session.commit()
            self.session.refresh(approval)
            logger.info(f"Completed execution for request {request_id}: {users_deactivated} successful, {users_failed} failed")
            return approval

        return None

    def fail_execution(
        self,
        request_id: str,
        error_message: str
    ) -> DeactivationApproval | None:
        """Mark approval execution as failed"""
        approval = self.get_approval_by_request_id(request_id)

        if approval:
            approval.execution_status = ExecutionStatus.FAILED
            approval.execution_completed_at = datetime.utcnow()
            approval.execution_errors = {'error': error_message}

            self.session.commit()
            self.session.refresh(approval)
            logger.error(f"Execution failed for request {request_id}: {error_message}")
            return approval

        return None

    def get_approval_statistics(self, days: int = 30) -> dict[str, Any]:
        """Get approval statistics for the last N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.session.query(DeactivationApproval).filter(
            DeactivationApproval.requested_at >= cutoff_date
        )

        total = query.count()

        # Count by approval status
        status_counts = {}
        for status in ApprovalStatus:
            count = query.filter(DeactivationApproval.status == status).count()
            status_counts[status.value] = count

        # Count by execution status
        execution_counts = {}
        for status in ExecutionStatus:
            count = query.filter(DeactivationApproval.execution_status == status).count()
            execution_counts[status.value] = count

        # Calculate totals
        total_users_requested = sum(a.user_count for a in query.all())
        total_users_deactivated = sum(a.users_deactivated or 0 for a in query.all())
        total_users_failed = sum(a.users_failed or 0 for a in query.all())

        return {
            'period_days': days,
            'total_requests': total,
            'status_breakdown': status_counts,
            'execution_breakdown': execution_counts,
            'total_users_requested': total_users_requested,
            'total_users_deactivated': total_users_deactivated,
            'total_users_failed': total_users_failed,
            'approval_rate': (status_counts.get('APPROVED', 0) / total * 100) if total > 0 else 0,
            'success_rate': (total_users_deactivated / total_users_requested * 100) if total_users_requested > 0 else 0
        }

    def get_recent_approvals(self, hours: int = 24, limit: int | None = None) -> list[DeactivationApproval]:
        """Get approvals from the last N hours"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        query = self.session.query(DeactivationApproval).filter(
            DeactivationApproval.requested_at >= cutoff_date
        ).order_by(desc(DeactivationApproval.requested_at))

        if limit:
            query = query.limit(limit)

        return query.all()
