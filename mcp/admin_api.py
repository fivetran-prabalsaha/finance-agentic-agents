"""
Admin API — Compliance Agent Configuration Portal

Provides JWT-authenticated REST endpoints for the Angular admin portal.
All routes under /auth/* and /admin/* are handled here and mounted on
the existing FastAPI app in mcp_server.py.

Authority levels (derived from NetSuite roles):
  L3 — Director         → read-only: violations, exceptions, reports
  L4 — Controller / VP  → read + edit thresholds, notifications, schedules, SOD rules
  L5 — CFO / C-Suite    → full access (feature flags, API key rotation, LLM config)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

try:
    from jose import JWTError, jwt
    _JWT_AVAILABLE = True
except ImportError:
    _JWT_AVAILABLE = False

from models.database_config import DatabaseConfig
from services.approval_service import ApprovalService


def SessionLocal():
    """Return a new SQLAlchemy session (mirrors the pattern used in mcp_tools.py)."""
    db_config = DatabaseConfig()
    return db_config.get_session()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-please-use-a-long-random-string")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Map role keywords → authority level
_ROLE_LEVEL_MAP = {
    "CFO": 5, "C-Suite": 5, "CEO": 5, "CTO": 5, "COO": 5,
    "Controller": 4, "VP Finance": 4, "VP of Finance": 4, "IT Director": 4,
    "Director": 3, "Manager": 3,
}

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class MeResponse(BaseModel):
    email: str
    name: str
    level: int
    level_label: str
    roles: list[str]
    job_title: str | None = None
    department: str | None = None


class ThresholdUpdate(BaseModel):
    critical: int | None = None
    high: int | None = None
    medium: int | None = None


class NotificationUpdate(BaseModel):
    notify_critical_immediately: bool | None = None
    notify_high_daily: bool | None = None
    notify_medium_weekly: bool | None = None
    slack_channel: str | None = None


class SchedulingUpdate(BaseModel):
    scan_interval_hours: int | None = None
    full_sync_cron_hour: int | None = None
    full_sync_cron_minute: int | None = None
    incremental_sync_hours: int | None = None
    redis_cache_ttl_seconds: int | None = None


class FeatureFlagUpdate(BaseModel):
    enable_vector_search: bool | None = None
    enable_historical_analysis: bool | None = None
    enable_ml_scoring: bool | None = None
    use_mcp_cache: bool | None = None
    use_conv_summaries: bool | None = None


class LlmConfigUpdate(BaseModel):
    fast_model: str | None = None
    reasoning_model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None


class SODRuleUpdate(BaseModel):
    rule_name: str | None = None
    description: str | None = None
    severity: str | None = None
    is_active: bool | None = None


class ViolationStatusUpdate(BaseModel):
    new_status: str
    notes: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_level(roles: list[str]) -> int:
    """Map a user's NetSuite role list to portal authority level (3-5)."""
    best = 0
    for role in roles:
        for keyword, lvl in _ROLE_LEVEL_MAP.items():
            if keyword.lower() in role.lower():
                best = max(best, lvl)
    return best if best >= 3 else 0  # 0 = no portal access


def _level_label(level: int) -> str:
    return {5: "C-Suite", 4: "Controller / VP", 3: "Director"}.get(level, "No Access")


def _create_token(payload: dict[str, Any]) -> str:
    if not _JWT_AVAILABLE:
        raise HTTPException(status_code=500, detail="JWT library not installed. Run: pip install python-jose[cryptography]")
    exp = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
    data = {**payload, "exp": exp, "iat": datetime.utcnow()}
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict[str, Any]:
    if not _JWT_AVAILABLE:
        raise HTTPException(status_code=500, detail="JWT library not installed.")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


def _require_level(min_level: int):
    """Dependency factory that enforces minimum authority level."""
    def _check(user: dict[str, Any] = Depends(_get_current_user)):
        if user.get("level", 0) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires authority level {min_level}+, you have {user.get('level', 0)}",
            )
        return user
    return _check


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
admin_router = APIRouter(prefix="/admin", tags=["Admin Portal"])

# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

_DEMO_PASSWORD = os.getenv("ADMIN_PORTAL_PASSWORD", "compliance2026!")


