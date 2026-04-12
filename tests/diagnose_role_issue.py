#!/usr/bin/env python3
"""
Diagnostic script to understand why roles are not being fetched

This script will:
1. Check if users exist
2. Check if any users in the system have roles
3. Test different user types (active vs inactive)
4. Show detailed error information
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.netsuite_client import NetSuiteClient


def main():
    client = NetSuiteClient()

    print("=" * 80)
    print(" ROLE FETCHING DIAGNOSTIC")
    print("=" * 80)
    print()

    # Test 1: Check version
    print("TEST 1: Verify RESTlet Version")
    print("-" * 80)
    result = client.search_users('test@test.com', 'email', False)
    if result['success']:
        version = result['data']['metadata'].get('version')
        print(f"Version: {version}")
        if version == '3.0.0-record-load':
            print("✅ v3 is deployed (uses record.load)")
        else:
            print("⚠️  Wrong version deployed")
    print()

    # Test 2: Fetch a batch of users
    print("TEST 2: Check Multiple Users")
    print("-" * 80)
    print("Fetching 20 users from main RESTlet...")

    result = client.get_users_and_roles(limit=20, include_permissions=False)

    if result['success']:
        users = result['data']['users']
        print(f"Found {len(users)} users")
        print()

        # Count users with roles
        users_with_roles = [u for u in users if u.get('roles_count', 0) > 0]
        users_without_roles = [u for u in users if u.get('roles_count', 0) == 0]

        print(f"Users with roles:    {len(users_with_roles)}")
        print(f"Users without roles: {len(users_without_roles)}")
        print()

        if users_with_roles:
            print("✅ GOOD NEWS: Some users DO have roles!")
            print()
            print("Sample users with roles:")
            for user in users_with_roles[:3]:
                print(f"  • {user['name']}: {user['roles_count']} roles")
            print()
            print("This means:")
            print("  ✅ OAuth has permission to read roles")
            print("  ✅ record.load() is working")
            print("  ✅ Role field exists")
            print()
            print("The issue is specific to Robin Turner / Prabal Saha")
            print("Possible reasons:")
            print("  - These specific users don't have roles assigned")
            print("  - These users are in a different subsidiary")
            print("  - These users are inactive and roles were removed")

        else:
            print("❌ PROBLEM: NO users have roles!")
            print()
            print("This means one of:")
            print("  1. OAuth integration lacks 'Employee' VIEW permission")
            print("  2. 'roles' sublist doesn't exist or has different name")
            print("  3. Field ID 'selectrecord' is wrong")
            print("  4. Truly no users have roles (unlikely)")
            print()
            print("Next steps:")
            print("  → Check NetSuite execution logs for errors")
            print("  → Verify OAuth permissions")
            print("  → Manually verify users have roles in NetSuite UI")

    print()

    # Test 3: Specific users
    print("TEST 3: Check Specific Test Users")
    print("-" * 80)

    test_users = [
        ('robin.turner@fivetran.com', 'Robin Turner'),
        ('prabal.saha@fivetran.com', 'Prabal Saha')
    ]

    for email, name in test_users:
        print(f"\nChecking: {name}")
        result = client.search_users(email, 'email', False)

        if result['success'] and result['data']['users']:
            for user in result['data']['users']:
                print(f"  Found: {user['name']}")
                print(f"    Internal ID: {user['internal_id']}")
                print(f"    Active: {user['is_active']}")
                print(f"    Roles: {user['roles_count']}")

                if user['roles_count'] == 0:
                    print("    ⚠️  No roles found")
                    print("    → Check if this user has roles in NetSuite UI")
                    print("    → Check NetSuite logs for 'Role Count' message")
        else:
            print("  ❌ Not found")

    print()
    print("=" * 80)
    print()
    print("NEXT STEPS:")
    print()
    print("1. Check NetSuite Execution Logs:")
    print("   Customization → Scripting → Script Execution Log")
    print("   Look for 'Role Count' or ERROR messages")
    print()
    print("2. Check NetSuite UI:")
    print("   Lists → Employees → Search for Robin Turner")
    print("   Open record → Access tab → Check Roles section")
    print()
    print("3. Check OAuth Permissions:")
    print("   Setup → Integration → Manage Integrations")
    print("   Verify: Employee (View), Role (View), Lists (View)")
    print()


if __name__ == '__main__':
    main()
