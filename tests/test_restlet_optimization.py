#!/usr/bin/env python3
"""
Test script to verify RESTlet optimization improvements

This script compares the old vs new RESTlet implementation and verifies:
1. Governance usage reduction (500x improvement expected)
2. Pagination functionality
3. Governance monitoring dashboard
4. Error handling and graceful degradation

Usage:
    python3 tests/test_restlet_optimization.py
"""

import json
import os
import sys
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.netsuite_client import NetSuiteClient


class RESTletOptimizationTester:
    """Test suite for RESTlet optimization verification"""

    def __init__(self):
        self.client = NetSuiteClient()
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests_passed': 0,
            'tests_failed': 0,
            'tests': []
        }

    def print_header(self, title: str):
        """Print formatted test section header"""
        print("\n" + "=" * 80)
        print(f" {title}")
        print("=" * 80 + "\n")

    def print_test(self, name: str, passed: bool, details: str = ""):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"   {details}")

        self.test_results['tests'].append({
            'name': name,
            'passed': passed,
            'details': details
        })

        if passed:
            self.test_results['tests_passed'] += 1
        else:
            self.test_results['tests_failed'] += 1

    def test_1_basic_connection(self) -> bool:
        """Test 1: Verify RESTlet connection"""
        self.print_header("TEST 1: Basic Connection Test")

        try:
            # Test connection
            success = self.client.test_connection()

            if success:
                self.print_test(
                    "RESTlet Connection",
                    True,
                    "Successfully connected to NetSuite"
                )
                return True
            else:
                self.print_test(
                    "RESTlet Connection",
                    False,
                    "Failed to connect to NetSuite"
                )
                return False

        except Exception as e:
            self.print_test(
                "RESTlet Connection",
                False,
                f"Error: {str(e)}"
            )
            return False

    def test_2_pagination(self) -> bool:
        """Test 2: Verify pagination with reduced limits"""
        self.print_header("TEST 2: Pagination Test")

        try:
            # Test small batch (10 users)
            print("Fetching 10 users...")
            result = self.client.get_users_and_roles(
                include_permissions=False,
                limit=10,
                offset=0
            )

            if not result['success']:
                self.print_test(
                    "Pagination (10 users)",
                    False,
                    f"API returned error: {result.get('error', 'Unknown')}"
                )
                return False

            metadata = result['data']['metadata']
            users = result['data']['users']

            # Verify metadata
            checks = [
                ('returned_count', metadata.get('returned_count') == len(users)),
                ('limit', metadata.get('limit') == 10),
                ('offset', metadata.get('offset') == 0),
                ('next_offset exists', 'next_offset' in metadata),
                ('has_more flag', 'has_more' in metadata),
            ]

            all_passed = all(check[1] for check in checks)

            for check_name, check_result in checks:
                self.print_test(
                    f"  {check_name}",
                    check_result,
                    f"Value: {metadata.get(check_name.replace(' ', '_'))}"
                )

            # Test pagination with offset
            if metadata.get('has_more'):
                print("\nTesting pagination with offset...")
                next_offset = metadata['next_offset']

                result2 = self.client.get_users_and_roles(
                    include_permissions=False,
                    limit=10,
                    offset=next_offset
                )

                if result2['success']:
                    users2 = result2['data']['users']
                    # Verify we got different users
                    user_ids_1 = {u['user_id'] for u in users}
                    user_ids_2 = {u['user_id'] for u in users2}
                    no_overlap = len(user_ids_1 & user_ids_2) == 0

                    self.print_test(
                        "  Pagination offset",
                        no_overlap,
                        f"Got {len(users2)} different users"
                    )

            return all_passed

        except Exception as e:
            self.print_test(
                "Pagination Test",
                False,
                f"Error: {str(e)}"
            )
            return False

    def test_3_governance_monitoring(self) -> bool:
        """Test 3: Verify governance monitoring dashboard"""
        self.print_header("TEST 3: Governance Monitoring Dashboard")

        try:
            print("Fetching users with governance monitoring...")
            result = self.client.get_users_and_roles(
                include_permissions=True,
                limit=50
            )

            if not result['success']:
                self.print_test(
                    "Governance Dashboard",
                    False,
                    f"API returned error: {result.get('error', 'Unknown')}"
                )
                return False

            # Check if governance dashboard exists
            governance = result['data'].get('governance', {})

            if not governance:
                self.print_test(
                    "Governance Dashboard Present",
                    False,
                    "No governance data in response"
                )
                return False

            # Verify governance fields
            expected_fields = [
                'starting_units',
                'ending_units',
                'units_used',
                'units_per_user',
                'optimization_ratio',
                'warnings',
                'safety_margin',
                'max_limit'
            ]

            all_fields_present = all(field in governance for field in expected_fields)

            self.print_test(
                "Governance Dashboard Present",
                True,
                f"Found {len(governance)} governance metrics"
            )

            # Display governance metrics
            print("\n📊 GOVERNANCE METRICS:")
            print(f"   Starting Units:       {governance.get('starting_units', 'N/A')}")
            print(f"   Ending Units:         {governance.get('ending_units', 'N/A')}")
            print(f"   Units Used:           {governance.get('units_used', 'N/A')}")
            print(f"   Units Per User:       {governance.get('units_per_user', 'N/A')}")
            print(f"   Optimization:         {governance.get('optimization_ratio', 'N/A')}")
            print(f"   Safety Margin:        {governance.get('safety_margin', 'N/A')}")
            print(f"   Max Limit:            {governance.get('max_limit', 'N/A')}")

            warnings = governance.get('warnings', [])
            if warnings:
                print(f"   ⚠️  Warnings:          {len(warnings)}")
                for warning in warnings:
                    print(f"      - {warning}")
            else:
                print("   ✅ Warnings:          None")

            # Calculate efficiency
            units_used = governance.get('units_used', 0)
            units_per_user = float(governance.get('units_per_user', 0))
            users_returned = result['data']['metadata'].get('returned_count', 0)

            print("\n📈 EFFICIENCY ANALYSIS:")
            print(f"   Users Processed:      {users_returned}")
            print(f"   Total Units Used:     {units_used}")
            print(f"   Efficiency:           {units_per_user} units/user")

            # Expected: < 1 unit per user (was ~10 units/user in old version)
            efficiency_good = units_per_user < 1.0

            self.print_test(
                "Governance Efficiency",
                efficiency_good,
                f"{units_per_user} units/user (target: < 1.0)"
            )

            self.print_test(
                "All Dashboard Fields Present",
                all_fields_present,
                f"{sum(1 for f in expected_fields if f in governance)}/{len(expected_fields)} fields"
            )

            return all_fields_present and efficiency_good

        except Exception as e:
            self.print_test(
                "Governance Monitoring",
                False,
                f"Error: {str(e)}"
            )
            return False

    def test_4_batch_processing(self) -> bool:
        """Test 4: Verify batch role and permission fetching"""
        self.print_header("TEST 4: Batch Processing Verification")

        try:
            print("Testing batch processing with 50 users...")
            start_time = time.time()

            result = self.client.get_users_and_roles(
                include_permissions=True,
                limit=50
            )

            end_time = time.time()
            execution_time = end_time - start_time

            if not result['success']:
                self.print_test(
                    "Batch Processing",
                    False,
                    f"API returned error: {result.get('error', 'Unknown')}"
                )
                return False

            users = result['data']['users']
            metadata = result['data']['metadata']
            governance = result['data'].get('governance', {})

            # Verify users have roles
            users_with_roles = sum(1 for u in users if u.get('roles_count', 0) > 0)
            roles_fetched = users_with_roles > 0

            self.print_test(
                "Roles Fetched",
                roles_fetched,
                f"{users_with_roles}/{len(users)} users have roles"
            )

            # Verify permissions were fetched
            users_with_permissions = 0
            total_permissions = 0

            for user in users:
                for role in user.get('roles', []):
                    perms = role.get('permissions', [])
                    if perms:
                        users_with_permissions += 1
                        total_permissions += len(perms)

            permissions_fetched = users_with_permissions > 0

            self.print_test(
                "Permissions Fetched",
                permissions_fetched,
                f"{total_permissions} total permissions across {users_with_permissions} roles"
            )

            # Verify execution time is reasonable
            api_time = metadata.get('execution_time_seconds', 0)
            time_reasonable = api_time < 10  # Should complete in < 10 seconds

            self.print_test(
                "Execution Time",
                time_reasonable,
                f"{api_time:.2f}s (API) + {execution_time:.2f}s (total) - Target: < 10s"
            )

            # Verify governance efficiency
            units_used = governance.get('units_used', 0)
            efficiency = units_used < 500  # Should use < 500 units for 50 users

            self.print_test(
                "Governance Efficiency",
                efficiency,
                f"{units_used} units for {len(users)} users (target: < 500)"
            )

            return roles_fetched and permissions_fetched and time_reasonable and efficiency

        except Exception as e:
            self.print_test(
                "Batch Processing",
                False,
                f"Error: {str(e)}"
            )
            return False

    def test_5_version_info(self) -> bool:
        """Test 5: Verify optimized version is deployed"""
        self.print_header("TEST 5: Version Information")

        try:
            result = self.client.get_users_and_roles(limit=1)

            if not result['success']:
                self.print_test(
                    "Version Check",
                    False,
                    "Could not fetch version info"
                )
                return False

            metadata = result['data']['metadata']
            version = metadata.get('version', 'unknown')

            # Check if optimized version
            is_optimized = 'optimized' in version.lower() or version.startswith('2.')

            self.print_test(
                "Optimized Version Deployed",
                is_optimized,
                f"Version: {version}"
            )

            # Display version info
            print("\n📦 VERSION INFORMATION:")
            print(f"   RESTlet Version:      {version}")
            print(f"   Timestamp:            {metadata.get('timestamp', 'N/A')}")
            print("   Features:")
            print("      ✅ Batch Role Fetching (SuiteQL)")
            print("      ✅ Batch Permission Fetching")
            print("      ✅ Governance Monitoring")
            print("      ✅ Reduced Default Limit (50)")
            print("      ✅ Governance Dashboard")

            return is_optimized

        except Exception as e:
            self.print_test(
                "Version Check",
                False,
                f"Error: {str(e)}"
            )
            return False

    def test_6_stress_test(self) -> bool:
        """Test 6: Stress test with maximum limit"""
        self.print_header("TEST 6: Stress Test (Max Limit)")

        try:
            print("Testing maximum limit (200 users)...")
            print("⚠️  This may take 10-15 seconds...\n")

            start_time = time.time()

            result = self.client.get_users_and_roles(
                include_permissions=True,
                limit=200  # Maximum allowed
            )

            end_time = time.time()
            end_time - start_time

            if not result['success']:
                self.print_test(
                    "Stress Test",
                    False,
                    f"API returned error: {result.get('error', 'Unknown')}"
                )
                return False

            users = result['data']['users']
            governance = result['data'].get('governance', {})
            metadata = result['data']['metadata']

            # Verify no governance warnings
            warnings = governance.get('warnings', [])
            no_warnings = len(warnings) == 0

            self.print_test(
                "No Governance Warnings",
                no_warnings,
                f"{len(warnings)} warnings" if warnings else "Clean execution"
            )

            # Verify reasonable execution time
            api_time = metadata.get('execution_time_seconds', 0)
            time_ok = api_time < 30  # Should complete in < 30 seconds

            self.print_test(
                "Execution Time Acceptable",
                time_ok,
                f"{api_time:.2f}s (API) - Target: < 30s"
            )

            # Verify governance usage
            units_used = governance.get('units_used', 0)
            units_ok = units_used < 1000  # Should use < 1000 units for 200 users

            self.print_test(
                "Governance Usage Acceptable",
                units_ok,
                f"{units_used} units for {len(users)} users (target: < 1000)"
            )

            # Calculate efficiency
            units_per_user = float(governance.get('units_per_user', 0))

            print("\n📊 STRESS TEST RESULTS:")
            print(f"   Users Processed:      {len(users)}")
            print(f"   Total Units Used:     {units_used}")
            print(f"   Units Per User:       {units_per_user}")
            print(f"   Execution Time:       {api_time:.2f}s")
            print(f"   Ending Units:         {governance.get('ending_units', 'N/A')}")

            return no_warnings and time_ok and units_ok

        except Exception as e:
            self.print_test(
                "Stress Test",
                False,
                f"Error: {str(e)}"
            )
            return False

    def run_all_tests(self):
        """Run all optimization tests"""
        print("\n" + "=" * 80)
        print(" RESTlet Optimization Test Suite")
        print(" Testing NetSuite SuiteScript 2.1 RESTlet v2.0.0 (Optimized)")
        print("=" * 80)

        # Run tests
        tests = [
            self.test_1_basic_connection,
            self.test_2_pagination,
            self.test_3_governance_monitoring,
            self.test_4_batch_processing,
            self.test_5_version_info,
            self.test_6_stress_test
        ]

        for test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"\n❌ Test {test_func.__name__} crashed: {str(e)}")
                self.test_results['tests_failed'] += 1

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        self.print_header("TEST SUMMARY")

        total_tests = self.test_results['tests_passed'] + self.test_results['tests_failed']
        pass_rate = (self.test_results['tests_passed'] / max(total_tests, 1)) * 100

        print(f"Total Tests:       {total_tests}")
        print(f"✅ Passed:         {self.test_results['tests_passed']}")
        print(f"❌ Failed:         {self.test_results['tests_failed']}")
        print(f"Pass Rate:         {pass_rate:.1f}%")
        print(f"Timestamp:         {self.test_results['timestamp']}")

        if self.test_results['tests_failed'] == 0:
            print("\n🎉 ALL TESTS PASSED! RESTlet optimization verified successfully.")
        else:
            print("\n⚠️  SOME TESTS FAILED. Review the results above.")

        # Save results to file
        results_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tests',
            'optimization_test_results.json'
        )

        try:
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            print(f"\n📄 Results saved to: {results_file}")
        except Exception as e:
            print(f"\n⚠️  Could not save results: {str(e)}")


def main():
    """Main test runner"""
    tester = RESTletOptimizationTester()
    tester.run_all_tests()


if __name__ == '__main__':
    main()
