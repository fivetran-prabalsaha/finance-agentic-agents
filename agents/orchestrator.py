"""
Orchestrator - LangGraph-based multi-agent coordinator

This orchestrator is responsible for:
1. Coordinating all compliance agents
2. Managing workflow state
3. Executing compliance scans
4. Error handling and recovery
5. Audit trail creation
"""

import logging
import operator
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.analyzer import SODAnalysisAgent
from agents.data_collector import DataCollectionAgent
from agents.knowledge_base import KnowledgeBaseAgent
from agents.notifier import NotificationAgent
from agents.risk_assessor import RiskAssessmentAgent
from repositories.role_repository import RoleRepository
from repositories.sod_rule_repository import SODRuleRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.netsuite_client import NetSuiteClient

logger = logging.getLogger(__name__)


class WorkflowStage(StrEnum):
    """Workflow execution stages"""
    INIT = "INIT"
    COLLECT_DATA = "COLLECT_DATA"
    ANALYZE_VIOLATIONS = "ANALYZE_VIOLATIONS"
    ASSESS_RISK = "ASSESS_RISK"
    SEND_NOTIFICATIONS = "SEND_NOTIFICATIONS"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class WorkflowState(TypedDict):
    """State object for LangGraph workflow"""
    stage: str
    scan_id: str | None
    users_collected: int
    violations_detected: int
    notifications_sent: int
    errors: Annotated[list[str], operator.add]
    results: dict[str, Any]
    start_time: datetime
    end_time: datetime | None


