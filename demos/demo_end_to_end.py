#!/usr/bin/env python3
"""
End-to-End Multi-Agent Workflow System Demo

Demonstrates the complete workflow:
1. Initialize system
2. Collect data from NetSuite
3. Analyze for SOD violations
4. Assess risk levels
5. Search knowledge base
6. Send notifications
7. Generate reports
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.knowledge_base_pgvector import create_knowledge_base
from agents.orchestrator import create_orchestrator
from agents.risk_assessor import create_risk_assessor
from models.database_config import DatabaseConfig
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.netsuite_client import NetSuiteClient
from utils.token_tracker import get_global_tracker, reset_global_tracker


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_step(step_num: int, title: str):
    """Print step header"""
    print(f"\n{'─'*80}")
    print(f"STEP {step_num}: {title}")
    print(f"{'─'*80}\n")


def main():
    """Run end-to-end compliance scenario"""

    # Initialize token tracking
    token_tracker = get_global_tracker()
    reset_global_tracker()

    print_header("END-TO-END AGENTIC COMPLIANCE SYSTEM DEMO")
    print("This demo demonstrates the complete compliance run by agents :")
    print("  • Data collection from SaaS platform (NetSuite)")
    print("  • SOD violation detection")
    print("  • Risk assessment and scoring")
    print("  • Knowledge base queries")
    print("  • Notification system")
    print("  • Reporting and analytics")
    print("  • Token usage and cost tracking")
    print()
    input("Press Enter to begin the demo...")

    # ========================================================================
    # STEP 1: System Initialization
    # ========================================================================
    print_step(1, "System Initialization")

    print("Checking database connection...")
    db_config = DatabaseConfig()
    if not db_config.test_connection():
        print("❌ Database connection failed!")
        print("\n💡 Quick fix:")
        print("   docker-compose up -d postgres")
        print("   python3 scripts/init_database.py")
        return

    print("✅ Database connection successful")
    print(f"   URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")

    print("\nInitializing repositories...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)

    print("✅ Repositories initialized")
    print("   • UserRepository")
    print("   • RoleRepository")
    print("   • ViolationRepository")

    # ========================================================================
    # STEP 2: Data Collection
    # ========================================================================
    print_step(2, "Data Collection from NetSuite")

    print("Creating NetSuite client...")
    netsuite_client = NetSuiteClient()

    print("Testing NetSuite connection...")
    if not netsuite_client.test_connection():
        print("❌ NetSuite connection failed!")
        return

    print("✅ NetSuite connection successful")
    print(f"   Account: {os.getenv('NETSUITE_ACCOUNT', 'Not set')}")

    print("\nFetching specific test users from NetSuite...")
    print("   Target Users:")
    print("   1. Jessica Wu (jessica.wu@fivetran.com)")
    print("   2. Robin Turner (robin.turner@fivetran.com)")

    from agents.data_collector import DataCollectionAgent
    DataCollectionAgent(netsuite_client=netsuite_client)

    # Fetch specific users by email
    target_emails = [
        'jessica.wu@fivetran.com',
        'robin.turner@fivetran.com'
    ]

    users = []
    for email in target_emails:
        print(f"\n   Searching for {email}...")
        result = netsuite_client.search_users(
            search_value=email,
            search_type='email',
            include_permissions=True,
            include_inactive=False
        )

        if result['success'] and result['data']['users']:
            user_records = result['data']['users']
            print(f"   ✓ Found {len(user_records)} record(s)")

            for user in user_records:
                print(f"      - {user['name']} (User ID: {user.get('user_id')})")
                users.append(user)
        else:
            print(f"   ⚠️  Not found: {email}")

    if users:
        print(f"\n✅ Fetched {len(users)} user record(s) successfully")

        # Show details
        print("\n📊 Users to Analyze:")
        for i, user in enumerate(users, 1):
            print(f"   {i}. {user['name']} ({user['email']})")
            print(f"      User ID: {user.get('user_id')}")
            print(f"      Roles: {user.get('roles_count', 0)}")
            print(f"      Department: {user.get('department', 'N/A')}")

        # Store in database
        print("\n💾 Storing users in database...")
        db_config = DatabaseConfig()
        session = db_config.get_session()
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)

        stored_count = 0
        for user_data in users:
            try:
                # Store user and get database object with UUID
                user = user_repo.upsert_user(user_data)

                # Store roles and assign to user
                for role_data in user_data.get('roles', []):
                    # Store role and get database object with UUID
                    role = role_repo.upsert_role(role_data)

                    # Use database UUIDs (not NetSuite IDs)
                    user_repo.assign_role_to_user(
                        str(user.id),  # Database UUID
                        str(role.id)   # Database UUID
                    )

                stored_count += 1
            except Exception as e:
                print(f"      Warning: Failed to store {user_data.get('email')}: {str(e)}")
                session.rollback()  # Rollback on error to allow next user to be processed

        print(f"✅ Stored {stored_count} user record(s) in database")
        session.close()
    else:
        print("❌ No users found!")
        return

    # ========================================================================
    # STEP 3: SOD Violation Analysis
    # ========================================================================
    print_step(3, "SOD Violation Detection")

    print("Creating Analysis Agent...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)
    sod_rule_repo = SODRuleRepository(session)

    from agents.analyzer import create_analyzer
    analyzer = create_analyzer(
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo
    )

    print("✅ Analysis Agent initialized")
    print(f"   SOD Rules Loaded: {len(analyzer.sod_rules)}")
    print("   Model: claude-opus-4.6")

    print("\n🔍 Running SOD analysis on all users...")
    print("   (Checking 17 SOD rules across all users)")

    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)
    sod_rule_repo = SODRuleRepository(session)

    analyzer = create_analyzer(
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo
    )

    analysis_result = analyzer.analyze_all_users()

    if analysis_result['success']:
        stats = analysis_result['stats']
        print("\n✅ Analysis Complete!")
        print("\n📊 Results:")
        print(f"   Users Analyzed: {stats['users_analyzed']}")
        print(f"   Total Violations: {stats['violations_detected']}")
        print(f"   • Critical: {stats['critical_violations']}")
        print(f"   • High: {stats['high_violations']}")
        print(f"   • Medium: {stats['medium_violations']}")
        print(f"   Duration: {(stats['end_time'] - stats['start_time']).total_seconds():.2f}s")

        # Show top violations
        if analysis_result['violations']:
            print("\n🚨 Top Violations Detected:")
            sorted_violations = sorted(
                analysis_result['violations'],
                key=lambda x: x['risk_score'],
                reverse=True
            )[:3]

            db_config = DatabaseConfig()
            session = db_config.get_session()
            user_repo = UserRepository(session)

            for i, v in enumerate(sorted_violations, 1):
                    user = user_repo.get_user_by_uuid(v['user_id'])
                    print(f"\n   {i}. {user.name if user else 'Unknown'}")
                    print(f"      Rule: {v['title']}")
                    print(f"      Severity: {v['severity']}")
                    print(f"      Risk Score: {v['risk_score']}/100")
                    print(f"      Description: {v['description'][:100]}...")

        # ================================================================
        # PER-USER COMPLIANCE SUMMARY
        # ================================================================
        print("\n" + "="*80)
        print("  PER-USER COMPLIANCE SUMMARY")
        print("="*80)

        # Get all violations grouped by user
        from collections import defaultdict
        user_violations_map = defaultdict(list)

        for violation in analysis_result.get('violations', []):
            user_violations_map[violation['user_id']].append(violation)

        # Get all target users we analyzed
        target_users = []
        for email in ['jessica.wu@fivetran.com', 'robin.turner@fivetran.com']:
            user_list = user_repo.search_users(email)
            target_users.extend(user_list)

        if target_users:
            for user in target_users:
                violations = user_violations_map.get(str(user.id), [])

                # Calculate risk level
                if violations:
                    max_risk = max(v['risk_score'] for v in violations)
                    critical_count = sum(1 for v in violations if v['severity'] == 'CRITICAL')
                    high_count = sum(1 for v in violations if v['severity'] == 'HIGH')

                    if critical_count > 0 or max_risk >= 80:
                        risk_indicator = "🔴 CRITICAL RISK"
                    elif high_count > 0 or max_risk >= 60:
                        risk_indicator = "🟠 HIGH RISK"
                    elif max_risk >= 40:
                        risk_indicator = "🟡 MEDIUM RISK"
                    else:
                        risk_indicator = "🟢 LOW RISK"
                else:
                    risk_indicator = "✅ NO VIOLATIONS"
                    max_risk = 0

                print(f"\n👤 {user.name} ({user.email})")
                print(f"   Status: {risk_indicator}")
                print(f"   Risk Score: {max_risk}/100")

                # Show roles
                user_with_roles = user_repo.get_user_by_uuid(str(user.id))
                if user_with_roles and hasattr(user_with_roles, 'user_roles'):
                    role_names = [ur.role.role_name for ur in user_with_roles.user_roles if ur.role]
                    print(f"   Roles ({len(role_names)}): {', '.join(role_names)}")

                # Show violations
                if violations:
                    print(f"\n   🚨 Violations Found: {len(violations)}")
                    for i, v in enumerate(violations[:3], 1):  # Show top 3
                        print(f"\n      {i}. {v['title']}")
                        print(f"         Severity: {v['severity']}")
                        print(f"         Risk: {v['risk_score']}/100")
                        print(f"         Issue: {v['description'][:80]}...")

                    if len(violations) > 3:
                        print(f"\n      ... and {len(violations) - 3} more violations")
                else:
                    print("\n   ✅ No SOD violations detected")
                    print("   💡 User's role assignments comply with all SOD rules")

        print("\n" + "="*80)

    else:
        print(f"❌ Analysis failed: {analysis_result.get('error')}")

    # ========================================================================
    # STEP 4: Risk Assessment
    # ========================================================================
    print_step(4, "Organization-Wide Risk Assessment")

    print("Creating Risk Assessment Agent...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    risk_assessor = create_risk_assessor(
        violation_repo=violation_repo,
        user_repo=user_repo
    )

    print("✅ Risk Assessor initialized")

    print("\n📊 Assessing organization risk...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    risk_assessor = create_risk_assessor(
        violation_repo=violation_repo,
        user_repo=user_repo
    )

    risk_result = risk_assessor.assess_organization_risk()

    if risk_result['success']:
        print("\n✅ Risk Assessment Complete!")
        print(f"\n🎯 Organization Risk Level: {risk_result['organization_risk_level']}")
        print(f"   Risk Score: {risk_result['organization_risk_score']}/100")

        print("\n📊 User Risk Distribution:")
        risk_dist = risk_result['risk_distribution']
        print(f"   Critical: {risk_dist['CRITICAL']} users")
        print(f"   High:     {risk_dist['HIGH']} users")
        print(f"   Medium:   {risk_dist['MEDIUM']} users")
        print(f"   Low:      {risk_dist['LOW']} users")

        print("\n💡 Recommendations:")
        for rec in risk_result['recommendations']:
            print(f"   {rec}")

        # Show high-risk users
        if risk_result['high_risk_users']:
            print("\n⚠️  High-Risk Users:")
            for i, user in enumerate(risk_result['high_risk_users'][:3], 1):
                print(f"   {i}. {user['email']}")
                print(f"      Risk Score: {user['risk_score']}/100")
                print(f"      Risk Level: {user['risk_level']}")

    # ========================================================================
    # STEP 5: Knowledge Base Queries
    # ========================================================================
    print_step(5, "Knowledge Base & Semantic Search")

    print("Creating Knowledge Base Agent...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    sod_rule_repo = SODRuleRepository(session)
    kb = create_knowledge_base(session=session, sod_rule_repo=sod_rule_repo)

    # Get stats from pgvector
    stats = kb.get_knowledge_base_stats()

    print("✅ Knowledge Base initialized (pgvector)")
    print(f"   Total Rules: {stats['total_rules']}")
    print(f"   Rules with Embeddings: {stats['rules_with_embeddings']}")
    print(f"   Provider: {stats['embedding_provider']}")
    print(f"   Dimension: {stats['embedding_dimension']}")

    # Semantic search
    print("\n🔍 Performing semantic search...")
    query = "financial approval conflicts"
    print(f"   Query: \"{query}\"")

    sod_rule_repo = SODRuleRepository(session)
    kb = create_knowledge_base(session=session, sod_rule_repo=sod_rule_repo)

    results = kb.search_similar_rules(
        query=query,
        top_k=3,
        min_similarity=0.3
    )

    print(f"\n✅ Found {len(results)} similar rules:")
    for i, result in enumerate(results, 1):
        rule_name = result.get('rule_name', 'Unknown')
        similarity = result.get('similarity', 0)
        rule_type = result.get('category', 'Unknown')
        severity = result.get('severity', 'Unknown')
        description = result.get('description', 'No description')[:80]
        print(f"\n   {i}. {rule_name} (Similarity: {similarity:.2f})")
        print(f"      Type: {rule_type}")
        print(f"      Severity: {severity}")
        print(f"      Description: {description}...")

    # Get knowledge base stats
    stats = kb.get_knowledge_base_stats()

    print("\n📊 Knowledge Base Statistics:")
    print(f"   Total Rules: {stats['total_rules']}")
    print(f"   Rules with Embeddings: {stats['rules_with_embeddings']}")
    print(f"   Violations Embedded: {stats['total_violations_embedded']}")
    print(f"   Provider: {stats['embedding_provider']}")
    print(f"   Dimension: {stats['embedding_dimension']}")

    # ========================================================================
    # STEP 6: Notification System
    # ========================================================================
    print_step(6, "Notification System")

    print("Creating Notification Agent...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    from agents.notifier import create_notifier
    notifier = create_notifier(
        violation_repo=violation_repo,
        user_repo=user_repo
    )

    print("✅ Notification Agent initialized")
    print(f"   Email: {'Enabled' if notifier.email_enabled else 'Disabled (no API key)'}")
    print(f"   Slack: {'Enabled' if notifier.slack_enabled else 'Disabled (no webhook)'}")
    print("   Console: Enabled (fallback)")

    print("\n📧 Testing notification system...")
    print("   (Using console output as demonstration)")

    # Get a critical violation if any exist
    db_config = DatabaseConfig()
    session = db_config.get_session()
    violation_repo = ViolationRepository(session)
    from models.database import ViolationSeverity

    critical_violations = violation_repo.get_open_violations(
        severity=ViolationSeverity.CRITICAL
    )

    if critical_violations:
        sample_violation = critical_violations[0]

        print("\n📋 Sample Notification:")
        print("   To: compliance@company.com")
        print(f"   Subject: 🚨 SOD Violation Detected: {sample_violation.title}")
        print(f"   User: {sample_violation.user.email if sample_violation.user else 'Unknown'}")
        print(f"   Severity: {sample_violation.severity.value}")
        print(f"   Risk Score: {sample_violation.risk_score}/100")
        print("   Status: Ready to send via Email/Slack")
    else:
        print("   ℹ️  No critical violations to demonstrate")

    # Generate user comparison table
    print("\n" + "="*80)
    print("  USER COMPLIANCE COMPARISON TABLE")
    print("="*80 + "\n")

    target_emails = ['jessica.wu@fivetran.com', 'robin.turner@fivetran.com']
    comparison_table = notifier.generate_user_comparison_table(
        user_emails=target_emails,
        include_border=True
    )

    print(comparison_table)
    print("\n" + "="*80)

    # ========================================================================
    # STEP 7: Complete Orchestrator Workflow
    # ========================================================================
    print_step(7, "Orchestrator - Complete Workflow Execution")

    print("Creating Orchestrator...")
    print("   (Coordinates all 6 agents via LangGraph workflow)")

    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    violation_repo = ViolationRepository(session)
    sod_rule_repo = SODRuleRepository(session)

    create_orchestrator(
        netsuite_client=netsuite_client,
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo,
        notification_recipients=['compliance@company.com']
    )

    print("✅ Orchestrator initialized")
    print("   Workflow Stages:")
    print("      1. COLLECT_DATA → Fetch from NetSuite")
    print("      2. ANALYZE_VIOLATIONS → Run SOD analysis")
    print("      3. ASSESS_RISK → Calculate org risk")
    print("      4. SEND_NOTIFICATIONS → Alert stakeholders")
    print("      5. COMPLETE → Finalize and audit")

    print("\n🚀 Executing complete compliance scan...")
    print("   (This demonstrates the full LangGraph workflow)")

    scan_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Note: We'll simulate this to avoid re-fetching
    print(f"\n   Scan ID: {scan_id}")
    print("   Status: SIMULATED (data already collected)")
    print("   ✅ Stage 1: Data Collection - Complete")
    print("   ✅ Stage 2: Violation Analysis - Complete")
    print("   ✅ Stage 3: Risk Assessment - Complete")
    print("   ✅ Stage 4: Notifications - Ready")
    print("   ✅ Stage 5: Finalization - Complete")

    # ========================================================================
    # STEP 8: Reporting & Analytics
    # ========================================================================
    print_step(8, "Reporting & Analytics Dashboard")

    print("Generating compliance dashboard...")

    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    # Get all users
    all_users = user_repo.get_all_users()
    active_users = [u for u in all_users if u.status.value == 'ACTIVE']
    high_risk_users = user_repo.get_high_risk_users(min_roles=3)

    # Get violation summary
    violation_summary = violation_repo.get_violation_summary()

    print("\n📊 Compliance Dashboard:")
    print("\n┌─────────────────────────────────────────────┐")
    print("│         USER STATISTICS                     │")
    print("└─────────────────────────────────────────────┘")
    print(f"   Total Users:      {len(all_users)}")
    print(f"   Active Users:     {len(active_users)}")
    print(f"   High-Risk Users:  {len(high_risk_users)}")

    print("\n┌─────────────────────────────────────────────┐")
    print("│       VIOLATION STATISTICS                  │")
    print("└─────────────────────────────────────────────┘")
    print(f"   Total Open:       {violation_summary.get('total_open', 0)}")
    severity_counts = violation_summary.get('severity_counts', {})
    print(f"   • Critical:       {severity_counts.get('CRITICAL', 0)}")
    print(f"   • High:           {severity_counts.get('HIGH', 0)}")
    print(f"   • Medium:         {severity_counts.get('MEDIUM', 0)}")

    print("\n┌─────────────────────────────────────────────┐")
    print("│         SYSTEM STATUS                       │")
    print("└─────────────────────────────────────────────┘")
    print("   ✅ Data Collection Agent:    Ready")
    print("   ✅ Analysis Agent:            Ready")
    print("   ✅ Risk Assessment Agent:     Ready")
    print("   ✅ Knowledge Base Agent:      Ready")
    print("   ✅ Notification Agent:        Ready")
    print("   ✅ Orchestrator:              Ready")
    print("   ✅ Database:                  Connected")
    print("   ✅ NetSuite Integration:      Active")

    # ========================================================================
    # STEP 9: Send Final Compliance Report
    # ========================================================================
    print_step(9, "Sending Final Compliance Report")

    print("📧 Preparing compliance report notification...")

    # Prepare scan summary data
    scan_duration = (datetime.now() - analysis_result['stats']['start_time']).total_seconds() if analysis_result.get('success') else 0

    scan_summary = {
        'scan_id': scan_id,
        'users_analyzed': len(all_users),
        'total_violations': violation_summary.get('total', 0),
        'violations_by_severity': violation_summary.get('by_severity', {}),
        'top_violators': [],  # Would be populated from actual violation data
        'department_stats': {},  # Would be populated from actual department analysis
        'compliance_rate': ((len(all_users) - violation_summary.get('open', 0)) / max(len(all_users), 1)) * 100,
        'scan_duration': f"{scan_duration:.1f}s",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Get top violators if violations exist
    if violation_summary.get('total', 0) > 0:
        # Get violations and group by user
        from collections import defaultdict
        user_violations = defaultdict(lambda: {'count': 0, 'max_risk': 0})

        all_violations = violation_repo.get_open_violations(limit=1000)
        for v in all_violations:
            user_email = v.user.email if v.user else 'Unknown'
            user_violations[user_email]['count'] += 1
            user_violations[user_email]['max_risk'] = max(
                user_violations[user_email]['max_risk'],
                v.risk_score or 0
            )
            user_violations[user_email]['name'] = v.user.name if v.user else 'Unknown'
            user_violations[user_email]['email'] = user_email

        # Sort and get top 5
        sorted_violators = sorted(
            user_violations.values(),
            key=lambda x: (x['count'], x['max_risk']),
            reverse=True
        )[:5]

        scan_summary['top_violators'] = [
            {
                'name': v['name'],
                'email': v['email'],
                'violation_count': v['count'],
                'risk_score': v['max_risk']
            }
            for v in sorted_violators
        ]

    print("\n📊 Report Summary:")
    print(f"   Users Analyzed:    {scan_summary['users_analyzed']}")
    print(f"   Total Violations:  {scan_summary['total_violations']}")
    print(f"   Compliance Rate:   {scan_summary['compliance_rate']:.1f}%")
    print(f"   Scan Duration:     {scan_summary['scan_duration']}")

    # Send via notification agent
    print("\n📤 Sending compliance report...")

    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    notifier = create_notifier(
        violation_repo=violation_repo,
        user_repo=user_repo
    )

    notification_result = notifier.send_compliance_report(
        scan_summary=scan_summary,
        recipients=['compliance@company.com'],
        channels=['CONSOLE', 'SLACK']  # Email will be sent if SENDGRID_API_KEY is configured
    )

    print("\n✅ Compliance report sent!")
    print(f"   Channels: {', '.join(notification_result.get('channels', {}).keys())}")

    for channel, result in notification_result.get('channels', {}).items():
        status = "✅" if result.get('success') else "❌"
        print(f"   {status} {channel}: {result.get('status', 'Unknown')}")

    session.close()

    # ========================================================================
    # TOKEN USAGE & COST SUMMARY
    # ========================================================================
    print_step(10, "Token Usage & Cost Analysis")

    token_tracker = get_global_tracker()
    token_tracker.print_summary()

    # Detailed cost breakdown
    summary = token_tracker.get_summary()
    if summary['total_cost'] > 0:
        print("\n💰 Cost Analysis:")
        print(f"   Cost per User Analyzed:     ${summary['total_cost'] / max(len(all_users), 1):.4f}")
        print(f"   Cost per Violation Found:   ${summary['total_cost'] / max(violation_summary.get('total', 1), 1):.4f}")
        print(f"   Estimated Monthly Cost*:    ${summary['total_cost'] * 30:.2f}")
        print(f"   Estimated Annual Cost*:     ${summary['total_cost'] * 365:.2f}")
        print("\n   * Based on daily scan with similar data volume")




if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
