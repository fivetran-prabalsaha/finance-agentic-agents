#!/usr/bin/env python3
"""
Enhanced Access Request Analysis with Level-Based SOD and Compensating Controls

Purpose:
1. Analyze NetSuite access requests with permission LEVEL granularity
2. Validate against job role context
3. Generate resolution options with compensating controls
4. Calculate residual risk after controls applied

Features:
- Level-based conflict detection (View, Edit, Create, Full)
- Job role validation
- Compensating control recommendations
- Risk scoring (inherent → residual)
- Business-aligned recommendations

Author: Prabal Saha
Date: 2026-02-12
Version: 2.0 (Level-Based)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.netsuite_client import NetSuiteClient


class LevelBasedSODAnalyzer:
    """
    Enhanced SOD analyzer with level-based conflict detection
    """

    def __init__(self, config_dir: Path):
        """Initialize with configuration files"""
        self.config_dir = config_dir

        # Load all configurations
        self.unified_config = self._load_json('netsuite_sod_config_unified.json')
        self.job_role_mappings = self._load_json('job_role_mappings.json')
        self.compensating_controls = self._load_json('compensating_controls.json')

        # Extract key data
        self.permission_levels = self.unified_config['permission_levels']
        self.permission_categories = self.unified_config['permission_categories']
        self.conflict_rules = self.unified_config['conflict_rules']
        self.role_filter = self.unified_config['role_filter']

        # Runtime data
        self.roles_data = None
        self.categorized_permissions = {}
        self.permission_metadata = {}

    def _load_json(self, filename: str) -> dict:
        """Load JSON configuration file"""
        filepath = self.config_dir / filename
        try:
            with open(filepath) as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Configuration file not found: {filepath}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {filepath}: {e}")
            sys.exit(1)

    def fetch_roles_from_netsuite(self, client: NetSuiteClient, restlet_url: str) -> dict:
        """Fetch roles from NetSuite with filtering"""
        print("=" * 80)
        print("STEP 1: Fetching Roles from NetSuite")
        print("=" * 80)

        role_prefix = self.role_filter['role_name_prefix']
        exclude_suffixes = self.role_filter['exclude_suffixes']

        print("\nRole filter:")
        print(f"   • Prefix: {role_prefix}")
        print(f"   • Exclude suffixes: {', '.join(exclude_suffixes)}")

        # Call RESTlet
        payload = {
            "includePermissions": True,
            "includeInactive": False,
            "rolePrefix": role_prefix
        }

        response = client.session.post(
            restlet_url,
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise Exception(f"RESTlet failed: {response.status_code} - {response.text}")

        result = response.json()
        if not result.get('success'):
            raise Exception(f"RESTlet error: {result.get('error')}")

        self.roles_data = result['data']

        # Filter out excluded suffixes
        original_count = len(self.roles_data['roles'])
        self.roles_data['roles'] = [
            role for role in self.roles_data['roles']
            if not any(role['role_name'].endswith(suffix) for suffix in exclude_suffixes)
        ]
        filtered_count = len(self.roles_data['roles'])
        excluded_count = original_count - filtered_count

        print("\n✅ Successfully fetched roles")
        print(f"   • Total roles: {original_count}")
        print(f"   • Excluded (OLD, etc.): {excluded_count}")
        print(f"   • Active roles for analysis: {filtered_count}")

        return self.roles_data

    def categorize_permissions(self):
        """Categorize permissions by function"""
        print("\n" + "=" * 80)
        print("STEP 2: Categorizing Permissions")
        print("=" * 80)

        # Collect all unique permissions
        all_permissions = set()
        for role in self.roles_data['roles']:
            for perm in role.get('permissions', []):
                all_permissions.add(perm['permission_name'])

        print(f"\nTotal unique permissions: {len(all_permissions)}")

        categorized_count = 0
        for perm_name in sorted(all_permissions):
            categorized = False

            for category, config in self.permission_categories.items():
                # Check exact keyword match
                if any(keyword.lower() == perm_name.lower() for keyword in config.get('keywords', [])):
                    self.categorized_permissions[perm_name] = category
                    self.permission_metadata[perm_name] = {
                        'category': category,
                        'base_risk': config['base_risk'],
                        'base_risk_score': config['base_risk_score'],
                        'conflicts_with': config['conflicts_with']
                    }
                    categorized = True
                    categorized_count += 1
                    break

                # Check regex patterns
                if not categorized and 'patterns' in config:
                    for pattern in config['patterns']:
                        try:
                            if re.search(pattern, perm_name, re.IGNORECASE):
                                self.categorized_permissions[perm_name] = category
                                self.permission_metadata[perm_name] = {
                                    'category': category,
                                    'base_risk': config['base_risk'],
                                    'base_risk_score': config['base_risk_score'],
                                    'conflicts_with': config['conflicts_with']
                                }
                                categorized = True
                                categorized_count += 1
                                break
                        except re.error:
                            pass

                if categorized:
                    break

            # Mark as uncategorized if not found
            if not categorized:
                self.categorized_permissions[perm_name] = 'uncategorized'
                self.permission_metadata[perm_name] = {
                    'category': 'uncategorized',
                    'base_risk': 'LOW',
                    'base_risk_score': 20,
                    'conflicts_with': []
                }

        print("✅ Categorization complete")
        print(f"   • Categorized: {categorized_count} ({(categorized_count/len(all_permissions)*100):.1f}%)")
        print(f"   • Uncategorized: {len(all_permissions) - categorized_count}")

    def analyze_role_pair_with_levels(self, role1: dict, role2: dict) -> list[dict]:
        """
        Analyze role pair with LEVEL-based conflict detection

        Returns list of conflicts with level details
        """
        conflicts = []

        role1_name = role1['role_name']
        role2_name = role2['role_name']

        # Get permissions by category for each role
        role1_perms_by_cat = defaultdict(list)
        role2_perms_by_cat = defaultdict(list)

        for perm in role1.get('permissions', []):
            perm_name = perm['permission_name']
            metadata = self.permission_metadata.get(perm_name, {})
            category = metadata.get('category', 'uncategorized')

            role1_perms_by_cat[category].append({
                'name': perm_name,
                'level': perm['permission_level'],
                'level_value': perm['permission_level_value'],
                'category': category,
                'metadata': metadata
            })

        for perm in role2.get('permissions', []):
            perm_name = perm['permission_name']
            metadata = self.permission_metadata.get(perm_name, {})
            category = metadata.get('category', 'uncategorized')

            role2_perms_by_cat[category].append({
                'name': perm_name,
                'level': perm['permission_level'],
                'level_value': perm['permission_level_value'],
                'category': category,
                'metadata': metadata
            })

        # Check each conflict rule
        for _rule_id, rule in self.conflict_rules.items():
            cat1 = rule['category1']
            cat2 = rule['category2']

            # Get permissions for these categories
            cat1_perms = role1_perms_by_cat.get(cat1, [])
            cat2_perms = role2_perms_by_cat.get(cat2, [])

            # Also check reverse (cat2 in role1, cat1 in role2)
            cat1_perms_reverse = role2_perms_by_cat.get(cat1, [])
            cat2_perms_reverse = role1_perms_by_cat.get(cat2, [])

            # Analyze all permission pairs
            pairs_to_check = []

            # Forward direction
            for perm1 in cat1_perms:
                for perm2 in cat2_perms:
                    pairs_to_check.append((perm1, perm2, role1_name, role2_name))

            # Reverse direction
            for perm1 in cat1_perms_reverse:
                for perm2 in cat2_perms_reverse:
                    pairs_to_check.append((perm1, perm2, role2_name, role1_name))

            for perm1, perm2, r1, r2 in pairs_to_check:
                conflict = self._check_level_conflict(perm1, perm2, rule, r1, r2)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _check_level_conflict(self, perm1: dict, perm2: dict, rule: dict,
                             role1_name: str, role2_name: str) -> dict | None:
        """
        Check if two permissions conflict based on level matrix

        Returns conflict dict if found, None otherwise
        """
        level1 = perm1['level_value']
        level2 = perm2['level_value']

        # Get conflict matrix
        matrix = rule['level_conflict_matrix']['matrix']

        # Look up severity
        if level1 >= len(matrix) or level2 >= len(matrix[0]):
            return None

        severity = matrix[level1][level2]

        if severity == "OK":
            return None

        # Calculate risk scores
        base_risk1 = perm1['metadata'].get('base_risk_score', 50)
        base_risk2 = perm2['metadata'].get('base_risk_score', 50)

        # Get level multipliers from category config
        cat1 = perm1['category']
        cat2 = perm2['category']

        cat1_config = self.permission_categories.get(cat1, {})
        cat2_config = self.permission_categories.get(cat2, {})

        level1_multiplier = cat1_config.get('level_risk_adjustments', {}).get(str(level1), {}).get('multiplier', 1.0)
        level2_multiplier = cat2_config.get('level_risk_adjustments', {}).get(str(level2), {}).get('multiplier', 1.0)

        # Calculate inherent risk
        inherent_risk = (base_risk1 * level1_multiplier + base_risk2 * level2_multiplier) / 2

        return {
            'rule_id': rule['rule_id'],
            'principle': rule['principle'],
            'description': rule['description'],
            'role1': role1_name,
            'role2': role2_name,
            'permission1': perm1['name'],
            'permission1_level': perm1['level'],
            'permission1_level_value': level1,
            'permission1_category': cat1,
            'permission2': perm2['name'],
            'permission2_level': perm2['level'],
            'permission2_level_value': level2,
            'permission2_category': cat2,
            'severity': severity,
            'inherent_risk': round(inherent_risk, 2),
            'matrix_position': [level1, level2],
            'resolution_strategies': rule['resolution_strategies'].get(severity, {})
        }

    def analyze_all_role_pairs(self) -> list[dict]:
        """Analyze all role pairs for conflicts"""
        print("\n" + "=" * 80)
        print("STEP 3: Analyzing Role Pairs with Level-Based Detection")
        print("=" * 80)

        all_conflicts = []
        roles = self.roles_data['roles']

        total_pairs = len(roles) * (len(roles) - 1) // 2
        print(f"\nAnalyzing {len(roles)} roles ({total_pairs} pairs)...")

        analyzed = 0
        for i, role1 in enumerate(roles):
            for role2 in roles[i+1:]:
                conflicts = self.analyze_role_pair_with_levels(role1, role2)
                all_conflicts.extend(conflicts)
                analyzed += 1

                if analyzed % 20 == 0:
                    print(f"   Analyzed {analyzed}/{total_pairs} pairs... ({len(all_conflicts)} conflicts so far)")

        # Summarize by severity
        severity_counts = defaultdict(int)
        for conflict in all_conflicts:
            severity_counts[conflict['severity']] += 1

        print("\n✅ Analysis complete")
        print(f"   • Total conflicts found: {len(all_conflicts)}")
        print(f"   • CRITICAL: {severity_counts.get('CRIT', 0)}")
        print(f"   • HIGH: {severity_counts.get('HIGH', 0)}")
        print(f"   • MEDIUM: {severity_counts.get('MED', 0)}")
        print(f"   • LOW: {severity_counts.get('LOW', 0)}")

        return all_conflicts

    def generate_resolution_for_conflict(self, conflict: dict) -> dict:
        """Generate resolution options with compensating controls"""
        severity = conflict['severity']
        resolution_strategies = conflict['resolution_strategies']

        # Get appropriate control package
        control_packages = self.compensating_controls['control_packages']

        if severity == 'CRIT':
            package = control_packages['critical_risk_package']
        elif severity == 'HIGH':
            package = control_packages['high_risk_package']
        elif severity == 'MED':
            package = control_packages['medium_risk_package']
        else:  # LOW
            package = control_packages['low_risk_package']

        # Get control details
        controls_detail = []
        for control_id in package['included_controls']:
            if control_id in self.compensating_controls['controls']:
                control = self.compensating_controls['controls'][control_id]
                controls_detail.append({
                    'control_id': control_id,
                    'name': control['name'],
                    'type': control['type'],
                    'risk_reduction': control['effectiveness']['risk_reduction_percentage'],
                    'description': control['description']
                })

        # Calculate residual risk
        inherent_risk = conflict['inherent_risk']
        total_risk_reduction = min(package['total_risk_reduction'], 95) / 100
        residual_risk = round(inherent_risk * (1 - total_risk_reduction), 2)

        return {
            'conflict_id': f"{conflict['rule_id']}-{conflict['role1'][:10]}-{conflict['role2'][:10]}",
            'severity': severity,
            'inherent_risk': inherent_risk,
            'residual_risk': residual_risk,
            'risk_reduction_percentage': package['total_risk_reduction'],
            'recommended_action': resolution_strategies.get('action', 'REVIEW'),
            'resolution_description': resolution_strategies.get('description', ''),
            'control_package': {
                'package_id': package['package_id'],
                'package_name': package['name'],
                'included_controls': controls_detail,
                'estimated_annual_cost': package.get('estimated_annual_cost', 'N/A'),
                'implementation_time_hours': package.get('implementation_time_hours', 0)
            },
            'resolution_options': resolution_strategies.get('resolution_options', [])
        }

    def validate_job_role(self, job_title: str, requested_roles: list[str]) -> dict:
        """Validate if role combination is typical for job title"""
        print("\n" + "=" * 80)
        print("STEP 4: Job Role Validation")
        print("=" * 80)

        print(f"\nJob Title: {job_title}")
        print(f"Requested Roles: {', '.join(requested_roles)}")

        # Find job role in mappings
        job_role_key = job_title.lower().replace(' ', '_').replace('/', '_')

        if job_role_key not in self.job_role_mappings['job_roles']:
            print("⚠️  Job title not found in mappings")
            return {
                'found': False,
                'is_typical_combination': False,
                'recommendation': 'MANUAL_REVIEW',
                'reason': 'Job title not in standard mappings'
            }

        job_role = self.job_role_mappings['job_roles'][job_role_key]

        # Check if requested roles are typical
        typical_roles = [r['role'] for r in job_role.get('typical_netsuite_roles', [])]

        all(role in typical_roles for role in requested_roles)

        # Find acceptable combinations
        acceptable_combos = job_role.get('acceptable_role_combinations', [])
        matching_combo = None

        for combo in acceptable_combos:
            if set(combo['roles']) == set(requested_roles):
                matching_combo = combo
                break

        if matching_combo:
            print("✅ Role combination found in acceptable list")
            print(f"   Business justification: {matching_combo.get('business_justification', 'N/A')}")
            print(f"   Requires compensating controls: {matching_combo.get('requires_compensating_controls', False)}")

            return {
                'found': True,
                'is_typical_combination': True,
                'requires_compensating_controls': matching_combo.get('requires_compensating_controls', False),
                'typical_controls': matching_combo.get('typical_controls', []),
                'business_justification': matching_combo.get('business_justification', ''),
                'recommendation': 'APPROVE_WITH_CONDITIONS' if matching_combo.get('requires_compensating_controls') else 'APPROVE'
            }
        else:
            print("⚠️  Role combination not in acceptable list")
            print(f"   Typical roles for {job_title}: {', '.join(typical_roles)}")

            return {
                'found': True,
                'is_typical_combination': False,
                'typical_roles': typical_roles,
                'recommendation': 'MANUAL_REVIEW',
                'reason': 'Requested combination not standard for this job title'
            }

    def analyze_access_request(self, job_title: str, requested_roles: list[str]) -> dict:
        """
        Complete access request analysis with job role context

        Args:
            job_title: User's job title (e.g., "Revenue Director")
            requested_roles: List of NetSuite role names

        Returns:
            Complete analysis with recommendations
        """
        print("=" * 80)
        print("ACCESS REQUEST ANALYSIS")
        print("=" * 80)
        print(f"\nJob Title: {job_title}")
        print(f"Requested Roles: {', '.join(requested_roles)}")

        # Find requested roles in data
        requested_role_objects = []
        for role_name in requested_roles:
            for role in self.roles_data['roles']:
                if role['role_name'] == role_name:
                    requested_role_objects.append(role)
                    break

        if len(requested_role_objects) != len(requested_roles):
            print("\n❌ ERROR: Some requested roles not found in NetSuite data")
            return {'error': 'Roles not found'}

        # Analyze conflicts between requested roles
        all_conflicts = []
        for i, role1 in enumerate(requested_role_objects):
            for role2 in requested_role_objects[i+1:]:
                conflicts = self.analyze_role_pair_with_levels(role1, role2)
                all_conflicts.extend(conflicts)

        print(f"\n✅ Conflict analysis complete: {len(all_conflicts)} conflicts found")

        # Generate resolutions for each conflict
        resolutions = []
        for conflict in all_conflicts:
            resolution = self.generate_resolution_for_conflict(conflict)
            resolutions.append(resolution)

        # Validate job role
        job_role_validation = self.validate_job_role(job_title, requested_roles)

        # Determine overall recommendation
        if not all_conflicts:
            overall_recommendation = "APPROVE"
            overall_risk = "LOW"
        elif job_role_validation.get('is_typical_combination') and job_role_validation.get('requires_compensating_controls'):
            overall_recommendation = "APPROVE_WITH_COMPENSATING_CONTROLS"
            max_risk = max([c['inherent_risk'] for c in all_conflicts])
            overall_risk = "CRITICAL" if max_risk > 75 else "HIGH" if max_risk > 50 else "MEDIUM"
        else:
            overall_recommendation = "MANUAL_REVIEW"
            overall_risk = "HIGH"

        return {
            'job_title': job_title,
            'requested_roles': requested_roles,
            'conflicts_found': len(all_conflicts),
            'conflicts': all_conflicts,
            'resolutions': resolutions,
            'job_role_validation': job_role_validation,
            'overall_recommendation': overall_recommendation,
            'overall_risk': overall_risk,
            'timestamp': datetime.utcnow().isoformat()
        }


def main():
    parser = argparse.ArgumentParser(
        description='Enhanced access request analysis with level-based SOD'
    )
    parser.add_argument('--job-title', required=True, help='User job title')
    parser.add_argument('--requested-roles', required=True,
                       help='Comma-separated list of NetSuite role names')
    parser.add_argument('--restlet-url', help='NetSuite RESTlet URL')
    parser.add_argument('--output', default='output/access_request_analysis.json',
                       help='Output file path')
    parser.add_argument('--mode', choices=['single-request', 'all-roles'],
                       default='single-request',
                       help='Analysis mode: single-request or all-roles')

    args = parser.parse_args()

    # Initialize analyzer
    config_dir = Path(__file__).parent.parent / 'data'
    analyzer = LevelBasedSODAnalyzer(config_dir)

    # Get RESTlet URL
    restlet_url = args.restlet_url or os.getenv('NETSUITE_FIVETRAN_RESTLET_URL')
    if not restlet_url:
        print("ERROR: RESTlet URL required (--restlet-url or NETSUITE_FIVETRAN_RESTLET_URL)")
        sys.exit(1)

    # Initialize NetSuite client
    client = NetSuiteClient()

    # Fetch roles from NetSuite
    analyzer.fetch_roles_from_netsuite(client, restlet_url)

    # Categorize permissions
    analyzer.categorize_permissions()

    if args.mode == 'single-request':
        # Analyze specific access request
        requested_roles = [r.strip() for r in args.requested_roles.split(',')]

        result = analyzer.analyze_access_request(args.job_title, requested_roles)

        # Save output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'=' * 80}")
        print("ANALYSIS COMPLETE")
        print(f"{'=' * 80}")
        print(f"\n✅ Results saved to: {output_path}")

        if 'error' in result:
            print(f"\n❌ Analysis Error: {result['error']}")
            sys.exit(1)

        print(f"\nOverall Recommendation: {result['overall_recommendation']}")
        print(f"Overall Risk: {result['overall_risk']}")
        print(f"Conflicts Found: {result['conflicts_found']}")

    else:
        # Analyze all role pairs
        all_conflicts = analyzer.analyze_all_role_pairs()

        # Generate resolutions
        print("\n" + "=" * 80)
        print("STEP 4: Generating Resolutions with Compensating Controls")
        print("=" * 80)

        resolutions = []
        for conflict in all_conflicts:
            resolution = analyzer.generate_resolution_for_conflict(conflict)
            resolutions.append(resolution)

        print(f"\n✅ Generated {len(resolutions)} resolution strategies")

        # Save output
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = {
            'analysis_type': 'all_roles',
            'total_conflicts': len(all_conflicts),
            'conflicts': all_conflicts,
            'resolutions': resolutions,
            'timestamp': datetime.utcnow().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n{'=' * 80}")
        print("ANALYSIS COMPLETE")
        print(f"{'=' * 80}")
        print(f"\n✅ Results saved to: {output_path}")


if __name__ == '__main__':
    main()
