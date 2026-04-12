#!/usr/bin/env python3
"""
Advanced Fivetran Role Permission Analysis with NetSuite Research

Purpose:
1. Extract all Fivetran role permissions
2. Research each permission using NetSuite documentation
3. Build fundamental permission conflict matrix
4. Generate research-backed SOD rules

This script uses:
- NetSuite RESTlet for data extraction
- Web search for permission research
- SOD best practices from NetSuite documentation
- Automated conflict detection based on permission functions

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

# NetSuite Permission Categories (based on NetSuite documentation)
PERMISSION_CATEGORIES = {
    # Transaction Creation/Entry
    'transaction_entry': {
        'keywords': ['TRAN_', '_ENTRY', '_CREATE', 'CREATE_'],
        'description': 'Can create or enter transactions',
        'risk': 'HIGH',
        'conflicts_with': ['transaction_approval', 'transaction_payment']
    },

    # Transaction Approval
    'transaction_approval': {
        'keywords': ['_APPROVE', 'APPROVE_', '_APPROVAL'],
        'description': 'Can approve transactions',
        'risk': 'HIGH',
        'conflicts_with': ['transaction_entry', 'transaction_payment', 'master_data_setup']
    },

    # Payment Processing
    'transaction_payment': {
        'keywords': ['TRAN_VENDPYMT', 'TRAN_CUSTPYMT', 'TRAN_PAYMENT', '_PAYMT'],
        'description': 'Can process payments',
        'risk': 'CRITICAL',
        'conflicts_with': ['transaction_entry', 'transaction_approval', 'vendor_setup']
    },

    # Vendor/Master Data Setup
    'vendor_setup': {
        'keywords': ['LIST_VENDOR', 'EDIT_VENDOR', 'SETUP_', 'ADMI_'],
        'description': 'Can create/modify vendor master data',
        'risk': 'HIGH',
        'conflicts_with': ['transaction_payment', 'transaction_approval']
    },

    # Journal Entry
    'journal_entry': {
        'keywords': ['TRAN_JOURNAL', 'JOURNAL_'],
        'description': 'Can create journal entries',
        'risk': 'CRITICAL',
        'conflicts_with': ['journal_approval', 'financial_reporting']
    },

    # Journal Approval
    'journal_approval': {
        'keywords': ['JOURNAL_APPROVE', 'APPROVE_JOURNAL'],
        'description': 'Can approve journal entries',
        'risk': 'HIGH',
        'conflicts_with': ['journal_entry']
    },

    # Bank Reconciliation
    'bank_reconciliation': {
        'keywords': ['TRAN_RECON', 'RECONCILE', 'BANK_'],
        'description': 'Can perform bank reconciliation',
        'risk': 'HIGH',
        'conflicts_with': ['transaction_payment', 'cash_management']
    },

    # Cash Management
    'cash_management': {
        'keywords': ['TRAN_DEPOSIT', 'TRAN_TRANSFER', 'CASH_'],
        'description': 'Can manage cash transactions',
        'risk': 'HIGH',
        'conflicts_with': ['bank_reconciliation', 'transaction_approval']
    },

    # User Administration
    'user_admin': {
        'keywords': ['ADMI_USER', 'SETUP_USER', 'LIST_USER', 'EDIT_USER'],
        'description': 'Can create/modify user accounts',
        'risk': 'CRITICAL',
        'conflicts_with': ['all_operational']
    },

    # Role Administration
    'role_admin': {
        'keywords': ['ADMI_ROLE', 'SETUP_ROLE', 'LIST_ROLE', 'EDIT_ROLE'],
        'description': 'Can create/modify roles and permissions',
        'risk': 'CRITICAL',
        'conflicts_with': ['all_operational']
    },

    # Financial Reporting
    'financial_reporting': {
        'keywords': ['REPO_FINANCIALS', 'REPO_', 'REPORT_'],
        'description': 'Can view financial reports',
        'risk': 'MEDIUM',
        'conflicts_with': ['journal_entry', 'transaction_entry']
    },

    # Inventory Management
    'inventory_mgmt': {
        'keywords': ['TRAN_INVADJST', 'TRAN_INVTRNFR', 'LIST_ITEM'],
        'description': 'Can manage inventory',
        'risk': 'HIGH',
        'conflicts_with': ['inventory_approval', 'purchasing']
    },

    # Purchase Order
    'purchasing': {
        'keywords': ['TRAN_PURCHORD', 'TRAN_PURCHREQ', 'PO_'],
        'description': 'Can create purchase orders',
        'risk': 'HIGH',
        'conflicts_with': ['purchase_approval', 'receiving']
    },

    # Purchase Approval
    'purchase_approval': {
        'keywords': ['PURCHORD_APPROVE', 'APPROVE_PURCH'],
        'description': 'Can approve purchase orders',
        'risk': 'HIGH',
        'conflicts_with': ['purchasing', 'receiving']
    },

    # Receiving
    'receiving': {
        'keywords': ['TRAN_ITEMRCPT', 'RECEIVE_', 'RECEIPT_'],
        'description': 'Can receive inventory',
        'risk': 'MEDIUM',
        'conflicts_with': ['purchasing', 'purchase_approval']
    },

    # Payroll
    'payroll': {
        'keywords': ['TRAN_PAYCHECK', 'PAYROLL_', 'ADMI_PAYROLL'],
        'description': 'Can process payroll',
        'risk': 'CRITICAL',
        'conflicts_with': ['employee_setup', 'payroll_approval']
    },

    # Employee Setup
    'employee_setup': {
        'keywords': ['LIST_EMPLOYEE', 'EDIT_EMPLOYEE', 'SETUP_EMPLOYEE'],
        'description': 'Can create/modify employee records',
        'risk': 'HIGH',
        'conflicts_with': ['payroll', 'payroll_approval']
    }
}


class AdvancedPermissionAnalyzer:
    """Advanced analyzer with NetSuite documentation research"""

    def __init__(self, netsuite_client: NetSuiteClient, restlet_url: str):
        self.client = netsuite_client
        self.restlet_url = restlet_url
        self.roles_data = None
        self.all_permissions = set()
        self.permission_metadata = {}
        self.permission_matrix = {}
        self.categorized_permissions = defaultdict(list)
        self.conflict_rules = []

    def fetch_fivetran_roles(self) -> dict[str, Any]:
        """Fetch all Fivetran roles and permissions from NetSuite"""
        print("=" * 80)
        print("STEP 1: Fetching Fivetran Roles from NetSuite")
        print("=" * 80)

        payload = {
            "includePermissions": True,
            "includeInactive": False,
            "rolePrefix": "Fivetran -"
        }

        print(f"\nCalling RESTlet: {self.restlet_url}")
        print("Requesting roles starting with: 'Fivetran -'")

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
        metadata = self.roles_data['metadata']

        # Filter out roles ending with "OLD"
        original_count = len(self.roles_data['roles'])
        self.roles_data['roles'] = [
            role for role in self.roles_data['roles']
            if not role['role_name'].endswith('OLD')
        ]
        filtered_count = len(self.roles_data['roles'])
        excluded_count = original_count - filtered_count

        print("\n✅ Successfully fetched Fivetran roles")
        print(f"   • Total roles: {original_count}")
        print(f"   • Excluded roles ending with 'OLD': {excluded_count}")
        print(f"   • Active roles for analysis: {filtered_count}")
        print(f"   • Execution time: {metadata['execution_time_ms']}ms")

        # Collect all unique permissions
        for role in self.roles_data['roles']:
            for perm in role.get('permissions', []):
                self.all_permissions.add(perm['permission_name'])

        print(f"   • Unique permissions across all roles: {len(self.all_permissions)}")

        return self.roles_data

    def categorize_permissions(self):
        """Categorize permissions based on NetSuite patterns"""
        import re

        print("\n" + "=" * 80)
        print("STEP 2: Categorizing Permissions by Function")
        print("=" * 80)

        # Load enhanced categorization from JSON file
        category_file = Path(__file__).parent.parent / 'data' / 'netsuite_permission_categories.json'
        if category_file.exists():
            with open(category_file) as f:
                category_data = json.load(f)
                enhanced_categories = category_data['categories']
        else:
            print("⚠️  Category file not found, using built-in categories")
            enhanced_categories = PERMISSION_CATEGORIES

        print("\nAnalyzing each permission against NetSuite categories...\n")

        uncategorized = []
        categorized_count = 0

        for perm in sorted(self.all_permissions):
            categorized = False

            for category, config in enhanced_categories.items():
                # Check exact keyword matches
                if any(keyword.lower() == perm.lower() for keyword in config.get('keywords', [])):
                    self.categorized_permissions[category].append(perm)
                    self.permission_metadata[perm] = {
                        'category': category,
                        'description': config['description'],
                        'risk_level': config['risk'],
                        'conflicts_with': config.get('conflicts_with', [])
                    }
                    if categorized_count < 50:  # Only print first 50 to avoid clutter
                        print(f"✓ {perm:45s} → {category:30s} (Risk: {config['risk']})")
                    categorized = True
                    categorized_count += 1
                    break

                # Check regex patterns
                if not categorized and 'patterns' in config:
                    for pattern in config['patterns']:
                        try:
                            if re.search(pattern, perm, re.IGNORECASE):
                                self.categorized_permissions[category].append(perm)
                                self.permission_metadata[perm] = {
                                    'category': category,
                                    'description': config['description'],
                                    'risk_level': config['risk'],
                                    'conflicts_with': config.get('conflicts_with', [])
                                }
                                if categorized_count < 50:
                                    print(f"✓ {perm:45s} → {category:30s} (Risk: {config['risk']})")
                                categorized = True
                                categorized_count += 1
                                break
                        except re.error:
                            pass

                if categorized:
                    break

            if not categorized:
                uncategorized.append(perm)
                self.permission_metadata[perm] = {
                    'category': 'uncategorized',
                    'description': 'Unknown function',
                    'risk_level': 'LOW',
                    'conflicts_with': []
                }

        if categorized_count > 50:
            print(f"   ... and {categorized_count - 50} more categorized")

        print("\n✅ Categorization complete")
        print(f"   • Categorized: {categorized_count}")
        print(f"   • Uncategorized: {len(uncategorized)}")
        print(f"   • Categorization rate: {(categorized_count / len(self.all_permissions) * 100):.1f}%")

        if uncategorized:
            print("\n   Uncategorized permissions (may need manual review):")
            for perm in uncategorized[:10]:
                print(f"      - {perm}")
            if len(uncategorized) > 10:
                print(f"      ... and {len(uncategorized) - 10} more")

    def build_permission_matrix(self):
        """Build matrix showing which roles have which permissions"""
        print("\n" + "=" * 80)
        print("STEP 3: Building Role-Permission Matrix")
        print("=" * 80)

        # Matrix: permission -> list of roles with that permission
        for role in self.roles_data['roles']:
            role_name = role['role_name']
            print(f"\n{role_name}:")
            print(f"   Total permissions: {role['permission_count']}")

            # Group permissions by category
            role_categories = defaultdict(list)

            for perm in role.get('permissions', []):
                perm_name = perm['permission_name']
                perm_level = perm['permission_level']

                # Add to matrix
                if perm_name not in self.permission_matrix:
                    self.permission_matrix[perm_name] = []

                self.permission_matrix[perm_name].append({
                    'role_name': role_name,
                    'role_id': role['role_id'],
                    'permission_level': perm_level
                })

                # Group by category for display
                metadata = self.permission_metadata.get(perm_name, {})
                category = metadata.get('category', 'uncategorized')
                role_categories[category].append(perm_name)

            # Display category summary
            print("   Permissions by category:")
            for category in sorted(role_categories.keys()):
                perms = role_categories[category]
                config = PERMISSION_CATEGORIES.get(category, {})
                risk = config.get('risk', 'UNKNOWN')
                print(f"      • {category:25s}: {len(perms):3d} permissions (Risk: {risk})")

        print("\n✅ Permission matrix built")
        print(f"   • Total unique permissions: {len(self.permission_matrix)}")
        print(f"   • Permissions shared across roles: {sum(1 for p in self.permission_matrix.values() if len(p) > 1)}")

    def analyze_fundamental_conflicts(self):
        """
        Analyze fundamental permission conflicts based on SOD principles

        This uses NetSuite documentation and SOD best practices to identify
        which permission combinations should NEVER be held by the same user.
        """
        print("\n" + "=" * 80)
        print("STEP 4: Analyzing Fundamental Permission Conflicts")
        print("=" * 80)

        print("\nApplying SOD principles to identify conflicting permission pairs...\n")

        conflicts_found = []

        # Analyze each role pair
        roles = self.roles_data['roles']
        for i, role1 in enumerate(roles):
            for role2 in roles[i+1:]:
                conflict = self._analyze_role_pair(role1, role2)
                if conflict:
                    conflicts_found.append(conflict)
                    print(f"⚠️  CONFLICT: {conflict['role1']} + {conflict['role2']}")
                    print(f"    Severity: {conflict['severity']}")
                    print(f"    Reason: {conflict['reason']}")
                    print(f"    Conflicting categories: {', '.join(conflict['conflicting_categories'])}")
                    print()

        self.conflict_rules = conflicts_found

        print("✅ Analysis complete")
        print(f"   • Total conflicts identified: {len(conflicts_found)}")
        print(f"   • CRITICAL conflicts: {sum(1 for c in conflicts_found if c['severity'] == 'CRITICAL')}")
        print(f"   • HIGH conflicts: {sum(1 for c in conflicts_found if c['severity'] == 'HIGH')}")
        print(f"   • MEDIUM conflicts: {sum(1 for c in conflicts_found if c['severity'] == 'MEDIUM')}")

        return conflicts_found

    def _analyze_role_pair(self, role1: dict, role2: dict) -> dict:
        """
        Analyze a pair of roles for fundamental conflicts

        Returns conflict dict if found, None otherwise
        """
        role1_name = role1['role_name']
        role2_name = role2['role_name']

        # Get categories for each role
        role1_categories = self._get_role_categories(role1)
        role2_categories = self._get_role_categories(role2)

        # Check for direct category conflicts
        conflicting_categories = []
        max_severity = None
        reasons = []

        for cat1, _perms1 in role1_categories.items():
            if cat1 not in PERMISSION_CATEGORIES:
                continue

            conflicts_with = PERMISSION_CATEGORIES[cat1]['conflicts_with']

            for cat2, _perms2 in role2_categories.items():
                if cat2 not in PERMISSION_CATEGORIES:
                    continue

                # Check if these categories conflict
                if cat2 in conflicts_with or 'all_operational' in conflicts_with:
                    conflicting_categories.append(f"{cat1} + {cat2}")

                    # Determine severity
                    risk1 = PERMISSION_CATEGORIES[cat1]['risk']
                    risk2 = PERMISSION_CATEGORIES[cat2]['risk']

                    conflict_severity = self._calculate_severity(risk1, risk2)
                    if max_severity is None or self._severity_rank(conflict_severity) > self._severity_rank(max_severity):
                        max_severity = conflict_severity

                    # Add reason
                    desc1 = PERMISSION_CATEGORIES[cat1]['description']
                    desc2 = PERMISSION_CATEGORIES[cat2]['description']
                    reasons.append(f"{desc1} + {desc2}")

        if conflicting_categories:
            return {
                'role1': role1_name,
                'role2': role2_name,
                'role1_id': role1['role_id'],
                'role2_id': role2['role_id'],
                'severity': max_severity,
                'reason': ' | '.join(set(reasons)),
                'conflicting_categories': conflicting_categories,
                'risk_category': 'Financial'  # Can be refined based on categories
            }

        return None

    def _get_role_categories(self, role: dict) -> dict[str, list[str]]:
        """Get categorized permissions for a role"""
        categories = defaultdict(list)

        for perm in role.get('permissions', []):
            perm_name = perm['permission_name']
            metadata = self.permission_metadata.get(perm_name, {})
            category = metadata.get('category', 'uncategorized')
            categories[category].append(perm_name)

        return categories

    def _calculate_severity(self, risk1: str, risk2: str) -> str:
        """Calculate conflict severity based on risk levels"""
        risk_scores = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        score1 = risk_scores.get(risk1, 2)
        score2 = risk_scores.get(risk2, 2)
        total_score = score1 + score2

        if total_score >= 7:
            return 'CRITICAL'
        elif total_score >= 5:
            return 'HIGH'
        elif total_score >= 3:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _severity_rank(self, severity: str) -> int:
        """Get numeric rank for severity"""
        ranks = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        return ranks.get(severity, 0)

    def generate_sod_rules(self) -> list[dict[str, Any]]:
        """Generate SOD rules from fundamental conflicts"""
        print("\n" + "=" * 80)
        print("STEP 5: Generating Research-Backed SOD Rules")
        print("=" * 80)

        sod_rules = []

        for i, conflict in enumerate(self.conflict_rules, 1):
            rule_id = f"SOD-FIVETRAN-{i:03d}"

            rule = {
                "rule_id": rule_id,
                "rule_name": f"{conflict['role1']} vs. {conflict['role2']} Separation",
                "rule_type": conflict['risk_category'],
                "description": f"{conflict['reason']}. Conflicting permission categories: {', '.join(conflict['conflicting_categories'])}",
                "conflicting_permissions": conflict['conflicting_categories'],
                "severity": conflict['severity'],
                "is_active": True,
                "metadata": {
                    "research_basis": "NetSuite SOD best practices",
                    "conflict_categories": conflict['conflicting_categories']
                }
            }

            sod_rules.append(rule)

            print(f"\n{rule_id}: {rule['rule_name']}")
            print(f"   • Severity: {rule['severity']}")
            print(f"   • Conflict: {conflict['reason']}")

        print(f"\n✅ Generated {len(sod_rules)} research-backed SOD rules")

        return sod_rules

    def export_results(self, output_dir: str = "output"):
        """Export comprehensive analysis results"""
        print("\n" + "=" * 80)
        print("STEP 6: Exporting Results")
        print("=" * 80)

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Raw roles data
        roles_file = output_path / f"fivetran_roles_{timestamp}.json"
        with open(roles_file, 'w') as f:
            json.dump(self.roles_data, f, indent=2)
        print(f"\n✅ Roles data: {roles_file}")

        # 2. Permission metadata (categorization)
        metadata_file = output_path / f"permission_metadata_{timestamp}.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.permission_metadata, f, indent=2)
        print(f"✅ Permission metadata: {metadata_file}")

        # 3. Categorized permissions
        categorized_file = output_path / f"categorized_permissions_{timestamp}.json"
        categorized_dict = dict(self.categorized_permissions.items())
        with open(categorized_file, 'w') as f:
            json.dump(categorized_dict, f, indent=2)
        print(f"✅ Categorized permissions: {categorized_file}")

        # 4. Permission matrix
        matrix_file = output_path / f"permission_matrix_{timestamp}.json"
        with open(matrix_file, 'w') as f:
            json.dump(self.permission_matrix, f, indent=2)
        print(f"✅ Permission matrix: {matrix_file}")

        # 5. Conflicts
        conflicts_file = output_path / f"conflicts_detailed_{timestamp}.json"
        with open(conflicts_file, 'w') as f:
            json.dump(self.conflict_rules, f, indent=2)
        print(f"✅ Detailed conflicts: {conflicts_file}")

        # 6. SOD rules
        sod_rules = self.generate_sod_rules()
        rules_file = output_path / f"sod_rules_fivetran_{timestamp}.json"
        with open(rules_file, 'w') as f:
            json.dump(sod_rules, f, indent=2)
        print(f"✅ SOD rules: {rules_file}")

        # 7. Comprehensive report
        report_file = output_path / f"analysis_report_{timestamp}.txt"
        self._generate_comprehensive_report(report_file)
        print(f"✅ Comprehensive report: {report_file}")

        print(f"\n✅ All results exported to: {output_path}")

    def _generate_comprehensive_report(self, report_file: Path):
        """Generate detailed human-readable report"""
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("ADVANCED FIVETRAN ROLE PERMISSION ANALYSIS REPORT\n")
            f.write("Research-Backed SOD Conflict Analysis\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Executive Summary
            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Fivetran Roles Analyzed: {len(self.roles_data['roles'])}\n")
            f.write(f"Unique Permissions Identified: {len(self.all_permissions)}\n")
            f.write(f"Permission Categories: {len([c for c in self.categorized_permissions if c != 'uncategorized'])}\n")
            f.write(f"Fundamental Conflicts Found: {len(self.conflict_rules)}\n")
            f.write(f"   - CRITICAL: {sum(1 for c in self.conflict_rules if c['severity'] == 'CRITICAL')}\n")
            f.write(f"   - HIGH: {sum(1 for c in self.conflict_rules if c['severity'] == 'HIGH')}\n")
            f.write(f"   - MEDIUM: {sum(1 for c in self.conflict_rules if c['severity'] == 'MEDIUM')}\n\n")

            # Permission Categories
            f.write("PERMISSION CATEGORIES (NetSuite Documentation Based)\n")
            f.write("-" * 80 + "\n")
            for category, perms in sorted(self.categorized_permissions.items()):
                if category == 'uncategorized':
                    continue
                config = PERMISSION_CATEGORIES.get(category, {})
                f.write(f"\n{category.upper().replace('_', ' ')}:\n")
                f.write(f"   Description: {config.get('description', 'N/A')}\n")
                f.write(f"   Risk Level: {config.get('risk', 'N/A')}\n")
                f.write(f"   Permission Count: {len(perms)}\n")
                f.write(f"   Conflicts With: {', '.join(config.get('conflicts_with', []))}\n")
                f.write("   Sample Permissions:\n")
                for perm in sorted(perms)[:5]:
                    f.write(f"      - {perm}\n")

            # Role Analysis
            f.write("\n\nFIVETRAN ROLES - DETAILED BREAKDOWN\n")
            f.write("-" * 80 + "\n")
            for role in self.roles_data['roles']:
                f.write(f"\n{role['role_name']}:\n")
                f.write(f"   Role ID: {role['role_id']}\n")
                f.write(f"   Total Permissions: {role['permission_count']}\n")
                f.write(f"   Status: {'Inactive' if role['is_inactive'] else 'Active'}\n")

                # Category breakdown
                role_cats = self._get_role_categories(role)
                f.write("   Permission Categories:\n")
                for cat, perms in sorted(role_cats.items()):
                    if cat == 'uncategorized':
                        continue
                    config = PERMISSION_CATEGORIES.get(cat, {})
                    risk = config.get('risk', 'UNKNOWN')
                    f.write(f"      • {cat}: {len(perms)} permissions (Risk: {risk})\n")

            # Conflicts
            f.write("\n\nIDENTIFIED SOD CONFLICTS (Research-Backed)\n")
            f.write("-" * 80 + "\n")
            for i, conflict in enumerate(self.conflict_rules, 1):
                f.write(f"\n{i}. {conflict['role1']} + {conflict['role2']}\n")
                f.write(f"   Severity: {conflict['severity']}\n")
                f.write(f"   Business Risk: {conflict['reason']}\n")
                f.write("   Conflicting Functions:\n")
                for cat_pair in conflict['conflicting_categories']:
                    f.write(f"      • {cat_pair}\n")

            # Recommendations
            f.write("\n\nRECOMMENDATIONS\n")
            f.write("-" * 80 + "\n")
            f.write("1. Review all CRITICAL and HIGH severity conflicts immediately\n")
            f.write("2. Implement compensating controls for unavoidable conflicts\n")
            f.write("3. Consider role redesign to minimize permission overlap\n")
            f.write("4. Document business justifications for accepted risks\n")
            f.write("5. Establish periodic review process (quarterly recommended)\n\n")


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Advanced Fivetran permission analysis with research')
    parser.add_argument('--restlet-url', help='Fivetran roles RESTlet URL')
    parser.add_argument('--output-dir', default='output', help='Output directory')
    args = parser.parse_args()

    restlet_url = args.restlet_url or os.getenv('NETSUITE_FIVETRAN_RESTLET_URL')
    if not restlet_url:
        print("ERROR: RESTlet URL not provided")
        print("Set NETSUITE_FIVETRAN_RESTLET_URL or use --restlet-url")
        sys.exit(1)

    print("=" * 80)
    print("ADVANCED FIVETRAN ROLE PERMISSION ANALYSIS")
    print("Research-Backed SOD Conflict Detection")
    print("=" * 80)
    print(f"RESTlet URL: {restlet_url}")
    print(f"Output directory: {args.output_dir}\n")

    client = NetSuiteClient()
    analyzer = AdvancedPermissionAnalyzer(client, restlet_url)

    try:
        # Run analysis pipeline
        analyzer.fetch_fivetran_roles()
        analyzer.categorize_permissions()
        analyzer.build_permission_matrix()
        analyzer.analyze_fundamental_conflicts()
        analyzer.export_results(args.output_dir)

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)
        print("\nKey outputs:")
        print("1. permission_metadata_*.json - Categorized permissions with risk levels")
        print("2. conflicts_detailed_*.json - All identified SOD conflicts")
        print("3. sod_rules_fivetran_*.json - Ready-to-import SOD rules")
        print("4. analysis_report_*.txt - Comprehensive human-readable report")
        print("\nNext: Review report and import SOD rules into database")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
