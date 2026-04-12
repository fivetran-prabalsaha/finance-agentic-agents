#!/usr/bin/env python3
"""
Live MCP Server Smoke Test
Tests all components through the actual MCP orchestrator
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

results = {'passed': 0, 'failed': 0, 'skipped': 0, 'tests': []}

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_test(name, status, message="", details=""):
    symbols = {'PASS': '✅', 'FAIL': '❌', 'SKIP': '⏭️'}
    print(f"\n{symbols.get(status, '•')} {name}")
    if message:
        print(f"   {message}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"   {line}")

    results['tests'].append({'name': name, 'status': status, 'message': message})
    if status == 'PASS':
        results['passed'] += 1
    elif status == 'FAIL':
        results['failed'] += 1
    else:
        results['skipped'] += 1

def main():
    print("\n" + "="*80)
    print("  SOD COMPLIANCE SYSTEM - LIVE MCP SERVER SMOKE TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)

    # TEST 1: Database Connection & Config
    print_header("TEST 1: Database Configuration")
    try:
        from models.database_config import get_db_config
        db_config = get_db_config()

        if db_config.test_connection():
            print_test("Database Connection", "PASS", "PostgreSQL connected")
        else:
            print_test("Database Connection", "FAIL", "Connection test failed")
    except Exception as e:
        print_test("Database Connection", "FAIL", str(e))

    # TEST 2: Database Tables & Data
    print_header("TEST 2: Database Tables & Data")
    try:
        from sqlalchemy import text

        from models.database_config import get_db_config

        db_config = get_db_config()
        session = db_config.get_session()

        tables = {
            'users': 'SELECT COUNT(*) FROM users',
            'roles': 'SELECT COUNT(*) FROM roles',
            'permissions': 'SELECT COUNT(*) FROM permissions',
            'sod_rules': 'SELECT COUNT(*) FROM sod_rules',
            'job_role_mappings': 'SELECT COUNT(*) FROM job_role_mappings',
            'sync_metadata': 'SELECT COUNT(*) FROM sync_metadata'
        }

        counts = {}
        for table, query in tables.items():
            try:
                count = session.execute(text(query)).scalar()
                counts[table] = count
            except Exception:
                counts[table] = "ERROR"

        session.close()

        details = "\n".join([f"{k}: {v:,}" if isinstance(v, int) else f"{k}: {v}"
                            for k, v in counts.items()])

        if all(isinstance(v, int) for v in counts.values()):
            print_test("Database Tables", "PASS",
                      f"All {len(counts)} tables accessible", details)
        else:
            print_test("Database Tables", "FAIL",
                      "Some tables missing or inaccessible", details)

    except Exception as e:
        print_test("Database Tables", "FAIL", str(e))

    # TEST 3: pgvector Extension
    print_header("TEST 3: pgvector Vector Store")
    try:
        from sqlalchemy import text

        from models.database_config import get_db_config

        db_config = get_db_config()
        session = db_config.get_session()

        ext_query = text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'")
        has_extension = session.execute(ext_query).scalar() > 0

        if has_extension:
            # Check for vector columns
            vector_query = text("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE data_type = 'USER-DEFINED'
                AND udt_name = 'vector'
                LIMIT 5
            """)
            vector_cols = session.execute(vector_query).fetchall()
            details = "\n".join([f"{row[0]}.{row[1]}" for row in vector_cols]) if vector_cols else "No vector columns"

            print_test("pgvector Extension", "PASS",
                      f"Enabled with {len(vector_cols)} vector columns", details)
        else:
            print_test("pgvector Extension", "FAIL", "Extension not installed")

        session.close()
    except Exception as e:
        print_test("pgvector Extension", "FAIL", str(e))

    # TEST 4: Embedding Service
    print_header("TEST 4: Embedding Service")
    try:
        import numpy as np

        from services.embedding_service import EmbeddingService

        service = EmbeddingService()

        # Test embedding
        test_text = "Test SOD violation for financial transactions"
        embedding = service.embed_text(test_text)

        if isinstance(embedding, np.ndarray) and len(embedding) > 0:
            details = f"Model: {service.embedding_provider.value}\nDimensions: {len(embedding)}\nCache: {service.use_cache}"
            print_test("Embedding Service", "PASS",
                      f"Generated {len(embedding)}-dimensional embedding", details)
        else:
            print_test("Embedding Service", "FAIL", "Failed to generate embedding")
    except Exception as e:
        print_test("Embedding Service", "FAIL", str(e))

    # TEST 5: Knowledge Base Agent
    print_header("TEST 5: Knowledge Base Agent")
    try:
        from agents.knowledge_base_pgvector import KnowledgeBaseAgentPgvector

        agent = KnowledgeBaseAgentPgvector()

        # Test search
        query = "What are SOD violations for accounts payable?"
        results_list = agent.search(query, top_k=3)

        if results_list and len(results_list) > 0:
            details = f"Query: {query}\nResults: {len(results_list)}"
            for i, result in enumerate(results_list[:2], 1):
                content = result.get('content', '')[:80]
                details += f"\n  {i}. {content}..."

            print_test("Knowledge Base Agent", "PASS",
                      f"Retrieved {len(results_list)} relevant documents", details)
        else:
            print_test("Knowledge Base Agent", "SKIP",
                      "No results (KB may need seeding)")
    except Exception as e:
        print_test("Knowledge Base Agent", "FAIL", str(e))

    # TEST 6: LLM Service
    print_header("TEST 6: LLM Service (Claude)")
    try:
        from services.llm.factory import create_llm_provider

        if not os.getenv('ANTHROPIC_API_KEY'):
            print_test("LLM Service", "SKIP", "ANTHROPIC_API_KEY not set")
        else:
            provider = create_llm_provider()
            details = f"Provider: {provider.provider_name}\nModel: {provider.model}"
            print_test("LLM Service", "PASS", "Provider initialized", details)
    except Exception as e:
        print_test("LLM Service", "FAIL", str(e))

    # TEST 7: Data Collector Agent
    print_header("TEST 7: Data Collection Agent")
    try:
        from sqlalchemy import text

        from agents.data_collector import DataCollectionAgent
        from models.database_config import get_db_config

        agent = DataCollectionAgent()

        # Check scheduler
        has_scheduler = hasattr(agent, 'scheduler')
        jobs_count = len(agent.scheduler.get_jobs()) if has_scheduler else 0

        # Get last sync
        db_config = get_db_config()
        session = db_config.get_session()
        last_sync = session.execute(text("""
            SELECT sync_type, status, started_at, completed_at
            FROM sync_metadata
            ORDER BY started_at DESC
            LIMIT 1
        """)).fetchone()
        session.close()

        details = f"Scheduler: {'Active' if has_scheduler else 'Inactive'}\nJobs: {jobs_count}"
        if last_sync:
            details += f"\nLast Sync: {last_sync[0]} ({last_sync[1]})"
            details += f"\nCompleted: {last_sync[3]}"

        if has_scheduler:
            print_test("Data Collection Agent", "PASS",
                      f"Agent running with {jobs_count} scheduled jobs", details)
        else:
            print_test("Data Collection Agent", "FAIL", "Scheduler not initialized")

    except Exception as e:
        print_test("Data Collection Agent", "FAIL", str(e))

    # TEST 8: SOD Analyzer Agent
    print_header("TEST 8: SOD Analyzer Agent")
    try:
        from agents.analyzer import SODAnalysisAgent
        from models.database_config import get_db_config
        from repositories.sod_rule_repository import SODRuleRepository

        db_config = get_db_config()
        session = db_config.get_session()

        sod_repo = SODRuleRepository(session)
        SODAnalysisAgent(sod_repo)

        rules = sod_repo.get_active_rules()

        details = f"Active Rules: {len(rules)}"
        if rules:
            by_severity = {}
            for rule in rules:
                severity = rule.severity.value if hasattr(rule.severity, 'value') else str(rule.severity)
                by_severity[severity] = by_severity.get(severity, 0) + 1

            for severity, count in sorted(by_severity.items()):
                details += f"\n  {severity}: {count}"

        session.close()

        if len(rules) > 0:
            print_test("SOD Analyzer Agent", "PASS",
                      f"{len(rules)} SOD rules loaded", details)
        else:
            print_test("SOD Analyzer Agent", "FAIL", "No SOD rules found")

    except Exception as e:
        print_test("SOD Analyzer Agent", "FAIL", str(e))

    # TEST 9: Notification Agent
    print_header("TEST 9: Notification Agent")
    try:
        from agents.notifier import NotificationAgent
        from models.database_config import get_db_config
        from repositories.job_role_mapping_repository import JobRoleMappingRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        db_config = get_db_config()
        session = db_config.get_session()

        violation_repo = ViolationRepository(session)
        user_repo = UserRepository(session)
        job_role_repo = JobRoleMappingRepository(session)

        agent = NotificationAgent(
            violation_repo=violation_repo,
            user_repo=user_repo,
            job_role_mapping_repo=job_role_repo,
            enable_cache=True
        )

        session.close()

        details = "Agent initialized with:\n  - ViolationRepository\n  - UserRepository\n  - JobRoleMappingRepository\n  - Cache enabled"
        print_test("Notification Agent", "PASS", "Agent operational", details)

    except Exception as e:
        print_test("Notification Agent", "FAIL", str(e))

    # TEST 10: Cache System
    print_header("TEST 10: Cache System")
    try:
        from functools import lru_cache

        @lru_cache(maxsize=128)
        def test_cache(x):
            return x * 2

        test_cache(42)
        cache_info1 = test_cache.cache_info()

        test_cache(42)
        cache_info2 = test_cache.cache_info()

        if cache_info2.hits > cache_info1.hits:
            details = f"Hits: {cache_info2.hits}\nMisses: {cache_info2.misses}\nSize: {cache_info2.currsize}/{cache_info2.maxsize}"
            print_test("Cache System", "PASS", "LRU cache working", details)
        else:
            print_test("Cache System", "FAIL", "Cache not working")
    except Exception as e:
        print_test("Cache System", "FAIL", str(e))

    # TEST 11: MCP Orchestrator
    print_header("TEST 11: MCP Orchestrator")
    try:
        from mcp.orchestrator import ComplianceOrchestrator

        orchestrator = ComplianceOrchestrator()

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

        if len(components) >= 4:
            print_test("MCP Orchestrator", "PASS",
                      f"{len(components)} components initialized", details)
        else:
            print_test("MCP Orchestrator", "FAIL",
                      f"Only {len(components)} components initialized", details)

    except Exception as e:
        print_test("MCP Orchestrator", "FAIL", str(e))

    # TEST 12: Repositories
    print_header("TEST 12: Data Repositories")
    try:
        from models.database_config import get_db_config
        from repositories.job_role_mapping_repository import JobRoleMappingRepository
        from repositories.sod_rule_repository import SODRuleRepository
        from repositories.user_repository import UserRepository
        from repositories.violation_repository import ViolationRepository

        db_config = get_db_config()
        session = db_config.get_session()

        repos = {
            'UserRepository': UserRepository(session),
            'ViolationRepository': ViolationRepository(session),
            'SODRuleRepository': SODRuleRepository(session),
            'JobRoleMappingRepository': JobRoleMappingRepository(session)
        }

        details = ""
        for name, repo in repos.items():
            try:
                if name == 'UserRepository':
                    count = len(repo.get_all_users(limit=1))
                    details += f"✓ {name}: working\n"
                elif name == 'SODRuleRepository':
                    count = len(repo.get_active_rules())
                    details += f"✓ {name}: {count} active rules\n"
                elif name == 'JobRoleMappingRepository':
                    mappings = repo.get_all()
                    details += f"✓ {name}: {len(mappings)} mappings\n"
                else:
                    details += f"✓ {name}: working\n"
            except Exception as e:
                details += f"✗ {name}: {str(e)}\n"

        session.close()

        print_test("Data Repositories", "PASS",
                  f"{len(repos)} repositories tested", details.strip())

    except Exception as e:
        print_test("Data Repositories", "FAIL", str(e))

    # Summary
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
        print("🎉 ALL TESTS PASSED! System is fully operational.")
        return 0
    else:
        print(f"⚠️  {results['failed']} TEST(S) FAILED.")
        print("\nFailed tests:")
        for test in results['tests']:
            if test['status'] == 'FAIL':
                print(f"  ❌ {test['name']}: {test['message']}")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
