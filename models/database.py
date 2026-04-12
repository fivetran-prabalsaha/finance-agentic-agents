"""
SQLAlchemy ORM Models for SOD Compliance System

Defines all database tables and relationships
"""

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
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


# Enums
class UserStatus(enum.Enum):
    """User account status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class ViolationSeverity(enum.Enum):
    """Severity levels for SOD violations"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ViolationStatus(enum.Enum):
    """Status of violation"""
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class ScanStatus(enum.Enum):
    """Status of compliance scan"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class NotificationChannel(enum.Enum):
    """Notification delivery channels"""
    EMAIL = "EMAIL"
    SLACK = "SLACK"
    DASHBOARD = "DASHBOARD"
    WEBHOOK = "WEBHOOK"


class NotificationStatus(enum.Enum):
    """Status of notification delivery"""
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class OktaUserStatus(enum.Enum):
    """Okta user status"""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEPROVISIONED = "DEPROVISIONED"
    STAGED = "STAGED"
    PASSWORD_EXPIRED = "PASSWORD_EXPIRED"
    LOCKED_OUT = "LOCKED_OUT"


class ReconciliationStatus(enum.Enum):
    """User reconciliation status"""
    MATCHED = "MATCHED"
    ORPHANED = "ORPHANED"
    MISSING_IN_OKTA = "MISSING_IN_OKTA"
    MISSING_IN_NETSUITE = "MISSING_IN_NETSUITE"
    STATUS_MISMATCH = "STATUS_MISMATCH"


class RiskLevel(enum.Enum):
    """Risk level for reconciliation discrepancies"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ApprovalStatus(enum.Enum):
    """Approval request status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ExecutionStatus(enum.Enum):
    """Execution status for deactivation"""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class ExecutionMethod(enum.Enum):
    """Method used for deactivation"""
    RESTLET = "RESTLET"
    MAPREDUCE = "MAPREDUCE"
    MANUAL = "MANUAL"


class DeactivationAction(enum.Enum):
    """Deactivation action type"""
    DEACTIVATE = "DEACTIVATE"
    REACTIVATE = "REACTIVATE"


# Models
class User(Base):
    """NetSuite users"""
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    internal_id = Column(String(50), unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, index=True)
    department = Column(String(255))
    subsidiary = Column(String(255))
    employee_id = Column(String(100))
    last_login = Column(DateTime)

    # NEW: Context fields for SOD analysis
    job_function = Column(String(100), index=True)  # IT/SYSTEMS_ENGINEERING, FINANCE, etc.
    business_unit = Column(String(255))             # Cost center/business unit
    title = Column(String(255))                     # Job title
    supervisor = Column(String(255))                # Manager name
    supervisor_id = Column(String(100))             # Manager internal ID
    location = Column(String(255))                  # Office location
    hire_date = Column(DateTime)                    # Hire date

    synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="user", cascade="all, delete-orphan")
    approved_exceptions = relationship("ApprovedExceptionModel", back_populates="user", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_user_status_email', 'status', 'email'),
        Index('idx_user_department', 'department'),
        Index('idx_user_job_function', 'job_function'),
    )

    def __repr__(self):
        return f"<User(user_id='{self.user_id}', name='{self.name}', email='{self.email}')>"


class Role(Base):
    """NetSuite roles"""
    __tablename__ = 'roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(String(100), unique=True, nullable=False, index=True)
    role_name = Column(String(255), nullable=False)
    is_custom = Column(Boolean, default=False)
    description = Column(Text)
    permission_count = Column(Integer, default=0)
    permissions = Column(JSON)  # Store permissions as JSON
    embedding = Column(Vector(384))  # pgvector for semantic search
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Role(role_id='{self.role_id}', name='{self.role_name}')>"


class UserRole(Base):
    """Association between users and roles"""
    __tablename__ = 'user_roles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String(255))
    notes = Column(Text)

    # Relationships
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")

    # Indexes
    __table_args__ = (
        Index('idx_user_role_unique', 'user_id', 'role_id', unique=True),
    )

    def __repr__(self):
        return f"<UserRole(user_id='{self.user_id}', role_id='{self.role_id}')>"


class SODRule(Base):
    """Segregation of Duties rules"""
    __tablename__ = 'sod_rules'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)
    description = Column(Text)
    conflicting_permissions = Column(JSON)  # List of conflicting permission patterns
    severity = Column(SQLEnum(ViolationSeverity), default=ViolationSeverity.MEDIUM)
    is_active = Column(Boolean, default=True)
    embedding = Column(Vector(384))  # pgvector for semantic search
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    violations = relationship("Violation", back_populates="rule")

    def __repr__(self):
        return f"<SODRule(rule_id='{self.rule_id}', name='{self.rule_name}')>"


class Violation(Base):
    """Detected SOD violations"""
    __tablename__ = 'violations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey('sod_rules.id'), nullable=False)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('compliance_scans.id'))

    severity = Column(SQLEnum(ViolationSeverity), nullable=False, index=True)
    status = Column(SQLEnum(ViolationStatus), default=ViolationStatus.OPEN, index=True)
    risk_score = Column(Float, default=0.0)  # 0-100 scale

    title = Column(String(500), nullable=False)
    description = Column(Text)
    conflicting_roles = Column(JSON)  # List of role IDs causing conflict
    conflicting_permissions = Column(JSON)  # Specific permissions in conflict

    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)
    resolved_by = Column(String(255))
    resolution_notes = Column(Text)

    embedding = Column(Vector(384))  # pgvector for similar violation search
    violation_metadata = Column(JSON)  # Additional context

    # Relationships
    user = relationship("User", back_populates="violations")
    rule = relationship("SODRule", back_populates="violations")
    scan = relationship("ComplianceScan", back_populates="violations")

    # Indexes
    __table_args__ = (
        Index('idx_violation_status_severity', 'status', 'severity'),
        Index('idx_violation_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<Violation(user_id='{self.user_id}', severity='{self.severity}', status='{self.status}')>"


class SyncStatus(enum.Enum):
    """Status of data collection sync"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SyncType(enum.Enum):
    """Type of data collection sync"""
    FULL = "FULL"
    INCREMENTAL = "INCREMENTAL"
    MANUAL = "MANUAL"


