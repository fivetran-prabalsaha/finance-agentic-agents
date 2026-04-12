"""
Compliance Orchestrator - Coordinates agents and connectors for MCP

This orchestrator sits between the MCP server and the existing compliance agents,
routing requests to appropriate components and aggregating results.
"""
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

# Import existing agents
from agents.analyzer import SODAnalysisAgent
from agents.knowledge_base_pgvector import create_knowledge_base
from agents.notifier import NotificationAgent

# Import connectors
from connectors.netsuite_connector import NetSuiteConnector

# Import database
from models.database_config import DatabaseConfig
from repositories.job_role_mapping_repository import JobRoleMappingRepository
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository

# Import repositories
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository

# Import LLM abstraction
from services.llm import LLMMessage

logger = logging.getLogger(__name__)


# Simple time-based cache for expensive operations
def timed_cache(seconds: int = 60):
    """Cache decorator with time-based expiration"""
    def decorator(func):
        cache = {}
        cache_time = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name, instance id, and all arguments
            # Convert args to strings, excluding self (args[0])
            args_str = "_".join(str(arg) for arg in args[1:])
            kwargs_str = "_".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = f"{id(args[0]) if args else ''}_{func.__name__}_{args_str}_{kwargs_str}"
            current_time = time.time()

            # Check if cached and not expired
            if key in cache and (current_time - cache_time.get(key, 0)) < seconds:
                logger.info(f"✅ Cache HIT for {func.__name__} (age: {current_time - cache_time[key]:.1f}s)")
                return cache[key]

            # Call function and cache result
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = current_time
            logger.info(f"❌ Cache MISS for {func.__name__}, caching for {seconds}s")
            return result

        return wrapper
    return decorator


