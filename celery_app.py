"""
Celery Application - Background job processing

This module defines Celery tasks for:
1. Scheduled compliance scans
2. Periodic risk assessments
3. Notification delivery
4. Data synchronization
"""

import logging
import os
from datetime import datetime

from celery import Celery
from celery.schedules import crontab

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'compliance_agent',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Celery Beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    'compliance-scan-every-4-hours': {
        'task': 'celery_app.run_compliance_scan',
        'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
        'args': ()
    },
    'risk-assessment-daily': {
        'task': 'celery_app.run_risk_assessment',
        'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
        'args': ()
    },
    'cleanup-old-data-weekly': {
        'task': 'celery_app.cleanup_old_data',
        'schedule': crontab(minute=0, hour=3, day_of_week=0),  # Sunday 3 AM
        'args': ()
    },
}


@celery_app.task(name='celery_app.run_compliance_scan', bind=True, max_retries=3)
def run_compliance_scan(self):
    """
    Scheduled task: Run full compliance scan

    Executes every 4 hours via Celery Beat
    """
    logger.info("Starting scheduled compliance scan")

    try:
        from agents.orchestrator import create_orchestrator
        from models.database_config import get_session
        from repositories.role_repository import RoleRepository
        from repositories.sod_rule_repository import SODRuleRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository
        from services.netsuite_client import NetSuiteClient

        # Get notification recipients from environment
        recipients = os.getenv('COMPLIANCE_NOTIFICATION_EMAILS', '').split(',')
        recipients = [r.strip() for r in recipients if r.strip()]

        with get_session() as session:
            user_repo = UserRepository(session)
            role_repo = RoleRepository(session)
            violation_repo = ViolationRepository(session)
            sod_rule_repo = SODRuleRepository(session)
            netsuite_client = NetSuiteClient()

            # Create orchestrator
            orchestrator = create_orchestrator(
                netsuite_client=netsuite_client,
                user_repo=user_repo,
                role_repo=role_repo,
                violation_repo=violation_repo,
                sod_rule_repo=sod_rule_repo,
                notification_recipients=recipients
            )

            # Execute scan
            scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            result = orchestrator.execute_compliance_scan(scan_id=scan_id)

            logger.info(f"Compliance scan complete: {result['summary']}")

            return {
                'status': 'SUCCESS',
                'scan_id': scan_id,
                'summary': result['summary'],
                'timestamp': result['timestamp']
            }

    except Exception as e:
        logger.error(f"Compliance scan failed: {str(e)}")

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=300)  # Retry after 5 minutes


@celery_app.task(name='celery_app.run_risk_assessment', bind=True)
def run_risk_assessment(self):
    """
    Scheduled task: Run organization-wide risk assessment

    Executes daily at 2 AM via Celery Beat
    """
    logger.info("Starting scheduled risk assessment")

    try:
        from agents.risk_assessor import create_risk_assessor
        from models.database_config import get_session
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        with get_session() as session:
            user_repo = UserRepository(session)
            violation_repo = ViolationRepository(session)

            # Create risk assessor
            risk_assessor = create_risk_assessor(
                violation_repo=violation_repo,
                user_repo=user_repo
            )

            # Run assessment
            result = risk_assessor.assess_organization_risk()

            logger.info(
                f"Risk assessment complete: "
                f"Organization risk = {result['organization_risk_level']}"
            )

            return {
                'status': 'SUCCESS',
                'organization_risk_level': result['organization_risk_level'],
                'organization_risk_score': result['organization_risk_score'],
                'timestamp': result['timestamp']
            }

    except Exception as e:
        logger.error(f"Risk assessment failed: {str(e)}")
        return {
            'status': 'FAILED',
            'error': str(e)
        }