class SyncMetadata(Base):
    """Data collection sync job metadata"""
    __tablename__ = 'sync_metadata'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Sync details
    sync_type = Column(SQLEnum(SyncType), nullable=False)
    system_name = Column(String(100), nullable=False, index=True)
    status = Column(SQLEnum(SyncStatus), nullable=False, index=True)

    # Timing
    started_at = Column(DateTime, nullable=False, index=True)
    completed_at = Column(DateTime, index=True)
    duration_seconds = Column(Float)

    # Metrics
    users_fetched = Column(Integer, default=0)
    users_synced = Column(Integer, default=0)
    users_updated = Column(Integer, default=0)
    users_created = Column(Integer, default=0)
    roles_synced = Column(Integer, default=0)
    violations_detected = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)

    # Additional context
    extra_metadata = Column('metadata', JSON)  # Column name is 'metadata', attribute is 'extra_metadata'
    triggered_by = Column(String(255))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_sync_last_success', 'system_name', 'completed_at',
              postgresql_where=(status == SyncStatus.SUCCESS)),
    )

    def __repr__(self):
        return f"<SyncMetadata(sync_type='{self.sync_type.value}', system='{self.system_name}', status='{self.status.value}')>"


class ComplianceScan(Base):
    """Compliance scan execution history"""
    __tablename__ = 'compliance_scans'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_type = Column(String(50), default='AUTOMATED')  # AUTOMATED, MANUAL, SCHEDULED
    status = Column(SQLEnum(ScanStatus), default=ScanStatus.PENDING, index=True)

    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    users_scanned = Column(Integer, default=0)
    violations_found = Column(Integer, default=0)
    violations_critical = Column(Integer, default=0)
    violations_high = Column(Integer, default=0)
    violations_medium = Column(Integer, default=0)
    violations_low = Column(Integer, default=0)

    triggered_by = Column(String(255))
    filters_applied = Column(JSON)
    error_message = Column(Text)
    scan_metadata = Column(JSON)

    # Relationships
    violations = relationship("Violation", back_populates="scan")
    agent_logs = relationship("AgentLog", back_populates="scan")

    def __repr__(self):
        return f"<ComplianceScan(id='{self.id}', status='{self.status}', violations={self.violations_found})>"


