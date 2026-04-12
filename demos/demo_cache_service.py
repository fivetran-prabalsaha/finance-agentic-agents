#!/usr/bin/env python3
"""
Cache Service Demo - Demonstrates Redis caching for LLM responses

This demo shows:
1. Cache hit/miss scenarios
2. Performance improvements with caching
3. Cache statistics
4. Cache invalidation
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.notifier import NotificationAgent
from models.database_config import DatabaseConfig
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.cache_service import CacheService


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_metric(label: str, value: str, unit: str = ""):
    """Print formatted metric"""
    print(f"   {label:30} {value:>15} {unit}")


def main():
    """Demonstrate cache service functionality"""

    print_header("CACHE SERVICE DEMO")

    # ========================================================================
    # STEP 1: Initialize Cache Service
    # ========================================================================
    print("STEP 1: Initialize Cache Service")
    print("-" * 80)

    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    cache = CacheService(redis_url=redis_url, enabled=True)

    if not cache.enabled:
        print("❌ Redis not available. Start Redis:")
        print("   brew services start redis")
        print("   # OR")
        print("   docker-compose up -d redis")
        return 1

    print("✅ Cache service initialized")
    print(f"   Redis URL: {redis_url}")

    # ========================================================================
    # STEP 2: Test Basic Cache Operations
    # ========================================================================
    print_header("STEP 2: Test Basic Cache Operations")

    # Set a value
    print("Setting cache value...")
    cache.set("test:key1", {"message": "Hello, Cache!"}, ttl=60)
    print("✅ Value set")

    # Get the value
    print("\nGetting cache value...")
    value = cache.get("test:key1")
    print(f"✅ Value retrieved: {value}")

    # Try non-existent key
    print("\nTrying non-existent key...")
    value = cache.get("test:nonexistent")
    print(f"✅ Result: {value} (expected None)")

    # ========================================================================
    # STEP 3: Test AI Analysis Caching
    # ========================================================================
    print_header("STEP 3: Test AI Analysis Caching")

    # Initialize database
    db_config = DatabaseConfig()
    session = db_config.get_session()
    user_repo = UserRepository(session)
    violation_repo = ViolationRepository(session)

    # Initialize notifier with cache enabled
    notifier = NotificationAgent(
        violation_repo=violation_repo,
        user_repo=user_repo,
        enable_cache=True
    )

    # Get a test user with violations
    all_users = user_repo.get_all_users()

    # Find user with violations
    test_user = None
    for user in all_users:
        violations = violation_repo.get_violations_by_user(user.id)
        if violations:
            test_user = user
            break

    if not test_user:
        print("⚠️  No users with violations found. Run analysis first:")
        print("   python3 demos/demo_end_to_end.py")
        return 0
    print(f"Testing with user: {test_user.name}")

    # Get violations
    violations = violation_repo.get_violations_by_user(test_user.id)
    print(f"User has {len(violations)} violations")

    # Get role names
    role_names = [ur.role.role_name for ur in test_user.user_roles]
    print(f"User has {len(role_names)} roles: {', '.join(role_names)}")

    # ========================================================================
    # First call - MISS (generate analysis)
    # ========================================================================
    print("\n" + "-" * 80)
    print("First call (CACHE MISS - will generate analysis)...")
    print("-" * 80)

    start_time = time.time()
    analysis1 = notifier._generate_ai_analysis(test_user, violations[:3], role_names)
    duration1 = time.time() - start_time

    print("\n📝 Analysis generated:")
    print(f"   Length: {len(analysis1)} characters")
    print(f"   Duration: {duration1:.2f} seconds")
    print(f"\n   Preview: {analysis1[:200]}...")

    # ========================================================================
    # Second call - HIT (from cache)
    # ========================================================================
    print("\n" + "-" * 80)
    print("Second call (CACHE HIT - will use cached analysis)...")
    print("-" * 80)

    start_time = time.time()
    analysis2 = notifier._generate_ai_analysis(test_user, violations[:3], role_names)
    duration2 = time.time() - start_time

    print("\n📝 Analysis retrieved:")
    print(f"   Length: {len(analysis2)} characters")
    print(f"   Duration: {duration2:.2f} seconds")
    print(f"   Speedup: {duration1/max(duration2, 0.001):.1f}x faster")

    # Verify they're identical
    if analysis1 == analysis2:
        print("\n✅ Cached analysis matches original")
    else:
        print("\n⚠️  Warning: Analyses differ!")

    # ========================================================================
    # STEP 4: Cache Statistics
    # ========================================================================
    print_header("STEP 4: Cache Statistics")

    stats = cache.get_stats()

    print("Cache Status:")
    print_metric("Status", stats.get('status', 'unknown'))
    print_metric("Redis Version", stats.get('redis_version', 'N/A'))
    print_metric("Memory Used", stats.get('used_memory_human', 'N/A'))
    print_metric("Total Keys", str(stats.get('total_keys', 0)))
    print_metric("Uptime", f"{stats.get('uptime_days', 0)} days")

    print("\nKeys by Type:")
    print_metric("AI Analysis", str(stats.get('ai_analysis_keys', 0)), "keys")
    print_metric("User Violations", str(stats.get('user_violations_keys', 0)), "keys")
    print_metric("Risk Scores", str(stats.get('risk_score_keys', 0)), "keys")

    # ========================================================================
    # STEP 5: Performance Comparison
    # ========================================================================
    print_header("STEP 5: Performance Comparison")

    print("Simulating multiple analysis requests...")
    print("-" * 80)

    # Without cache (estimate based on first call)
    num_requests = 10
    estimated_without_cache = duration1 * num_requests

    # With cache
    start_time = time.time()
    for _i in range(num_requests):
        notifier._generate_ai_analysis(test_user, violations[:3], role_names)
    actual_with_cache = time.time() - start_time

    print("\n📊 Performance Metrics:")
    print_metric("Requests", str(num_requests))
    print_metric("Without cache (estimated)", f"{estimated_without_cache:.2f}", "seconds")
    print_metric("With cache (actual)", f"{actual_with_cache:.2f}", "seconds")
    print_metric("Time saved", f"{estimated_without_cache - actual_with_cache:.2f}", "seconds")
    print_metric("Speedup", f"{estimated_without_cache/max(actual_with_cache, 0.001):.1f}x")

    # Cost savings (assuming $0.50 per analysis)
    cost_per_analysis = 0.50
    cost_without_cache = cost_per_analysis * num_requests
    cost_with_cache = cost_per_analysis * 1  # Only first call costs money
    cost_saved = cost_without_cache - cost_with_cache

    print("\n💰 Cost Savings (estimated):")
    print_metric("Without cache", f"${cost_without_cache:.2f}")
    print_metric("With cache", f"${cost_with_cache:.2f}")
    print_metric("Saved", f"${cost_saved:.2f}")

    # ========================================================================
    # STEP 6: Cache Invalidation
    # ========================================================================
    print_header("STEP 6: Cache Invalidation")

    print("Testing cache invalidation...")
    print(f"Invalidating all cache entries for user: {test_user.name}")

    deleted_count = cache.invalidate_user(str(test_user.id))
    print(f"✅ Deleted {deleted_count} cache entries")

    # Verify cache is cleared
    analysis3 = cache.get_ai_analysis(
        user_id=str(test_user.id),
        violation_ids=[str(v.id) for v in violations[:3]],
        role_names=role_names
    )

    if analysis3 is None:
        print("✅ Cache successfully cleared")
    else:
        print("⚠️  Cache still contains data")

    # ========================================================================
    # STEP 7: Cache Best Practices
    # ========================================================================
    print_header("STEP 7: Cache Best Practices")

    print("📋 Best Practices for Cache Usage:\n")

    print("1. ✅ Use Caching For:")
    print("   • LLM-generated analysis (expensive)")
    print("   • Risk score calculations (complex)")
    print("   • Violation detection results (frequent)")
    print("   • User compliance summaries")

    print("\n2. ❌ Don't Cache:")
    print("   • Real-time data (user status, roles)")
    print("   • Rapidly changing data")
    print("   • One-time operations")
    print("   • User-specific sensitive data (compliance)")

    print("\n3. ⏱️  TTL Recommendations:")
    print("   • AI Analysis: 24 hours (stable)")
    print("   • Violation Detection: 1 hour (may change)")
    print("   • Risk Scores: 1 hour (recalculated often)")
    print("   • User Summaries: 6 hours (moderate change)")

    print("\n4. 🔄 Invalidation Strategy:")
    print("   • Invalidate on user role changes")
    print("   • Invalidate on SOD rule updates")
    print("   • Invalidate on manual remediation")
    print("   • Use pattern matching for bulk invalidation")

    # ========================================================================
    # Summary
    # ========================================================================
    print_header("SUMMARY")

    print("✅ Cache Service Demo Complete!\n")

    print("Key Takeaways:")
    print(f"   • Cache provides {estimated_without_cache/max(actual_with_cache, 0.001):.1f}x speedup for repeated requests")
    print(f"   • Estimated cost savings: ${cost_saved:.2f} for {num_requests} requests")
    print("   • AI analysis is cached for 24 hours")
    print("   • Cache can be invalidated per user or by pattern")

    print("\nNext Steps:")
    print("   • Enable cache in production (REDIS_URL env var)")
    print("   • Monitor cache hit rate")
    print("   • Tune TTL values based on usage patterns")
    print("   • Set up cache alerts for errors")

    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
