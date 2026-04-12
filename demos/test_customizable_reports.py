"""
Test Customizable Report Generation

Demonstrates the ReportGeneratorAgent's ability to generate different types
of reports tailored to specific audiences with custom focus areas.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.report_generator import AudienceType, ReportGeneratorAgent, ReportType


def get_sample_analysis_data():
    """Sample SOD analysis data for demonstration"""
    return {
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
            {
                "name": "John Smith",
                "email": "john.smith@company.com",
                "violation_count": 5,
                "max_risk_score": 89,
                "department": "Finance",
                "violations": [
                    "Journal Entry Creator + Approver",
                    "Vendor Setup + Payment Processing",
                    "Check Writer + Bank Reconciliation"
                ]
            },
            {
                "name": "Jane Doe",
                "email": "jane.doe@company.com",
                "violation_count": 4,
                "max_risk_score": 78,
                "department": "IT",
                "violations": [
                    "System Admin + Financial Access",
                    "User Management + Audit Log Access"
                ]
            },
            {
                "name": "Bob Johnson",
                "email": "bob.j@company.com",
                "violation_count": 3,
                "max_risk_score": 72,
                "department": "Finance",
                "violations": [
                    "Expense Report Submitter + Approver",
                    "Purchase Order Creator + Receiver"
                ]
            }
        ],
        "department_stats": {
            "Finance": {
                "users": 45,
                "violations": 82,
                "compliant": 30,
                "compliance_rate": 66.7
            },
            "IT": {
                "users": 38,
                "violations": 56,
                "compliant": 20,
                "compliance_rate": 52.6
            },
            "Sales": {
                "users": 120,
                "violations": 45,
                "compliant": 95,
                "compliance_rate": 79.2
            },
            "Operations": {
                "users": 85,
                "violations": 38,
                "compliant": 65,
                "compliance_rate": 76.5
            },
            "HR": {
                "users": 28,
                "violations": 12,
                "compliant": 25,
                "compliance_rate": 89.3
            }
        },
        "risk_distribution": {
            "High Risk (80-100)": 12,
            "Medium-High Risk (60-79)": 45,
            "Medium Risk (40-59)": 89,
            "Low Risk (20-39)": 101,
            "Compliant (0-19)": 1686
        },
        "violation_details": [
            {
                "rule_name": "Journal Entry SOD",
                "severity": "CRITICAL",
                "user_name": "John Smith",
                "description": "User can both create and approve journal entries, creating fraud risk"
            },
            {
                "rule_name": "System Admin Financial Access",
                "severity": "HIGH",
                "user_name": "Jane Doe",
                "description": "System administrator has direct access to financial records"
            },
            {
                "rule_name": "Vendor Setup + Payment",
                "severity": "HIGH",
                "user_name": "John Smith",
                "description": "User can create vendors and process payments to them"
            }
        ]
    }


def print_separator(title):
    """Print formatted section separator"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100 + "\n")


def save_report(report_name, content):
    """Save report to file"""
    filename = f"/tmp/{report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w') as f:
        f.write(content)
    print(f"📄 Report saved to: {filename}")


