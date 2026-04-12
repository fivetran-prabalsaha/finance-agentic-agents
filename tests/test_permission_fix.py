#!/usr/bin/env python3
"""
Test script to verify permission fetching is working correctly

This script tests the fixed user_search_restlet to ensure:
1. Permissions are actually being returned
2. Permission data is complete and accurate
3. SOD analysis can now work properly

Usage:
    python3 tests/test_permission_fix.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.netsuite_client import NetSuiteClient


class PermissionFixTester:
    """Test suite for permission fetching fix"""

    def __init__(self):
        self.client = NetSuiteClient()
        self.test_users = [
            'prabal.saha@fivetran.com',
            'robin.turner@fivetran.com'
        ]

    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80 + "\n")

    def test_permission_fetching(self):
        """Test that permissions are being fetched correctly"""
        self.print_header("PERMISSION FETCHING TEST")

        for email in self.test_users:
            print(f"\n📧 Testing: {email}")
            print("-" * 80)

            # Search for user with permissions
            result = self.client.search_users(
                search_value=email,
                search_type='email',
                include_permissions=True
            )

            if not result['success']:
                print("❌ FAIL: Could not fetch user")
                print(f"   Error: {result.get('error', 'Unknown')}")
                continue

            users = result['data']['users']
            if not users:
                print("❌ FAIL: User not found")
                continue

            # May return multiple users (duplicates)
            for idx, user in enumerate(users):
                if len(users) > 1:
                    print(f"\n   Record {idx + 1} of {len(users)}: {user['name']}")
                else:
                    print(f"\n   User: {user['name']}")

                roles = user.get('roles', [])
                print(f"   Roles: {len(roles)}")

                if not roles:
                    print("   ⚠️  WARNING: No roles found")
                    continue

                # Check each role for permissions
                total_permissions = 0
                roles_with_permissions = 0
                roles_without_permissions = 0

                for role in roles:
                    role_name = role.get('role_name', 'Unknown')
                    permissions = role.get('permissions', [])
                    perm_count = len(permissions)

                    total_permissions += perm_count

                    if perm_count > 0:
                        roles_with_permissions += 1
                        print(f"   ✅ {role_name}: {perm_count} permissions")

                        # Show sample permissions
                        if perm_count > 0 and perm_count <= 5:
                            for perm in permissions[:5]:
                                print(f"      • {perm.get('permission_name', perm.get('key', 'Unknown'))} ({perm.get('level', 'N/A')})")
                        elif perm_count > 5:
                            for perm in permissions[:3]:
                                print(f"      • {perm.get('permission_name', perm.get('key', 'Unknown'))} ({perm.get('level', 'N/A')})")
                            print(f"      ... and {perm_count - 3} more")

                    else:
                        roles_without_permissions += 1
                        print(f"   ❌ {role_name}: 0 permissions (MISSING)")

                # Summary
                print("\n   📊 Summary:")
                print(f"      Total Roles:              {len(roles)}")
                print(f"      Roles with Permissions:   {roles_with_permissions}")
                print(f"      Roles without Permissions: {roles_without_permissions}")
                print(f"      Total Permissions:        {total_permissions}")

                # Status
                if roles_without_permissions == 0 and total_permissions > 0:
                    print("\n   ✅ STATUS: PASS - All roles have permissions")
                elif roles_with_permissions > 0:
                    print("\n   ⚠️  STATUS: PARTIAL - Some roles missing permissions")
                else:
                    print("\n   ❌ STATUS: FAIL - No permissions found")

    def test_sod_analysis_accuracy(self):
        """Test that SOD analysis can now work with permission data"""
        self.print_header("SOD ANALYSIS ACCURACY TEST")

        print("Testing if SOD rules can now check permissions...")
        print()

        # Sample SOD rules that require permissions
        test_cases = [
            {
                'rule': 'Journal Entry Creation vs. Approval',
                'permissions_needed': ['Create Journal Entry', 'Approve Journal Entry']
            },
            {
                'rule': 'AP Entry vs. Approval Separation',
                'permissions_needed': ['Create Bill', 'Approve Bill']
            },
            {
                'rule': 'Bank Reconciliation vs. Cash Transactions',
                'permissions_needed': ['Bank Reconciliation', 'Create Check']
            }
        ]

        for email in self.test_users:
            print(f"\n📧 User: {email}")
            print("-" * 80)

            result = self.client.search_users(
                search_value=email,
                search_type='email',
                include_permissions=True
            )

            if not result['success'] or not result['data']['users']:
                print("   ❌ Could not fetch user")
                continue

            # Get all permissions across all roles
            all_permissions = set()
            for user in result['data']['users']:
                for role in user.get('roles', []):
                    for perm in role.get('permissions', []):
                        perm_key = perm.get('key', '')
                        perm_name = perm.get('permission_name', '')
                        if perm_key:
                            all_permissions.add(perm_key)
                        if perm_name:
                            all_permissions.add(perm_name)

            print(f"   Total unique permissions: {len(all_permissions)}")
            print()

            # Test each rule
            for test_case in test_cases:
                rule_name = test_case['rule']
                needed = test_case['permissions_needed']

                print(f"   Testing: {rule_name}")

                # Check if we can find these permissions (fuzzy match)
                found = []
                for perm_needed in needed:
                    perm_lower = perm_needed.lower()
                    matches = [p for p in all_permissions if perm_lower in p.lower()]
                    if matches:
                        found.append(perm_needed)
                        print(f"      ✓ Can check: {perm_needed}")
                    else:
                        print(f"      ❌ Cannot check: {perm_needed} (not in permission list)")

                if len(found) == len(needed):
                    print("      ✅ Rule can be fully checked")
                elif len(found) > 0:
                    print(f"      ⚠️  Rule partially checkable ({len(found)}/{len(needed)})")
                else:
                    print("      ❌ Rule cannot be checked")
                print()

    def test_governance_usage(self):
        """Test governance usage for permission fetching"""
        self.print_header("GOVERNANCE USAGE TEST")

        print("Testing governance efficiency when fetching permissions...")
        print()

        result = self.client.search_users(
            search_value='prabal.saha@fivetran.com',
            search_type='email',
            include_permissions=True
        )

        if not result['success']:
            print("❌ FAIL: Could not fetch data")
            return

        governance = result['data'].get('governance', {})

        if not governance:
            print("⚠️  WARNING: No governance data in response")
            print("   This means you might be using the old RESTlet")
            return

        print("📊 Governance Metrics:")
        print(f"   Starting Units:    {governance.get('starting_units', 'N/A')}")
        print(f"   Ending Units:      {governance.get('ending_units', 'N/A')}")
        print(f"   Units Used:        {governance.get('units_used', 'N/A')}")
        print(f"   Units Per User:    {governance.get('units_per_user', 'N/A')}")
        print()

        units_per_user = float(governance.get('units_per_user', 0))

        if units_per_user < 5:
            print(f"✅ EXCELLENT: {units_per_user} units/user (target: < 5)")
        elif units_per_user < 10:
            print(f"✅ GOOD: {units_per_user} units/user (target: < 10)")
        elif units_per_user < 20:
            print(f"⚠️  ACCEPTABLE: {units_per_user} units/user (target: < 20)")
        else:
            print(f"❌ HIGH: {units_per_user} units/user (consider optimization)")

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 80)
        print(" PERMISSION FIX VERIFICATION TEST SUITE")
        print(" Testing NetSuite RESTlet v2.0 (With Permissions)")
        print("=" * 80)

        self.test_permission_fetching()
        self.test_sod_analysis_accuracy()
        self.test_governance_usage()

        self.print_header("TEST SUITE COMPLETE")

        print("Next Steps:")
        print()
        print("1. ✅ If all tests passed:")
        print("   - Permissions are being fetched correctly")
        print("   - SOD analysis will now work at 100% accuracy")
        print("   - Run full SOD analysis: python3 demos/test_two_users.py")
        print()
        print("2. ❌ If tests failed:")
        print("   - Old RESTlet might still be deployed")
        print("   - Deploy: netsuite_scripts/user_search_restlet_with_permissions.js")
        print("   - See: docs/PERMISSION_FIX_DEPLOYMENT.md")
        print()


def main():
    """Main entry point"""
    tester = PermissionFixTester()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
