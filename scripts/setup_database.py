#!/usr/bin/env python3
"""
Setup Database for SOD Compliance System

Creates database, user, and initializes schema.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def print_step(step_num, message):
    """Print formatted step"""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {message}")
    print(f"{'='*70}")

def create_database_and_user():
    """Create database and user using psycopg2"""

    print_step(1, "Creating Database and User")

    # Connect to default postgres database as superuser
    try:
        # Try to connect to existing postgres database
        conn = psycopg2.connect(
            dbname='postgres',
            user=os.getenv('USER'),  # Current system user
            host='localhost',
            port='5432'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("✅ Connected to PostgreSQL")

        # Create user if not exists
        print("\n📝 Creating user 'compliance_user'...")
        try:
            cursor.execute("DROP USER IF EXISTS compliance_user;")
            cursor.execute("CREATE USER compliance_user WITH PASSWORD 'compliance_pass';")
            print("✅ User 'compliance_user' created")
        except Exception as e:
            print(f"⚠️  User creation: {e}")

        # Create database if not exists
        print("\n📝 Creating database 'compliance_db'...")
        try:
            cursor.execute("DROP DATABASE IF EXISTS compliance_db;")
            cursor.execute("CREATE DATABASE compliance_db OWNER compliance_user;")
            print("✅ Database 'compliance_db' created")
        except Exception as e:
            print(f"⚠️  Database creation: {e}")

        # Grant privileges
        print("\n📝 Granting privileges...")
        try:
            cursor.execute("GRANT ALL PRIVILEGES ON DATABASE compliance_db TO compliance_user;")
            print("✅ Privileges granted")
        except Exception as e:
            print(f"⚠️  Privilege grant: {e}")

        cursor.close()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        print("\n💡 Trying alternative connection method...")

        # Try without user specification
        try:
            conn = psycopg2.connect(
                dbname='postgres',
                host='localhost',
                port='5432'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            print("✅ Connected to PostgreSQL (no user)")

            # Create user
            try:
                cursor.execute("DROP USER IF EXISTS compliance_user;")
                cursor.execute("CREATE USER compliance_user WITH PASSWORD 'compliance_pass';")
                print("✅ User 'compliance_user' created")
            except Exception as e:
                print(f"⚠️  User: {e}")

            # Create database
            try:
                cursor.execute("DROP DATABASE IF EXISTS compliance_db;")
                cursor.execute("CREATE DATABASE compliance_db OWNER compliance_user;")
                print("✅ Database 'compliance_db' created")
            except Exception as e:
                print(f"⚠️  Database: {e}")

            # Grant privileges
            try:
                cursor.execute("GRANT ALL PRIVILEGES ON DATABASE compliance_db TO compliance_user;")
                print("✅ Privileges granted")
            except Exception as e:
                print(f"⚠️  Privileges: {e}")

            cursor.close()
            conn.close()

            return True

        except Exception as e2:
            print(f"❌ Alternative connection also failed: {e2}")
            return False

def initialize_schema():
    """Create all tables using SQLAlchemy models"""

    print_step(2, "Initializing Database Schema")

    # Set DATABASE_URL for this session
    os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

    try:
        from models.database_config import Base, DatabaseConfig

        print("📝 Loading database models...")

        print(f"✅ Models loaded: {len(Base.metadata.tables)} tables")

        # Create database config
        db_config = DatabaseConfig()

        print("\n📝 Creating tables...")
        db_config.create_tables()

        print("✅ Schema created successfully")

        # Show created tables
        print("\n📋 Created Tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"   • {table_name}")

        return True

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_database():
    """Verify database setup"""

    print_step(3, "Verifying Database Setup")

    os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

    try:
        from models.database_config import get_db_config

        db_config = get_db_config()

        print("📝 Testing connection...")
        if db_config.test_connection():
            print("✅ Database connection successful")

            # Get session and verify tables
            session = db_config.get_session()

            from repositories.role_repository import RoleRepository
            from repositories.user_repository import UserRepository
            from repositories.violation_repository import ViolationRepository

            user_repo = UserRepository(session)
            role_repo = RoleRepository(session)
            ViolationRepository(session)

            user_count = user_repo.get_user_count()
            role_count = role_repo.get_role_count()

            print("\n📊 Database Statistics:")
            print(f"   • Users: {user_count}")
            print(f"   • Roles: {role_count}")
            print("   • Violations: 0 (no analysis run yet)")

            session.close()

            return True
        else:
            print("❌ Database connection test failed")
            return False

    except Exception as e:
        print(f"❌ Verification error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main setup function"""

    print("\n" + "="*70)
    print("  SOD COMPLIANCE SYSTEM - DATABASE SETUP")
    print("="*70)

    print("\n📋 This script will:")
    print("   1. Create PostgreSQL database 'compliance_db'")
    print("   2. Create user 'compliance_user' with password")
    print("   3. Initialize database schema (tables)")
    print("   4. Verify setup")

    # Step 1: Create database and user
    if not create_database_and_user():
        print("\n❌ Database/user creation failed")
        print("\n💡 Manual setup:")
        print("   psql postgres -c \"CREATE USER compliance_user WITH PASSWORD 'compliance_pass';\"")
        print("   psql postgres -c \"CREATE DATABASE compliance_db OWNER compliance_user;\"")
        return False

    # Step 2: Initialize schema
    if not initialize_schema():
        print("\n❌ Schema initialization failed")
        return False

    # Step 3: Verify
    if not verify_database():
        print("\n❌ Verification failed")
        return False

    # Success
    print("\n" + "="*70)
    print("  ✅ DATABASE SETUP COMPLETE!")
    print("="*70)

    print("\n📊 Connection Details:")
    print("   Database: compliance_db")
    print("   User:     compliance_user")
    print("   Password: compliance_pass")
    print("   Host:     localhost")
    print("   Port:     5432")
    print("   URL:      postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db")

    print("\n🚀 Next Steps:")
    print("   1. Sync data from NetSuite:")
    print("      python3 scripts/sync_from_netsuite.py --limit 20")
    print()
    print("   2. Run end-to-end demo:")
    print("      python3 demos/demo_end_to_end.py")
    print()
    print("   3. Query database:")
    print("      export DATABASE_URL='postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'")
    print("      python3 scripts/query_database.py")
    print()

    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