class ComplianceOrchestrator:
    """
    Orchestrator for coordinating all compliance agents using LangGraph
    """

    def __init__(
        self,
        netsuite_client: NetSuiteClient,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        violation_repo: ViolationRepository,
        sod_rule_repo: SODRuleRepository,
        notification_recipients: list[str] | None = None
    ):
        """
        Initialize Compliance Orchestrator

        Args:
            netsuite_client: NetSuite client instance
            user_repo: User repository
            role_repo: Role repository
            violation_repo: Violation repository
            sod_rule_repo: SOD rule repository
            notification_recipients: Email addresses for notifications
        """
        self.netsuite_client = netsuite_client
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.violation_repo = violation_repo
        self.sod_rule_repo = sod_rule_repo
        self.notification_recipients = notification_recipients or []

        # Initialize agents
        self.data_collector = DataCollectionAgent(enable_scheduler=False)

        self.analyzer = SODAnalysisAgent(
            user_repo=user_repo,
            role_repo=role_repo,
            violation_repo=violation_repo,
            sod_rule_repo=sod_rule_repo
        )

        self.risk_assessor = RiskAssessmentAgent(
            violation_repo=violation_repo,
            user_repo=user_repo
        )

        self.knowledge_base = KnowledgeBaseAgent(role_repo=role_repo)

        self.notifier = NotificationAgent(
            violation_repo=violation_repo,
            user_repo=user_repo
        )

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

        logger.info("Compliance Orchestrator initialized with 5 agents")

    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph workflow for compliance scanning

        Returns:
            StateGraph workflow
        """
        # Create workflow graph
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("collect_data", self._collect_data_node)
        workflow.add_node("analyze_violations", self._analyze_violations_node)
        workflow.add_node("assess_risk", self._assess_risk_node)
        workflow.add_node("send_notifications", self._send_notifications_node)
        workflow.add_node("finalize", self._finalize_node)

        # Define edges
        workflow.set_entry_point("collect_data")

        workflow.add_edge("collect_data", "analyze_violations")
        workflow.add_edge("analyze_violations", "assess_risk")
        workflow.add_edge("assess_risk", "send_notifications")
        workflow.add_edge("send_notifications", "finalize")
        workflow.add_edge("finalize", END)

        # Compile workflow
        return workflow.compile()

    def _collect_data_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node 1: Collect user data from NetSuite

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info("Stage 1: Collecting data from NetSuite")

        try:
            # Trigger full sync — DataCollectionAgent handles all storage internally
            result = self.data_collector.full_sync(triggered_by='orchestrator')

            if result['success']:
                state['users_collected'] = result.get('users_synced', 0)
                state['results']['data_collection'] = result
                state['stage'] = WorkflowStage.COLLECT_DATA.value

                logger.info(f"Data collection complete: {result.get('users_synced', 0)} users")
            else:
                error_msg = f"Data collection failed: {result.get('error')}"
                logger.error(error_msg)
                state['errors'].append(error_msg)
                state['stage'] = WorkflowStage.ERROR.value

        except Exception as e:
            error_msg = f"Error in data collection: {str(e)}"
            logger.error(error_msg)
            state['errors'].append(error_msg)
            state['stage'] = WorkflowStage.ERROR.value

        return state

    def _analyze_violations_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node 2: Analyze users for SOD violations

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info("Stage 2: Analyzing SOD violations")

        try:
            # Run SOD analysis on all users
            result = self.analyzer.analyze_all_users(scan_id=state.get('scan_id'))

            if result['success']:
                state['violations_detected'] = result['stats']['violations_detected']
                state['results']['analysis'] = result
                state['stage'] = WorkflowStage.ANALYZE_VIOLATIONS.value

                logger.info(
                    f"Analysis complete: {result['stats']['violations_detected']} violations detected"
                )
            else:
                error_msg = f"Analysis failed: {result.get('error')}"
                logger.error(error_msg)
                state['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error in analysis: {str(e)}"
            logger.error(error_msg)
            state['errors'].append(error_msg)

        return state

    def _assess_risk_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node 3: Assess organization-wide risk

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info("Stage 3: Assessing organization risk")

        try:
            # Assess organization risk
            result = self.risk_assessor.assess_organization_risk()

            if result['success']:
                state['results']['risk_assessment'] = result
                state['stage'] = WorkflowStage.ASSESS_RISK.value

                logger.info(
                    f"Risk assessment complete: "
                    f"Organization risk level = {result['organization_risk_level']}"
                )
            else:
                error_msg = f"Risk assessment failed: {result.get('error')}"
                logger.error(error_msg)
                state['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"Error in risk assessment: {str(e)}"
            logger.error(error_msg)
            state['errors'].append(error_msg)

        return state

    def _send_notifications_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node 4: Send notifications for critical violations

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info("Stage 4: Sending notifications")

        try:
            # Send batch notification for critical violations
            if self.notification_recipients:
                result = self.notifier.notify_critical_violations_batch(
                    recipients=self.notification_recipients,
                    channels=['EMAIL', 'SLACK']
                )

                if result['success']:
                    state['notifications_sent'] = result.get('violations_count', 0)
                    state['results']['notifications'] = result
                    logger.info("Notifications sent successfully")
                else:
                    logger.warning("Notification delivery had issues")
                    state['results']['notifications'] = result
            else:
                logger.info("No notification recipients configured - skipping")
                state['results']['notifications'] = {
                    'success': True,
                    'message': 'No recipients configured'
                }

            state['stage'] = WorkflowStage.SEND_NOTIFICATIONS.value

        except Exception as e:
            error_msg = f"Error sending notifications: {str(e)}"
            logger.error(error_msg)
            state['errors'].append(error_msg)

        return state

    def _finalize_node(self, state: WorkflowState) -> WorkflowState:
        """
        Node 5: Finalize workflow and create audit trail

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        logger.info("Stage 5: Finalizing workflow")

        state['end_time'] = datetime.now()
        state['stage'] = WorkflowStage.COMPLETE.value

        duration = (state['end_time'] - state['start_time']).total_seconds()

        logger.info(f"Workflow complete in {duration:.2f}s")
        logger.info(f"  Users collected: {state['users_collected']}")
        logger.info(f"  Violations detected: {state['violations_detected']}")
        logger.info(f"  Notifications sent: {state['notifications_sent']}")

        if state['errors']:
            logger.warning(f"  Errors encountered: {len(state['errors'])}")

        return state

    def execute_compliance_scan(
        self,
        scan_id: str | None = None
    ) -> dict[str, Any]:
        """
        Execute full compliance scan workflow

        Args:
            scan_id: Optional scan ID for tracking

        Returns:
            Workflow execution results
        """
        logger.info("="*80)
        logger.info("STARTING COMPLIANCE SCAN")
        logger.info("="*80)

        # Initialize state
        initial_state: WorkflowState = {
            'stage': WorkflowStage.INIT.value,
            'scan_id': scan_id,
            'users_collected': 0,
            'violations_detected': 0,
            'notifications_sent': 0,
            'errors': [],
            'results': {},
            'start_time': datetime.now(),
            'end_time': None
        }

        try:
            # Execute workflow
            final_state = self.workflow.invoke(initial_state)

            # Build result summary
            result = {
                'success': len(final_state.get('errors', [])) == 0,
                'scan_id': scan_id,
                'stage': final_state.get('stage'),
                'summary': {
                    'users_collected': final_state.get('users_collected', 0),
                    'violations_detected': final_state.get('violations_detected', 0),
                    'notifications_sent': final_state.get('notifications_sent', 0)
                },
                'duration_seconds': (
                    final_state['end_time'] - final_state['start_time']
                ).total_seconds() if final_state.get('end_time') else 0,
                'errors': final_state.get('errors', []),
                'results': final_state.get('results', {}),
                'timestamp': datetime.now().isoformat()
            }

            logger.info("="*80)
            logger.info("COMPLIANCE SCAN COMPLETE")
            logger.info("="*80)

            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Workflow execution failed'
            }

    def execute_user_scan(self, user_email: str) -> dict[str, Any]:
        """
        Execute targeted scan for a specific user

        Args:
            user_email: User email to scan

        Returns:
            User scan results
        """
        logger.info(f"Executing targeted scan for user: {user_email}")

        try:
            # Get user from NetSuite
            user_data = self.netsuite_client.get_user_by_email(user_email)

            if not user_data['success']:
                return {
                    'success': False,
                    'error': 'User not found in NetSuite'
                }

            # Store user in database
            user = self.user_repo.upsert_user(user_data['data'])

            # Analyze for violations
            violations = self.analyzer._analyze_user(user)

            # Calculate risk score
            risk_result = self.risk_assessor.calculate_user_risk_score(str(user.id))

            # Send notification if high risk
            if risk_result['risk_level'] in ['CRITICAL', 'HIGH'] and self.notification_recipients:
                self.notifier.notify_risk_threshold_exceeded(
                    user=user,
                    risk_score=risk_result['risk_score'],
                    risk_level=risk_result['risk_level'],
                    recipients=self.notification_recipients,
                    channels=['EMAIL', 'SLACK']
                )

            return {
                'success': True,
                'user_email': user_email,
                'violations': len(violations),
                'risk_score': risk_result['risk_score'],
                'risk_level': risk_result['risk_level'],
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"User scan failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_compliance_status(self) -> dict[str, Any]:
        """
        Get current compliance status summary

        Returns:
            Compliance status report
        """
        logger.info("Getting compliance status")

        try:
            # Get violation summary
            violation_summary = self.violation_repo.get_violation_summary()

            # Get organization risk
            risk_assessment = self.risk_assessor.assess_organization_risk()

            # Get knowledge base stats
            kb_stats = self.knowledge_base.get_knowledge_base_stats()

            return {
                'success': True,
                'violations': violation_summary,
                'risk_assessment': risk_assessment,
                'knowledge_base': kb_stats,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get compliance status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


# Factory function
def create_orchestrator(
    netsuite_client: NetSuiteClient,
    user_repo: UserRepository,
    role_repo: RoleRepository,
    violation_repo: ViolationRepository,
    sod_rule_repo: SODRuleRepository,
    notification_recipients: list[str] | None = None
) -> ComplianceOrchestrator:
    """Create a configured Compliance Orchestrator instance"""
    return ComplianceOrchestrator(
        netsuite_client=netsuite_client,
        user_repo=user_repo,
        role_repo=role_repo,
        violation_repo=violation_repo,
        sod_rule_repo=sod_rule_repo,
        notification_recipients=notification_recipients
    )
