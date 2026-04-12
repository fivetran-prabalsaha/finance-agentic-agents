#!/usr/bin/env python3
"""
Analyze and Categorize NetSuite Permissions

Reads the extracted Fivetran role permissions and categorizes each permission
into SOD categories (transaction_entry, transaction_approval, etc.) with
their permission levels.

Usage:
    python3 scripts/analyze_and_categorize_permissions.py
"""

import json
from collections import defaultdict
from pathlib import Path

# Permission category patterns
CATEGORY_PATTERNS = {
    'transaction_entry': {
        'keywords': ['bill', 'invoice', 'payment', 'expense', 'journal', 'transaction', 'entry',
                     'cash sale', 'credit memo', 'customer deposit', 'customer refund',
                     'vendor credit', 'vendor return', 'purchase order', 'sales order',
                     'revenue recognition', 'period end', 'intercompany', 'allocate'],
        'prefixes': ['TRAN_', 'LIST_TRAN', 'REGT_'],
        'excludes': ['approve', 'approval', 'bank', 'reconcile', 'vendor', 'employee', 'setup']
    },
    'transaction_approval': {
        'keywords': ['approve', 'approval', 'authorize', 'authorization'],
        'prefixes': ['APPR_'],
        'excludes': []
    },
    'transaction_payment': {
        'keywords': ['payment', 'pay', 'check', 'ach', 'eft', 'wire', 'paycheck', 'payroll'],
        'prefixes': ['TRAN_PAY', 'REGT_PAY'],
        'excludes': ['receivable', 'deposit', 'receive']
    },
    'bank_reconciliation': {
        'keywords': ['bank', 'reconcile', 'reconciliation', 'statement'],
        'prefixes': ['TRAN_BANK', 'REPO_BANK'],
        'excludes': []
    },
    'vendor_setup': {
        'keywords': ['vendor', 'supplier', 'payee'],
        'prefixes': ['LIST_VENDOR', 'ADMI_VENDOR'],
        'excludes': ['bill', 'payment', 'transaction']
    },
    'customer_setup': {
        'keywords': ['customer', 'client'],
        'prefixes': ['LIST_CUST', 'ADMI_CUST'],
        'excludes': ['invoice', 'payment', 'transaction', 'deposit']
    },
    'user_admin': {
        'keywords': ['user', 'employee', 'access', 'permission', 'security', 'login'],
        'prefixes': ['ADMI_USER', 'ADMI_EMPLOYEE', 'ADMI_ACCESS'],
        'excludes': ['role']
    },
    'role_admin': {
        'keywords': ['role'],
        'prefixes': ['ADMI_ROLE'],
        'excludes': []
    },
    'financial_reporting': {
        'keywords': ['report', 'financial', 'graph', 'analytics', 'dashboard'],
        'prefixes': ['REPO_', 'GRAP_'],
        'excludes': []
    },
    'system_admin': {
        'keywords': ['system', 'configuration', 'setup', 'administration', 'integration',
                     'workflow', 'script', 'customization', 'saml', 'sso'],
        'prefixes': ['ADMI_', 'SETUP_'],
        'excludes': ['user', 'role', 'employee', 'vendor', 'customer']
    }
}


def categorize_permission(perm_id: str, perm_name: str) -> list[str]:
    """
    Categorize a permission based on its ID and name

    Returns list of categories (some permissions may belong to multiple)
    """
    categories = []
    perm_lower = f"{perm_id} {perm_name}".lower()

    for category, patterns in CATEGORY_PATTERNS.items():
        # Check if any exclude keyword matches
        if any(exclude in perm_lower for exclude in patterns['excludes']):
            continue

        # Check prefix match
        if any(perm_id.startswith(prefix) for prefix in patterns['prefixes']):
            categories.append(category)
            continue

        # Check keyword match
        if any(keyword in perm_lower for keyword in patterns['keywords']):
            categories.append(category)

    # Default category if none matched
    if not categories:
        # Try to infer from prefix
        if perm_id.startswith('TRAN_'):
            categories.append('transaction_entry')
        elif perm_id.startswith('LIST_'):
            categories.append('setup_lists')
        elif perm_id.startswith('REPO_'):
            categories.append('financial_reporting')
        elif perm_id.startswith('ADMI_'):
            categories.append('system_admin')
        else:
            categories.append('uncategorized')

    return categories


