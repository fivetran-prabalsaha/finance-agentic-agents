#!/usr/bin/env python3
"""
Comprehensive Internal SOD Analysis for All Roles

Analyzes all roles in the database for internal segregation of duties conflicts.
Identifies maker-checker violations, 3-way match bypasses, and other risky
permission combinations within single roles.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from models.database_config import DatabaseConfig


class InternalSODAnalyzer:
    """Analyzes roles for internal SOD conflicts"""

    def __init__(self):
        self.db_config = DatabaseConfig()
        self.session = self.db_config.get_session()

        # Define conflict patterns
        self.conflict_patterns = self._load_conflict_patterns()

    def _load_conflict_patterns(self) -> dict:
        """Define internal SOD conflict patterns"""
        return {
            "maker_checker": {
                "name": "Maker-Checker Violation",
                "severity": "CRITICAL",
                "patterns": [
                    # AP conflicts
                    (["Bills", "TRAN_VENDBILL"], ["Edit", "Create"],
                     ["Pay Bills", "TRAN_VENDPYMT"], ["Full", "Edit"]),
                    (["Bills", "TRAN_VENDBILL"], ["Edit", "Create"],
                     ["Vendor Bill Approval", "TRAN_VENDBILLAPPRV"], ["Full", "Edit"]),

                    # AR conflicts
                    (["Invoice", "TRAN_CUSTINVC"], ["Edit", "Create"],
                     ["Invoice Approval", "TRAN_CUSTINVCAPPRV"], ["Full", "Edit"]),
                    (["Cash Sale", "TRAN_CASHSALE"], ["Edit", "Create"],
                     ["Cash Sale Approval", "TRAN_CASHSALEAPPRV"], ["Full", "Edit"]),

                    # JE conflicts
                    (["Make Journal Entry", "TRAN_JOURNAL"], ["Edit", "Create"],
                     ["Journal Approval", "TRAN_JOURNALAPPRV"], ["Full", "Edit"]),

                    # Purchase Order conflicts
                    (["Purchase Order", "TRAN_PURCHORD"], ["Edit", "Create"],
                     ["Purchase Order Approval", "TRAN_PURCHORDAPPRV"], ["Full", "Edit"]),
                ]
            },
            "three_way_match": {
                "name": "3-Way Match Bypass",
                "severity": "HIGH",
                "patterns": [
                    # Can receive items AND create bills
                    (["Item Receipt", "TRAN_ITEMRCPT"], ["Edit", "Create"],
                     ["Bills", "TRAN_VENDBILL"], ["Edit", "Create"]),

                    # Can create PO AND receive items
                    (["Purchase Order", "TRAN_PURCHORD"], ["Edit", "Create"],
                     ["Item Receipt", "TRAN_ITEMRCPT"], ["Edit", "Create"]),
                ]
            },
            "full_cycle": {
                "name": "Full Transaction Cycle Control",
                "severity": "HIGH",
                "patterns": [
                    # PO → Receipt → Bill → Payment
                    (["Purchase Order", "TRAN_PURCHORD"], ["Edit", "Create", "Full"],
                     ["Item Receipt", "TRAN_ITEMRCPT"], ["Edit", "Create", "Full"],
                     ["Bills", "TRAN_VENDBILL"], ["Edit", "Create", "Full"],
                     ["Pay Bills", "TRAN_VENDPYMT"], ["Edit", "Create", "Full"]),

                    # Sales Order → Invoice → Payment
                    (["Sales Order", "TRAN_SALESORD"], ["Edit", "Create", "Full"],
                     ["Invoice", "TRAN_CUSTINVC"], ["Edit", "Create", "Full"],
                     ["Customer Payment", "TRAN_CUSTPYMT"], ["Edit", "Create", "Full"]),
                ]
            },
            "cash_handling": {
                "name": "Cash Handling Conflicts",
                "severity": "CRITICAL",
                "patterns": [
                    # Can create cash sales AND process payments
                    (["Cash Sale", "TRAN_CASHSALE"], ["Edit", "Create"],
                     ["Customer Payment", "TRAN_CUSTPYMT"], ["Edit", "Create"]),

                    # Can write checks AND reconcile bank
                    (["Check", "TRAN_CHECK"], ["Edit", "Create"],
                     ["Bank Reconciliation", "TRAN_RNCNCL"], ["Edit", "Create"]),
                ]
            },
            "admin_financial": {
                "name": "Admin + Financial Access",
                "severity": "CRITICAL",
                "patterns": [
                    # Script development + financial transactions
                    (["SuiteScript", "ADMI_SCRIPTDEPLOY"], ["Edit", "Create", "Full"],
                     ["Bills", "TRAN_VENDBILL"], ["Edit", "Create"]),

                    # User admin + financial
                    (["Employee Record", "LIST_EMPLOYEE_RECORD"], ["Edit", "Create", "Full"],
                     ["Pay Bills", "TRAN_VENDPYMT"], ["Edit", "Create", "Full"]),
                ]
            }
        }

    def analyze_all_roles(self) -> dict:
        """Analyze all roles for internal conflicts"""
        print("=" * 80)
        print("COMPREHENSIVE INTERNAL SOD ANALYSIS")
        print("=" * 80)
        print()

        # Fetch all roles
        query = text("""
            SELECT role_id, role_name, is_custom, permissions
            FROM roles
            WHERE json_array_length(permissions) > 0
            ORDER BY json_array_length(permissions) DESC
        """)

        result = self.session.execute(query)
        roles = result.fetchall()

        print(f"Analyzing {len(roles)} roles...\n")

        all_results = []

        for role_id, role_name, is_custom, permissions in roles:
            print(f"Analyzing: {role_name}")

            # Convert permissions if needed
            if isinstance(permissions, str):
                permissions = json.loads(permissions)

            conflicts = self.analyze_role(role_name, permissions)

            all_results.append({
                'role_id': role_id,
                'role_name': role_name,
                'is_custom': is_custom,
                'permission_count': len(permissions),
                'conflicts': conflicts
            })

        return self._generate_report(all_results)

    def analyze_role(self, role_name: str, permissions: list[dict]) -> list[dict]:
        """Analyze a single role for internal conflicts"""
        conflicts = []

        # Build permission index for fast lookup
        perm_index = {}
        for perm in permissions:
            perm_name = perm.get('permission_name', '')
            perm_id = perm.get('permission', '')
            level = perm.get('level', '')

            perm_index[perm_name] = level
            perm_index[perm_id] = level

        # Check each conflict pattern
        for category, config in self.conflict_patterns.items():
            for pattern in config['patterns']:
                if self._matches_pattern(perm_index, pattern):
                    conflicts.append({
                        'category': category,
                        'name': config['name'],
                        'severity': config['severity'],
                        'pattern': self._describe_pattern(pattern)
                    })

        return conflicts

    def _matches_pattern(self, perm_index: dict, pattern: tuple) -> bool:
        """Check if permissions match a conflict pattern"""
        # Pattern format: (perm1_names, perm1_levels, perm2_names, perm2_levels, ...)

        for i in range(0, len(pattern), 2):
            if i + 1 >= len(pattern):
                break

            perm_names = pattern[i]
            required_levels = pattern[i + 1]

            # Check if any of the permission names exist with required level
            found = False
            for perm_name in perm_names:
                if perm_name in perm_index:
                    level = perm_index[perm_name]
                    if level in required_levels:
                        found = True
                        break

            if not found:
                return False

        return True

    def _describe_pattern(self, pattern: tuple) -> str:
        """Create human-readable description of pattern"""
        descriptions = []
        for i in range(0, len(pattern), 2):
            if i + 1 >= len(pattern):
                break
            perm_names = pattern[i]
            levels = pattern[i + 1]
            descriptions.append(f"{perm_names[0]} ({'/'.join(levels)})")

        return " + ".join(descriptions)

    def _generate_report(self, results: list[dict]) -> dict:
        """Generate comprehensive report"""
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print()

        # Summary statistics
        total_roles = len(results)
        roles_with_conflicts = sum(1 for r in results if r['conflicts'])
        total_conflicts = sum(len(r['conflicts']) for r in results)

        # Group by severity
        critical_roles = [r for r in results if any(c['severity'] == 'CRITICAL' for c in r['conflicts'])]
        high_roles = [r for r in results if any(c['severity'] == 'HIGH' for c in r['conflicts']) and r not in critical_roles]

        print("📊 SUMMARY")
        print(f"   • Total Roles Analyzed: {total_roles}")
        print(f"   • Roles with Conflicts: {roles_with_conflicts} ({roles_with_conflicts*100//total_roles}%)")
        print(f"   • Total Conflicts Found: {total_conflicts}")
        print(f"   • Critical Risk Roles: {len(critical_roles)}")
        print(f"   • High Risk Roles: {len(high_roles)}")
        print()

        # Top offenders
        print("🔴 TOP 10 ROLES BY CONFLICT COUNT:")
        sorted_results = sorted(results, key=lambda x: len(x['conflicts']), reverse=True)
        for i, role in enumerate(sorted_results[:10], 1):
            if role['conflicts']:
                print(f"{i:2}. {role['role_name']:45} | {len(role['conflicts'])} conflicts")
        print()

        # Critical roles
        if critical_roles:
            print("🚨 CRITICAL RISK ROLES:")
            for role in critical_roles[:10]:
                print(f"\n• {role['role_name']}")
                print(f"  Permissions: {role['permission_count']}")
                critical_conflicts = [c for c in role['conflicts'] if c['severity'] == 'CRITICAL']
                for conflict in critical_conflicts:
                    print(f"  - {conflict['name']}: {conflict['pattern']}")

        print("\n" + "=" * 80)

        # Save detailed report
        self._save_detailed_report(results)

        return {
            'total_roles': total_roles,
            'roles_with_conflicts': roles_with_conflicts,
            'total_conflicts': total_conflicts,
            'critical_roles': len(critical_roles),
            'high_roles': len(high_roles),
            'results': results
        }

    def _save_detailed_report(self, results: list[dict]):
        """Save detailed report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output/role_analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        report_file = output_dir / f"all_roles_internal_sod_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Detailed report saved to: {report_file}")


if __name__ == "__main__":
    analyzer = InternalSODAnalyzer()
    results = analyzer.analyze_all_roles()