@auth_router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """
    Authenticate elevated user and issue a JWT.

    Password is validated against ADMIN_PORTAL_PASSWORD env var (development)
    or a bcrypt-hashed value stored in the DB (production path: extend here).
    Only users with authority level >= 3 (Director+) can log in.
    """
    db = SessionLocal()
    try:
        svc = ApprovalService(db)
        user_info = svc.authenticate_user(body.email)

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Password check — simple env-var approach for demo; extend with bcrypt for prod
        if body.password != _DEMO_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        roles = user_info.get("roles", [])
        level = _compute_level(roles)

        if level < 3:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portal access requires Director-level or above NetSuite role",
            )

        token_payload = {
            "sub": body.email,
            "name": user_info.get("name", ""),
            "level": level,
            "roles": roles,
            "job_title": user_info.get("job_title"),
            "department": user_info.get("department"),
        }
        token = _create_token(token_payload)

        user_out = {
            "email": body.email,
            "name": user_info.get("name", ""),
            "level": level,
            "level_label": _level_label(level),
            "roles": roles,
            "job_title": user_info.get("job_title"),
            "department": user_info.get("department"),
        }
        return LoginResponse(access_token=token, user=user_out)

    finally:
        db.close()


@auth_router.get("/me", response_model=MeResponse)
async def me(user: dict[str, Any] = Depends(_get_current_user)):
    """Return current user info from JWT."""
    return MeResponse(
        email=user["sub"],
        name=user.get("name", ""),
        level=user.get("level", 0),
        level_label=_level_label(user.get("level", 0)),
        roles=user.get("roles", []),
        job_title=user.get("job_title"),
        department=user.get("department"),
    )


# ---------------------------------------------------------------------------
# Admin — System Health
# ---------------------------------------------------------------------------

@admin_router.get("/system-health")
async def system_health(user: dict[str, Any] = Depends(_require_level(3))):
    """Return health status of all integrations."""
    health: dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "integrations": {},
        "mcp_server": "healthy",
    }

    # Database
    try:
        db = SessionLocal()
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        health["integrations"]["database"] = {"status": "healthy"}
        db.close()
    except Exception as e:
        health["integrations"]["database"] = {"status": "error", "detail": str(e)}

    # MCP server port
    health["integrations"]["mcp_server"] = {
        "status": "healthy",
        "port": int(os.getenv("MCP_SERVER_PORT", "8080")),
    }

    # NetSuite credentials present?
    ns_key = os.getenv("NETSUITE_CONSUMER_KEY", "")
    health["integrations"]["netsuite"] = {
        "status": "configured" if ns_key else "not_configured",
        "account_id": os.getenv("NETSUITE_ACCOUNT_ID", ""),
    }

    # Okta
    okta_domain = os.getenv("OKTA_DOMAIN", "")
    health["integrations"]["okta"] = {
        "status": "configured" if okta_domain else "not_configured",
        "domain": okta_domain,
    }

    # Slack
    slack_token = os.getenv("SLACK_BOT_TOKEN", "")
    health["integrations"]["slack"] = {
        "status": "configured" if slack_token else "not_configured",
        "channel": os.getenv("SLACK_CHANNEL", "#compliance-alerts"),
    }

    # Redis
    redis_url = os.getenv("REDIS_URL", "")
    health["integrations"]["redis"] = {
        "status": "configured" if redis_url else "not_configured",
    }

    return health


# ---------------------------------------------------------------------------
# Admin — Configuration (read)
# ---------------------------------------------------------------------------

