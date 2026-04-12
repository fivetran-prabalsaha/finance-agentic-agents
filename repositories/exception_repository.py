"""
Exception Repository

Handles database operations for approved exceptions, controls, violations, and reviews
"""

import logging
import uuid
from datetime import date, datetime
from typing import Any

import sqlalchemy
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from models.approved_exception import (
    ApprovedExceptionModel,
    ExceptionControlModel,
    ExceptionReviewModel,
    ExceptionStatus,
    ExceptionViolationModel,
    ImplementationStatus,
    ReviewOutcome,
)

logger = logging.getLogger(__name__)


class ExceptionRepository:
    """Repository for exception management operations"""

    def __init__(self, session: Session):
        """
        Initialize repository with database session

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    # =========================================================================
    # APPROVED EXCEPTIONS - CREATE
    # =========================================================================

    def create_exception(
        self,
        user_id: uuid.UUID,
        user_name: str,
        role_ids: list[int],
        role_names: list[str],
        conflict_count: int,
        risk_score: float,
        business_justification: str,
        approved_by: str,
        **kwargs
    ) -> ApprovedExceptionModel:
        """
        Create a new approved exception

        Args:
            user_id: UUID of the user
            user_name: User's full name
            role_ids: List of role internal IDs
            role_names: List of role names
            conflict_count: Total number of conflicts
            risk_score: Risk score 0-100
            business_justification: Business reason for approval
            approved_by: Name of person who approved
            **kwargs: Additional optional fields

        Returns:
            Created ApprovedExceptionModel
        """
        try:
            # Generate exception code
            exception_code = self._generate_exception_code()

            exception = ApprovedExceptionModel(
                exception_code=exception_code,
                user_id=user_id,
                user_name=user_name,
                role_ids=role_ids,
                role_names=role_names,
                conflict_count=conflict_count,
                risk_score=risk_score,
                business_justification=business_justification,
                approved_by=approved_by,
                **kwargs
            )

            self.session.add(exception)
            self.session.flush()  # Get exception_id

            logger.info(f"Created exception {exception_code} for user {user_name}")
            return exception

        except Exception as e:
            logger.error(f"Error creating exception: {str(e)}")
            self.session.rollback()
            raise

    def _generate_exception_code(self) -> str:
        """
        Generate next sequential exception code (e.g., EXC-2026-001)

        Returns:
            Exception code string
        """
        year = datetime.now().year
        prefix = f"EXC-{year}-"

        # Get highest number for this year
        result = self.session.query(
            func.max(
                func.cast(
                    func.substring(
                        ApprovedExceptionModel.exception_code,
                        len(prefix) + 1
                    ),
                    sqlalchemy.Integer
                )
            )
        ).filter(
            ApprovedExceptionModel.exception_code.like(f"{prefix}%")
        ).scalar()

        next_number = (result or 0) + 1
        return f"{prefix}{next_number:03d}"

    # =========================================================================
    # APPROVED EXCEPTIONS - READ
    # =========================================================================

    def get_by_id(self, exception_id: uuid.UUID) -> ApprovedExceptionModel | None:
        """Get exception by ID"""
        try:
            return self.session.query(ApprovedExceptionModel).filter(
                ApprovedExceptionModel.exception_id == exception_id
            ).first()
        except Exception as e:
            logger.error(f"Error fetching exception by ID: {str(e)}")
            return None

    def get_by_code(self, exception_code: str) -> ApprovedExceptionModel | None:
        """Get exception by exception code"""
        try:
            return self.session.query(ApprovedExceptionModel).filter(
                ApprovedExceptionModel.exception_code == exception_code
            ).first()
        except Exception as e:
            logger.error(f"Error fetching exception by code: {str(e)}")
            return None

    def get_by_user(
        self,
        user_id: uuid.UUID,
        status: ExceptionStatus | None = None
    ) -> list[ApprovedExceptionModel]:
        """
        Get all exceptions for a user

        Args:
            user_id: User UUID
            status: Optional status filter

        Returns:
            List of exceptions
        """
        try:
            query = self.session.query(ApprovedExceptionModel).filter(
                ApprovedExceptionModel.user_id == user_id
            )

            if status:
                query = query.filter(ApprovedExceptionModel.status == status)

            return query.order_by(desc(ApprovedExceptionModel.approved_date)).all()

        except Exception as e:
            logger.error(f"Error fetching exceptions for user: {str(e)}")
            return []

    def find_active_exception(
        self,
        user_id: uuid.UUID,
        rule_id: str | None = None
    ) -> bool:
        """
        Check if there is an active approved exception for a user (and optional rule).

        Args:
            user_id: User UUID
            rule_id: Optional SOD rule ID to match against; if None, any active exception qualifies

        Returns:
            True if an active approved exception exists, False otherwise
        """
        try:
            query = self.session.query(ApprovedExceptionModel).filter(
                and_(
                    ApprovedExceptionModel.user_id == user_id,
                    ApprovedExceptionModel.status == ExceptionStatus.ACTIVE
                )
            )

            if rule_id is not None:
                # Check if rule_id appears in the stored rule/role context
                # Exceptions store role_ids; we match if the rule's code is in exception metadata
                exceptions = query.all()
                for exc in exceptions:
                    metadata = exc.__dict__.get('exception_metadata') or {}
                    approved_rules = metadata.get('rule_ids', [])
                    if str(rule_id) in [str(r) for r in approved_rules]:
                        return True
                return False

            return query.first() is not None

        except Exception as e:
            logger.error(f"Error checking active exception for user {user_id}: {str(e)}")
            return False

    def find_similar_exceptions(
        self,
        role_ids: list[int],
        job_title: str | None = None,
        department: str | None = None,
        limit: int = 3,
        status: ExceptionStatus = ExceptionStatus.ACTIVE
    ) -> list[tuple[ApprovedExceptionModel, float]]:
        """
        Find similar exceptions based on role overlap

        Args:
            role_ids: List of role IDs to match
            job_title: Optional job title for bonus similarity
            department: Optional department for bonus similarity
            limit: Maximum number of results
            status: Exception status filter (default: ACTIVE)

        Returns:
            List of (exception, similarity_score) tuples, sorted by similarity desc
        """
        try:
            # Get all exceptions with matching status
            exceptions = self.session.query(ApprovedExceptionModel).filter(
                ApprovedExceptionModel.status == status
            ).all()

            role_ids_set = set(role_ids)
            similarities = []

            for exception in exceptions:
                exception_role_ids = set(exception.role_ids)

                # Calculate Jaccard similarity for roles
                intersection = len(role_ids_set & exception_role_ids)
                union = len(role_ids_set | exception_role_ids)
                role_similarity = intersection / union if union > 0 else 0

                # Bonus for matching job title
                job_title_match = 0.2 if (job_title and exception.job_title and
                                         exception.job_title.lower() == job_title.lower()) else 0

                # Bonus for matching department
                dept_match = 0.1 if (department and exception.department and
                                   exception.department.lower() == department.lower()) else 0

                # Total similarity (0-1.0)
                total_similarity = (role_similarity * 0.7) + job_title_match + dept_match

                if total_similarity > 0:
                    similarities.append((exception, total_similarity))

            # Sort by similarity descending and take top N
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:limit]

        except Exception as e:
            logger.error(f"Error finding similar exceptions: {str(e)}")
            return []

    def list_all(
        self,
        status: ExceptionStatus | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ApprovedExceptionModel]:
        """
        List all exceptions with optional filters

        Args:
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of exceptions
        """
        try:
            query = self.session.query(ApprovedExceptionModel)

            if status:
                query = query.filter(ApprovedExceptionModel.status == status)

            return query.order_by(
                desc(ApprovedExceptionModel.approved_date)
            ).limit(limit).offset(offset).all()

        except Exception as e:
            logger.error(f"Error listing exceptions: {str(e)}")
            return []

    def count_by_status(self) -> dict[str, int]:
        """
        Count exceptions by status

        Returns:
            Dict of status -> count
        """
        try:
            results = self.session.query(
                ApprovedExceptionModel.status,
                func.count(ApprovedExceptionModel.exception_id)
            ).group_by(ApprovedExceptionModel.status).all()

            return {str(status.value): count for status, count in results}

        except Exception as e:
            logger.error(f"Error counting exceptions by status: {str(e)}")
            return {}

    # =========================================================================
    # APPROVED EXCEPTIONS - UPDATE
    # =========================================================================

    def update_status(
        self,
        exception_id: uuid.UUID,
        new_status: ExceptionStatus,
        reason: str | None = None
    ) -> bool:
        """
        Update exception status

        Args:
            exception_id: Exception UUID
            new_status: New status
            reason: Optional reason for status change

        Returns:
            True if successful
        """
        try:
            exception = self.get_by_id(exception_id)
            if not exception:
                logger.warning(f"Exception {exception_id} not found")
                return False

            old_status = exception.status
            exception.status = new_status
            exception.status_reason = reason
            exception.status_updated_date = datetime.utcnow()

            # Add to audit trail
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "status_change",
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason
            }

            if exception.audit_trail:
                exception.audit_trail.append(audit_entry)
            else:
                exception.audit_trail = [audit_entry]

            self.session.commit()
            logger.info(f"Updated exception {exception.exception_code} status: {old_status} -> {new_status}")
            return True

        except Exception as e:
            logger.error(f"Error updating exception status: {str(e)}")
            self.session.rollback()
            return False

    # =========================================================================
    # EXCEPTION CONTROLS
    # =========================================================================

    def add_control_to_exception(
        self,
        exception_id: uuid.UUID,
        control_id: uuid.UUID,
        estimated_annual_cost: float | None = None,
        risk_reduction_percentage: int | None = None,
        **kwargs
    ) -> ExceptionControlModel | None:
        """
        Add a compensating control to an exception

        Args:
            exception_id: Exception UUID
            control_id: Control UUID
            estimated_annual_cost: Estimated annual cost
            risk_reduction_percentage: Risk reduction %
            **kwargs: Additional optional fields

        Returns:
            Created ExceptionControlModel or None
        """
        try:
            # Check if this control is already assigned
            existing = self.session.query(ExceptionControlModel).filter(
                and_(
                    ExceptionControlModel.exception_id == exception_id,
                    ExceptionControlModel.control_id == control_id
                )
            ).first()

            if existing:
                logger.warning(f"Control {control_id} already assigned to exception {exception_id}")
                return existing

            exception_control = ExceptionControlModel(
                exception_id=exception_id,
                control_id=control_id,
                estimated_annual_cost=estimated_annual_cost,
                risk_reduction_percentage=risk_reduction_percentage,
                **kwargs
            )

            self.session.add(exception_control)
            self.session.flush()

            logger.info(f"Added control {control_id} to exception {exception_id}")
            return exception_control

        except Exception as e:
            logger.error(f"Error adding control to exception: {str(e)}")
            self.session.rollback()
            return None

    def get_exception_controls(
        self,
        exception_id: uuid.UUID
    ) -> list[ExceptionControlModel]:
        """Get all controls for an exception"""
        try:
            return self.session.query(ExceptionControlModel).filter(
                ExceptionControlModel.exception_id == exception_id
            ).all()
        except Exception as e:
            logger.error(f"Error fetching exception controls: {str(e)}")
            return []

    def update_control_status(
        self,
        exception_control_id: int,
        new_status: ImplementationStatus,
        notes: str | None = None
    ) -> bool:
        """Update control implementation status"""
        try:
            control = self.session.query(ExceptionControlModel).filter(
                ExceptionControlModel.exception_control_id == exception_control_id
            ).first()

            if not control:
                return False

            control.implementation_status = new_status
            if notes:
                control.implementation_notes = notes

            self.session.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating control status: {str(e)}")
            self.session.rollback()
            return False

    # =========================================================================
    # EXCEPTION VIOLATIONS
    # =========================================================================

    def record_violation(
        self,
        exception_id: uuid.UUID,
        violation_type: str,
        severity: str,
        description: str,
        **kwargs
    ) -> ExceptionViolationModel | None:
        """
        Record a violation of an approved exception

        Args:
            exception_id: Exception UUID
            violation_type: Type of violation
            severity: CRITICAL, HIGH, MEDIUM, LOW
            description: Description of what happened
            **kwargs: Additional optional fields

        Returns:
            Created ExceptionViolationModel or None
        """
        try:
            violation = ExceptionViolationModel(
                exception_id=exception_id,
                violation_type=violation_type,
                severity=severity,
                description=description,
                **kwargs
            )

            self.session.add(violation)
            self.session.flush()

            # Automatically update exception status to VIOLATED
            exception = self.get_by_id(exception_id)
            if exception and exception.status == ExceptionStatus.ACTIVE:
                self.update_status(
                    exception_id,
                    ExceptionStatus.VIOLATED,
                    f"Control failure: {violation_type}"
                )

            logger.info(f"Recorded violation for exception {exception_id}: {violation_type}")
            return violation

        except Exception as e:
            logger.error(f"Error recording violation: {str(e)}")
            self.session.rollback()
            return None

    def get_exception_violations(
        self,
        exception_id: uuid.UUID
    ) -> list[ExceptionViolationModel]:
        """Get all violations for an exception"""
        try:
            return self.session.query(ExceptionViolationModel).filter(
                ExceptionViolationModel.exception_id == exception_id
            ).order_by(desc(ExceptionViolationModel.violation_date)).all()
        except Exception as e:
            logger.error(f"Error fetching violations: {str(e)}")
            return []

    # =========================================================================
    # EXCEPTION REVIEWS
    # =========================================================================

    def create_review(
        self,
        exception_id: uuid.UUID,
        reviewer_name: str,
        outcome: ReviewOutcome,
        **kwargs
    ) -> ExceptionReviewModel | None:
        """
        Create an exception review record

        Args:
            exception_id: Exception UUID
            reviewer_name: Name of reviewer
            outcome: Review outcome
            **kwargs: Additional fields

        Returns:
            Created ExceptionReviewModel or None
        """
        try:
            review = ExceptionReviewModel(
                exception_id=exception_id,
                review_date=date.today(),
                reviewer_name=reviewer_name,
                outcome=outcome,
                **kwargs
            )

            self.session.add(review)
            self.session.flush()

            # Update exception's last_review_date and next_review_date
            exception = self.get_by_id(exception_id)
            if exception:
                exception.last_review_date = review.review_date
                if 'next_review_date' in kwargs:
                    exception.next_review_date = kwargs['next_review_date']

            logger.info(f"Created review for exception {exception_id}: {outcome}")
            return review

        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            self.session.rollback()
            return None

    def get_exception_reviews(
        self,
        exception_id: uuid.UUID
    ) -> list[ExceptionReviewModel]:
        """Get all reviews for an exception"""
        try:
            return self.session.query(ExceptionReviewModel).filter(
                ExceptionReviewModel.exception_id == exception_id
            ).order_by(desc(ExceptionReviewModel.review_date)).all()
        except Exception as e:
            logger.error(f"Error fetching reviews: {str(e)}")
            return []

    # =========================================================================
    # STATISTICS AND REPORTING
    # =========================================================================

    def get_effectiveness_stats(self) -> dict[str, Any]:
        """
        Get effectiveness statistics for all exceptions

        Returns:
            Dict with statistics
        """
        try:
            total = self.session.query(func.count(ApprovedExceptionModel.exception_id)).scalar() or 0

            # Count by status
            status_counts = self.count_by_status()

            # Total costs
            total_cost = self.session.query(
                func.sum(ExceptionControlModel.estimated_annual_cost)
            ).filter(
                ExceptionControlModel.implementation_status.in_([
                    ImplementationStatus.ACTIVE,
                    ImplementationStatus.IMPLEMENTED
                ])
            ).scalar() or 0

            # Average risk score
            avg_risk_score = self.session.query(
                func.avg(ApprovedExceptionModel.risk_score)
            ).filter(
                ApprovedExceptionModel.status == ExceptionStatus.ACTIVE
            ).scalar() or 0

            # Violation counts
            total_violations = self.session.query(
                func.count(ExceptionViolationModel.violation_id)
            ).scalar() or 0

            return {
                "total_exceptions": total,
                "by_status": status_counts,
                "total_annual_cost": float(total_cost),
                "average_risk_score": float(avg_risk_score),
                "total_violations": total_violations
            }

        except Exception as e:
            logger.error(f"Error calculating effectiveness stats: {str(e)}")
            return {}

    def get_exceptions_needing_review(self) -> list[ApprovedExceptionModel]:
        """
        Get exceptions that need review (next_review_date in past or today)

        Returns:
            List of exceptions
        """
        try:
            today = date.today()
            return self.session.query(ApprovedExceptionModel).filter(
                and_(
                    ApprovedExceptionModel.status == ExceptionStatus.ACTIVE,
                    ApprovedExceptionModel.next_review_date <= today
                )
            ).order_by(ApprovedExceptionModel.next_review_date).all()

        except Exception as e:
            logger.error(f"Error fetching exceptions needing review: {str(e)}")
            return []


# Add import to sqlalchemy for INTEGER cast
