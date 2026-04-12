"""
User Reconciliation Repository

Data access layer for Okta-NetSuite user reconciliation records
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.database import ReconciliationStatus, RiskLevel, UserReconciliation

logger = logging.getLogger(__name__)


class UserReconciliationRepository:
    """Repository for user reconciliation operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_reconciliation(self, recon_data: dict[str, Any]) -> UserReconciliation:
        """Create a new reconciliation record"""
        reconciliation = UserReconciliation(
            netsuite_user_id=recon_data.get('netsuite_user_id'),
            okta_user_id=recon_data.get('okta_user_id'),
            email=recon_data['email'],
            netsuite_status=recon_data.get('netsuite_status'),
            okta_status=recon_data.get('okta_status'),
            reconciliation_status=ReconciliationStatus[recon_data['reconciliation_status']],
            discrepancy_reason=recon_data.get('discrepancy_reason'),
            risk_level=RiskLevel[recon_data['risk_level']] if recon_data.get('risk_level') else None,
            requires_action=recon_data.get('requires_action', False),
            action_required=recon_data.get('action_required'),
            scan_id=recon_data.get('scan_id')
        )

        self.session.add(reconciliation)
        self.session.commit()
        self.session.refresh(reconciliation)

        logger.info(f"Created reconciliation record for {reconciliation.email}: {reconciliation.reconciliation_status}")
        return reconciliation

    def get_reconciliation_by_id(self, recon_id: str) -> UserReconciliation | None:
        """Get reconciliation by UUID"""
        return self.session.query(UserReconciliation).filter(
            UserReconciliation.id == recon_id
        ).first()

    def get_reconciliations_by_email(self, email: str, limit: int | None = None) -> list[UserReconciliation]:
        """Get reconciliation records for a specific email"""
        query = self.session.query(UserReconciliation).filter(
            UserReconciliation.email == email
        ).order_by(desc(UserReconciliation.reconciled_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_latest_reconciliation_by_email(self, email: str) -> UserReconciliation | None:
        """Get the most recent reconciliation record for an email"""
        return self.session.query(UserReconciliation).filter(
            UserReconciliation.email == email
        ).order_by(desc(UserReconciliation.reconciled_at)).first()

    def get_reconciliations_by_status(
        self,
        status: ReconciliationStatus,
        limit: int | None = None
    ) -> list[UserReconciliation]:
        """Get reconciliations by status"""
        query = self.session.query(UserReconciliation).filter(
            UserReconciliation.reconciliation_status == status
        ).order_by(desc(UserReconciliation.reconciled_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_orphaned_users(self, risk_level: RiskLevel | None = None) -> list[UserReconciliation]:
        """Get orphaned users (active in NetSuite but deprovisioned in Okta)"""
        query = self.session.query(UserReconciliation).filter(
            UserReconciliation.reconciliation_status == ReconciliationStatus.ORPHANED
        )

        if risk_level:
            query = query.filter(UserReconciliation.risk_level == risk_level)

        return query.order_by(desc(UserReconciliation.reconciled_at)).all()

    def get_high_risk_discrepancies(self) -> list[UserReconciliation]:
        """Get all high-risk reconciliation discrepancies"""
        return self.session.query(UserReconciliation).filter(
            UserReconciliation.risk_level == RiskLevel.HIGH
        ).order_by(desc(UserReconciliation.reconciled_at)).all()

    def get_reconciliations_requiring_action(self, limit: int | None = None) -> list[UserReconciliation]:
        """Get reconciliations that require action"""
        query = self.session.query(UserReconciliation).filter(
            UserReconciliation.requires_action
        ).order_by(
            UserReconciliation.risk_level.desc(),
            desc(UserReconciliation.reconciled_at)
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_reconciliations_by_scan(self, scan_id: str) -> list[UserReconciliation]:
        """Get all reconciliations from a specific scan"""
        return self.session.query(UserReconciliation).filter(
            UserReconciliation.scan_id == scan_id
        ).order_by(UserReconciliation.email).all()

    def get_recent_reconciliations(self, hours: int = 24, limit: int | None = None) -> list[UserReconciliation]:
        """Get reconciliations from the last N hours"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        query = self.session.query(UserReconciliation).filter(
            UserReconciliation.reconciled_at >= cutoff_date
        ).order_by(desc(UserReconciliation.reconciled_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_reconciliation_summary(self, scan_id: str | None = None) -> dict[str, Any]:
        """Get summary statistics for reconciliations"""
        query = self.session.query(UserReconciliation)

        if scan_id:
            query = query.filter(UserReconciliation.scan_id == scan_id)

        total = query.count()

        # Count by reconciliation status
        status_counts = {}
        for status in ReconciliationStatus:
            count = query.filter(UserReconciliation.reconciliation_status == status).count()
            status_counts[status.value] = count

        # Count by risk level
        risk_counts = {}
        for risk in RiskLevel:
            count = query.filter(UserReconciliation.risk_level == risk).count()
            risk_counts[risk.value] = count

        # Action required count
        action_required = query.filter(UserReconciliation.requires_action).count()

        return {
            'total_reconciliations': total,
            'status_breakdown': status_counts,
            'risk_breakdown': risk_counts,
            'action_required': action_required,
            'matched': status_counts.get('MATCHED', 0),
            'orphaned': status_counts.get('ORPHANED', 0),
            'missing_in_okta': status_counts.get('MISSING_IN_OKTA', 0),
            'missing_in_netsuite': status_counts.get('MISSING_IN_NETSUITE', 0),
            'status_mismatch': status_counts.get('STATUS_MISMATCH', 0),
            'high_risk': risk_counts.get('HIGH', 0),
            'medium_risk': risk_counts.get('MEDIUM', 0),
            'low_risk': risk_counts.get('LOW', 0)
        }

    def bulk_create_reconciliations(self, reconciliations_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Bulk create reconciliation records"""
        created = 0
        errors = []

        for recon_data in reconciliations_data:
            try:
                self.create_reconciliation(recon_data)
                created += 1
            except Exception as e:
                logger.error(f"Error creating reconciliation for {recon_data.get('email')}: {str(e)}")
                errors.append({
                    'email': recon_data.get('email'),
                    'error': str(e)
                })

        return {
            'created': created,
            'total': len(reconciliations_data),
            'errors': errors
        }

    def delete_old_reconciliations(self, days: int = 90) -> int:
        """Delete reconciliation records older than N days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = self.session.query(UserReconciliation).filter(
            UserReconciliation.reconciled_at < cutoff_date
        ).delete()

        self.session.commit()
        logger.info(f"Deleted {deleted} reconciliation records older than {days} days")
        return deleted

    def update_reconciliation_status(
        self,
        recon_id: str,
        status: ReconciliationStatus,
        requires_action: bool | None = None,
        action_required: str | None = None
    ) -> UserReconciliation | None:
        """Update reconciliation status"""
        recon = self.get_reconciliation_by_id(recon_id)

        if recon:
            recon.reconciliation_status = status

            if requires_action is not None:
                recon.requires_action = requires_action

            if action_required is not None:
                recon.action_required = action_required

            self.session.commit()
            self.session.refresh(recon)
            logger.info(f"Updated reconciliation {recon_id} status to {status}")
            return recon

        return None

    def get_reconciliations_for_deactivation(self) -> list[UserReconciliation]:
        """Get reconciliations that recommend deactivation in NetSuite"""
        return self.session.query(UserReconciliation).filter(
            and_(
                UserReconciliation.requires_action,
                UserReconciliation.action_required.in_(['DEACTIVATE_NETSUITE', 'DEACTIVATE']),
                UserReconciliation.risk_level.in_([RiskLevel.HIGH, RiskLevel.MEDIUM])
            )
        ).order_by(
            UserReconciliation.risk_level.desc(),
            desc(UserReconciliation.reconciled_at)
        ).all()
