#!/usr/bin/env python3
"""
Simple interactive database query tool
Usage: python query_db.py
"""

import sys

from sqlalchemy import text
from tabulate import tabulate

from models.database import Role, SODRule, User, Violation
from models.database_config import get_db_config


def test_connection():
    """Test database connection"""
    print("Testing database connection...")
    db_config = get_db_config()
    if db_config.test_connection():
        print("✓ Connected successfully!\n")
        return True
    else:
        print("✗ Connection failed!")
        print("Make sure PostgreSQL is running:")
        print("  docker-compose up -d postgres")
        return False


def show_menu():
    """Display interactive menu"""
    print("\n" + "="*60)
    print("Database Query Tool")
    print("="*60)
    print("1. Show all tables and row counts")
    print("2. View users (first 10)")
    print("3. View roles (first 10)")
    print("4. View SOD rules")
    print("5. View violations")
    print("6. Run custom SQL query")
    print("7. Show database schema")
    print("8. Count records in all tables")
    print("0. Exit")
    print("="*60)


def show_table_counts(session):
    """Show row counts for all tables"""
    tables = ['users', 'roles', 'user_roles', 'sod_rules', 'violations', 'scan_history']
    results = []

    for table in tables:
        try:
            count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            results.append([table, count])
        except Exception as e:
            results.append([table, f"Error: {str(e)[:40]}"])

    print("\nTable Row Counts:")
    print(tabulate(results, headers=['Table', 'Count'], tablefmt='grid'))


def view_users(session):
    """View first 10 users"""
    users = session.query(User).limit(10).all()

    if not users:
        print("No users found")
        return

    data = [[u.user_id, u.name, u.email, u.status.value, u.department] for u in users]
    print("\nUsers (first 10):")
    print(tabulate(data, headers=['User ID', 'Name', 'Email', 'Status', 'Department'], tablefmt='grid'))


def view_roles(session):
    """View first 10 roles"""
    roles = session.query(Role).limit(10).all()

    if not roles:
        print("No roles found")
        return

    data = [[r.role_id, r.role_name, r.is_custom, r.permission_count] for r in roles]
    print("\nRoles (first 10):")
    print(tabulate(data, headers=['Role ID', 'Role Name', 'Custom?', 'Permissions'], tablefmt='grid'))


def view_sod_rules(session):
    """View SOD rules"""
    try:
        rules = session.query(SODRule).limit(20).all()

        if not rules:
            print("No SOD rules found")
            return

        data = [[r.rule_id, r.rule_name[:40], r.severity.value, r.is_active] for r in rules]
        print("\nSOD Rules:")
        print(tabulate(data, headers=['Rule ID', 'Rule Name', 'Severity', 'Active'], tablefmt='grid'))
    except Exception as e:
        print(f"Error viewing SOD rules: {str(e)}")


def view_violations(session):
    """View violations"""
    try:
        violations = session.query(Violation).limit(20).all()

        if not violations:
            print("No violations found")
            return

        data = [[v.violation_id[:8], v.user_id, v.severity.value, v.status.value,
                 str(v.detected_at)[:19]] for v in violations]
        print("\nViolations (first 20):")
        print(tabulate(data, headers=['ID', 'User ID', 'Severity', 'Status', 'Detected'], tablefmt='grid'))
    except Exception as e:
        print(f"Error viewing violations: {str(e)}")


def run_custom_query(session):
    """Run a custom SQL query"""
    print("\nEnter your SQL query (or 'back' to return):")
    print("Example: SELECT * FROM users LIMIT 5;")
    query = input("> ").strip()

    if query.lower() == 'back':
        return

    try:
        result = session.execute(text(query))

        # Try to fetch results if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            rows = result.fetchall()
            if rows:
                headers = result.keys()
                print(tabulate(rows, headers=headers, tablefmt='grid'))
                print(f"\n{len(rows)} rows returned")
            else:
                print("No rows returned")
        else:
            session.commit()
            print("✓ Query executed successfully")
    except Exception as e:
        print(f"✗ Query failed: {str(e)}")
        session.rollback()


def show_schema(session):
    """Show database schema"""
    query = """
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """

    try:
        result = session.execute(text(query))
        rows = result.fetchall()

        if rows:
            print("\nDatabase Schema:")
            print(tabulate(rows, headers=['Table', 'Column', 'Type', 'Nullable'], tablefmt='grid'))
        else:
            print("No tables found")
    except Exception as e:
        print(f"Error: {str(e)}")


def main():
    """Main interactive loop"""
    print("\n" + "🔍 SOD Compliance Database Query Tool".center(60))

    # Test connection first
    if not test_connection():
        sys.exit(1)

    # Get database session
    db_config = get_db_config()

    while True:
        show_menu()
        choice = input("\nSelect option: ").strip()

        try:
            with db_config.get_session_context() as session:
                if choice == '1':
                    show_table_counts(session)
                elif choice == '2':
                    view_users(session)
                elif choice == '3':
                    view_roles(session)
                elif choice == '4':
                    view_sod_rules(session)
                elif choice == '5':
                    view_violations(session)
                elif choice == '6':
                    run_custom_query(session)
                elif choice == '7':
                    show_schema(session)
                elif choice == '8':
                    show_table_counts(session)
                elif choice == '0':
                    print("\nGoodbye!")
                    break
                else:
                    print("Invalid option")
        except Exception as e:
            print(f"Error: {str(e)}")

        input("\nPress Enter to continue...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
