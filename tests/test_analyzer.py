#!/usr/bin/env python3
"""
Test suite for SOD Analysis Agent

Tests the analyzer's ability to detect violations and calculate risk scores
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set database URL before imports
os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.analyzer import SODAnalysisAgent
from models.database_config import DatabaseConfig, get_session
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository


def test_analyzer_initialization():
    """Test 1: Analyzer initializes with SOD rules"""
    print("\n" + "="*80)
    print("TEST 1: Analyzer Initialization")
    print("="*80)

    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        print("✅ Analyzer initialized successfully")
        print("   Model: claude-opus-4.6 (for complex reasoning)")
        print(f"   SOD Rules Loaded: {len(analyzer.sod_rules)}")
        print(f"   Rule Types: { {rule['rule_type'] for rule in analyzer.sod_rules} }")

        # Show sample rules
        print("\n   Sample SOD Rules:")
        for rule in analyzer.sod_rules[:3]:
            print(f"   - {rule['rule_id']}: {rule['rule_name']} ({rule['severity']})")

        return analyzer


def test_analyze_specific_users():
    """Test 2: Analyze Robin Turner and Prabal Saha"""
    print("\n" + "="*80)
    print("TEST 2: Analyze Specific Users")
    print("="*80)

    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        # Test users
        test_emails = [
            'prabal.saha@fivetran.com',
            'robin.turner@fivetran.com'
        ]

        results = []
        for email in test_emails:
            print(f"\n📊 Analyzing: {email}")

            user = user_repo.get_user_by_email(email)
            if not user:
                print("   ❌ User not found in database")
                print("   💡 Run: python3 scripts/sync_from_netsuite.py --limit 2000")
                continue

            # Analyze user
            violations = analyzer._analyze_user(user)

            print("   ✅ User found")
            print(f"   Roles: {len(user.user_roles)}")
            print(f"   Role Names: {[ur.role.name for ur in user.user_roles]}")
            print(f"   Violations Detected: {len(violations)}")

            if violations:
                print("\n   🚨 Violations:")
                for v in violations:
                    print(f"      - {v['title']}")
                    print(f"        Severity: {v['severity']}")
                    print(f"        Risk Score: {v['risk_score']}")
                    print(f"        Conflicting Items: {', '.join(v['conflicting_permissions'][:3])}")
            else:
                print("   ✅ No violations detected")

            results.append({
                'email': email,
                'violations': len(violations)
            })

        return results


def test_batch_analysis():
    """Test 3: Batch analyze all users"""
    print("\n" + "="*80)
    print("TEST 3: Batch Analysis (All Users)")
    print("="*80)

    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        print("\n🔍 Running comprehensive SOD analysis...")
        print("   (This may take a few moments)\n")

        result = analyzer.analyze_all_users()

        if result['success']:
            stats = result['stats']
            print("✅ Analysis Complete!")
            print("\n📊 Statistics:")
            print(f"   Users Analyzed: {stats['users_analyzed']}")
            print(f"   Total Violations: {stats['violations_detected']}")
            print(f"   Critical: {stats['critical_violations']}")
            print(f"   High: {stats['high_violations']}")
            print(f"   Medium: {stats['medium_violations']}")
            print(f"   Duration: {(stats['end_time'] - stats['start_time']).total_seconds():.2f}s")

            # Show top 5 violations
            if result['violations']:
                print("\n🚨 Top 5 Violations:")
                sorted_violations = sorted(
                    result['violations'],
                    key=lambda x: x['risk_score'],
                    reverse=True
                )[:5]

                for i, v in enumerate(sorted_violations, 1):
                    # Get user email from database
                    user = user_repo.get_user_by_id(v['user_id'])
                    print(f"\n   {i}. User: {user.email if user else 'Unknown'}")
                    print(f"      Rule: {v['title']}")
                    print(f"      Severity: {v['severity']}")
                    print(f"      Risk Score: {v['risk_score']}")

        else:
            print(f"❌ Analysis failed: {result.get('error')}")

        return result


def test_ai_analysis():
    """Test 4: AI-powered analysis with Claude Opus"""
    print("\n" + "="*80)
    print("TEST 4: AI-Powered Deep Analysis (Claude Opus)")
    print("="*80)

    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        # Test with Robin Turner (high risk user)
        test_email = 'robin.turner@fivetran.com'

        print(f"\n🤖 Running AI analysis on: {test_email}")
        print("   Using Claude Opus 4.6 for deep reasoning...\n")

        result = analyzer.analyze_user_with_ai_reasoning(test_email)

        if result['success']:
            ai_analysis = result['ai_analysis']

            print("✅ AI Analysis Complete!\n")
            print("📊 Overall Assessment:")
            print(f"   Risk Level: {ai_analysis['overall_risk_level']}")
            print(f"   Risk Score: {ai_analysis['risk_score']}/100")
            print(f"   Remediation Priority: {ai_analysis['remediation_priority']}")

            print("\n🎯 Primary Concerns:")
            for concern in ai_analysis.get('primary_concerns', [])[:3]:
                print(f"   - {concern}")

            print("\n💡 Key Recommendation:")
            if ai_analysis.get('detailed_recommendations'):
                rec = ai_analysis['detailed_recommendations'][0]
                print(f"   Action: {rec['action']}")
                print(f"   Rationale: {rec['rationale']}")

            print("\n📋 Business Impact:")
            impact = ai_analysis.get('business_impact_assessment', '')
            print(f"   {impact[:200]}..." if len(impact) > 200 else f"   {impact}")

        else:
            print(f"❌ AI analysis failed: {result.get('error')}")

        return result


def test_violation_summary():
    """Test 5: Get violation summary"""
    print("\n" + "="*80)
    print("TEST 5: Violation Summary Dashboard")
    print("="*80)

    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        result = analyzer.get_analysis_summary()

        if result['success']:
            summary = result['summary']

            print("\n📊 Violation Summary:")
            print(f"   Total Open: {summary.get('total_open', 0)}")
            print(f"   Critical: {summary.get('severity_counts', {}).get('CRITICAL', 0)}")
            print(f"   High: {summary.get('severity_counts', {}).get('HIGH', 0)}")
            print(f"   Medium: {summary.get('severity_counts', {}).get('MEDIUM', 0)}")

            print("\n🚨 Top Critical Violations:")
            for i, v in enumerate(result['top_critical_violations'][:5], 1):
                print(f"   {i}. {v['user_email']}")
                print(f"      Rule: {v['rule']}")
                print(f"      Risk: {v['risk_score']}")

        else:
            print(f"❌ Failed to get summary: {result.get('error')}")

        return result


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("  SOD ANALYSIS AGENT - TEST SUITE")
    print("="*80)

    try:
        # Test database connection
        print("\n🔌 Testing database connection...")
        db_config = DatabaseConfig()
        if not db_config.test_connection():
            print("❌ Database connection failed!")
            print("💡 Make sure PostgreSQL is running and database is initialized")
            print("   docker-compose up -d postgres")
            print("   python3 scripts/init_database.py")
            return

        print("✅ Database connection successful\n")

        # Run tests
        test_analyzer_initialization()
        test_analyze_specific_users()
        test_batch_analysis()

        # Optional: AI analysis (requires API key and costs money)
        run_ai_test = os.getenv('RUN_AI_ANALYSIS', 'false').lower() == 'true'
        if run_ai_test:
            test_ai_analysis()
        else:
            print("\n" + "="*80)
            print("TEST 4: AI Analysis (SKIPPED)")
            print("="*80)
            print("\n💡 Set RUN_AI_ANALYSIS=true to run Claude Opus analysis")

        test_violation_summary()

        print("\n" + "="*80)
        print("  ✅ ALL TESTS COMPLETE")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
