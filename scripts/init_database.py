#!/usr/bin/env python3
"""
Initialize Database - Create tables and setup

Creates all database tables and optionally loads seed data
"""

import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from models.database_config import enable_pgvector, get_db_config, init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def main():
    """Initialize the database"""
    print("\n" + "=" * 80)
    print("  SOD COMPLIANCE DATABASE INITIALIZATION")
    print("=" * 80 + "\n")

    # Test connection first
    print("1. Testing database connection...")
    db_config = get_db_config()

    if not db_config.test_connection():
        print("   ✗ Database connection failed!")
        print("   Please check your DATABASE_URL in .env file")
        print(f"   Current URL: {db_config._safe_url()}")
        return

    print("   ✓ Connection successful\n")

    # Enable pgvector extension
    print("2. Enabling pgvector extension...")
    try:
        enable_pgvector()
        print("   ✓ pgvector enabled\n")
    except Exception as e:
        print(f"   ⚠  Could not enable pgvector: {str(e)}")
        print("   This is optional - continuing...\n")

    # Create tables
    print("3. Creating database tables...")
    try:
        init_database(drop_existing=False)
        print("   ✓ Tables created successfully\n")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        print(f"   ✗ Error: {str(e)}\n")
        return

    # Show created tables
    print("4. Verifying tables...")
    from sqlalchemy import inspect
    inspector = inspect(db_config.engine)
    tables = inspector.get_table_names()

    print(f"   ✓ Found {len(tables)} tables:")
    for table in sorted(tables):
        print(f"     • {table}")

    print("\n" + "=" * 80)
    print("  ✓ DATABASE INITIALIZATION COMPLETE")
    print("=" * 80 + "\n")

    print("Next steps:")
    print("  • Run data collection: python3 scripts/sync_from_netsuite.py")
    print("  • Test database: python3 tests/test_database.py")
    print("  • View data: psql $DATABASE_URL")
    print()


if __name__ == '__main__':
    main()
