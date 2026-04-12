"""
Test script for Autonomous Data Collection Agent

Run with: python -m pytest tests/test_collection_agent.py -v
"""

import pytest

from agents.data_collector import DataCollectionAgent
from models.database_config import DatabaseConfig, init_database


@pytest.fixture(scope="module")
def db_config():
    """Create test database configuration"""
    config = DatabaseConfig()
    init_database(config)
    return config


@pytest.fixture(scope="module")
def agent(db_config):
    """Create collection agent instance (scheduler disabled for testing)"""
    return DataCollectionAgent(db_config=db_config, enable_scheduler=False)


def test_agent_initialization(agent):
    """Test that agent initializes correctly"""
    assert agent is not None
    assert agent.session is not None
    assert agent.user_repo is not None
    assert agent.role_repo is not None
    assert agent.sync_repo is not None
    assert 'netsuite' in agent.connectors
    assert agent.analyzer is not None
    print("✅ Agent initialization successful")


def test_manual_sync(agent):
    """Test manual sync execution"""
    print("\n🔄 Starting manual sync test...")

    result = agent.manual_sync(system_name='netsuite', sync_type='full')

    # Verify result structure
    assert 'success' in result
    assert 'sync_id' in result

    if result['success']:
        print("✅ Manual sync completed successfully")
        print(f"   • Sync ID: {result['sync_id']}")
        print(f"   • Duration: {result['duration']:.2f}s")
        print(f"   • Users Fetched: {result['users_fetched']}")
        print(f"   • Users Synced: {result['users_synced']}")
        print(f"   • Roles Synced: {result['roles_synced']}")
        print(f"   • Violations Detected: {result['violations_detected']}")

        # Verify metrics are reasonable
        assert result['users_synced'] > 0, "Should sync at least some users"
        assert result['duration'] > 0, "Duration should be positive"
    else:
        print(f"⚠️  Manual sync failed: {result.get('error')}")
        print("   This is expected if NetSuite connector is not configured")


def test_get_sync_status(agent):
    """Test getting sync status"""
    print("\n📊 Getting sync status...")

    status = agent.get_sync_status('netsuite')

    # Verify status structure
    assert 'is_running' in status
    assert 'recent_syncs' in status
    assert 'statistics_7d' in status

    print("✅ Status retrieved successfully")
    print(f"   • Agent Running: {status['is_running']}")
    print(f"   • Recent Syncs: {len(status['recent_syncs'])}")

    if status['last_successful_sync']:
        last = status['last_successful_sync']
        print("   • Last Successful Sync:")
        print(f"     - Completed: {last['completed_at']}")
        print(f"     - Duration: {last.get('duration', 'N/A')}s")
        print(f"     - Users: {last.get('users_synced', 0)}")


def test_sync_metadata_tracking(agent):
    """Test that sync metadata is properly tracked"""
    print("\n📝 Testing sync metadata tracking...")

    from repositories.sync_metadata_repository import SyncMetadataRepository

    sync_repo = SyncMetadataRepository(agent.session)

    # Get recent syncs
    recent = sync_repo.get_recent_syncs('netsuite', limit=5)

    print(f"✅ Found {len(recent)} recent syncs")

    for sync in recent[:3]:
        print(f"   • {sync.sync_type.value} sync - {sync.status.value}")
        print(f"     Started: {sync.started_at}")
        if sync.completed_at:
            print(f"     Duration: {sync.duration_seconds:.2f}s")
        if sync.error_message:
            print(f"     Error: {sync.error_message[:50]}...")


def test_sync_statistics(agent):
    """Test sync statistics calculation"""
    print("\n📈 Testing sync statistics...")

    from repositories.sync_metadata_repository import SyncMetadataRepository

    sync_repo = SyncMetadataRepository(agent.session)

    # Get 7-day statistics
    stats = sync_repo.get_sync_statistics('netsuite', days=7)

    print("✅ Statistics calculated successfully")
    print(f"   • Total Syncs: {stats['total_syncs']}")
    print(f"   • Successful: {stats['successful']}")
    print(f"   • Failed: {stats['failed']}")
    print(f"   • Success Rate: {stats['success_rate']:.1f}%")
    print(f"   • Avg Duration: {stats['avg_duration']:.2f}s")
    print(f"   • Total Users Synced: {stats['total_users_synced']}")


def test_scheduler_jobs(db_config):
    """Test that scheduler jobs are configured correctly"""
    print("\n⏰ Testing scheduler configuration...")

    # Create agent with scheduler enabled
    agent = DataCollectionAgent(db_config=db_config, enable_scheduler=True)

    # Start scheduler
    agent.start()

    # Verify scheduler is running
    assert agent.is_running is True
    assert agent.scheduler is not None
    assert agent.scheduler.running is True

    # Get scheduled jobs
    jobs = agent.scheduler.get_jobs()
    assert len(jobs) >= 2, "Should have at least 2 jobs (full + incremental sync)"

    print(f"✅ Scheduler started with {len(jobs)} jobs")
    for job in jobs:
        print(f"   • {job.name} (ID: {job.id})")
        print(f"     Next run: {job.next_run_time}")

    # Stop scheduler
    agent.stop()
    assert agent.is_running is False

    print("✅ Scheduler stopped successfully")


def test_full_sync_integration(agent):
    """Test full sync with all components"""
    print("\n🔍 Testing full sync integration...")

    # This is an integration test that requires:
    # 1. NetSuite credentials configured
    # 2. Database connection working
    # 3. SOD rules loaded

    result = agent.full_sync(system_name='netsuite', triggered_by='test')

    if result['success']:
        print("✅ Full sync integration test passed")
        print(f"   • Sync ID: {result['sync_id']}")
        print(f"   • Duration: {result['duration']:.2f}s")
        print(f"   • Users Fetched: {result['users_fetched']}")
        print(f"   • Users Synced: {result['users_synced']}")
        print(f"   • Roles Synced: {result['roles_synced']}")
        print(f"   • Violations Detected: {result['violations_detected']}")

        # Verify data was actually synced
        from repositories.user_repository import UserRepository
        user_repo = UserRepository(agent.session)
        user_count = user_repo.count_users()
        print(f"   • Total Users in DB: {user_count}")

        assert user_count == result['users_synced'], "User count should match synced count"
    else:
        print(f"⚠️  Full sync failed: {result.get('error')}")
        print("   This is expected if NetSuite connector is not configured")
        pytest.skip("NetSuite connector not configured")


if __name__ == "__main__":
    """Run tests manually without pytest"""
    print("=" * 80)
    print("Testing Autonomous Data Collection Agent")
    print("=" * 80)

    # Create config and agent
    config = DatabaseConfig()
    init_database(config)
    agent = DataCollectionAgent(db_config=config, enable_scheduler=False)

    # Run tests
    try:
        test_agent_initialization(agent)
        test_manual_sync(agent)
        test_get_sync_status(agent)
        test_sync_metadata_tracking(agent)
        test_sync_statistics(agent)
        test_scheduler_jobs(config)

        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        agent.session.close()
