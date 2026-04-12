"""
Notification Agent - Multi-channel alert system

This agent is responsible for:
1. Email notifications (SendGrid)
2. Slack notifications
3. Notification template management
4. Multi-channel delivery
5. Notification tracking and audit
"""

import logging
import os
from datetime import datetime
from enum import StrEnum
from typing import Any

from models.database import (
    User,
    Violation,
    ViolationSeverity,
)
from repositories.job_role_mapping_repository import JobRoleMappingRepository
from repositories.user_repository import UserRepository
from repositories.violation_repository import ViolationRepository
from services.cache_service import get_cache_service
from services.llm import LLMMessage, get_llm_from_config

logger = logging.getLogger(__name__)


class NotificationPriority(StrEnum):
    """Notification priority levels"""
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class NotificationAgent:
    """Agent for sending multi-channel notifications"""

    def __init__(
        self,
        violation_repo: ViolationRepository,
        user_repo: UserRepository,
        job_role_mapping_repo: JobRoleMappingRepository | None = None,
        sendgrid_api_key: str | None = None,
        slack_webhook_url: str | None = None,
        enable_cache: bool = True
    ):
        """
        Initialize Notification Agent

        Args:
            violation_repo: Violation repository instance
            user_repo: User repository instance
            job_role_mapping_repo: Job role mapping repository instance
            sendgrid_api_key: SendGrid API key for email
            slack_webhook_url: Slack webhook URL for notifications
            enable_cache: Whether to enable Redis caching for AI analysis
        """
        self.violation_repo = violation_repo
        self.user_repo = user_repo
        self.job_role_mapping_repo = job_role_mapping_repo

        # Initialize cache service
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            logger.warning("REDIS_URL not set — cache service will be disabled")
            enable_cache = False
            redis_url = ''
        self.cache = get_cache_service(redis_url=redis_url, enabled=enable_cache)
        if self.cache.enabled:
            logger.info("Cache service enabled for AI analysis")
        else:
            logger.warning("Cache service disabled - all LLM calls will be fresh")

        # Initialize email client (SendGrid)
        self.sendgrid_api_key = sendgrid_api_key or os.getenv('SENDGRID_API_KEY')
        self.email_enabled = bool(self.sendgrid_api_key)

        if self.email_enabled:
            try:
                from sendgrid import SendGridAPIClient
                self.sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
                logger.info("SendGrid email client initialized")
            except ImportError:
                logger.warning("sendgrid package not installed. Email notifications disabled.")
                self.email_enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid: {str(e)}")
                self.email_enabled = False

        # Initialize Slack client
        self.slack_webhook_url = slack_webhook_url or os.getenv('SLACK_WEBHOOK_URL')
        self.slack_enabled = bool(self.slack_webhook_url)

        if self.slack_enabled:
            logger.info("Slack notifications enabled")

        # Initialize AI analysis using LLM abstraction layer
        try:
            self.llm = get_llm_from_config()
            self.ai_enabled = True
            logger.info(f"AI analysis enabled ({self.llm.get_provider_name()} - {self.llm.get_model_name()})")
        except Exception as e:
            self.llm = None
            self.ai_enabled = False
            logger.warning(f"AI analysis disabled: {str(e)}")

        logger.info(f"Notification Agent initialized (Email: {self.email_enabled}, Slack: {self.slack_enabled}, AI: {self.ai_enabled})")

    def notify_violation_detected(
        self,
        violation: Violation,
        recipients: list[str],
        channels: list[str] = None
    ) -> dict[str, Any]:
        """
        Send notification when a new violation is detected

        Args:
            violation: Violation object
            recipients: List of email addresses
            channels: List of channels ('EMAIL', 'SLACK')

        Returns:
            Notification results
        """
        if channels is None:
            channels = ['EMAIL']
        logger.info(f"Sending violation notification: {violation.id}")

        # Determine priority based on severity
        priority = self._severity_to_priority(violation.severity)

        # Generate notification content
        subject = self._generate_subject(violation, priority)
        message = self._generate_violation_message(violation)

        results = []

        # Send via email
        if 'EMAIL' in channels and self.email_enabled:
            email_result = self._send_email(
                recipients=recipients,
                subject=subject,
                message=message,
                violation=violation
            )
            results.append(email_result)

        # Send via Slack
        if 'SLACK' in channels and self.slack_enabled:
            slack_result = self._send_slack(
                message=message,
                violation=violation,
                priority=priority
            )
            results.append(slack_result)

        # Fallback to console if no channels enabled
        if not results:
            logger.warning("No notification channels enabled - logging to console")
            results.append(self._log_to_console(subject, message))

        return {
            'success': all(r.get('success', False) for r in results),
            'violation_id': str(violation.id),
            'channels_sent': [r['channel'] for r in results if r.get('success')],
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    def notify_critical_violations_batch(
        self,
        recipients: list[str],
        channels: list[str] = None
    ) -> dict[str, Any]:
        """
        Send batch notification for all open critical violations

        Args:
            recipients: List of email addresses
            channels: List of channels

        Returns:
            Notification results
        """
        if channels is None:
            channels = ['EMAIL', 'SLACK']
        logger.info("Sending batch notification for critical violations")

        # Get all critical violations
        critical_violations = self.violation_repo.get_open_violations(
            severity=ViolationSeverity.CRITICAL
        )

        if not critical_violations:
            logger.info("No critical violations to report")
            return {
                'success': True,
                'message': 'No critical violations',
                'violations_count': 0
            }

        # Generate summary
        subject = f"🚨 URGENT: {len(critical_violations)} Critical SOD Violations Detected"
        message = self._generate_batch_message(critical_violations)

        results = []

        # Send via email
        if 'EMAIL' in channels and self.email_enabled:
            email_result = self._send_email(
                recipients=recipients,
                subject=subject,
                message=message,
                is_batch=True
            )
            results.append(email_result)

        # Send via Slack
        if 'SLACK' in channels and self.slack_enabled:
            slack_result = self._send_slack(
                message=message,
                priority=NotificationPriority.URGENT,
                is_batch=True,
                violation_count=len(critical_violations)
            )
            results.append(slack_result)

        if not results:
            results.append(self._log_to_console(subject, message))

        return {
            'success': all(r.get('success', False) for r in results),
            'violations_count': len(critical_violations),
            'channels_sent': [r['channel'] for r in results if r.get('success')],
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    def notify_risk_threshold_exceeded(
        self,
        user: User,
        risk_score: float,
        risk_level: str,
        recipients: list[str],
        channels: list[str] = None
    ) -> dict[str, Any]:
        """
        Notify when user risk score exceeds threshold

        Args:
            user: User object
            risk_score: Current risk score
            risk_level: Risk level (CRITICAL, HIGH, etc.)
            recipients: List of email addresses
            channels: Notification channels

        Returns:
            Notification results
        """
        if channels is None:
            channels = ['EMAIL', 'SLACK']
        logger.info(f"Sending risk threshold notification for user: {user.email}")

        subject = f"⚠️  Risk Alert: {user.email} - {risk_level} Risk ({risk_score}/100)"
        message = self._generate_risk_alert_message(user, risk_score, risk_level)

        results = []

        if 'EMAIL' in channels and self.email_enabled:
            email_result = self._send_email(
                recipients=recipients,
                subject=subject,
                message=message,
                user=user
            )
            results.append(email_result)

        if 'SLACK' in channels and self.slack_enabled:
            slack_result = self._send_slack(
                message=message,
                priority=NotificationPriority.HIGH,
                user=user
            )
            results.append(slack_result)

        if not results:
            results.append(self._log_to_console(subject, message))

        return {
            'success': all(r.get('success', False) for r in results),
            'user_id': str(user.id),
            'user_email': user.email,
            'risk_score': risk_score,
            'channels_sent': [r['channel'] for r in results if r.get('success')],
            'results': results,
            'timestamp': datetime.now().isoformat()
        }

    def _send_email(
        self,
        recipients: list[str],
        subject: str,
        message: str,
        violation: Violation | None = None,
        user: User | None = None,
        is_batch: bool = False
    ) -> dict[str, Any]:
        """Send email notification via SendGrid"""
        if not self.email_enabled:
            return {
                'success': False,
                'channel': 'EMAIL',
                'error': 'Email not configured'
            }

        try:
            from sendgrid.helpers.mail import Content, Email, Mail, To

            # Create HTML content
            html_content = self._format_email_html(message, violation, user)

            # Build email
            from_email = Email(os.getenv('SENDGRID_FROM_EMAIL', 'noreply@compliance.system'))
            to_emails = [To(email) for email in recipients]
            content = Content("text/html", html_content)

            mail = Mail(
                from_email=from_email,
                to_emails=to_emails,
                subject=subject,
                html_content=content
            )

            # Send email
            response = self.sendgrid_client.send(mail)

            logger.info(f"Email sent successfully to {len(recipients)} recipients")

            return {
                'success': True,
                'channel': 'EMAIL',
                'recipients': recipients,
                'status_code': response.status_code
            }

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {
                'success': False,
                'channel': 'EMAIL',
                'error': str(e)
            }

    def _send_slack(
        self,
        message: str,
        violation: Violation | None = None,
        user: User | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        is_batch: bool = False,
        violation_count: int = 0
    ) -> dict[str, Any]:
        """Send Slack notification via webhook"""
        if not self.slack_enabled:
            return {
                'success': False,
                'channel': 'SLACK',
                'error': 'Slack not configured'
            }

        try:
            import requests

            # Format for Slack
            slack_message = self._format_slack_message(
                message,
                violation,
                user,
                priority,
                is_batch,
                violation_count
            )

            # Send to Slack
            response = requests.post(
                self.slack_webhook_url,
                json=slack_message,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Slack notification sent successfully")
                return {
                    'success': True,
                    'channel': 'SLACK',
                    'status_code': response.status_code
                }
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
                return {
                    'success': False,
                    'channel': 'SLACK',
                    'error': f"HTTP {response.status_code}"
                }

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return {
                'success': False,
                'channel': 'SLACK',
                'error': str(e)
            }

    def _log_to_console(self, subject: str, message: str) -> dict[str, Any]:
        """Log notification to console (fallback)"""
        logger.info("="*80)
        logger.info(f"NOTIFICATION: {subject}")
        logger.info("="*80)
        logger.info(message)
        logger.info("="*80)

        return {
            'success': True,
            'channel': 'CONSOLE',
            'message': 'Logged to console'
        }

    def _severity_to_priority(self, severity: ViolationSeverity) -> NotificationPriority:
        """Map violation severity to notification priority"""
        mapping = {
            ViolationSeverity.CRITICAL: NotificationPriority.URGENT,
            ViolationSeverity.HIGH: NotificationPriority.HIGH,
            ViolationSeverity.MEDIUM: NotificationPriority.NORMAL,
            ViolationSeverity.LOW: NotificationPriority.LOW
        }
        return mapping.get(severity, NotificationPriority.NORMAL)

    def _generate_subject(self, violation: Violation, priority: NotificationPriority) -> str:
        """Generate email subject line"""
        priority_icon = {
            NotificationPriority.URGENT: "🚨",
            NotificationPriority.HIGH: "⚠️ ",
            NotificationPriority.NORMAL: "📋",
            NotificationPriority.LOW: "ℹ️ "
        }

        icon = priority_icon.get(priority, "📋")
        return f"{icon} SOD Violation Detected: {violation.title}"

    def _generate_violation_message(self, violation: Violation) -> str:
        """Generate violation notification message"""
        user_email = violation.user.email if violation.user else 'Unknown'
        rule_name = violation.rule.rule_name if violation.rule else 'Unknown'

        message = f"""
SOD Violation Detected

User: {user_email}
Severity: {violation.severity.value}
Risk Score: {violation.risk_score}/100

Rule: {rule_name}
Description: {violation.description}

Conflicting Roles: {', '.join(violation.conflicting_roles) if violation.conflicting_roles else 'N/A'}

Department: {violation.violation_metadata.get('department', 'N/A') if violation.violation_metadata else 'N/A'}

Detected At: {violation.detected_at.strftime('%Y-%m-%d %H:%M:%S') if violation.detected_at else 'Unknown'}

Remediation Guidance:
{violation.violation_metadata.get('remediation_guidance', 'Review user access and remove conflicting roles.') if violation.violation_metadata else 'Review user access and remove conflicting roles.'}

Action Required: Please review this violation and take appropriate action.
"""
        return message.strip()

    def _generate_batch_message(self, violations: list[Violation]) -> str:
        """Generate batch violation message"""
        message_parts = [
            "Critical SOD Violations Summary",
            f"Total Violations: {len(violations)}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Top 10 Critical Violations:",
            ""
        ]

        for i, violation in enumerate(violations[:10], 1):
            user_email = violation.user.email if violation.user else 'Unknown'
            message_parts.append(
                f"{i}. {user_email} - {violation.title} (Risk: {violation.risk_score}/100)"
            )

        message_parts.extend([
            "",
            "Action Required:",
            "1. Review all critical violations immediately",
            "2. Prioritize users with multiple violations",
            "3. Begin remediation within 24 hours",
            "4. Document all actions taken"
        ])

        return "\n".join(message_parts)

    def _generate_risk_alert_message(
        self,
        user: User,
        risk_score: float,
        risk_level: str
    ) -> str:
        """Generate risk threshold alert message"""
        message = f"""
Risk Threshold Alert

User: {user.email}
Name: {user.name or 'N/A'}
Department: {user.department or 'N/A'}
Title: {user.title or 'N/A'}

Current Risk Score: {risk_score}/100
Risk Level: {risk_level}

Roles: {len(user.user_roles)}
Role Names: {', '.join([ur.role.name for ur in user.user_roles]) if user.user_roles else 'None'}

This user has exceeded the acceptable risk threshold and requires immediate review.

Recommended Actions:
1. Review user's access rights
2. Verify all role assignments are necessary
3. Check for SOD violations
4. Consider implementing compensating controls
5. Schedule access recertification
"""
        return message.strip()

    def _format_email_html(
        self,
        message: str,
        violation: Violation | None = None,
        user: User | None = None
    ) -> str:
        """Format message as HTML for email"""
        # Simple HTML template
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #d32f2f; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ padding: 20px; background-color: #f5f5f5; border-radius: 5px; margin-top: 10px; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
                pre {{ white-space: pre-wrap; word-wrap: break-word; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>SOD Compliance Alert</h2>
                </div>
                <div class="content">
                    <pre>{message}</pre>
                </div>
                <div class="footer">
                    <p>This is an automated notification from the SOD Compliance System.</p>
                    <p>For questions, contact your compliance team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def _format_slack_message(
        self,
        message: str,
        violation: Violation | None = None,
        user: User | None = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        is_batch: bool = False,
        violation_count: int = 0
    ) -> dict[str, Any]:
        """Format message for Slack"""
        # Color based on priority
        color_map = {
            NotificationPriority.URGENT: "#d32f2f",
            NotificationPriority.HIGH: "#f57c00",
            NotificationPriority.NORMAL: "#1976d2",
            NotificationPriority.LOW: "#388e3c"
        }

        color = color_map.get(priority, "#1976d2")

        # Build Slack message with blocks
        slack_message = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "🚨 SOD Compliance Alert" if priority == NotificationPriority.URGENT else "📋 SOD Compliance Notification"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"```{message}```"
                            }
                        }
                    ]
                }
            ]
        }

        if is_batch:
            slack_message["text"] = f"🚨 {violation_count} Critical SOD Violations Detected"
        elif violation:
            slack_message["text"] = f"SOD Violation: {violation.title}"
        elif user:
            slack_message["text"] = f"Risk Alert: {user.email}"

        return slack_message

    def send_compliance_report(
        self,
        scan_summary: dict[str, Any],
        recipients: list[str],
        channels: list[str] = None
    ) -> dict[str, Any]:
        """
        Send final compliance scan report

        Args:
            scan_summary: Dictionary containing:
                - scan_id: Scan identifier
                - users_analyzed: Total users scanned
                - total_violations: Total violations found
                - violations_by_severity: Dict with counts per severity
                - top_violators: List of top violating users
                - department_stats: Dict with department breakdown
                - compliance_rate: Overall compliance percentage
                - scan_duration: Time taken for scan
                - timestamp: Scan completion time
            recipients: List of email addresses
            channels: List of channels to send to

        Returns:
            Notification results with status per channel
        """
        if channels is None:
            channels = ['EMAIL', 'SLACK', 'CONSOLE']
        logger.info(f"Sending compliance report to {len(recipients)} recipients via {channels}")

        # Generate subject and message
        subject = self._generate_compliance_report_subject(scan_summary)
        message = self._generate_compliance_report_message(scan_summary)

        results = {
            'sent_at': datetime.utcnow().isoformat(),
            'recipients': recipients,
            'channels': {}
        }

        # Send via requested channels
        if 'EMAIL' in channels and self.email_enabled:
            email_result = self._send_email(
                recipients=recipients,
                subject=subject,
                message=message
            )
            results['channels']['EMAIL'] = email_result

        if 'SLACK' in channels and self.slack_enabled:
            slack_result = self._send_slack(
                message=self._format_compliance_report_slack(scan_summary)
            )
            results['channels']['SLACK'] = slack_result

        if 'CONSOLE' in channels:
            console_result = self._log_to_console(subject, message)
            results['channels']['CONSOLE'] = console_result

        logger.info(f"Compliance report sent via {len(results['channels'])} channels")
        return results

    def _generate_compliance_report_subject(self, scan_summary: dict[str, Any]) -> str:
        """Generate subject line for compliance report"""
        total_violations = scan_summary.get('total_violations', 0)
        compliance_rate = scan_summary.get('compliance_rate', 0)

        if total_violations == 0:
            status_icon = "✅"
            status = "All Clear"
        elif compliance_rate >= 90:
            status_icon = "⚠️"
            status = "Minor Issues"
        elif compliance_rate >= 70:
            status_icon = "🚨"
            status = "Action Required"
        else:
            status_icon = "🔴"
            status = "Critical Issues"

        return f"{status_icon} SOD Compliance Report - {status} ({compliance_rate:.1f}% Compliant)"

    def _generate_compliance_report_message(self, scan_summary: dict[str, Any]) -> str:
        """Generate plain text compliance report message"""
        lines = [
            "=" * 70,
            "SOD COMPLIANCE SCAN REPORT",
            "=" * 70,
            "",
            f"Scan ID: {scan_summary.get('scan_id', 'N/A')}",
            f"Completed: {scan_summary.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}",
            f"Duration: {scan_summary.get('scan_duration', 'N/A')}",
            "",
            "=" * 70,
            "SUMMARY STATISTICS",
            "=" * 70,
            "",
            f"Users Analyzed:      {scan_summary.get('users_analyzed', 0):,}",
            f"Total Violations:    {scan_summary.get('total_violations', 0):,}",
            f"Compliance Rate:     {scan_summary.get('compliance_rate', 0):.1f}%",
            ""
        ]

        # Violations by severity
        violations_by_severity = scan_summary.get('violations_by_severity', {})
        if violations_by_severity:
            lines.extend([
                "VIOLATIONS BY SEVERITY:",
                f"  🔴 Critical:  {violations_by_severity.get('CRITICAL', 0):,}",
                f"  🟠 High:      {violations_by_severity.get('HIGH', 0):,}",
                f"  🟡 Medium:    {violations_by_severity.get('MEDIUM', 0):,}",
                f"  🟢 Low:       {violations_by_severity.get('LOW', 0):,}",
                ""
            ])

        # Top violators
        top_violators = scan_summary.get('top_violators', [])
        if top_violators:
            lines.extend([
                "TOP VIOLATORS:",
                ""
            ])
            for i, violator in enumerate(top_violators[:5], 1):
                lines.append(
                    f"  {i}. {violator.get('name', 'Unknown')} ({violator.get('email', 'N/A')})"
                )
                lines.append(
                    f"     Violations: {violator.get('violation_count', 0)} | Risk Score: {violator.get('risk_score', 0)}/100"
                )
            lines.append("")

        # Department statistics
        department_stats = scan_summary.get('department_stats', {})
        if department_stats:
            lines.extend([
                "DEPARTMENT BREAKDOWN:",
                ""
            ])
            # Sort by violation count
            sorted_depts = sorted(
                department_stats.items(),
                key=lambda x: x[1].get('violations', 0),
                reverse=True
            )[:5]

            for dept, stats in sorted_depts:
                compliance = (stats.get('compliant', 0) / max(stats.get('users', 1), 1)) * 100
                lines.append(
                    f"  {dept}: {stats.get('violations', 0)} violations, "
                    f"{stats.get('users', 0)} users, {compliance:.1f}% compliant"
                )
            lines.append("")

        # Recommendations
        lines.extend([
            "=" * 70,
            "RECOMMENDED ACTIONS",
            "=" * 70,
            ""
        ])

        critical_count = violations_by_severity.get('CRITICAL', 0)
        high_count = violations_by_severity.get('HIGH', 0)

        if critical_count > 0:
            lines.append(f"  ⚠️  URGENT: Address {critical_count} CRITICAL violations immediately")
        if high_count > 0:
            lines.append(f"  ⚠️  HIGH: Review and remediate {high_count} HIGH severity violations")
        if scan_summary.get('total_violations', 0) == 0:
            lines.append("  ✅ No violations detected - system is compliant")

        lines.extend([
            "",
            "=" * 70,
            "For detailed analysis, review the full compliance dashboard.",
            "=" * 70
        ])

        return "\n".join(lines)

    def _format_compliance_report_html(self, scan_summary: dict[str, Any]) -> str:
        """Generate HTML formatted compliance report for email"""
        compliance_rate = scan_summary.get('compliance_rate', 0)
        total_violations = scan_summary.get('total_violations', 0)

        # Status badge color
        if compliance_rate >= 95:
            badge_color = "#4caf50"  # Green
            status_text = "Excellent"
        elif compliance_rate >= 85:
            badge_color = "#ff9800"  # Orange
            status_text = "Good"
        elif compliance_rate >= 70:
            badge_color = "#ff5722"  # Deep Orange
            status_text = "Needs Attention"
        else:
            badge_color = "#f44336"  # Red
            status_text = "Critical"

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .status-badge {{ background: {badge_color}; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block; margin: 10px 0; }}
                .summary-box {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
                .metric-label {{ font-size: 14px; color: #666; }}
                .severity-critical {{ color: #d32f2f; font-weight: bold; }}
                .severity-high {{ color: #f57c00; font-weight: bold; }}
                .severity-medium {{ color: #fbc02d; font-weight: bold; }}
                .severity-low {{ color: #388e3c; font-weight: bold; }}
                .violator {{ background: white; padding: 15px; margin: 10px 0; border-left: 3px solid #ff5722; }}
                .footer {{ background: #f5f5f5; padding: 20px; text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔒 SOD Compliance Report</h1>
                <div class="status-badge">{status_text}: {compliance_rate:.1f}% Compliant</div>
            </div>

            <div class="summary-box">
                <h2>📊 Summary Statistics</h2>
                <div class="metric">
                    <div class="metric-value">{scan_summary.get('users_analyzed', 0):,}</div>
                    <div class="metric-label">Users Analyzed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{total_violations:,}</div>
                    <div class="metric-label">Total Violations</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{compliance_rate:.1f}%</div>
                    <div class="metric-label">Compliance Rate</div>
                </div>
            </div>
        """

        # Violations by severity
        violations_by_severity = scan_summary.get('violations_by_severity', {})
        if violations_by_severity:
            html += """
            <div class="summary-box">
                <h2>🚨 Violations by Severity</h2>
                <ul>
            """
            for severity, count in violations_by_severity.items():
                severity_class = f"severity-{severity.lower()}"
                html += f'<li class="{severity_class}">{severity}: {count:,} violations</li>'
            html += "</ul></div>"

        # Top violators
        top_violators = scan_summary.get('top_violators', [])
        if top_violators:
            html += """
            <div class="summary-box">
                <h2>⚠️ Top Violators</h2>
            """
            for i, violator in enumerate(top_violators[:5], 1):
                html += f"""
                <div class="violator">
                    <strong>{i}. {violator.get('name', 'Unknown')}</strong> ({violator.get('email', 'N/A')})<br>
                    Violations: {violator.get('violation_count', 0)} | Risk Score: {violator.get('risk_score', 0)}/100
                </div>
                """
            html += "</div>"

        # Footer
        html += f"""
            <div class="footer">
                <p>Scan ID: {scan_summary.get('scan_id', 'N/A')}<br>
                Completed: {scan_summary.get('timestamp', 'N/A')}<br>
                Duration: {scan_summary.get('scan_duration', 'N/A')}</p>
                <p>This is an automated compliance report. For detailed analysis, access the compliance dashboard.</p>
            </div>
        </body>
        </html>
        """
        return html

    def _format_compliance_report_slack(self, scan_summary: dict[str, Any]) -> dict[str, Any]:
        """Format compliance report for Slack"""
        compliance_rate = scan_summary.get('compliance_rate', 0)
        total_violations = scan_summary.get('total_violations', 0)
        violations_by_severity = scan_summary.get('violations_by_severity', {})

        # Determine color based on compliance
        if compliance_rate >= 95:
            color = "#4caf50"  # Green
        elif compliance_rate >= 85:
            color = "#ff9800"  # Orange
        else:
            color = "#f44336"  # Red

        # Build violation summary text
        violation_text = ""
        if violations_by_severity:
            violation_text = f"\n🔴 Critical: {violations_by_severity.get('CRITICAL', 0)}"
            violation_text += f"\n🟠 High: {violations_by_severity.get('HIGH', 0)}"
            violation_text += f"\n🟡 Medium: {violations_by_severity.get('MEDIUM', 0)}"
            violation_text += f"\n🟢 Low: {violations_by_severity.get('LOW', 0)}"

        slack_message = {
            "text": f"SOD Compliance Report: {compliance_rate:.1f}% Compliant",
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "🔒 SOD Compliance Scan Complete"
                            }
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Users Analyzed:*\n{scan_summary.get('users_analyzed', 0):,}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Total Violations:*\n{total_violations:,}"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Compliance Rate:*\n{compliance_rate:.1f}%"
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Scan Duration:*\n{scan_summary.get('scan_duration', 'N/A')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Add violations breakdown if present
        if violation_text:
            slack_message["attachments"][0]["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Violations by Severity:*{violation_text}"
                }
            })

        # Add top violators if present
        top_violators = scan_summary.get('top_violators', [])
        if top_violators:
            violators_text = ""
            for i, violator in enumerate(top_violators[:3], 1):
                violators_text += f"\n{i}. {violator.get('name', 'Unknown')} - {violator.get('violation_count', 0)} violations"

            slack_message["attachments"][0]["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top Violators:*{violators_text}"
                }
            })

        return slack_message

    def _generate_ai_analysis(
        self,
        user: User,
        violations: list[Violation],
        role_names: list[str]
    ) -> str:
        """
        Generate AI-powered analysis of why user has compliance issues

        Uses Redis cache to avoid redundant LLM calls for identical scenarios.

        Args:
            user: User object
            violations: List of violations for this user
            role_names: List of role names assigned to user

        Returns:
            AI-generated analysis text (cached if available)
        """
        if not self.ai_enabled or not violations:
            return ""

        # Check cache first
        violation_ids = [str(v.id) for v in violations]
        cached_analysis = self.cache.get_ai_analysis(
            user_id=str(user.id),
            violation_ids=violation_ids,
            role_names=role_names
        )

        if cached_analysis:
            logger.info(f"Using cached AI analysis for user {user.name}")
            return cached_analysis

        # Prepare violation details
        violation_details = []
        for v in violations:
            detail = {
                'rule': v.title,
                'severity': v.severity.value,
                'description': v.description,
                'conflicting_roles': v.conflicting_roles,
                'conflicting_permissions': v.conflicting_permissions
            }
            violation_details.append(detail)

        # Format violation summary
        violation_summary_lines = []
        for i, v in enumerate(violations[:3], 1):  # Top 3 violations
            violation_summary_lines.append(
                f"{i}. {v.title} ({v.severity.value})\n"
                f"   - {v.description[:150]}..."
            )
        violation_summary = "\n".join(violation_summary_lines)

        if len(violations) > 3:
            violation_summary += f"\n... and {len(violations) - 3} more violations"

        # Check if this role combination is acceptable for user's job title
        job_role_context = ""
        if self.job_role_mapping_repo and user.title:
            try:
                validation_result = self.job_role_mapping_repo.check_role_combination_acceptable(
                    user.title,
                    role_names
                )

                if validation_result.get('is_acceptable'):
                    # This is an ACCEPTABLE combination for this job title
                    job_role_context = f"""

═══════════════════════════════════════════════════════════════════
IMPORTANT JOB ROLE CONTEXT - READ THIS FIRST
═══════════════════════════════════════════════════════════════════

For job title '{user.title}', this role combination is ACCEPTABLE and STANDARD per company policy.

✅ This is NOT an unexpected configuration - it is the PROPER setup for this role.

Business Justification:
{validation_result.get('business_justification', 'Role combination approved for this job function')}

Required Compensating Controls: {', '.join(validation_result.get('typical_controls', []))}
Requires Controls: {"YES" if validation_result.get('requires_controls') else "NO"}
Approval Level: {validation_result.get('approval_required', 'Standard approval')}

Your analysis MUST acknowledge that:
1. This configuration is EXPECTED and APPROVED for this job title
2. While technical SOD conflicts exist, they are ACCEPTABLE with proper controls
3. Focus on COMPENSATING CONTROLS (monitoring, approval workflows, audit logs)
4. DO NOT recommend role removal - recommend control implementation instead
5. This is a legitimate business need, not a compliance violation to fix

Shift your tone from "violation that must be fixed" to "accepted configuration that requires oversight."
═══════════════════════════════════════════════════════════════════
"""
            except Exception as e:
                logger.error(f"Error checking job role mapping: {str(e)}")

        # Create messages using LLM abstraction layer
        system_message = """You are a compliance analyst. Provide ONLY a brief summary paragraph.

STRICT REQUIREMENTS:
- Maximum 3-4 sentences total
- NO markdown headers (no #, ##, ###)
- NO bullet points or lists
- NO sections (Summary, Risk Context, Required Action, etc.)
- Plain text paragraph ONLY

Format: One short paragraph that states:
1. Is this configuration acceptable for the job title? (Yes/No)
2. Key risk or justification (one sentence)
3. Primary action needed (implement controls OR remove role)

If ACCEPTABLE for job title: Focus on compensating controls needed.
If NOT ACCEPTABLE: State which role to remove."""

        user_message = f"""User: {user.name} ({user.title or "Unknown"})
Roles: {', '.join(role_names)}
Violations: {len(violations)}
{violation_summary}{job_role_context}

Provide 2-3 sentence summary: Is this OK for the job title? What action is needed?"""

        messages = [
            LLMMessage(role="system", content=system_message),
            LLMMessage(role="user", content=user_message)
        ]

        # Generate analysis
        try:
            response = self.llm.generate(messages)
            analysis = response.content.strip()

            # Cache the result for future use (24 hour TTL)
            if analysis:
                self.cache.set_ai_analysis(
                    user_id=str(user.id),
                    violation_ids=violation_ids,
                    role_names=role_names,
                    analysis=analysis,
                    ttl=86400  # 24 hours
                )
                logger.info(f"Cached AI analysis for user {user.name}")

            return analysis

        except Exception as e:
            logger.error(f"Failed to generate AI analysis: {str(e)}")
            return ""

    def generate_user_comparison_table(
        self,
        user_emails: list[str],
        include_border: bool = True
    ) -> str:
        """
        Generate a formatted comparison table for multiple users

        Args:
            user_emails: List of user email addresses to compare
            include_border: Whether to include ASCII borders

        Returns:
            Formatted ASCII table string
        """
        # Fetch user data and violations
        user_data = []
        for email in user_emails:
            user = self.user_repo.get_user_by_email(email)
            if not user:
                continue

            # Get violations for this user
            violations = self.violation_repo.get_violations_by_user(
                str(user.id),
                status=None  # Get all violations
            )

            # Calculate metrics
            total_roles = len(user.user_roles) if hasattr(user, 'user_roles') else 0
            violation_count = len(violations)

            # Get role names
            role_names = []
            if hasattr(user, 'user_roles'):
                for user_role in user.user_roles:
                    if user_role.role:
                        role_names.append(user_role.role.role_name)
            roles_str = ", ".join(role_names) if role_names else "No roles"

            critical_count = sum(1 for v in violations if v.severity == ViolationSeverity.CRITICAL)
            high_count = sum(1 for v in violations if v.severity == ViolationSeverity.HIGH)
            medium_count = sum(1 for v in violations if v.severity == ViolationSeverity.MEDIUM)

            # Calculate risk score (0-100)
            if violations:
                risk_score = int(max(v.risk_score for v in violations))
            else:
                risk_score = 0

            # Determine compliance status
            if critical_count > 0:
                compliance_status = "NON-COMPLIANT"
                compliance_icon = "✗"
            elif high_count > 0:
                compliance_status = "AT-RISK"
                compliance_icon = "⚠"
            elif medium_count > 0:
                compliance_status = "REVIEW NEEDED"
                compliance_icon = "⚠"
            else:
                compliance_status = "COMPLIANT"
                compliance_icon = "✓"

            # Determine remediation time
            if critical_count > 0:
                remediation_time = "Immediate"
            elif high_count > 0:
                remediation_time = "24 hours"
            elif medium_count > 0:
                remediation_time = "1 week"
            else:
                remediation_time = "None needed"

            # Priority actions
            priority_actions = []
            if critical_count > 0:
                priority_actions.append(f"{critical_count} immediate")
            if high_count > 0:
                priority_actions.append(f"{high_count} urgent")

            if not priority_actions:
                priority_str = "None"
            else:
                priority_str = ", ".join(priority_actions)

            # Generate AI analysis for this user
            ai_analysis = ""
            if violations:
                ai_analysis = self._generate_ai_analysis(user, violations, role_names)

            user_data.append({
                'name': user.name,
                'email': email,
                'total_roles': total_roles,
                'assigned_roles': roles_str,
                'violations': violation_count,
                'compliance_icon': compliance_icon,
                'risk_score': risk_score,
                'compliance_status': compliance_status,
                'critical_issues': critical_count,
                'high_severity': high_count,
                'medium_severity': medium_count,
                'remediation_time': remediation_time,
                'priority_actions': priority_str,
                'ai_analysis': ai_analysis
            })

        if not user_data:
            return "No users found for comparison"

        # Build the table
        table = self._format_comparison_table(user_data, include_border)

        # Add AI analysis summaries
        if any(u.get('ai_analysis') for u in user_data):
            table += "\n\n" + "="*80
            table += "\nAI COMPLIANCE ANALYSIS"
            table += "\n" + "="*80 + "\n"

            for user in user_data:
                if user.get('ai_analysis'):
                    table += f"\n📋 {user['name']}:\n"
                    table += f"{user['ai_analysis']}\n"

        return table

    def _format_comparison_table(
        self,
        user_data: list[dict[str, Any]],
        include_border: bool
    ) -> str:
        """Format the user comparison data as an ASCII table"""

        # Define column widths

        # Prepare rows
        rows = []

        # Metrics to display
        metrics = [
            ('Total Roles', 'total_roles'),
            ('Assigned Roles', 'assigned_roles'),
            ('Compliance Status', 'compliance_status'),
        ]

        # Build header row
        header = ['Metric'] + [f"User: {u['name']}" for u in user_data]
        rows.append(header)

        # Build data rows
        for metric_info in metrics:
            metric_name = metric_info[0]
            metric_key = metric_info[1]
            include_icon = metric_info[2] if len(metric_info) > 2 else False
            suffix = metric_info[3] if len(metric_info) > 3 else ''

            row = [metric_name]
            for user in user_data:
                value = user[metric_key]

                if include_icon:
                    # Add compliance icon
                    icon = user['compliance_icon']
                    cell_value = f"{value} {icon}"
                elif suffix:
                    cell_value = f"{value}{suffix}"
                else:
                    cell_value = str(value)

                row.append(cell_value)

            rows.append(row)

        # Calculate column widths
        col_widths = []
        num_cols = len(rows[0])
        for col_idx in range(num_cols):
            max_width = max(len(str(row[col_idx])) for row in rows)
            col_widths.append(max_width + 2)  # Add padding

        # Format the table
        lines = []

        if include_border:
            # Top border
            border_line = "+" + "+".join(["-" * w for w in col_widths]) + "+"
            lines.append(border_line)

        # Format each row
        for row_idx, row in enumerate(rows):
            if include_border:
                formatted_row = "|" + "|".join([
                    f" {str(row[i]).ljust(col_widths[i] - 1)}" for i in range(num_cols)
                ]) + "|"
            else:
                formatted_row = " | ".join([
                    str(row[i]).ljust(col_widths[i] - 2) for i in range(num_cols)
                ])

            lines.append(formatted_row)

            # Add separator after header
            if row_idx == 0 and include_border:
                lines.append(border_line)

        if include_border:
            # Bottom border
            lines.append(border_line)

        return "\n".join(lines)


# Factory function
def create_notifier(
    violation_repo: ViolationRepository,
    user_repo: UserRepository,
    sendgrid_api_key: str | None = None,
    slack_webhook_url: str | None = None
) -> NotificationAgent:
    """Create a configured Notification Agent instance"""
    return NotificationAgent(
        violation_repo=violation_repo,
        user_repo=user_repo,
        sendgrid_api_key=sendgrid_api_key,
        slack_webhook_url=slack_webhook_url
    )
