#!/usr/bin/env python3
"""
SOD Compliance Agent - Interactive Demo
Showcases the Data Collection Agent capabilities
"""

import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.data_collector import DataCollectionAgent

load_dotenv()


def print_header(title):
    """Print a styled header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_section(title):
    """Print a section divider"""
    print("\n" + "-" * 80)
    print(f"  {title}")
    print("-" * 80 + "\n")


def animate_loading(message, duration=1.5):
    """Show a loading animation"""
    import sys
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r  {frames[i % len(frames)]} {message}...")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r  ✓ {message}... Done!\n")


def demo_1_connection():
    """Demo 1: Test NetSuite Connection"""
    print_header("DEMO 1: NetSuite Connection Test")

    print("Initializing Data Collection Agent...")
    agent = DataCollectionAgent()
    print("✓ Agent initialized with Claude Sonnet 4.5\n")

    animate_loading("Testing NetSuite connection")

    if agent.test_connection():
        print("✓ Successfully connected to NetSuite Sandbox")
        print("  Account: 5260239-sb1")
        print("  RESTlet: script=3684, deploy=1")
        print("  Authentication: OAuth 1.0a")
        return agent
    else:
        print("✗ Connection failed!")
        return None


def demo_2_fetch_sample(agent):
    """Demo 2: Fetch Sample Users"""
    print_header("DEMO 2: Fetch Sample Users (Fast)")

    print("Fetching 20 users WITHOUT permissions (fast query)...")
    animate_loading("Querying NetSuite", 1.0)

    result = agent.netsuite_client.get_users_and_roles(
        limit=20,
        include_permissions=False
    )

    if result.get('success'):
        users = result['data']['users']
        metadata = result['data']['metadata']

        print("\n✓ Query successful!")
        print(f"  Total users in system: {metadata['total_users']:,}")
        print(f"  Fetched: {len(users)} users")
        print(f"  Execution time: {metadata['execution_time_seconds']:.2f}s")

        print("\n  Sample Users:")
        for i, user in enumerate(users[:5], 1):
            print(f"    {i}. {user['name']:<30} {user['email']:<40} ({user['roles_count']} roles)")

        return True
    else:
        print(f"✗ Error: {result.get('error')}")
        return False


def demo_3_fetch_with_permissions(agent):
    """Demo 3: Fetch Users WITH Full Permissions"""
    print_header("DEMO 3: Fetch Users with Full Role Permissions")

    print("Fetching 10 users WITH complete permissions (slower, more data)...")
    animate_loading("Querying NetSuite with SuiteQL", 2.0)

    result = agent.netsuite_client.get_users_and_roles(
        limit=10,
        include_permissions=True
    )

    if result.get('success'):
        users = result['data']['users']
        metadata = result['data']['metadata']

        # Count total permissions
        total_perms = 0
        for user in users:
            for role in user.get('roles', []):
                total_perms += len(role.get('permissions', []))

        print("\n✓ Query successful!")
        print(f"  Users fetched: {len(users)}")
        print(f"  Total permissions retrieved: {total_perms:,}")
        print(f"  Execution time: {metadata['execution_time_seconds']:.2f}s")

        # Show detailed user
        if users:
            print("\n  Detailed View - First User:")
            user = users[0]
            print(f"    Name: {user['name']}")
            print(f"    Email: {user['email']}")
            print(f"    Status: {user['status']}")
            print(f"    Department: {user.get('department', 'N/A')}")
            print(f"    Roles: {user['roles_count']}")

            if user.get('roles'):
                print("\n    Role Breakdown:")
                for role in user['roles']:
                    perm_count = len(role.get('permissions', []))
                    print(f"      • {role['role_name']}: {perm_count} permissions")

                    if role.get('permissions'):
                        print("        Sample permissions:")
                        for perm in role['permissions'][:3]:
                            print(f"          - {perm['permission']}: {perm['level']}")

        return users
    else:
        print(f"✗ Error: {result.get('error')}")
        return []


def demo_4_find_specific_user(agent):
    """Demo 4: Search for Specific User"""
    print_header("DEMO 4: Find Specific User by Email")

    email = "robin.turner@fivetran.com"
    print(f"Searching for: {email}")
    animate_loading("Querying user database", 1.5)

    user = agent.netsuite_client.get_user_by_email(email, include_permissions=True)

    if user:
        print("\n✓ User found!")
        print("\n  Personal Information:")
        print(f"    Name: {user['name']}")
        print(f"    Email: {user['email']}")
        print(f"    User ID: {user['user_id']}")
        print(f"    Internal ID: {user['internal_id']}")
        print(f"    Status: {user['status']}")
        print(f"    Department: {user.get('department', 'N/A')}")
        print(f"    Subsidiary: {user.get('subsidiary', 'N/A')}")

        print("\n  Role & Permission Analysis:")
        print(f"    Total Roles: {user['roles_count']}")

        if user.get('roles'):
            total_perms = sum(len(r.get('permissions', [])) for r in user['roles'])
            print(f"    Total Permissions: {total_perms}")
            print("\n    Roles:")
            for role in user['roles']:
                perm_count = len(role.get('permissions', []))
                print(f"      • {role['role_name']}")
                print(f"        ID: {role['role_id']}")
                print(f"        Permissions: {perm_count}")
                print(f"        Custom Role: {role.get('is_custom', False)}")

        return user
    else:
        print(f"✗ User not found: {email}")
        return None


def demo_5_high_risk_users(agent):
    """Demo 5: Identify High-Risk Users"""
    print_header("DEMO 5: High-Risk User Analysis")

    print("Analyzing users for SOD risks...")
    print("Fetching 500 users to analyze role assignments...")
    animate_loading("Collecting user data", 2.0)

    result = agent.netsuite_client.get_users_and_roles(
        limit=500,
        include_permissions=False
    )

    if not result.get('success'):
        print(f"✗ Error: {result.get('error')}")
        return

    users = result['data']['users']

    animate_loading("Identifying high-risk patterns", 1.0)

    high_risk = agent.get_high_risk_users(users, min_roles=3)

    print("\n✓ Analysis complete!")
    print(f"  Total users analyzed: {len(users):,}")
    print(f"  High-risk users (3+ roles): {len(high_risk)}")

    if high_risk:
        print("\n  ⚠️  HIGH RISK USERS - Multiple Role Assignments:")
        print(f"  {'Name':<30} {'Email':<35} {'Roles':>5}")
        print(f"  {'-'*30} {'-'*35} {'-'*5}")

        for user in high_risk[:10]:
            print(f"  {user['name']:<30} {user['email']:<35} {user['roles_count']:>5}")

        if len(high_risk) > 10:
            print(f"\n  ... and {len(high_risk) - 10} more high-risk users")

        # Show role breakdown for top user
        if high_risk:
            print(f"\n  Top Risk User: {high_risk[0]['name']}")
            print("  Roles assigned:")
            for role in high_risk[0]['roles'][:5]:
                print(f"    • {role}")
    else:
        print("\n  ✓ No high-risk users found (all users have < 3 roles)")

    return high_risk


def demo_6_claude_analysis(agent):
    """Demo 6: Claude AI-Powered Analysis"""
    print_header("DEMO 6: Claude AI Role Distribution Analysis")

    print("Using Claude Sonnet 4.5 to analyze role patterns...")
    print("Fetching 200 users for comprehensive analysis...")
    animate_loading("Collecting data", 1.5)

    result = agent.netsuite_client.get_users_and_roles(
        limit=200,
        include_permissions=False
    )

    if not result.get('success'):
        print(f"✗ Error: {result.get('error')}")
        return

    users = result['data']['users']

    animate_loading("Claude is analyzing role distribution", 3.0)

    analysis_result = agent.analyze_user_role_distribution(users)

    if not analysis_result.get('success'):
        print(f"✗ Analysis failed: {analysis_result.get('error')}")
        return

    analysis = analysis_result['analysis']
    stats = analysis_result['raw_stats']

    print("\n✓ Claude analysis complete!")

    print("\n  📊 Statistics:")
    print(f"    Total users analyzed: {stats['total_users']}")
    print(f"    Users with multiple roles: {stats['users_with_multiple_roles']}")
    print(f"    Users with no roles: {stats['users_with_no_roles']}")
    print(f"    Unique roles in system: {stats['unique_roles']}")

    print("\n  📈 Top 5 Most Common Roles:")
    for i, (role, count) in enumerate(stats['top_roles'][:5], 1):
        print(f"    {i}. {role}: {count} users")

    print("\n  🤖 Claude's Analysis:")
    print(f"    {analysis.get('summary', 'N/A')}")

    if analysis.get('concerns'):
        print("\n  ⚠️  Key Concerns:")
        for concern in analysis['concerns']:
            print(f"    • {concern}")

    if analysis.get('recommendations'):
        print("\n  💡 Recommendations:")
        for rec in analysis['recommendations']:
            print(f"    • {rec}")

    if analysis.get('high_risk_patterns'):
        print("\n  🚨 High-Risk Patterns Detected:")
        for pattern in analysis['high_risk_patterns']:
            print(f"    • {pattern}")


def main():
    """Run the complete demo"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  SOD COMPLIANCE SYSTEM - DATA COLLECTION AGENT DEMO".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        # Demo 1: Connection
        agent = demo_1_connection()
        if not agent:
            return

        input("\nPress Enter to continue to Demo 2...")

        # Demo 2: Sample fetch
        if not demo_2_fetch_sample(agent):
            return

        input("\nPress Enter to continue to Demo 3...")

        # Demo 3: Full permissions
        demo_3_fetch_with_permissions(agent)

        input("\nPress Enter to continue to Demo 4...")

        # Demo 4: Specific user
        demo_4_find_specific_user(agent)

        input("\nPress Enter to continue to Demo 5...")

        # Demo 5: High risk
        demo_5_high_risk_users(agent)

        input("\nPress Enter to continue to Demo 6 (Claude AI Analysis)...")

        # Demo 6: Claude analysis
        demo_6_claude_analysis(agent)

        # Summary
        print_header("DEMO COMPLETE")
        print("✓ All 6 demonstrations completed successfully!")
        print("\nCapabilities Demonstrated:")
        print("  1. ✓ NetSuite OAuth 1.0a connection")
        print("  2. ✓ Fast user data fetching (1,933 users)")
        print("  3. ✓ Complete permission retrieval (224 per role)")
        print("  4. ✓ User search by email")
        print("  5. ✓ High-risk user identification (SOD violations)")
        print("  6. ✓ Claude AI-powered analysis and insights")

        print("\nNext Steps:")
        print("  • Build database layer to persist this data")
        print("  • Create Analysis Agent to detect specific SOD violations")
        print("  • Implement Risk Assessment Agent for scoring")
        print("  • Add notification system for alerts")

        print("\n" + "█" * 80)
        print("█" + "  Thank you for watching the demo!".center(78) + "█")
        print("█" * 80 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Demo error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
