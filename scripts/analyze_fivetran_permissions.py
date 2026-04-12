#!/usr/bin/env python3
"""
Fivetran Role Permission Analysis Script

Purpose: Extract Fivetran roles, analyze permission conflicts, and generate SOD rules

This script:
1. Calls the Fivetran roles RESTlet to get all Fivetran roles and permissions
2. Analyzes permissions across roles to identify potential conflicts
3. Generates SOD rules based on permission conflicts
4. Outputs results for review and rule creation

Usage:
    python3 scripts/analyze_fivetran_permissions.py

Requirements:
    - NetSuite RESTlet deployed (fivetran_roles_permissions_restlet.js)
    - NETSUITE_FIVETRAN_RESTLET_URL environment variable set
    - Or pass --restlet-url parameter

Author: Prabal Saha
Date: 2026-02-12
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.netsuite_client import NetSuiteClient


class FivetranPermissionAnalyzer:
    """Analyzes Fivetran role permissions for SOD conflicts"""

    def __init__(self, netsuite_client: NetSuiteClient, restlet_url: str):
        """
        Initialize analyzer

        Args:
            netsuite_client: NetSuite client for API calls
            restlet_url: URL of Fivetran roles RESTlet
        """
        self.client = netsuite_client
        self.restlet_url = restlet_url
        self.roles_data = None
        self.permission_matrix = {}
        self.conflicts = []

    def fetch_fivetran_roles(self) -> dict[str, Any]:
        """
        Fetch all Fivetran roles and permissions from NetSuite

        Returns:
            Dict with roles and metadata
        """
        print("=" * 80)
        print("STEP 1: Fetching Fivetran Roles from NetSuite")
        print("=" * 80)

        payload = {
            "includePermissions": True,
            "includeInactive": False,
            "rolePrefix": "Fivetran -"
        }

        print(f"\nCalling RESTlet: {self.restlet_url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")

        # Make request
        response = self.client.session.post(
            self.restlet_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise Exception(f"RESTlet call failed: {response.status_code} - {response.text}")

        result = response.json()

        if not result.get('success'):
            raise Exception(f"RESTlet returned error: {result.get('error')}")

        self.roles_data = result['data']

        # Print summary
        metadata = self.roles_data['metadata']
        print("\n✅ Successfully fetched roles")
        print(f"   • Total roles: {metadata['total_roles']}")
        print(f"   • Execution time: {metadata['execution_time_ms']}ms")
        print(f"   • Governance used: {metadata['governance_used']} units")

        return self.roles_data

    def build_permission_matrix(self):
        """
        Build a matrix of roles and their permissions

        Creates:
            permission_matrix[permission_name] = [list of roles with that permission]
        """
        print("\n" + "=" * 80)
        print("STEP 2: Building Permission Matrix")
        print("=" * 80)

        self.permission_matrix = defaultdict(list)

        for role in self.roles_data['roles']:
            role_name = role['role_name']
            permissions = role.get('permissions', [])

            print(f"\n{role_name}:")
            print(f"   • Permissions: {len(permissions)}")

            for perm in permissions:
                perm_name = perm['permission_name']
                perm_level = perm['permission_level']

                # Store role with permission and level
                self.permission_matrix[perm_name].append({
                    'role_name': role_name,
                    'role_id': role['role_id'],
                    'permission_level': perm_level
                })

        print("\n✅ Permission matrix built")
        print(f"   • Unique permissions: {len(self.permission_matrix)}")
        print(f"   • Permissions shared across roles: {sum(1 for p in self.permission_matrix.values() if len(p) > 1)}")

    def analyze_conflicts(self) -> list[dict[str, Any]]:
        """
        Analyze permission matrix for potential SOD conflicts

        Returns:
            List of potential conflicts
        """
        print("\n" + "=" * 80)
        print("STEP 3: Analyzing Permission Conflicts")
        print("=" * 80)

        self.conflicts = []

        # Define high-risk permission patterns
        high_risk_patterns = {
            'create_edit': ['CREATE', 'EDIT', 'FULL'],
            'approve': ['APPROVE'],
            'view': ['VIEW'],
            'process': ['PROCESS', 'EXECUTE'],
            'delete': ['DELETE'],
            'master_data': ['MANAGE', 'SETUP', 'MAINTAIN']
        }

        # Categorize permissions
        permission_categories = defaultdict(list)

        for perm_name, roles in self.permission_matrix.items():
            # Only analyze permissions shared by multiple roles
            if len(roles) < 2:
                continue

            # Categorize permission
            perm_upper = perm_name.upper()
            for category, patterns in high_risk_patterns.items():
                if any(pattern in perm_upper for pattern in patterns):
                    permission_categories[category].append({
                        'permission': perm_name,
                        'roles': roles
                    })
                    break

        # Identify conflicts: roles that have conflicting permission types
        print("\nAnalyzing role combinations for conflicts...\n")

        # Get all unique role pairs
        all_roles = set()
        for role in self.roles_data['roles']:
            all_roles.add(role['role_name'])

        role_list = sorted(all_roles)

        for i, role1 in enumerate(role_list):
            for role2 in role_list[i+1:]:
                conflict = self._check_role_pair_conflict(role1, role2, permission_categories)
                if conflict:
                    self.conflicts.append(conflict)

        print("\n✅ Conflict analysis complete")
        print(f"   • Total conflicts found: {len(self.conflicts)}")

        return self.conflicts

    def _check_role_pair_conflict(
        self,
        role1: str,
        role2: str,
        permission_categories: dict[str, list[dict]]
    ) -> dict[str, Any]:
        """
        Check if two roles have conflicting permissions

        Args:
            role1: First role name
            role2: Second role name
            permission_categories: Categorized permissions

        Returns:
            Conflict dict if conflict found, None otherwise
        """
        # Classic SOD conflict patterns
        sod_patterns = [
            # Financial SOD
            (['create_edit'], ['approve'], 'HIGH', 'Same user can create and approve transactions'),
            (['master_data'], ['process'], 'HIGH', 'Same user can setup master data and process transactions'),
            (['create_edit'], ['delete'], 'MEDIUM', 'Same user can create and delete records'),

            # AP SOD
            (['create_edit'], ['process'], 'HIGH', 'AP processing conflict'),

            # General segregation
            (['approve'], ['process'], 'MEDIUM', 'Approval and processing by same user'),
        ]

        role1_categories = self._get_role_categories(role1, permission_categories)
        role2_categories = self._get_role_categories(role2, permission_categories)

        # Check each SOD pattern
        for cat1_list, cat2_list, severity, description in sod_patterns:
            # Check if role1 has permissions from cat1 and role2 has permissions from cat2
            role1_has_cat1 = any(cat in role1_categories for cat in cat1_list)
            role2_has_cat2 = any(cat in role2_categories for cat in cat2_list)

            # Check reverse (role2 has cat1, role1 has cat2)
            role2_has_cat1 = any(cat in role2_categories for cat in cat1_list)
            role1_has_cat2 = any(cat in role1_categories for cat in cat2_list)

            if (role1_has_cat1 and role2_has_cat2) or (role2_has_cat1 and role1_has_cat2):
                # Found a conflict
                conflicting_perms = self._get_conflicting_permissions(
                    role1, role2, cat1_list + cat2_list, permission_categories
                )

                if conflicting_perms:
                    return {
                        'role1': role1,
                        'role2': role2,
                        'severity': severity,
                        'description': description,
                        'conflicting_permissions': conflicting_perms,
                        'risk_category': 'Financial'  # Can be refined
                    }

        return None

    def _get_role_categories(
        self,
        role_name: str,
        permission_categories: dict[str, list[dict]]
    ) -> set[str]:
        """Get all permission categories for a role"""
        categories = set()
        for category, perms in permission_categories.items():
            for perm_info in perms:
                if any(r['role_name'] == role_name for r in perm_info['roles']):
                    categories.add(category)
        return categories

    def _get_conflicting_permissions(
        self,
        role1: str,
        role2: str,
        categories: list[str],
        permission_categories: dict[str, list[dict]]
    ) -> list[str]:
        """Get list of specific conflicting permissions"""
        conflicting = []
        for category in categories:
            if category in permission_categories:
                for perm_info in permission_categories[category]:
                    role_names = [r['role_name'] for r in perm_info['roles']]
                    if role1 in role_names or role2 in role_names:
                        conflicting.append(perm_info['permission'])
        return list(set(conflicting))

    def generate_sod_rules(self) -> list[dict[str, Any]]:
        """
        Generate SOD rules from identified conflicts

        Returns:
            List of SOD rule definitions
        """
        print("\n" + "=" * 80)
        print("STEP 4: Generating SOD Rules")
        print("=" * 80)

        sod_rules = []

        for i, conflict in enumerate(self.conflicts, 1):
            rule_id = f"SOD-FIVETRAN-{i:03d}"

            rule = {
                "rule_id": rule_id,
                "rule_name": f"{conflict['role1']} vs. {conflict['role2']} Separation",
                "rule_type": conflict['risk_category'],
                "description": f"{conflict['description']}. Conflicting permissions: {', '.join(conflict['conflicting_permissions'][:5])}",
                "conflicting_permissions": conflict['conflicting_permissions'],
                "severity": conflict['severity'],
                "is_active": True
            }

            sod_rules.append(rule)

            print(f"\n{rule_id}: {rule['rule_name']}")
            print(f"   • Severity: {rule['severity']}")
            print(f"   • Permissions: {len(rule['conflicting_permissions'])}")

        print(f"\n✅ Generated {len(sod_rules)} SOD rules")

        return sod_rules

    def export_results(self, output_dir: str = "output"):
        """
        Export analysis results to files

        Args:
            output_dir: Directory to save output files
        """
        print("\n" + "=" * 80)
        print("STEP 5: Exporting Results")
        print("=" * 80)

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Export raw roles data
        roles_file = output_path / f"fivetran_roles_{timestamp}.json"
        with open(roles_file, 'w') as f:
            json.dump(self.roles_data, f, indent=2)
        print(f"\n✅ Roles data: {roles_file}")

        # 2. Export permission matrix
        matrix_file = output_path / f"permission_matrix_{timestamp}.json"
        # Convert defaultdict to regular dict for JSON serialization
        matrix_dict = dict(self.permission_matrix.items())
        with open(matrix_file, 'w') as f:
            json.dump(matrix_dict, f, indent=2)
        print(f"✅ Permission matrix: {matrix_file}")

        # 3. Export conflicts
        conflicts_file = output_path / f"conflicts_{timestamp}.json"
        with open(conflicts_file, 'w') as f:
            json.dump(self.conflicts, f, indent=2)
        print(f"✅ Conflicts: {conflicts_file}")

        # 4. Export SOD rules
        sod_rules = self.generate_sod_rules()
        rules_file = output_path / f"sod_rules_fivetran_{timestamp}.json"
        with open(rules_file, 'w') as f:
            json.dump(sod_rules, f, indent=2)
        print(f"✅ SOD rules: {rules_file}")

        # 5. Generate human-readable report
        report_file = output_path / f"analysis_report_{timestamp}.txt"
        self._generate_report(report_file)
        print(f"✅ Analysis report: {report_file}")

        print(f"\n✅ All results exported to: {output_path}")

    def _generate_report(self, report_file: Path):
        """Generate human-readable analysis report"""
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("FIVETRAN ROLE PERMISSION ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Fivetran Roles: {len(self.roles_data['roles'])}\n")
            f.write(f"Unique Permissions: {len(self.permission_matrix)}\n")
            f.write(f"Conflicts Identified: {len(self.conflicts)}\n\n")

            # Roles
            f.write("FIVETRAN ROLES\n")
            f.write("-" * 80 + "\n")
            for role in self.roles_data['roles']:
                f.write(f"\n{role['role_name']}:\n")
                f.write(f"   Role ID: {role['role_id']}\n")
                f.write(f"   Permissions: {role['permission_count']}\n")
                f.write(f"   Active: {'Yes' if not role['is_inactive'] else 'No'}\n")

            # Conflicts
            f.write("\n\nIDENTIFIED CONFLICTS\n")
            f.write("-" * 80 + "\n")
            for i, conflict in enumerate(self.conflicts, 1):
                f.write(f"\n{i}. {conflict['role1']} + {conflict['role2']}\n")
                f.write(f"   Severity: {conflict['severity']}\n")
                f.write(f"   Description: {conflict['description']}\n")
                f.write(f"   Conflicting Permissions ({len(conflict['conflicting_permissions'])}):\n")
                for perm in conflict['conflicting_permissions'][:10]:
                    f.write(f"      - {perm}\n")
                if len(conflict['conflicting_permissions']) > 10:
                    f.write(f"      ... and {len(conflict['conflicting_permissions']) - 10} more\n")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Analyze Fivetran role permissions for SOD conflicts')
    parser.add_argument(
        '--restlet-url',
        help='Fivetran roles RESTlet URL (or set NETSUITE_FIVETRAN_RESTLET_URL env var)'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for results (default: output)'
    )

    args = parser.parse_args()

    # Get RESTlet URL
    restlet_url = args.restlet_url or os.getenv('NETSUITE_FIVETRAN_RESTLET_URL')
    if not restlet_url:
        print("ERROR: RESTlet URL not provided")
        print("Set NETSUITE_FIVETRAN_RESTLET_URL environment variable or use --restlet-url parameter")
        sys.exit(1)

    print("=" * 80)
    print("FIVETRAN ROLE PERMISSION ANALYSIS")
    print("=" * 80)
    print(f"RESTlet URL: {restlet_url}")
    print(f"Output directory: {args.output_dir}\n")

    # Initialize NetSuite client
    print("Initializing NetSuite client...")
    client = NetSuiteClient()

    # Initialize analyzer
    analyzer = FivetranPermissionAnalyzer(client, restlet_url)

    # Run analysis
    try:
        # Step 1: Fetch roles
        analyzer.fetch_fivetran_roles()

        # Step 2: Build permission matrix
        analyzer.build_permission_matrix()

        # Step 3: Analyze conflicts
        analyzer.analyze_conflicts()

        # Step 4 & 5: Generate rules and export
        analyzer.export_results(args.output_dir)

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Review the analysis report")
        print("2. Validate identified conflicts")
        print("3. Import SOD rules into database")
        print("4. Run SOD analysis on users")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
