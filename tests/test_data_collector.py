#!/usr/bin/env python3
"""
Test script for Data Collection Agent

Tests:
1. NetSuite connection
2. User data fetching
3. Role analysis with Claude
4. High-risk user identification
"""

import logging
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from agents.data_collector import DataCollectionAgent

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_separator(title: str):
    """Print a visual separator"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_connection():
    """Test 1: Verify NetSuite connection"""
    print_separator("TEST 1: NetSuite Connection")

    agent = DataCollectionAgent()

    if agent.test_connection():
        print("✓ Connection successful!")
        return True
    else:
        print("✗ Connection failed!")
        return False


def test_fetch_users():
    """Test 2: Fetch users without permissions (fast test)"""
    print_separator("TEST 2: Fetch Users (No Permissions)")

    agent = DataCollectionAgent()

    print("Fetching first 100 users without permissions...")
    result = agent.netsuite_client.get_users_and_roles(
        limit=100,
        include_permissions=False
    )

    if result.get('success'):
        users = result['data']['users']
        metadata = result['data']['metadata']

        print(f"\n✓ Fetched {len(users)} users")
        print(f"  Total in system: {metadata['total_users']}")
        print(f"  Execution time: {metadata['execution_time_seconds']:.2f}s")

        if users:
            print("\nSample user:")
            user = users[0]
            print(f"  Name: {user['name']}")
            print(f"  Email: {user['email']}")
            print(f"  Status: {user['status']}")
            print(f"  Roles: {user['roles_count']}")

        return True
    else:
        print(f"✗ Error: {result.get('error')}")
        return False


def test_fetch_with_permissions():
    """Test 3: Fetch users WITH permissions (slower)"""
    print_separator("TEST 3: Fetch Users (With Permissions)")

    agent = DataCollectionAgent()

    print("Fetching 50 users WITH full permissions...")
    result = agent.netsuite_client.get_users_and_roles(
        limit=50,
        include_permissions=True
    )

    if result.get('success'):
        users = result['data']['users']
        metadata = result['data']['metadata']

        print(f"\n✓ Fetched {len(users)} users")
        print(f"  Execution time: {metadata['execution_time_seconds']:.2f}s")

        # Count total permissions
        total_perms = 0
        for user in users:
            for role in user.get('roles', []):
                total_perms += len(role.get('permissions', []))

        print(f"  Total permissions retrieved: {total_perms}")

        # Show detailed user
        if users:
            user = users[0]
            print("\nDetailed sample user:")
            print(f"  Name: {user['name']}")
            print(f"  Roles: {user['roles_count']}")

            if user.get('roles'):
                role = user['roles'][0]
                print(f"\n  First role: {role['role_name']}")
                print(f"    Permissions: {len(role.get('permissions', []))}")

                if role.get('permissions'):
                    print("    Sample permissions:")
                    for perm in role['permissions'][:5]:
                        print(f"      - {perm['permission']}: {perm['level']}")

        return True
    else:
        print(f"✗ Error: {result.get('error')}")
        return False


def test_find_specific_user():
    """Test 4: Find Robin Turner"""
    print_separator("TEST 4: Find Specific User (Robin Turner)")

    agent = DataCollectionAgent()

    print("Searching for robin.turner@fivetran.com...")
    user = agent.netsuite_client.get_user_by_email(
        'robin.turner@fivetran.com',
        include_permissions=True
    )

    if user:
        print("\n✓ Found user!")
        print(f"  Name: {user['name']}")
        print(f"  Email: {user['email']}")
        print(f"  Status: {user['status']}")
        print(f"  Department: {user.get('department', 'N/A')}")
        print(f"  Roles: {user['roles_count']}")

        if user.get('roles'):
            print("\n  Role details:")
            for role in user['roles']:
                perm_count = len(role.get('permissions', []))
                print(f"    • {role['role_name']}: {perm_count} permissions")

        return True
    else:
        print("✗ User not found")
        return False


def test_high_risk_users():
    """Test 5: Identify high-risk users"""
    print_separator("TEST 5: High-Risk User Identification")

    agent = DataCollectionAgent()

    print("Fetching users to analyze risk...")
    result = agent.netsuite_client.get_users_and_roles(
        limit=500,
        include_permissions=False
    )

    if not result.get('success'):
        print(f"✗ Error fetching users: {result.get('error')}")
        return False

    users = result['data']['users']
    high_risk = agent.get_high_risk_users(users, min_roles=3)

    print("\n✓ Analysis complete")
    print(f"  Total users analyzed: {len(users)}")
    print(f"  High-risk users (3+ roles): {len(high_risk)}")

    if high_risk:
        print("\n  Top 5 high-risk users:")
        for user in high_risk[:5]:
            print(f"    • {user['name']} ({user['email']}): {user['roles_count']} roles")
            print(f"      Roles: {', '.join(user['roles'][:3])}")

    return True


def test_claude_analysis():
    """Test 6: Claude-powered role analysis"""
    print_separator("TEST 6: Claude Analysis (Role Distribution)")

    agent = DataCollectionAgent()

    print("Fetching users for Claude analysis...")
    result = agent.netsuite_client.get_users_and_roles(
        limit=200,
        include_permissions=False
    )

    if not result.get('success'):
        print(f"✗ Error fetching users: {result.get('error')}")
        return False

    users = result['data']['users']

    print(f"Analyzing {len(users)} users with Claude Sonnet 4.5...")
    analysis_result = agent.analyze_user_role_distribution(users)

    if not analysis_result.get('success'):
        print(f"✗ Analysis failed: {analysis_result.get('error')}")
        return False

    analysis = analysis_result['analysis']
    stats = analysis_result['raw_stats']

    print("\n✓ Analysis complete!")

    print("\nStatistics:")
    print(f"  Total users: {stats['total_users']}")
    print(f"  Users with multiple roles: {stats['users_with_multiple_roles']}")
    print(f"  Users with no roles: {stats['users_with_no_roles']}")
    print(f"  Unique roles: {stats['unique_roles']}")

    print("\nClaude's Summary:")
    print(f"  {analysis.get('summary', 'N/A')}")

    if analysis.get('concerns'):
        print("\nKey Concerns:")
        for concern in analysis['concerns']:
            print(f"  • {concern}")

    if analysis.get('recommendations'):
        print("\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  • {rec}")

    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  DATA COLLECTION AGENT - TEST SUITE")
    print("  Started:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    tests = [
        ("Connection Test", test_connection),
        ("Basic User Fetch", test_fetch_users),
        ("Fetch with Permissions", test_fetch_with_permissions),
        ("Find Specific User", test_find_specific_user),
        ("High-Risk Users", test_high_risk_users),
        ("Claude Analysis", test_claude_analysis)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {str(e)}")
            results.append((test_name, False))

    # Summary
    print_separator("TEST SUMMARY")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed!")
    else:
        print(f"\n  ⚠ {total - passed} test(s) failed")

    print("\n" + "=" * 80 + "\n")


if __name__ == '__main__':
    main()
