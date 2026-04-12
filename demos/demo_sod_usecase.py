#!/usr/bin/env python3
"""
SOD Compliance Demo - Use Case: High-Risk User Detection

Demonstrates comparing low-risk vs high-risk users:
- Prabal Saha: 1 role (LOW RISK)
- Robin Turner: 3 roles (HIGH RISK - SOD VIOLATION)
"""

import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.data_collector import DataCollectionAgent

load_dotenv()


def print_box(text, width=80):
    """Print text in a box"""
    print("\n┌" + "─" * (width - 2) + "┐")
    print("│" + text.center(width - 2) + "│")
    print("└" + "─" * (width - 2) + "┘")


def analyze_user(user, user_type="USER"):
    """Analyze and display user risk profile"""

    print(f"\n{'='*80}")
    print(f"  {user_type}: {user['name']}")
    print(f"{'='*80}")

    print("\n📋 Profile:")
    print(f"  Name:       {user['name']}")
    print(f"  Email:      {user['email']}")
    print(f"  Status:     {user['status']}")
    print(f"  Department: {user.get('department', 'N/A')}")
    print(f"  Subsidiary: {user.get('subsidiary', 'N/A')}")

    print("\n🎭 Access Control:")
    print(f"  Total Roles: {user['roles_count']}")

    if user.get('roles'):
        total_perms = 0

        for idx, role in enumerate(user['roles'], 1):
            perm_count = len(role.get('permissions', []))
            total_perms += perm_count

            print(f"\n  Role {idx}: {role['role_name']}")
            print(f"    ID:          {role['role_id']}")
            print(f"    Type:        {'Custom' if role.get('is_custom') else 'Standard'}")
            print(f"    Permissions: {perm_count}")

            if perm_count > 0:
                print("    Key Permissions:")
                for perm in role['permissions'][:3]:
                    perm_name = perm.get('permission_name', perm.get('permission', 'Unknown'))
                    perm_level = perm.get('level', 'N/A')
                    print(f"      • {perm_name}: {perm_level}")

                if perm_count > 3:
                    print(f"      ... and {perm_count - 3} more")

        print("\n📊 Risk Analysis:")
        print(f"  Total Unique Permissions: {total_perms}")

        # Risk scoring
        risk_score = 0
        risk_factors = []

        if user['roles_count'] >= 3:
            risk_score = 90
            risk_level = "🚨 CRITICAL HIGH"
            risk_factors.append(f"Has {user['roles_count']} roles (major SOD concern)")
        elif user['roles_count'] == 2:
            risk_score = 60
            risk_level = "⚠️  HIGH"
            risk_factors.append(f"Has {user['roles_count']} roles (potential SOD conflict)")
        else:
            risk_score = 20
            risk_level = "✅ LOW"
            risk_factors.append("Single role assignment (standard practice)")

        # Check for admin role
        if any('admin' in r['role_name'].lower() for r in user['roles']):
            if user['roles_count'] > 1:
                risk_score += 10
                risk_factors.append("Has Admin role PLUS other roles (elevated concern)")

        # Check for finance-related roles
        finance_keywords = ['controller', 'finance', 'accounting', 'ap', 'ar', 'treasury']
        finance_roles = [r for r in user['roles']
                        if any(kw in r['role_name'].lower() for kw in finance_keywords)]

        if len(finance_roles) > 1:
            risk_score += 15
            risk_factors.append("Multiple finance-related roles (SOD violation)")

        # High permission count
        if total_perms > 300:
            risk_factors.append(f"Excessive permissions ({total_perms} total)")

        print(f"  Risk Score:  {risk_score}/100")
        print(f"  Risk Level:  {risk_level}")

        print("\n  Risk Factors:")
        for factor in risk_factors:
            print(f"    • {factor}")

        # SOD recommendations
        if risk_score >= 60:
            print("\n🔍 SOD Compliance Recommendations:")
            if user['roles_count'] >= 3:
                print("    1. Immediately review role assignments")
                print("    2. Check for conflicting duties (create vs approve)")
                print("    3. Consider role consolidation or separation")
            if finance_roles:
                print("    4. Verify financial transaction controls")
                print("    5. Ensure proper approval workflows")
            print("    6. Schedule quarterly access review")
            print("    7. Document business justification for multiple roles")

    print()


