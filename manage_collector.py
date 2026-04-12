#!/usr/bin/env python3
"""
Management CLI for Autonomous Data Collection Agent

Usage:
    python manage_collector.py start       # Start the agent
    python manage_collector.py stop        # Stop the agent
    python manage_collector.py status      # Show sync status
    python manage_collector.py sync        # Trigger manual sync
    python manage_collector.py history     # Show recent sync history
    python manage_collector.py stats       # Show sync statistics
"""

import argparse
import logging
import sys

from agents.data_collector import (
    get_collection_agent,
    start_collection_agent,
    stop_collection_agent,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_start(args):
    """Start the autonomous collection agent"""
    print("🚀 Starting Autonomous Data Collection Agent...")

    try:
        start_collection_agent()
        print("✅ Agent started successfully!")
        print("\nScheduled Jobs:")
        print("  • Full sync: Daily at 2:00 AM")
        print("  • Incremental sync: Every hour")
        print("\nThe agent will run in the background.")
        print("Use 'python manage_collector.py status' to check sync status")
        print("Use 'python manage_collector.py stop' to stop the agent")

        # Keep the process running
        if args.daemon:
            print("\nRunning in daemon mode... Press Ctrl+C to stop")
            try:
                import time
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\n🛑 Stopping agent...")
                stop_collection_agent()
                print("✅ Agent stopped")

    except Exception as e:
        print(f"❌ Failed to start agent: {str(e)}")
        logger.error("Failed to start agent", exc_info=True)
        sys.exit(1)


def cmd_stop(args):
    """Stop the autonomous collection agent"""
    print("🛑 Stopping Autonomous Data Collection Agent...")

    try:
        stop_collection_agent()
        print("✅ Agent stopped successfully")
    except Exception as e:
        print(f"❌ Failed to stop agent: {str(e)}")
        logger.error("Failed to stop agent", exc_info=True)
        sys.exit(1)


def cmd_status(args):
    """Show current sync status"""
    print("📊 Autonomous Collection Agent Status\n")

    try:
        agent = get_collection_agent()
        status = agent.get_sync_status(args.system)

        # Agent running status
        print(f"Agent Status: {'🟢 Running' if status['is_running'] else '🔴 Stopped'}")
        print()

        # Last successful sync
        if status['last_successful_sync']:
            last = status['last_successful_sync']
            print("Last Successful Sync:")
            print(f"  • Completed: {last['completed_at']}")
            print(f"  • Duration: {last['duration']:.2f}s" if last['duration'] else "  • Duration: N/A")
            print(f"  • Users Synced: {last['users_synced']}")
            print()
        else:
            print("Last Successful Sync: None\n")

        # Recent syncs
        if status['recent_syncs']:
            print(f"Recent Syncs (Last {len(status['recent_syncs'])}):")
            for sync in status['recent_syncs'][:5]:
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏳'
                }.get(sync['status'], '❓')

                print(f"  {status_emoji} {sync['started_at']} - {sync['type'].upper()} - {sync['status'].upper()}")
                if sync['duration']:
                    print(f"     Duration: {sync['duration']:.2f}s, Users: {sync['users_synced']}")
            print()

        # 7-day statistics
        if status['statistics_7d']:
            stats = status['statistics_7d']
            print("7-Day Statistics:")
            print(f"  • Total Syncs: {stats['total_syncs']}")
            print(f"  • Success Rate: {stats['success_rate']:.1f}%")
            print(f"  • Avg Duration: {stats['avg_duration']:.2f}s")
            print(f"  • Total Users Synced: {stats['total_users_synced']}")
            print(f"  • Total Roles Synced: {stats['total_roles_synced']}")
            print(f"  • Total Violations Detected: {stats['total_violations_detected']}")

    except Exception as e:
        print(f"❌ Failed to get status: {str(e)}")
        logger.error("Failed to get status", exc_info=True)
        sys.exit(1)


