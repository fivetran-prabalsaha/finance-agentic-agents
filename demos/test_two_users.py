"""
Test SOD Analysis for Two Specific Users: Prabal Saha and Robin Tuner

This script:
1. Fetches data for two specific users from NetSuite
2. Analyzes their roles and permissions against SOD rules
3. Uses Claude Opus for deep reasoning and recommendations
4. Generates a detailed SOD conflict report
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from services.netsuite_client import NetSuiteClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SODReportGenerator:
    """Generate detailed SOD conflict reports for specific users"""

    def __init__(self):
        self.netsuite_client = NetSuiteClient()
        self.llm_opus = ChatAnthropic(model="claude-opus-4-6", temperature=0)

        # Load SOD rules
        rules_path = Path(__file__).parent.parent / "database" / "seed_data" / "sod_rules.json"
        with open(rules_path) as f:
            self.sod_rules = json.load(f)

        logger.info(f"Loaded {len(self.sod_rules)} SOD rules")

    def fetch_users_by_name(self, search_value: str, fetch_permissions: bool = True) -> list[dict[str, Any]]:
        """
        Fetch all matching users from NetSuite by name or email using search RESTlet

        Returns ALL matches when there are duplicates.

        Args:
            search_value: Name (e.g., "Prabal Saha") or email (e.g., "john@company.com")
            fetch_permissions: If True and permissions are empty, fetch from main RESTlet

        Returns:
            List of user data dictionaries
        """
        logger.info(f"Searching for user: {search_value}")

        # Determine search type based on input
        search_type = 'email' if '@' in search_value else 'both'

        # Use the new search_users method for targeted lookup
        result = self.netsuite_client.search_users(
            search_value=search_value,
            search_type=search_type,
            include_permissions=True,
            include_inactive=False
        )

        if not result.get('success'):
            logger.error(f"Failed to search for user: {result.get('error')}")
            return []

        users = result['data']['users']

        if len(users) == 0:
            logger.warning(f"User '{search_value}' not found")
            logger.info("Tip: Check the exact name or email in NetSuite")
            return []

        elif len(users) == 1:
            logger.info(f"✓ Found 1 user: {users[0].get('name')} ({users[0].get('email')})")
        else:
            # Multiple matches - return ALL of them
            logger.warning(f"Found {len(users)} users matching '{search_value}'")
            for i, user in enumerate(users, 1):
                logger.info(f"  {i}. {user.get('name')} ({user.get('email')}) - User ID: {user.get('user_id')}")
            logger.info(f"✓ Will analyze all {len(users)} records separately")

        # Check and fetch permissions for each user
        for idx, user in enumerate(users):
            has_permissions = False
            for role in user.get('roles', []):
                if len(role.get('permissions', [])) > 0:
                    has_permissions = True
                    break

            # If no permissions and fetch_permissions is True, get from main RESTlet
            if not has_permissions and fetch_permissions and user.get('email'):
                logger.info(f"Fetching detailed permissions for {user.get('name')}...")
                detailed_user = self.netsuite_client.get_user_by_email(user['email'])
                if detailed_user:
                    logger.info("✓ Fetched detailed permissions")
                    # Replace the user in the list with the detailed version
                    users[idx] = detailed_user
                else:
                    logger.warning("Could not fetch detailed permissions, using search results")

        return users

    def analyze_user_violations(self, user: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Analyze a user against all SOD rules

        Args:
            user: User data dictionary

        Returns:
            List of violations detected
        """
        violations = []

        user_roles = user.get('roles', [])
        user_role_names = [r.get('role_name', '') for r in user_roles]

        # Collect all permissions
        user_permissions = set()
        for role in user_roles:
            for perm in role.get('permissions', []):
                perm_key = perm.get('key', '')
                if perm_key:
                    user_permissions.add(perm_key)

        logger.info(f"Analyzing {user.get('name')}: {len(user_roles)} roles, {len(user_permissions)} permissions")

        # Check each SOD rule
        for rule in self.sod_rules:
            violation = self._check_rule_violation(
                user=user,
                user_role_names=user_role_names,
                user_permissions=user_permissions,
                rule=rule
            )

            if violation:
                violations.append(violation)

        return violations

    def _check_rule_violation(
        self,
        user: dict[str, Any],
        user_role_names: list[str],
        user_permissions: set,
        rule: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Check if user violates a specific SOD rule"""
        rule_violated = False
        conflicting_items = []

        # Special check for IT_ACCESS rules (role-based)
        if rule['rule_type'] == 'IT_ACCESS':
            # Check Administrator + business roles
            if any('Administrator' in role or 'Admin' in role for role in user_role_names):
                business_roles = ['AP Clerk', 'AR Clerk', 'Sales Representative', 'Financials',
                                'Accountant', 'Finance', 'Sales', 'Purchasing']
                conflicting = [role for role in user_role_names
                             if any(br.lower() in role.lower() for br in business_roles)]
                if conflicting:
                    rule_violated = True
                    admin_role = [r for r in user_role_names if 'Admin' in r][0]
                    conflicting_items = [admin_role] + conflicting

        # Check for conflicting permissions
        conflicts = rule.get('conflicting_permissions', {}).get('conflicts', [])
        for conflict_pair in conflicts:
            # Check if user has ALL permissions in this conflict pair
            has_all = all(self._has_permission(perm, user_permissions) for perm in conflict_pair)
            if has_all:
                rule_violated = True
                conflicting_items.extend(conflict_pair)

        if not rule_violated:
            return None

        # Calculate risk score
        risk_score = self._calculate_risk_score(user, rule, conflicting_items)

        return {
            'rule_id': rule['rule_id'],
            'rule_name': rule['rule_name'],
            'rule_type': rule['rule_type'],
            'description': rule['description'],
            'severity': rule['severity'],
            'regulatory_framework': rule.get('regulatory_framework', 'INTERNAL'),
            'risk_score': risk_score,
            'conflicting_items': conflicting_items,
            'remediation_guidance': rule.get('remediation_guidance', ''),
            'detected_at': datetime.now().isoformat()
        }

    def _has_permission(self, permission_name: str, user_permissions: set) -> bool:
        """Check if user has a permission (fuzzy matching)"""
        # Exact match
        if permission_name in user_permissions:
            return True

        # Fuzzy match
        permission_lower = permission_name.lower()
        for perm in user_permissions:
            if permission_lower in perm.lower() or perm.lower() in permission_lower:
                return True

        return False

    def _calculate_risk_score(
        self,
        user: dict[str, Any],
        rule: dict[str, Any],
        conflicting_items: list[str]
    ) -> float:
        """Calculate risk score (0-100)"""
        severity_scores = {
            'CRITICAL': 90,
            'HIGH': 70,
            'MEDIUM': 50,
            'LOW': 30
        }

        base_score = severity_scores.get(rule['severity'], 50)

        # Add penalty for number of conflicts
        conflict_penalty = min(len(conflicting_items) * 2, 10)

        # Add penalty for sensitive department
        department_penalty = 0
        department = user.get('department', '').upper()
        if any(dept in department for dept in ['FINANCE', 'ACCOUNTING', 'IT', 'HR', 'ENGINEERING']):
            department_penalty = 5

        # Add penalty for multiple roles
        role_count = len(user.get('roles', []))
        role_penalty = 0
        if role_count >= 4:
            role_penalty = 10
        elif role_count >= 3:
            role_penalty = 5

        final_score = min(base_score + conflict_penalty + department_penalty + role_penalty, 100)

        return round(final_score, 2)

    def generate_ai_analysis(
        self,
        user: dict[str, Any],
        violations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Use Claude Opus for deep AI analysis of user's violations

        Args:
            user: User data
            violations: List of violations detected

        Returns:
            AI-powered analysis with recommendations
        """
        logger.info(f"Generating AI analysis for {user.get('name')}")

        # Prepare user context
        user_roles = [r.get('role_name') for r in user.get('roles', [])]

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior compliance analyst with expertise in Segregation of Duties (SOD) and internal controls.

Analyze the user's access rights and detected violations in detail. Consider:
- SOX compliance requirements
- Financial transaction controls
- Principle of least privilege
- Business impact if access is misused
- Industry best practices

Provide comprehensive, actionable analysis in JSON format."""),
            ("user", """Analyze this NetSuite user's SOD compliance status:

USER INFORMATION:
Name: {user_name}
Email: {user_email}
Department: {department}
Title: {title}
Total Roles: {role_count}
Roles: {roles}

VIOLATIONS DETECTED: {violation_count}

DETAILED VIOLATIONS:
{violations}

Provide comprehensive analysis in this JSON format:
{{
    "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
    "risk_score": <number 0-100>,
    "executive_summary": "2-3 sentence summary of the risk profile",
    "primary_concerns": [
        "Concern 1",
        "Concern 2"
    ],
    "role_combination_analysis": "Detailed analysis of why these role combinations are problematic",
    "business_impact_assessment": "What could happen if this access is misused - be specific",
    "sox_compliance_issues": [
        "SOX issue 1",
        "SOX issue 2"
    ],
    "remediation_priority": "IMMEDIATE|HIGH|MEDIUM|LOW",
    "detailed_recommendations": [
        {{
            "action": "Specific action to take",
            "rationale": "Why this is critical",
            "implementation_steps": ["Step 1", "Step 2", "Step 3"]
        }}
    ],
    "compensating_controls": [
        "Alternative control if segregation not immediately possible"
    ],
    "monitoring_recommendations": [
        "What to monitor for this user going forward"
    ],
    "timeline": "Recommended timeline for remediation"
}}""")
        ])

        # Format violations for Claude
        violations_text = ""
        for i, v in enumerate(violations, 1):
            violations_text += f"""
{i}. {v['rule_name']} ({v['severity']})
   - Rule Type: {v['rule_type']}
   - Framework: {v['regulatory_framework']}
   - Risk Score: {v['risk_score']}/100
   - Description: {v['description']}
   - Conflicting Items: {', '.join(v['conflicting_items'])}
   - Remediation: {v['remediation_guidance']}
"""

        chain = prompt | self.llm_opus | JsonOutputParser()

        analysis = chain.invoke({
            "user_name": user.get('name', 'N/A'),
            "user_email": user.get('email', 'N/A'),
            "department": user.get('department', 'N/A'),
            "title": user.get('title', 'N/A'),
            "role_count": len(user.get('roles', [])),
            "roles": json.dumps(user_roles, indent=2),
            "violation_count": len(violations),
            "violations": violations_text
        })

        return analysis

    def generate_report(
        self,
        user1_name: str,
        user2_name: str
    ) -> dict[str, Any]:
        """
        Generate comprehensive SOD report for two users

        Args:
            user1_name: First user's full name
            user2_name: Second user's full name

        Returns:
            Complete report dictionary
        """
        print("\n" + "="*80)
        print(" SOD COMPLIANCE ANALYSIS REPORT")
        print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80 + "\n")

        # Fetch users (may return multiple records for same email)
        print("📥 Fetching user data from NetSuite...")
        users_list1 = self.fetch_users_by_name(user1_name)
        users_list2 = self.fetch_users_by_name(user2_name)

        if not users_list1:
            print(f"❌ User '{user1_name}' not found")
            return {'success': False, 'error': f"User '{user1_name}' not found"}

        if not users_list2:
            print(f"❌ User '{user2_name}' not found")
            return {'success': False, 'error': f"User '{user2_name}' not found"}

        total_users = len(users_list1) + len(users_list2)
        print(f"✓ Found {len(users_list1)} record(s) for '{user1_name}'")
        print(f"✓ Found {len(users_list2)} record(s) for '{user2_name}'")
        print(f"✓ Total records to analyze: {total_users}\n")

        # Flatten all users into a single list for analysis
        all_users = []
        for user in users_list1:
            all_users.append(('user1', user))
        for user in users_list2:
            all_users.append(('user2', user))

        # Analyze violations for each user
        print("🔍 Analyzing SOD violations...")
        all_violations = []
        for group, user in all_users:
            violations = self.analyze_user_violations(user)
            all_violations.append((group, user, violations))
            print(f"✓ {user.get('name')}: {len(violations)} violations detected")
        print()

        # Generate AI analysis for each user
        print("🤖 Generating AI-powered analysis (Claude Opus 4.6)...")
        analyses_with_ai = []
        for group, user, violations in all_violations:
            ai_analysis = self.generate_ai_analysis(user, violations) if violations else None
            analyses_with_ai.append((group, user, violations, ai_analysis))
        print("✓ AI analysis complete\n")

        # Print detailed reports for each user
        for group, user, violations, ai_analysis in analyses_with_ai:
            # Add label if duplicate
            if len(users_list1) > 1 and group == 'user1':
                label = f"{user.get('name')} (User ID: {user.get('user_id')})"
            elif len(users_list2) > 1 and group == 'user2':
                label = f"{user.get('name')} (User ID: {user.get('user_id')})"
            else:
                label = user.get('name')

            print("\n" + "="*80)
            print(f" USER ANALYSIS: {label}")
            print("="*80)
            self._print_user_report(user, violations, ai_analysis, skip_header=True)

        # Generate comparison (show summary of all users)
        print("\n" + "="*80)
        print(" COMPARATIVE ANALYSIS")
        print("="*80 + "\n")

        for group, user, violations, ai_analysis in analyses_with_ai:
            risk_score = sum(v.get('risk_score', 0) for v in violations)
            print(f"User: {user.get('name')} (ID: {user.get('user_id')})")
            print(f"   Violations: {len(violations)}")
            print(f"   Total Risk Score: {risk_score:.2f}")
            print(f"   Critical: {sum(1 for v in violations if v['severity'] == 'CRITICAL')}")
            print(f"   High: {sum(1 for v in violations if v['severity'] == 'HIGH')}")
            print()

        # Return results
        results = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'users_analyzed': []
        }

        for group, user, violations, ai_analysis in analyses_with_ai:
            results['users_analyzed'].append({
                'group': group,
                'info': user,
                'violations': violations,
                'ai_analysis': ai_analysis
            })

        return results

    def _print_user_report(
        self,
        user: dict[str, Any],
        violations: list[dict[str, Any]],
        ai_analysis: dict[str, Any] | None,
        skip_header: bool = False
    ):
        """Print detailed report for one user"""
        if not skip_header:
            print("\n" + "="*80)
            print(f" USER ANALYSIS: {user.get('name', 'Unknown')}")
            print("="*80)

        print("\n📋 USER INFORMATION:")
        print(f"   Name: {user.get('name', 'N/A')}")
        print(f"   Email: {user.get('email', 'N/A')}")
        print(f"   Department: {user.get('department', 'N/A')}")
        print(f"   Title: {user.get('title', 'N/A')}")
        print(f"   User ID: {user.get('user_id', 'N/A')}")

        # Roles
        print(f"\n🎭 ROLES ({len(user.get('roles', []))}):")
        for i, role in enumerate(user.get('roles', []), 1):
            perm_count = len(role.get('permissions', []))
            print(f"   {i}. {role.get('role_name', 'Unknown')} ({perm_count} permissions)")

        # Violations
        if violations:
            print(f"\n⚠️  SOD VIOLATIONS DETECTED: {len(violations)}")
            print("-" * 80)

            for i, v in enumerate(violations, 1):
                severity_emoji = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }.get(v['severity'], '⚪')

                print(f"\n{severity_emoji} VIOLATION #{i}: {v['rule_name']}")
                print(f"   Severity: {v['severity']} | Risk Score: {v['risk_score']}/100")
                print(f"   Type: {v['rule_type']} | Framework: {v['regulatory_framework']}")
                print(f"   Description: {v['description']}")
                print(f"   Conflicting Items: {', '.join(v['conflicting_items'])}")
                print(f"   Remediation: {v['remediation_guidance']}")
        else:
            print("\n✅ NO SOD VIOLATIONS DETECTED")

        # AI Analysis
        if ai_analysis:
            print("\n🤖 AI-POWERED RISK ASSESSMENT (Claude Opus 4.6):")
            print("-" * 80)
            print(f"\n   Risk Level: {ai_analysis.get('overall_risk_level', 'N/A')}")
            print(f"   Risk Score: {ai_analysis.get('risk_score', 0)}/100")
            print(f"   Remediation Priority: {ai_analysis.get('remediation_priority', 'N/A')}")

            print("\n   Executive Summary:")
            print(f"   {ai_analysis.get('executive_summary', 'N/A')}")

            print("\n   Primary Concerns:")
            for concern in ai_analysis.get('primary_concerns', []):
                print(f"   • {concern}")

            print("\n   Role Combination Analysis:")
            print(f"   {ai_analysis.get('role_combination_analysis', 'N/A')}")

            print("\n   Business Impact Assessment:")
            print(f"   {ai_analysis.get('business_impact_assessment', 'N/A')}")

            if ai_analysis.get('sox_compliance_issues'):
                print("\n   SOX Compliance Issues:")
                for issue in ai_analysis['sox_compliance_issues']:
                    print(f"   • {issue}")

            print("\n   📋 DETAILED RECOMMENDATIONS:")
            for i, rec in enumerate(ai_analysis.get('detailed_recommendations', []), 1):
                print(f"\n   {i}. {rec.get('action', 'N/A')}")
                print(f"      Rationale: {rec.get('rationale', 'N/A')}")
                print("      Implementation Steps:")
                for step in rec.get('implementation_steps', []):
                    print(f"      - {step}")

            if ai_analysis.get('compensating_controls'):
                print("\n   🛡️  COMPENSATING CONTROLS:")
                for control in ai_analysis['compensating_controls']:
                    print(f"   • {control}")

            if ai_analysis.get('monitoring_recommendations'):
                print("\n   👁️  MONITORING RECOMMENDATIONS:")
                for mon in ai_analysis['monitoring_recommendations']:
                    print(f"   • {mon}")

            print(f"\n   ⏱️  Timeline: {ai_analysis.get('timeline', 'N/A')}")

        print("\n")

    def _print_comparison(
        self,
        user1: dict[str, Any],
        user2: dict[str, Any],
        user1_violations: list[dict[str, Any]],
        user2_violations: list[dict[str, Any]]
    ):
        """Print comparison between two users"""
        print("\n" + "="*80)
        print(" COMPARATIVE ANALYSIS")
        print("="*80 + "\n")

        # Calculate scores
        user1_risk = sum(v['risk_score'] for v in user1_violations) if user1_violations else 0
        user2_risk = sum(v['risk_score'] for v in user2_violations) if user2_violations else 0

        print(f"User 1: {user1.get('name')}")
        print(f"   Violations: {len(user1_violations)}")
        print(f"   Total Risk Score: {user1_risk:.2f}")
        print(f"   Critical: {sum(1 for v in user1_violations if v['severity'] == 'CRITICAL')}")
        print(f"   High: {sum(1 for v in user1_violations if v['severity'] == 'HIGH')}")

        print(f"\nUser 2: {user2.get('name')}")
        print(f"   Violations: {len(user2_violations)}")
        print(f"   Total Risk Score: {user2_risk:.2f}")
        print(f"   Critical: {sum(1 for v in user2_violations if v['severity'] == 'CRITICAL')}")
        print(f"   High: {sum(1 for v in user2_violations if v['severity'] == 'HIGH')}")

        print("\n📊 Comparison:")
        if user1_risk > 0 and user2_risk > 0:
            if user1_risk > user2_risk:
                print(f"   ⚠️  {user1.get('name')} has {((user1_risk/user2_risk-1)*100):.1f}% higher risk than {user2.get('name')}")
            elif user2_risk > user1_risk:
                print(f"   ⚠️  {user2.get('name')} has {((user2_risk/user1_risk-1)*100):.1f}% higher risk than {user1.get('name')}")
            else:
                print("   ✓ Both users have equal risk levels")
        elif user1_risk > 0 and user2_risk == 0:
            print(f"   ⚠️  {user1.get('name')} has violations while {user2.get('name')} is compliant")
        elif user2_risk > 0 and user1_risk == 0:
            print(f"   ⚠️  {user2.get('name')} has violations while {user1.get('name')} is compliant")
        else:
            print("   ✓ Both users are compliant (no violations)")

        print("\n" + "="*80 + "\n")


def main():
    """Main execution"""
    try:
        generator = SODReportGenerator()

        # Generate report for Prabal Saha and Robin Turner
        # Using email addresses for reliable search
        result = generator.generate_report(
            user1_name="prabal.saha@fivetran.com",
            user2_name="robin.turner@fivetran.com"
        )

        if result.get('success'):
            print("✅ SOD Analysis Complete!")
            print(f"\nReport generated at: {result['timestamp']}")
        else:
            print(f"❌ Analysis failed: {result.get('error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
