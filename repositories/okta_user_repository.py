"""
Okta User Repository

Data access layer for Okta user data
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from models.database import OktaUser, OktaUserStatus

logger = logging.getLogger(__name__)


class OktaUserRepository:
    """Repository for Okta user operations"""

    def __init__(self, session: Session):
        self.session = session

    def create_user(self, user_data: dict[str, Any]) -> OktaUser:
        """Create a new Okta user"""
        user = OktaUser(
            okta_id=user_data['okta_id'],
            email=user_data['email'],
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            status=OktaUserStatus[user_data['status']],
            login=user_data.get('login'),
            activated=user_data.get('activated'),
            status_changed=user_data.get('status_changed'),
            last_login=user_data.get('last_login'),
            last_updated=user_data.get('last_updated'),
            password_changed=user_data.get('password_changed'),
            department=user_data.get('department'),
            title=user_data.get('title'),
            employee_number=user_data.get('employee_number'),
            manager=user_data.get('manager'),
            manager_id=user_data.get('manager_id'),
            okta_groups=user_data.get('okta_groups', [])
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        logger.info(f"Created Okta user: {user.email} (ID: {user.id})")
        return user

    def get_user_by_id(self, user_id: str) -> OktaUser | None:
        """Get user by UUID"""
        return self.session.query(OktaUser).filter(OktaUser.id == user_id).first()

    def get_user_by_okta_id(self, okta_id: str) -> OktaUser | None:
        """Get user by Okta ID"""
        return self.session.query(OktaUser).filter(OktaUser.okta_id == okta_id).first()

    def get_user_by_email(self, email: str) -> OktaUser | None:
        """Get user by email"""
        return self.session.query(OktaUser).filter(OktaUser.email == email).first()

    def upsert_user(self, user_data: dict[str, Any]) -> OktaUser:
        """Create or update Okta user"""
        existing_user = self.get_user_by_okta_id(user_data['okta_id'])

        if existing_user:
            # Update existing user
            existing_user.email = user_data['email']
            existing_user.first_name = user_data.get('first_name')
            existing_user.last_name = user_data.get('last_name')
            existing_user.status = OktaUserStatus[user_data['status']]
            existing_user.login = user_data.get('login')
            existing_user.activated = user_data.get('activated')
            existing_user.status_changed = user_data.get('status_changed')
            existing_user.last_login = user_data.get('last_login')
            existing_user.last_updated = user_data.get('last_updated')
            existing_user.password_changed = user_data.get('password_changed')
            existing_user.department = user_data.get('department')
            existing_user.title = user_data.get('title')
            existing_user.employee_number = user_data.get('employee_number')
            existing_user.manager = user_data.get('manager')
            existing_user.manager_id = user_data.get('manager_id')
            existing_user.okta_groups = user_data.get('okta_groups', [])
            existing_user.synced_at = datetime.utcnow()
            existing_user.updated_at = datetime.utcnow()

            self.session.commit()
            self.session.refresh(existing_user)

            logger.info(f"Updated Okta user: {existing_user.email}")
            return existing_user
        else:
            # Create new user
            return self.create_user(user_data)

    def bulk_upsert_users(self, users_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Bulk create/update Okta users"""
        created = 0
        updated = 0
        errors = []

        for user_data in users_data:
            try:
                existing = self.get_user_by_okta_id(user_data['okta_id'])
                if existing:
                    self.upsert_user(user_data)
                    updated += 1
                else:
                    self.upsert_user(user_data)
                    created += 1
            except Exception as e:
                logger.error(f"Error upserting Okta user {user_data.get('email')}: {str(e)}")
                errors.append({
                    'email': user_data.get('email'),
                    'error': str(e)
                })

        return {
            'created': created,
            'updated': updated,
            'total': len(users_data),
            'errors': errors
        }

    def get_all_users(self, status: OktaUserStatus | None = None, limit: int | None = None) -> list[OktaUser]:
        """Get all Okta users, optionally filtered by status"""
        query = self.session.query(OktaUser)

        if status:
            query = query.filter(OktaUser.status == status)

        query = query.order_by(desc(OktaUser.synced_at))

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_active_users(self) -> list[OktaUser]:
        """Get all active Okta users"""
        return self.get_all_users(status=OktaUserStatus.ACTIVE)

    def get_deprovisioned_users(self, days: int | None = None) -> list[OktaUser]:
        """Get deprovisioned users, optionally within the last N days"""
        query = self.session.query(OktaUser).filter(
            OktaUser.status == OktaUserStatus.DEPROVISIONED
        )

        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(OktaUser.status_changed >= cutoff_date)

        return query.order_by(desc(OktaUser.status_changed)).all()

    def get_suspended_users(self) -> list[OktaUser]:
        """Get all suspended Okta users"""
        return self.get_all_users(status=OktaUserStatus.SUSPENDED)

    def get_users_by_department(self, department: str) -> list[OktaUser]:
        """Get users by department"""
        return self.session.query(OktaUser).filter(
            OktaUser.department == department
        ).order_by(OktaUser.email).all()

    def get_stale_users(self, hours: int = 24) -> list[OktaUser]:
        """Get users not synced in the last N hours"""
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(OktaUser).filter(
            OktaUser.synced_at < cutoff_date
        ).order_by(OktaUser.synced_at).all()

    def get_user_count_by_status(self) -> dict[str, int]:
        """Get count of users by status"""
        results = {}
        for status in OktaUserStatus:
            count = self.session.query(OktaUser).filter(
                OktaUser.status == status
            ).count()
            results[status.value] = count
        return results

    def delete_user(self, user_id: str) -> bool:
        """Delete an Okta user"""
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            logger.info(f"Deleted Okta user: {user.email}")
            return True
        return False

    def update_sync_timestamp(self, user_id: str) -> bool:
        """Update the sync timestamp for a user"""
        user = self.get_user_by_id(user_id)
        if user:
            user.synced_at = datetime.utcnow()
            self.session.commit()
            return True
        return False