def cmd_sync(args):
    """Trigger manual sync"""
    sync_type = args.type or 'full'
    system = args.system or 'netsuite'

    print(f"🔄 Triggering {sync_type.upper()} sync for {system}...\n")

    try:
        agent = get_collection_agent()
        result = agent.manual_sync(system_name=system, sync_type=sync_type)

        if result['success']:
            print("✅ Sync completed successfully!\n")
            print(f"Sync ID: {result['sync_id']}")
            print(f"Duration: {result['duration']:.2f}s")
            print(f"Users Fetched: {result['users_fetched']}")
            print(f"Users Synced: {result['users_synced']}")
            print(f"Roles Synced: {result['roles_synced']}")
            print(f"Violations Detected: {result['violations_detected']}")
        else:
            print(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Failed to trigger sync: {str(e)}")
        logger.error("Failed to trigger sync", exc_info=True)
        sys.exit(1)


def cmd_history(args):
    """Show recent sync history"""
    print("📜 Recent Sync History\n")

    try:
        agent = get_collection_agent()
        from repositories.sync_metadata_repository import SyncMetadataRepository

        sync_repo = SyncMetadataRepository(agent.session)
        recent = sync_repo.get_recent_syncs(
            system_name=args.system,
            limit=args.limit or 20
        )

        if not recent:
            print("No sync history found")
            return

        for sync in recent:
            status_emoji = {
                'success': '✅',
                'failed': '❌',
                'running': '🔄',
                'pending': '⏳'
            }.get(sync.status.value, '❓')

            print(f"{status_emoji} {sync.sync_type.value.upper()} - {sync.status.value.upper()}")
            print(f"   ID: {sync.id}")
            print(f"   Started: {sync.started_at}")
            if sync.completed_at:
                print(f"   Completed: {sync.completed_at}")
                print(f"   Duration: {sync.duration_seconds:.2f}s")
            print(f"   Users: {sync.users_synced or 0}, Roles: {sync.roles_synced or 0}, Violations: {sync.violations_detected or 0}")

            if sync.error_message:
                print(f"   ❌ Error: {sync.error_message}")

            print()

    except Exception as e:
        print(f"❌ Failed to get history: {str(e)}")
        logger.error("Failed to get history", exc_info=True)
        sys.exit(1)


def cmd_stats(args):
    """Show sync statistics"""
    system = args.system or 'netsuite'
    days = args.days or 7

    print(f"📈 Sync Statistics for {system} (Last {days} days)\n")

    try:
        agent = get_collection_agent()
        from repositories.sync_metadata_repository import SyncMetadataRepository

        sync_repo = SyncMetadataRepository(agent.session)
        stats = sync_repo.get_sync_statistics(system, days=days)

        if stats['total_syncs'] == 0:
            print("No syncs found in this period")
            return

        print(f"Total Syncs: {stats['total_syncs']}")
        print(f"  • Successful: {stats['successful']} ({stats['success_rate']:.1f}%)")
        print(f"  • Failed: {stats['failed']}")
        print()
        print("Performance:")
        print(f"  • Average Duration: {stats['avg_duration']:.2f}s")
        print()
        print("Data Synced:")
        print(f"  • Total Users: {stats['total_users_synced']}")
        print(f"  • Total Roles: {stats['total_roles_synced']}")
        print(f"  • Total Violations: {stats['total_violations_detected']}")

    except Exception as e:
        print(f"❌ Failed to get statistics: {str(e)}")
        logger.error("Failed to get statistics", exc_info=True)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Manage Autonomous Data Collection Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_collector.py start --daemon    # Start agent in daemon mode
  python manage_collector.py status           # Check current status
  python manage_collector.py sync --type full # Trigger full sync
  python manage_collector.py history --limit 10  # Show last 10 syncs
  python manage_collector.py stats --days 30  # Show 30-day statistics
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    subparsers.required = True

    # Start command
    start_parser = subparsers.add_parser('start', help='Start the agent')
    start_parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run in daemon mode (stays running)'
    )
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop the agent')
    stop_parser.set_defaults(func=cmd_stop)

    # Status command
    status_parser = subparsers.add_parser('status', help='Show sync status')
    status_parser.add_argument(
        '--system', '-s',
        help='Filter by system name (default: netsuite)'
    )
    status_parser.set_defaults(func=cmd_status)

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Trigger manual sync')
    sync_parser.add_argument(
        '--type', '-t',
        choices=['full', 'incremental'],
        default='full',
        help='Type of sync to perform'
    )
    sync_parser.add_argument(
        '--system', '-s',
        default='netsuite',
        help='System to sync (default: netsuite)'
    )
    sync_parser.set_defaults(func=cmd_sync)

    # History command
    history_parser = subparsers.add_parser('history', help='Show sync history')
    history_parser.add_argument(
        '--system', '-s',
        help='Filter by system name'
    )
    history_parser.add_argument(
        '--limit', '-l',
        type=int,
        default=20,
        help='Number of records to show (default: 20)'
    )
    history_parser.set_defaults(func=cmd_history)

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show sync statistics')
    stats_parser.add_argument(
        '--system', '-s',
        default='netsuite',
        help='System to analyze (default: netsuite)'
    )
    stats_parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Number of days to analyze (default: 7)'
    )
    stats_parser.set_defaults(func=cmd_stats)

    # Parse and execute
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
