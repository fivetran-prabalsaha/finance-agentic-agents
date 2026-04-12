#!/usr/bin/env python3
"""
Test Context-Aware SOD Analysis

Tests that IT/Systems users are correctly exempted from financial SOD rules
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
    print("  CONTEXT-AWARE SOD ANALYSIS TEST")
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

    # Get Prabal Saha
    print("\n📊 Fetching user: Prabal Saha")
    prabal = user_repo.get_user_by_email('prabal.saha@fivetran.com')

    if not prabal:
        print("❌ User not found in database")
        return

    print(f"✅ Found user: {prabal.name}")
    print(f"   Email: {prabal.email}")
    print(f"   Department: {prabal.department}")
    print(f"   Job Function: {prabal.job_function or 'NOT SET'}")
    print(f"   Title: {prabal.title or 'NOT SET'}")

    # Get roles
    user_with_roles = user_repo.get_user_by_uuid(str(prabal.id))
    role_names = [ur.role.role_name for ur in user_with_roles.user_roles if ur.role]
    print(f"   Roles ({len(role_names)}): {', '.join(role_names)}")

    # Test 1: Check if user is identified as IT/Systems
    print("\n🔍 Test 1: Is user identified as IT/Systems?")
    is_it_user = analyzer._is_it_systems_user(prabal)
    print(f"   Result: {is_it_user}")

    if is_it_user:
        print("   ✅ PASS: User correctly identified as IT/Systems")
    else:
        print("   ❌ FAIL: User should be identified as IT/Systems")
        print(f"   Reason: job_function='{prabal.job_function}', department='{prabal.department}'")

    # Test 2: Count financial rules
    print("\n🔍 Test 2: How many financial rules exist?")
    financial_rules = [r for r in analyzer.sod_rules if analyzer._is_financial_rule(r)]
    print(f"   Total SOD Rules: {len(analyzer.sod_rules)}")
    print(f"   Financial Rules: {len(financial_rules)}")

    # Test 3: Run SOD analysis
    print(f"\n🔍 Test 3: Running SOD analysis on {prabal.name}...")

    violations = analyzer._analyze_user(prabal, scan_id=None)

    print("\n📊 Analysis Results:")
    print(f"   Violations Detected: {len(violations)}")

    if violations:
        print("\n🚨 Violations Found:")
        for i, v in enumerate(violations[:5], 1):
            print(f"\n   {i}. {v['title']}")
            print(f"      Rule Type: {v.get('rule_type', 'Unknown')}")
            print(f"      Severity: {v['severity']}")
            print(f"      Risk: {v['risk_score']}/100")
    else:
        print("\n✅ No violations detected")
        print("   💡 IT/Systems user correctly exempted from financial SOD rules")

    # Test 4: Check a non-IT user for comparison
    print("\n🔍 Test 4: Comparing with Robin Turner (Finance user)...")
    robin = user_repo.get_user_by_email('robin.turner@fivetran.com')

    if robin:
        print(f"✅ Found user: {robin.name}")
        print(f"   Department: {robin.department}")
        print(f"   Job Function: {robin.job_function or 'NOT SET'}")

        is_it_user_robin = analyzer._is_it_systems_user(robin)
        print(f"   Is IT/Systems: {is_it_user_robin}")

        robin_violations = analyzer._analyze_user(robin, scan_id=None)
        print(f"   Violations: {len(robin_violations)}")

        if robin_violations:
            print("   🚨 Robin Turner correctly flagged with violations")
        else:
            print("   ⚠️  Robin Turner has no violations (unexpected)")

    # Summary
    print("\n" + "="*80)
    print("  TEST SUMMARY")
    print("="*80)

    tests_passed = 0
    tests_total = 3

    if is_it_user:
        tests_passed += 1
        print("✅ Test 1: IT/Systems user identification - PASS")
    else:
        print("❌ Test 1: IT/Systems user identification - FAIL")

    if financial_rules:
        tests_passed += 1
        print(f"✅ Test 2: Financial rules loaded - PASS ({len(financial_rules)} rules)")
    else:
        print("❌ Test 2: Financial rules loaded - FAIL")

    if len(violations) == 0 and is_it_user:
        tests_passed += 1
        print("✅ Test 3: Context-aware exemption - PASS (no violations for IT user)")
    elif len(violations) > 0 and is_it_user:
        print(f"❌ Test 3: Context-aware exemption - FAIL (IT user still has {len(violations)} violations)")
    else:
        print("⚠️  Test 3: Context-aware exemption - INCONCLUSIVE")

    print(f"\n📊 Tests Passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("🎉 ALL TESTS PASSED - Context-aware SOD analysis is working!")
    else:
        print("⚠️  SOME TESTS FAILED - Review the output above")

    session.close()
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
