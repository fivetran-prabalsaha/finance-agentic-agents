"""
SQLAlchemy Models for Exception Management

Defines models for storing approved SOD exceptions with compensating controls,
tracking their effectiveness, and learning from precedents.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from models.database_config import Base


# Enums for Exception Management
class ExceptionStatus(enum.Enum):
    """Status of approved exception"""
    ACTIVE = "ACTIVE"                    # Exception is currently active
    VIOLATED = "VIOLATED"                # Controls failed, violation occurred
    REMEDIATED = "REMEDIATED"            # Access removed, exception closed
    EXPIRED = "EXPIRED"                  # Time-based expiration reached
    REVOKED = "REVOKED"                  # Manually revoked by compliance


class ImplementationStatus(enum.Enum):
    """Implementation status of compensating control"""
    PLANNED = "PLANNED"                  # Control planned but not started
    IN_PROGRESS = "IN_PROGRESS"          # Implementation underway
    IMPLEMENTED = "IMPLEMENTED"          # Technical implementation complete
    ACTIVE = "ACTIVE"                    # Control active and operational
    FAILED = "FAILED"                    # Implementation failed
    DEACTIVATED = "DEACTIVATED"          # Control turned off


class RemediationStatus(enum.Enum):
    """Remediation status for exception violations"""
    OPEN = "OPEN"                        # Newly detected, needs action
    IN_PROGRESS = "IN_PROGRESS"          # Remediation work ongoing
    RESOLVED = "RESOLVED"                # Successfully remediated
    ACCEPTED_RISK = "ACCEPTED_RISK"      # Risk accepted, no remediation


class ReviewOutcome(enum.Enum):
    """Outcome of periodic exception review"""
    APPROVED_CONTINUE = "APPROVED_CONTINUE"    # Continue with current controls
    APPROVED_MODIFY = "APPROVED_MODIFY"        # Continue with modified controls
    REVOKED = "REVOKED"                        # Revoke exception, remove access
    ESCALATED = "ESCALATED"                    # Escalate to higher authority


# =============================================================================
# APPROVED EXCEPTION MODEL
# =============================================================================

class ApprovedExceptionModel(Base):
    """
    Master table for approved SOD exceptions

    Stores all approved exceptions where users are granted conflicting
    permissions with compensating controls to mitigate risk.
    """
    __tablename__ = 'approved_exceptions'

    # Identity
    exception_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exception_code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "EXC-2026-001"

    # User/Request Info
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    user_name = Column(String(255), nullable=False)
    user_email = Column(String(255))
    job_title = Column(String(255))
    department = Column(String(255))

    # Role Combination (stored as arrays for easy matching)
    role_ids = Column(ARRAY(UUID), nullable=False)
    role_names = Column(ARRAY(String), nullable=False)

    # Violation Details
    conflict_count = Column(Integer, nullable=False)
    critical_conflicts = Column(Integer, default=0)
    high_conflicts = Column(Integer, default=0)
    medium_conflicts = Column(Integer, default=0)
    low_conflicts = Column(Integer, default=0)
    risk_score = Column(DECIMAL(5, 2))  # 0-100

    # Business Context
    business_justification = Column(Text, nullable=False)
    request_reason = Column(Text)
    ticket_reference = Column(String(100))

    # Approval Info
    approved_by = Column(String(255), nullable=False)
    approved_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    approval_authority = Column(String(100))  # e.g., "CFO", "Audit Committee"

    # Review Schedule
    review_frequency = Column(String(50))  # e.g., "Monthly", "Quarterly", "Annual"
    next_review_date = Column(Date, index=True)
    last_review_date = Column(Date)

    # Status
    status = Column(SQLEnum(ExceptionStatus), nullable=False, default=ExceptionStatus.ACTIVE, index=True)
    status_reason = Column(Text)
    status_updated_date = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # Optional: auto-expire after N months

    # Audit trail (JSONB for flexibility)
    audit_trail = Column(JSONB, default=[])

    # Search optimization (generated column for full-text search)
    # Note: This would be created in migration as GENERATED ALWAYS AS

    # Relationships
    user = relationship("User", back_populates="approved_exceptions")
    controls = relationship("ExceptionControlModel", back_populates="exception", cascade="all, delete-orphan")
    violations = relationship("ExceptionViolationModel", back_populates="exception", cascade="all, delete-orphan")
    reviews = relationship("ExceptionReviewModel", back_populates="exception", cascade="all, delete-orphan")

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint('risk_score >= 0 AND risk_score <= 100', name='valid_risk_score'),
        Index('idx_approved_exceptions_user', 'user_id'),
        Index('idx_approved_exceptions_status', 'status'),
        Index('idx_approved_exceptions_date', 'approved_date'),
        Index('idx_approved_exceptions_next_review', 'next_review_date'),
        # GIN index for role_ids array search would be created in migration
    )

    def __repr__(self):
        return f"<ApprovedExceptionModel(code='{self.exception_code}', user='{self.user_name}', status='{self.status}')>"


# =============================================================================
# EXCEPTION CONTROLS MODEL
# =============================================================================

class ExceptionControlModel(Base):
    """
    Many-to-many relationship between exceptions and compensating controls

    Tracks which controls are applied to which exceptions, their implementation
    status, cost, and effectiveness.
    """
    __tablename__ = 'exception_controls'

    exception_control_id = Column(Integer, primary_key=True, autoincrement=True)
    exception_id = Column(UUID(as_uuid=True), ForeignKey('approved_exceptions.exception_id', ondelete='CASCADE'), nullable=False)
    control_id = Column(UUID(as_uuid=True), ForeignKey('compensating_controls.id'), nullable=False)

    # Implementation Details
    implementation_date = Column(Date)
    implementation_status = Column(SQLEnum(ImplementationStatus), default=ImplementationStatus.PLANNED, index=True)

    # Cost Tracking (actual vs estimated)
    estimated_annual_cost = Column(DECIMAL(10, 2))
    actual_annual_cost = Column(DECIMAL(10, 2))
    implementation_cost = Column(DECIMAL(10, 2))

    # Effectiveness Tracking
    risk_reduction_percentage = Column(Integer)  # From control definition
    effectiveness_score = Column(DECIMAL(5, 2))  # Actual effectiveness 0-100
    violations_prevented = Column(Integer, default=0)
    violations_occurred = Column(Integer, default=0)

    # Notes
    implementation_notes = Column(Text)
    effectiveness_notes = Column(Text)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exception = relationship("ApprovedExceptionModel", back_populates="controls")
    control = relationship("CompensatingControl")

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint('effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100)', name='valid_effectiveness'),
        Index('idx_exception_controls_exception', 'exception_id'),
        Index('idx_exception_controls_control', 'control_id'),
        Index('idx_exception_controls_status', 'implementation_status'),
    )

    def __repr__(self):
        return f"<ExceptionControlModel(exception_id='{self.exception_id}', control_id='{self.control_id}', status='{self.implementation_status}')>"


# =============================================================================
# EXCEPTION VIOLATIONS MODEL
# =============================================================================

class ExceptionViolationModel(Base):
    """
    Tracks when an approved exception is violated (control failure)

    Records instances where compensating controls failed to prevent a violation,
    enabling effectiveness tracking and control improvement.
    """
    __tablename__ = 'exception_violations'

    violation_id = Column(Integer, primary_key=True, autoincrement=True)
    exception_id = Column(UUID(as_uuid=True), ForeignKey('approved_exceptions.exception_id'), nullable=False)

    # Violation Details
    violation_date = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    violation_type = Column(String(100))  # What rule was violated
    severity = Column(String(20))  # CRITICAL, HIGH, MEDIUM, LOW

    # Description
    description = Column(Text, nullable=False)
    root_cause = Column(Text)

    # Which control failed?
    failed_control_id = Column(UUID(as_uuid=True), ForeignKey('compensating_controls.id'))
    failure_reason = Column(Text)

    # Detection
    detected_by = Column(String(255))  # System or person who detected
    detection_method = Column(String(100))  # e.g., "Audit", "Automated monitoring"

    # Remediation
    remediation_action = Column(Text)
    remediation_status = Column(SQLEnum(RemediationStatus), default=RemediationStatus.OPEN, index=True)
    remediated_date = Column(DateTime)
    remediated_by = Column(String(255))

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    exception = relationship("ApprovedExceptionModel", back_populates="violations")
    failed_control = relationship("CompensatingControl")

    # Indexes
    __table_args__ = (
        Index('idx_exception_violations_exception', 'exception_id'),
        Index('idx_exception_violations_date', 'violation_date'),
        Index('idx_exception_violations_status', 'remediation_status'),
    )

    def __repr__(self):
        return f"<ExceptionViolationModel(exception_id='{self.exception_id}', type='{self.violation_type}', status='{self.remediation_status}')>"


# =============================================================================
# EXCEPTION REVIEWS MODEL
# =============================================================================

class ExceptionReviewModel(Base):
    """
    Tracks periodic reviews of approved exceptions

    Records scheduled and ad-hoc reviews to ensure exceptions remain appropriate
    and controls remain effective.
    """
    __tablename__ = 'exception_reviews'

    review_id = Column(Integer, primary_key=True, autoincrement=True)
    exception_id = Column(UUID(as_uuid=True), ForeignKey('approved_exceptions.exception_id'), nullable=False)

    # Review Details
    review_date = Column(Date, nullable=False, index=True)
    reviewer_name = Column(String(255), nullable=False)
    review_type = Column(String(50))  # e.g., "Scheduled", "Ad-hoc", "Audit-triggered"

    # Review Outcome
    outcome = Column(SQLEnum(ReviewOutcome), nullable=False)

    # Findings
    controls_effective = Column(Boolean)
    violations_found = Column(Boolean)
    findings = Column(Text)
    recommendations = Column(Text)

    # Next Review
    next_review_date = Column(Date)

    # Audit
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    exception = relationship("ApprovedExceptionModel", back_populates="reviews")

    # Indexes
    __table_args__ = (
        Index('idx_exception_reviews_exception', 'exception_id'),
        Index('idx_exception_reviews_date', 'review_date'),
    )

    def __repr__(self):
        return f"<ExceptionReviewModel(exception_id='{self.exception_id}', date='{self.review_date}', outcome='{self.outcome}')>"


# =============================================================================
# COMPENSATING CONTROL MODEL (Reference - may already exist)
# =============================================================================

class CompensatingControl(Base):
    """
    Compensating controls library

    NOTE: This model may already exist in database.py. Include here for reference.
    If it exists, remove this definition and just import it.
    """
    __tablename__ = 'compensating_controls'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    control_type = Column(String(100))  # e.g., "Preventive", "Detective", "Corrective"

    # Effectiveness Metrics
    risk_reduction_percentage = Column(Integer)  # 0-100% risk reduction
    implementation_time_hours = Column(Integer)  # Hours to implement
    annual_cost_estimate = Column(DECIMAL(10, 2))  # Annual operating cost

    # Applicability
    severity_levels = Column(ARRAY(String))  # Which severity levels this applies to

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_col = Column('metadata', JSONB, default={})

    def __repr__(self):
        return f"<CompensatingControl(id='{self.control_id}', name='{self.name}')>"
