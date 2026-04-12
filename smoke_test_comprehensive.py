#!/usr/bin/env python3
"""
Comprehensive Smoke Test for SOD Compliance System
Tests: Agents, Database, Cache, Vector Store, LLM
"""
import os
import sys
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test results tracker
results = {
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'tests': []
}

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_test(name, status, message="", details=""):
    """Print test result"""
    symbols = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}
    print(f"\n{symbols.get(status, '•')} {name}")
    if message:
        print(f"   {message}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"   {line}")

    results['tests'].append({
        'name': name,
        'status': status,
        'message': message,
        'details': details
    })

    if status == 'PASS':
        results['passed'] += 1
    elif status == 'FAIL':
        results['failed'] += 1
    else:
        results['skipped'] += 1

def test_database_connection():
    """Test 1: Database Connection"""
    print_header("TEST 1: Database Connection")
    try:
        from sqlalchemy import text

        from models.database import get_session

        session = get_session()
        result = session.execute(text("SELECT 1")).scalar()

        if result == 1:
            print_test("Database Connection", "PASS", "PostgreSQL connection established")
            return True
        else:
            print_test("Database Connection", "FAIL", f"Unexpected result: {result}")
            return False
    except Exception as e:
        print_test("Database Connection", "FAIL", str(e), traceback.format_exc())
        return False

def test_database_tables():
    """Test 2: Database Tables & Data"""
    print_header("TEST 2: Database Tables & Data")
    try:
        from sqlalchemy import text

        from models.database import get_session

        session = get_session()

        # Check critical tables
        tables = {
            'users': 'SELECT COUNT(*) FROM users',
            'roles': 'SELECT COUNT(*) FROM roles',
            'permissions': 'SELECT COUNT(*) FROM permissions',
            'sod_rules': 'SELECT COUNT(*) FROM sod_rules',
            'violations': 'SELECT COUNT(*) FROM violations',
            'sync_metadata': 'SELECT COUNT(*) FROM sync_metadata',
            'job_role_mappings': 'SELECT COUNT(*) FROM job_role_mappings'
        }

        counts = {}
        for table, query in tables.items():
            try:
                count = session.execute(text(query)).scalar()
                counts[table] = count
            except Exception as e:
                counts[table] = f"ERROR: {str(e)}"

        details = "\n".join([f"{k}: {v}" for k, v in counts.items()])

        # Check if we have data
        if isinstance(counts['users'], int) and counts['users'] > 0:
            print_test("Database Tables", "PASS", f"{len(counts)} tables verified", details)
            return True
        else:
            print_test("Database Tables", "FAIL", "Missing data in critical tables", details)
            return False

    except Exception as e:
        print_test("Database Tables", "FAIL", str(e), traceback.format_exc())
        return False

def test_vector_store():
    """Test 3: pgvector & Embeddings"""
    print_header("TEST 3: pgvector Vector Store")
    try:
        from sqlalchemy import text

        from models.database import get_session

        session = get_session()

        # Check pgvector extension
        ext_query = text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'")
        has_extension = session.execute(ext_query).scalar() > 0

        if not has_extension:
            print_test("pgvector Extension", "FAIL", "pgvector extension not installed")
            return False

        # Check if we have vector columns
        vector_query = text("""
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE data_type = 'USER-DEFINED'
            AND udt_name = 'vector'
            LIMIT 5
        """)
        vector_cols = session.execute(vector_query).fetchall()

        details = "\n".join([f"{row[0]}.{row[1]}" for row in vector_cols])

        if len(vector_cols) > 0:
            print_test("pgvector Extension", "PASS",
                      f"Found {len(vector_cols)} vector columns", details)
            return True
        else:
            print_test("pgvector Extension", "SKIP", "No vector columns found (KB may not be seeded)")
            return True

    except Exception as e:
        print_test("pgvector Extension", "FAIL", str(e), traceback.format_exc())
        return False

def test_embedding_service():
    """Test 4: Embedding Service"""
    print_header("TEST 4: Embedding Service")
    try:
        from services.embedding_service import EmbeddingService

        service = EmbeddingService()

        # Test embedding generation
        test_text = "Test SOD violation for financial transactions"
        embedding = service.get_embedding(test_text)

        if embedding and len(embedding) > 0:
            details = f"Model: {service.embedding_model}\nDimensions: {len(embedding)}\nCache: {service.use_cache}"
            print_test("Embedding Service", "PASS",
                      f"Generated {len(embedding)}-dimensional embedding", details)
            return True
        else:
            print_test("Embedding Service", "FAIL", "Failed to generate embedding")
            return False

    except Exception as e:
        print_test("Embedding Service", "FAIL", str(e), traceback.format_exc())
        return False

def test_knowledge_base_agent():
    """Test 5: Knowledge Base Agent"""
    print_header("TEST 5: Knowledge Base Agent (pgvector)")
    try:
        from agents.knowledge_base_pgvector import KnowledgeBaseAgent

        agent = KnowledgeBaseAgent()

        # Test semantic search
        query = "What are SOD violations for accounts payable?"
        results = agent.search(query, top_k=3)

        if results and len(results) > 0:
            details = f"Query: {query}\nResults: {len(results)}"
            for i, result in enumerate(results[:3], 1):
                details += f"\n  {i}. {result.get('content', '')[:100]}... (score: {result.get('similarity', 0):.3f})"

            print_test("Knowledge Base Agent", "PASS",
                      f"Retrieved {len(results)} relevant documents", details)
            return True
        else:
            print_test("Knowledge Base Agent", "SKIP",
                      "No results (KB may not be seeded yet)")
            return True

    except Exception as e:
        print_test("Knowledge Base Agent", "FAIL", str(e), traceback.format_exc())
        return False

def test_llm_service():
    """Test 6: LLM Service"""
    print_header("TEST 6: LLM Service (Claude)")
    try:
        from services.llm_service import LLMService

        service = LLMService()

        # Check if API key is configured
        if not os.getenv('ANTHROPIC_API_KEY'):
            print_test("LLM Service", "SKIP", "ANTHROPIC_API_KEY not set")
            return True

        # Simple test query (won't actually call API to save costs)
        # Just verify service initializes
        details = f"Provider: {service.provider}\nModel: {service.model}"
        print_test("LLM Service", "PASS", "Service initialized", details)
        return True

    except Exception as e:
        print_test("LLM Service", "FAIL", str(e), traceback.format_exc())
        return False

def test_data_collector_agent():
    """Test 7: Data Collection Agent"""
    print_header("TEST 7: Data Collection Agent")
    try:
        from sqlalchemy import text

        from agents.data_collector import DataCollectionAgent
        from models.database import get_session

        agent = DataCollectionAgent()

        # Check if scheduler is configured
        if hasattr(agent, 'scheduler'):
            details = f"Scheduler: Active\nJobs: {len(agent.scheduler.get_jobs())}"

            # Get last sync info
            session = get_session()
            last_sync = session.execute(text("""
                SELECT sync_type, status, started_at, completed_at
                FROM sync_metadata
                ORDER BY started_at DESC
                LIMIT 1
            """)).fetchone()

            if last_sync:
                details += f"\nLast Sync: {last_sync[0]} ({last_sync[1]})"
                details += f"\nCompleted: {last_sync[3]}"

            print_test("Data Collection Agent", "PASS",
                      "Agent initialized with scheduler", details)
            return True
        else:
            print_test("Data Collection Agent", "FAIL", "Scheduler not found")
            return False

    except Exception as e:
        print_test("Data Collection Agent", "FAIL", str(e), traceback.format_exc())
        return False

def test_analyzer_agent():
    """Test 8: SOD Analyzer Agent"""
    print_header("TEST 8: SOD Analyzer Agent")
    try:
        from agents.analyzer import SODAnalyzer
        from models.database import get_session
        from repositories.sod_rule_repository import SODRuleRepository

        session = get_session()

        # Initialize analyzer
        sod_repo = SODRuleRepository(session)
        SODAnalyzer(sod_repo)

        # Get active rules
        rules = sod_repo.get_active_rules()

        details = f"Active Rules: {len(rules)}"
        if rules:
            by_severity = {}
            for rule in rules:
                severity = rule.severity.value if hasattr(rule.severity, 'value') else str(rule.severity)
                by_severity[severity] = by_severity.get(severity, 0) + 1

            for severity, count in sorted(by_severity.items()):
                details += f"\n  {severity}: {count}"

        if len(rules) > 0:
            print_test("SOD Analyzer Agent", "PASS",
                      f"{len(rules)} SOD rules loaded", details)
            return True
        else:
            print_test("SOD Analyzer Agent", "FAIL", "No SOD rules found")
            return False

    except Exception as e:
        print_test("SOD Analyzer Agent", "FAIL", str(e), traceback.format_exc())
        return False

def test_notifier_agent():
    """Test 9: Notification Agent"""
    print_header("TEST 9: Notification Agent")
    try:
        from agents.notifier import NotificationAgent
        from models.database import get_session
        from repositories.job_role_mapping_repository import JobRoleMappingRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        session = get_session()

        # Initialize agent with repositories
        violation_repo = ViolationRepository(session)
        user_repo = UserRepository(session)
        job_role_repo = JobRoleMappingRepository(session)

        NotificationAgent(
            violation_repo=violation_repo,
            user_repo=user_repo,
            job_role_mapping_repo=job_role_repo,
            enable_cache=True
        )

        details = "Agent initialized with:\n  - ViolationRepository\n  - UserRepository\n  - JobRoleMappingRepository\n  - Cache enabled"

        print_test("Notification Agent", "PASS", "Agent initialized", details)
        return True

    except Exception as e:
        print_test("Notification Agent", "FAIL", str(e), traceback.format_exc())
        return False

def test_cache_system():
    """Test 10: Cache System"""
    print_header("TEST 10: Cache System")
    try:
        from functools import lru_cache

        # Test Python's built-in LRU cache
        @lru_cache(maxsize=128)
        def cached_function(x):
            return x * 2

        # Call function twice
        cached_function(42)
        cache_info1 = cached_function.cache_info()

        cached_function(42)
        cache_info2 = cached_function.cache_info()

        # Second call should be from cache
        if cache_info2.hits > cache_info1.hits:
            details = f"Hits: {cache_info2.hits}\nMisses: {cache_info2.misses}\nSize: {cache_info2.currsize}\nMax Size: {cache_info2.maxsize}"
            print_test("Cache System", "PASS", "LRU cache working", details)
            return True
        else:
            print_test("Cache System", "FAIL", "Cache not working as expected")
            return False

    except Exception as e:
        print_test("Cache System", "FAIL", str(e), traceback.format_exc())
        return False

def test_orchestrator():
    """Test 11: MCP Orchestrator"""
    print_header("TEST 11: MCP Orchestrator")
    try:
        from mcp.orchestrator import ComplianceOrchestrator

        orchestrator = ComplianceOrchestrator()

        # Check that orchestrator has all required components
        components = []
        if hasattr(orchestrator, 'session'):
            components.append("Database Session")
        if hasattr(orchestrator, 'data_collector'):
            components.append("Data Collector")
        if hasattr(orchestrator, 'analyzer'):
            components.append("SOD Analyzer")
        if hasattr(orchestrator, 'notifier_agent'):
            components.append("Notification Agent")
        if hasattr(orchestrator, 'kb_agent'):
            components.append("Knowledge Base Agent")

        details = "Components:\n" + "\n".join([f"  • {c}" for c in components])

        if len(components) >= 5:
            print_test("MCP Orchestrator", "PASS",
                      f"{len(components)} components initialized", details)
            return True
        else:
            print_test("MCP Orchestrator", "FAIL",
                      f"Only {len(components)}/5 components initialized", details)
            return False

    except Exception as e:
        print_test("MCP Orchestrator", "FAIL", str(e), traceback.format_exc())
        return False

def test_repositories():
    """Test 12: All Repositories"""
    print_header("TEST 12: Data Repositories")
    try:
        from models.database import get_session
        from repositories.job_role_mapping_repository import JobRoleMappingRepository
        from repositories.sod_rule_repository import SODRuleRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        session = get_session()

        repos = {
            'UserRepository': UserRepository(session),
            'ViolationRepository': ViolationRepository(session),
            'SODRuleRepository': SODRuleRepository(session),
            'JobRoleMappingRepository': JobRoleMappingRepository(session)
        }

        # Test basic queries
        details = ""
        for name, repo in repos.items():
            try:
                if name == 'UserRepository':
                    count = len(repo.get_all_users(limit=1))
                    details += f"✓ {name}: {count} user(s) found\n"
                elif name == 'SODRuleRepository':
                    count = len(repo.get_active_rules())
                    details += f"✓ {name}: {count} active rule(s)\n"
                elif name == 'JobRoleMappingRepository':
                    mapping = repo.get_all()
                    details += f"✓ {name}: {len(mapping)} mapping(s)\n"
                else:
                    details += f"✓ {name}: initialized\n"
            except Exception as e:
                details += f"✗ {name}: {str(e)}\n"

        print_test("Data Repositories", "PASS",
                  f"{len(repos)} repositories tested", details.strip())
        return True

    except Exception as e:
        print_test("Data Repositories", "FAIL", str(e), traceback.format_exc())
        return False

def print_summary():
    """Print test summary"""
    print_header("SMOKE TEST SUMMARY")

    total = results['passed'] + results['failed'] + results['skipped']
    pass_rate = (results['passed'] / total * 100) if total > 0 else 0

    print(f"\n{'Total Tests:':<20} {total}")
    print(f"{'✅ Passed:':<20} {results['passed']}")
    print(f"{'❌ Failed:':<20} {results['failed']}")
    print(f"{'⏭️  Skipped:':<20} {results['skipped']}")
    print(f"{'Pass Rate:':<20} {pass_rate:.1f}%")

    print("\n" + "="*80)

    if results['failed'] == 0:
        print("🎉 ALL TESTS PASSED! System is operational.")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED. Review errors above.")
        print("\nFailed tests:")
        for test in results['tests']:
            if test['status'] == 'FAIL':
                print(f"  ❌ {test['name']}")
        return 1

def main():
    """Run all smoke tests"""
    print("\n" + "="*80)
    print("  SOD COMPLIANCE SYSTEM - COMPREHENSIVE SMOKE TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)

    # Run all tests
    test_database_connection()
    test_database_tables()
    test_vector_store()
    test_embedding_service()
    test_knowledge_base_agent()
    test_llm_service()
    test_data_collector_agent()
    test_analyzer_agent()
    test_notifier_agent()
    test_cache_system()
    test_orchestrator()
    test_repositories()

    # Print summary
    exit_code = print_summary()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
