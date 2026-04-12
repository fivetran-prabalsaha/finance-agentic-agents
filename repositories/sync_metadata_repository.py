"""
Sync Metadata Repository - CRUD operations for data collection sync metadata

Handles tracking of autonomous collection agent sync jobs
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from models.database import SyncMetadata, SyncStatus, SyncType

logger = logging.getLogger(__name__)


class SyncMetadataRepository:
    """Repository for SyncMetadata data access"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_sync(self, sync_data: dict[str, Any]) -> SyncMetadata:
        """
        Create a new sync metadata record

        Args:
            sync_data: Dictionary with sync fields

        Returns:
            Created SyncMetadata object
        """
        sync = SyncMetadata(
            sync_type=SyncType[sync_data['sync_type'].upper()],
            system_name=sync_data['system_name'],
            status=SyncStatus[sync_data.get('status', 'PENDING').upper()],
            started_at=sync_data.get('started_at', datetime.utcnow()),
            triggered_by=sync_data.get('triggered_by', 'scheduler'),
            extra_metadata=sync_data.get('metadata', {})
        )

        self.session.add(sync)
        self.session.commit()
        self.session.refresh(sync)

        logger.info(f"Created sync record: {sync.id} ({sync.sync_type.value})")
        return sync

    def update_sync(
        self,
        sync_id: str,
        updates: dict[str, Any]
    ) -> SyncMetadata | None:
        """
        Update a sync metadata record

        Args:
            sync_id: Sync UUID
            updates: Dictionary of fields to update

        Returns:
            Updated SyncMetadata object or None
        """
        sync = self.session.query(SyncMetadata).filter(
            SyncMetadata.id == sync_id
        ).first()

        if not sync:
            logger.warning(f"Sync not found: {sync_id}")
            return None

        # Update fields
        for key, value in updates.items():
            if key == 'status' and isinstance(value, str):
                value = SyncStatus[value.upper()]
            if hasattr(sync, key):
                setattr(sync, key, value)

        sync.updated_at = datetime.utcnow()

        # Calculate duration if completing
        if updates.get('completed_at') and sync.started_at:
            sync.duration_seconds = (
                updates['completed_at'] - sync.started_at
            ).total_seconds()

        self.session.commit()
        self.session.refresh(sync)

        logger.info(f"Updated sync: {sync.id} - {sync.status.value}")
        return sync

    def get_sync_by_id(self, sync_id: str) -> SyncMetadata | None:
        """
        Get sync by ID

        Args:
            sync_id: Sync UUID

        Returns:
            SyncMetadata object or None
        """
        return self.session.query(SyncMetadata).filter(
            SyncMetadata.id == sync_id
        ).first()

    def get_last_successful_sync(
        self,
        system_name: str,
        sync_type: str | None = None
    ) -> SyncMetadata | None:
        """
        Get the last successful sync for a system

        Args:
            system_name: System name (e.g., 'netsuite')
            sync_type: Optional sync type filter

        Returns:
            SyncMetadata object or None
        """
        query = self.session.query(SyncMetadata).filter(
            and_(
                SyncMetadata.system_name == system_name,
                SyncMetadata.status == SyncStatus.SUCCESS
            )
        )

        if sync_type:
            query = query.filter(
                SyncMetadata.sync_type == SyncType[sync_type.upper()]
            )

        return query.order_by(desc(SyncMetadata.completed_at)).first()

    def get_recent_syncs(
        self,
        system_name: str | None = None,
        limit: int = 10
    ) -> list[SyncMetadata]:
        """
        Get recent syncs

        Args:
            system_name: Optional system filter
            limit: Maximum number of records

        Returns:
            List of SyncMetadata objects
        """
        query = self.session.query(SyncMetadata)

        if system_name:
            query = query.filter(SyncMetadata.system_name == system_name)

        return query.order_by(desc(SyncMetadata.started_at)).limit(limit).all()

    def get_failed_syncs(
        self,
        system_name: str | None = None,
        since: datetime | None = None
    ) -> list[SyncMetadata]:
        """
        Get failed syncs

        Args:
            system_name: Optional system filter
            since: Optional time filter

        Returns:
            List of failed SyncMetadata objects
        """
        query = self.session.query(SyncMetadata).filter(
            SyncMetadata.status == SyncStatus.FAILED
        )

        if system_name:
            query = query.filter(SyncMetadata.system_name == system_name)

        if since:
            query = query.filter(SyncMetadata.started_at >= since)

        return query.order_by(desc(SyncMetadata.started_at)).all()

    def get_sync_statistics(
        self,
        system_name: str,
        days: int = 7
    ) -> dict[str, Any]:
        """
        Get sync statistics for a time period

        Args:
            system_name: System name
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        since = datetime.utcnow() - timedelta(days=days)

        syncs = self.session.query(SyncMetadata).filter(
            and_(
                SyncMetadata.system_name == system_name,
                SyncMetadata.started_at >= since
            )
        ).all()

        if not syncs:
            return {
                'total_syncs': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
                'total_users_synced': 0
            }

        successful = [s for s in syncs if s.status == SyncStatus.SUCCESS]
        failed = [s for s in syncs if s.status == SyncStatus.FAILED]

        completed_syncs = [s for s in syncs if s.duration_seconds is not None]
        avg_duration = (
            sum(s.duration_seconds for s in completed_syncs) / len(completed_syncs)
            if completed_syncs else 0.0
        )

        return {
            'total_syncs': len(syncs),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(syncs) * 100 if syncs else 0.0,
            'avg_duration': round(avg_duration, 2),
            'total_users_synced': sum(s.users_synced or 0 for s in successful),
            'total_roles_synced': sum(s.roles_synced or 0 for s in successful),
            'total_violations_detected': sum(s.violations_detected or 0 for s in successful)
        }

    def cleanup_old_syncs(self, days: int = 30) -> int:
        """
        Delete sync records older than specified days

        Args:
            days: Age threshold in days

        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        count = self.session.query(SyncMetadata).filter(
            SyncMetadata.created_at < cutoff
        ).delete()

        self.session.commit()

        logger.info(f"Cleaned up {count} old sync records (older than {days} days)")
        return count
