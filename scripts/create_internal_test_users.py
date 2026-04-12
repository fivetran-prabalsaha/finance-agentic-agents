#!/usr/bin/env python3
"""
Create Internal Test Users

Creates anonymized test users for internal demos by copying real user profiles
but with different names/emails. Keeps all roles, violations, and department
structure identical for realistic testing.

Usage:
    # Create both test users (based on Robin Turner and Chase Roles)
    python3 scripts/create_internal_test_users.py --create

    # Create specific test user
    python3 scripts/create_internal_test_users.py --create --user test-user-a

    # Delete test users
    python3 scripts/create_internal_test_users.py --delete

    # List test users
    python3 scripts/create_internal_test_users.py --list
"""

import argparse
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from models.database import (
    Role,
    User,
    UserRole,
    UserStatus,
    Violation,
    ViolationStatus,
)
from models.database_config import get_db_config

# Test user configurations
TEST_USERS = {
    'test-user-a': {
        'source_email': 'robin.turner@fivetran.com',
        'test_name': 'Test User A',
        'test_email': 'test.user.a@fivetran.com',
        'description': 'High-violation Finance user (mimics Robin Turner)'
    },
    'test-user-b': {
        'source_email': 'chase.roles@fivetran.com',
        'test_name': 'Test User B',
        'test_email': 'test.user.b@fivetran.com',
        'description': 'Multiple-role user (mimics Chase Roles)'
    }
}