def main():
    print_separator("🎯 CUSTOMIZABLE REPORT GENERATION DEMO")
    print("Demonstrating ReportGeneratorAgent with different audiences and customizations\n")

    # Initialize agent
    print("🔧 Initializing Report Generator Agent...")
    agent = ReportGeneratorAgent(model="claude-opus-4-6")
    print("✅ Agent ready\n")

    # Get sample data
    analysis_data = get_sample_analysis_data()
    print(f"📊 Sample Data: {analysis_data['users_analyzed']} users, "
          f"{analysis_data['total_violations']} violations, "
          f"{analysis_data['compliance_rate']}% compliant\n")

    # ========================================================================
    # DEMO 1: Executive Summary
    # ========================================================================
    print_separator("DEMO 1: Executive Summary for C-Suite")

    print("📝 Generating executive summary...")
    print("   • Audience: Executives")
    print("   • Focus: Finance department, HIGH/CRITICAL violations")
    print("   • Custom instruction: Emphasize urgency before Q1 audit\n")

    report1 = agent.generate_custom_report(
        analysis_data=analysis_data,
        report_type=ReportType.EXECUTIVE_SUMMARY,
        audience=AudienceType.EXECUTIVES,
        focus_areas=["Finance department", "CRITICAL and HIGH severity violations"],
        custom_instructions=(
            "Emphasize the urgency of addressing these violations before the "
            "upcoming Q1 SOX audit in 3 weeks. Include estimated cost of non-compliance."
        )
    )

    print("✅ Generated Executive Summary")
    print(f"   • Generated at: {report1['generated_at']}")
    print(f"   • Report type: {report1['report_type']}")
    print(f"   • Audience: {report1['audience']}\n")

    print("--- REPORT PREVIEW (First 800 characters) ---")
    print(report1['report_content'][:800] + "...\n")

    save_report("executive_summary", report1['report_content'])

    # ========================================================================
    # DEMO 2: Technical Report for IT Security
    # ========================================================================
    print_separator("DEMO 2: Technical Report for IT Security Team")

    print("📝 Generating technical report...")
    print("   • Audience: IT Security")
    print("   • Focus: System access patterns, role configurations")
    print("   • Sections: Include technical remediation steps\n")

    report2 = agent.generate_custom_report(
        analysis_data=analysis_data,
        report_type=ReportType.TECHNICAL_REPORT,
        audience=AudienceType.IT_SECURITY,
        focus_areas=["System admin violations", "Role permission conflicts"],
        include_sections=[
            "Role/Permission Matrices",
            "Technical Remediation Steps",
            "System Configuration Changes"
        ],
        custom_instructions=(
            "Provide specific NetSuite role IDs and permission changes needed. "
            "Include commands/scripts where applicable."
        )
    )

    print("✅ Generated Technical Report")
    print(f"   • Generated at: {report2['generated_at']}")
    print(f"   • Report type: {report2['report_type']}")
    print(f"   • Audience: {report2['audience']}\n")

    print("--- REPORT PREVIEW (First 800 characters) ---")
    print(report2['report_content'][:800] + "...\n")

    save_report("technical_report", report2['report_content'])

    # ========================================================================
    # DEMO 3: Audit Report for External Auditors
    # ========================================================================
    print_separator("DEMO 3: Audit Report for External Auditors")

    print("📝 Generating audit report...")
    print("   • Audience: External Auditors")
    print("   • Focus: SOX compliance, material weaknesses")
    print("   • Custom instruction: Map to PCAOB standards\n")

    report3 = agent.generate_custom_report(
        analysis_data=analysis_data,
        report_type=ReportType.AUDIT_REPORT,
        audience=AudienceType.AUDITORS,
        focus_areas=["CRITICAL violations", "Material weakness assessment"],
        custom_instructions=(
            "Map violations to specific SOX sections (302, 404) and PCAOB standards. "
            "Include management response section. Follow Big 4 audit documentation standards."
        )
    )

    print("✅ Generated Audit Report")
    print(f"   • Generated at: {report3['generated_at']}")
    print(f"   • Report type: {report3['report_type']}")
    print(f"   • Audience: {report3['audience']}\n")

    print("--- REPORT PREVIEW (First 800 characters) ---")
    print(report3['report_content'][:800] + "...\n")

    save_report("audit_report", report3['report_content'])

    # ========================================================================
    # DEMO 4: Department Report for Finance Manager
    # ========================================================================
    print_separator("DEMO 4: Department Report for Finance Manager")

    print("📝 Generating department-specific report...")
    print("   • Audience: Department Heads")
    print("   • Focus: Finance department only")
    print("   • Exclude: Other departments\n")

    report4 = agent.generate_custom_report(
        analysis_data=analysis_data,
        report_type=ReportType.DEPARTMENT_REPORT,
        audience=AudienceType.DEPARTMENT_HEADS,
        focus_areas=["Finance department"],
        exclude_sections=["IT department", "Sales department", "HR department"],
        custom_instructions=(
            "Focus only on Finance team violations. List specific team members "
            "and actionable steps the Finance Manager can take immediately. "
            "Compare Finance compliance to company average."
        )
    )

    print("✅ Generated Department Report")
    print(f"   • Generated at: {report4['generated_at']}")
    print(f"   • Report type: {report4['report_type']}")
    print(f"   • Audience: {report4['audience']}\n")

    print("--- REPORT PREVIEW (First 800 characters) ---")
    print(report4['report_content'][:800] + "...\n")

    save_report("department_report", report4['report_content'])

    # ========================================================================
    # DEMO 5: Detailed Analysis for Compliance Team
    # ========================================================================
    print_separator("DEMO 5: Detailed Analysis for Compliance Team")

    print("📝 Generating detailed compliance analysis...")
    print("   • Audience: Compliance Team")
    print("   • Focus: All violations with root cause analysis")
    print("   • Include: Detailed remediation plans\n")

    report5 = agent.generate_custom_report(
        analysis_data=analysis_data,
        report_type=ReportType.DETAILED_ANALYSIS,
        audience=AudienceType.COMPLIANCE_TEAM,
        focus_areas=["Root cause analysis", "Remediation timelines"],
        include_sections=[
            "Complete Violation Breakdown",
            "Individual User Risk Profiles",
            "Detailed Remediation Plans",
            "Success Metrics"
        ],
        custom_instructions=(
            "Include specific timeline for each remediation action. "
            "Provide resource requirements (hours, personnel). "
            "Add checkpoints for progress tracking."
        )
    )

    print("✅ Generated Detailed Analysis")
    print(f"   • Generated at: {report5['generated_at']}")
    print(f"   • Report type: {report5['report_type']}")
    print(f"   • Audience: {report5['audience']}\n")

    print("--- REPORT PREVIEW (First 800 characters) ---")
    print(report5['report_content'][:800] + "...\n")

    save_report("detailed_analysis", report5['report_content'])

    # ========================================================================
    # Summary
    # ========================================================================
    print_separator("📊 DEMO SUMMARY")

    print("✅ Successfully generated 5 different customized reports:\n")
    print("1. Executive Summary")
    print("   → Tailored for C-suite with business impact focus")
    print("   → Emphasized Finance dept and critical violations")
    print("   → Included Q1 audit urgency\n")

    print("2. Technical Report")
    print("   → Tailored for IT Security team")
    print("   → Included role/permission matrices")
    print("   → Provided NetSuite-specific remediation steps\n")

    print("3. Audit Report")
    print("   → Tailored for external auditors")
    print("   → Mapped to SOX 302/404 and PCAOB standards")
    print("   → Included management response section\n")

    print("4. Department Report")
    print("   → Tailored for Finance Manager")
    print("   → Focused only on Finance team")
    print("   → Actionable steps for immediate implementation\n")

    print("5. Detailed Analysis")
    print("   → Tailored for Compliance team")
    print("   → Complete remediation plans with timelines")
    print("   → Resource requirements included\n")

    print("=" * 100)
    print("🎯 All reports saved to /tmp/ directory")
    print("=" * 100)

    print("\n💡 KEY FEATURES DEMONSTRATED:")
    print("   ✓ Multiple report types (Executive, Technical, Audit, Department, Detailed)")
    print("   ✓ Multiple audiences (Executives, IT, Auditors, Dept Heads, Compliance)")
    print("   ✓ Focus areas customization")
    print("   ✓ Section inclusion/exclusion")
    print("   ✓ Custom instructions for LLM")
    print("   ✓ Dynamic prompt building")
    print("   ✓ Claude Opus 4-6 integration")


if __name__ == "__main__":
    main()
