#!/usr/bin/env python3
"""
Sync from NetSuite - Fetch users and roles from NetSuite and store in database

This script:
1. Fetches users and roles from NetSuite via the Data Collection Agent
2. Stores them in PostgreSQL using repositories
3. Reports statistics
"""

import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from agents.data_collector import DataCollectionAgent
from models.database import UserStatus
from models.database_config import get_db_config
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def sync_users_and_roles(limit: int = 100, include_permissions: bool = True):
    """
    Sync users and roles from NetSuite to database

    Args:
        limit: Number of users to fetch
        include_permissions: Whether to fetch full permission details
    """
    print("\n" + "=" * 80)
    print("  SYNC FROM NETSUITE TO DATABASE")
    print("=" * 80 + "\n")

    # Initialize agent
    print("1. Initializing Data Collection Agent...")
    agent = DataCollectionAgent()
    print("   ✓ Agent ready\n")

    # Test NetSuite connection
    print("2. Testing NetSuite connection...")
    if not agent.test_connection():
        print("   ✗ NetSuite connection failed!")
        return
    print("   ✓ Connected to NetSuite\n")

    # Test database connection
    print("3. Testing database connection...")
    db_config = get_db_config()
    if not db_config.test_connection():
        print("   ✗ Database connection failed!")
        return
    print("   ✓ Connected to database\n")

    # Fetch users from NetSuite
    print(f"4. Fetching {limit} users from NetSuite...")
    start_time = datetime.now()

    result = agent.netsuite_client.get_users_and_roles(
        limit=limit,
        include_permissions=include_permissions
    )

    if not result.get('success'):
        print(f"   ✗ Error: {result.get('error')}")
        return

    users_data = result['data']['users']
    fetch_time = (datetime.now() - start_time).total_seconds()

    print(f"   ✓ Fetched {len(users_data)} users in {fetch_time:.2f}s\n")

    # Store in database
    print("5. Storing data in database...")
    session = db_config.get_session()

    try:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)

        # Extract unique roles
        roles_map = {}
        for user in users_data:
            for role in user.get('roles', []):
                role_id = role['role_id']
                if role_id not in roles_map:
                    roles_map[role_id] = {
                        'role_id': role_id,
                        'role_name': role['role_name'],
                        'is_custom': role.get('is_custom', False),
                        'permissions': role.get('permissions', []),
                        'permission_count': len(role.get('permissions', []))
                    }

        # Upsert roles
        print(f"   • Upserting {len(roles_map)} roles...")
        roles_created = role_repo.bulk_upsert_roles(list(roles_map.values()))
        print(f"     ✓ {roles_created} roles processed")

        # Upsert users
        print(f"   • Upserting {len(users_data)} users...")
        users_created = 0
        roles_assigned = 0

        for user_data in users_data:
            # Prepare user data
            user_info = {
                'user_id': user_data['user_id'],
                'internal_id': user_data.get('internal_id'),
                'name': user_data['name'],
                'email': user_data['email'],
                'status': user_data.get('status', 'ACTIVE'),
                'department': user_data.get('department'),
                'subsidiary': user_data.get('subsidiary'),
                'employee_id': user_data.get('employee_id'),
                'last_login': user_data.get('last_login')
            }

            # Upsert user
            user = user_repo.upsert_user(user_info)
            users_created += 1

            # Assign roles
            for role_data in user_data.get('roles', []):
                role = role_repo.get_role_by_id(role_data['role_id'])
                if role:
                    try:
                        user_repo.assign_role_to_user(
                            user_id=str(user.id),
                            role_id=str(role.id),
                            assigned_by='NetSuite Sync'
                        )
                        roles_assigned += 1
                    except Exception:
                        # Role already assigned
                        pass

        print(f"     ✓ {users_created} users processed")
        print(f"     ✓ {roles_assigned} role assignments created\n")

        session.commit()

    except Exception as e:
        logger.error(f"Error storing data: {str(e)}")
        session.rollback()
        print(f"   ✗ Error: {str(e)}\n")
        return
    finally:
        session.close()

    # Get statistics
    print("6. Database statistics:")
    session = db_config.get_session()
    try:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)

        total_users = user_repo.get_user_count()
        active_users = user_repo.get_user_count(status=UserStatus.ACTIVE)
        total_roles = role_repo.get_role_count()
        high_risk_users = len(user_repo.get_high_risk_users(min_roles=3))

        print(f"   • Total users: {total_users}")
        print(f"   • Active users: {active_users}")
        print(f"   • Total roles: {total_roles}")
        print(f"   • High-risk users (3+ roles): {high_risk_users}")

        # Show sample users
        print("\n   Sample users in database:")
        users = user_repo.get_all_users(limit=5)
        for user in users:
            role_count = len(user.user_roles)
            print(f"     • {user.name} ({user.email}) - {role_count} roles")

    finally:
        session.close()

    print("\n" + "=" * 80)
    print("  ✓ SYNC COMPLETE")
    print("=" * 80 + "\n")

    print("Next steps:")
    print("  • View users: python3 -c \"from scripts.query_database import show_users; show_users()\"")
    print("  • Run demo with database: python3 demo_with_database.py")
    print("  • Query database: psql $DATABASE_URL")
    print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Sync NetSuite data to database')
    parser.add_argument('--limit', type=int, default=100, help='Number of users to fetch')
    parser.add_argument('--no-permissions', action='store_true', help='Skip permission details (faster)')

    args = parser.parse_args()

    sync_users_and_roles(
        limit=args.limit,
        include_permissions=not args.no_permissions
    )


if __name__ == '__main__':
    main()
