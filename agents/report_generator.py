"""
Report Generator Agent - Customizable SOD Compliance Reports

This agent uses Claude to generate customized reports based on user preferences.
"""

import logging
from datetime import datetime
from enum import StrEnum
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from utils.langchain_callback import TokenTrackingCallback

logger = logging.getLogger(__name__)


class ReportType(StrEnum):
    """Report types available"""
    EXECUTIVE_SUMMARY = "executive_summary"
    DETAILED_ANALYSIS = "detailed_analysis"
    TECHNICAL_REPORT = "technical_report"
    AUDIT_REPORT = "audit_report"
    DEPARTMENT_REPORT = "department_report"
    TREND_ANALYSIS = "trend_analysis"


class ReportFormat(StrEnum):
    """Output formats"""
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    TEXT = "text"


class AudienceType(StrEnum):
    """Target audience"""
    EXECUTIVES = "executives"
    COMPLIANCE_TEAM = "compliance_team"
    AUDITORS = "auditors"
    IT_SECURITY = "it_security"
    DEPARTMENT_HEADS = "department_heads"


class ReportGeneratorAgent:
    """
    Agent for generating customizable SOD compliance reports using Claude.

    Takes analysis results and user preferences to generate tailored reports.
    """

    def __init__(self, model: str = "claude-sonnet-4-5"):
        """
        Initialize Report Generator Agent

        Args:
            model: Claude model to use for generation (Sonnet default — sufficient for structured reports)
        """
        self._token_callback = TokenTrackingCallback(agent_name="report_generator", operation="report_generation")
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.3,
            max_tokens=2048,
            callbacks=[self._token_callback]
        )
        logger.info(f"Report Generator initialized with model: {model}")

    def generate_custom_report(
        self,
        analysis_data: dict[str, Any],
        report_type: ReportType = ReportType.EXECUTIVE_SUMMARY,
        audience: AudienceType = AudienceType.EXECUTIVES,
        focus_areas: list[str] | None = None,
        include_sections: list[str] | None = None,
        exclude_sections: list[str] | None = None,
        custom_instructions: str | None = None
    ) -> dict[str, Any]:
        """
        Generate a customized compliance report

        Args:
            analysis_data: Dict containing:
                - users_analyzed: int
                - total_violations: int
                - violations_by_severity: Dict
                - top_violators: List[Dict]
                - department_stats: Dict
                - risk_distribution: Dict
                - violation_details: List[Dict]
            report_type: Type of report to generate
            audience: Target audience for the report
            focus_areas: Specific areas to emphasize (e.g., ["Finance", "HIGH severity"])
            include_sections: Sections to include
            exclude_sections: Sections to exclude
            custom_instructions: Additional instructions for the LLM

        Returns:
            Dict with generated report and metadata
        """
        logger.info(f"Generating {report_type} report for {audience}")

        # Build dynamic prompt based on preferences
        prompt = self._build_prompt(
            report_type=report_type,
            audience=audience,
            focus_areas=focus_areas,
            include_sections=include_sections,
            exclude_sections=exclude_sections,
            custom_instructions=custom_instructions
        )

        # Generate report
        chain = prompt | self.llm | StrOutputParser()

        report_content = chain.invoke({
            "analysis_data": self._format_analysis_data(analysis_data),
            "users_analyzed": analysis_data.get("users_analyzed", 0),
            "total_violations": analysis_data.get("total_violations", 0),
            "compliance_rate": analysis_data.get("compliance_rate", 0),
            "current_date": datetime.now().strftime("%Y-%m-%d")
        })

        return {
            "report_content": report_content,
            "report_type": report_type,
            "audience": audience,
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "focus_areas": focus_areas,
                "included_sections": include_sections,
                "excluded_sections": exclude_sections
            }
        }

    def _build_prompt(
        self,
        report_type: ReportType,
        audience: AudienceType,
        focus_areas: list[str] | None,
        include_sections: list[str] | None,
        exclude_sections: list[str] | None,
        custom_instructions: str | None
    ) -> ChatPromptTemplate:
        """Build dynamic prompt based on user preferences"""

        # Base system message
        system_message = self._get_system_message(report_type, audience)

        # Add focus areas if specified
        if focus_areas:
            focus_instruction = f"\n\nFOCUS AREAS: Pay special attention to: {', '.join(focus_areas)}"
            system_message += focus_instruction

        # Add section instructions
        if include_sections:
            system_message += f"\n\nINCLUDE THESE SECTIONS: {', '.join(include_sections)}"

        if exclude_sections:
            system_message += f"\n\nEXCLUDE THESE SECTIONS: {', '.join(exclude_sections)}"

        # Add custom instructions
        if custom_instructions:
            system_message += f"\n\nADDITIONAL INSTRUCTIONS: {custom_instructions}"

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", """Based on the following SOD compliance analysis data, generate the requested report:

