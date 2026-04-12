"""
Analysis Agent - Detects SOD violations and compliance risks

This agent is responsible for:
1. Loading SOD rules from configuration
2. Analyzing user-role-permission combinations
3. Detecting conflicting permissions
4. Calculating risk scores
5. Storing violations in database
6. Using Claude Opus for complex reasoning
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from models.database import ViolationSeverity
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from utils.langchain_callback import TokenTrackingCallback

logger = logging.getLogger(__name__)

# Static system prompt (identical for every user — eligible for prefix caching)
_SOD_ANALYST_SYSTEM_PROMPT = (
    "You are a senior compliance analyst specializing in Segregation of Duties (SOD) and internal controls. "
    "Analyze the user's access rights and provide: "
    "1. Overall risk assessment. "
    "2. Specific concerns about role combinations. "
    "3. Potential business impact if access is misused. "
    "4. Detailed remediation recommendations. "
    "5. Priority level for remediation. "
    "Consider: SOX compliance, principle of least privilege, separation of creation/approval duties, "
    "and financial transaction controls. Respond in JSON format."
)


class SODAnalysisAgent:
    """Agent for analyzing SOD violations using Claude Opus for reasoning"""

    def __init__(
        self,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        violation_repo: ViolationRepository,
        sod_rule_repo: SODRuleRepository,
        sod_rules_path: str | None = None,
        llm_model: str = "claude-opus-4.6",  # Use Opus for complex reasoning
        exception_repo=None  # Optional ExceptionRepository for business justification checks
    ):
        """
        Initialize SOD Analysis Agent

        Args:
            user_repo: User repository instance
            role_repo: Role repository instance
            violation_repo: Violation repository instance
            sod_rule_repo: SOD rule repository instance
            sod_rules_path: Path to SOD rules JSON file
            llm_model: Claude model to use (Opus for deep analysis)
            exception_repo: Optional ExceptionRepository for approved exception lookups
        """
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.violation_repo = violation_repo
        self.sod_rule_repo = sod_rule_repo
        self.exception_repo = exception_repo
        self._token_callback = TokenTrackingCallback(agent_name="analyzer", operation="sod_analysis")
        self.llm = ChatAnthropic(
            model=llm_model,
            temperature=0,
            max_tokens=2048,
            callbacks=[self._token_callback]
        )

        # Load SOD rules
        if sod_rules_path is None:
            sod_rules_path = Path(__file__).parent.parent / "database" / "seed_data" / "sod_rules.json"

        self.sod_rules = self._load_sod_rules(sod_rules_path)

        # Store SOD rules in database and create mapping
        self.rule_id_to_uuid = self._store_sod_rules_in_db()

        self.analysis_stats = {
            'users_analyzed': 0,
            'violations_detected': 0,
            'critical_violations': 0,
            'high_violations': 0,
            'medium_violations': 0,
            'start_time': None,
            'end_time': None
        }

        logger.info(f"SOD Analysis Agent initialized with model: {llm_model}")
        logger.info(f"Loaded {len(self.sod_rules)} SOD rules")
        logger.info(f"Stored {len(self.rule_id_to_uuid)} SOD rules in database")

    def _load_sod_rules(self, rules_path: str) -> list[dict[str, Any]]:
        """Load SOD rules from JSON file"""
        try:
            with open(rules_path) as f:
                rules = json.load(f)
            logger.info(f"Loaded {len(rules)} SOD rules from {rules_path}")
            return rules
        except Exception as e:
            logger.error(f"Failed to load SOD rules: {str(e)}")
            return []

    def _store_sod_rules_in_db(self) -> dict[str, str]:
        """
        Store SOD rules in database and create mapping from rule_id to UUID

        Returns:
            Dictionary mapping rule_id (string like "SOD-FIN-001") to database UUID
        """
        mapping = {}

        for rule in self.sod_rules:
            try:
                # Upsert rule in database
                rule_obj = self.sod_rule_repo.upsert_rule(rule)

                # Store mapping from string rule_id to database UUID
                mapping[rule['rule_id']] = str(rule_obj.id)

            except Exception as e:
                logger.error(f"Failed to store rule {rule.get('rule_id')}: {str(e)}")

        logger.info(f"Created rule ID mappings for {len(mapping)} rules")
        return mapping

    def analyze_all_users(self, scan_id: str | None = None) -> dict[str, Any]:
        """
        Analyze all active users for SOD violations

        Args:
            scan_id: Optional compliance scan ID to associate violations with

        Returns:
            Dictionary with analysis results and statistics
        """
        logger.info("Starting comprehensive SOD analysis for all users")
        self.analysis_stats['start_time'] = datetime.now()

        try:
            # Get all active users with their roles and permissions
            users = self.user_repo.get_users_with_roles()
            logger.info(f"Analyzing {len(users)} active users")

            all_violations = []

            for user in users:
                user_violations = self._analyze_user(user, scan_id)
                all_violations.extend(user_violations)
                self.analysis_stats['users_analyzed'] += 1

            # Count by severity
            self.analysis_stats['violations_detected'] = len(all_violations)
            self.analysis_stats['critical_violations'] = sum(
                1 for v in all_violations if v['severity'] == 'CRITICAL'
            )
            self.analysis_stats['high_violations'] = sum(
                1 for v in all_violations if v['severity'] == 'HIGH'
            )
            self.analysis_stats['medium_violations'] = sum(
                1 for v in all_violations if v['severity'] == 'MEDIUM'
            )

            self.analysis_stats['end_time'] = datetime.now()
            duration = (self.analysis_stats['end_time'] - self.analysis_stats['start_time']).total_seconds()

            logger.info(
                f"Analysis complete: {self.analysis_stats['violations_detected']} violations found "
                f"({self.analysis_stats['critical_violations']} critical, "
                f"{self.analysis_stats['high_violations']} high) in {duration:.2f}s"
            )

            return {
                'success': True,
                'violations': all_violations,
                'stats': self.analysis_stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during SOD analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'SOD analysis failed'
            }

    def _analyze_user(self, user: Any, scan_id: str | None = None) -> list[dict[str, Any]]:
        """
        Analyze a single user for SOD violations

        Args:
            user: User object with roles and permissions loaded
            scan_id: Optional scan ID

        Returns:
            List of violations detected for this user
        """
        violations = []

        # Get user's roles and all permissions
        user_roles = [ur.role for ur in user.user_roles]
        user_role_names = [role.role_name for role in user_roles]

        # Collect all unique permissions across all roles
        user_permissions = set()
        for role in user_roles:
            if role.permissions:
                for perm in role.permissions:
                    user_permissions.add(perm.get('key', ''))

        logger.debug(f"Analyzing user {user.email}: {len(user_roles)} roles, {len(user_permissions)} permissions")

        # Check each SOD rule
        for rule in self.sod_rules:
            violation = self._check_rule_violation(
                user=user,
                user_roles=user_roles,
                user_role_names=user_role_names,
                user_permissions=user_permissions,
                rule=rule,
                scan_id=scan_id
            )

            if violation:
                violations.append(violation)

        return violations

    def _check_rule_violation(
        self,
        user: Any,
        user_roles: list[Any],
        user_role_names: list[str],
        user_permissions: set,
        rule: dict[str, Any],
        scan_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Check if user violates a specific SOD rule

        Args:
            user: User object
            user_roles: List of role objects
            user_role_names: List of role names
            user_permissions: Set of permission keys
            rule: SOD rule to check
            scan_id: Optional scan ID

        Returns:
            Violation dictionary if violated, None otherwise
        """
        rule_violated = False
        conflicting_items = []

        # ================================================================
        # CONTEXT-AWARE EXEMPTIONS (Check job function before flagging)
        # ================================================================

        # Exempt IT/Systems Engineering users from financial SOD rules
        if self._is_it_systems_user(user) and self._is_financial_rule(rule):
            logger.info(
                f"Exempting IT/Systems user {user.email} from financial rule {rule['rule_id']} "
                f"(Job Function: {user.job_function})"
            )
            return None

        # Exempt users with documented business justification
        if self._has_business_justification(user, rule):
            logger.info(
                f"User {user.email} has business justification for rule {rule['rule_id']}"
            )
            return None

        # ================================================================
        # ROLE-BASED VIOLATION CHECKS (Quick Fix for Common Patterns)
        # ================================================================

        # 1. Administrator + Financial Roles (CRITICAL)
        if 'Administrator' in user_role_names:
            # Check for any Controller or finance-related roles
            finance_keywords = ['Controller', 'Finance', 'Financial', 'AP Manager', 'AR Manager', 'Treasury']
            conflicting = []
            for role in user_role_names:
                if role != 'Administrator' and any(keyword in role for keyword in finance_keywords):
                    conflicting.append(role)

            if conflicting and rule['rule_type'] in ['FINANCIAL', 'IT_ACCESS']:
                rule_violated = True
                conflicting_items = ['Administrator'] + conflicting
                logger.info(f"Role-based violation detected: Administrator + {conflicting}")

        # 2. Administrator + AP/AR/Purchasing Roles (CRITICAL)
        if not rule_violated and 'Administrator' in user_role_names:
            business_roles = ['AP Clerk', 'AR Clerk', 'Sales Representative', 'Purchasing', 'Buyer']
            conflicting = []
            for role in user_role_names:
                if any(bus_role in role for bus_role in business_roles):
                    conflicting.append(role)

            if conflicting and rule['rule_type'] in ['FINANCIAL', 'PROCUREMENT', 'IT_ACCESS']:
                rule_violated = True
                conflicting_items = ['Administrator'] + conflicting
                logger.info(f"Role-based violation detected: Administrator + {conflicting}")

        # 3. Create + Approve Role Combinations (HIGH)
        if not rule_violated:
            # Check for roles with both "create" and "approve" keywords
            create_roles = [role for role in user_role_names if 'Create' in role or 'Entry' in role]
            approve_roles = [role for role in user_role_names if 'Approve' in role or 'Approval' in role]

            if create_roles and approve_roles and rule['rule_type'] == 'FINANCIAL':
                rule_violated = True
                conflicting_items = create_roles + approve_roles
                logger.info("Role-based violation detected: Create + Approve roles")

        # 4. Legacy IT_ACCESS check for specific business roles
        if not rule_violated and rule['rule_type'] == 'IT_ACCESS' and 'Administrator' in user_role_names:
            # Special check for admin + specific business roles
            specific_roles = ['AP Clerk', 'AR Clerk', 'Sales Representative', 'Financials']
            conflicting = [role for role in user_role_names if role in specific_roles]
            if conflicting:
                rule_violated = True
                conflicting_items = ['Administrator'] + conflicting

        # Check for conflicting permissions (permission-based check)
        conflicts = rule.get('conflicting_permissions', {}).get('conflicts', [])
        for conflict_pair in conflicts:
            # Check if user has ALL permissions in this conflict pair
            has_all = all(self._has_permission(perm, user_permissions) for perm in conflict_pair)
            if has_all:
                rule_violated = True
                conflicting_items.extend(conflict_pair)

        if not rule_violated:
            return None

        # Calculate risk score for this violation
        risk_score = self._calculate_violation_risk_score(
            user=user,
            rule=rule,
            conflicting_items=conflicting_items
        )

        # Create violation record - use database UUID for rule_id
        rule_uuid = self.rule_id_to_uuid.get(rule['rule_id'])
        if not rule_uuid:
            logger.error(f"No UUID mapping found for rule {rule['rule_id']}")
            return None

        violation_data = {
            'user_id': str(user.id),
            'rule_id': rule_uuid,  # Use database UUID
            'scan_id': scan_id,
            'severity': rule['severity'],
            'status': 'OPEN',
            'risk_score': risk_score,
            'title': f"{rule['rule_name']} Violation",
            'description': f"{rule['description']} User {user.email} has conflicting items: {', '.join(conflicting_items)}",
            'conflicting_roles': user_role_names,
            'conflicting_permissions': list(conflicting_items),
            'violation_metadata': {
                'rule_type': rule['rule_type'],
                'regulatory_framework': rule.get('regulatory_framework', 'INTERNAL'),
                'remediation_guidance': rule.get('remediation_guidance', ''),
                'detected_at': datetime.now().isoformat(),
                'department': user.department
            }
        }

        # Store in database
        try:
            self.violation_repo.create_violation(violation_data)
            logger.info(
                f"Violation detected: {user.email} - {rule['rule_name']} "
                f"(severity: {rule['severity']}, risk: {risk_score})"
            )
            return violation_data
        except Exception as e:
            logger.error(f"Failed to store violation: {str(e)}")
            return violation_data

    def _has_permission(self, permission_name: str, user_permissions: set) -> bool:
        """
        Check if user has a specific permission (fuzzy matching)

        Args:
            permission_name: Permission name to check
            user_permissions: Set of user's permission keys

        Returns:
            True if user has the permission
        """
        # Exact match
        if permission_name in user_permissions:
            return True

        # Fuzzy match (contains)
        permission_lower = permission_name.lower()
        for perm in user_permissions:
            if permission_lower in perm.lower():
                return True

        return False

    def _calculate_violation_risk_score(
        self,
        user: Any,
        rule: dict[str, Any],
        conflicting_items: list[str]
    ) -> float:
        """
        Calculate risk score for a violation (0-100)

        Args:
            user: User object
            rule: SOD rule
            conflicting_items: List of conflicting roles/permissions

        Returns:
            Risk score between 0-100
        """
        base_score = 0

        # Base score by severity
        severity_scores = {
            'CRITICAL': 90,
            'HIGH': 70,
            'MEDIUM': 50,
            'LOW': 30
        }
        base_score = severity_scores.get(rule['severity'], 50)

        # Add points based on number of conflicting items
        conflict_penalty = min(len(conflicting_items) * 2, 10)

        # Add points if user is in sensitive department
        department_penalty = 0
        if user.department and user.department.upper() in ['FINANCE', 'ACCOUNTING', 'IT', 'HR']:
            department_penalty = 5

        # Add points based on total role count
        role_count_penalty = 0
        role_count = len(user.user_roles)
        if role_count >= 4:
            role_count_penalty = 10
        elif role_count >= 3:
            role_count_penalty = 5

        final_score = min(base_score + conflict_penalty + department_penalty + role_count_penalty, 100)

        return round(final_score, 2)

    def analyze_user_with_ai_reasoning(
        self,
        user_email: str,
        include_remediation: bool = True
    ) -> dict[str, Any]:
        """
        Use Claude Opus to perform deep analysis on a specific user with AI reasoning

        Args:
            user_email: User email to analyze
            include_remediation: Whether to include remediation suggestions

        Returns:
            AI-powered analysis with reasoning and recommendations
        """
        logger.info(f"Starting AI-powered analysis for user: {user_email}")

        try:
            # Get user data
            user = self.user_repo.get_user_by_email(user_email)
            if not user:
                return {
                    'success': False,
                    'error': f"User {user_email} not found"
                }

            # Get user's roles with permissions
            user_roles = [ur.role for ur in user.user_roles]

            # Get all permissions
            all_permissions = []
            for role in user_roles:
                if role.permissions:
                    all_permissions.extend(role.permissions)

            # Get existing violations
            existing_violations = self.violation_repo.get_violations_by_user(str(user.id))

            # Prepare context for Claude
            user_context = {
                'email': user.email,
                'name': user.name,
                'department': user.department,
                'title': user.title,
                'roles': [{'name': r.name, 'permission_count': len(r.permissions or [])} for r in user_roles],
                'total_roles': len(user_roles),
                'total_permissions': len(all_permissions),
                'violations_detected': len(existing_violations),
                'violation_severities': [v.severity.value for v in existing_violations]
            }

            # Create prompt — system message uses cache_control for prefix caching
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=[{
                    "type": "text",
                    "text": _SOD_ANALYST_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"}
                }]),
                ("user", """Analyze this NetSuite user's access rights:

User: {user_email}
Name: {user_name}
Department: {department}
Job Title: {title}

Roles: {roles}
Total Permissions: {total_permissions}

Automated Violations Detected: {violations_detected}
Violation Severities: {violation_severities}

Provide comprehensive analysis in this JSON format:
{{
    "overall_risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
    "risk_score": <number 0-100>,
    "primary_concerns": ["List of main concerns"],
    "role_combination_analysis": "Detailed analysis of role combinations",
    "business_impact_assessment": "What could happen if this access is misused",
    "sox_compliance_issues": ["SOX-related concerns"],
    "remediation_priority": "IMMEDIATE|HIGH|MEDIUM|LOW",
    "detailed_recommendations": [
        {{
            "action": "Specific action to take",
            "rationale": "Why this is needed",
            "implementation_steps": ["Step 1", "Step 2"]
        }}
    ],
    "compensating_controls": ["Alternative controls if segregation not possible"],
    "monitoring_recommendations": ["What to monitor for this user"]
}}""")
            ])

            chain = prompt | self.llm | JsonOutputParser()

            # Invoke Claude Opus for deep reasoning
            analysis = chain.invoke({
                "user_email": user.email,
                "user_name": user.name or "N/A",
                "department": user.department or "N/A",
                "title": user.title or "N/A",
                "roles": json.dumps(user_context['roles'], indent=2),
                "total_permissions": user_context['total_permissions'],
                "violations_detected": user_context['violations_detected'],
                "violation_severities": ", ".join(user_context['violation_severities']) if user_context['violation_severities'] else "None"
            })

            logger.info(f"AI analysis complete for {user_email}: Risk Level = {analysis.get('overall_risk_level')}")

            return {
                'success': True,
                'user_context': user_context,
                'ai_analysis': analysis,
                'existing_violations': [
                    {
                        'rule': v.rule.rule_name if v.rule else 'Unknown',
                        'severity': v.severity.value,
                        'status': v.status.value,
                        'risk_score': v.risk_score
                    }
                    for v in existing_violations
                ],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error during AI analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'AI analysis failed'
            }

    def get_analysis_summary(self) -> dict[str, Any]:
        """
        Get summary of all violations in the system

        Returns:
            Summary statistics and top violations
        """
        try:
            # Get violation counts by severity
            summary = self.violation_repo.get_violation_summary()

            # Get top 10 most critical violations
            critical_violations = self.violation_repo.get_open_violations(
                severity=ViolationSeverity.CRITICAL
            )[:10]

            return {
                'success': True,
                'summary': summary,
                'top_critical_violations': [
                    {
                        'user_email': v.user.email if v.user else 'Unknown',
                        'rule': v.rule.rule_name if v.rule else 'Unknown',
                        'risk_score': v.risk_score,
                        'detected_at': v.detected_at.isoformat()
                    }
                    for v in critical_violations
                ],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting analysis summary: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _is_it_systems_user(self, user: Any) -> bool:
        """
        Check if user is IT/Systems Engineering staff

        IT/Systems users need Administrator access for legitimate system management,
        not for financial operations. They should be exempt from financial SOD rules.

        Args:
            user: User object

        Returns:
            True if user is IT/Systems staff, False otherwise
        """
        if not hasattr(user, 'job_function') or not user.job_function:
            # Fallback to department/title if job_function not set
            department = (user.department or '').lower()
            title = (getattr(user, 'title', None) or '').lower()

            # Check department
            if any(keyword in department for keyword in [
                'systems engineering',
                'system engineering',
                'it',
                'technology',
                'engineering',
                'devops'
            ]):
                return True

            # Check title
            if any(keyword in title for keyword in [
                'engineer',
                'systems',
                'devops',
                'sre',
                'technical'
            ]):
                return True

            return False

        # Check job_function field
        it_functions = [
            'IT/SYSTEMS_ENGINEERING',
            'IT',
            'SYSTEMS_ENGINEERING',
            'TECHNOLOGY',
            'DEVOPS',
            'SRE'
        ]

        return user.job_function in it_functions

    def _is_financial_rule(self, rule: dict[str, Any]) -> bool:
        """
        Check if rule is related to financial operations

        Args:
            rule: SOD rule dictionary

        Returns:
            True if rule is financial, False otherwise
        """
        financial_types = ['FINANCIAL', 'ACCOUNTING', 'AP', 'AR', 'TREASURY']

        rule_type = rule.get('rule_type', '')
        if rule_type in financial_types:
            return True

        # Check rule ID
        rule_id = rule.get('rule_id', '')
        if 'FIN' in rule_id or 'ACC' in rule_id:
            return True

        # Check rule name and description
        rule_name = rule.get('rule_name', '').lower()
        rule_desc = rule.get('description', '').lower()

        financial_keywords = [
            'financial',
            'accounting',
            'payable',
            'receivable',
            'journal',
            'treasury',
            'payment',
            'invoice',
            'bill',
            'expense'
        ]

        for keyword in financial_keywords:
            if keyword in rule_name or keyword in rule_desc:
                return True

        return False

    def _has_business_justification(self, user: Any, rule: dict[str, Any]) -> bool:
        """
        Check if user has a documented, active approved exception for this rule combination.

        Queries the approved_exceptions table via ExceptionRepository.

        Args:
            user: User object
            rule: SOD rule dictionary

        Returns:
            True if user has an active approved exception, False otherwise
        """
        if self.exception_repo is None:
            return False

        try:
            import uuid as _uuid
            user_id = user.id if not isinstance(user.id, _uuid.UUID) else user.id
            rule_id = rule.get('rule_code') or rule.get('rule_id')
            return self.exception_repo.find_active_exception(user_id, rule_id)
        except Exception as e:
            logger.warning(f"Error checking business justification for {getattr(user, 'email', user)}: {e}")
            return False


# Factory function
def create_analyzer(
    user_repo: UserRepository,
    role_repo: RoleRepository,
    violation_repo: ViolationRepository,
    sod_rule_repo: SODRuleRepository
) -> SODAnalysisAgent:
    """Create a configured SOD Analysis Agent instance"""
    return SODAnalysisAgent(
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo
    )