def create_test_user(source_email: str, test_name: str, test_email: str, description: str):
    """
    Create a test user by copying an existing user's profile

    Args:
        source_email: Email of user to copy from
        test_name: Name for test user
        test_email: Email for test user
        description: Description of test user
    """
    db_config = get_db_config()
    session = db_config.get_session()

    try:
        print(f"\n{'='*70}")
        print(f"Creating test user: {test_name}")
        print(f"Source: {source_email}")
        print(f"Description: {description}")
        print(f"{'='*70}\n")

        # 1. Check if test user already exists
        existing = session.query(User).filter_by(email=test_email).first()
        if existing:
            print(f"❌ Test user {test_email} already exists!")
            print("   Use --delete first to remove existing test user")
            return False

        # 2. Find source user
        print(f"📥 Finding source user: {source_email}")
        source_user = session.query(User).filter_by(email=source_email).first()

        if not source_user:
            print(f"❌ Source user not found: {source_email}")
            return False

        print(f"✅ Found source user: {source_user.name}")
        print(f"   Department: {source_user.department}")
        print(f"   Job Title: {source_user.title or 'N/A'}")

        # 3. Get source user's roles
        print("\n📋 Copying roles...")
        source_roles = session.query(UserRole).filter_by(user_id=source_user.id).all()
        print(f"   Found {len(source_roles)} roles to copy")

        role_details = []
        for ur in source_roles:
            role = session.query(Role).filter_by(id=ur.role_id).first()  # ur.role_id is FK to roles.id
            if role:
                role_details.append({
                    'role_id': role.id,  # Use UUID primary key for FK reference
                    'role_name': role.role_name,
                    'system_role_id': role.role_id  # This is the string external ID
                })
                print(f"   - {role.role_name}")

        # 4. Get source user's violations
        print("\n⚠️  Copying violations...")
        source_violations = session.query(Violation).filter_by(user_id=source_user.id).all()
        print(f"   Found {len(source_violations)} violations to copy")

        # Count by severity
        severity_counts = {}
        for v in source_violations:
            severity = v.severity.value if v.severity else 'UNKNOWN'
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in sorted(severity_counts.items()):
            emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(severity, '⚪')
            print(f"   {emoji} {severity}: {count}")

        # 5. Create test user
        print("\n👤 Creating test user...")
        new_user_id = str(uuid.uuid4())
        new_user = User(
            user_id=new_user_id,
            internal_id=f'TEST_{uuid.uuid4().hex[:8].upper()}',
            name=test_name,
            email=test_email,
            department=source_user.department,  # Keep original department
            title=source_user.title,             # Keep original job title
            status=UserStatus.ACTIVE
        )
        session.add(new_user)
        session.flush()

        print(f"✅ Created user: {test_name}")
        print(f"   User ID: {new_user_id}")
        print(f"   Email: {test_email}")
        print(f"   Department: {new_user.department}")

        # 6. Copy roles
        print("\n🎭 Assigning roles...")
        for role_info in role_details:
            new_user_role = UserRole(
                user_id=new_user.id,  # Use the UUID primary key, not user_id string
                role_id=role_info['role_id']
            )
            session.add(new_user_role)
            print(f"   ✅ Assigned: {role_info['role_name']}")

        # 7. Copy violations
        print("\n⚠️  Creating violations...")
        for old_violation in source_violations:
            new_violation = Violation(
                user_id=new_user.id,  # Use the UUID primary key, not user_id string
                rule_id=old_violation.rule_id,
                severity=old_violation.severity,
                title=old_violation.title if hasattr(old_violation, 'title') else 'SOD Violation',
                description=old_violation.description,  # Keep original description
                conflicting_roles=old_violation.conflicting_roles,  # Keep original role references
                conflicting_permissions=old_violation.conflicting_permissions,
                risk_score=old_violation.risk_score,
                status=ViolationStatus.OPEN  # Use OPEN instead of ACTIVE
            )
            session.add(new_violation)

        print(f"   ✅ Created {len(source_violations)} violations")

        # 8. Commit all changes
        print("\n💾 Committing changes...")
        session.commit()

        print(f"\n{'='*70}")
        print("✅ SUCCESS: Test user created")
        print(f"{'='*70}")
        print("\n📊 Summary:")
        print(f"   Name: {test_name}")
        print(f"   Email: {test_email}")
        print(f"   Roles: {len(role_details)}")
        print(f"   Violations: {len(source_violations)}")
        print(f"   Department: {new_user.department}")
        print(f"   Job Title: {new_user.title or 'N/A'}")
        print("\n🧪 Test with:")
        print(f'   get_user_violations(user_identifier="{test_email}", format="table")')
        print(f'   "Review violations for {test_name}"')

        return True

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error creating test user: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def delete_test_user(test_email: str):
    """Delete a test user and all related data"""
    db_config = get_db_config()
    session = db_config.get_session()

    try:
        print(f"\n🗑️  Deleting test user: {test_email}")

        # Find user
        user = session.query(User).filter_by(email=test_email).first()
        if not user:
            print(f"❌ Test user not found: {test_email}")
            return False


        # Delete violations
        violations = session.query(Violation).filter_by(user_id=user.id).all()
        for v in violations:
            session.delete(v)
        print(f"   ✅ Deleted {len(violations)} violations")

        # Delete user roles
        user_roles = session.query(UserRole).filter_by(user_id=user.id).all()
        for ur in user_roles:
            session.delete(ur)
        print(f"   ✅ Deleted {len(user_roles)} role assignments")

        # Delete user
        session.delete(user)
        print(f"   ✅ Deleted user: {user.name}")

        session.commit()

        print("\n✅ Test user deleted successfully")
        return True

    except Exception as e:
        session.rollback()
        print(f"\n❌ Error deleting test user: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def list_test_users():
    """List all test users"""
    db_config = get_db_config()
    session = db_config.get_session()

    try:
        print(f"\n{'='*70}")
        print("INTERNAL TEST USERS")
        print(f"{'='*70}\n")

        # Find all test users
        test_emails = [info['test_email'] for info in TEST_USERS.values()]
        users = session.query(User).filter(User.email.in_(test_emails)).all()

        if not users:
            print("No test users found.\n")
            print("Available test users to create:")
            for _key, info in TEST_USERS.items():
                print(f"  • {info['test_name']} ({info['test_email']})")
                print(f"    {info['description']}")
            return

        for user in users:
            # Get role count
            role_count = session.query(UserRole).filter_by(user_id=user.id).count()

            # Get violation count by severity
            violations = session.query(Violation).filter_by(user_id=user.id).all()
            severity_counts = {}
            for v in violations:
                severity = v.severity.value if v.severity else 'UNKNOWN'
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            print(f"👤 {user.name}")
            print(f"   Email: {user.email}")
            print(f"   Department: {user.department}")
            print(f"   Job Title: {user.title or 'N/A'}")
            print(f"   Roles: {role_count}")
            print(f"   Violations: {len(violations)} total")
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in severity_counts:
                    emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🟢'}[severity]
                    print(f"     {emoji} {severity}: {severity_counts[severity]}")
            print()

        print(f"Total test users: {len(users)}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n❌ Error listing test users: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Create anonymized test users for internal demos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create both test users
  python3 scripts/create_internal_test_users.py --create

  # Create specific test user
  python3 scripts/create_internal_test_users.py --create --user test-user-a

  # Delete all test users
  python3 scripts/create_internal_test_users.py --delete

  # List existing test users
  python3 scripts/create_internal_test_users.py --list

Available test users:
  test-user-a: High-violation Finance user (mimics Robin Turner)
  test-user-b: Multiple-role user (mimics Chase Roles)
        """
    )

    parser.add_argument('--create', action='store_true',
                        help='Create test user(s)')
    parser.add_argument('--delete', action='store_true',
                        help='Delete test user(s)')
    parser.add_argument('--list', action='store_true',
                        help='List all test users')
    parser.add_argument('--user', choices=['test-user-a', 'test-user-b', 'all'],
                        default='all',
                        help='Which test user to create/delete (default: all)')

    args = parser.parse_args()

    # Validate arguments
    if not (args.create or args.delete or args.list):
        parser.print_help()
        return

    if args.list:
        list_test_users()
        return

    # Determine which users to process
    if args.user == 'all':
        users_to_process = list(TEST_USERS.keys())
    else:
        users_to_process = [args.user]

    # Create users
    if args.create:
        print(f"\n🏗️  Creating {len(users_to_process)} test user(s)...\n")
        success_count = 0
        for user_key in users_to_process:
            info = TEST_USERS[user_key]
            if create_test_user(
                source_email=info['source_email'],
                test_name=info['test_name'],
                test_email=info['test_email'],
                description=info['description']
            ):
                success_count += 1

        print(f"\n{'='*70}")
        print(f"✅ Created {success_count}/{len(users_to_process)} test users")
        print(f"{'='*70}\n")

    # Delete users
    if args.delete:
        print(f"\n🗑️  Deleting {len(users_to_process)} test user(s)...\n")
        success_count = 0
        for user_key in users_to_process:
            info = TEST_USERS[user_key]
            if delete_test_user(info['test_email']):
                success_count += 1

        print(f"\n{'='*70}")
        print(f"✅ Deleted {success_count}/{len(users_to_process)} test users")
        print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