{analysis_data}

Summary Statistics:
- Users Analyzed: {users_analyzed}
- Total Violations: {total_violations}
- Compliance Rate: {compliance_rate}%
- Report Date: {current_date}

Generate a comprehensive, well-structured report that addresses the specific audience and includes all requested elements.""")
        ])

    def _get_system_message(self, report_type: ReportType, audience: AudienceType) -> str:
        """Get system message based on report type and audience"""

        base_message = "You are an expert SOX compliance analyst generating SOD compliance reports."

        # Report type specific instructions
        report_instructions = {
            ReportType.EXECUTIVE_SUMMARY: """
Generate a concise executive summary (1-2 pages) that includes:
- High-level overview of compliance status
- Key risks and concerns
- Top 3-5 action items with business impact
- Strategic recommendations
- ROI of remediation

Use business language, not technical jargon. Focus on risk to the business.
""",
            ReportType.DETAILED_ANALYSIS: """
Generate a comprehensive detailed analysis that includes:
- Complete violation breakdown by severity, type, and department
- Individual user risk profiles
- Root cause analysis
- Detailed remediation plans with timelines
- Resource requirements
- Success metrics

Include all technical details and supporting data.
""",
            ReportType.TECHNICAL_REPORT: """
Generate a technical report for IT/Security teams that includes:
- System access patterns
- Role/permission matrices
- Configuration issues
- Technical remediation steps
- Implementation details
- Integration requirements

Use technical terminology appropriate for IT professionals.
""",
            ReportType.AUDIT_REPORT: """
Generate an audit-ready report that includes:
- SOX compliance status
- Regulatory framework mapping (SOX, PCAOB)
- Control deficiencies
- Material weakness assessment
- Audit trail evidence
- Management response section

Follow SOX audit documentation standards.
""",
            ReportType.DEPARTMENT_REPORT: """
Generate a department-focused report that includes:
- Department-specific violations
- Team members with violations
- Department compliance score
- Peer department comparison
- Department-specific remediation plan

Tailor language for department heads and their teams.
""",
            ReportType.TREND_ANALYSIS: """
Generate a trend analysis report that includes:
- Historical comparison
- Violation trends over time
- Compliance rate trends
- Emerging risk patterns
- Predictive insights
- Effectiveness of previous remediations

