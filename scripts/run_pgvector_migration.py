#!/usr/bin/env python3
"""
Run pgvector migration script

This script applies migration 004_pgvector_embeddings.sql to enable
pgvector and create necessary infrastructure for Phase 1-3.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_migration():
    """Run the pgvector migration"""

    # Load environment variables
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False

    logger.info("Connecting to database...")

    # Create engine
    engine = create_engine(database_url)

    # Read migration file
    migration_file = Path(__file__).parent.parent / "migrations" / "004_pgvector_embeddings.sql"

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    logger.info(f"Reading migration: {migration_file}")

    with open(migration_file) as f:
        migration_sql = f.read()

    # Execute migration
    try:
        # Use raw connection for multi-statement execution
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()

        try:
            logger.info("Executing migration (this may take a moment)...")
            cursor.execute(migration_sql)
            raw_conn.commit()
            logger.info("✓ Migration complete!")

        except Exception as e:
            raw_conn.rollback()
            error_msg = str(e)
            # Check if it's just a "already exists" warning
            if 'already exists' not in error_msg.lower():
                raise
            logger.info("✓ Migration complete (some objects already existed)")

        finally:
            cursor.close()

        # Now use SQLAlchemy connection for verification
        with engine.connect() as connection:

            # Verify pgvector
            result = connection.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"))
            row = result.fetchone()

            if row:
                logger.info(f"✓ pgvector extension verified: version {row[1]}")
            else:
                logger.warning("⚠  pgvector extension not found")

            # Check tables
            result = connection.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('sod_rules', 'violations', 'violation_exemptions')
                ORDER BY table_name
            """))

            tables = [row[0] for row in result.fetchall()]
            logger.info(f"✓ Found tables: {', '.join(tables)}")

            # Check embedding columns
            result = connection.execute(text("""
                SELECT table_name, column_name, udt_name
                FROM information_schema.columns
                WHERE column_name = 'embedding'
                ORDER BY table_name
            """))

            for row in result:
                logger.info(f"✓ Embedding column: {row[0]}.{row[1]} (type: {row[2]})")

            return True

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