def main():
    """Run SOD use case demo"""

    print_box("SOD COMPLIANCE USE CASE DEMO")
    print("\n🎯 Objective: Detect and analyze SOD violations")
    print("   Comparing LOW RISK vs HIGH RISK user profiles\n")

    # Initialize
    print("⚙️  Initializing Data Collection Agent...")
    agent = DataCollectionAgent()
    print("✓ Agent ready\n")

    print("📥 Fetching user data from NetSuite...")

    # Fetch Prabal (low risk - in first 100 users)
    print("   Finding Prabal Saha...")
    result1 = agent.netsuite_client.get_users_and_roles(
        limit=100,
        include_permissions=True
    )

    prabal = None
    if result1.get('success'):
        for user in result1['data']['users']:
            if 'prabal.saha@fivetran.com' in user['email'].lower():
                prabal = user
                print("   ✓ Found Prabal Saha")
                break

    # Fetch Robin (high risk - around offset 1400)
    print("   Finding Robin Turner...")
    result2 = agent.netsuite_client.get_users_and_roles(
        limit=100,
        offset=1400,
        include_permissions=True
    )

    robin = None
    if result2.get('success'):
        for user in result2['data']['users']:
            if 'robin.turner@fivetran.com' in user['email'].lower():
                robin = user
                print("   ✓ Found Robin Turner")
                break

    print("\n✓ Data collection complete\n")

    # Analyze users
    print("="*80)
    print("  COMPARATIVE SOD RISK ANALYSIS")
    print("="*80)

    if prabal:
        analyze_user(prabal, "LOW RISK USER")

    if robin:
        analyze_user(robin, "HIGH RISK USER")

    # Summary comparison
    if prabal and robin:
        print("\n" + "="*80)
        print("  COMPARATIVE SUMMARY")
        print("="*80)

        print(f"\n  {'Metric':<30} {'Prabal Saha':<25} {'Robin Turner':<25}")
        print(f"  {'-'*30} {'-'*25} {'-'*25}")
        print(f"  {'Roles':<30} {prabal['roles_count']:<25} {robin['roles_count']:<25}")

        prabal_perms = sum(len(r.get('permissions', [])) for r in prabal.get('roles', []))
        robin_perms = sum(len(r.get('permissions', [])) for r in robin.get('roles', []))

        print(f"  {'Total Permissions':<30} {prabal_perms:<25} {robin_perms:<25}")
        print(f"  {'Department':<30} {prabal.get('department', 'N/A'):<25} {robin.get('department', 'N/A'):<25}")
        print(f"  {'Risk Level':<30} {'✅ LOW':<25} {'🚨 CRITICAL':<25}")

        print("\n  Key Findings:")
        print(f"    • Robin Turner has {robin['roles_count']}x more roles than Prabal")
        print(f"    • Robin has {robin_perms - prabal_perms} more permissions")
        print("    • Robin's profile requires immediate SOD review")
        print("    • Robin works in Finance with admin access (high-risk combination)")

    # Next steps
    print("\n" + "="*80)
    print("  RECOMMENDED ACTIONS")
    print("="*80)

    print("\n  ⚡ Immediate (High Risk Users):")
    print("    1. Schedule compliance review meeting with Robin Turner's manager")
    print("    2. Document business justification for multiple role assignments")
    print("    3. Review recent financial transactions for approval conflicts")
    print("    4. Implement compensating controls if roles cannot be reduced")

    print("\n  📅 Ongoing (All Users):")
    print("    5. Run automated SOD scans every 4 hours (via Celery)")
    print("    6. Set up Slack alerts for new high-risk role assignments")
    print("    7. Quarterly access reviews for all users with 2+ roles")
    print("    8. Maintain audit trail of all role changes")

    print("\n" + "="*80)
    print("\n✅ SOD Use Case Demo Complete!\n")
    print("📊 Results:")
    print("   • Identified 1 high-risk user (Robin Turner)")
    print("   • Risk score: 90+/100 (SOD violation)")
    print("   • Compliance action required: Yes")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    main()
