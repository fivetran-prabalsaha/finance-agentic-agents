#!/usr/bin/env python3
"""
SOD Analysis Agent Demo

Demonstrates automated SOD violation detection using AI-powered analysis
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.analyzer import SODAnalysisAgent
from models.database_config import DatabaseConfig, get_session
from repositories.role_repository import RoleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_analyzer_capabilities():
    """Main demo showcasing analyzer capabilities"""

    print_header("SOD ANALYSIS AGENT - COMPREHENSIVE DEMO")

    print("This demo showcases:")
    print("  ✓ Automated SOD violation detection")
    print("  ✓ Rule-based compliance checking")
    print("  ✓ Risk scoring and prioritization")
    print("  ✓ AI-powered deep analysis with Claude Opus")
    print("  ✓ Violation storage and reporting")
    print()

    # Initialize
    with get_session() as session:
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)

        # Create analyzer
        print_header("STEP 1: Initialize Analysis Agent")

        analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo
        )

        print("✅ SOD Analysis Agent Initialized")
        print("   Model: claude-opus-4.6 (for complex reasoning)")
        print(f"   SOD Rules Loaded: {len(analyzer.sod_rules)}")
        print()
        print("📋 Rule Categories:")

        # Group rules by type
        rule_types = {}
        for rule in analyzer.sod_rules:
            rule_type = rule['rule_type']
            if rule_type not in rule_types:
                rule_types[rule_type] = []
            rule_types[rule_type].append(rule)

        for rule_type, rules in rule_types.items():
            print(f"   - {rule_type}: {len(rules)} rules")

        # Show critical rules
        print()
        print("🚨 Critical SOD Rules:")
        critical_rules = [r for r in analyzer.sod_rules if r['severity'] == 'CRITICAL']
        for rule in critical_rules[:3]:
            print(f"   - {rule['rule_name']}")
            print(f"     {rule['description']}")

        # Analyze specific high-risk user
        print_header("STEP 2: Analyze High-Risk User (Robin Turner)")

        robin_email = 'robin.turner@fivetran.com'
        robin = user_repo.get_user_by_email(robin_email)

        if not robin:
            print(f"❌ User not found: {robin_email}")
            print("💡 Run sync first: python3 scripts/sync_from_netsuite.py --limit 2000")
            return

        print("👤 User Profile:")
        print(f"   Name: {robin.name}")
        print(f"   Email: {robin.email}")
        print(f"   Department: {robin.department}")
        print(f"   Title: {robin.title}")
        print(f"   Status: {robin.status.value}")
        print()

        # Show roles
        print(f"🔐 Assigned Roles: {len(robin.user_roles)}")
        for ur in robin.user_roles:
            role = ur.role
            perm_count = len(role.permissions) if role.permissions else 0
            print(f"   - {role.name} ({perm_count} permissions)")

        # Run violation analysis
        print()
        print("🔍 Running SOD violation detection...")
        violations = analyzer._analyze_user(robin)

        print()
        print("📊 Analysis Results:")
        print(f"   Violations Detected: {len(violations)}")

        if violations:
            print()
            print("🚨 Detected Violations:")

            # Group by severity
            by_severity = {}
            for v in violations:
                sev = v['severity']
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append(v)

            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if severity in by_severity:
                    viols = by_severity[severity]
                    print(f"\n   {severity} ({len(viols)}):")
                    for v in viols:
                        print(f"   ├─ {v['title']}")
                        print(f"   │  Risk Score: {v['risk_score']}/100")
                        print(f"   │  Rule: {v['rule_id']}")
                        print(f"   │  Description: {v['description'][:100]}...")
                        print(f"   │  Conflicting Items: {', '.join(v['conflicting_permissions'][:3])}")
                        print(f"   └─ Status: {v['status']}")

        # Compare with low-risk user
        print_header("STEP 3: Compare with Low-Risk User (Prabal Saha)")

        prabal_email = 'prabal.saha@fivetran.com'
        prabal = user_repo.get_user_by_email(prabal_email)

        if prabal:
            print("👤 User Profile:")
            print(f"   Name: {prabal.name}")
            print(f"   Email: {prabal.email}")
            print(f"   Roles: {len(prabal.user_roles)}")

            prabal_violations = analyzer._analyze_user(prabal)

            print(f"   Violations: {len(prabal_violations)}")
            print()
            print("📊 Risk Comparison:")
            print(f"   Robin Turner:  {len(violations)} violations (HIGH RISK)")
            print(f"   Prabal Saha:   {len(prabal_violations)} violations (LOW RISK)")
        else:
            print("⚠️  User not found in database")

        # Batch analysis
        print_header("STEP 4: Organization-Wide SOD Scan")

        print("🔍 Scanning all active users for SOD violations...")
        print("   (This analyzes every user against all 17 SOD rules)\n")

        result = analyzer.analyze_all_users()

        if result['success']:
            stats = result['stats']

            print("✅ Organization-Wide Scan Complete!\n")
            print("📊 Scan Statistics:")
            print(f"   Users Analyzed: {stats['users_analyzed']}")
            print(f"   Scan Duration: {(stats['end_time'] - stats['start_time']).total_seconds():.2f}s")
            print()
            print("🚨 Violations Detected:")
            print(f"   Total: {stats['violations_detected']}")
            print(f"   ├─ Critical: {stats['critical_violations']}")
            print(f"   ├─ High: {stats['high_violations']}")
            print(f"   └─ Medium: {stats['medium_violations']}")

            # Show top 10 violations by risk score
            if result['violations']:
                print()
                print("🔥 Top 10 Highest Risk Violations:")

                sorted_violations = sorted(
                    result['violations'],
                    key=lambda x: x['risk_score'],
                    reverse=True
                )[:10]

                for i, v in enumerate(sorted_violations, 1):
                    user = user_repo.get_user_by_id(v['user_id'])
                    user_email = user.email if user else 'Unknown'

                    print(f"\n   {i}. {user_email}")
                    print(f"      Rule: {v['title']}")
                    print(f"      Severity: {v['severity']}")
                    print(f"      Risk Score: {v['risk_score']}/100")
                    print(f"      Department: {v['violation_metadata'].get('department', 'N/A')}")

        # Violation summary
        print_header("STEP 5: Compliance Dashboard Summary")

        summary_result = analyzer.get_analysis_summary()

        if summary_result['success']:
            summary = summary_result['summary']

            print("📊 Overall Compliance Status:\n")
            print(f"   Open Violations: {summary.get('total_open', 0)}")

            severity_counts = summary.get('severity_counts', {})
            print("   By Severity:")
            print(f"   ├─ Critical: {severity_counts.get('CRITICAL', 0)}")
            print(f"   ├─ High: {severity_counts.get('HIGH', 0)}")
            print(f"   └─ Medium: {severity_counts.get('MEDIUM', 0)}")

            status_counts = summary.get('status_counts', {})
            print()
            print("   By Status:")
            print(f"   ├─ Open: {status_counts.get('OPEN', 0)}")
            print(f"   ├─ Under Review: {status_counts.get('UNDER_REVIEW', 0)}")
            print(f"   └─ Resolved: {status_counts.get('RESOLVED', 0)}")

            print()
            print("🎯 Recommended Actions:")
            print(f"   1. Address {severity_counts.get('CRITICAL', 0)} critical violations immediately")
            print(f"   2. Review {severity_counts.get('HIGH', 0)} high-severity violations this week")
            print(f"   3. Create remediation plan for {severity_counts.get('MEDIUM', 0)} medium violations")

        # AI Analysis (optional)
        print_header("STEP 6: AI-Powered Deep Analysis")

        run_ai = os.getenv('RUN_AI_ANALYSIS', 'false').lower() == 'true'

        if run_ai and robin:
            print(f"🤖 Running Claude Opus 4.6 analysis on: {robin_email}")
            print("   (This uses advanced AI reasoning for deep insights)\n")

            ai_result = analyzer.analyze_user_with_ai_reasoning(robin_email)

            if ai_result['success']:
                ai_analysis = ai_result['ai_analysis']

                print("✅ AI Analysis Complete!\n")
                print("🎯 Overall Assessment:")
                print(f"   Risk Level: {ai_analysis['overall_risk_level']}")
                print(f"   AI Risk Score: {ai_analysis['risk_score']}/100")
                print(f"   Remediation Priority: {ai_analysis['remediation_priority']}")

                print("\n⚠️  Primary Concerns:")
                for concern in ai_analysis.get('primary_concerns', [])[:3]:
                    print(f"   • {concern}")

                print("\n💡 Top Recommendation:")
                if ai_analysis.get('detailed_recommendations'):
                    rec = ai_analysis['detailed_recommendations'][0]
                    print(f"   Action: {rec['action']}")
                    print(f"   Rationale: {rec['rationale']}")
                    if rec.get('implementation_steps'):
                        print("   Steps:")
                        for step in rec['implementation_steps'][:3]:
                            print(f"      {step}")

                print("\n🛡️  Compensating Controls:")
                for control in ai_analysis.get('compensating_controls', [])[:2]:
                    print(f"   • {control}")
        else:
            print("💡 AI Analysis (SKIPPED)")
            print()
            print("   To enable AI-powered deep analysis:")
            print("   1. Set environment variable: export RUN_AI_ANALYSIS=true")
            print("   2. Ensure ANTHROPIC_API_KEY is set")
            print("   3. Re-run this demo")
            print()
            print("   AI analysis provides:")
            print("   • Deep reasoning about risk implications")
            print("   • Detailed remediation recommendations")
            print("   • Business impact assessment")
            print("   • SOX compliance analysis")

        # Summary
        print_header("DEMO COMPLETE - SUMMARY")

        print("✅ What We Demonstrated:\n")
        print("   1. ✓ Loaded 17 SOD rules covering Financial, IT, Procurement, and Compliance")
        print("   2. ✓ Analyzed individual users for role conflicts")
        print("   3. ✓ Compared high-risk vs low-risk user profiles")
        print("   4. ✓ Performed organization-wide SOD scan")
        print("   5. ✓ Generated compliance dashboard summary")
        print("   6. ✓ (Optional) AI-powered deep analysis with Claude Opus")
        print()
        print("🚀 Next Steps:\n")
        print("   • Review critical violations in compliance dashboard")
        print("   • Create remediation tickets for high-risk users")
        print("   • Set up scheduled scans (daily/weekly)")
        print("   • Configure notification agent for new violations")
        print("   • Export reports for audit purposes")
        print()
        print("📚 Documentation:")
        print("   • Technical Details: docs/DATABASE_LAYER_README.md")
        print("   • Architecture: docs/HYBRID_ARCHITECTURE.md")
        print("   • SOD Rules: database/seed_data/sod_rules.json")
        print()


def main():
    """Run the demo"""
    try:
        # Check database connection
        db_config = DatabaseConfig()
        if not db_config.test_connection():
            print("\n❌ Database connection failed!")
            print("\n💡 Setup instructions:")
            print("   1. Start PostgreSQL: docker-compose up -d postgres")
            print("   2. Initialize database: python3 scripts/init_database.py")
            print("   3. Sync NetSuite data: python3 scripts/sync_from_netsuite.py --limit 2000")
            return

        # Run demo
        demo_analyzer_capabilities()

        print()
        print("="*80)
        print("  ✅ DEMO COMPLETE")
        print("="*80)
        print()

    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
