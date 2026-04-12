#!/usr/bin/env python3
"""
Test Database Layer

Tests all database models and repositories
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import UserStatus
from models.database_config import get_db_config
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_connection():
    """Test 1: Database connection"""
    print_section("TEST 1: Database Connection")

    db_config = get_db_config()

    if db_config.test_connection():
        print("✓ Database connection successful")
        print(f"  URL: {db_config._safe_url()}")
        return True
    else:
        print("✗ Database connection failed")
        return False


def test_user_repository():
    """Test 2: User Repository"""
    print_section("TEST 2: User Repository")

    db_config = get_db_config()
    session = db_config.get_session()

    try:
        repo = UserRepository(session)

        # Get user count
        count = repo.get_user_count()
        print(f"✓ Total users in database: {count}")

        if count == 0:
            print("  ⚠  No users in database yet")
            print("  Run: python3 scripts/sync_from_netsuite.py")
            return False

        # Get active users
        active_count = repo.get_user_count(status=UserStatus.ACTIVE)
        print(f"✓ Active users: {active_count}")

        # Get sample users
        users = repo.get_all_users(limit=5)
        print("\n  Sample users:")
        for user in users:
            print(f"    • {user.name} ({user.email}) - {len(user.user_roles)} roles")

        # Test search
        if users:
            search_term = users[0].name.split()[0]
            results = repo.search_users(search_term, limit=5)
            print(f"\n✓ Search test ('{search_term}'): {len(results)} results")

        # Get high-risk users
        high_risk = repo.get_high_risk_users(min_roles=3)
        print(f"\n✓ High-risk users (3+ roles): {len(high_risk)}")

        if high_risk:
            print("  Top high-risk user:")
            user = high_risk[0]
            print(f"    • {user.name} ({user.email})")
            print(f"    • Roles: {len(user.user_roles)}")

        return True

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        session.close()


def test_role_repository():
    """Test 3: Role Repository"""
    print_section("TEST 3: Role Repository")

    db_config = get_db_config()
    session = db_config.get_session()

    try:
        repo = RoleRepository(session)

        # Get role count
        count = repo.get_role_count()
        print(f"✓ Total roles in database: {count}")

        if count == 0:
            print("  ⚠  No roles in database yet")
            return False

        # Get custom vs standard roles
        custom_count = repo.get_role_count(is_custom=True)
        standard_count = repo.get_role_count(is_custom=False)
        print(f"  • Custom roles: {custom_count}")
        print(f"  • Standard roles: {standard_count}")

        # Get sample roles
        roles = repo.get_all_roles()[:5]
        print("\n  Sample roles:")
        for role in roles:
            print(f"    • {role.role_name} (ID: {role.role_id}) - {role.permission_count} permissions")

        # Get admin roles
        admin_roles = repo.get_admin_roles()
        print(f"\n✓ Admin roles found: {len(admin_roles)}")
        if admin_roles:
            for role in admin_roles[:3]:
                print(f"    • {role.role_name}")

        # Get high-permission roles
        high_perm_roles = repo.get_roles_with_high_permissions(min_permissions=100)
        print(f"\n✓ Roles with 100+ permissions: {len(high_perm_roles)}")

        return True

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        session.close()


def test_violation_repository():
    """Test 4: Violation Repository"""
    print_section("TEST 4: Violation Repository")

    db_config = get_db_config()
    session = db_config.get_session()

    try:
        repo = ViolationRepository(session)

        # Get violation summary
        summary = repo.get_violation_summary()
        print(f"✓ Total violations: {summary['total']}")
        print(f"  • Open: {summary['open']}")

        if summary['total'] == 0:
            print("\n  ⚠  No violations in database yet")
            print("  This is expected if analysis hasn't run")
            return True

        print("\n  By severity:")
        for severity, count in summary['by_severity'].items():
            if count > 0:
                print(f"    • {severity}: {count}")

        print("\n  By status:")
        for status, count in summary['by_status'].items():
            if count > 0:
                print(f"    • {status}: {count}")

        # Get open violations
        open_violations = repo.get_open_violations(limit=5)
        if open_violations:
            print("\n  Sample open violations:")
            for v in open_violations[:3]:
                print(f"    • {v.title}")
                print(f"      User: {v.user.name if v.user else 'N/A'}")
                print(f"      Severity: {v.severity.value}, Risk: {v.risk_score}/100")

        return True

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        session.close()


def test_users_with_roles():
    """Test 5: Users with Roles (Join Query)"""
    print_section("TEST 5: Users with Roles (Join Queries)")

    db_config = get_db_config()
    session = db_config.get_session()

    try:
        repo = UserRepository(session)

        # Get users with roles loaded
        users = repo.get_users_with_roles(status=UserStatus.ACTIVE)[:10]
        print(f"✓ Fetched {len(users)} users with roles loaded")

        if not users:
            print("  ⚠  No users with roles found")
            return False

        print("\n  Users and their roles:")
        for user in users[:5]:
            roles_list = [ur.role.role_name for ur in user.user_roles]
            print(f"    • {user.name}")
            print(f"      Email: {user.email}")
            print(f"      Roles ({len(roles_list)}): {', '.join(roles_list[:3])}")
            if len(roles_list) > 3:
                print(f"               ... and {len(roles_list) - 3} more")
            print()

        return True

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False
    finally:
        session.close()


def main():
    """Run all database tests"""
    print("\n" + "█" * 80)
    print("█" + "  DATABASE LAYER TEST SUITE".center(78) + "█")
    print("█" * 80)

    tests = [
        ("Connection Test", test_connection),
        ("User Repository", test_user_repository),
        ("Role Repository", test_role_repository),
        ("Violation Repository", test_violation_repository),
        ("Users with Roles", test_users_with_roles)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed! Database layer is working.")
    else:
        print(f"\n  ⚠  {total - passed} test(s) failed or skipped")
        print("  Make sure to run: python3 scripts/sync_from_netsuite.py")

    print("\n" + "█" * 80 + "\n")


if __name__ == '__main__':
    main()