@admin_router.get("/config")
async def get_config(user: dict[str, Any] = Depends(_require_level(3))):
    """Return all non-secret configuration items."""

    def _mask(val: str) -> str:
        if not val:
            return ""
        return "****" + val[-4:] if len(val) > 4 else "****"

    return {
        "llm": {
            "fast_model": os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-4-5-20251001"),
            "reasoning_model": os.getenv("CLAUDE_MODEL_REASONING", "claude-opus-4-6"),
            "anthropic_api_key_last4": _mask(os.getenv("ANTHROPIC_API_KEY", "")),
            "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2048")),
            "timeout_seconds": int(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
            "max_retries": int(os.getenv("LLM_MAX_RETRIES", "3")),
            "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "openai"),
            "pgvector_dimension": int(os.getenv("PGVECTOR_DIMENSION", "1536")),
        },
        "thresholds": {
            "critical": int(os.getenv("CRITICAL_THRESHOLD", "90")),
            "high": int(os.getenv("HIGH_THRESHOLD", "70")),
            "medium": int(os.getenv("MEDIUM_THRESHOLD", "40")),
        },
        "scheduling": {
            "scan_interval_hours": int(os.getenv("SCAN_INTERVAL_HOURS", "4")),
            "scan_timezone": os.getenv("SCAN_TIMEZONE", "America/New_York"),
            "full_sync_cron": "0 2 * * *",
            "incremental_sync_hours": 1,
            "redis_cache_ttl_seconds": int(os.getenv("REDIS_CACHE_TTL", "86400")),
            "mcp_cache_ttl_seconds": 60,
        },
        "notifications": {
            "notify_critical_immediately": os.getenv("NOTIFY_CRITICAL_IMMEDIATELY", "true").lower() == "true",
            "notify_high_daily": os.getenv("NOTIFY_HIGH_DAILY", "true").lower() == "true",
            "notify_medium_weekly": os.getenv("NOTIFY_MEDIUM_WEEKLY", "true").lower() == "true",
            "notify_low_weekly": os.getenv("NOTIFY_LOW_WEEKLY", "true").lower() == "true",
            "slack_channel": os.getenv("SLACK_CHANNEL", "#compliance-alerts"),
            "slack_webhook_masked": _mask(os.getenv("SLACK_WEBHOOK_URL", "")),
            "sendgrid_from_email": os.getenv("SENDGRID_FROM_EMAIL", ""),
        },
        "integrations": {
            "netsuite": {
                "account_id": os.getenv("NETSUITE_ACCOUNT_ID", ""),
                "restlet_url": os.getenv("NETSUITE_RESTLET_URL", ""),
                "search_restlet_url": os.getenv("NETSUITE_SEARCH_RESTLET_URL", ""),
                "fivetran_restlet_url": os.getenv("NETSUITE_FIVETRAN_RESTLET_URL", ""),
                "api_rate_limit": int(os.getenv("NETSUITE_API_RATE_LIMIT", "10")),
                "page_size": 200,
            },
            "okta": {
                "domain": os.getenv("OKTA_DOMAIN", ""),
                "pagination_limit": 200,
                "request_timeout_seconds": 30,
            },
            "slack": {
                "max_tokens_per_response": int(os.getenv("SLACK_MAX_TOKENS", "1024")),
                "max_history_turns": int(os.getenv("SLACK_MAX_HISTORY_TURNS", "4")),
                "tool_output_max_chars": int(os.getenv("SLACK_TOOL_OUTPUT_MAX_CHARS", "2000")),
            },
        },
        "mcp_server": {
            "host": os.getenv("MCP_SERVER_HOST", "0.0.0.0"),
            "port": int(os.getenv("MCP_SERVER_PORT", "8080")),
            "protocol_version": "2024-11-05",
        },
        "feature_flags": {
            "enable_vector_search": os.getenv("ENABLE_VECTOR_SEARCH", "true").lower() == "true",
            "enable_historical_analysis": os.getenv("ENABLE_HISTORICAL_ANALYSIS", "true").lower() == "true",
            "enable_ml_scoring": os.getenv("ENABLE_ML_SCORING", "false").lower() == "true",
            "use_mcp_cache": os.getenv("USE_MCP_CACHE", "true").lower() == "true",
            "use_conv_summaries": os.getenv("USE_CONV_SUMMARIES", "true").lower() == "true",
            "debug": os.getenv("DEBUG", "false").lower() == "true",
        },
    }


# ---------------------------------------------------------------------------
# Admin — Configuration (write) — L4+ required
# ---------------------------------------------------------------------------