class ComplianceOrchestrator:
    """
    Orchestrates compliance operations across agents and connectors

    This class coordinates:
    - Data fetching from external systems (NetSuite, Okta)
    - SOD analysis via AnalysisAgent
    - AI-powered analysis via NotificationAgent
    - Vector search via KnowledgeBaseAgent
    - Result aggregation and formatting
    """

    def __init__(self):
        """Initialize orchestrator with database, agents, and connectors"""
        logger.info("Initializing ComplianceOrchestrator...")

        # Initialize database
        self.db_config = DatabaseConfig()
        self.session = self.db_config.get_session()

        # Initialize repositories
        self.user_repo = UserRepository(self.session)
        self.role_repo = RoleRepository(self.session)
        self.violation_repo = ViolationRepository(self.session)
        self.rule_repo = SODRuleRepository(self.session)
        self.job_role_mapping_repo = JobRoleMappingRepository(self.session)

        # Initialize agents
        self.analysis_agent = SODAnalysisAgent(
            user_repo=self.user_repo,
            role_repo=self.role_repo,
            violation_repo=self.violation_repo,
            sod_rule_repo=self.rule_repo
        )
        self.notifier_agent = NotificationAgent(
            violation_repo=self.violation_repo,
            user_repo=self.user_repo,
            job_role_mapping_repo=self.job_role_mapping_repo,
            enable_cache=True  # Enable Redis caching
        )
        # Use factory function to auto-create embeddings from sod_rules.json
        self.kb_agent = create_knowledge_base(
            session=self.session,
            sod_rule_repo=self.rule_repo
        )

        # Initialize connectors
        self.connectors = {
            "netsuite": NetSuiteConnector(),
            # Add more connectors as implemented
            # "okta": OktaConnector(),
            # "salesforce": SalesforceConnector(),
        }

        logger.info("ComplianceOrchestrator initialized successfully")

    @timed_cache(seconds=60)  # Cache for 60 seconds (systems don't change often)
    def list_available_systems_sync(self) -> list[dict[str, Any]]:
        """
        List all configured systems with their status

        CACHED: Results cached for 60 seconds to improve performance

        Returns:
            List of system dictionaries with status information
        """
        logger.info("Listing available systems...")
        systems = []

        for name, connector in self.connectors.items():
            try:
                # Test connection
                status = connector.test_connection_sync()

                # Get user count
                user_count = connector.get_user_count_sync() if status else 0

                # Get last review date
                last_review = connector.get_last_sync_date_sync(self.violation_repo)

                systems.append({
                    "name": name,
                    "type": connector.get_system_type(),
                    "status": "connected" if status else "disconnected",
                    "user_count": user_count,
                    "last_review": last_review.strftime("%Y-%m-%d %H:%M:%S") if last_review else "Never"
                })

                logger.info(f"System {name}: {status}, {user_count} users")

            except Exception as e:
                logger.error(f"Error checking system {name}: {str(e)}")
                systems.append({
                    "name": name,
                    "type": "unknown",
                    "status": "error",
                    "user_count": 0,
                    "last_review": "Error",
                    "error": str(e)
                })

        return systems

    @timed_cache(seconds=300)  # Cache for 5 minutes (reviews don't change often)
    def perform_access_review_sync(
        self,
        system_name: str,
        analysis_type: str = "sod_violations",
        include_recommendations: bool = True
    ) -> dict[str, Any]:
        """
        Perform a comprehensive access review for a system

        Steps:
        1. Fetch users/roles from external system
        2. Sync to local database
        3. Run SOD analysis
        4. Generate AI recommendations (if requested)
        5. Return structured results

        Args:
            system_name: System to review (e.g., 'netsuite')
            analysis_type: Type of analysis ('sod_violations', 'excessive_permissions', etc.)
            include_recommendations: Generate AI-powered recommendations

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting access review for {system_name}")
        start_time = datetime.utcnow()

        # Step 1: Get connector
        connector = self.connectors.get(system_name)
        if not connector:
            raise ValueError(f"System not configured: {system_name}. Available: {list(self.connectors.keys())}")

        # Step 2: Test connection
        logger.info(f"Testing connection to {system_name}...")
        if not connector.test_connection_sync():
            raise ConnectionError(f"Cannot connect to {system_name}")

        # Step 3: Fetch data from external system
        logger.info(f"Fetching users from {system_name}...")
        users_data = connector.fetch_users_with_roles_sync(
            include_permissions=True
        )

        if not users_data:
            return {
                "system_name": system_name,
                "timestamp": start_time.isoformat(),
                "users_analyzed": 0,
                "total_violations": 0,
                "error": "No users found in system"
            }

        # Step 4: Sync to database
        logger.info(f"Syncing {len(users_data)} users to database...")
        synced_users = connector.sync_to_database_sync(users_data, self.user_repo, self.role_repo)

        # Step 5: Run SOD analysis
        logger.info(f"Running SOD analysis for {len(synced_users)} users...")
        analysis_result = self.analysis_agent.analyze_all_users()

        if not analysis_result.get('success'):
            logger.error(f"SOD analysis failed: {analysis_result.get('error')}")
            return {
                "system_name": system_name,
                "timestamp": start_time.isoformat(),
                "users_analyzed": len(synced_users),
                "total_violations": 0,
                "error": analysis_result.get('error', 'SOD analysis failed')
            }

        violations = analysis_result.get('violations', [])

        # Step 6: Calculate statistics (violations are dicts with string severity values)
        high_risk = len([v for v in violations if v.get('severity') == "HIGH"])
        medium_risk = len([v for v in violations if v.get('severity') == "MEDIUM"])
        low_risk = len([v for v in violations if v.get('severity') == "LOW"])

        # Step 7: Get top violators
        user_violation_counts = {}
        for violation in violations:
            user_id = violation.get('user_id') or violation.get('user', {}).get('id')
            if not user_id:
                continue

            if user_id not in user_violation_counts:
                user = self.user_repo.get_user_by_uuid(str(user_id))
                if not user:
                    continue
                user_violation_counts[user_id] = {
                    "user": user,
                    "count": 0,
                    "high_risk": 0,
                    "medium_risk": 0,
                    "low_risk": 0
                }
            user_violation_counts[user_id]["count"] += 1
            severity_str = violation.get('severity', 'LOW')
            if severity_str == "HIGH":
                user_violation_counts[user_id]["high_risk"] += 1
            elif severity_str == "MEDIUM":
                user_violation_counts[user_id]["medium_risk"] += 1
            else:
                user_violation_counts[user_id]["low_risk"] += 1

        top_violators = sorted(
            [
                {
                    "name": v["user"].name,
                    "email": v["user"].email,
                    "violation_count": v["count"],
                    "high_risk": v["high_risk"],
                    "medium_risk": v["medium_risk"],
                    "low_risk": v["low_risk"]
                }
                for v in user_violation_counts.values()
            ],
            key=lambda x: (x["high_risk"], x["violation_count"]),
            reverse=True
        )

        # Step 8: Generate AI recommendations (if requested)
        recommendations = ""
        if include_recommendations and violations:
            logger.info("Generating AI recommendations...")
            recommendations = self._generate_recommendations_sync(
                system_name, violations, top_violators
            )

        # Step 9: Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        logger.info(f"Access review complete: {len(violations)} violations found in {execution_time:.2f}s")

        return {
            "system_name": system_name,
            "timestamp": start_time.isoformat(),
            "execution_time_seconds": round(execution_time, 2),
            "users_analyzed": len(synced_users),
            "total_violations": len(violations),
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "top_violators": top_violators[:10],  # Top 10
            "recommendations": recommendations,
            "analysis_type": analysis_type
        }

    @timed_cache(seconds=60)  # Cache for 1 minute (user lookups)
    def get_user_violations_sync(
        self,
        system_name: str,
        user_identifier: str,
        include_ai_analysis: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed violations for a specific user

        Args:
            system_name: System name ('netsuite', 'okta', etc.)
            user_identifier: User email or ID
            include_ai_analysis: Include AI-powered risk analysis

        Returns:
            Dictionary with user violations and analysis
        """
        logger.info(f"Fetching violations for {user_identifier} in {system_name}")

        # Find user by email or ID
        user = self.user_repo.get_user_by_email(user_identifier)
        if not user:
            # Try by ID
            try:
                user = self.user_repo.get_user_by_id(user_identifier)
            except:
                pass

        # Auto-sync user from source system if not found in database
        if not user:
            logger.info(f"User not in database, attempting auto-sync from {system_name}...")
            connector = self.connectors.get(system_name.lower())

            if not connector:
                raise ValueError(f"Unknown system: {system_name}")

            try:
                # Fetch user from source system
                users_data = connector.fetch_users_with_roles_sync(
                    include_permissions=False,
                    include_inactive=False
                )

                # Find the requested user
                source_user = None
                for u in users_data:
                    if u.get('email') == user_identifier or str(u.get('user_id')) == user_identifier:
                        source_user = u
                        break

                if source_user:
                    # Sync user to database
                    logger.info(f"✅ Found user in {system_name}, syncing to database...")
                    user_data = {
                        'user_id': str(source_user.get('user_id')),
                        'internal_id': str(source_user.get('internal_id', source_user.get('user_id'))),
                        'name': source_user.get('name'),
                        'email': source_user.get('email'),
                        'status': 'ACTIVE' if source_user.get('is_active', True) else 'INACTIVE',
                        'department': source_user.get('department'),
                        'subsidiary': source_user.get('subsidiary'),
                        'employee_id': source_user.get('employee_id'),
                        'job_function': source_user.get('job_function'),
                        'title': source_user.get('title'),
                        'location': source_user.get('location')
                    }
                    user = self.user_repo.create_user(user_data)
                    logger.info(f"✅ User synced: {user.email} (UUID: {user.id})")
                else:
                    raise ValueError(f"User not found in {system_name}: {user_identifier}")

            except Exception as e:
                logger.error(f"Failed to auto-sync user: {str(e)}")
                raise ValueError(f"User not found: {user_identifier}")

        # Get violations
        violations = self.violation_repo.get_violations_by_user(user.id)

        # Get user roles
        roles = [ur.role.role_name for ur in user.user_roles]

        # Format violations
        formatted_violations = []
        for v in violations:
            formatted_violations.append({
                "id": str(v.id),
                "rule_name": v.rule.rule_name,
                "severity": v.severity.value if hasattr(v.severity, 'value') else str(v.severity),
                "description": v.description or v.rule.description,
                "risk_score": v.risk_score,
                "status": v.status.value if hasattr(v.status, 'value') else str(v.status),
                "detected_at": v.detected_at.isoformat(),
                "conflicting_roles": v.conflicting_roles or []
            })

        # Generate AI analysis (if requested)
        ai_analysis = ""
        if include_ai_analysis and violations:
            logger.info("Generating AI analysis for user violations...")
            ai_analysis = self.notifier_agent._generate_ai_analysis(
                user, violations, roles
            )

        return {
            "user_name": user.name,
            "email": user.email,
            "system": system_name,
            "roles": roles,
            "role_count": len(roles),
            "violation_count": len(violations),
            "violations": formatted_violations,
            "ai_analysis": ai_analysis,
            "department": user.department,
            "status": user.status.value if user.status else 'UNKNOWN',
            "is_active": user.status.value == "ACTIVE" if user.status else False,
            "synced_at": user.synced_at.strftime('%Y-%m-%d %H:%M:%S') if user.synced_at else 'Unknown'
        }

    def remediate_violation_sync(
        self,
        violation_id: str,
        action: str,
        notes: str = ""
    ) -> dict[str, Any]:
        """
        Create remediation plan for a violation

        Args:
            violation_id: Violation UUID
            action: Remediation action type
            notes: Additional notes

        Returns:
            Remediation status dictionary
        """
        logger.info(f"Creating remediation for violation {violation_id}: {action}")

        # Get violation
        violation = self.violation_repo.get_violation_by_id(violation_id)
        if not violation:
            raise ValueError(f"Violation not found: {violation_id}")

        # Get user
        user = violation.user

        # TODO: Implement actual remediation actions
        # For now, return a structured response

        next_steps = []
        if action == "remove_role":
            next_steps = [
                f"Identify which role to remove from {user.name}",
                "Create ticket in ServiceNow for role removal",
                "Notify user's manager for approval",
                "Schedule role removal after approval"
            ]
        elif action == "request_approval":
            next_steps = [
                f"Send approval request to {user.name}'s manager",
                "Document business justification for current role assignment",
                "Set up compensating controls if approval granted",
                "Re-review in 90 days"
            ]
        elif action == "create_ticket":
            next_steps = [
                "Create ServiceNow ticket with violation details",
                "Assign to IT Security team",
                "Set priority based on risk level",
                "Track remediation progress"
            ]
        elif action == "notify_manager":
            next_steps = [
                f"Send notification to {user.name}'s manager",
                "Include violation details and risk assessment",
                "Request action within 7 days",
                "Escalate if no response"
            ]

        return {
            "status": "initiated",
            "violation_id": violation_id,
            "user_name": user.name,
            "user_email": user.email,
            "action": action,
            "ticket_id": f"REM-{violation_id[:8].upper()}",
            "notes": notes,
            "next_steps": next_steps,
            "created_at": datetime.utcnow().isoformat()
        }

    def schedule_review_sync(
        self,
        system_name: str,
        frequency: str,
        day_of_week: str | None = None,
        time: str | None = None,
        timezone: str = "America/Los_Angeles"
    ) -> dict[str, Any]:
        """
        Schedule recurring compliance review

        Args:
            system_name: System to review
            frequency: 'daily', 'weekly', or 'monthly'
            day_of_week: Day for weekly reviews
            time: Time in HH:MM format
            timezone: IANA timezone

        Returns:
            Schedule confirmation dictionary
        """
        logger.info(f"Scheduling {frequency} review for {system_name}")

        # TODO: Implement actual scheduling with APScheduler or similar
        # For now, return a mock response

        schedule_desc = self._build_schedule_description(frequency, day_of_week, time)
        next_run = self._calculate_next_run(frequency, day_of_week, time, timezone)

        return {
            "status": "scheduled",
            "system_name": system_name,
            "frequency": frequency,
            "schedule_description": schedule_desc,
            "next_run": next_run,
            "timezone": timezone,
            "notification_channels": ["Email", "Claude UI"],
            "created_at": datetime.utcnow().isoformat()
        }

    @timed_cache(seconds=120)  # Cache for 2 minutes (stats change slowly)
    def get_violation_stats_sync(
        self,
        systems: list[str] | None = None,
        time_range: str = "month"
    ) -> dict[str, Any]:
        """
        Get aggregate violation statistics

        Args:
            systems: List of systems to include (None = all)
            time_range: 'today', 'week', 'month', 'quarter', 'year'

        Returns:
            Statistics dictionary
        """
        logger.info(f"Fetching violation stats for {time_range}")

        # Get all open violations
        all_violations = self.violation_repo.get_open_violations()

        # Filter by system if specified
        if systems:
            all_violations = [
                v for v in all_violations
                if v.user and hasattr(v.user, 'source_system') and v.user.source_system in systems
            ]

        # Calculate statistics
        total_violations = len(all_violations)
        high_risk = len([v for v in all_violations if v.severity == "HIGH"])
        medium_risk = len([v for v in all_violations if v.severity == "MEDIUM"])
        low_risk = len([v for v in all_violations if v.severity == "LOW"])

        # Get unique users
        unique_users = {v.user_id for v in all_violations if v.user_id}
        total_users = len(unique_users)

        # Group by system
        by_system = {}
        for violation in all_violations:
            if violation.user:
                system = getattr(violation.user, 'source_system', 'unknown')
                if system not in by_system:
                    by_system[system] = 0
                by_system[system] += 1

        by_system_list = [
            {"name": system, "violation_count": count}
            for system, count in by_system.items()
        ]

        return {
            "time_range": time_range,
            "system_count": len(by_system),
            "total_users": total_users,
            "total_violations": total_violations,
            "high_risk": high_risk,
            "high_risk_percent": round(high_risk / max(total_violations, 1) * 100, 1),
            "medium_risk": medium_risk,
            "medium_risk_percent": round(medium_risk / max(total_violations, 1) * 100, 1),
            "low_risk": low_risk,
            "low_risk_percent": round(low_risk / max(total_violations, 1) * 100, 1),
            "by_system": by_system_list,
            "trend_description": "Statistics for current period"
        }

    # Helper methods

    def _generate_recommendations_sync(
        self,
        system_name: str,
        violations: list,
        top_violators: list[dict[str, Any]]
    ) -> str:
        """Generate AI-powered recommendations based on violations"""

        if not violations:
            return "No violations found - system is compliant."

        # Create summary for AI
        # Note: violations are dictionaries, not objects
        high_risk_count = len([v for v in violations if v.get('severity') == "HIGH"])
        total_count = len(violations)
        top_3 = top_violators[:3]

        # Generate recommendations using existing NotificationAgent LLM
        prompt = f"""Based on the SOD compliance analysis of {system_name}:

Total Violations: {total_count}
High-Risk Violations: {high_risk_count}

Top Violators:
{chr(10).join([f"- {v['name']} ({v['email']}): {v['violation_count']} violations" for v in top_3])}

Provide 3-5 prioritized recommendations for remediation. Focus on:
1. Highest risk users/violations
2. Quick wins that reduce multiple violations
3. Process improvements to prevent future violations

Be specific and actionable."""

        try:
            # Use the same LLM as NotificationAgent
            messages = [LLMMessage(role="user", content=prompt)]
            response = self.notifier_agent.llm.generate(messages)
            return response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {str(e)}")
            return "Unable to generate AI recommendations at this time."

    def _build_schedule_description(
        self,
        frequency: str,
        day_of_week: str | None,
        time: str | None
    ) -> str:
        """Build human-readable schedule description"""
        time_str = time or "09:00"

        if frequency == "daily":
            return f"Every day at {time_str}"
        elif frequency == "weekly":
            day = (day_of_week or "monday").capitalize()
            return f"Every {day} at {time_str}"
        elif frequency == "monthly":
            return f"First day of each month at {time_str}"

        return frequency

    def _calculate_next_run(
        self,
        frequency: str,
        day_of_week: str | None,
        time: str | None,
        timezone: str
    ) -> str:
        """Calculate next run timestamp (simplified)"""
        # TODO: Implement actual calculation with timezone support

        now = datetime.utcnow()

        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(days=7)
        elif frequency == "monthly":
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        return next_run.strftime("%Y-%m-%d %H:%M:%S") + f" {timezone}"

    def list_all_users_sync(
        self,
        system_name: str = "netsuite",
        include_inactive: bool = False,
        filter_by_department: str | None = None,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        List all users from a system with their roles

        Args:
            system_name: System to query
            include_inactive: Include inactive users
            filter_by_department: Optional department filter
            limit: Maximum number of users to return

        Returns:
            Dictionary with user list and summary
        """
        logger.info(f"Listing all users from {system_name}")

        # Get connector
        connector = self.connectors.get(system_name)
        if not connector:
            raise ValueError(f"System not configured: {system_name}")

        # Fetch users from external system
        logger.info("Fetching users from external system...")
        users_data = connector.fetch_users_with_roles_sync(
            include_permissions=False,  # Don't need permissions for listing
            include_inactive=include_inactive
        )

        if not users_data:
            return {
                "system_name": system_name,
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "users": []
            }

        # Filter by department if specified (partial match to handle hierarchical dept names)
        if filter_by_department:
            filter_lower = filter_by_department.lower()
            users_data = [
                u for u in users_data
                if filter_lower in u.get('department', '').lower()
            ]
            logger.info(f"Filtered to {len(users_data)} users matching department filter: '{filter_by_department}'")

        # Get user IDs for violation lookup
        user_emails = [u['email'] for u in users_data if u.get('email')]

        # Get violation counts from database
        violation_counts = {}
        try:
            for email in user_emails:
                user = self.user_repo.get_user_by_email(email)  # Fixed: removed invalid system_name parameter
                if user:
                    violations = self.violation_repo.get_violations_by_user(user.id)
                    violation_counts[email] = len(violations)
                    logger.debug(f"User {email}: {len(violations)} violations")
        except Exception as e:
            logger.error(f"Could not fetch violation counts: {e}", exc_info=True)

        # Format user list
        formatted_users = []
        active_count = 0
        inactive_count = 0

        for user_data in users_data[:limit]:
            is_active = user_data.get('status', '').upper() == 'ACTIVE'
            if is_active:
                active_count += 1
            else:
                inactive_count += 1

            formatted_users.append({
                "name": user_data.get('name', 'Unknown'),
                "email": user_data.get('email', ''),
                "is_active": is_active,
                "department": user_data.get('department'),
                "role_count": len(user_data.get('roles', [])),
                "roles": [r.get('name') for r in user_data.get('roles', [])],
                "violation_count": violation_counts.get(user_data.get('email'), 0)
            })

        # Sort by name
        formatted_users.sort(key=lambda x: x['name'].lower())

        return {
            "system_name": system_name,
            "total_users": len(users_data),
            "active_users": active_count,
            "inactive_users": inactive_count,
            "users": formatted_users
        }
