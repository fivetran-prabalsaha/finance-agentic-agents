#!/usr/bin/env python3
"""
Fix database constraints and run full sync to fetch all 1,933 users
"""

import sys

from sqlalchemy import text

from agents.data_collector import DataCollectionAgent
from models.database_config import DatabaseConfig


def fix_database_constraints():
    """Update database constraints to match lowercase enum values"""
    print("Fixing database constraints...")

    db_config = DatabaseConfig()
    engine = db_config.engine

    with engine.connect() as conn:
        # Drop old constraints
        conn.execute(text("""
            ALTER TABLE sync_metadata DROP CONSTRAINT IF EXISTS sync_metadata_status_check;
        """))
        conn.execute(text("""
            ALTER TABLE sync_metadata DROP CONSTRAINT IF EXISTS sync_metadata_sync_type_check;
        """))

        # Add new constraints with lowercase values
        conn.execute(text("""
            ALTER TABLE sync_metadata ADD CONSTRAINT sync_metadata_status_check
            CHECK (status IN ('pending', 'running', 'success', 'failed', 'cancelled'));
        """))
        conn.execute(text("""
            ALTER TABLE sync_metadata ADD CONSTRAINT sync_metadata_sync_type_check
            CHECK (sync_type IN ('full', 'incremental', 'manual'));
        """))

        conn.commit()

    print("✅ Database constraints fixed")

def run_full_sync():
    """Run full sync to fetch all 1,933 users"""
    print("\n" + "="*80)
    print("Starting FULL sync from NetSuite")
    print("="*80)
    print("Fetching all 1,933 users (this may take 1-2 minutes)...\n")

    db_config = DatabaseConfig()
    agent = DataCollectionAgent(db_config=db_config, enable_scheduler=False)

    result = agent.full_sync(system_name='netsuite', triggered_by='manual')

    print("\n" + "="*80)
    print("SYNC RESULTS:")
    print("="*80)

    if result.get('success'):
        print("✅ Success!")
        print(f"   Users fetched: {result.get('users_fetched', 0)}")
        print(f"   Users synced: {result.get('users_synced', 0)}")
        print(f"   Roles synced: {result.get('roles_synced', 0)}")
        print(f"   Violations detected: {result.get('violations_detected', 0)}")
        print(f"   Duration: {result.get('duration', 0):.2f} seconds")
    else:
        print(f"❌ Failed: {result.get('error')}")
        return False

    return True

if __name__ == "__main__":
    try:
        # Step 1: Fix database constraints
        fix_database_constraints()

        # Step 2: Run full sync
        success = run_full_sync()

        if success:
            print("\n✅ All done! Database now has all 1,933 users.")
            sys.exit(0)
        else:
            print("\n❌ Sync failed. Check logs above.")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
