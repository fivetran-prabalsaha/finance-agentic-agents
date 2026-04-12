#!/usr/bin/env python3
"""
Quick database query - no dependencies needed
Usage: python quick_query.py "SELECT * FROM users LIMIT 5"
"""

import sys

from sqlalchemy import text

from models.database_config import get_db_config


def run_query(query_string):
    """Run a SQL query and display results"""
    db_config = get_db_config()

    # Test connection
    if not db_config.test_connection():
        print("✗ Cannot connect to database")
        print("\nMake sure PostgreSQL is running:")
        print("  docker-compose up -d postgres")
        return False

    print(f"\n🔍 Running query:\n{query_string}\n")

    try:
        with db_config.get_session_context() as session:
            result = session.execute(text(query_string))

            # Handle SELECT queries
            if query_string.strip().upper().startswith('SELECT'):
                rows = result.fetchall()
                if rows:
                    # Print headers
                    headers = result.keys()
                    print("| " + " | ".join(str(h) for h in headers) + " |")
                    print("|" + "|".join(["-" * (len(str(h)) + 2) for h in headers]) + "|")

                    # Print rows
                    for row in rows:
                        print("| " + " | ".join(str(v)[:50] for v in row) + " |")

                    print(f"\n✓ {len(rows)} rows returned")
                else:
                    print("No rows returned")
            else:
                session.commit()
                print("✓ Query executed successfully")

            return True

    except Exception as e:
        print(f"✗ Query failed: {str(e)}")
        return False


def show_examples():
    """Show example queries"""
    print("""
Quick Query Tool - Usage Examples:

python quick_query.py "SELECT COUNT(*) FROM users"
python quick_query.py "SELECT * FROM users LIMIT 5"
python quick_query.py "SELECT * FROM roles WHERE is_custom = true"
python quick_query.py "SELECT * FROM sod_rules ORDER BY severity DESC"
python quick_query.py "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"

Common queries:
- Show all tables: SELECT tablename FROM pg_tables WHERE schemaname='public'
- Count users: SELECT COUNT(*) FROM users
- Count violations: SELECT COUNT(*) FROM violations
- Show SOD rules: SELECT rule_id, rule_name, severity FROM sod_rules LIMIT 10
""")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python quick_query.py \"YOUR SQL QUERY\"")
        show_examples()
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    run_query(query)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        sys.exit(0)
