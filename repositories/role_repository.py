"""
Role Repository - CRUD operations for roles

Handles all database operations for Role model
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.database import Role

logger = logging.getLogger(__name__)


class RoleRepository:
    """Repository for Role data access"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def create_role(self, role_data: dict[str, Any]) -> Role:
        """
        Create a new role

        Args:
            role_data: Dictionary with role fields

        Returns:
            Created Role object
        """
        role = Role(
            role_id=role_data['role_id'],
            role_name=role_data['role_name'],
            is_custom=role_data.get('is_custom', False),
            description=role_data.get('description'),
            permission_count=role_data.get('permission_count', 0),
            permissions=role_data.get('permissions', [])
        )

        self.session.add(role)
        self.session.commit()
        self.session.refresh(role)

        logger.info(f"Created role: {role.role_name}")
        return role

    def get_role_by_id(self, role_id: str) -> Role | None:
        """
        Get role by role_id

        Args:
            role_id: NetSuite role ID

        Returns:
            Role object or None
        """
        return self.session.query(Role).filter(Role.role_id == role_id).first()

    def get_role_by_uuid(self, uuid: str) -> Role | None:
        """
        Get role by UUID (database ID)

        Args:
            uuid: Role UUID

        Returns:
            Role object or None
        """
        return self.session.query(Role).filter(Role.id == uuid).first()

    def get_role_by_name(self, role_name: str) -> Role | None:
        """
        Get role by name

        Args:
            role_name: Role name

        Returns:
            Role object or None
        """
        return self.session.query(Role).filter(Role.role_name == role_name).first()

    def get_all_roles(self, is_custom: bool | None = None) -> list[Role]:
        """
        Get all roles with optional filter

        Args:
            is_custom: Filter by custom role flag

        Returns:
            List of Role objects
        """
        query = self.session.query(Role)

        if is_custom is not None:
            query = query.filter(Role.is_custom == is_custom)

        return query.order_by(Role.role_name).all()

    def upsert_role(self, role_data: dict[str, Any]) -> Role:
        """
        Create or update role (upsert)

        Args:
            role_data: Dictionary with role fields

        Returns:
            Role object (created or updated)
        """
        role = self.get_role_by_id(role_data['role_id'])

        if role:
            # Update existing role
            role.role_name = role_data.get('role_name', role.role_name)
            role.is_custom = role_data.get('is_custom', role.is_custom)
            role.description = role_data.get('description', role.description)
            role.permission_count = role_data.get('permission_count', role.permission_count)
            role.permissions = role_data.get('permissions', role.permissions)
            role.updated_at = datetime.utcnow()

            logger.info(f"Updated role: {role.role_name}")
        else:
            # Create new role
            role = self.create_role(role_data)

        self.session.commit()
        return role

    def bulk_upsert_roles(self, roles_data: list[dict[str, Any]]) -> int:
        """
        Bulk create or update roles

        Args:
            roles_data: List of role data dictionaries

        Returns:
            Number of roles processed
        """
        count = 0
        for role_data in roles_data:
            try:
                self.upsert_role(role_data)
                count += 1
            except Exception as e:
                logger.error(f"Error upserting role {role_data.get('role_name')}: {str(e)}")
                self.session.rollback()

        logger.info(f"Bulk upserted {count}/{len(roles_data)} roles")
        return count

    def search_roles(self, search_term: str, limit: int = 100) -> list[Role]:
        """
        Search roles by name

        Args:
            search_term: Search string
            limit: Maximum results

        Returns:
            List of matching Role objects
        """
        search_pattern = f"%{search_term}%"

        return (
            self.session.query(Role)
            .filter(Role.role_name.ilike(search_pattern))
            .limit(limit)
            .all()
        )

    def get_roles_with_high_permissions(self, min_permissions: int = 100) -> list[Role]:
        """
        Get roles with many permissions

        Args:
            min_permissions: Minimum permission count

        Returns:
            List of Role objects
        """
        return (
            self.session.query(Role)
            .filter(Role.permission_count >= min_permissions)
            .order_by(Role.permission_count.desc())
            .all()
        )

    def delete_role(self, role_id: str):
        """
        Delete a role

        Args:
            role_id: Role ID to delete
        """
        role = self.get_role_by_id(role_id)
        if role:
            self.session.delete(role)
            self.session.commit()
            logger.info(f"Deleted role: {role.role_name}")

    def get_role_count(self, is_custom: bool | None = None) -> int:
        """
        Get total role count

        Args:
            is_custom: Filter by custom role flag

        Returns:
            Number of roles
        """
        query = self.session.query(Role)

        if is_custom is not None:
            query = query.filter(Role.is_custom == is_custom)

        return query.count()

    def get_admin_roles(self) -> list[Role]:
        """
        Get roles with 'admin' in the name

        Returns:
            List of Role objects
        """
        return (
            self.session.query(Role)
            .filter(Role.role_name.ilike('%admin%'))
            .all()
        )

    def get_finance_roles(self) -> list[Role]:
        """
        Get finance-related roles

        Returns:
            List of Role objects
        """
        keywords = ['finance', 'controller', 'accounting', 'ap', 'ar', 'treasury']

        filters = [Role.role_name.ilike(f'%{keyword}%') for keyword in keywords]

        return (
            self.session.query(Role)
            .filter(or_(*filters))
            .all()
        )
