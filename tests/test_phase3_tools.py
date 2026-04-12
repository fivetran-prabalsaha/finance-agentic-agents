"""
Integration Tests for Phase 3: Violation Detection and Review Management

Tests the 3 new Phase 3 tools:
- detect_exception_violations
- conduct_exception_review
- get_exceptions_for_review
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.mcp_tools import (
    conduct_exception_review_handler,
    detect_exception_violations_handler,
    get_exceptions_for_review_handler,
    list_approved_exceptions_handler,
    # Also import Phase 2 tools for setup
    record_exception_approval_handler,
)


async def setup_test_exception():
    """Create a test exception for Phase 3 testing"""
    print("\n" + "="*80)
    print("SETUP: Creating test exception")
    print("="*80)

    result = await record_exception_approval_handler(
        user_identifier="abbey.skuse@fivetran.com",
        user_name="Abbey Skuse",
        role_names=["Fivetran - Controller"],
        conflict_count=5,
        critical_conflicts=1,
        risk_score=45.0,
        business_justification="Test exception for Phase 3 validation",
        approved_by="Test Manager",
        approval_authority="Manager",
        job_title="Test Controller",
        department="Finance",
        compensating_controls=[
            {
                "control_name": "Dual Approval",
                "risk_reduction_percentage": 80,
                "estimated_annual_cost": 50000
            }
        ],
        review_frequency="Quarterly"
    )

    print(result)

    # Extract exception code
    if "Exception Code:" in result:
        code_line = [line for line in result.split('\n') if 'Exception Code:' in line][0]
        exception_code = code_line.split('`')[1]
        return exception_code

    return None


async def test_detect_violations():
    """Test automated violation detection"""
    print("\n" + "="*80)
    print("TEST 1: Detect Exception Violations")
    print("="*80)

    result = await detect_exception_violations_handler(
        check_all=True,
        auto_record=False
    )

    print(result)


async def test_get_exceptions_for_review():
    """Test getting exceptions needing review"""
    print("\n" + "="*80)
    print("TEST 2: Get Exceptions For Review")
    print("="*80)

    result = await get_exceptions_for_review_handler(
        include_upcoming=True,
        days_ahead=90  # Look 90 days ahead
    )

    print(result)


async def test_conduct_review(exception_code):
    """Test conducting an exception review"""
    print("\n" + "="*80)
    print("TEST 3: Conduct Exception Review")
    print("="*80)

    if not exception_code:
        print("❌ Skipping - no exception code available")
        return

    result = await conduct_exception_review_handler(
        exception_code=exception_code,
        reviewer_name="Test Reviewer",
        outcome="APPROVED_CONTINUE",
        findings="Exception is functioning as expected. All controls are active and effective.",
        recommendations="Continue with current controls. Schedule next review in 3 months."
    )

    print(result)


async def test_detect_with_auto_record():
    """Test detection with auto-recording enabled"""
    print("\n" + "="*80)
    print("TEST 4: Detect Violations (Auto-Record)")
    print("="*80)

    result = await detect_exception_violations_handler(
        check_all=True,
        auto_record=True
    )

    print(result)


async def main():
    """Run all Phase 3 tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "PHASE 3: VIOLATION DETECTION & REVIEW TEST SUITE" + " "*14 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # Check if we have existing exceptions
        existing = await list_approved_exceptions_handler(status="ACTIVE", limit=1)

        # If no exceptions, create one
        exception_code = None
        if "No exceptions found" in existing:
            print("\nℹ️  No existing exceptions found. Creating test exception...")
            exception_code = await setup_test_exception()
        else:
            # Extract code from existing exception
            if "EXC-" in existing:
                for line in existing.split('\n'):
                    if 'EXC-' in line:
                        # Extract EXC-YYYY-NNN pattern
                        import re
                        match = re.search(r'EXC-\d{4}-\d{3}', line)
                        if match:
                            exception_code = match.group(0)
                            break
            print(f"\nℹ️  Using existing exception: {exception_code}")

        # Test 1: Detect violations
        await test_detect_violations()

        # Test 2: Get exceptions for review
        await test_get_exceptions_for_review()

        # Test 3: Conduct review
        await test_conduct_review(exception_code)

        # Test 4: Detect with auto-record (should find nothing since we just reviewed)
        await test_detect_with_auto_record()

        print("\n" + "="*80)
        print("✅ ALL PHASE 3 TESTS COMPLETED")
        print("="*80)

        print("\n💡 Next Steps:")
        print("• Run detect_exception_violations periodically (daily/weekly)")
        print("• Use get_exceptions_for_review to plan review sessions")
        print("• Conduct reviews for overdue exceptions")
        print("• Monitor effectiveness with get_exception_effectiveness_stats")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