def determine_risk_level(categories: list[str], perm_level: str) -> str:
    """Determine risk level based on categories and permission level"""

    # High-risk categories
    high_risk_categories = {'transaction_approval', 'transaction_payment', 'user_admin', 'role_admin'}

    # Medium-risk categories
    medium_risk_categories = {'transaction_entry', 'bank_reconciliation', 'vendor_setup'}

    # Check if any high-risk category
    if any(cat in high_risk_categories for cat in categories):
        if perm_level in ['Full', 'Edit']:
            return 'HIGH'
        elif perm_level == 'Create':
            return 'MEDIUM'
        else:
            return 'LOW'

    # Check if any medium-risk category
    if any(cat in medium_risk_categories for cat in categories):
        if perm_level == 'Full':
            return 'MEDIUM'
        elif perm_level in ['Edit', 'Create']:
            return 'LOW'
        else:
            return 'MINIMAL'

    # Low-risk categories (reporting, viewing, etc.)
    if perm_level in ['Full', 'Edit']:
        return 'LOW'
    else:
        return 'MINIMAL'


def analyze_permissions(roles_file: Path) -> dict:
    """Analyze all permissions from roles file"""

    with open(roles_file) as f:
        data = json.load(f)

    # Collect all unique permissions
    permissions = {}
    permission_usage = defaultdict(lambda: {'roles': set(), 'levels': set()})

    for role in data['roles']:
        role_name = role['role_name']
        for perm in role.get('permissions', []):
            perm_id = perm['permission_id']
            perm_name = perm['permission_name']
            perm_level = perm['permission_level']

            # Track permission details
            if perm_id not in permissions:
                categories = categorize_permission(perm_id, perm_name)
                risk_level = determine_risk_level(categories, perm_level)

                permissions[perm_id] = {
                    'permission_id': perm_id,
                    'permission_name': perm_name,
                    'categories': categories,
                    'base_risk_level': risk_level
                }

            # Track usage
            permission_usage[perm_id]['roles'].add(role_name)
            permission_usage[perm_id]['levels'].add(perm_level)

    # Add usage statistics
    for perm_id, perm_data in permissions.items():
        usage = permission_usage[perm_id]
        perm_data['used_by_roles'] = list(usage['roles'])
        perm_data['levels_granted'] = sorted(usage['levels'])
        perm_data['usage_count'] = len(usage['roles'])

    return permissions


