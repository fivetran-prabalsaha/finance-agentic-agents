"""
Job Role Mapping Repository

Handles database operations for job_role_mappings table
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from models.database import JobRoleMapping

logger = logging.getLogger(__name__)


class JobRoleMappingRepository:
    """Repository for job role mappings"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    def get_by_job_title(self, job_title: str) -> JobRoleMapping | None:
        """
        Get job role mapping by job title (case-insensitive)

        Args:
            job_title: Job title to search for

        Returns:
            JobRoleMapping or None
        """
        if not job_title:
            return None

        try:
            # Try exact match first (case-insensitive)
            mapping = self.session.query(JobRoleMapping).filter(
                JobRoleMapping.job_title.ilike(job_title.strip())
            ).first()

            if mapping:
                logger.debug(f"Found job role mapping for: {job_title}")
                return mapping

            # Try partial match (for variations like "Manager" vs "Accounting Manager")
            mapping = self.session.query(JobRoleMapping).filter(
                JobRoleMapping.job_title.ilike(f"%{job_title.strip()}%")
            ).first()

            if mapping:
                logger.debug(f"Found partial job role mapping for: {job_title} -> {mapping.job_title}")
                return mapping

            logger.debug(f"No job role mapping found for: {job_title}")
            return None

        except Exception as e:
            logger.error(f"Error fetching job role mapping: {str(e)}")
            return None

    def get_by_id(self, mapping_id: str) -> JobRoleMapping | None:
        """Get job role mapping by ID"""
        try:
            return self.session.query(JobRoleMapping).filter(
                JobRoleMapping.id == mapping_id
            ).first()
        except Exception as e:
            logger.error(f"Error fetching job role mapping by ID: {str(e)}")
            return None

    def get_all_active(self) -> list[JobRoleMapping]:
        """Get all active job role mappings"""
        try:
            return self.session.query(JobRoleMapping).filter(
                JobRoleMapping.is_active
            ).all()
        except Exception as e:
            logger.error(f"Error fetching active job role mappings: {str(e)}")
            return []

    def check_role_combination_acceptable(
        self,
        job_title: str,
        role_names: list[str]
    ) -> dict[str, Any]:
        """
        Check if role combination is acceptable for job title

        Args:
            job_title: Job title
            role_names: List of role names assigned to user

        Returns:
            Dictionary with:
            - is_acceptable: bool
            - requires_controls: bool
            - typical_controls: List[str]
            - business_justification: str
            - approval_required: str (optional)
        """
        mapping = self.get_by_job_title(job_title)

        if not mapping:
            return {
                "is_acceptable": False,
                "requires_controls": False,
                "typical_controls": [],
                "business_justification": "",
                "reason": f"No job role mapping found for: {job_title}"
            }

        # Check if role combination matches acceptable combinations
        acceptable_combos = mapping.acceptable_role_combinations or []
        role_set = set(role_names)

        for combo in acceptable_combos:
            combo_roles = set(combo.get('roles', []))

            # Check if roles match
            if role_set == combo_roles or role_set.issubset(combo_roles):
                return {
                    "is_acceptable": True,
                    "requires_controls": combo.get('requires_compensating_controls', False),
                    "typical_controls": combo.get('typical_controls', mapping.typical_controls or []),
                    "business_justification": combo.get('business_justification', mapping.business_justification or ""),
                    "approval_required": combo.get('approval_required', ''),
                    "matched_combination": combo
                }

        return {
            "is_acceptable": False,
            "requires_controls": True,
            "typical_controls": mapping.typical_controls or [],
            "business_justification": "",
            "reason": f"Role combination not in acceptable list for {job_title}",
            "expected_roles": [combo.get('roles', []) for combo in acceptable_combos]
        }

    def create(self, data: dict[str, Any]) -> JobRoleMapping:
        """Create new job role mapping"""
        try:
            mapping = JobRoleMapping(**data)
            self.session.add(mapping)
            self.session.commit()
            self.session.refresh(mapping)
            logger.info(f"Created job role mapping: {mapping.job_title}")
            return mapping
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating job role mapping: {str(e)}")
            raise

    def update(self, mapping_id: str, data: dict[str, Any]) -> JobRoleMapping | None:
        """Update job role mapping"""
        try:
            mapping = self.get_by_id(mapping_id)
            if not mapping:
                return None

            for key, value in data.items():
                if hasattr(mapping, key):
                    setattr(mapping, key, value)

            self.session.commit()
            self.session.refresh(mapping)
            logger.info(f"Updated job role mapping: {mapping.job_title}")
            return mapping
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating job role mapping: {str(e)}")
            raise
