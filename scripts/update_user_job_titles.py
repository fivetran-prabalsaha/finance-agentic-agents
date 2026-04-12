"""
Update User Job Titles from NetSuite

Triggers a manual sync to fetch job titles for all existing users
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connectors.netsuite_connector import NetSuiteConnector
from models.database_config import DatabaseConfig
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_job_titles():
    """Fetch users from NetSuite and update job titles"""

    logger.info("=" * 80)
    logger.info("UPDATING USER JOB TITLES FROM NETSUITE")
    logger.info("=" * 80)

    # Initialize database
    db_config = DatabaseConfig()
    session = db_config.get_session()

    user_repo = UserRepository(session)
    RoleRepository(session)

    # Initialize NetSuite connector
    try:
        connector = NetSuiteConnector()
        logger.info("✅ NetSuite connector initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize NetSuite connector: {str(e)}")
        return

    # Fetch users from NetSuite
    logger.info("\n📥 Fetching users from NetSuite...")
    try:
        users = connector.fetch_users_with_roles_sync(
            include_permissions=False,  # Don't need permissions, just user data
            include_inactive=False
        )
        logger.info(f"✅ Fetched {len(users)} users from NetSuite")
    except Exception as e:
        logger.error(f"❌ Failed to fetch users: {str(e)}")
        return

    # Update job titles
    logger.info("\n🔄 Updating user job titles in database...")

    updated_count = 0
    skipped_count = 0
    title_set_count = 0

    for user_data in users:
        email = user_data.get('email')
        if not email:
            continue

        # DEBUG: Log available fields for prabal.saha@fivetran.com
        if email == 'prabal.saha@fivetran.com':
            logger.info(f"\n🔍 DEBUG: Available fields for {email}:")
            logger.info(f"   Fields: {list(user_data.keys())}")
            for key in ['title', 'jobTitle', 'jobtitle', 'job_title', 'jobTitle.name', 'title.name']:
                value = user_data.get(key)
                if value:
                    logger.info(f"   • {key}: {value}")

        # Extract job title using same logic as connector
        job_title = (
            user_data.get('title') or
            user_data.get('jobTitle') or
            user_data.get('jobtitle') or
            user_data.get('job_title') or
            user_data.get('jobTitle.name') or
            user_data.get('title.name') or
            None
        )

        # Get existing user
        user = user_repo.get_user_by_email(email)
        if not user:
            skipped_count += 1
            continue

        # SAFETY: Don't clear existing titles if NetSuite returns None
        # Only update if we have a new title, or if existing title is None
        if job_title is None and user.title is not None:
            logger.debug(f"   Skipping {email}: NetSuite returned no title, keeping existing '{user.title}'")
            continue

        # Update only if job title changed
        if user.title != job_title:
            old_title = user.title or "(not set)"
            new_title = job_title or "(not set)"

            user.title = job_title
            session.commit()

            logger.info(f"   • {user.name:30} | {old_title:25} → {new_title:25}")
            updated_count += 1

            if job_title:
                title_set_count += 1

    logger.info("\n" + "=" * 80)
    logger.info("UPDATE COMPLETE")
    logger.info(f"✅ Updated: {updated_count} users")
    logger.info(f"   • Job titles set: {title_set_count}")
    logger.info(f"   • Job titles cleared: {updated_count - title_set_count}")
    logger.info(f"⏭️  Skipped: {skipped_count} (not in database)")
    logger.info("=" * 80)

    # Show statistics
    logger.info("\n📊 CURRENT DATABASE STATISTICS")
    total_users = session.execute(text("SELECT COUNT(*) FROM users WHERE status = 'ACTIVE'")).scalar()
    with_title = session.execute(text("SELECT COUNT(*) FROM users WHERE status = 'ACTIVE' AND title IS NOT NULL AND title != ''")).scalar()
    without_title = total_users - with_title

    logger.info(f"   Total Active Users: {total_users}")
    logger.info(f"   With Job Title: {with_title} ({with_title*100//total_users if total_users > 0 else 0}%)")
    logger.info(f"   Without Job Title: {without_title} ({without_title*100//total_users if total_users > 0 else 0}%)")

    # Show sample of users with titles
    logger.info("\n📋 SAMPLE USERS WITH JOB TITLES (First 10):")
    sample_users = session.execute(text("""
        SELECT name, email, title, department
        FROM users
        WHERE status = 'ACTIVE' AND title IS NOT NULL AND title != ''
        LIMIT 10
    """)).fetchall()

    for user in sample_users:
        logger.info(f"   • {user[0]:30} | {user[2]:30} | {user[3] or 'N/A'}")

    # Show users without titles (potential issue)
    logger.info("\n⚠️  USERS WITHOUT JOB TITLES (First 10):")
    no_title_users = session.execute(text("""
        SELECT name, email, department
        FROM users
        WHERE status = 'ACTIVE' AND (title IS NULL OR title = '')
        LIMIT 10
    """)).fetchall()

    if no_title_users:
        for user in no_title_users:
            logger.info(f"   • {user[0]:30} | {user[1]:40} | {user[2] or 'N/A'}")
        logger.info(f"\n   Note: {without_title} total users missing job titles")
        logger.info("   This likely means NetSuite doesn't have job titles set for these employees")
    else:
        logger.info("   ✅ All active users have job titles set!")


if __name__ == "__main__":
    try:
        update_job_titles()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