Focus on patterns, trends, and predictive analysis.
"""
        }

        # Audience specific tone
        audience_tone = {
            AudienceType.EXECUTIVES: "Use executive business language. Focus on strategic impact, ROI, and business risk. Keep it concise and action-oriented.",
            AudienceType.COMPLIANCE_TEAM: "Use compliance and regulatory language. Focus on control frameworks, remediation steps, and audit readiness.",
            AudienceType.AUDITORS: "Use formal audit terminology. Focus on evidence, control deficiencies, and regulatory compliance. Include references to SOX and PCAOB standards.",
            AudienceType.IT_SECURITY: "Use technical IT security language. Focus on access controls, system configurations, and technical implementation.",
            AudienceType.DEPARTMENT_HEADS: "Use clear business language. Focus on their team's specific issues, actionable steps they can take, and impact on operations."
        }

        return f"{base_message}\n\n{report_instructions.get(report_type, '')}\n\nAUDIENCE: {audience_tone.get(audience, '')}"

    def _format_analysis_data(self, data: dict[str, Any]) -> str:
        """Format analysis data for the prompt"""
        formatted = []

        # Violations by severity
        if "violations_by_severity" in data:
            formatted.append("VIOLATIONS BY SEVERITY:")
            for severity, count in data["violations_by_severity"].items():
                formatted.append(f"  {severity}: {count}")

        # Top violators
        if "top_violators" in data:
            formatted.append("\nTOP VIOLATORS:")
            for i, user in enumerate(data["top_violators"][:5], 1):
                formatted.append(f"  {i}. {user.get('name')} - {user.get('violation_count')} violations (Risk: {user.get('max_risk_score')}/100)")

        # Department stats
        if "department_stats" in data:
            formatted.append("\nDEPARTMENT ANALYSIS:")
            for dept, stats in list(data["department_stats"].items())[:10]:
                comp_rate = (stats.get('compliant', 0) / stats.get('users', 1)) * 100
                formatted.append(f"  {dept}: {stats.get('violations')} violations, {comp_rate:.1f}% compliant")

        # Risk distribution
        if "risk_distribution" in data:
            formatted.append("\nRISK DISTRIBUTION:")
            for level, count in data["risk_distribution"].items():
                formatted.append(f"  {level}: {count} users")

        # Violation details (sample)
        if "violation_details" in data and data["violation_details"]:
            formatted.append("\nSAMPLE VIOLATIONS:")
            for v in data["violation_details"][:3]:
                formatted.append(f"  - {v.get('rule_name')} ({v.get('severity')}): {v.get('user_name')} - {v.get('description', '')[:100]}...")

        return "\n".join(formatted)

    def generate_composite_report_with_llm(
        self,
        analysis_results: dict[str, Any],
        customization: dict[str, Any]
    ) -> str:
        """
        Generate a fully customized composite report using Claude

        Args:
            analysis_results: Full analysis data from SOD scan
            customization: Dict with:
                - report_type: ReportType enum
                - audience: AudienceType enum
                - focus_areas: List[str] (optional)
                - include_sections: List[str] (optional)
                - exclude_sections: List[str] (optional)
                - custom_instructions: str (optional)
                - format: ReportFormat enum (optional)

        Returns:
            Formatted report string
        """
        result = self.generate_custom_report(
            analysis_data=analysis_results,
            report_type=customization.get("report_type", ReportType.EXECUTIVE_SUMMARY),
            audience=customization.get("audience", AudienceType.EXECUTIVES),
            focus_areas=customization.get("focus_areas"),
            include_sections=customization.get("include_sections"),
            exclude_sections=customization.get("exclude_sections"),
            custom_instructions=customization.get("custom_instructions")
        )

        return result["report_content"]


# Example usage
if __name__ == "__main__":
    # Example: Generate executive summary
    agent = ReportGeneratorAgent()

    sample_data = {
        "users_analyzed": 1933,
        "total_violations": 247,
        "compliance_rate": 87.2,
        "violations_by_severity": {
            "CRITICAL": 15,
            "HIGH": 62,
            "MEDIUM": 120,
            "LOW": 50
        },
        "top_violators": [
            {"name": "Jane Doe", "violation_count": 5, "max_risk_score": 89},
            {"name": "John Smith", "violation_count": 4, "max_risk_score": 78}
        ],
        "department_stats": {
            "Finance": {"users": 45, "violations": 28, "compliant": 30},
            "IT": {"users": 38, "violations": 42, "compliant": 20}
        },
        "risk_distribution": {
            "High Risk": 12,
            "Medium Risk": 45,
            "Low Risk": 89,
            "Compliant": 1787
        }
    }

    # Generate executive summary focusing on Finance department
    report = agent.generate_custom_report(
        analysis_data=sample_data,
        report_type=ReportType.EXECUTIVE_SUMMARY,
        audience=AudienceType.EXECUTIVES,
        focus_areas=["Finance department", "HIGH severity violations"],
        custom_instructions="Emphasize the urgency of addressing Finance department violations before the upcoming SOX audit."
    )

    print(report["report_content"])
