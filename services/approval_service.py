"""
Approval Service - Role-Based Access Control and Approval Workflows

Handles:
- User authentication and role validation
- Approval authority checks
- Manager chain lookup
- Jira ticket creation for escalations
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for managing exception approval workflows with RBAC"""

    def __init__(self, session):
        self.session = session

    # =========================================================================
    # APPROVAL AUTHORITY CONFIGURATION
    # =========================================================================

    # Define roles that can approve exceptions at different risk levels
    APPROVAL_AUTHORITY_MAP = {
        "CRITICAL": [
            "Fivetran - CFO",
            "CFO",  # Also accept non-prefixed version
            "Fivetran - Chief Financial Officer",
            "Chief Financial Officer",
            "Fivetran - Audit Committee Member",
            "Audit Committee Member"
        ],
        "HIGH": [
            "Fivetran - CFO",
            "CFO",
            "Fivetran - Controller",
            "Controller",
            "Fivetran - Chief Financial Officer",
            "Chief Financial Officer",
            "Fivetran - VP Finance",
            "VP Finance",
            "Fivetran - Audit Committee Member",
            "Audit Committee Member"
        ],
        "MEDIUM": [
            "Fivetran - CFO",
            "CFO",
            "Fivetran - Controller",
            "Controller",
            "Fivetran - Director",
            "Director",
            "Fivetran - VP Finance",
            "VP Finance",
            "Fivetran - Compliance Officer",
            "Compliance Officer"
        ],
        "LOW": [
            "Fivetran - CFO",
            "CFO",
            "Fivetran - Controller",
            "Controller",
            "Fivetran - Director",
            "Director",
            "Fivetran - Manager",
            "Manager",
            "Fivetran - Compliance Officer",
            "Compliance Officer"
        ]
    }

    # Map risk scores to risk levels
    @staticmethod
    def get_risk_level(risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 75:
            return "CRITICAL"
        elif risk_score >= 60:
            return "HIGH"
        elif risk_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    # =========================================================================
    # USER AUTHENTICATION
    # =========================================================================

    def authenticate_user(self, email: str) -> dict[str, Any] | None:
        """
        Authenticate user by email and return user info

        Args:
            email: User email address

        Returns:
            Dict with user info or None if not found/inactive
        """
        try:
            from models.database import UserStatus
            from repositories.user_repository import UserRepository

            user_repo = UserRepository(self.session)
            user = user_repo.get_user_by_email(email)

            if not user:
                logger.warning(f"User not found: {email}")
                return None

            if user.status != UserStatus.ACTIVE:
                logger.warning(f"User not active: {email} (status: {user.status})")
                return None

            # Get user's roles
            roles = user_repo.get_user_roles(str(user.id))
            role_names = [role.role_name for role in roles]

            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "status": user.status,
                "job_title": user.title,
                "department": user.department,
                "supervisor": user.supervisor,
                "supervisor_id": user.supervisor_id,
                "roles": role_names
            }

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {str(e)}")
            return None

    # =========================================================================
    # APPROVAL AUTHORITY CHECKS
    # =========================================================================

    def check_approval_authority(
        self,
        user_email: str,
        risk_score: float,
        conflict_count: int = 0
    ) -> tuple[bool, str, str | None]:
        """
        Check if user has authority to approve exception at given risk level

        Args:
            user_email: Email of user attempting to approve
            risk_score: Risk score of the exception
            conflict_count: Number of conflicts (for additional context)

        Returns:
            Tuple of (has_authority: bool, risk_level: str, reason: Optional[str])
        """
        try:
            # Authenticate user
            user_info = self.authenticate_user(user_email)
            if not user_info:
                return False, "UNKNOWN", f"User {user_email} not found or inactive"

            user_roles = user_info['roles']
            risk_level = self.get_risk_level(risk_score)

            # Get required roles for this risk level
            required_roles = self.APPROVAL_AUTHORITY_MAP.get(risk_level, [])

            # Check if user has any of the required roles
            user_role_set = set(user_roles)
            required_role_set = set(required_roles)
            authorized_roles = user_role_set & required_role_set

            if authorized_roles:
                # User is authorized
                logger.info(
                    f"User {user_email} authorized to approve {risk_level} exception "
                    f"via role(s): {', '.join(authorized_roles)}"
                )
                return True, risk_level, None
            else:
                # User is NOT authorized
                reason = (
                    f"User {user_email} ({', '.join(user_roles) if user_roles else 'No roles'}) "
                    f"lacks authority to approve {risk_level} risk exceptions. "
                    f"Required role(s): {', '.join(required_roles)}"
                )
                logger.warning(reason)
                return False, risk_level, reason

        except Exception as e:
            logger.error(f"Error checking approval authority: {str(e)}")
            return False, "UNKNOWN", f"Error checking authority: {str(e)}"

    def get_required_approval_roles(self, risk_score: float) -> list[str]:
        """
        Get list of roles that can approve exceptions at this risk level

        Args:
            risk_score: Risk score of exception

        Returns:
            List of role names
        """
        risk_level = self.get_risk_level(risk_score)
        return self.APPROVAL_AUTHORITY_MAP.get(risk_level, [])

    # =========================================================================
    # MANAGER CHAIN LOOKUP
    # =========================================================================

    def find_approver_in_chain(
        self,
        user_email: str,
        risk_score: float,
        max_levels: int = 5
    ) -> dict[str, Any] | None:
        """
        Walk up the manager chain to find someone with approval authority

        Args:
            user_email: Starting user email
            risk_score: Risk score of exception
            max_levels: Maximum levels to traverse (prevent infinite loops)

        Returns:
            Dict with approver info or None if no one found
        """
        try:
            from repositories.user_repository import UserRepository

            user_repo = UserRepository(self.session)
            current_email = user_email
            levels_traversed = 0

            while levels_traversed < max_levels:
                # Get current user
                user_info = self.authenticate_user(current_email)
                if not user_info:
                    break

                # Check if this user can approve
                has_authority, risk_level, _ = self.check_approval_authority(
                    current_email,
                    risk_score
                )

                if has_authority:
                    # Found an approver!
                    logger.info(
                        f"Found approver in chain: {user_info['name']} "
                        f"({current_email}) at level {levels_traversed}"
                    )
                    return {
                        **user_info,
                        "levels_up": levels_traversed,
                        "risk_level": risk_level
                    }

                # Move up to supervisor
                if not user_info.get('supervisor_id'):
                    logger.warning(f"No supervisor found for {current_email}")
                    break

                # Get supervisor
                supervisor = user_repo.get_user_by_id(user_info['supervisor_id'])
                if not supervisor:
                    logger.warning(f"Supervisor {user_info['supervisor_id']} not found")
                    break

                current_email = supervisor.email
                levels_traversed += 1

            # No approver found in chain
            logger.warning(
                f"No approver found in manager chain for {user_email} "
                f"(traversed {levels_traversed} levels)"
            )
            return None

        except Exception as e:
            logger.error(f"Error finding approver in chain: {str(e)}")
            return None

    # =========================================================================
    # JIRA INTEGRATION
    # =========================================================================

    def create_approval_jira_ticket(
        self,
        requester_info: dict[str, Any],
        approver_info: dict[str, Any],
        exception_details: dict[str, Any]
    ) -> str | None:
        """
        Create Jira ticket for exception approval routing

        Args:
            requester_info: Info about user requesting approval
            approver_info: Info about manager who should approve
            exception_details: Exception details (user, roles, conflicts, etc.)

        Returns:
            Jira ticket ID or None if failed
        """
        try:
            # Check if Jira is configured
            import os
            jira_url = os.getenv('JIRA_URL')
            jira_api_token = os.getenv('JIRA_API_TOKEN')
            jira_email = os.getenv('JIRA_EMAIL')
            jira_project = os.getenv('JIRA_PROJECT', 'COMP')  # Default to COMP project

            if not all([jira_url, jira_api_token, jira_email]):
                logger.warning("Jira not configured - skipping ticket creation")
                return None

            # Create ticket via Jira API
            import requests
            from requests.auth import HTTPBasicAuth

            # Format description
            description = self._format_jira_description(
                requester_info,
                approver_info,
                exception_details
            )

            # Prepare ticket data
            ticket_data = {
                "fields": {
                    "project": {"key": jira_project},
                    "summary": (
                        f"SOD Exception Approval Required: "
                        f"{exception_details.get('user_name')} - "
                        f"{len(exception_details.get('role_names', []))} roles, "
                        f"{exception_details.get('conflict_count', 0)} conflicts"
                    ),
                    "description": description,
                    "issuetype": {"name": "Task"},
                    "priority": {"name": self._get_jira_priority(exception_details.get('risk_score', 0))},
                    "labels": ["sod-exception", "approval-required", "compliance"]
                }
            }

            # Add assignee if we have Jira username
            if approver_info.get('jira_username'):
                ticket_data["fields"]["assignee"] = {"name": approver_info['jira_username']}

            # Create ticket
            response = requests.post(
                f"{jira_url}/rest/api/2/issue",
                auth=HTTPBasicAuth(jira_email, jira_api_token),
                json=ticket_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 201:
                ticket = response.json()
                ticket_key = ticket.get('key')
                logger.info(f"Created Jira ticket: {ticket_key}")
                return ticket_key
            else:
                logger.error(f"Failed to create Jira ticket: {response.status_code} - {response.text}")
                return None

        except ImportError:
            logger.warning("requests library not installed - cannot create Jira ticket")
            return None
        except Exception as e:
            logger.error(f"Error creating Jira ticket: {str(e)}")
            return None

    def _format_jira_description(
        self,
        requester_info: dict[str, Any],
        approver_info: dict[str, Any],
        exception_details: dict[str, Any]
    ) -> str:
        """Format Jira ticket description"""

        risk_level = self.get_risk_level(exception_details.get('risk_score', 0))
        risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}

        description = f"""
*SOD Exception Approval Request*

{risk_emoji.get(risk_level, '⚪')} *Risk Level:* {risk_level} ({exception_details.get('risk_score', 0):.1f}/100)

---

h3. Requester Information
* *Name:* {requester_info.get('name')}
* *Email:* {requester_info.get('email')}
* *Role(s):* {', '.join(requester_info.get('roles', ['None']))}
* *Authority:* Insufficient for {risk_level} risk approval

h3. Exception Details
* *User:* {exception_details.get('user_name')} ({exception_details.get('user_email', 'N/A')})
* *Job Title:* {exception_details.get('job_title', 'N/A')}
* *Department:* {exception_details.get('department', 'N/A')}

h3. Role Combination Requested
{self._format_roles_list(exception_details.get('role_names', []))}

h3. SOD Conflicts Detected
* *Total Conflicts:* {exception_details.get('conflict_count', 0)}
* *Critical:* {exception_details.get('critical_conflicts', 0)}
* *High:* {exception_details.get('high_conflicts', 0)}
* *Medium:* {exception_details.get('medium_conflicts', 0)}
* *Low:* {exception_details.get('low_conflicts', 0)}

h3. Business Justification
{exception_details.get('business_justification', 'Not provided')}

h3. Proposed Compensating Controls
{self._format_controls_list(exception_details.get('compensating_controls', []))}

---

h3. Approval Required From
* *Name:* {approver_info.get('name')}
* *Email:* {approver_info.get('email')}
* *Position:* {approver_info.get('job_title', 'N/A')}
* *Levels Up:* {approver_info.get('levels_up', 0)} (in reporting chain)

h3. Action Required
# Review exception details and business justification
# Verify compensating controls are adequate
# Approve or deny via Claude Desktop using exception code once recorded
# Document your decision and rationale

*Note:* This exception was automatically routed to you because the requester lacks authority to approve {risk_level} risk exceptions.
"""
        return description

    def _format_roles_list(self, roles: list[str]) -> str:
        """Format roles for Jira"""
        if not roles:
            return "* None"
        return "\n".join(f"* {role}" for role in roles)

    def _format_controls_list(self, controls: list[dict[str, Any]]) -> str:
        """Format controls for Jira"""
        if not controls:
            return "* No controls specified"

        lines = []
        for _i, control in enumerate(controls, 1):
            name = control.get('control_name', 'Unnamed')
            reduction = control.get('risk_reduction_percentage', 0)
            cost = control.get('estimated_annual_cost', 0)
            lines.append(
                f"* *{name}* - {reduction}% risk reduction, "
                f"${cost:,.0f}/year estimated cost"
            )
        return "\n".join(lines)

    def _get_jira_priority(self, risk_score: float) -> str:
        """Get Jira priority based on risk score"""
        if risk_score >= 75:
            return "Highest"
        elif risk_score >= 60:
            return "High"
        elif risk_score >= 40:
            return "Medium"
        else:
            return "Low"

    # =========================================================================
    # APPROVAL WORKFLOW
    # =========================================================================

    def process_approval_request(
        self,
        requester_email: str,
        exception_details: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Process an exception approval request with RBAC

        Args:
            requester_email: Email of person requesting approval
            exception_details: Details of exception to approve

        Returns:
            Dict with:
            - approved: bool (if requester can approve directly)
            - risk_level: str
            - message: str (explanation)
            - jira_ticket: Optional[str] (if escalated)
            - approver: Optional[Dict] (if escalated)
        """
        try:
            # Authenticate requester
            requester_info = self.authenticate_user(requester_email)
            if not requester_info:
                return {
                    "approved": False,
                    "risk_level": "UNKNOWN",
                    "message": f"User {requester_email} not found or inactive",
                    "jira_ticket": None,
                    "approver": None
                }

            risk_score = exception_details.get('risk_score', 0)

            # Check approval authority
            has_authority, risk_level, reason = self.check_approval_authority(
                requester_email,
                risk_score
            )

            if has_authority:
                # User can approve directly
                return {
                    "approved": True,
                    "risk_level": risk_level,
                    "message": (
                        f"✅ {requester_info['name']} authorized to approve "
                        f"{risk_level} risk exceptions"
                    ),
                    "jira_ticket": None,
                    "approver": requester_info
                }
            else:
                # Need to escalate - find approver in chain
                approver = self.find_approver_in_chain(requester_email, risk_score)

                if not approver:
                    # No approver found - escalate to CFO
                    return {
                        "approved": False,
                        "risk_level": risk_level,
                        "message": (
                            "❌ No approver found in reporting chain. "
                            "Please escalate to CFO or Audit Committee manually."
                        ),
                        "jira_ticket": None,
                        "approver": None
                    }

                # Create Jira ticket for approval routing
                jira_ticket = self.create_approval_jira_ticket(
                    requester_info,
                    approver,
                    exception_details
                )

                return {
                    "approved": False,
                    "risk_level": risk_level,
                    "message": (
                        f"⚠️ Escalated for approval:\n"
                        f"• Requester: {requester_info['name']} (insufficient authority)\n"
                        f"• Approver: {approver['name']} ({approver['email']})\n"
                        f"• Levels Up: {approver['levels_up']}\n"
                        f"• Risk Level: {risk_level}\n"
                        f"• Jira Ticket: {jira_ticket or 'Not created (Jira not configured)'}"
                    ),
                    "jira_ticket": jira_ticket,
                    "approver": approver
                }

        except Exception as e:
            logger.error(f"Error processing approval request: {str(e)}")
            return {
                "approved": False,
                "risk_level": "UNKNOWN",
                "message": f"Error processing approval: {str(e)}",
                "jira_ticket": None,
                "approver": None
            }
