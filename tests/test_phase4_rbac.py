"""
Integration Tests for Phase 4: RBAC and Approval Workflows

Tests the 2 new Phase 4 tools:
- check_my_approval_authority
- request_exception_approval
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.mcp_tools import check_my_approval_authority_handler, request_exception_approval_handler


async def test_check_authority_cfo():
    """Test authority check for CFO role"""
    print("\n" + "="*80)
    print("TEST 1: Check Authority - CFO User")
    print("="*80)

    result = await check_my_approval_authority_handler(
        my_email="kalor@fivetran.com",  # Real CFO user
        check_for_risk_score=85.0  # CRITICAL level
    )

    print(result)


async def test_check_authority_controller():
    """Test authority check for Controller role"""
    print("\n" + "="*80)
    print("TEST 2: Check Authority - Controller User")
    print("="*80)

    result = await check_my_approval_authority_handler(
        my_email="robin.turner@fivetran.com",  # Real Controller user
        check_for_risk_score=65.0  # HIGH level
    )

    print(result)


async def test_check_authority_no_score():
    """Test authority check without specific risk score"""
    print("\n" + "="*80)
    print("TEST 3: Check Authority - General (No Risk Score)")
    print("="*80)

    result = await check_my_approval_authority_handler(
        my_email="robin.turner@fivetran.com"  # Real Controller user
    )

    print(result)


async def test_approval_request_authorized():
    """Test approval request from authorized user (auto-approve)"""
    print("\n" + "="*80)
    print("TEST 4: Request Approval - Authorized User (Auto-Approve)")
    print("="*80)

    result = await request_exception_approval_handler(
        requester_email="robin.turner@fivetran.com",  # Controller - can approve HIGH
        user_identifier="test.user@fivetran.com",
        user_name="Test User",
        role_names=["Fivetran - Tax Manager", "Fivetran - Controller"],
        conflict_count=5,
        critical_conflicts=1,
        risk_score=55.0,  # HIGH level - Controller can approve
        business_justification="Test exception for Phase 4 RBAC validation",
        job_title="Tax Manager",
        department="Finance",
        compensating_controls=[
            {
                "control_name": "Dual Approval Workflow",
                "risk_reduction_percentage": 80,
                "estimated_annual_cost": 50000
            }
        ],
        review_frequency="Quarterly",
        auto_approve_if_authorized=True  # Automatically approve if authorized
    )

    print(result)


async def test_approval_request_unauthorized():
    """Test approval request from unauthorized user (escalation)"""
    print("\n" + "="*80)
    print("TEST 5: Request Approval - Unauthorized User (Escalation)")
    print("="*80)

    result = await request_exception_approval_handler(
        requester_email="hanz.lizardo@fivetran.com",  # Billing Manager - cannot approve CRITICAL
        user_identifier="another.user@fivetran.com",
        user_name="Another User",
        role_names=["Fivetran - Revenue Recognition Manager", "Fivetran - AR Processing"],
        conflict_count=8,
        critical_conflicts=2,
        risk_score=78.0,  # CRITICAL level - Requires CFO
        business_justification="Exception requiring CFO approval",
        job_title="Revenue Manager",
        department="Finance",
        compensating_controls=[
            {
                "control_name": "Weekly Manager Review",
                "risk_reduction_percentage": 60,
                "estimated_annual_cost": 75000
            }
        ],
        review_frequency="Monthly",
        auto_approve_if_authorized=False  # Just request, don't auto-approve
    )

    print(result)


async def test_approval_request_no_auto_approve():
    """Test approval request without auto-approve (just validation)"""
    print("\n" + "="*80)
    print("TEST 6: Request Approval - No Auto-Approve (Just Check)")
    print("="*80)

    result = await request_exception_approval_handler(
        requester_email="robin.turner@fivetran.com",  # Controller - can approve MEDIUM
        user_identifier="check.user@fivetran.com",
        user_name="Check User",
        role_names=["Fivetran - GL Accounting", "Fivetran - AP Processing"],
        conflict_count=3,
        critical_conflicts=0,
        risk_score=45.0,  # MEDIUM level
        business_justification="Testing approval workflow without auto-approve",
        job_title="Accountant",
        department="Finance",
        compensating_controls=[
            {
                "control_name": "Monthly Reconciliation",
                "risk_reduction_percentage": 70,
                "estimated_annual_cost": 30000
            }
        ],
        review_frequency="Quarterly",
        auto_approve_if_authorized=False  # Don't auto-approve, just validate
    )

    print(result)


async def main():
    """Run all Phase 4 tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*18 + "PHASE 4: RBAC & APPROVAL WORKFLOW TEST SUITE" + " "*16 + "║")
    print("╚" + "="*78 + "╝")

    try:
        # Test 1: Check authority for CFO
        await test_check_authority_cfo()

        # Test 2: Check authority for Controller
        await test_check_authority_controller()

        # Test 3: Check authority without specific risk score
        await test_check_authority_no_score()

        # Test 4: Approval request from authorized user (auto-approve)
        await test_approval_request_authorized()

        # Test 5: Approval request from unauthorized user (escalation)
        await test_approval_request_unauthorized()

        # Test 6: Approval request without auto-approve
        await test_approval_request_no_auto_approve()

        print("\n" + "="*80)
        print("✅ ALL PHASE 4 TESTS COMPLETED")
        print("="*80)

        print("\n💡 Next Steps:")
        print("• Configure Jira environment variables (JIRA_URL, JIRA_API_TOKEN, etc.)")
        print("• Use check_my_approval_authority to verify user permissions")
        print("• Use request_exception_approval for RBAC-enabled exception workflow")
        print("• Review Jira tickets created for escalations")
        print("• Test manager chain lookup for complex reporting structures")
        print("\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