def generate_analysis_report(permissions: dict) -> str:
    """Generate a markdown report of the analysis"""

    report = []
    report.append("# NetSuite Permission Analysis & Categorization")
    report.append(f"\n**Total Permissions**: {len(permissions)}\n")

    # Category breakdown
    category_counts = defaultdict(int)
    for perm in permissions.values():
        for cat in perm['categories']:
            category_counts[cat] += 1

    report.append("## Permissions by Category\n")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        report.append(f"- **{cat}**: {count} permissions")

    # Risk level breakdown
    risk_counts = defaultdict(int)
    for perm in permissions.values():
        risk_counts[perm['base_risk_level']] += 1

    report.append("\n## Permissions by Risk Level\n")
    for risk, count in sorted(risk_counts.items(), key=lambda x: ['HIGH', 'MEDIUM', 'LOW', 'MINIMAL'].index(x[0]) if x[0] in ['HIGH', 'MEDIUM', 'LOW', 'MINIMAL'] else 999):
        report.append(f"- **{risk}**: {count} permissions")

    # High-risk permissions
    report.append("\n## High-Risk Permissions (Sample)\n")
    high_risk = [p for p in permissions.values() if p['base_risk_level'] == 'HIGH']
    for perm in sorted(high_risk, key=lambda x: -x['usage_count'])[:20]:
        report.append(f"\n### {perm['permission_name']}")
        report.append(f"- **ID**: `{perm['permission_id']}`")
        report.append(f"- **Categories**: {', '.join(perm['categories'])}")
        report.append(f"- **Levels Granted**: {', '.join(perm['levels_granted'])}")
        report.append(f"- **Used by {perm['usage_count']} roles**")

    # SOD-relevant categories
    report.append("\n## SOD-Relevant Permission Categories\n")

    sod_categories = [
        'transaction_entry',
        'transaction_approval',
        'transaction_payment',
        'bank_reconciliation',
        'vendor_setup',
        'user_admin',
        'role_admin'
    ]

    for cat in sod_categories:
        cat_perms = [p for p in permissions.values() if cat in p['categories']]
        report.append(f"\n### {cat.replace('_', ' ').title()} ({len(cat_perms)} permissions)\n")

        # Show top 10 by usage
        for perm in sorted(cat_perms, key=lambda x: -x['usage_count'])[:10]:
            report.append(f"- **{perm['permission_name']}** (`{perm['permission_id']}`) - {', '.join(perm['levels_granted'])} - Used by {perm['usage_count']} roles")

    return '\n'.join(report)


def main():
    """Main execution"""
    # Find most recent roles file
    roles_files = sorted(Path('output').glob('fivetran_roles_*.json'), reverse=True)
    if not roles_files:
        print("❌ No Fivetran roles file found in output/")
        return

    roles_file = roles_files[0]
    print(f"📖 Reading: {roles_file}")

    # Analyze permissions
    permissions = analyze_permissions(roles_file)
    print(f"✅ Analyzed {len(permissions)} unique permissions")

    # Save detailed mapping
    output_file = Path('data/netsuite_permission_mapping.json')
    with open(output_file, 'w') as f:
        json.dump({
            'version': '1.0',
            'generated_at': '2026-02-12',
            'source_file': str(roles_file),
            'total_permissions': len(permissions),
            'permissions': permissions
        }, f, indent=2)
    print(f"✅ Saved detailed mapping: {output_file}")

    # Generate report
    report = generate_analysis_report(permissions)
    report_file = Path('docs/PERMISSION_ANALYSIS.md')
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"✅ Generated analysis report: {report_file}")

    # Print summary
    print("\n" + "="*60)
    print("PERMISSION CATEGORIZATION SUMMARY")
    print("="*60)

    category_counts = defaultdict(int)
    for perm in permissions.values():
        for cat in perm['categories']:
            category_counts[cat] += 1

    print("\nBy Category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = (count / len(permissions)) * 100
        print(f"  {cat:30s}: {count:3d} ({pct:5.1f}%)")

    risk_counts = defaultdict(int)
    for perm in permissions.values():
        risk_counts[perm['base_risk_level']] += 1

    print("\nBy Risk Level:")
    for risk in ['HIGH', 'MEDIUM', 'LOW', 'MINIMAL']:
        count = risk_counts.get(risk, 0)
        pct = (count / len(permissions)) * 100
        print(f"  {risk:10s}: {count:3d} ({pct:5.1f}%)")

    # SOD-relevant stats
    sod_categories = [
        'transaction_entry', 'transaction_approval', 'transaction_payment',
        'bank_reconciliation', 'vendor_setup', 'user_admin', 'role_admin'
    ]

    sod_count = len([p for p in permissions.values() if any(cat in sod_categories for cat in p['categories'])])
    print(f"\nSOD-Relevant Permissions: {sod_count} ({(sod_count/len(permissions))*100:.1f}%)")

    print("\n" + "="*60)
    print("✅ Analysis Complete!")
    print("="*60)


if __name__ == '__main__':
    main()
