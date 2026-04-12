#!/usr/bin/env python3
"""
Verify Local Setup - Tests all components of the local development environment
"""

import os
import sys

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_success(msg):
    print(f"{GREEN}✓ {msg}{NC}")

def print_error(msg):
    print(f"{RED}✗ {msg}{NC}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{NC}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{NC}")

def print_header(msg):
    print(f"\n{BLUE}{'=' * 60}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'=' * 60}{NC}\n")

def test_imports():
    """Test if required Python packages are available"""
    print_header("Testing Python Dependencies")

    failed = []

    packages = [
        ('psycopg2', 'PostgreSQL driver'),
        ('redis', 'Redis client'),
        ('anthropic', 'Claude API client'),
        ('langchain', 'LangChain framework'),
        ('fastapi', 'FastAPI framework'),
        ('pydantic', 'Pydantic validation'),
    ]

    for package, description in packages:
        try:
            __import__(package)
            print_success(f"{description} ({package})")
        except ImportError:
            print_error(f"{description} ({package}) - not installed")
            failed.append(package)

    if failed:
        print_warning(f"\nMissing packages: {', '.join(failed)}")
        print_info("Run: poetry install")
        return False

    return True

def test_database():
    """Test PostgreSQL connection and schema"""
    print_header("Testing Database Connection")

    try:
        import psycopg2

        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='compliance_db',
            user='compliance_user',
            password='compliance_pass',
            connect_timeout=5
        )
        cur = conn.cursor()

        print_success("Connected to PostgreSQL")

        # Check pgvector extension
        cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone():
            print_success("pgvector extension enabled")
        else:
            print_warning("pgvector extension not found")

        # Check tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]

        expected_tables = [
            'users', 'roles', 'user_roles', 'sod_rules',
            'violations', 'compliance_scans', 'agent_logs',
            'audit_trail', 'notifications'
        ]

        for table in expected_tables:
            if table in tables:
                print_success(f"Table '{table}' exists")
            else:
                print_error(f"Table '{table}' missing")

        # Check SOD rules
        cur.execute("SELECT COUNT(*) FROM sod_rules")
        rule_count = cur.fetchone()[0]
        print_info(f"SOD rules loaded: {rule_count}")

        if rule_count > 0:
            # Show sample rules
            cur.execute("""
                SELECT rule_id, rule_name, severity
                FROM sod_rules
                LIMIT 3
            """)
            print_info("Sample rules:")
            for rule_id, rule_name, severity in cur.fetchall():
                print(f"  • {rule_id}: {rule_name} ({severity})")
        else:
            print_warning("No SOD rules loaded - run seed script")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print_error(f"Database connection failed: {e}")
        print_info("Make sure Postgres is running: docker-compose up -d postgres")
        return False

def test_redis():
    """Test Redis connection"""
    print_header("Testing Redis Connection")

    try:
        import redis

        r = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            socket_connect_timeout=5
        )

        # Test ping
        if r.ping():
            print_success("Connected to Redis")

        # Test set/get
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        if value == b'test_value':
            print_success("Redis read/write working")
        r.delete('test_key')

        return True

    except Exception as e:
        print_error(f"Redis connection failed: {e}")
        print_info("Make sure Redis is running: docker-compose up -d redis")
        return False

def test_environment():
    """Test environment configuration"""
    print_header("Testing Environment Configuration")

    if not os.path.exists('.env'):
        print_error(".env file not found")
        print_info("Run: cp .env.example .env")
        return False

    print_success(".env file exists")

    # Check for required variables
    required_vars = [
        'DATABASE_URL',
        'REDIS_URL',
        'ANTHROPIC_API_KEY',
    ]

    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if value and 'xxxxx' not in value:
            print_success(f"{var} is configured")
        else:
            print_warning(f"{var} not configured")
            missing.append(var)

    if missing:
        print_info(f"Configure in .env: {', '.join(missing)}")

    # Check for mock mode
    if os.getenv('USE_MOCK_DATA', '').lower() == 'true':
        print_info("Mock mode enabled (good for local development)")

    return True

def test_claude_api():
    """Test Claude API connection (optional)"""
    print_header("Testing Claude API (Optional)")

    api_key = os.getenv('ANTHROPIC_API_KEY', '')

    if not api_key or 'xxxxx' in api_key:
        print_warning("Claude API key not configured")
        print_info("Set ANTHROPIC_API_KEY in .env to test Claude integration")
        return True  # Not critical for local setup

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Simple test
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful'"}]
        )

        if response.content:
            print_success("Claude API connection working")
            return True

    except Exception as e:
        print_warning(f"Claude API test failed: {e}")
        print_info("This is optional - you can use mock mode for development")
        return True  # Not critical

def main():
    """Run all verification tests"""
    print_header("🔍 Local Setup Verification")

    # Load environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print_success("Loaded .env file")
    except ImportError:
        print_warning("python-dotenv not installed (optional)")

    results = {
        'Python Dependencies': test_imports(),
        'Database': test_database(),
        'Redis': test_redis(),
        'Environment': test_environment(),
        'Claude API': test_claude_api(),
    }

    # Summary
    print_header("📊 Verification Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = f"{GREEN}PASS{NC}" if passed_test else f"{RED}FAIL{NC}"
        print(f"  {test_name}: {status}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print_success("\n✨ All systems ready! You can start building.")
        print_info("\nNext steps:")
        print("  1. Start coding in agents/ directory")
        print("  2. Create your first agent: agents/data_collector.py")
        print("  3. Test with: poetry run python -m agents.data_collector")
        return 0
    else:
        print_warning("\n⚠️  Some tests failed - review errors above")
        print_info("\nCommon fixes:")
        print("  • Install dependencies: poetry install")
        print("  • Start containers: docker-compose up -d")
        print("  • Configure .env: cp .env.example .env")
        return 1

if __name__ == '__main__':
    sys.exit(main())
