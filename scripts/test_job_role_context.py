"""
Test Job Role Context-Aware Analysis

Tests the new job role mapping integration with prabal.saha@fivetran.com
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from agents.notifier import NotificationAgent
from models.database_config import DatabaseConfig
from repositories.job_role_mapping_repository import JobRoleMappingRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_prabal_saha():
    """Test job role context for prabal.saha@fivetran.com"""

    logger.info("=" * 80)
    logger.info("TESTING JOB ROLE CONTEXT-AWARE ANALYSIS")
    logger.info("User: prabal.saha@fivetran.com")
    logger.info("=" * 80)

    # Initialize database
    db_config = DatabaseConfig()
    session = db_config.get_session()

    # Initialize repositories
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)
    job_role_repo = JobRoleMappingRepository(session)

    # Get user
    user = user_repo.get_user_by_email("prabal.saha@fivetran.com")

    if not user:
        logger.error("❌ User not found: prabal.saha@fivetran.com")
        return

    logger.info("\n📋 USER INFORMATION")
    logger.info(f"   Name: {user.name}")
    logger.info(f"   Email: {user.email}")
    logger.info(f"   Job Title: {user.title or 'NOT SET'}")
    logger.info(f"   Department: {user.department or 'NOT SET'}")
    logger.info(f"   Status: {user.status}")

    # Get user roles
    role_names = [ur.role.role_name for ur in user.user_roles]
    logger.info(f"\n🎭 ASSIGNED ROLES ({len(role_names)})")
    for role in role_names:
        logger.info(f"   • {role}")

    # Get violations
    violations = violation_repo.get_violations_by_user(user.id)
    logger.info(f"\n🚨 VIOLATIONS FOUND: {len(violations)}")

    if violations:
        severity_counts = {}
        for v in violations:
            severity = v.severity.value if hasattr(v.severity, 'value') else str(v.severity)
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in severity_counts.items():
            logger.info(f"   • {severity}: {count}")

    # CHECK JOB ROLE MAPPING (THE FIX)
    logger.info("\n🔍 JOB ROLE CONTEXT ANALYSIS")

    if not user.title:
        logger.warning("   ⚠️  No job title set for user - cannot perform context-aware analysis")
    else:
        # Check if role combination is acceptable for job title
        validation = job_role_repo.check_role_combination_acceptable(
            user.title,
            role_names
        )

        logger.info(f"   Job Title: {user.title}")
        logger.info(f"   Is Acceptable: {validation.get('is_acceptable')}")
        logger.info(f"   Requires Controls: {validation.get('requires_controls')}")

        if validation.get('is_acceptable'):
            logger.info("\n✅ ACCEPTABLE CONFIGURATION")
            logger.info("   Business Justification:")
            justification = validation.get('business_justification', '')
            for line in justification.split('.'):
                if line.strip():
                    logger.info(f"   • {line.strip()}")

            logger.info("\n🛡️  REQUIRED COMPENSATING CONTROLS:")
            controls = validation.get('typical_controls', [])
            for control in controls:
                logger.info(f"   • {control}")

            approval = validation.get('approval_required', '')
            if approval:
                logger.info(f"\n📝 APPROVAL REQUIRED: {approval}")

            logger.info("\n💡 RECOMMENDATION:")
            logger.info(f"   This is the PROPER configuration for {user.title}.")
            logger.info("   Focus on implementing compensating controls, NOT role removal.")
            logger.info("   This is a legitimate business need, not a compliance violation.")

        else:
            logger.info("\n❌ NOT ACCEPTABLE CONFIGURATION")
            reason = validation.get('reason', '')
            logger.info(f"   Reason: {reason}")

            expected = validation.get('expected_roles', [])
            if expected:
                logger.info("\n   Expected Role Combinations:")
                for combo in expected:
                    logger.info(f"   • {combo}")

    # Test AI Analysis with new context
    logger.info("\n🤖 TESTING AI ANALYSIS WITH JOB ROLE CONTEXT")
    logger.info("=" * 80)

    try:
        notifier = NotificationAgent(
            violation_repo=violation_repo,
            user_repo=user_repo,
            job_role_mapping_repo=job_role_repo,
            enable_cache=False  # Disable cache for testing
        )

        if violations:
            logger.info("Generating AI analysis with job role context...")
            ai_analysis = notifier._generate_ai_analysis(user, violations, role_names)

            logger.info("\n" + "=" * 80)
            logger.info("AI ANALYSIS OUTPUT:")
            logger.info("=" * 80)
            print(ai_analysis)
            logger.info("=" * 80)
        else:
            logger.info("No violations to analyze")

    except Exception as e:
        logger.error(f"Error generating AI analysis: {str(e)}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_prabal_saha()
