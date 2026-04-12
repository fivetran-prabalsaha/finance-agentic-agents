#!/usr/bin/env python3
"""
Quick test of SOD analysis functionality
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.analyzer import create_analyzer
from models.database_config import DatabaseConfig
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository


def main():
    print("="*80)
    print("  SOD ANALYSIS TEST")
    print("="*80)

    # Initialize
    db_config = DatabaseConfig()
    session = db_config.get_session()

    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)
    sod_rule_repo = SODRuleRepository(session)

    # Create analyzer
    analyzer = create_analyzer(
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo
    )

    print("\n✅ Analyzer initialized")
    print(f"   SOD Rules: {len(analyzer.sod_rules)}")

    # Get users
    users = user_repo.get_users_with_roles()
    print(f"\n📊 Found {len(users)} users in database")

    # Show users with their roles
    for user in users[:5]:  # Show first 5
        role_names = [ur.role.role_name for ur in user.user_roles if ur.role]
        print(f"   • {user.name}: {len(role_names)} roles - {', '.join(role_names)}")

    # Run analysis
    print("\n🔍 Running SOD analysis...")

    result = analyzer.analyze_all_users()

    if result['success']:
        stats = result['stats']
        print("\n✅ Analysis Complete!")
        print(f"   Users Analyzed: {stats['users_analyzed']}")
        print(f"   Violations: {stats['violations_detected']}")
        print(f"   • Critical: {stats['critical_violations']}")
        print(f"   • High: {stats['high_violations']}")
        print(f"   • Medium: {stats['medium_violations']}")

        # Show violations
        if result['violations']:
            print("\n🚨 Violations Found:")
            for i, v in enumerate(result['violations'][:3], 1):
                user = user_repo.get_user_by_id(v['user_id'])
                print(f"\n   {i}. {user.name if user else 'Unknown'}")
                print(f"      Rule: {v['title']}")
                print(f"      Severity: {v['severity']}")
                print(f"      Risk: {v['risk_score']}/100")
        else:
            print("\n✅ No violations detected")

    else:
        print(f"\n❌ Analysis failed: {result.get('error')}")

    session.close()
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