class AgentLog(Base):
    """Agent execution logs for monitoring"""
    __tablename__ = 'agent_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey('compliance_scans.id'))
    agent_name = Column(String(100), nullable=False, index=True)
    log_level = Column(String(20), default='INFO')
    message = Column(Text)
    execution_time_ms = Column(Float)
    success = Column(Boolean, default=True)
    error_details = Column(JSON)
    log_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    scan = relationship("ComplianceScan", back_populates="agent_logs")

    # Indexes
    __table_args__ = (
        Index('idx_agent_log_scan_agent', 'scan_id', 'agent_name'),
    )

    def __repr__(self):
        return f"<AgentLog(agent='{self.agent_name}', level='{self.log_level}')>"


class Notification(Base):
    """Notification delivery log"""
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    violation_id = Column(UUID(as_uuid=True), ForeignKey('violations.id'))
    notification_type = Column(String(50), nullable=False)  # EMAIL, SLACK, DASHBOARD
    recipient = Column(String(255), nullable=False)
    subject = Column(String(500))
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivery_status = Column(String(50), default='PENDING')  # PENDING, SENT, FAILED
    error_message = Column(Text)
    notification_metadata = Column(JSON)

    def __repr__(self):
        return f"<Notification(type='{self.notification_type}', recipient='{self.recipient}')>"


