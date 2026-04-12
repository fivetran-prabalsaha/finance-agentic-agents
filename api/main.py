"""
FastAPI Application - REST API for Compliance System

This API provides endpoints for:
1. User management and querying
2. Violation management
3. Risk assessment
4. Compliance scanning
5. Notifications
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from agents.notifier import create_notifier
from agents.orchestrator import create_orchestrator
from agents.risk_assessor import create_risk_assessor
from models.database_config import DatabaseConfig, get_session
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.netsuite_client import NetSuiteClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Compliance API")
    db_config = DatabaseConfig()
    if not db_config.test_connection():
        logger.error("Database connection failed!")
    else:
        logger.info("Database connection successful")

    yield

    # Shutdown
    logger.info("Shutting down Compliance API")


# Initialize FastAPI app
app = FastAPI(
    title="SOD Compliance API",
    description="REST API for SOD Compliance and Risk Assessment System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models (Request/Response schemas)
# ============================================================================

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str | None
    department: str | None
    status: str
    roles_count: int


class ViolationResponse(BaseModel):
    id: str
    user_email: str
    rule_name: str
    severity: str
    risk_score: float
    status: str
    detected_at: str


class RiskScoreResponse(BaseModel):
    user_id: str
    user_email: str
    risk_score: float
    risk_level: str
    violations_count: int


class ScanRequest(BaseModel):
    scan_id: str | None = None
    notify_recipients: list[EmailStr] | None = []


class UserScanRequest(BaseModel):
    user_email: EmailStr


class NotificationRequest(BaseModel):
    recipients: list[EmailStr]
    channels: list[str] = ["EMAIL", "SLACK"]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: str
    version: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_repositories():
    """Dependency to get repository instances"""
    session = next(get_session())
    try:
        yield {
            'user_repo': UserRepository(session),
            'role_repo': RoleRepository(session),
            'violation_repo': ViolationRepository(session)
        }
    finally:
        session.close()


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_config = DatabaseConfig()
    db_status = "healthy" if db_config.test_connection() else "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "1.0.0"
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "SOD Compliance API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# User Endpoints
# ============================================================================

@app.get("/api/users", tags=["Users"])
async def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    repos=Depends(get_repositories)
):
    """Get list of users"""
    try:
        users = repos['user_repo'].get_all_users()
        users_slice = users[offset:offset+limit]

        return {
            "total": len(users),
            "limit": limit,
            "offset": offset,
            "users": [
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "name": user.name,
                    "department": user.department,
                    "status": user.status.value,
                    "roles_count": len(user.user_roles)
                }
                for user in users_slice
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_email}", tags=["Users"])
async def get_user(user_email: str, repos=Depends(get_repositories)):
    """Get specific user by email"""
    try:
        user = repos['user_repo'].get_user_by_email(user_email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "department": user.department,
            "title": user.title,
            "status": user.status.value,
            "roles": [
                {
                    "role_id": ur.role.role_id,
                    "role_name": ur.role.name,
                    "permissions_count": len(ur.role.permissions) if ur.role.permissions else 0
                }
                for ur in user.user_roles
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_email}/violations", tags=["Users"])
async def get_user_violations(user_email: str, repos=Depends(get_repositories)):
    """Get all violations for a user"""
    try:
        user = repos['user_repo'].get_user_by_email(user_email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        violations = repos['violation_repo'].get_violations_by_user(str(user.id))

        return {
            "user_email": user_email,
            "total_violations": len(violations),
            "violations": [
                {
                    "id": str(v.id),
                    "rule_name": v.rule.rule_name if v.rule else "Unknown",
                    "severity": v.severity.value,
                    "risk_score": v.risk_score,
                    "status": v.status.value,
                    "detected_at": v.detected_at.isoformat() if v.detected_at else None
                }
                for v in violations
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching violations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/{user_email}/risk", tags=["Users"])
async def get_user_risk(user_email: str, repos=Depends(get_repositories)):
    """Get risk score for a user"""
    try:
        user = repos['user_repo'].get_user_by_email(user_email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        risk_assessor = create_risk_assessor(
            violation_repo=repos['violation_repo'],
            user_repo=repos['user_repo']
        )

        result = risk_assessor.calculate_user_risk_score(str(user.id))

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating risk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Violation Endpoints
# ============================================================================

@app.get("/api/violations", tags=["Violations"])
async def list_violations(
    severity: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    repos=Depends(get_repositories)
):
    """Get list of violations"""
    try:
        from models.database import ViolationSeverity, ViolationStatus

        # Convert string to enum if provided
        severity_enum = ViolationSeverity[severity] if severity else None
        status_enum = ViolationStatus[status] if status else None

        violations = repos['violation_repo'].get_open_violations(
            severity=severity_enum
        )

        # Filter by status if provided
        if status_enum:
            violations = [v for v in violations if v.status == status_enum]

        violations = violations[:limit]

        return {
            "total": len(violations),
            "violations": [
                {
                    "id": str(v.id),
                    "user_email": v.user.email if v.user else "Unknown",
                    "rule_name": v.rule.rule_name if v.rule else "Unknown",
                    "severity": v.severity.value,
                    "risk_score": v.risk_score,
                    "status": v.status.value,
                    "detected_at": v.detected_at.isoformat() if v.detected_at else None
                }
                for v in violations
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching violations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/violations/summary", tags=["Violations"])
async def get_violations_summary(repos=Depends(get_repositories)):
    """Get violation summary statistics"""
    try:
        summary = repos['violation_repo'].get_violation_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Compliance Scan Endpoints
# ============================================================================

@app.post("/api/scans/full", tags=["Scans"])
async def run_full_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    repos=Depends(get_repositories)
):
    """Trigger a full compliance scan"""
    try:
        netsuite_client = NetSuiteClient()

        orchestrator = create_orchestrator(
            netsuite_client=netsuite_client,
            user_repo=repos['user_repo'],
            role_repo=repos['role_repo'],
            violation_repo=repos['violation_repo'],
            notification_recipients=scan_request.notify_recipients
        )

        scan_id = scan_request.scan_id or f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Run scan in background
        background_tasks.add_task(
            orchestrator.execute_compliance_scan,
            scan_id=scan_id
        )

        return {
            "message": "Compliance scan started",
            "scan_id": scan_id,
            "status": "RUNNING",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting scan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scans/user", tags=["Scans"])
async def scan_user(
    request: UserScanRequest,
    repos=Depends(get_repositories)
):
    """Scan a specific user"""
    try:
        netsuite_client = NetSuiteClient()

        orchestrator = create_orchestrator(
            netsuite_client=netsuite_client,
            user_repo=repos['user_repo'],
            role_repo=repos['role_repo'],
            violation_repo=repos['violation_repo']
        )

        result = orchestrator.execute_user_scan(request.user_email)

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Risk Assessment Endpoints
# ============================================================================

@app.get("/api/risk/organization", tags=["Risk Assessment"])
async def get_organization_risk(repos=Depends(get_repositories)):
    """Get organization-wide risk assessment"""
    try:
        risk_assessor = create_risk_assessor(
            violation_repo=repos['violation_repo'],
            user_repo=repos['user_repo']
        )

        result = risk_assessor.assess_organization_risk()

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing organization risk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Notification Endpoints
# ============================================================================

@app.post("/api/notifications/critical", tags=["Notifications"])
async def send_critical_notifications(
    request: NotificationRequest,
    repos=Depends(get_repositories)
):
    """Send notifications for critical violations"""
    try:
        notifier = create_notifier(
            violation_repo=repos['violation_repo'],
            user_repo=repos['user_repo']
        )

        result = notifier.notify_critical_violations_batch(
            recipients=request.recipients,
            channels=request.channels
        )

        return result
    except Exception as e:
        logger.error(f"Error sending notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Statistics Endpoints
# ============================================================================

@app.get("/api/stats/dashboard", tags=["Statistics"])
async def get_dashboard_stats(repos=Depends(get_repositories)):
    """Get dashboard statistics"""
    try:
        # Get violation summary
        violation_summary = repos['violation_repo'].get_violation_summary()

        # Get user stats
        all_users = repos['user_repo'].get_all_users()
        active_users = [u for u in all_users if u.status.value == 'ACTIVE']

        # Get high-risk users
        high_risk_users = repos['user_repo'].get_high_risk_users(min_roles=3)

        return {
            "users": {
                "total": len(all_users),
                "active": len(active_users),
                "high_risk": len(high_risk_users)
            },
            "violations": violation_summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
