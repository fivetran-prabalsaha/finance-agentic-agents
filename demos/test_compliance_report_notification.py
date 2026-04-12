#!/usr/bin/env python3
"""
Test Compliance Report Notification

Quick test to verify the new send_compliance_report() method works.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.notifier import create_notifier
from models.database_config import DatabaseConfig
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository


def main():
    print("\n" + "="*70)
    print("  COMPLIANCE REPORT NOTIFICATION TEST")
    print("="*70 + "\n")

    # Initialize
    print("1. Initializing repositories...")
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)
    print("   ✓ Repositories initialized\n")

    # Create notifier
    print("2. Creating notification agent...")
    notifier = create_notifier(
        violation_repo=violation_repo,
        user_repo=user_repo
    )
    print(f"   ✓ Notifier ready (Email: {notifier.email_enabled}, Slack: {notifier.slack_enabled})\n")

    # Prepare sample scan summary
    print("3. Preparing sample compliance report...")
    scan_summary = {
        'scan_id': f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'users_analyzed': 1933,
        'total_violations': 247,
        'violations_by_severity': {
            'CRITICAL': 15,
            'HIGH': 62,
            'MEDIUM': 120,
            'LOW': 50
        },
        'top_violators': [
            {
                'name': 'John Smith',
                'email': 'john.smith@company.com',
                'violation_count': 5,
                'risk_score': 89
            },
            {
                'name': 'Jane Doe',
                'email': 'jane.doe@company.com',
                'violation_count': 4,
                'risk_score': 78
            },
            {
                'name': 'Bob Johnson',
                'email': 'bob.j@company.com',
                'violation_count': 3,
                'risk_score': 72
            }
        ],
        'department_stats': {
            'Finance': {
                'users': 45,
                'violations': 82,
                'compliant': 30
            },
            'IT': {
                'users': 38,
                'violations': 56,
                'compliant': 20
            }
        },
        'compliance_rate': 87.2,
        'scan_duration': '45.3s',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    print("   ✓ Sample report prepared\n")
    print(f"   Users Analyzed:    {scan_summary['users_analyzed']}")
    print(f"   Total Violations:  {scan_summary['total_violations']}")
    print(f"   Compliance Rate:   {scan_summary['compliance_rate']}%\n")

    # Send compliance report
    print("4. Sending compliance report notification...\n")

    result = notifier.send_compliance_report(
        scan_summary=scan_summary,
        recipients=['compliance@company.com', 'audit@company.com'],
        channels=['CONSOLE', 'SLACK']  # Will also send EMAIL if configured
    )

    print("\n" + "="*70)
    print("  NOTIFICATION RESULTS")
    print("="*70 + "\n")

    print(f"✅ Report sent at: {result['sent_at']}")
    print(f"   Recipients: {', '.join(result['recipients'])}")
    print(f"   Channels used: {len(result['channels'])}\n")

    for channel, channel_result in result['channels'].items():
        status = "✅" if channel_result.get('success') else "❌"
        print(f"{status} {channel}:")
        print(f"   Status: {channel_result.get('status', 'Unknown')}")
        if channel_result.get('message'):
            print(f"   Message: {channel_result['message']}")

    session.close()

    print("\n" + "="*70)
    print("  ✅ TEST COMPLETE!")
    print("="*70)

    print("\n💡 Next Steps:")
    print("   • Configure SENDGRID_API_KEY in .env for email notifications")
    print("   • Configure SLACK_WEBHOOK_URL in .env for Slack notifications")
    print("   • Run full demo: python3 demos/demo_end_to_end.py")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
