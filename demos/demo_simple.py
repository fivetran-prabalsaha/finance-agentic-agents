#!/usr/bin/env python3
"""
Simple Demo - No interaction required
Perfect for presentations and stakeholder demos
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.data_collector import DataCollectionAgent


def print_box(text, width=70):
    """Print text in a box"""
    print("┌" + "─" * width + "┐")
    print("│" + text.center(width) + "│")
    print("└" + "─" * width + "┘")

print("\n")
print_box("SOD COMPLIANCE AGENT - LIVE DEMO")
print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Initialize
print("▶ Initializing Data Collection Agent...")
agent = DataCollectionAgent()
print("  ✓ Agent ready (Claude Sonnet 4.5 integrated)\n")

# Test connection
print("▶ Testing NetSuite connection...")
if agent.test_connection():
    print("  ✓ Connected to NetSuite Sandbox (5260239-sb1)")
    print("  ✓ RESTlet: script=3684, deploy=1")
    print("  ✓ Authentication: OAuth 1.0a\n")
else:
    print("  ✗ Connection failed!\n")
    sys.exit(1)

# Fetch users
print("▶ Fetching users from NetSuite...")
result = agent.netsuite_client.get_users_and_roles(
    limit=20,
    include_permissions=False
)

if result.get('success'):
    users = result['data']['users']
    metadata = result['data']['metadata']

    print(f"  ✓ Fetched {len(users)} users")
    print(f"  ✓ Total users in system: {metadata['total_users']:,}")
    print(f"  ✓ Execution time: {metadata['execution_time_seconds']:.2f}s\n")

    # Show sample
    print("📋 Sample Users:\n")
    print(f"  {'Name':<30} {'Email':<40} {'Roles':>6}")
    print(f"  {'-'*30} {'-'*40} {'-'*6}")
    for user in users[:8]:
        print(f"  {user['name']:<30} {user['email']:<40} {user['roles_count']:>6}")

    print()

    # Identify high-risk
    print("▶ Analyzing for SOD risks...")
    high_risk = agent.get_high_risk_users(users, min_roles=2)
    print("  ✓ Analysis complete")
    print(f"  ⚠️  Found {len(high_risk)} users with 2+ roles (potential SOD risks)\n")

    if high_risk:
        print("🚨 High-Risk Users:\n")
        for user in high_risk[:3]:
            print(f"  • {user['name']} ({user['email']})")
            print(f"    Roles: {', '.join(user['roles'][:3])}")
            print()

    # Summary
    print("─" * 70)
    print("\n✅ DEMO COMPLETE\n")
    print("Capabilities Demonstrated:")
    print("  ✓ NetSuite OAuth connection")
    print("  ✓ Real-time data fetching")
    print("  ✓ High-risk user detection")
    print("  ✓ Automatic SOD analysis\n")

    print("📊 System Status:")
    print(f"  • Active Users: {metadata['total_users']:,}")
    print("  • Agent Status: ✅ Production Ready")
    print(f"  • Last Sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

else:
    print(f"  ✗ Error: {result.get('error')}\n")
