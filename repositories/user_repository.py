"""
User Repository - CRUD operations for users and user-role assignments

Handles all database operations for User and UserRole models
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from models.database import Role, User, UserRole, UserStatus

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for User data access"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_user(self, user_data: dict[str, Any]) -> User:
        """
        Create a new user

        Args:
            user_data: Dictionary with user fields

        Returns:
            Created User object
        """
        user = User(
            user_id=user_data['user_id'],
            internal_id=user_data.get('internal_id'),
            name=user_data['name'],
            email=user_data['email'],
            status=UserStatus[user_data.get('status', 'ACTIVE')],
            department=user_data.get('department'),
            subsidiary=user_data.get('subsidiary'),
            employee_id=user_data.get('employee_id'),
            last_login=user_data.get('last_login'),

            # Context fields for SOD analysis
            job_function=user_data.get('job_function'),
            business_unit=user_data.get('business_unit'),
            title=user_data.get('title'),
            supervisor=user_data.get('supervisor'),
            supervisor_id=user_data.get('supervisor_id'),
            location=user_data.get('location'),
            hire_date=user_data.get('hire_date'),

            synced_at=datetime.utcnow()
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        logger.info(f"Created user: {user.email}")
        return user

    def get_user_by_id(self, user_id: str) -> User | None:
        """
        Get user by user_id

        Args:
            user_id: NetSuite user ID

        Returns:
            User object or None
        """
        return self.session.query(User).filter(User.user_id == user_id).first()

    def get_user_by_email(self, email: str) -> User | None:
        """
        Get user by email (case-insensitive)

        Args:
            email: User email address

        Returns:
            User object or None
        """
        return self.session.query(User).filter(User.email.ilike(email)).first()

    def get_user_by_uuid(self, uuid: str) -> User | None:
        """
        Get user by UUID (database ID)

        Args:
            uuid: User UUID

        Returns:
            User object or None
        """
        return self.session.query(User).filter(User.id == uuid).first()

    def get_all_users(
        self,
        status: UserStatus | None = None,
        department: str | None = None,
        limit: int = 1000,
        offset: int = 0
    ) -> list[User]:
        """
        Get all users with optional filters

        Args:
            status: Filter by user status
            department: Filter by department
            limit: Maximum number of users to return
            offset: Pagination offset

        Returns:
            List of User objects
        """
        query = self.session.query(User)

        if status:
            query = query.filter(User.status == status)

        if department:
            query = query.filter(User.department == department)

        return query.order_by(User.name).limit(limit).offset(offset).all()

    def upsert_user(self, user_data: dict[str, Any]) -> User:
        """
        Create or update user (upsert)

        Args:
            user_data: Dictionary with user fields

        Returns:
            User object (created or updated)
        """
        # Check by email first (unique constraint in DB)
        user = self.get_user_by_email(user_data['email'])

        # If not found by email, check by user_id
        if not user:
            user = self.get_user_by_id(user_data['user_id'])

        if user:
            # Update existing user
            user.user_id = user_data.get('user_id', user.user_id)
            user.name = user_data.get('name', user.name)
            user.email = user_data.get('email', user.email)
            user.status = UserStatus[user_data.get('status', user.status.value)]
            user.department = user_data.get('department', user.department)
            user.subsidiary = user_data.get('subsidiary', user.subsidiary)
            user.employee_id = user_data.get('employee_id', user.employee_id)
            user.internal_id = user_data.get('internal_id', user.internal_id)
            user.last_login = user_data.get('last_login', user.last_login)

            # Update context fields for SOD analysis
            user.job_function = user_data.get('job_function', user.job_function)
            user.business_unit = user_data.get('business_unit', user.business_unit)
            user.title = user_data.get('title', user.title)
            user.supervisor = user_data.get('supervisor', user.supervisor)
            user.supervisor_id = user_data.get('supervisor_id', user.supervisor_id)
            user.location = user_data.get('location', user.location)
            user.hire_date = user_data.get('hire_date', user.hire_date)

            user.synced_at = datetime.utcnow()
            user.updated_at = datetime.utcnow()

            logger.info(f"Updated user: {user.email}")
        else:
            # Create new user
            user = self.create_user(user_data)

        self.session.commit()
        return user

    def bulk_upsert_users(self, users_data: list[dict[str, Any]]) -> int:
        """
        Bulk create or update users

        Args:
            users_data: List of user data dictionaries

        Returns:
            Number of users processed
        """
        count = 0
        for user_data in users_data:
            try:
                self.upsert_user(user_data)
                count += 1
            except Exception as e:
                logger.error(f"Error upserting user {user_data.get('email')}: {str(e)}")
                self.session.rollback()

        logger.info(f"Bulk upserted {count}/{len(users_data)} users")
        return count

    def get_users_with_roles(
        self,
        status: UserStatus | None = None,
        min_roles: int = 0
    ) -> list[User]:
        """
        Get users with their roles loaded

        Args:
            status: Filter by user status
            min_roles: Minimum number of roles

        Returns:
            List of User objects with roles
        """
        query = (
            self.session.query(User)
            .options(joinedload(User.user_roles).joinedload(UserRole.role))
        )

        if status:
            query = query.filter(User.status == status)

        users = query.all()

        if min_roles > 0:
            users = [u for u in users if len(u.user_roles) >= min_roles]

        return users

    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by: str | None = None,
        notes: str | None = None
    ) -> UserRole:
        """
        Assign a role to a user

        Args:
            user_id: User UUID
            role_id: Role UUID
            assigned_by: Who assigned the role
            notes: Optional notes

        Returns:
            UserRole object
        """
        # Check if already assigned
        existing = (
            self.session.query(UserRole)
            .filter(and_(UserRole.user_id == user_id, UserRole.role_id == role_id))
            .first()
        )

        if existing:
            logger.info("Role already assigned to user")
            return existing

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            notes=notes
        )

        self.session.add(user_role)
        self.session.commit()
        self.session.refresh(user_role)

        logger.info(f"Assigned role {role_id} to user {user_id}")
        return user_role

    def remove_role_from_user(self, user_id: str, role_id: str):
        """
        Remove a role from a user

        Args:
            user_id: User UUID
            role_id: Role UUID
        """
        user_role = (
            self.session.query(UserRole)
            .filter(and_(UserRole.user_id == user_id, UserRole.role_id == role_id))
            .first()
        )

        if user_role:
            self.session.delete(user_role)
            self.session.commit()
            logger.info(f"Removed role {role_id} from user {user_id}")

    def get_user_roles(self, user_id: str) -> list[Role]:
        """
        Get all roles for a user

        Args:
            user_id: User UUID

        Returns:
            List of Role objects
        """
        user = (
            self.session.query(User)
            .filter(User.id == user_id)
            .options(joinedload(User.user_roles).joinedload(UserRole.role))
            .first()
        )

        if not user:
            return []

        return [ur.role for ur in user.user_roles]

    def get_high_risk_users(self, min_roles: int = 3) -> list[User]:
        """
        Get users with multiple roles (high SOD risk)

        Args:
            min_roles: Minimum number of roles to be considered high risk

        Returns:
            List of User objects with roles loaded
        """
        users = self.get_users_with_roles(status=UserStatus.ACTIVE)
        high_risk = [u for u in users if len(u.user_roles) >= min_roles]

        logger.info(f"Found {len(high_risk)} high-risk users with {min_roles}+ roles")
        return high_risk

    def search_users(self, search_term: str, limit: int = 100) -> list[User]:
        """
        Search users by name or email

        Args:
            search_term: Search string
            limit: Maximum results

        Returns:
            List of matching User objects
        """
        search_pattern = f"%{search_term}%"

        return (
            self.session.query(User)
            .filter(
                or_(
                    User.name.ilike(search_pattern),
                    User.email.ilike(search_pattern)
                )
            )
            .limit(limit)
            .all()
        )

    def delete_user(self, user_id: str):
        """
        Delete a user (and cascade delete user_roles)

        Args:
            user_id: User ID to delete
        """
        user = self.get_user_by_id(user_id)
        if user:
            self.session.delete(user)
            self.session.commit()
            logger.info(f"Deleted user: {user.email}")

    def get_user_count(self, status: UserStatus | None = None) -> int:
        """
        Get total user count

        Args:
            status: Filter by status

        Returns:
            Number of users
        """
        query = self.session.query(User)

        if status:
            query = query.filter(User.status == status)

        return query.count()