class AuditTrail(Base):
    """Audit trail for compliance actions"""
    __tablename__ = 'audit_trail'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False, index=True)  # USER, ROLE, VIOLATION
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, RESOLVE
    actor = Column(String(255), nullable=False)
    changes = Column(JSON)  # Before/after values
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    audit_metadata = Column(JSON)

    # Indexes
    __table_args__ = (
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<AuditTrail(entity='{self.entity_type}', action='{self.action}', actor='{self.actor}')>"


# Okta-NetSuite Reconciliation Models

class OktaUser(Base):
    """Okta user data for reconciliation"""
    __tablename__ = 'okta_users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    okta_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(255))
    last_name = Column(String(255))
    status = Column(SQLEnum(OktaUserStatus), nullable=False, index=True)

    # Okta metadata
    login = Column(String(255))
    activated = Column(DateTime)
    status_changed = Column(DateTime)
    last_login = Column(DateTime)
    last_updated = Column(DateTime)
    password_changed = Column(DateTime)

    # Profile information
    department = Column(String(255))
    title = Column(String(255))
    employee_number = Column(String(100))
    manager = Column(String(255))
    manager_id = Column(String(255))

    # Okta groups (stored as JSON array)
    okta_groups = Column(JSON)

    # Sync metadata
    synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reconciliations = relationship("UserReconciliation", back_populates="okta_user", foreign_keys="UserReconciliation.okta_user_id")

    # Indexes
    __table_args__ = (
        Index('idx_okta_email', 'email'),
        Index('idx_okta_status', 'status'),
        Index('idx_okta_synced', 'synced_at'),
    )

    def __repr__(self):
        return f"<OktaUser(okta_id='{self.okta_id}', email='{self.email}', status='{self.status}')>"


class UserReconciliation(Base):
    """User reconciliation between Okta and NetSuite"""
    __tablename__ = 'user_reconciliations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User references
    netsuite_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    okta_user_id = Column(UUID(as_uuid=True), ForeignKey('okta_users.id'))
    email = Column(String(255), nullable=False, index=True)

    # Status comparison
    netsuite_status = Column(String(50))
    okta_status = Column(String(50))
    reconciliation_status = Column(SQLEnum(ReconciliationStatus), nullable=False, index=True)

    # Details
    discrepancy_reason = Column(Text)
    risk_level = Column(SQLEnum(RiskLevel))

    # Action tracking
    requires_action = Column(Boolean, default=False, index=True)
    action_required = Column(String(100))  # DEACTIVATE_NETSUITE, INVESTIGATE, etc.

    # Metadata
    reconciled_at = Column(DateTime, default=datetime.utcnow, index=True)
    scan_id = Column(UUID(as_uuid=True))

    # Relationships
    netsuite_user = relationship("User", foreign_keys=[netsuite_user_id])
    okta_user = relationship("OktaUser", back_populates="reconciliations", foreign_keys=[okta_user_id])

    # Indexes
    __table_args__ = (
        Index('idx_recon_status', 'reconciliation_status'),
        Index('idx_recon_email', 'email'),
        Index('idx_recon_requires_action', 'requires_action'),
        Index('idx_recon_risk_level', 'risk_level'),
    )

    def __repr__(self):
        return f"<UserReconciliation(email='{self.email}', status='{self.reconciliation_status}', risk='{self.risk_level}')>"


class DeactivationApproval(Base):
    """Deactivation approval requests"""
    __tablename__ = 'deactivation_approvals'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Request details
    request_id = Column(String(100), unique=True, nullable=False, index=True)
    user_ids = Column(JSON, nullable=False)  # Array of NetSuite user IDs to deactivate
    user_count = Column(Integer, nullable=False)

    # Approval workflow
    status = Column(SQLEnum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    requested_by = Column(String(255), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)

    approved_by = Column(String(255))
    approved_at = Column(DateTime)

    rejected_by = Column(String(255))
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)

    # Execution tracking
    execution_status = Column(SQLEnum(ExecutionStatus))
    execution_method = Column(SQLEnum(ExecutionMethod))
    execution_started_at = Column(DateTime)
    execution_completed_at = Column(DateTime)

    # Results
    users_deactivated = Column(Integer, default=0)
    users_failed = Column(Integer, default=0)
    execution_errors = Column(JSON)

    # Metadata
    expires_at = Column(DateTime)  # Auto-reject after 48 hours
    approval_metadata = Column(JSON)

    # Relationships
    deactivation_logs = relationship("DeactivationLog", back_populates="approval_request")

    # Indexes
    __table_args__ = (
        Index('idx_approval_status', 'status'),
        Index('idx_approval_requested_at', 'requested_at'),
        Index('idx_approval_execution_status', 'execution_status'),
    )

    def __repr__(self):
        return f"<DeactivationApproval(request_id='{self.request_id}', status='{self.status}', users={self.user_count})>"


class DeactivationLog(Base):
    """Deactivation action logs"""
    __tablename__ = 'deactivation_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    netsuite_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    netsuite_internal_id = Column(String(100), index=True)
    email = Column(String(255), nullable=False, index=True)

    # Approval reference
    approval_request_id = Column(UUID(as_uuid=True), ForeignKey('deactivation_approvals.id'))

    # Action details
    action = Column(SQLEnum(DeactivationAction), nullable=False)
    method = Column(SQLEnum(ExecutionMethod))

    # Status
    status = Column(String(50), nullable=False, index=True)  # SUCCESS, FAILED, PENDING
    error_message = Column(Text)

    # Metadata
    performed_by = Column(String(255))
    performed_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Audit trail
    reason = Column(Text)
    okta_status_at_time = Column(String(50))
    netsuite_status_before = Column(String(50))
    netsuite_status_after = Column(String(50))

    log_metadata = Column(JSON)

    # Relationships
    netsuite_user = relationship("User", foreign_keys=[netsuite_user_id])
    approval_request = relationship("DeactivationApproval", back_populates="deactivation_logs")

    # Indexes
    __table_args__ = (
        Index('idx_deactivation_email', 'email'),
        Index('idx_deactivation_status', 'status'),
        Index('idx_deactivation_performed_at', 'performed_at'),
        Index('idx_deactivation_approval', 'approval_request_id'),
    )

    def __repr__(self):
        return f"<DeactivationLog(email='{self.email}', action='{self.action}', status='{self.status}')>"


# Phase 3: Learning & Refinement Models

class ExemptionStatus(enum.Enum):
    """Exemption request status"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class ViolationExemption(Base):
    """Approved exemptions for SOD violations (Phase 3: Learning Loop)"""
    __tablename__ = 'violation_exemptions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # References
    violation_id = Column(UUID(as_uuid=True), ForeignKey('violations.id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    rule_id = Column(UUID(as_uuid=True), ForeignKey('sod_rules.id'))

    # Exemption details
    reason = Column(String(500), nullable=False)
    rationale = Column(Text, nullable=False)  # Detailed business justification
    business_justification = Column(Text)
    compensating_controls = Column(Text)  # What controls mitigate the risk

    # Approval workflow
    status = Column(SQLEnum(ExemptionStatus), default=ExemptionStatus.PENDING, index=True)
    requested_by = Column(String(255), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)

    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    approval_notes = Column(Text)

    rejected_by = Column(String(255))
    rejected_at = Column(DateTime)
    rejection_reason = Column(Text)

    # Expiration and review
    expires_at = Column(DateTime)  # Exemptions should be reviewed periodically
    last_reviewed_at = Column(DateTime)
    next_review_date = Column(DateTime, index=True)
    auto_approved = Column(Boolean, default=False)

    # Risk assessment
    risk_score = Column(Float)  # Risk score at time of approval
    risk_acceptance_level = Column(String(50))  # HIGH, MEDIUM, LOW

    # Embedding for similarity search (Phase 3: Learn from approved exemptions)
    embedding = Column(Vector(384))  # pgvector for finding similar exemption cases

    # Audit trail
    exemption_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    violation = relationship("Violation", foreign_keys=[violation_id])
    user = relationship("User", foreign_keys=[user_id])
    rule = relationship("SODRule", foreign_keys=[rule_id])

    # Indexes
    __table_args__ = (
        Index('idx_exemption_status', 'status'),
        Index('idx_exemption_user', 'user_id'),
        Index('idx_exemption_rule', 'rule_id'),
        Index('idx_exemption_requested_at', 'requested_at'),
        Index('idx_exemption_next_review', 'next_review_date'),
    )

    def __repr__(self):
        return f"<ViolationExemption(id='{self.id}', status='{self.status}', reason='{self.reason[:50]}...')>"


class JobRoleMapping(Base):
    """
    Job role to NetSuite role mappings with acceptable combinations

    Maps job titles to acceptable role combinations and business justifications
    for context-aware SOD analysis
    """
    __tablename__ = "job_role_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_role_id = Column(String(50), unique=True, nullable=False)
    job_title = Column(String(255), nullable=False)
    department = Column(String(100))
    acceptable_role_combinations = Column(JSONB, default=[])  # List of acceptable role combinations
    business_justification = Column(Text)  # Business justification for role combination
    requires_compensating_controls = Column(Boolean, default=False)
    typical_controls = Column(ARRAY(String), default=[])  # Array of control IDs
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_col = Column('metadata', JSONB, default={})  # Use metadata_col to avoid SQLAlchemy reserved name

    # Indexes
    __table_args__ = (
        Index('idx_job_role_mappings_title', 'job_title'),
        Index('idx_job_role_mappings_dept', 'department'),
        Index('idx_job_role_mappings_active', 'is_active'),
    )

    def __repr__(self):
        return f"<JobRoleMapping(id='{self.id}', job_title='{self.job_title}', department='{self.department}')>"


# Import exception models (must be after User and CompensatingControl are defined)