@celery_app.task(name='celery_app.analyze_user', bind=True, max_retries=2)
def analyze_user(self, user_email: str):
    """
    Ad-hoc task: Analyze a specific user

    Args:
        user_email: User email to analyze

    Returns:
        Analysis results
    """
    logger.info(f"Analyzing user: {user_email}")

    try:
        from agents.orchestrator import create_orchestrator
        from models.database_config import get_session
        from repositories.role_repository import RoleRepository
        from repositories.sod_rule_repository import SODRuleRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository
        from services.netsuite_client import NetSuiteClient

        with get_session() as session:
            user_repo = UserRepository(session)
            role_repo = RoleRepository(session)
            violation_repo = ViolationRepository(session)
            sod_rule_repo = SODRuleRepository(session)
            netsuite_client = NetSuiteClient()

            orchestrator = create_orchestrator(
                netsuite_client=netsuite_client,
                user_repo=user_repo,
                role_repo=role_repo,
                violation_repo=violation_repo,
                sod_rule_repo=sod_rule_repo
            )

            result = orchestrator.execute_user_scan(user_email)

            logger.info(f"User analysis complete: {result}")

            return result

    except Exception as e:
        logger.error(f"User analysis failed: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name='celery_app.send_violation_alert', bind=True)
def send_violation_alert(self, violation_id: str, recipients: list):
    """
    Ad-hoc task: Send alert for a specific violation

    Args:
        violation_id: Violation UUID
        recipients: List of email addresses

    Returns:
        Notification result
    """
    logger.info(f"Sending alert for violation: {violation_id}")

    try:
        from agents.notifier import create_notifier
        from models.database_config import get_session
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        with get_session() as session:
            user_repo = UserRepository(session)
            violation_repo = ViolationRepository(session)

            # Get violation
            violation = violation_repo.get_violation_by_id(violation_id)

            if not violation:
                logger.error(f"Violation not found: {violation_id}")
                return {
                    'status': 'FAILED',
                    'error': 'Violation not found'
                }

            # Create notifier
            notifier = create_notifier(
                violation_repo=violation_repo,
                user_repo=user_repo
            )

            # Send notification
            result = notifier.notify_violation_detected(
                violation=violation,
                recipients=recipients,
                channels=['EMAIL', 'SLACK']
            )

            logger.info(f"Alert sent: {result}")

            return result

    except Exception as e:
        logger.error(f"Alert failed: {str(e)}")
        return {
            'status': 'FAILED',
            'error': str(e)
        }


@celery_app.task(name='celery_app.sync_netsuite_data', bind=True, max_retries=3)
def sync_netsuite_data(self):
    """
    Scheduled task: Sync data from NetSuite

    Can be triggered manually or scheduled
    """
    logger.info("Starting NetSuite data sync")

    try:
        from agents.data_collector import DataCollectionAgent
        from models.database_config import get_session
        from repositories.role_repository import RoleRepository
        from repositories.user_repository import UserRepository
        from services.netsuite_client import NetSuiteClient

        with get_session() as session:
            user_repo = UserRepository(session)
            role_repo = RoleRepository(session)
            netsuite_client = NetSuiteClient()

            # Create data collector
            data_collector = DataCollectionAgent(netsuite_client=netsuite_client)

            # Fetch data
            result = data_collector.fetch_users_from_netsuite(
                include_permissions=True,
                status='ACTIVE'
            )

            if result['success']:
                users = result['data']

                # Store in database
                for user_data in users:
                    # Store user and get database object with UUID
                    user = user_repo.upsert_user(user_data)

                    for role_data in user_data.get('roles', []):
                        # Store role and get database object with UUID
                        role = role_repo.upsert_role(role_data)
                        # Use database UUIDs (not NetSuite IDs)
                        user_repo.assign_role_to_user(
                            str(user.id),  # Database UUID
                            str(role.id)   # Database UUID
                        )

                logger.info(f"Data sync complete: {len(users)} users synced")

                return {
                    'status': 'SUCCESS',
                    'users_synced': len(users),
                    'timestamp': result['timestamp']
                }
            else:
                raise Exception(result.get('error', 'Unknown error'))

    except Exception as e:
        logger.error(f"Data sync failed: {str(e)}")
        raise self.retry(exc=e, countdown=600)  # Retry after 10 minutes


@celery_app.task(name='celery_app.cleanup_old_data', bind=True)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Scheduled task: Cleanup old resolved violations and audit logs

    Executes weekly on Sunday at 3 AM

    Args:
        days_to_keep: Number of days of data to keep
    """
    logger.info(f"Starting data cleanup (keeping last {days_to_keep} days)")

    try:
        from datetime import timedelta

        from sqlalchemy import and_

        from models.database import AuditTrail, Violation, ViolationStatus
        from models.database_config import get_session

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        with get_session() as session:
            # Delete old resolved violations
            deleted_violations = session.query(Violation).filter(
                and_(
                    Violation.status == ViolationStatus.RESOLVED,
                    Violation.resolved_at < cutoff_date
                )
            ).delete()

            # Delete old audit logs
            deleted_logs = session.query(AuditTrail).filter(
                AuditTrail.created_at < cutoff_date
            ).delete()

            session.commit()

            logger.info(
                f"Cleanup complete: {deleted_violations} violations, "
                f"{deleted_logs} audit logs deleted"
            )

            return {
                'status': 'SUCCESS',
                'violations_deleted': deleted_violations,
                'logs_deleted': deleted_logs,
                'cutoff_date': cutoff_date.isoformat()
            }

    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return {
            'status': 'FAILED',
            'error': str(e)
        }


# Task monitoring
@celery_app.task(name='celery_app.get_task_status')
def get_task_status(task_id: str):
    """
    Get status of a Celery task

    Args:
        task_id: Celery task ID

    Returns:
        Task status and result
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    return {
        'task_id': task_id,
        'state': result.state,
        'info': result.info,
        'ready': result.ready(),
        'successful': result.successful() if result.ready() else None
    }


if __name__ == '__main__':
    # For testing tasks
    logger.info("Celery app initialized")
    logger.info(f"Broker: {celery_app.conf.broker_url}")
    logger.info(f"Backend: {celery_app.conf.result_backend}")
    logger.info("Available tasks:")
    for task_name in celery_app.tasks:
        if not task_name.startswith('celery.'):
            logger.info(f"  - {task_name}")
