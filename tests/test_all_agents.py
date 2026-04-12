#!/usr/bin/env python3
"""
Comprehensive Test Suite for All Agents

Tests each agent individually to verify functionality:
1. Data Collector Agent
2. Analyzer Agent
3. Risk Assessor Agent
4. Knowledge Base Agent
5. Notification Agent
6. Orchestrator Agent
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ['DATABASE_URL'] = 'postgresql://compliance_user:compliance_pass@localhost:5432/compliance_db'

from agents.analyzer import create_analyzer
from agents.data_collector import DataCollectionAgent
from agents.knowledge_base import create_knowledge_base
from agents.notifier import create_notifier
from agents.orchestrator import create_orchestrator
from agents.risk_assessor import create_risk_assessor
from models.database_config import DatabaseConfig
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.netsuite_client import NetSuiteClient


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_test(test_name, passed):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"   {status}: {test_name}")

def test_data_collector():
    """Test Agent 1: Data Collector"""
    print_header("TEST 1: DATA COLLECTOR AGENT")

    test_results = {
        'initialization': False,
        'user_search': False,
        'data_quality': False,
        'role_count': False
    }

    try:
        # Test initialization
        netsuite_client = NetSuiteClient()
        DataCollectionAgent(netsuite_client=netsuite_client)
        test_results['initialization'] = True
        print("✅ Agent initialized")

        # Test user search (via NetSuite client)
        print("\n🔍 Testing user search...")
        result = netsuite_client.search_users(
            search_value='prabal.saha@fivetran.com',
            search_type='email'
        )

        if result['success'] and result['data']['users']:
            test_results['user_search'] = True
            users = result['data']['users']
            print(f"✅ Found {len(users)} user(s)")

            # Test data quality
            user = users[0]
            required_fields = ['user_id', 'email', 'name', 'roles']
            if all(field in user for field in required_fields):
                test_results['data_quality'] = True
                print("✅ All required fields present")

            # Test job function field
            if 'job_function' in user:
                print(f"✅ Job function field: {user['job_function']}")

            # Test roles
            if user.get('roles') and len(user['roles']) > 0:
                test_results['role_count'] = True
                print(f"✅ Roles loaded: {len(user['roles'])} roles")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Data Collector Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def test_analyzer():
    """Test Agent 2: Analyzer"""
    print_header("TEST 2: ANALYZER AGENT")

    test_results = {
        'initialization': False,
        'rules_loaded': False,
        'analysis_execution': False,
        'context_aware': False,
        'violation_storage': False
    }

    try:
        # Initialize
        db_config = DatabaseConfig()
        session = db_config.get_session()

        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)
        sod_rule_repo = SODRuleRepository(session)

        # Test initialization
        analyzer = create_analyzer(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo,
            sod_rule_repo=sod_rule_repo
        )
        test_results['initialization'] = True
        print("✅ Agent initialized")

        # Test rules loaded
        if len(analyzer.sod_rules) > 0:
            test_results['rules_loaded'] = True
            print(f"✅ SOD rules loaded: {len(analyzer.sod_rules)} rules")

        # Test analysis execution
        print("\n🔍 Testing SOD analysis...")
        result = analyzer.analyze_all_users()

        if result['success']:
            test_results['analysis_execution'] = True
            stats = result['stats']
            print("✅ Analysis completed")
            print(f"   Users analyzed: {stats['users_analyzed']}")
            print(f"   Violations: {stats['violations_detected']}")

        # Test context-aware logic
        print("\n🔍 Testing context-aware exemptions...")
        prabal = user_repo.get_user_by_email('prabal.saha@fivetran.com')
        if prabal:
            is_it_user = analyzer._is_it_systems_user(prabal)
            if is_it_user and prabal.job_function == 'IT/SYSTEMS_ENGINEERING':
                test_results['context_aware'] = True
                print("✅ Context-aware logic working")
                print(f"   Job Function: {prabal.job_function}")
                print(f"   Is IT User: {is_it_user}")

        # Test violation storage
        if result.get('violations') and len(result['violations']) > 0:
            test_results['violation_storage'] = True
            print(f"✅ Violations stored: {len(result['violations'])} violations")

        session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Analyzer Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def test_risk_assessor():
    """Test Agent 3: Risk Assessor"""
    print_header("TEST 3: RISK ASSESSOR AGENT")

    test_results = {
        'initialization': False,
        'user_risk_calculation': False,
        'org_risk_assessment': False,
        'risk_distribution': False
    }

    try:
        # Initialize
        db_config = DatabaseConfig()
        session = db_config.get_session()

        violation_repo = ViolationRepository(session)
        user_repo = UserRepository(session)

        # Test initialization
        risk_assessor = create_risk_assessor(
            violation_repo=violation_repo,
            user_repo=user_repo
        )
        test_results['initialization'] = True
        print("✅ Agent initialized")

        # Test user risk calculation
        print("\n🔍 Testing user risk calculation...")
        prabal = user_repo.get_user_by_email('prabal.saha@fivetran.com')
        if prabal:
            # Calculate risk score (accepts both UUID and NetSuite ID)
            risk_result = risk_assessor.calculate_user_risk_score(str(prabal.id))
            if risk_result['success']:
                test_results['user_risk_calculation'] = True
                print(f"✅ User risk calculated: {risk_result['risk_score']}/100")
                print(f"   Risk Level: {risk_result['risk_level']}")
            else:
                print(f"⚠️  Risk calculation returned: {risk_result.get('error', 'Unknown error')}")

        # Test organization risk assessment
        print("\n🔍 Testing organization risk assessment...")
        org_result = risk_assessor.assess_organization_risk()

        if org_result['success']:
            test_results['org_risk_assessment'] = True
            print("✅ Organization risk assessed")
            print(f"   Risk Level: {org_result['organization_risk_level']}")
            print(f"   Risk Score: {org_result['organization_risk_score']}/100")

        # Test risk distribution
        if 'risk_distribution' in org_result:
            test_results['risk_distribution'] = True
            dist = org_result['risk_distribution']
            print("✅ Risk distribution calculated")
            print(f"   Critical: {dist.get('CRITICAL', 0)} users")
            print(f"   High: {dist.get('HIGH', 0)} users")
            print(f"   Medium: {dist.get('MEDIUM', 0)} users")

        session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Risk Assessor Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def test_knowledge_base():
    """Test Agent 4: Knowledge Base"""
    print_header("TEST 4: KNOWLEDGE BASE AGENT")

    test_results = {
        'initialization': False,
        'embeddings_created': False,
        'semantic_search': False,
        'rule_retrieval': False
    }

    try:
        # Initialize
        db_config = DatabaseConfig()
        session = db_config.get_session()
        role_repo = RoleRepository(session)

        # Test initialization
        print("🔍 Initializing Knowledge Base...")
        kb_agent = create_knowledge_base(role_repo=role_repo)
        test_results['initialization'] = True
        print("✅ Agent initialized")

        # Test embeddings
        if len(kb_agent.sod_rules) > 0 and hasattr(kb_agent, 'embeddings'):
            test_results['embeddings_created'] = True
            print(f"✅ Embeddings created for {len(kb_agent.sod_rules)} rules")

        # Test semantic search
        print("\n🔍 Testing semantic search...")
        query = "financial approval conflicts"
        results = kb_agent.search_similar_rules(query, top_k=3)

        if results:
            test_results['semantic_search'] = True
            print(f"✅ Semantic search working: {len(results)} results")
            for i, result in enumerate(results[:2], 1):
                rule_name = result['rule'].get('rule_name', result['rule_id'])
                print(f"   {i}. {rule_name} (similarity: {result['similarity']:.2f})")

        # Test rule retrieval
        print("\n🔍 Testing rule retrieval...")
        financial_rules = kb_agent.get_rules_by_type('FINANCIAL')
        if financial_rules:
            test_results['rule_retrieval'] = True
            print(f"✅ Rule retrieval working: {len(financial_rules)} financial rules")

        session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Knowledge Base Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def test_notifier():
    """Test Agent 5: Notification Agent"""
    print_header("TEST 5: NOTIFICATION AGENT")

    test_results = {
        'initialization': False,
        'comparison_table': False,
        'notification_formatting': False
    }

    try:
        # Initialize
        db_config = DatabaseConfig()
        session = db_config.get_session()

        violation_repo = ViolationRepository(session)
        user_repo = UserRepository(session)

        # Test initialization
        notifier = create_notifier(
            violation_repo=violation_repo,
            user_repo=user_repo
        )
        test_results['initialization'] = True
        print("✅ Agent initialized")
        print(f"   Email: {'Enabled' if notifier.email_enabled else 'Disabled'}")
        print(f"   Slack: {'Enabled' if notifier.slack_enabled else 'Disabled'}")

        # Test comparison table
        print("\n🔍 Testing user comparison table...")
        target_emails = ['prabal.saha@fivetran.com', 'robin.turner@fivetran.com']
        comparison_table = notifier.generate_user_comparison_table(
            user_emails=target_emails,
            include_border=True
        )

        if comparison_table and len(comparison_table) > 100:
            test_results['comparison_table'] = True
            print("✅ Comparison table generated")
            print(f"   Table size: {len(comparison_table)} characters")

        # Test notification formatting
        print("\n🔍 Testing notification formatting...")
        from models.database import ViolationSeverity
        violations = violation_repo.get_open_violations(
            severity=ViolationSeverity.CRITICAL,
            limit=1
        )

        if violations:
            test_results['notification_formatting'] = True
            v = violations[0]
            print("✅ Notification formatting working")
            print(f"   Sample: {v.title[:50]}...")

        session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Notification Agent Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def test_orchestrator():
    """Test Agent 6: Orchestrator"""
    print_header("TEST 6: ORCHESTRATOR AGENT")

    test_results = {
        'initialization': False,
        'workflow_definition': False,
        'agent_coordination': False
    }

    try:
        # Initialize
        netsuite_client = NetSuiteClient()
        db_config = DatabaseConfig()
        session = db_config.get_session()

        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        violation_repo = ViolationRepository(session)
        sod_rule_repo = SODRuleRepository(session)

        # Test initialization
        orchestrator = create_orchestrator(
            netsuite_client=netsuite_client,
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo,
            sod_rule_repo=sod_rule_repo
        )
        test_results['initialization'] = True
        print("✅ Agent initialized")

        # Test workflow definition
        if hasattr(orchestrator, 'workflow') or hasattr(orchestrator, 'data_collector'):
            test_results['workflow_definition'] = True
            print("✅ Workflow defined")
            print("   Agents configured:")
            print("      - Data Collector")
            print("      - Analyzer")
            print("      - Risk Assessor")
            print("      - Notifier")

        # Test agent coordination
        if (hasattr(orchestrator, 'analyzer') and
            hasattr(orchestrator, 'risk_assessor')):
            test_results['agent_coordination'] = True
            print("✅ Agent coordination configured")

        session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n📊 Orchestrator Test Results:")
    for test_name, passed in test_results.items():
        print_test(test_name, passed)

    return all(test_results.values())

def main():
    print("="*80)
    print("  COMPREHENSIVE AGENT TEST SUITE")
    print("="*80)
    print("\nTesting all 6 agents individually...\n")

    # Track results
    all_results = {}

    # Test each agent
    try:
        all_results['Data Collector'] = test_data_collector()
    except Exception as e:
        print(f"❌ Data Collector test failed: {str(e)}")
        all_results['Data Collector'] = False

    try:
        all_results['Analyzer'] = test_analyzer()
    except Exception as e:
        print(f"❌ Analyzer test failed: {str(e)}")
        all_results['Analyzer'] = False

    try:
        all_results['Risk Assessor'] = test_risk_assessor()
    except Exception as e:
        print(f"❌ Risk Assessor test failed: {str(e)}")
        all_results['Risk Assessor'] = False

    try:
        all_results['Knowledge Base'] = test_knowledge_base()
    except Exception as e:
        print(f"❌ Knowledge Base test failed: {str(e)}")
        all_results['Knowledge Base'] = False

    try:
        all_results['Notifier'] = test_notifier()
    except Exception as e:
        print(f"❌ Notifier test failed: {str(e)}")
        all_results['Notifier'] = False

    try:
        all_results['Orchestrator'] = test_orchestrator()
    except Exception as e:
        print(f"❌ Orchestrator test failed: {str(e)}")
        all_results['Orchestrator'] = False

    # Final summary
    print("\n" + "="*80)
    print("  FINAL TEST SUMMARY")
    print("="*80)

    passed_count = sum(1 for passed in all_results.values() if passed)
    total_count = len(all_results)

    for agent_name, passed in all_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {agent_name}")

    print("\n" + "="*80)
    print(f"📊 Overall Results: {passed_count}/{total_count} agents passed")

    if passed_count == total_count:
        print("🎉 ALL AGENTS WORKING CORRECTLY!")
    else:
        print(f"⚠️  {total_count - passed_count} agent(s) need attention")

    print("="*80)

    return passed_count == total_count

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