@admin_router.patch("/config/thresholds")
async def update_thresholds(
    body: ThresholdUpdate,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Update risk score thresholds (writes to .env equivalent; restarts needed for full effect)."""
    updates: dict[str, str] = {}
    if body.critical is not None:
        os.environ["CRITICAL_THRESHOLD"] = str(body.critical)
        updates["critical"] = body.critical
    if body.high is not None:
        os.environ["HIGH_THRESHOLD"] = str(body.high)
        updates["high"] = body.high
    if body.medium is not None:
        os.environ["MEDIUM_THRESHOLD"] = str(body.medium)
        updates["medium"] = body.medium

    logger.info(f"Thresholds updated by {user['sub']}: {updates}")
    return {"updated": updates, "note": "Changes applied in-memory. Restart MCP server to persist."}


@admin_router.patch("/config/notifications")
async def update_notifications(
    body: NotificationUpdate,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Update notification settings."""
    updates: dict[str, Any] = {}
    if body.notify_critical_immediately is not None:
        os.environ["NOTIFY_CRITICAL_IMMEDIATELY"] = str(body.notify_critical_immediately).lower()
        updates["notify_critical_immediately"] = body.notify_critical_immediately
    if body.notify_high_daily is not None:
        os.environ["NOTIFY_HIGH_DAILY"] = str(body.notify_high_daily).lower()
        updates["notify_high_daily"] = body.notify_high_daily
    if body.notify_medium_weekly is not None:
        os.environ["NOTIFY_MEDIUM_WEEKLY"] = str(body.notify_medium_weekly).lower()
        updates["notify_medium_weekly"] = body.notify_medium_weekly
    if body.slack_channel is not None:
        os.environ["SLACK_CHANNEL"] = body.slack_channel
        updates["slack_channel"] = body.slack_channel

    logger.info(f"Notifications updated by {user['sub']}: {updates}")
    return {"updated": updates}


@admin_router.patch("/config/scheduling")
async def update_scheduling(
    body: SchedulingUpdate,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Update sync schedule and cache TTL settings."""
    updates: dict[str, Any] = {}
    if body.scan_interval_hours is not None:
        os.environ["SCAN_INTERVAL_HOURS"] = str(body.scan_interval_hours)
        updates["scan_interval_hours"] = body.scan_interval_hours
    if body.redis_cache_ttl_seconds is not None:
        os.environ["REDIS_CACHE_TTL"] = str(body.redis_cache_ttl_seconds)
        updates["redis_cache_ttl_seconds"] = body.redis_cache_ttl_seconds

    logger.info(f"Scheduling updated by {user['sub']}: {updates}")
    return {"updated": updates, "note": "Full/incremental sync schedule changes require server restart."}


@admin_router.patch("/config/feature-flags")
async def update_feature_flags(
    body: FeatureFlagUpdate,
    user: dict[str, Any] = Depends(_require_level(5)),
):
    """Update feature flags — requires CFO-level (L5)."""
    updates: dict[str, Any] = {}
    flag_map = {
        "enable_vector_search": ("ENABLE_VECTOR_SEARCH", body.enable_vector_search),
        "enable_historical_analysis": ("ENABLE_HISTORICAL_ANALYSIS", body.enable_historical_analysis),
        "enable_ml_scoring": ("ENABLE_ML_SCORING", body.enable_ml_scoring),
        "use_mcp_cache": ("USE_MCP_CACHE", body.use_mcp_cache),
        "use_conv_summaries": ("USE_CONV_SUMMARIES", body.use_conv_summaries),
    }
    for key, (env_var, val) in flag_map.items():
        if val is not None:
            os.environ[env_var] = str(val).lower()
            updates[key] = val

    logger.info(f"Feature flags updated by {user['sub']}: {updates}")
    return {"updated": updates}


@admin_router.patch("/config/llm")
async def update_llm_config(
    body: LlmConfigUpdate,
    user: dict[str, Any] = Depends(_require_level(5)),
):
    """Update LLM model selection and token limits — requires L5."""
    updates: dict[str, Any] = {}
    if body.fast_model is not None:
        os.environ["CLAUDE_MODEL_FAST"] = body.fast_model
        updates["fast_model"] = body.fast_model
    if body.reasoning_model is not None:
        os.environ["CLAUDE_MODEL_REASONING"] = body.reasoning_model
        updates["reasoning_model"] = body.reasoning_model
    if body.max_tokens is not None:
        os.environ["LLM_MAX_TOKENS"] = str(body.max_tokens)
        updates["max_tokens"] = body.max_tokens
    if body.temperature is not None:
        os.environ["LLM_TEMPERATURE"] = str(body.temperature)
        updates["temperature"] = body.temperature

    logger.info(f"LLM config updated by {user['sub']}: {updates}")
    return {"updated": updates}


@admin_router.post("/config/test-connection")
async def test_connection(
    payload: dict[str, str],
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Test connectivity for a given integration (netsuite | okta | slack | database)."""
    integration = payload.get("integration", "").lower()
    result: dict[str, Any] = {"integration": integration, "tested_at": datetime.utcnow().isoformat()}

    if integration == "database":
        try:
            db = SessionLocal()
            db.execute(__import__("sqlalchemy").text("SELECT 1"))
            db.close()
            result["status"] = "ok"
        except Exception as e:
            result["status"] = "error"
            result["detail"] = str(e)

    elif integration == "netsuite":
        try:
            from services.netsuite_client import NetSuiteClient
            client = NetSuiteClient()
            sample = client.get_all_users_paginated(page_size=1, include_permissions=False)
            result["status"] = "ok"
            result["sample_count"] = len(sample.get("users", []))
        except Exception as e:
            result["status"] = "error"
            result["detail"] = str(e)

    elif integration == "okta":
        try:
            from connectors.okta_connector import OktaConnector
            OktaConnector()
            result["status"] = "ok"
        except Exception as e:
            result["status"] = "error"
            result["detail"] = str(e)

    else:
        result["status"] = "unknown_integration"
        result["supported"] = ["database", "netsuite", "okta"]

    return result


# ---------------------------------------------------------------------------
# Admin — SOD Rules
# ---------------------------------------------------------------------------

@admin_router.get("/sod-rules")
async def list_sod_rules(user: dict[str, Any] = Depends(_require_level(3))):
    """Return all SOD rules."""
    db = SessionLocal()
    try:
        from repositories.sod_rule_repository import SODRuleRepository
        repo = SODRuleRepository(db)
        rules = repo.get_all_rules()
        return {
            "total": len(rules),
            "rules": [
                {
                    "id": str(r.id),
                    "rule_code": r.rule_code,
                    "rule_name": r.rule_name,
                    "description": r.description,
                    "category": r.risk_category,
                    "severity": r.severity,
                    "is_active": r.is_active,
                    "conflicting_permissions": r.conflicting_permissions,
                }
                for r in rules
            ],
        }
    finally:
        db.close()


@admin_router.patch("/sod-rules/{rule_id}")
async def update_sod_rule(
    rule_id: str,
    body: SODRuleUpdate,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Edit SOD rule (severity, description, active flag) — L4+ required."""
    db = SessionLocal()
    try:
        from repositories.sod_rule_repository import SODRuleRepository
        repo = SODRuleRepository(db)
        rule = repo.get_by_id(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"SOD rule {rule_id} not found")

        updates: dict[str, Any] = {}
        if body.rule_name is not None:
            rule.rule_name = body.rule_name
            updates["rule_name"] = body.rule_name
        if body.description is not None:
            rule.description = body.description
            updates["description"] = body.description
        if body.severity is not None:
            if body.severity not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
                raise HTTPException(status_code=400, detail="severity must be CRITICAL/HIGH/MEDIUM/LOW")
            rule.severity = body.severity
            updates["severity"] = body.severity
        if body.is_active is not None:
            rule.is_active = body.is_active
            updates["is_active"] = body.is_active

        db.commit()
        logger.info(f"SOD rule {rule_id} updated by {user['sub']}: {updates}")
        return {"rule_id": rule_id, "updated": updates}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin — Violations
# ---------------------------------------------------------------------------

@admin_router.get("/violations")
async def list_violations(
    severity: str | None = None,
    status_filter: str | None = None,
    department: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict[str, Any] = Depends(_require_level(3)),
):
    """Return paginated violations with optional filters."""
    db = SessionLocal()
    try:
        from repositories.violation_repository import ViolationRepository
        repo = ViolationRepository(db)

        kwargs: dict[str, Any] = {"limit": limit, "offset": offset}
        if severity:
            kwargs["severity"] = severity

        violations = repo.list_violations(**kwargs)

        return {
            "total": len(violations),
            "limit": limit,
            "offset": offset,
            "violations": [
                {
                    "id": str(v.id),
                    "user_name": v.user_name if hasattr(v, "user_name") else "",
                    "user_email": v.user_email if hasattr(v, "user_email") else "",
                    "rule_name": v.rule_name if hasattr(v, "rule_name") else "",
                    "severity": str(v.severity),
                    "risk_score": float(v.risk_score) if v.risk_score else 0,
                    "status": str(v.status) if hasattr(v, "status") else "OPEN",
                    "detected_at": v.created_at.isoformat() if v.created_at else None,
                }
                for v in violations
            ],
        }
    finally:
        db.close()


@admin_router.patch("/violations/{violation_id}/status")
async def update_violation_status(
    violation_id: str,
    body: ViolationStatusUpdate,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Update violation status (OPEN → IN_REVIEW → RESOLVED)."""
    db = SessionLocal()
    try:
        from repositories.violation_repository import ViolationRepository
        repo = ViolationRepository(db)
        updated = repo.update_status(violation_id, body.new_status, body.notes)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Violation {violation_id} not found")
        logger.info(f"Violation {violation_id} → {body.new_status} by {user['sub']}")
        return {"violation_id": violation_id, "new_status": body.new_status}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin — Exceptions
# ---------------------------------------------------------------------------

@admin_router.get("/exceptions")
async def list_exceptions(
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    user: dict[str, Any] = Depends(_require_level(3)),
):
    """Return paginated approved exceptions."""
    db = SessionLocal()
    try:
        from models.approved_exception import ExceptionStatus
        from repositories.exception_repository import ExceptionRepository
        repo = ExceptionRepository(db)

        status_enum = None
        if status_filter:
            try:
                status_enum = ExceptionStatus[status_filter.upper()]
            except KeyError:
                pass

        exceptions = repo.list_all(status=status_enum, limit=limit, offset=offset)
        stats = repo.get_effectiveness_stats()

        return {
            "total": stats.get("total_exceptions", 0),
            "stats": stats,
            "exceptions": [
                {
                    "exception_id": str(e.exception_id),
                    "exception_code": e.exception_code,
                    "user_name": e.user_name,
                    "user_email": e.user_email,
                    "job_title": e.job_title,
                    "role_names": e.role_names,
                    "conflict_count": e.conflict_count,
                    "risk_score": float(e.risk_score) if e.risk_score else 0,
                    "status": e.status.value if e.status else "ACTIVE",
                    "approved_by": e.approved_by,
                    "approved_date": e.approved_date.isoformat() if e.approved_date else None,
                    "review_frequency": e.review_frequency,
                    "next_review_date": e.next_review_date.isoformat() if e.next_review_date else None,
                    "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                }
                for e in exceptions
            ],
        }
    finally:
        db.close()


@admin_router.get("/exceptions/due-review")
async def exceptions_due_review(user: dict[str, Any] = Depends(_require_level(3))):
    """Return exceptions where next_review_date <= today."""
    db = SessionLocal()
    try:
        from repositories.exception_repository import ExceptionRepository
        repo = ExceptionRepository(db)
        due = repo.get_exceptions_needing_review()

        return {
            "total_due": len(due),
            "exceptions": [
                {
                    "exception_code": e.exception_code,
                    "user_name": e.user_name,
                    "role_names": e.role_names,
                    "next_review_date": e.next_review_date.isoformat() if e.next_review_date else None,
                    "status": e.status.value,
                    "risk_score": float(e.risk_score) if e.risk_score else 0,
                }
                for e in due
            ],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin — Audit Trail
# ---------------------------------------------------------------------------

@admin_router.get("/audit-trail")
async def audit_trail(
    limit: int = 100,
    offset: int = 0,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Return paginated audit log from audit_trail_repository."""
    db = SessionLocal()
    try:
        from repositories.audit_trail_repository import AuditTrailRepository
        repo = AuditTrailRepository(db)
        entries = repo.list_recent(limit=limit, offset=offset)

        return {
            "total": len(entries),
            "entries": [
                {
                    "id": str(e.id) if hasattr(e, "id") else "",
                    "timestamp": e.created_at.isoformat() if hasattr(e, "created_at") else "",
                    "actor": e.actor if hasattr(e, "actor") else "",
                    "entity_type": e.entity_type if hasattr(e, "entity_type") else "",
                    "entity_id": str(e.entity_id) if hasattr(e, "entity_id") else "",
                    "action": e.action if hasattr(e, "action") else "",
                    "changes": e.changes if hasattr(e, "changes") else {},
                }
                for e in entries
            ],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Admin — Token Analytics
# ---------------------------------------------------------------------------

@admin_router.get("/token-analytics")
async def token_analytics(
    days: int = 30,
    user: dict[str, Any] = Depends(_require_level(4)),
):
    """Return LLM token usage and cost summary for the last N days."""
    try:
        from utils.token_tracker import TokenTracker
        tracker = TokenTracker()
        summary = tracker.get_summary(days=days)
        return {"period_days": days, "summary": summary}
    except Exception as e:
        logger.warning(f"TokenTracker not available: {e}")
        return {
            "period_days": days,
            "summary": {
                "note": "Token analytics not available (LangSmith provides this via smith.langchain.com)",
                "langsmith_project": os.getenv("LANGCHAIN_PROJECT", "compliance-agent"),
            },
        }
