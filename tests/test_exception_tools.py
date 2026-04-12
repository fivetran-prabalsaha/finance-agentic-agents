"""
Integration Tests for Exception Management MCP Tools

Tests the 6 new exception management tools added in Phase 2:
- record_exception_approval
- find_similar_exceptions
- get_exception_details
- list_approved_exceptions
- record_exception_violation
- get_exception_effectiveness_stats
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.mcp_tools import (
    find_similar_exceptions_handler,
    get_exception_details_handler,
    get_exception_effectiveness_stats_handler,
    list_approved_exceptions_handler,
    record_exception_approval_handler,
    record_exception_violation_handler,
)


async def test_record_exception_approval():
    """Test recording a new exception approval"""
    print("\n" + "="*80)
    print("TEST 1: Record Exception Approval")
    print("="*80)

    result = await record_exception_approval_handler(
        user_identifier="abbey.skuse@fivetran.com",
        user_name="Abbey Skuse",
        role_names=["Fivetran - Controller", "Fivetran - AP Manager"],
        conflict_count=12,
        critical_conflicts=3,
        risk_score=72.5,
        business_justification="CFO vacation coverage - temporary 90 days",
        approved_by="Jane Smith",
        approval_authority="CFO",
        job_title="Controller",
        department="Finance",
        compensating_controls=[
            {
                "control_name": "Dual Approval Workflow",
                "risk_reduction_percentage": 80,
                "estimated_annual_cost": 100000
            },
            {
                "control_name": "Enhanced Audit Review",
                "risk_reduction_percentage": 60,
                "estimated_annual_cost": 75000
            }
        ],
        review_frequency="Quarterly",
        expiration_days=90
    )

    print(result)

    # Extract exception code for next tests
    if "Exception Code:" in result:
        code_line = [line for line in result.split('\n') if 'Exception Code:' in line][0]
        exception_code = code_line.split('`')[1]
        return exception_code

    return None


async def test_find_similar_exceptions():
    """Test finding similar exceptions"""
    print("\n" + "="*80)
    print("TEST 2: Find Similar Exceptions")
    print("="*80)

    result = await find_similar_exceptions_handler(
        role_names=["Fivetran - Controller", "Fivetran - AP Manager"],
        job_title="Controller",
        department="Finance",
        limit=3
    )

    print(result)


async def test_get_exception_details(exception_code):
    """Test getting exception details"""
    print("\n" + "="*80)
    print("TEST 3: Get Exception Details")
    print("="*80)

    if not exception_code:
        print("❌ Skipping - no exception code available")
        return

    result = await get_exception_details_handler(
        exception_code=exception_code
    )

    print(result)


async def test_list_approved_exceptions():
    """Test listing exceptions"""
    print("\n" + "="*80)
    print("TEST 4: List Approved Exceptions")
    print("="*80)

    result = await list_approved_exceptions_handler(
        status="ACTIVE",
        limit=5
    )

    print(result)


async def test_record_violation(exception_code):
    """Test recording an exception violation"""
    print("\n" + "="*80)
    print("TEST 5: Record Exception Violation")
    print("="*80)

    if not exception_code:
        print("❌ Skipping - no exception code available")
        return

    result = await record_exception_violation_handler(
        exception_code=exception_code,
        violation_type="Unauthorized Transaction",
        severity="HIGH",
        description="User approved $50K invoice without dual approval",
        failed_control_name="Dual Approval Workflow",
        failure_reason="Workflow bypassed using emergency override",
        detected_by="Automated Monitoring System",
        detection_method="Real-time transaction monitoring"
    )

    print(result)


async def test_effectiveness_stats():
    """Test getting effectiveness statistics"""
    print("\n" + "="*80)
    print("TEST 6: Get Exception Effectiveness Stats")
    print("="*80)

    result = await get_exception_effectiveness_stats_handler()

    print(result)


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "EXCEPTION MANAGEMENT TOOLS TEST SUITE" + " "*21 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # Test 1: Record exception
        exception_code = await test_record_exception_approval()

        # Test 2: Find similar exceptions
        await test_find_similar_exceptions()

        # Test 3: Get exception details
        await test_get_exception_details(exception_code)

        # Test 4: List exceptions
        await test_list_approved_exceptions()

        # Test 5: Record violation
        await test_record_violation(exception_code)

        # Test 6: Effectiveness stats
        await test_effectiveness_stats()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)

        print("\n💡 Next Steps:")
        print("• Review the output above to verify all tools work correctly")
        print("• Test the tools via Claude Desktop integration")
        print("• Test the enhanced analyze_access_request with precedent search")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
