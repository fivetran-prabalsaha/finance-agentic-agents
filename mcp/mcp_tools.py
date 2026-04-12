"""
MCP Tools - Tool definitions and handlers for Claude UI integration

Each tool represents a capability that Claude can invoke via MCP protocol.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

from sqlalchemy import text

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    # Fallback if dateutil not installed
    relativedelta = None
from .orchestrator import ComplianceOrchestrator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_orchestrator() -> ComplianceOrchestrator:
    """Get or create orchestrator instance (cached)"""
    logger.info("Creating new orchestrator instance...")
    return ComplianceOrchestrator()


# ============================================================================
# TOOL SCHEMAS
# ============================================================================

TOOL_SCHEMAS = {
    "list_systems": {
        "description": "List all available systems for compliance review with their current status and user counts",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "perform_access_review": {
        "description": "Perform a comprehensive multi-step user access review for an ENTIRE system, analyzing SOD violations, excessive permissions, and inactive users across ALL users. Use when user wants 'full system audit', 'comprehensive review', 'analyze all NetSuite users', or 'complete access review'. This is a heavyweight operation that processes all users. For specific users/departments, use get_user_violations or list_all_users with filter_by_department instead for faster results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "Name of the system to review",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis to perform",
                    "enum": ["sod_violations", "excessive_permissions", "inactive_users", "all"],
                    "default": "sod_violations"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include AI-powered remediation recommendations",
                    "default": True
                }
            },
            "required": ["system_name"]
        }
    },

    "get_user_violations": {
        "description": "Get SOD violations for a specific USER (cross-role conflicts from multiple roles assigned to same user). Use this to check if a PERSON has conflicting role combinations. NOT for analyzing whether a ROLE itself is safe - use get_role_conflicts or analyze_role_permissions for that. Includes AI-powered risk analysis and recommendations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System name where user exists",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "user_identifier": {
                    "type": "string",
                    "description": "User email address or user ID"
                },
                "include_ai_analysis": {
                    "type": "boolean",
                    "description": "Include AI-powered risk analysis and recommendations",
                    "default": True
                },
                "format": {
                    "type": "string",
                    "enum": ["table", "detailed", "concise"],
                    "description": "Output format: table (tabular summary - default), detailed (full list), concise (brief overview)",
                    "default": "table"
                }
            },
            "required": ["system_name", "user_identifier"]
        }
    },

    "remediate_violation": {
        "description": "Create a remediation plan or ticket for a specific violation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "violation_id": {
                    "type": "string",
                    "description": "UUID of the violation to remediate"
                },
                "action": {
                    "type": "string",
                    "description": "Type of remediation action to take",
                    "enum": ["remove_role", "request_approval", "create_ticket", "notify_manager"]
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or context for remediation"
                }
            },
            "required": ["violation_id", "action"]
        }
    },

    "schedule_review": {
        "description": "Schedule a recurring compliance review for a system",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System to review",
                    "enum": ["netsuite", "okta", "salesforce"]
                },
                "frequency": {
                    "type": "string",
                    "description": "Review frequency",
                    "enum": ["daily", "weekly", "monthly"]
                },
                "day_of_week": {
                    "type": "string",
                    "description": "Day of week for weekly reviews",
                    "enum": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                },
                "time": {
                    "type": "string",
                    "description": "Time in HH:MM format (24-hour)",
                    "pattern": "^([0-1][0-9]|2[0-3]):[0-5][0-9]$"
                },
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone identifier",
                    "default": "America/Los_Angeles"
                }
            },
            "required": ["system_name", "frequency"]
        }
    },

    "get_violation_stats": {
        "description": "Get aggregate violation statistics across systems for a time period",
        "inputSchema": {
            "type": "object",
            "properties": {
                "systems": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of systems to include (empty array = all systems)"
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for statistics",
                    "enum": ["today", "week", "month", "quarter", "year"],
                    "default": "month"
                }
            },
            "required": []
        }
    },

    "start_collection_agent": {
        "description": "Start the autonomous data collection agent that syncs user/role/permission data from external systems",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "stop_collection_agent": {
        "description": "Stop the autonomous data collection agent",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "get_collection_agent_status": {
        "description": "Get current status of the autonomous collection agent, including recent sync history and statistics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "Optional system filter (default: all systems)"
                }
            },
            "required": []
        }
    },

    "trigger_manual_sync": {
        "description": "Manually trigger a data sync from an external system to update user/role/permission data",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System to sync",
                    "enum": ["netsuite", "okta", "salesforce"],
                    "default": "netsuite"
                },
                "sync_type": {
                    "type": "string",
                    "description": "Type of sync to perform",
                    "enum": ["full", "incremental"],
                    "default": "full"
                }
            },
            "required": []
        }
    },

    "list_all_users": {
        "description": "Get a complete list of all active users in a system with their roles and basic information. Use when user asks to 'show Finance users', 'list Accounting team', 'who is in [department]', 'list all users', or 'review [department] access'. Supports hierarchical department matching (e.g., 'Finance' matches 'Fivetran : G&A : Finance'). For individual user analysis, use get_user_violations instead.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System to list users from",
                    "enum": ["netsuite", "okta", "salesforce"],
                    "default": "netsuite"
                },
                "include_inactive": {
                    "type": "boolean",
                    "description": "Include inactive users in the list",
                    "default": False
                },
                "filter_by_department": {
                    "type": "string",
                    "description": "Optional department filter to show only users from specific department"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of users to return (default: 100, max: 500)",
                    "default": 100
                }
            },
            "required": ["system_name"]
        }
    },

    "analyze_access_request": {
        "description": "Analyze an access request for SOD conflicts using level-based analysis. Returns concise summary with: conflict count, severity breakdown, top 3-5 critical issues, and direct recommendation (approve/deny/review). Avoid verbose explanations or detailed bullet lists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title of the user requesting access (e.g., 'Revenue Director', 'Controller')"
                },
                "requested_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of NetSuite role names being requested (e.g., ['Fivetran - Revenue Manager', 'Fivetran - Revenue Approver'])"
                },
                "user_email": {
                    "type": "string",
                    "description": "Optional email address of the user"
                }
            },
            "required": ["job_title", "requested_roles"]
        }
    },

    "query_sod_rules": {
        "description": "Query SOD rules from the database with optional filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category1": {
                    "type": "string",
                    "description": "First permission category (e.g., 'transaction_entry', 'transaction_approval')"
                },
                "category2": {
                    "type": "string",
                    "description": "Second permission category to check conflicts"
                },
                "severity": {
                    "type": "string",
                    "description": "Filter by severity level",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rules to return",
                    "default": 10
                }
            },
            "required": []
        }
    },

    "get_compensating_controls": {
        "description": "Get recommended compensating controls for a specific severity level. Returns concise list with control names, risk reduction %, and total cost estimate. Present as brief summary, not detailed bullet lists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "description": "Severity level of the conflict",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
                },
                "include_cost": {
                    "type": "boolean",
                    "description": "Include cost estimates for controls",
                    "default": True
                }
            },
            "required": ["severity"]
        }
    },

    "validate_job_role": {
        "description": "Validate if a role combination is typical for a specific job title",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title to validate (e.g., 'Revenue Director', 'Controller')"
                },
                "requested_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "NetSuite roles being requested"
                }
            },
            "required": ["job_title", "requested_roles"]
        }
    },

    "check_permission_conflict": {
        "description": "Check if two specific permissions conflict based on their levels",
        "inputSchema": {
            "type": "object",
            "properties": {
                "permission1_name": {
                    "type": "string",
                    "description": "First permission name (e.g., 'Invoice')"
                },
                "permission1_level": {
                    "type": "string",
                    "description": "Level of first permission",
                    "enum": ["None", "View", "Create", "Edit", "Full"]
                },
                "permission2_name": {
                    "type": "string",
                    "description": "Second permission name (e.g., 'Invoice Approval')"
                },
                "permission2_level": {
                    "type": "string",
                    "description": "Level of second permission",
                    "enum": ["None", "View", "Create", "Edit", "Full"]
                }
            },
            "required": ["permission1_name", "permission1_level", "permission2_name", "permission2_level"]
        }
    },

    "get_permission_categories": {
        "description": "Get all permission categories and their risk scores from the database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_permissions": {
                    "type": "boolean",
                    "description": "Include list of permissions in each category",
                    "default": False
                }
            },
            "required": []
        }
    },

    "search_permissions": {
        "description": "Search and filter NetSuite permissions by name, category, or risk level",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "Search term to match permission names"
                },
                "category": {
                    "type": "string",
                    "description": "Filter by permission category"
                },
                "risk_level": {
                    "type": "string",
                    "description": "Filter by risk level",
                    "enum": ["HIGH", "MEDIUM", "LOW", "MINIMAL"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 20
                }
            },
            "required": []
        }
    },

    "query_knowledge_base": {
        "description": "Query the vector knowledge base for SOD rules, controls, and resolution strategies. IMPORTANT: Use database tools (recommend_roles_for_job_title, analyze_access_request) FIRST for role recommendations. Knowledge base is for understanding concepts, NOT for determining what roles to assign.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query to search for (e.g., 'revenue approval conflicts', 'payment segregation controls')"
                },
                "doc_type": {
                    "type": "string",
                    "description": "Filter by document type",
                    "enum": ["SOD_RULE", "COMPENSATING_CONTROL", "RESOLUTION_STRATEGY", "JOB_ROLE", "ALL"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },

    "recommend_roles_for_job_title": {
        "description": "**PRIMARY TOOL for role recommendations** - Gets actual roles from database by analyzing what existing employees with similar job titles currently have. Use when user asks 'what roles should I give [job title]', 'roles for new Controller', 'safe roles for [position]', 'onboard new hire as [title]', or 'role recommendations for [job]'. ALWAYS use this FIRST before recommending roles. Includes automatic SOD conflict checking. Never assume roles based on job title alone - always query actual peer data to ensure recommendations match organizational patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_title": {
                    "type": "string",
                    "description": "Job title of the new hire (e.g., 'Revenue Director', 'Controller', 'Sales Manager')"
                },
                "department": {
                    "type": "string",
                    "description": "Optional department filter (e.g., 'Accounting', 'Finance', 'Operations') to match peers in same department"
                },
                "format": {
                    "type": "string",
                    "enum": ["summary", "detailed"],
                    "description": "Output format - 'summary' for brief list, 'detailed' for peer breakdown",
                    "default": "summary"
                }
            },
            "required": ["job_title"]
        }
    },

    "analyze_role_permissions": {
        "description": "Analyze internal SOD conflicts within a single NetSuite role (deep analysis). Performs comprehensive level-based conflict detection, identifies incompatible permissions, and generates detailed report with remediation recommendations. Use this for NEW roles not yet in knowledge base, or when you need fresh analysis. For faster results on existing roles, use get_role_conflicts instead. This analyzes the ROLE itself, not user violations. Returns summary + saves detailed analysis to file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role_name": {
                    "type": "string",
                    "description": "Name of the NetSuite role to analyze (e.g., 'Fivetran - Cash Accountant', 'Fivetran - Controller')"
                },
                "include_remediation_plan": {
                    "type": "boolean",
                    "description": "Include detailed remediation recommendations",
                    "default": True
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format for detailed report",
                    "enum": ["markdown", "json", "both"],
                    "default": "markdown"
                }
            },
            "required": ["role_name"]
        }
    },

    "get_role_conflicts": {
        "description": "**PRIMARY TOOL for analyzing NetSuite ROLE conflicts** - Gets internal SOD conflicts within a single role (e.g., maker-checker violations where one role can both create AND approve transactions). This is NOT for user violations. Use this when asked to 'analyze [role name]' or 'check if [role] is safe'. Returns pre-analyzed conflict information from knowledge base including CRITICAL maker-checker violations, 3-way match bypasses, and remediation guidance. Works with role names containing special characters like 'A/P Analyst'. IMPORTANT: User having 0 violations does NOT mean the role itself is safe - always check role's internal conflicts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role_name": {
                    "type": "string",
                    "description": "Name of the NetSuite role (e.g., 'Fivetran - A/P Analyst', 'Fivetran - Controller'). Can include special characters."
                }
            },
            "required": ["role_name"]
        }
    },

    "record_exception_approval": {
        "description": "Record approval of a SOD exception with compensating controls. Creates a permanent record of approved role combinations that violate SOD rules, along with the controls required to mitigate the risk. Use this after analyzing an access request that has conflicts but is approved with controls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_identifier": {
                    "type": "string",
                    "description": "User email or ID"
                },
                "user_name": {
                    "type": "string",
                    "description": "Full name of the user"
                },
                "role_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of role names being approved"
                },
                "conflict_count": {
                    "type": "integer",
                    "description": "Total number of SOD conflicts detected"
                },
                "critical_conflicts": {
                    "type": "integer",
                    "description": "Number of CRITICAL severity conflicts"
                },
                "risk_score": {
                    "type": "number",
                    "description": "Overall risk score (0-100)"
                },
                "business_justification": {
                    "type": "string",
                    "description": "Business reason for approving this exception"
                },
                "approved_by": {
                    "type": "string",
                    "description": "Name of the approver"
                },
                "approval_authority": {
                    "type": "string",
                    "description": "Title/role of approver (e.g., 'CFO', 'VP Compliance')"
                },
                "job_title": {
                    "type": "string",
                    "description": "User's job title"
                },
                "department": {
                    "type": "string",
                    "description": "User's department"
                },
                "compensating_controls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "control_name": {"type": "string"},
                            "risk_reduction_percentage": {"type": "number"},
                            "estimated_annual_cost": {"type": "number"}
                        }
                    },
                    "description": "List of compensating controls being implemented"
                },
                "review_frequency": {
                    "type": "string",
                    "enum": ["Monthly", "Quarterly", "Annually"],
                    "description": "How often this exception should be reviewed",
                    "default": "Quarterly"
                },
                "expiration_days": {
                    "type": "integer",
                    "description": "Number of days until exception expires (optional)"
                }
            },
            "required": ["user_identifier", "user_name", "role_names", "conflict_count", "risk_score", "business_justification", "approved_by"]
        }
    },

    "find_similar_exceptions": {
        "description": "Find previously approved exceptions similar to a proposed role combination. Uses similarity matching (70% role overlap + 20% job title + 10% department) to find precedents. Returns top 3 matches with their controls, costs, and effectiveness. Use this BEFORE approving new exceptions to leverage existing control frameworks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Role names to search for similar exceptions"
                },
                "job_title": {
                    "type": "string",
                    "description": "Optional job title for better matching"
                },
                "department": {
                    "type": "string",
                    "description": "Optional department for better matching"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of similar exceptions to return",
                    "default": 3
                }
            },
            "required": ["role_names"]
        }
    },

    "get_exception_details": {
        "description": "Get complete details of a specific approved exception including all controls, violations, and review history. Use this to review the status and effectiveness of an existing exception.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "exception_code": {
                    "type": "string",
                    "description": "Exception code (e.g., 'EXC-2026-001')"
                }
            },
            "required": ["exception_code"]
        }
    },

    "list_approved_exceptions": {
        "description": "List all approved SOD exceptions with optional filters. Returns paginated summary view of exceptions with status, user, roles, and control counts. Use this to browse or audit approved exceptions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["ACTIVE", "VIOLATED", "REMEDIATED", "EXPIRED", "REVOKED"],
                    "description": "Filter by exception status"
                },
                "user_identifier": {
                    "type": "string",
                    "description": "Filter by user email or ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                },
                "offset": {
                    "type": "integer",
                    "description": "Pagination offset",
                    "default": 0
                }
            },
            "required": []
        }
    },

    "record_exception_violation": {
        "description": "Record a violation of an approved exception (compensating control failure). Use this when monitoring detects that a required control was bypassed or failed. Automatically updates exception status to VIOLATED and triggers review process.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "exception_code": {
                    "type": "string",
                    "description": "Exception code (e.g., 'EXC-2026-001')"
                },
                "violation_type": {
                    "type": "string",
                    "description": "Type of violation (e.g., 'Unauthorized Transaction', 'Control Bypass')"
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Severity of the violation"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of what happened"
                },
                "failed_control_name": {
                    "type": "string",
                    "description": "Name of the control that failed"
                },
                "failure_reason": {
                    "type": "string",
                    "description": "Why the control failed"
                },
                "detected_by": {
                    "type": "string",
                    "description": "Who/what detected the violation",
                    "default": "Automated Monitoring"
                },
                "detection_method": {
                    "type": "string",
                    "description": "How the violation was detected"
                }
            },
            "required": ["exception_code", "violation_type", "severity", "description", "failed_control_name"]
        }
    },

    "get_exception_effectiveness_stats": {
        "description": "Get dashboard statistics on exception effectiveness including total costs, violation rates, control effectiveness, and ROI analysis. Use this for compliance reporting and to identify poorly performing exceptions that need review.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    "detect_exception_violations": {
        "description": "Automatically detect violations of approved exceptions by checking if users with exceptions have new SOD conflicts or are bypassing compensating controls. Run this periodically (daily/weekly) to monitor exception compliance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "check_all": {
                    "type": "boolean",
                    "description": "Check all active exceptions (default) or only specific users",
                    "default": True
                },
                "exception_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific exception codes to check"
                },
                "auto_record": {
                    "type": "boolean",
                    "description": "Automatically record detected violations (default: false, returns report only)",
                    "default": False
                }
            },
            "required": []
        }
    },

    "conduct_exception_review": {
        "description": "Conduct a periodic review of an approved exception. Records review findings, outcome (continue/modify/revoke), and updates next review date. Use this when completing scheduled quarterly/annual exception reviews.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "exception_code": {
                    "type": "string",
                    "description": "Exception code to review (e.g., 'EXC-2026-001')"
                },
                "reviewer_name": {
                    "type": "string",
                    "description": "Name of person conducting review"
                },
                "outcome": {
                    "type": "string",
                    "enum": ["APPROVED_CONTINUE", "APPROVED_MODIFY", "REVOKED", "ESCALATED"],
                    "description": "Review outcome"
                },
                "findings": {
                    "type": "string",
                    "description": "Review findings and observations"
                },
                "recommendations": {
                    "type": "string",
                    "description": "Recommendations for improvement or changes"
                },
                "control_modifications": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "control_name": {"type": "string"},
                            "modification": {"type": "string"}
                        }
                    },
                    "description": "List of control modifications if outcome is APPROVED_MODIFY"
                }
            },
            "required": ["exception_code", "reviewer_name", "outcome"]
        }
    },

    "get_exceptions_for_review": {
        "description": "Get list of exceptions that are due or overdue for periodic review. Use this to identify which exceptions need review attention and schedule review sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_upcoming": {
                    "type": "boolean",
                    "description": "Include exceptions with reviews coming up in next 30 days",
                    "default": True
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "How many days ahead to look for upcoming reviews",
                    "default": 30
                }
            },
            "required": []
        }
    },

    "initialize_session": {
        "description": "Initialize compliance session and show personalized welcome with user's permissions and approval authority. Call this when user first logs in to show what they can do. Returns friendly welcome message with approval capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "my_email": {
                    "type": "string",
                    "description": "Your email address"
                }
            },
            "required": ["my_email"]
        }
    },

    "check_my_approval_authority": {
        "description": "Check if current user (by email) has authority to approve SOD exceptions at different risk levels. Validates against NetSuite roles and returns approval authority matrix. Use this when user logs in to show what they can approve.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "my_email": {
                    "type": "string",
                    "description": "Your email address (will be validated against active users)"
                },
                "check_for_risk_score": {
                    "type": "number",
                    "description": "Optional: Check authority for specific risk score (0-100)"
                }
            },
            "required": ["my_email"]
        }
    },

    "request_exception_approval": {
        "description": "Request approval for SOD exception with automatic RBAC validation and routing. Checks if requester has approval authority. If not, automatically finds approver in reporting chain and creates Jira ticket for escalation. Use this instead of record_exception_approval when you want RBAC enforcement.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "requester_email": {
                    "type": "string",
                    "description": "Email of person requesting the approval"
                },
                "user_identifier": {
                    "type": "string",
                    "description": "User email or ID for whom exception is being requested"
                },
                "user_name": {
                    "type": "string",
                    "description": "Full name of the user"
                },
                "role_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of role names being requested"
                },
                "conflict_count": {
                    "type": "integer",
                    "description": "Total number of SOD conflicts detected"
                },
                "critical_conflicts": {
                    "type": "integer",
                    "description": "Number of CRITICAL severity conflicts",
                    "default": 0
                },
                "risk_score": {
                    "type": "number",
                    "description": "Overall risk score (0-100)"
                },
                "business_justification": {
                    "type": "string",
                    "description": "Business reason for approving this exception"
                },
                "job_title": {
                    "type": "string",
                    "description": "User's job title"
                },
                "department": {
                    "type": "string",
                    "description": "User's department"
                },
                "compensating_controls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "control_name": {"type": "string"},
                            "risk_reduction_percentage": {"type": "number"},
                            "estimated_annual_cost": {"type": "number"}
                        }
                    },
                    "description": "List of compensating controls being proposed"
                },
                "review_frequency": {
                    "type": "string",
                    "enum": ["Monthly", "Quarterly", "Annually"],
                    "description": "How often this exception should be reviewed",
                    "default": "Quarterly"
                },
                "auto_approve_if_authorized": {
                    "type": "boolean",
                    "description": "If requester has authority, auto-approve and record exception",
                    "default": False
                }
            },
            "required": ["requester_email", "user_identifier", "user_name", "role_names", "conflict_count", "risk_score", "business_justification"]
        }
    },

    "generate_violation_report": {
        "description": "Generate a detailed tabular report of SOD violations for a specific user. Shows top violations in markdown table format, or exports all violations to Excel/CSV for large datasets. Perfect for analyzing violation patterns and generating audit reports.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "detailed", "excel", "csv"],
                    "description": "Report format: markdown (table), detailed (role matrix), excel (full export), csv (basic export)",
                    "default": "markdown"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of violations to show in console output (only for markdown/detailed formats)",
                    "default": 5
                },
                "export_path": {
                    "type": "string",
                    "description": "Optional file path for Excel/CSV export. If not specified, generates file in /tmp/compliance_reports/"
                }
            },
            "required": ["user_email"]
        }
    },

    "get_role_risk_matrix": {
        "description": (
            "Returns the precomputed SOD conflict matrix for Fivetran NetSuite roles. "
            "Use this tool for questions like: 'which Fivetran roles are dangerous?', "
            "'which role combinations trigger SOD conflicts?', 'is it safe to combine role X with role Y?', "
            "'show me intra-role conflicts', 'what conflicts does Fivetran-Controller have?'. "
            "This matrix is computed from actual role permissions + levels — independent of real user assignments, "
            "so it covers ALL 17 Fivetran roles and all 153 role pairs even if no user currently holds them. "
            "Contrast with list_violations which only surfaces conflicts found in real user data."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "role_name": {
                    "type": "string",
                    "description": (
                        "Filter to conflicts involving this role (partial, case-insensitive). "
                        "E.g. 'Controller', 'A/P Analyst', 'Billing Manager'. "
                        "Omit to return a summary matrix of all role pairs."
                    )
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Filter by conflict severity. Omit to return all severities."
                },
                "include_intra_role": {
                    "type": "boolean",
                    "description": (
                        "When true, includes intra-role conflicts (permissions dangerous within a single role). "
                        "Default true."
                    ),
                    "default": True
                },
                "include_cross_role": {
                    "type": "boolean",
                    "description": (
                        "When true, includes cross-role conflicts (conflicts that emerge when two different roles "
                        "are combined). Default true."
                    ),
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of conflict rows to return. Default 50.",
                    "default": 50
                }
            },
            "required": []
        }
    },
    "list_violations": {
        "description": "List SOD violations with optional filters. Two modes: (1) roles_only=false (default) — for questions about specific people or 'who has violations', returns each affected user with name/email/department/conflicting roles. (2) roles_only=true — for questions like 'which roles have inherent conflicts?', 'which role combinations are toxic?', 'what are the dangerous role pairs?' — returns ONLY the unique conflicting role combinations grouped by severity with affected user counts, NO names or emails at all.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "department": {
                    "type": "string",
                    "description": "Filter by department name (case-insensitive partial match), e.g. 'Finance', 'IT', 'Accounting'. Omit to return all departments."
                },
                "severity": {
                    "type": "string",
                    "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                    "description": "Filter by violation severity. Omit to return all severities."
                },
                "status": {
                    "type": "string",
                    "enum": ["OPEN", "PENDING_REVIEW", "RESOLVED"],
                    "description": "Filter by violation status. Defaults to OPEN (excludes resolved violations).",
                    "default": "OPEN"
                },
                "roles_only": {
                    "type": "boolean",
                    "description": "When true, returns only unique conflicting role combinations with affected user counts — no names or emails. Use this when the question is about which roles or role patterns introduce conflicts, not about specific people.",
                    "default": False
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of rows to return.",
                    "default": 25
                }
            },
            "required": []
        }
    }
}


# ============================================================================
# TOOL HANDLERS
# ============================================================================

async def list_systems_handler() -> str:
    """
    List all available systems

    Returns:
        Formatted string with system information
    """
    try:
        logger.info("list_systems_handler called")
        # Use cached orchestrator instance
        orchestrator = get_orchestrator()
        logger.info("Got orchestrator, calling list_available_systems_sync")
        # Run synchronous method in thread pool
        systems = await asyncio.to_thread(orchestrator.list_available_systems_sync)
        logger.info(f"list_available_systems_sync returned {len(systems)} systems")

        if not systems:
            return "No systems configured. Please configure system connectors."

        result = "**Available Systems for Compliance Review:**\n\n"

        for system in systems:
            status_emoji = "✅" if system['status'] == "connected" else "❌"
            result += f"{status_emoji} **{system['name'].upper()}** ({system['type']})\n"
            result += f"   • Status: {system['status']}\n"
            result += f"   • Users: {system['user_count']:,}\n"
            result += f"   • Last reviewed: {system['last_review']}\n\n"

        return result

    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        print("=== ERROR IN list_systems_handler ===", flush=True)
        print(full_traceback, flush=True)
        print("=== END ERROR ===", flush=True)
        logger.error(f"Error in list_systems_handler: {str(e)}\n{full_traceback}")
        return f"Error listing systems: {str(e)}"


async def perform_access_review_handler(
    system_name: str,
    analysis_type: str = "sod_violations",
    include_recommendations: bool = True
) -> str:
    """
    Perform access review

    Returns:
        Formatted string with review results
    """
    try:
        logger.info(f"Performing access review: {system_name}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.perform_access_review_sync,
            system_name=system_name,
            analysis_type=analysis_type,
            include_recommendations=include_recommendations
        )

        # Format response
        output = f"**Access Review Complete - {result['system_name'].upper()}**\n\n"
        output += "📊 **Summary:**\n"
        output += f"   • Users Analyzed: {result['users_analyzed']:,}\n"
        output += f"   • Total Violations: {result['total_violations']:,}\n"
        output += f"   • High-Risk: {result['high_risk_count']} 🔴\n"
        output += f"   • Medium-Risk: {result['medium_risk_count']} 🟡\n"
        output += f"   • Low-Risk: {result['low_risk_count']} 🟢\n"
        output += f"   • Execution Time: {result['execution_time_seconds']}s\n\n"

        if result['top_violators']:
            output += "👥 **Top Violators:**\n"
            for i, user in enumerate(result['top_violators'][:5], 1):
                output += f"{i}. **{user['name']}** ({user['email']})\n"
                output += f"   └─ {user['violation_count']} violations "
                output += f"({user['high_risk']} high, {user['medium_risk']} medium, {user['low_risk']} low)\n"
            output += "\n"

        if include_recommendations and result.get('recommendations'):
            output += f"💡 **Recommendations:**\n{result['recommendations']}\n\n"

        output += "ℹ️  _Use `get_user_violations` to see details for specific users._"

        return output

    except Exception as e:
        logger.error(f"Error in perform_access_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error performing access review: {str(e)}"


def _format_violations_table(result: dict[str, Any], include_ai_analysis: bool = True) -> str:
    """Format violations as tables (concise tabular format)"""
    output = f"**SOD Violation Analysis: {result['user_name']}**\n\n"

    # User Status - Show first
    result.get('status', 'UNKNOWN')
    is_active = result.get('is_active', False)
    synced_at = result.get('synced_at', 'Unknown')

    status_emoji = "✅" if is_active else "❌"
    status_text = "ACTIVE" if is_active else "INACTIVE"

    output += "**👤 User Status**\n\n"
    output += f"{status_emoji} **{status_text}** in NetSuite (as of {synced_at})\n\n"
    output += "---\n\n"

    # Summary table
    output += "**📊 Summary**\n\n"
    output += "| Metric | Value |\n"
    output += "|--------|-------|\n"
    output += f"| Total Violations | **{result['violation_count']}** |\n"

    # Count by severity
    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for v in result['violations']:
        severity = v.get('severity', 'UNKNOWN')
        if severity in severity_counts:
            severity_counts[severity] += 1

    output += f"| 🔴 CRITICAL | {severity_counts['CRITICAL']} |\n"
    output += f"| 🟠 HIGH | {severity_counts['HIGH']} |\n"
    output += f"| 🟡 MEDIUM | {severity_counts['MEDIUM']} |\n"
    output += f"| 🟢 LOW | {severity_counts['LOW']} |\n"
    output += f"| Roles | {result['role_count']} |\n"
    output += f"| Department | {result.get('department', 'N/A')} |\n"
    output += "\n"

    # Root cause analysis
    if result['roles']:
        output += "**🎯 Root Cause**\n\n"
        output += f"Administrator role combined with financial roles ({', '.join(result['roles'])})\n\n"

    # Top violations table (top 3 by severity)
    critical_violations = [v for v in result['violations'] if v.get('severity') == 'CRITICAL'][:3]

    if critical_violations:
        output += "**⚠️ Top 3 Critical Conflicts**\n\n"
        output += "| # | Violation Type | Risk Score | Impact |\n"
        output += "|---|---------------|------------|--------|\n"

        for i, v in enumerate(critical_violations, 1):
            violation_title = v.get('rule_name', 'Unknown')
            # Shorten title if too long
            if len(violation_title) > 50:
                violation_title = violation_title[:47] + "..."

            risk_score = v.get('risk_score', 0)

            # Determine impact description
            if 'payroll' in violation_title.lower():
                impact = "Payroll fraud risk"
            elif 'journal' in violation_title.lower():
                impact = "Maker-checker bypass"
            elif 'ap' in violation_title.lower() or 'bill' in violation_title.lower():
                impact = "Fraud risk"
            else:
                impact = "SOD conflict"

            output += f"| {i} | {violation_title} | {risk_score:.0f}/100 | {impact} |\n"

        output += "\n"

    # Action required
    output += "**✅ Action Required**\n\n"
    output += "| Priority | Action | Impact |\n"
    output += "|----------|--------|--------|\n"
    output += "| 🔴 HIGH | Remove Administrator role | Eliminates maker-checker bypasses |\n"
    output += "| 🟢 LOW | Retain Controller + NetSuite 360 | Maintains appropriate financial access |\n"
    output += "\n"

    if include_ai_analysis and result.get('ai_analysis'):
        output += f"**🤖 AI Analysis**\n\n{result['ai_analysis']}\n\n"

    return output


def _format_violations_concise(result: dict[str, Any]) -> str:
    """Format violations in concise format"""
    # User Status - Show first
    is_active = result.get('is_active', False)
    synced_at = result.get('synced_at', 'Unknown')
    status_emoji = "✅" if is_active else "❌"
    status_text = "ACTIVE" if is_active else "INACTIVE"

    output = f"**{result['user_name']}** ({result['email']})\n\n"
    output += f"{status_emoji} **{status_text}** in NetSuite (as of {synced_at})\n\n"

    # Count by severity
    severity_counts = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for v in result['violations']:
        severity = v.get('severity', 'UNKNOWN')
        if severity in severity_counts:
            severity_counts[severity] += 1

    output += f"**{result['violation_count']} violations** | "
    output += f"{severity_counts['CRITICAL']} CRITICAL | "
    output += f"{severity_counts['HIGH']} HIGH | "
    output += f"{severity_counts['MEDIUM']} MEDIUM\n\n"

    output += "**Root cause:** Administrator role combined with financial roles\n\n"

    output += "**Top 3 critical conflicts:**\n"
    critical_violations = [v for v in result['violations'] if v.get('severity') == 'CRITICAL'][:3]
    for i, v in enumerate(critical_violations, 1):
        title = v.get('rule_name', 'Unknown')
        # Extract key phrase
        if 'payroll' in title.lower():
            short_title = "Payroll processing + employee master data modification"
        elif 'journal' in title.lower():
            short_title = "Journal entry creation + approval (maker-checker bypass)"
        elif 'ap' in title.lower() or 'bill' in title.lower():
            short_title = "AP bill entry + approval (fraud risk)"
        else:
            short_title = title[:60]

        output += f"{i}. {short_title}\n"

    output += "\n**Action required:** Remove Administrator role immediately. "
    output += "Retain only Controller + NetSuite 360 for appropriate financial access."

    return output


async def get_user_violations_handler(
    system_name: str,
    user_identifier: str,
    include_ai_analysis: bool = True,
    format: str = "table"
) -> str:
    """
    Get user violation details

    Args:
        system_name: System to query
        user_identifier: User email or ID
        include_ai_analysis: Include AI risk analysis
        format: Output format (detailed, table, concise)

    Returns:
        Formatted string with user violations
    """
    try:
        logger.info(f"Fetching violations for user: {user_identifier}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.get_user_violations_sync,
            system_name=system_name,
            user_identifier=user_identifier,
            include_ai_analysis=include_ai_analysis
        )

        # Format based on requested style
        if format.lower() == "table" or format.lower() == "tabular":
            return _format_violations_table(result, include_ai_analysis)
        elif format.lower() == "concise":
            return _format_violations_concise(result)
        else:
            # Default detailed format
            output = f"**{result['user_name']} - Violation Report**\n\n"

            # User Status - Show first
            is_active = result.get('is_active', False)
            synced_at = result.get('synced_at', 'Unknown')
            status_emoji = "✅" if is_active else "❌"
            status_text = "ACTIVE" if is_active else "INACTIVE"
            output += f"{status_emoji} **{status_text}** in NetSuite (as of {synced_at})\n\n"

            # Then show other details
            output += f"📧 Email: {result['email']}\n"
            output += f"🏢 System: {result['system']}\n"
            output += f"🎭 Roles ({result['role_count']}): {', '.join(result['roles'])}\n"
            output += f"⚠️  Total Violations: {result['violation_count']}\n"
            if result.get('department'):
                output += f"📁 Department: {result['department']}\n"
            output += "\n"

            if result['violations']:
                output += "**Violations:**\n\n"
                for i, v in enumerate(result['violations'], 1):
                    severity_emoji = "🔴" if v['severity'] == "HIGH" else "🟡" if v['severity'] == "MEDIUM" else "🟢"
                    output += f"{i}. {severity_emoji} **{v['severity']}**: {v['rule_name']}\n"
                    output += f"   • Description: {v['description']}\n"
                    output += f"   • Risk Score: {v['risk_score']:.1f}/100\n"
                    output += f"   • Status: {v['status']}\n"
                    output += f"   • Detected: {v['detected_at']}\n"
                    output += f"   • Violation ID: `{v['id']}`\n\n"

            if include_ai_analysis and result.get('ai_analysis'):
                output += f"🤖 **AI Risk Analysis:**\n{result['ai_analysis']}\n\n"

            output += "ℹ️  _Use `remediate_violation` with a violation ID to create a remediation plan._"

            return output

    except Exception as e:
        logger.error(f"Error in get_user_violations_handler: {str(e)}", exc_info=True)
        return f"❌ Error fetching user violations: {str(e)}"


async def remediate_violation_handler(
    violation_id: str,
    action: str,
    notes: str = ""
) -> str:
    """
    Create remediation plan

    Returns:
        Formatted string with remediation status
    """
    try:
        logger.info(f"Creating remediation: {violation_id}, {action}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.remediate_violation_sync,
            violation_id=violation_id,
            action=action,
            notes=notes
        )

        # Format response
        output = "✅ **Remediation Initiated**\n\n"
        output += f"📋 Ticket ID: `{result['ticket_id']}`\n"
        output += f"👤 User: {result['user_name']} ({result['user_email']})\n"
        output += f"⚠️  Violation ID: `{result['violation_id']}`\n"
        output += f"🔧 Action: {result['action']}\n"
        output += f"📝 Status: {result['status']}\n"

        if notes:
            output += f"💬 Notes: {notes}\n"

        if result.get('next_steps'):
            output += "\n📌 **Next Steps:**\n"
            for step in result['next_steps']:
                output += f"   • {step}\n"

        output += f"\n⏰ Created: {result['created_at']}"

        return output

    except Exception as e:
        logger.error(f"Error in remediate_violation_handler: {str(e)}", exc_info=True)
        return f"❌ Error creating remediation: {str(e)}"


async def schedule_review_handler(
    system_name: str,
    frequency: str,
    day_of_week: str | None = None,
    time: str | None = None,
    timezone: str = "America/Los_Angeles"
) -> str:
    """
    Schedule recurring review

    Returns:
        Formatted string with schedule confirmation
    """
    try:
        logger.info(f"Scheduling review: {system_name}, {frequency}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.schedule_review_sync,
            system_name=system_name,
            frequency=frequency,
            day_of_week=day_of_week,
            time=time,
            timezone=timezone
        )

        # Format response
        output = "✅ **Review Scheduled Successfully**\n\n"
        output += f"🏢 System: {result['system_name']}\n"
        output += f"🔄 Frequency: {result['frequency']}\n"
        output += f"📅 Schedule: {result['schedule_description']}\n"
        output += f"⏰ Next Run: {result['next_run']}\n"
        output += f"🌍 Timezone: {result['timezone']}\n\n"

        output += "📬 **Notifications will be sent via:**\n"
        for channel in result['notification_channels']:
            output += f"   • {channel}\n"

        output += "\nℹ️  _You'll receive a notification when each review completes._"

        return output

    except Exception as e:
        logger.error(f"Error in schedule_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error scheduling review: {str(e)}"


async def get_violation_stats_handler(
    systems: list[str] = None,
    time_range: str = "month"
) -> str:
    """
    Get violation statistics

    Returns:
        Formatted string with statistics
    """
    try:
        logger.info(f"Fetching violation stats: {time_range}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.get_violation_stats_sync,
            systems=systems if systems else None,
            time_range=time_range
        )

        # Format response
        output = f"**Violation Statistics - {time_range.capitalize()}**\n\n"
        output += "📊 **Overview:**\n"
        output += f"   • Systems Analyzed: {result['system_count']}\n"
        output += f"   • Total Users: {result['total_users']:,}\n"
        output += f"   • Total Violations: {result['total_violations']:,}\n\n"

        output += "🎯 **Risk Distribution:**\n"
        output += f"   • 🔴 High-Risk: {result['high_risk']} ({result['high_risk_percent']}%)\n"
        output += f"   • 🟡 Medium-Risk: {result['medium_risk']} ({result['medium_risk_percent']}%)\n"
        output += f"   • 🟢 Low-Risk: {result['low_risk']} ({result['low_risk_percent']}%)\n\n"

        if result['by_system']:
            output += "🏢 **Violations by System:**\n"
            for system in result['by_system']:
                output += f"   • {system['name']}: {system['violation_count']} violations\n"

        output += f"\n📈 **Trend:** {result['trend_description']}"

        return output

    except Exception as e:
        logger.error(f"Error in get_violation_stats_handler: {str(e)}", exc_info=True)
        return f"❌ Error fetching statistics: {str(e)}"


async def start_collection_agent_handler() -> str:
    """
    Start the autonomous collection agent

    Returns:
        Formatted string with status
    """
    try:
        logger.info("Starting autonomous collection agent")

        from agents.data_collector import get_collection_agent

        # Run synchronous method in thread pool
        agent = await asyncio.to_thread(get_collection_agent)

        if agent.is_running:
            return "⚠️  **Collection Agent Already Running**\n\nThe autonomous collection agent is already running.\nUse `get_collection_agent_status` to check its status."

        await asyncio.to_thread(agent.start)

        output = "✅ **Autonomous Collection Agent Started**\n\n"
        output += "📅 **Scheduled Jobs:**\n"
        output += "   • Full sync: Daily at 2:00 AM\n"
        output += "   • Incremental sync: Every hour\n\n"
        output += "The agent will run in the background and keep data synchronized.\n"
        output += "Use `get_collection_agent_status` to monitor sync progress."

        return output

    except Exception as e:
        logger.error(f"Error in start_collection_agent_handler: {str(e)}", exc_info=True)
        return f"❌ Error starting collection agent: {str(e)}"


async def stop_collection_agent_handler() -> str:
    """
    Stop the autonomous collection agent

    Returns:
        Formatted string with status
    """
    try:
        logger.info("Stopping autonomous collection agent")

        from agents.data_collector import get_collection_agent

        # Run synchronous method in thread pool
        agent = await asyncio.to_thread(get_collection_agent)

        if not agent.is_running:
            return "⚠️  **Collection Agent Not Running**\n\nThe autonomous collection agent is not currently running."

        await asyncio.to_thread(agent.stop)

        output = "✅ **Autonomous Collection Agent Stopped**\n\n"
        output += "The agent has been stopped. Scheduled syncs will not run.\n"
        output += "Use `start_collection_agent` to restart it."

        return output

    except Exception as e:
        logger.error(f"Error in stop_collection_agent_handler: {str(e)}", exc_info=True)
        return f"❌ Error stopping collection agent: {str(e)}"


async def get_collection_agent_status_handler(system_name: str | None = None) -> str:
    """
    Get collection agent status

    Returns:
        Formatted string with status
    """
    try:
        logger.info("Fetching collection agent status")

        from agents.data_collector import get_collection_agent

        # Run synchronous method in thread pool
        agent = await asyncio.to_thread(get_collection_agent)
        status = await asyncio.to_thread(agent.get_sync_status, system_name)

        # Format response
        output = "📊 **Autonomous Collection Agent Status**\n\n"

        # Agent running status
        if status['is_running']:
            output += "🟢 **Status:** Running\n"
        else:
            output += "🔴 **Status:** Stopped\n"
        output += "\n"

        # Last successful sync
        if status['last_successful_sync']:
            last = status['last_successful_sync']
            output += "✅ **Last Successful Sync:**\n"
            output += f"   • Completed: {last['completed_at']}\n"
            if last['duration']:
                output += f"   • Duration: {last['duration']:.2f}s\n"
            output += f"   • Users Synced: {last['users_synced']}\n"
            output += "\n"
        else:
            output += "**Last Successful Sync:** None\n\n"

        # Recent syncs
        if status['recent_syncs']:
            output += f"📜 **Recent Syncs (Last {min(5, len(status['recent_syncs']))}):**\n"
            for sync in status['recent_syncs'][:5]:
                status_emoji = {
                    'success': '✅',
                    'failed': '❌',
                    'running': '🔄',
                    'pending': '⏳'
                }.get(sync['status'], '❓')

                output += f"{status_emoji} {sync['started_at']} - {sync['type'].upper()} - {sync['status'].upper()}\n"
                if sync['duration']:
                    output += f"   └─ Duration: {sync['duration']:.2f}s, Users: {sync['users_synced']}\n"
            output += "\n"

        # 7-day statistics
        if status['statistics_7d']:
            stats = status['statistics_7d']
            output += "📈 **7-Day Statistics:**\n"
            output += f"   • Total Syncs: {stats['total_syncs']}\n"
            output += f"   • Success Rate: {stats['success_rate']:.1f}%\n"
            output += f"   • Avg Duration: {stats['avg_duration']:.2f}s\n"
            output += f"   • Users Synced: {stats['total_users_synced']}\n"
            output += f"   • Roles Synced: {stats['total_roles_synced']}\n"
            output += f"   • Violations Detected: {stats['total_violations_detected']}\n"

        return output

    except Exception as e:
        logger.error(f"Error in get_collection_agent_status_handler: {str(e)}", exc_info=True)
        return f"❌ Error fetching agent status: {str(e)}"


async def trigger_manual_sync_handler(
    system_name: str = "netsuite",
    sync_type: str = "full"
) -> str:
    """
    Trigger manual sync

    Returns:
        Formatted string with sync results
    """
    try:
        logger.info(f"Triggering manual sync: {system_name}, {sync_type}")

        from agents.data_collector import get_collection_agent

        # Run synchronous method in thread pool
        agent = await asyncio.to_thread(get_collection_agent)
        result = await asyncio.to_thread(agent.manual_sync, system_name, sync_type)

        if result['success']:
            output = "✅ **Sync Completed Successfully**\n\n"
            output += f"🆔 Sync ID: `{result['sync_id']}`\n"
            output += f"⏱️  Duration: {result['duration']:.2f}s\n"
            output += f"👥 Users Fetched: {result['users_fetched']}\n"
            output += f"💾 Users Synced: {result['users_synced']}\n"
            output += f"🎭 Roles Synced: {result['roles_synced']}\n"
            output += f"⚠️  Violations Detected: {result['violations_detected']}\n\n"
            output += "ℹ️  _Use `get_violation_stats` to see detailed violation statistics._"
            return output
        else:
            return f"❌ **Sync Failed**\n\nError: {result.get('error', 'Unknown error')}"

    except Exception as e:
        logger.error(f"Error in trigger_manual_sync_handler: {str(e)}", exc_info=True)
        return f"❌ Error triggering sync: {str(e)}"


async def list_all_users_handler(
    system_name: str = "netsuite",
    include_inactive: bool = False,
    filter_by_department: str | None = None,
    limit: int = 100
) -> str:
    """
    List all users with their roles

    Returns:
        Formatted string with user list
    """
    try:
        logger.info(f"Listing all users from {system_name}")

        orchestrator = get_orchestrator()
        # Run synchronous method in thread pool
        result = await asyncio.to_thread(
            orchestrator.list_all_users_sync,
            system_name=system_name,
            include_inactive=include_inactive,
            filter_by_department=filter_by_department,
            limit=limit
        )

        # Format response
        output = f"**User List - {result['system_name'].upper()}**\n\n"
        output += "📊 **Summary:**\n"
        output += f"   • Total Users: {result['total_users']:,}\n"
        output += f"   • Active Users: {result['active_users']:,}\n"
        if result.get('inactive_users'):
            output += f"   • Inactive Users: {result['inactive_users']:,}\n"
        if filter_by_department:
            output += f"   • Department Filter: {filter_by_department}\n"
        output += f"   • Showing: {len(result['users'])} users\n\n"

        if result['users']:
            output += "👥 **Users:**\n\n"
            for i, user in enumerate(result['users'], 1):
                status_emoji = "✅" if user['is_active'] else "❌"
                output += f"{i}. {status_emoji} **{user['name']}** ({user['email']})\n"
                output += f"   └─ Roles: {user['role_count']} | "
                if user.get('department'):
                    output += f"Department: {user['department']} | "
                output += f"Violations: {user.get('violation_count', 0)}\n"

                if i >= limit:
                    remaining = result['total_users'] - i
                    if remaining > 0:
                        output += f"\n_...and {remaining} more users_\n"
                    break
        else:
            output += "No users found.\n"

        output += "\nℹ️  _Use `get_user_violations` to see details for specific users._"

        return output

    except Exception as e:
        logger.error(f"Error in list_all_users_handler: {str(e)}", exc_info=True)
        return f"❌ Error listing users: {str(e)}"


async def analyze_access_request_handler(
    job_title: str,
    requested_roles: list[str],
    user_email: str | None = None
) -> str:
    """
    Analyze access request with level-based SOD analysis

    Returns:
        Formatted string with analysis results
    """
    try:
        logger.info(f"Analyzing access request for {job_title}: {requested_roles}")

        import json
        import subprocess

        # Prepare command
        roles_arg = ",".join(requested_roles)
        cmd = [
            "python3",
            "scripts/analyze_access_request_with_levels.py",
            "--job-title", job_title,
            "--requested-roles", roles_arg,
            "--mode", "single-request"
        ]

        # Run analysis
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return f"❌ **Analysis Failed**\n\nError: {result.stderr}"

        # Read JSON output from file (script writes to output/access_request_analysis.json)
        try:
            from pathlib import Path
            output_file = Path("output/access_request_analysis.json")
            if not output_file.exists():
                return f"❌ **Analysis Failed**\n\nOutput file not found: {output_file}"

            with open(output_file) as f:
                analysis = json.load(f)

        except json.JSONDecodeError as e:
            return f"❌ **Analysis Failed**\n\nCould not parse JSON output: {str(e)}"
        except Exception as e:
            return f"❌ **Analysis Failed**\n\nError reading output file: {str(e)}"

        # Format response
        output = f"**Access Request Analysis: {job_title}**\n\n"
        output += f"📋 **Requested Roles** ({len(requested_roles)}):\n"
        for role in requested_roles:
            output += f"   • {role}\n"
        output += "\n"

        # Overall recommendation
        recommendation = analysis.get('overall_recommendation', 'UNKNOWN')
        risk = analysis.get('overall_risk', 'UNKNOWN')
        conflicts_found = analysis.get('conflicts_found', 0)

        risk_emoji = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡',
            'LOW': '🟢'
        }.get(risk, '⚪')

        output += "**Overall Assessment:**\n"
        output += f"   • Conflicts Found: {conflicts_found}\n"
        output += f"   • Risk Level: {risk_emoji} {risk}\n"
        output += f"   • Recommendation: **{recommendation}**\n\n"

        # Job role validation
        if 'job_role_validation' in analysis:
            validation = analysis['job_role_validation']
            output += "**Job Role Validation:**\n"
            output += f"   • Is Typical Combination: {'✅ Yes' if validation.get('is_typical_combination') else '❌ No'}\n"
            output += f"   • Requires Controls: {'⚠️  Yes' if validation.get('requires_compensating_controls') else '✅ No'}\n"
            if validation.get('business_justification'):
                output += f"   • Justification: {validation['business_justification'][:200]}...\n"
            output += "\n"

        # Conflicts
        if analysis.get('conflicts'):
            output += f"**Detected Conflicts** ({len(analysis['conflicts'])}):\n\n"
            for i, conflict in enumerate(analysis['conflicts'][:5], 1):
                severity = conflict.get('severity', 'UNKNOWN')
                sev_emoji = {'CRIT': '🔴', 'HIGH': '🟠', 'MED': '🟡', 'LOW': '🟢'}.get(severity, '⚪')

                output += f"{i}. {sev_emoji} **{severity}** - {conflict.get('principle', 'Unknown principle')}\n"
                output += f"   • {conflict.get('permission1', 'Unknown')} ({conflict.get('permission1_level', '?')})\n"
                output += f"   • {conflict.get('permission2', 'Unknown')} ({conflict.get('permission2_level', '?')})\n"
                output += f"   • Inherent Risk: {conflict.get('inherent_risk', 0):.1f}/100\n"
                output += "\n"

            if len(analysis['conflicts']) > 5:
                output += f"_...and {len(analysis['conflicts']) - 5} more conflicts_\n\n"

        # NEW: Search for similar approved exceptions (precedents)
        if conflicts_found > 0:
            try:
                precedents_result = await find_similar_exceptions_handler(
                    role_names=requested_roles,
                    job_title=job_title,
                    limit=2  # Show top 2 matches only in analysis
                )

                # Only show precedents if we found some
                if precedents_result and "No Similar Exceptions Found" not in precedents_result:
                    output += "---\n\n"
                    output += "💡 **SIMILAR APPROVED PRECEDENTS**\n\n"
                    output += "_Found previously approved exceptions with similar role combinations:_\n\n"

                    # Extract just the match summaries (simplified view)
                    lines = precedents_result.split('\n')
                    in_match_section = False
                    match_count = 0
                    for line in lines:
                        if line.strip().startswith('🟢') or line.strip().startswith('🟡') or line.strip().startswith('🟠'):
                            in_match_section = True
                            match_count += 1
                            if match_count <= 2:  # Only show first 2
                                output += line + '\n'
                        elif in_match_section and match_count <= 2:
                            if line.strip().startswith('---'):
                                in_match_section = False
                                if match_count < 2:
                                    output += line + '\n'
                                else:
                                    break
                            elif line.strip():
                                output += line + '\n'

                    output += "\n_Use `find_similar_exceptions([role_names])` for complete precedent details._\n\n"
            except Exception as e:
                logger.warning(f"Could not fetch precedents: {str(e)}")
                # Don't fail the entire analysis if precedent search fails
                pass

        # Resolutions
        if analysis.get('resolutions'):
            output += "**Recommended Controls:**\n\n"
            for i, resolution in enumerate(analysis['resolutions'][:3], 1):
                output += f"{i}. **{resolution.get('recommended_action', 'Unknown')}**\n"
                output += f"   • Inherent Risk: {resolution.get('inherent_risk', 0):.1f}/100\n"
                output += f"   • Residual Risk: {resolution.get('residual_risk', 0):.1f}/100\n"
                output += f"   • Risk Reduction: {resolution.get('risk_reduction_percentage', 0)}%\n"

                if resolution.get('control_package'):
                    pkg = resolution['control_package']
                    output += f"   • Package: {pkg.get('package_name', 'Unknown')}\n"
                    output += f"   • Annual Cost: {pkg.get('estimated_annual_cost', 'N/A')}\n"
                output += "\n"

        output += "ℹ️  _Use `get_compensating_controls` to see detailed control descriptions._\n\n"
        output += "⚠️  **Cost Disclaimer:** Annual cost estimates are approximate and vary by organization size (50%-200% of shown values). "
        output += "Costs include system configuration, monitoring tools, staff review time, and audit costs. "
        output += "Excludes NetSuite base subscription and existing staff salaries."

        return output

    except subprocess.TimeoutExpired:
        return "❌ **Analysis Timeout**\n\nThe analysis took too long to complete."
    except Exception as e:
        logger.error(f"Error in analyze_access_request_handler: {str(e)}", exc_info=True)
        return f"❌ Error analyzing access request: {str(e)}"


async def query_sod_rules_handler(
    category1: str | None = None,
    category2: str | None = None,
    severity: str | None = None,
    limit: int = 10
) -> str:
    """
    Query SOD rules from database

    Returns:
        Formatted string with SOD rules
    """
    try:
        logger.info(f"Querying SOD rules: cat1={category1}, cat2={category2}, sev={severity}")


        import psycopg2

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            # Build query
            query = """
                SELECT rule_id, rule_name, principle, category1, category2,
                       base_risk_score, severity, description
                FROM sod_rules
                WHERE is_active = true
            """
            params = []

            if category1:
                query += " AND category1 = %s"
                params.append(category1)

            if category2:
                query += " AND category2 = %s"
                params.append(category2)

            if severity:
                query += " AND severity = %s"
                params.append(severity)

            query += " LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            rules = cursor.fetchall()
        finally:
            conn.close()

        if not rules:
            return "No SOD rules found matching the criteria."

        output = f"**SOD Rules** ({len(rules)} found):\n\n"

        for rule in rules:
            rule_id, name, principle, cat1, cat2, risk, sev, desc = rule
            output += f"**{rule_id}**: {name}\n"
            output += f"   • Principle: {principle}\n"
            output += f"   • Categories: {cat1} ↔ {cat2}\n"
            output += f"   • Severity: {sev} | Risk: {risk}/100\n"
            if desc:
                output += f"   • Description: {desc[:150]}...\n"
            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error in query_sod_rules_handler: {str(e)}", exc_info=True)
        return f"❌ Error querying SOD rules: {str(e)}"


async def get_compensating_controls_handler(
    severity: str,
    include_cost: bool = True
) -> str:
    """
    Get compensating controls for severity level

    Returns:
        Formatted string with controls
    """
    try:
        logger.info(f"Getting compensating controls for {severity}")


        import psycopg2

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            # Get control package for severity
            cursor.execute("""
                SELECT package_id, package_name, description,
                       included_control_ids, total_risk_reduction,
                       estimated_annual_cost, implementation_time_hours
                FROM control_packages
                WHERE severity_level = %s AND is_active = true
                LIMIT 1
            """, (severity,))

            package = cursor.fetchone()

            if not package:
                return f"No control package found for severity: {severity}"

            pkg_id, pkg_name, desc, control_ids, risk_reduction, cost, hours = package

            output = f"**{pkg_name}** (for {severity} severity)\n\n"
            if desc:
                output += f"{desc}\n\n"
            output += "**Package Details:**\n"
            output += f"   • Risk Reduction: {risk_reduction}%\n"
            if include_cost:
                output += f"   • Annual Cost: {cost}\n"
                output += f"   • Implementation Time: {hours} hours\n"
            output += "\n"

            # Get individual controls
            if control_ids:
                cursor.execute("""
                    SELECT control_id, name, control_type, description,
                           risk_reduction_percentage, annual_cost_estimate
                    FROM compensating_controls
                    WHERE control_id = ANY(%s) AND is_active = true
                """, (control_ids,))

                controls = cursor.fetchall()

                if controls:
                    output += f"**Included Controls** ({len(controls)}):\n\n"
                    for ctrl in controls:
                        ctrl_id, name, ctrl_type, ctrl_desc, reduction, ctrl_cost = ctrl
                        output += f"• **{name}** ({ctrl_type})\n"
                        output += f"  └─ Risk Reduction: {reduction}%"
                        if include_cost:
                            output += f" | Cost: {ctrl_cost}"
                        output += "\n"
                        if ctrl_desc:
                            output += f"  └─ {ctrl_desc[:120]}...\n"
                        output += "\n"
        finally:
            conn.close()

        return output

    except Exception as e:
        logger.error(f"Error in get_compensating_controls_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting compensating controls: {str(e)}"


async def validate_job_role_handler(
    job_title: str,
    requested_roles: list[str]
) -> str:
    """
    Validate job role combination

    Returns:
        Formatted string with validation results
    """
    try:
        logger.info(f"Validating job role: {job_title}")


        import psycopg2

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            # Search for job role by title (case-insensitive)
            cursor.execute("""
                SELECT job_role_id, job_title, department,
                       typical_netsuite_roles, acceptable_role_combinations,
                       typical_resolution_strategy, typical_required_controls,
                       business_justification
                FROM job_role_mappings
                WHERE LOWER(job_title) = LOWER(%s) AND is_active = true
                LIMIT 1
            """, (job_title,))

            role_mapping = cursor.fetchone()
        finally:
            conn.close()

        if not role_mapping:
            return f"❌ **Job Role Not Found**\n\nNo mapping found for job title: {job_title}\n\nℹ️  Use `get_permission_categories` to see available job roles."

        role_id, title, dept, typical, acceptable, strategy, controls, justification = role_mapping

        output = f"**Job Role Validation: {title}**\n\n"
        if dept:
            output += f"📁 Department: {dept}\n\n"

        # Check if requested roles match typical roles
        typical_role_names = [r.get('role', '') for r in typical] if isinstance(typical, list) else []

        matches = [r for r in requested_roles if r in typical_role_names]

        output += "**Requested Roles Analysis:**\n"
        output += f"   • Roles Requested: {len(requested_roles)}\n"
        output += f"   • Typical for Role: {len(matches)}/{len(requested_roles)}\n"
        output += f"   • Resolution Strategy: {strategy}\n\n"

        # Show typical roles
        if typical_role_names:
            output += f"**Typical Roles for {title}:**\n"
            for role_name in typical_role_names[:5]:
                match_emoji = "✅" if role_name in requested_roles else "○"
                output += f"   {match_emoji} {role_name}\n"
            output += "\n"

        # Required controls
        if controls and len(controls) > 0:
            output += "**Typically Required Controls:**\n"
            for ctrl in controls[:5]:
                output += f"   • {ctrl}\n"
            output += "\n"

        # Business justification
        if justification:
            output += "**Business Justification:**\n"
            output += f"{justification[:300]}...\n\n"

        # Recommendation
        if len(matches) == len(requested_roles):
            output += "✅ **Recommendation**: APPROVE - This is a typical combination for this job role."
        elif len(matches) > 0:
            output += "⚠️  **Recommendation**: REVIEW - Some roles are typical, but additional roles may require justification."
        else:
            output += "❌ **Recommendation**: REVIEW REQUIRED - This is not a typical combination for this job role."

        return output

    except Exception as e:
        logger.error(f"Error in validate_job_role_handler: {str(e)}", exc_info=True)
        return f"❌ Error validating job role: {str(e)}"


async def check_permission_conflict_handler(
    permission1_name: str,
    permission1_level: str,
    permission2_name: str,
    permission2_level: str
) -> str:
    """
    Check if two permissions conflict

    Returns:
        Formatted string with conflict analysis
    """
    try:
        logger.info(f"Checking conflict: {permission1_name}({permission1_level}) vs {permission2_name}({permission2_level})")

        # Convert level names to values
        level_map = {'None': 0, 'View': 1, 'Create': 2, 'Edit': 3, 'Full': 4}
        level1 = level_map.get(permission1_level, 0)
        level2 = level_map.get(permission2_level, 0)

        # Use level-based conflict matrix
        severity_matrix = [
            ['OK',   'OK',   'OK',   'OK',   'OK'  ],
            ['OK',   'OK',   'LOW',  'LOW',  'MED' ],
            ['OK',   'LOW',  'MED',  'HIGH', 'CRIT'],
            ['OK',   'LOW',  'HIGH', 'CRIT', 'CRIT'],
            ['OK',   'MED',  'CRIT', 'CRIT', 'CRIT']
        ]

        severity = severity_matrix[level1][level2]

        output = "**Permission Conflict Analysis**\n\n"
        output += f"**Permission 1**: {permission1_name} ({permission1_level}, level {level1})\n"
        output += f"**Permission 2**: {permission2_name} ({permission2_level}, level {level2})\n\n"

        severity_emoji = {'OK': '✅', 'LOW': '🟢', 'MED': '🟡', 'HIGH': '🟠', 'CRIT': '🔴'}.get(severity, '⚪')

        output += f"**Conflict Severity**: {severity_emoji} **{severity}**\n\n"

        # Explanation
        if severity == 'OK':
            output += "✅ No conflict - This combination is permissible without additional controls."
        elif severity == 'LOW':
            output += "🟢 Low risk - Permissible with basic oversight (manager review, periodic audit)."
        elif severity == 'MED':
            output += "🟡 Medium risk - Requires compensating controls (transaction limits, dual approval)."
        elif severity == 'HIGH':
            output += "🟠 High risk - Requires extensive controls or level reduction."
        elif severity == 'CRIT':
            output += "🔴 Critical conflict - Reject or require executive override with maximum controls."

        output += f"\n\nℹ️  _Use `get_compensating_controls` with severity='{severity}' to see recommended controls._"

        return output

    except Exception as e:
        logger.error(f"Error in check_permission_conflict_handler: {str(e)}", exc_info=True)
        return f"❌ Error checking permission conflict: {str(e)}"


async def get_permission_categories_handler(
    include_permissions: bool = False
) -> str:
    """
    Get all permission categories

    Returns:
        Formatted string with categories
    """
    try:
        logger.info("Getting permission categories")


        import psycopg2

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT category_id, category_name, description, base_risk_score
                FROM permission_categories
                ORDER BY base_risk_score DESC
            """)

            categories = cursor.fetchall()
        finally:
            conn.close()

        if not categories:
            return "No permission categories found in database."

        output = f"**Permission Categories** ({len(categories)}):\n\n"

        for cat in categories:
            cat_id, name, desc, risk = cat
            output += f"• **{name}** (`{cat_id}`)\n"
            output += f"  └─ Base Risk: {risk}/100\n"
            if desc:
                output += f"  └─ {desc[:100]}...\n"
            output += "\n"

        output += "\nℹ️  _Use `search_permissions` with category to see permissions in each category._"

        return output

    except Exception as e:
        logger.error(f"Error in get_permission_categories_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting permission categories: {str(e)}"


async def search_permissions_handler(
    search_term: str | None = None,
    category: str | None = None,
    risk_level: str | None = None,
    limit: int = 20
) -> str:
    """
    Search permissions

    Returns:
        Formatted string with search results
    """
    try:
        logger.info(f"Searching permissions: term={search_term}, cat={category}, risk={risk_level}")

        import json
        from pathlib import Path

        # Load permission mapping
        mapping_file = Path('data/netsuite_permission_mapping.json')
        if not mapping_file.exists():
            return "❌ Permission mapping file not found. Run `analyze_and_categorize_permissions.py` first."

        with open(mapping_file) as f:
            data = json.load(f)

        permissions = data.get('permissions', {})

        # Filter permissions
        filtered = []
        for _perm_id, perm in permissions.items():
            matches = True

            if search_term:
                if search_term.lower() not in perm['permission_name'].lower():
                    matches = False

            if category:
                if category not in perm.get('categories', []):
                    matches = False

            if risk_level:
                if perm.get('base_risk_level') != risk_level:
                    matches = False

            if matches:
                filtered.append(perm)

        # Sort by usage count
        filtered.sort(key=lambda x: x.get('usage_count', 0), reverse=True)
        filtered = filtered[:limit]

        if not filtered:
            return "No permissions found matching the criteria."

        output = f"**Permission Search Results** ({len(filtered)} found):\n\n"

        for perm in filtered:
            output += f"• **{perm['permission_name']}** (`{perm['permission_id']}`)\n"
            output += f"  └─ Categories: {', '.join(perm.get('categories', []))}\n"
            output += f"  └─ Risk: {perm.get('base_risk_level', 'UNKNOWN')}\n"
            output += f"  └─ Levels: {', '.join(perm.get('levels_granted', []))}\n"
            output += f"  └─ Used by: {perm.get('usage_count', 0)} roles\n"
            output += "\n"

        if len(permissions) > limit:
            output += f"_Showing {limit} of {len(permissions)} total results_\n"

        return output

    except Exception as e:
        logger.error(f"Error in search_permissions_handler: {str(e)}", exc_info=True)
        return f"❌ Error searching permissions: {str(e)}"


async def query_knowledge_base_handler(
    query: str,
    doc_type: str = "ALL",
    limit: int = 5
) -> str:
    """
    Query vector knowledge base using semantic search

    This grounds the analysis in actual compliance data from the vector database
    before generating recommendations.

    Returns:
        Formatted string with relevant knowledge base documents
    """
    try:
        logger.info(f"Querying knowledge base: query='{query}', type={doc_type}, limit={limit}")

        import json

        import psycopg2
        from sentence_transformers import SentenceTransformer

        # Load embedding model
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Generate query embedding
        query_embedding = model.encode(query).tolist()

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            # Build query with optional doc_type filter
            sql = """
                SELECT
                    doc_id,
                    doc_type,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_base_documents
            """
            params = [query_embedding]

            if doc_type != "ALL":
                sql += " WHERE doc_type = %s"
                params.append(doc_type)

            sql += """
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding, limit])

            cursor.execute(sql, params)
            results = cursor.fetchall()
        finally:
            conn.close()

        if not results:
            return f"No knowledge base documents found for query: '{query}'"

        # Format output
        output = f"**Knowledge Base Search Results** ({len(results)} found)\n"
        output += f"Query: _{query}_\n\n"

        for i, (doc_id, doc_type_val, content, metadata, similarity) in enumerate(results, 1):
            # Parse metadata if it's JSON
            meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata

            output += f"{i}. **{doc_id}** (Similarity: {similarity:.2%})\n"
            output += f"   • Type: {doc_type_val}\n"

            # Show relevant metadata
            if meta_dict:
                if 'severity' in meta_dict:
                    output += f"   • Severity: {meta_dict['severity']}\n"
                if 'risk_score' in meta_dict:
                    output += f"   • Risk Score: {meta_dict['risk_score']}/100\n"
                if 'principle' in meta_dict:
                    output += f"   • Principle: {meta_dict['principle']}\n"

            # Show content preview
            content_preview = content[:200] + "..." if len(content) > 200 else content
            output += f"   • Content: {content_preview}\n"
            output += "\n"

        output += "\nℹ️  _These results are retrieved from the pgvector knowledge base and should be used to ground compliance recommendations._"

        return output

    except Exception as e:
        logger.error(f"Error in query_knowledge_base_handler: {str(e)}", exc_info=True)
        return f"❌ Error querying knowledge base: {str(e)}"


async def recommend_roles_for_job_title_handler(
    job_title: str,
    department: str = None,
    format: str = "summary"
) -> str:
    """
    Recommend roles based on what existing employees with similar job titles have

    Args:
        job_title: Job title of new hire
        department: Optional department filter
        format: 'summary' or 'detailed'

    Returns:
        Formatted recommendations based on peer analysis
    """
    try:
        logger.info(f"Getting role recommendations for job title: {job_title}, department: {department}")

        from models.database_config import DatabaseConfig
        from services.role_recommendation_service import RoleRecommendationService

        db_config = DatabaseConfig()
        session = db_config.get_session()

        service = RoleRecommendationService(session)
        result = service.recommend_roles_by_job_title(job_title, department=department)

        if not result['success']:
            return f"❌ {result['message']}"

        # Check how many peers actually have roles
        peers_with_roles = sum(1 for p in result['peer_details'] if p['role_count'] > 0)
        peers_without_roles = result['peers_analyzed'] - peers_with_roles

        # Format output - COMPACT without names
        dept_filter = f" in {department}" if department else ""
        output = f"**{job_title}{dept_filter}**\n\n"

        output += "📊 **Peer Analysis:**\n"
        output += f"   • {result['peers_analyzed']} peer(s) found\n"
        output += f"   • {peers_with_roles} with roles, {peers_without_roles} without\n"

        # Warn if sample size is too small
        if peers_with_roles == 0:
            output += "\n❌ No peers with roles assigned.\n"
            output += "Use `analyze_access_request` to test role combinations.\n"
            return output
        elif peers_with_roles < 2:
            output += f"\n⚠️ Limited data ({peers_with_roles} peer with roles)\n"

        # Show roles
        if result['recommended_roles']:
            output += "\n**Recommended Roles** (from peers):\n"
            for rec in result['recommended_roles']:
                output += f"• {rec['role_name']}\n"

        # Show conflict warning if exists
        if result.get('conflict_analysis') and result['conflict_analysis'].get('has_conflicts'):
            conflict = result['conflict_analysis']
            risk_emoji = "🔴" if conflict.get('risk_level') == 'HIGH' else "🟠" if conflict.get('risk_level') == 'MEDIUM' else "🟡"
            if conflict.get('conflict_count'):
                output += f"\n{risk_emoji} **{conflict['conflict_count']} SOD conflicts** ({conflict.get('risk_level', 'UNKNOWN')} risk)\n"
            output += "Requires compensating controls. Use `analyze_access_request` for details.\n"
        else:
            output += "\n✅ No significant conflicts detected\n"

        return output

    except Exception as e:
        logger.error(f"Error in recommend_roles_for_job_title_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting role recommendations: {str(e)}"


async def analyze_role_permissions_handler(
    role_name: str,
    include_remediation_plan: bool = True,
    output_format: str = "markdown"
) -> str:
    """
    Analyze internal SOD conflicts within a single role

    This generates a comprehensive report with:
    - Conflict analysis (CRITICAL/HIGH/MEDIUM)
    - Permission breakdown by category
    - Level modification recommendations
    - Remediation options

    Returns summary + saves detailed report to file
    """
    try:
        logger.info(f"Analyzing role: {role_name}")

        import json
        from collections import defaultdict
        from datetime import datetime
        from pathlib import Path

        import psycopg2

        # Get role permissions from database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT role_name, permissions
                FROM roles
                WHERE role_name = %s
            """, (role_name,))

            result = cursor.fetchone()
        finally:
            conn.close()

        if not result:
            return f"❌ Role not found: {role_name}\n\nAvailable roles can be found using list_all_users tool."

        _, permissions_json = result
        permissions = json.loads(permissions_json) if isinstance(permissions_json, str) else permissions_json

        # Load permission mapping
        perm_mapping_path = Path('data/netsuite_permission_mapping.json')
        if not perm_mapping_path.exists():
            return "❌ Permission mapping file not found. Run analyze_and_categorize_permissions.py first."

        with open(perm_mapping_path) as f:
            perm_mapping = json.load(f)['permissions']

        # Level values
        LEVEL_MAP = {
            'None': 0,
            'View': 1,
            'Create': 2,
            'Edit': 3,
            'Full': 4
        }

        # Conflict matrix
        CONFLICT_MATRIX = [
            ['OK',   'OK',   'OK',   'OK',   'OK'  ],
            ['OK',   'OK',   'LOW',  'LOW',  'MED' ],
            ['OK',   'LOW',  'MED',  'HIGH', 'CRIT'],
            ['OK',   'LOW',  'HIGH', 'CRIT', 'CRIT'],
            ['OK',   'MED',  'CRIT', 'CRIT', 'CRIT']
        ]

        # Categorize permissions
        categorized_perms = []
        for perm in permissions:
            perm_id = perm['permission']
            perm_name = perm['permission_name']
            level = perm['level']
            level_value = LEVEL_MAP.get(level, 0)

            if perm_id in perm_mapping:
                categories = perm_mapping[perm_id].get('categories', [])
                risk = perm_mapping[perm_id].get('base_risk_level', 'UNKNOWN')
            else:
                categories = []
                risk = 'UNKNOWN'

            categorized_perms.append({
                'id': perm_id,
                'name': perm_name,
                'level': level,
                'level_value': level_value,
                'categories': categories,
                'risk': risk
            })

        # Find conflicts
        conflicts = []
        by_category = defaultdict(list)
        for perm in categorized_perms:
            for cat in perm['categories']:
                by_category[cat].append(perm)

        # SOD category pairs to check
        SOD_CATEGORY_PAIRS = [
            ('transaction_entry', 'transaction_approval'),
            ('transaction_entry', 'transaction_payment'),
            ('transaction_payment', 'bank_reconciliation'),
            ('vendor_setup', 'transaction_payment'),
            ('user_admin', 'transaction_entry'),
            ('user_admin', 'transaction_approval'),
            ('role_admin', 'transaction_entry')
        ]

        for cat1, cat2 in SOD_CATEGORY_PAIRS:
            perms1 = by_category.get(cat1, [])
            perms2 = by_category.get(cat2, [])

            for p1 in perms1:
                for p2 in perms2:
                    if p1['id'] != p2['id']:
                        severity = CONFLICT_MATRIX[p1['level_value']][p2['level_value']]

                        if severity in ['MED', 'HIGH', 'CRIT']:
                            conflicts.append({
                                'perm1': p1,
                                'perm2': p2,
                                'severity': severity,
                                'categories': f"{cat1} ↔ {cat2}"
                            })

        # Sort by severity
        severity_order = {'CRIT': 3, 'HIGH': 2, 'MED': 1}
        conflicts.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)

        # Count by severity
        by_sev = defaultdict(list)
        for c in conflicts:
            by_sev[c['severity']].append(c)

        # Generate detailed report file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_role_name = role_name.replace(' ', '_').replace('-', '_')

        output_dir = Path('output/role_analysis')
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / f"{safe_role_name}_{timestamp}.md"

        # Generate comprehensive markdown report
        with open(report_path, 'w') as f:
            f.write(f"# {role_name} - Internal SOD Conflict Analysis\n\n")
            f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Permissions**: {len(permissions)}\n")
            f.write(f"**Categorized Permissions**: {len([p for p in categorized_perms if p['categories']])}\n")
            f.write(f"**Internal Conflicts Found**: {len(conflicts)}\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")

            if conflicts:
                f.write("### Risk Assessment\n\n")
                f.write("| Severity | Count | Risk Level |\n")
                f.write("|----------|-------|------------|\n")
                f.write(f"| 🔴 CRITICAL | {len(by_sev.get('CRIT', []))} | {'Unacceptable - Immediate action required' if by_sev.get('CRIT') else 'None'} |\n")
                f.write(f"| 🟠 HIGH | {len(by_sev.get('HIGH', []))} | {'High Risk - Remediation needed' if by_sev.get('HIGH') else 'None'} |\n")
                f.write(f"| 🟡 MEDIUM | {len(by_sev.get('MED', []))} | {'Moderate Risk - Review recommended' if by_sev.get('MED') else 'None'} |\n")
                f.write(f"| **Total** | **{len(conflicts)}** | **{'Role requires attention' if conflicts else 'No issues'}** |\n\n")

                if by_sev.get('CRIT'):
                    f.write("### ⚠️  Overall Recommendation\n\n")
                    f.write(f"**ROLE REQUIRES REDESIGN** - {len(by_sev['CRIT'])} CRITICAL conflicts detected.\n\n")
            else:
                f.write("✅ **No internal SOD conflicts detected in this role.**\n\n")

            # Detailed conflicts
            if conflicts:
                f.write("---\n\n## Detailed Conflict Analysis\n\n")

                for sev in ['CRIT', 'HIGH', 'MED']:
                    if sev in by_sev:
                        f.write(f"### {sev} SEVERITY CONFLICTS ({len(by_sev[sev])} found)\n\n")

                        for i, conflict in enumerate(by_sev[sev][:20], 1):
                            p1 = conflict['perm1']
                            p2 = conflict['perm2']

                            f.write(f"#### Conflict #{i}\n\n")
                            f.write(f"**{p1['name']}** ({p1['level']}, level {p1['level_value']})\n")
                            f.write("↔\n")
                            f.write(f"**{p2['name']}** ({p2['level']}, level {p2['level_value']})\n\n")
                            f.write(f"- **Category Conflict**: {conflict['categories']}\n")
                            f.write(f"- **Severity**: {sev}\n")
                            f.write(f"- **Recommended Fix**: Reduce {p1['name']} to View level OR separate into different role\n\n")

                        if len(by_sev[sev]) > 20:
                            f.write(f"_... and {len(by_sev[sev]) - 20} more {sev} conflicts_\n\n")

            # Permission breakdown
            f.write("---\n\n## Permission Breakdown by Category\n\n")

            for cat in sorted(by_category.keys()):
                perms = by_category[cat]
                f.write(f"### {cat.upper().replace('_', ' ')} ({len(perms)} permissions)\n\n")
                f.write("| Permission | Level | Risk |\n")
                f.write("|------------|-------|------|\n")

                for p in perms[:30]:
                    risk_icon = '🔴' if p['risk'] == 'HIGH' else '🟡' if p['risk'] == 'MEDIUM' else '🟢'
                    f.write(f"| {p['name']} | {p['level']} | {risk_icon} {p['risk']} |\n")

                if len(perms) > 30:
                    f.write(f"\n_... and {len(perms) - 30} more permissions_\n")
                f.write("\n")

            # Remediation recommendations
            if include_remediation_plan and conflicts:
                f.write("---\n\n## Remediation Recommendations\n\n")

                # Priority level changes
                f.write("### Priority 1: Critical Level Changes\n\n")
                f.write("These changes will eliminate the most CRITICAL conflicts:\n\n")
                f.write("| Permission | Current Level | Recommended Level | Impact |\n")
                f.write("|------------|---------------|-------------------|--------|\n")

                # Find permissions involved in CRIT conflicts
                crit_perms = set()
                for c in by_sev.get('CRIT', []):
                    if c['perm1']['level_value'] >= 3:
                        crit_perms.add((c['perm1']['name'], c['perm1']['level'], c['perm1']['level_value']))
                    if c['perm2']['level_value'] >= 3:
                        crit_perms.add((c['perm2']['name'], c['perm2']['level'], c['perm2']['level_value']))

                for name, level, level_val in sorted(crit_perms, key=lambda x: x[2], reverse=True)[:10]:
                    if level_val == 4:
                        recommended = "Edit (3)"
                    elif level_val == 3:
                        recommended = "View (1)"
                    else:
                        recommended = level

                    f.write(f"| {name} | {level} ({level_val}) | {recommended} | Reduces CRIT conflicts |\n")

                f.write("\n")

        # Generate summary for MCP response
        summary = f"**Role Analysis Complete: {role_name}**\n\n"
        summary += "📊 **Analysis Summary**:\n"
        summary += f"• Total Permissions: {len(permissions)}\n"
        summary += f"• Total Conflicts: {len(conflicts)}\n"
        summary += f"• 🔴 CRITICAL: {len(by_sev.get('CRIT', []))}\n"
        summary += f"• 🟠 HIGH: {len(by_sev.get('HIGH', []))}\n"
        summary += f"• 🟡 MEDIUM: {len(by_sev.get('MED', []))}\n\n"

        if len(by_sev.get('CRIT', [])) > 0:
            summary += "⚠️  **CRITICAL ISSUES FOUND**\n\n"
            summary += "Top 5 Critical Conflicts:\n\n"
            for i, c in enumerate(by_sev['CRIT'][:5], 1):
                p1 = c['perm1']
                p2 = c['perm2']
                summary += f"{i}. **{p1['name']}** ({p1['level']}) ↔ **{p2['name']}** ({p2['level']})\n"
                summary += f"   Category: {c['categories']}\n\n"
        else:
            summary += "✅ **No critical conflicts found**\n\n"

        summary += "📄 **Detailed Report Generated**:\n"
        summary += f"• File: `{report_path}`\n"
        summary += "• Format: Markdown\n"
        summary += f"• Size: {len(conflicts)} conflicts analyzed\n\n"

        if include_remediation_plan and conflicts:
            summary += "📋 **Remediation Options Included**:\n"
            summary += "• Priority level changes\n"
            summary += "• Permission breakdown by category\n"
            summary += "• Specific recommendations for each conflict\n\n"

        summary += "💡 **Next Steps**:\n"
        summary += f"1. Review detailed report at: `{report_path}`\n"
        summary += "2. Implement recommended level changes\n"
        summary += "3. Test role functionality after changes\n"
        summary += "4. Re-run analysis to verify conflict resolution\n"

        logger.info(f"Role analysis complete. Report saved to: {report_path}")

        return summary

    except Exception as e:
        logger.error(f"Error in analyze_role_permissions_handler: {str(e)}", exc_info=True)
        return f"❌ Error analyzing role permissions: {str(e)}"


async def get_role_conflicts_handler(role_name: str) -> str:
    """
    Get pre-analyzed internal SOD conflicts for a role from knowledge base

    This is faster and simpler than analyze_role_permissions as it queries
    the pre-built knowledge base rather than analyzing from scratch.
    """
    try:
        logger.info(f"Querying knowledge base for role conflicts: {role_name}")

        import json

        import psycopg2
        from sentence_transformers import SentenceTransformer

        # Load embedding model
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # Generate query embedding
        query_text = f"{role_name} internal SOD conflicts"
        query_embedding = model.encode(query_text).tolist()

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        try:
            cursor = conn.cursor()

            # Search knowledge base for this specific role
            cursor.execute("""
                SELECT
                    title,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM knowledge_base_documents
                WHERE doc_type = 'role_conflict_analysis'
                  AND title ILIKE %s
                ORDER BY similarity DESC
                LIMIT 1
            """, (query_embedding, f"%{role_name}%"))

            result = cursor.fetchone()
        finally:
            conn.close()

        if not result:
            return f"""❌ No conflict analysis found for role: {role_name}

This could mean:
1. The role has not been analyzed yet
2. The role name doesn't match exactly (try searching with query_knowledge_base)
3. The role has no conflicts (check with analyze_role_permissions)

Tip: Try using query_knowledge_base with a broader search."""

        title, content, metadata_json, similarity = result
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json

        # Format response
        metadata.get('conflict_count', 0)
        metadata.get('severity_max', 'UNKNOWN')

        response = f"""# {title}

{content}

---

**Data Quality**:
- Similarity Score: {similarity:.1%}
- Last Analysis: Pre-analyzed (2026-02-12)
- Source: Knowledge Base

**Next Steps**:
1. Review users assigned this role
2. Implement recommended remediations
3. Set up compensating controls if role cannot be split immediately

Use `analyze_access_request` to check if specific users have additional conflicts beyond this role's internal issues."""

        return response

    except Exception as e:
        logger.error(f"Error in get_role_conflicts_handler: {str(e)}", exc_info=True)
        return f"❌ Error querying role conflicts: {str(e)}\n\nTry using query_knowledge_base tool instead."


# ============================================================================
# EXCEPTION MANAGEMENT HANDLERS
# ============================================================================

async def record_exception_approval_handler(
    user_identifier: str,
    user_name: str,
    role_names: list[str],
    conflict_count: int,
    risk_score: float,
    business_justification: str,
    approved_by: str,
    approval_authority: str = None,
    job_title: str = None,
    department: str = None,
    critical_conflicts: int = 0,
    compensating_controls: list[dict[str, Any]] = None,
    review_frequency: str = "Quarterly",
    expiration_days: int = None
) -> str:
    """
    Record an approved SOD exception with compensating controls

    Returns:
        Formatted confirmation with exception code and control summary
    """
    try:
        logger.info(f"Recording exception approval for user: {user_identifier}")

        from datetime import datetime, timedelta

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository
        from repositories.role_repository import RoleRepository
        from repositories.user_repository import UserRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)

        # Get user UUID
        user = user_repo.get_user_by_email(user_identifier)
        if not user:
            user = user_repo.get_user_by_id(user_identifier)
        if not user:
            return f"❌ User not found: {user_identifier}\n\nPlease ensure the user exists in the system first."

        # Convert role names to IDs
        role_ids = []
        for role_name in role_names:
            role = role_repo.get_role_by_name(role_name)
            if role:
                role_ids.append(role.id)
            else:
                logger.warning(f"Role not found: {role_name}")

        # Calculate expiration date if provided
        expires_at = None
        if expiration_days:
            expires_at = datetime.utcnow() + timedelta(days=expiration_days)

        # Create exception
        exception = exception_repo.create_exception(
            user_id=user.id,
            user_name=user_name,
            role_ids=role_ids,
            role_names=role_names,
            conflict_count=conflict_count,
            critical_conflicts=critical_conflicts,
            risk_score=risk_score,
            business_justification=business_justification,
            approved_by=approved_by,
            approval_authority=approval_authority,
            job_title=job_title,
            department=department,
            review_frequency=review_frequency,
            expires_at=expires_at
        )

        # Add compensating controls if provided
        total_cost = 0
        if compensating_controls:
            for control in compensating_controls:
                # Look up control by name in compensating_controls table
                control_name = control.get('control_name', '')
                session.query(text("SELECT id FROM compensating_controls WHERE name ILIKE :name LIMIT 1"))
                result = session.execute(text("SELECT id FROM compensating_controls WHERE name ILIKE :name LIMIT 1"), {"name": f"%{control_name}%"}).fetchone()

                if result:
                    control_id = result[0]
                else:
                    # Use default dual approval if not found
                    result = session.execute(text("SELECT id FROM compensating_controls WHERE control_id = 'dual_approval_workflow' LIMIT 1")).fetchone()
                    control_id = result[0] if result else None

                if control_id:
                    exception_repo.add_control_to_exception(
                        exception.exception_id,
                        control_id=control_id,
                        estimated_annual_cost=control.get('estimated_annual_cost', 0),
                        risk_reduction_percentage=control.get('risk_reduction_percentage', 0)
                    )
                    total_cost += control.get('estimated_annual_cost', 0)
                else:
                    logger.warning(f"Control not found and no default available: {control_name}")

        session.commit()

        # Format response
        output = f"""✅ **Exception Approved and Recorded**

**Exception Code:** `{exception.exception_code}`
**User:** {user_name} ({user_identifier})
**Status:** {exception.status.value}

**Conflict Summary:**
• Total Conflicts: {conflict_count}
• Critical Conflicts: {critical_conflicts}
• Risk Score: {risk_score:.1f}/100

**Approved Role Combination:**
"""
        for i, role in enumerate(role_names, 1):
            output += f"{i}. {role}\n"

        if compensating_controls:
            output += f"\n**Compensating Controls ({len(compensating_controls)}):**\n"
            for i, control in enumerate(compensating_controls, 1):
                ctrl_name = control.get('control_name', 'Unnamed Control')
                risk_red = control.get('risk_reduction_percentage', 0)
                cost = control.get('estimated_annual_cost', 0)
                output += f"{i}. {ctrl_name}\n"
                output += f"   └─ Risk Reduction: {risk_red}%\n"
                output += f"   └─ Annual Cost: ${cost:,.0f}\n"

            output += f"\n**Total Annual Cost:** ${total_cost:,.0f}\n"

        output += f"\n**Review Schedule:** {review_frequency}"
        if expires_at:
            output += f"\n**Expires:** {expires_at.strftime('%Y-%m-%d')}"

        output += f"\n**Approved By:** {approved_by}"
        if approval_authority:
            output += f" ({approval_authority})"

        output += f"\n\n**Business Justification:**\n{business_justification}"

        output += "\n\n💡 **Next Steps:**\n"
        output += "• Implement all compensating controls\n"
        output += f"• Set up {review_frequency.lower()} review calendar\n"
        output += "• Monitor for violations using exception tracking\n"
        output += f"• Use `get_exception_details('{exception.exception_code}')` to check status"

        return output

    except Exception as e:
        logger.error(f"Error in record_exception_approval_handler: {str(e)}", exc_info=True)
        return f"❌ Error recording exception approval: {str(e)}"


async def find_similar_exceptions_handler(
    role_names: list[str],
    job_title: str = None,
    department: str = None,
    limit: int = 3
) -> str:
    """
    Find similar previously approved exceptions

    Returns:
        Formatted list of similar exceptions with similarity scores
    """
    try:
        logger.info(f"Finding similar exceptions for roles: {role_names}")

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository
        from repositories.role_repository import RoleRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)
        role_repo = RoleRepository(session)

        # Convert role names to IDs
        role_ids = []
        for role_name in role_names:
            role = role_repo.get_role_by_name(role_name)
            if role:
                role_ids.append(role.id)

        if not role_ids:
            return f"❌ No matching roles found for: {', '.join(role_names)}"

        # Find similar exceptions
        similar = exception_repo.find_similar_exceptions(
            role_ids=role_ids,
            job_title=job_title,
            department=department,
            limit=limit
        )

        if not similar:
            output = "📝 **No Similar Exceptions Found**\n\n"
            output += "**Searched For:**\n"
            output += f"• Roles: {', '.join(role_names)}\n"
            if job_title:
                output += f"• Job Title: {job_title}\n"
            if department:
                output += f"• Department: {department}\n"
            output += "\n💡 This appears to be a novel role combination. You may need to design new compensating controls."
            return output

        # Format response
        output = f"💡 **Similar Approved Exceptions Found** ({len(similar)})\n\n"
        output += "**Searching for:**\n"
        output += f"• Roles: {', '.join(role_names)}\n"
        if job_title:
            output += f"• Job Title: {job_title}\n"
        if department:
            output += f"• Department: {department}\n"
        output += "\n---\n\n"

        for i, (exception, similarity) in enumerate(similar, 1):
            similarity_pct = similarity * 100
            emoji = "🟢" if similarity >= 0.9 else "🟡" if similarity >= 0.7 else "🟠"

            output += f"{emoji} **Match #{i}: {exception.exception_code}** ({similarity_pct:.0f}% similar)\n"
            output += f"**User:** {exception.user_name}\n"
            if exception.job_title:
                output += f"**Job Title:** {exception.job_title}\n"
            if exception.department:
                output += f"**Department:** {exception.department}\n"

            output += f"**Status:** {exception.status.value}\n"
            output += f"**Approved:** {exception.approved_date.strftime('%Y-%m-%d')}\n"
            output += f"**Risk Score:** {exception.risk_score:.1f}/100\n"

            output += f"\n**Roles ({len(exception.role_names)}):**\n"
            for role in exception.role_names:
                output += f"  • {role}\n"

            # Get controls
            controls = exception_repo.get_exception_controls(exception.exception_id)
            if controls:
                output += f"\n**Compensating Controls ({len(controls)}):**\n"
                total_cost = 0
                for control in controls:
                    output += f"  • Control (Risk Reduction: {control.risk_reduction_percentage or 0}%)\n"
                    if control.estimated_annual_cost:
                        total_cost += control.estimated_annual_cost

                if total_cost > 0:
                    output += f"  └─ **Total Annual Cost:** ${total_cost:,.0f}\n"

            output += "\n"

            if i == 1 and similarity >= 0.8:
                output += "✅ **Recommendation:** This exception is highly similar (≥80%). Consider using the same control framework.\n\n"

            output += "---\n\n"

        output += "💡 **Next Steps:**\n"
        output += "• Review controls from best match for reusability\n"
        output += "• Use `get_exception_details('<code>')` for full details\n"
        output += "• Adapt controls to your specific situation\n"

        return output

    except Exception as e:
        logger.error(f"Error in find_similar_exceptions_handler: {str(e)}", exc_info=True)
        return f"❌ Error finding similar exceptions: {str(e)}"


async def get_exception_details_handler(
    exception_code: str
) -> str:
    """
    Get complete details of a specific exception

    Returns:
        Full exception report including controls, violations, and reviews
    """
    try:
        logger.info(f"Getting exception details: {exception_code}")

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get exception by code
        exception = exception_repo.get_by_code(exception_code)

        if not exception:
            return f"❌ Exception not found: {exception_code}\n\nUse `list_approved_exceptions()` to see available exceptions."

        # Get related data
        controls = exception_repo.get_exception_controls(exception.exception_id)
        violations = exception_repo.get_exception_violations(exception.exception_id)
        reviews = exception_repo.get_exception_reviews(exception.exception_id)

        # Format response
        status_emoji = {
            "ACTIVE": "🟢",
            "VIOLATED": "🔴",
            "REMEDIATED": "🟡",
            "EXPIRED": "⚪",
            "REVOKED": "⛔"
        }

        output = f"""# {status_emoji.get(exception.status.value, '•')} Exception Details: {exception.exception_code}

**Status:** {exception.status.value}
**User:** {exception.user_name}
**Risk Score:** {exception.risk_score:.1f}/100

## Conflict Summary

• **Total Conflicts:** {exception.conflict_count}
• **Critical Conflicts:** {exception.critical_conflicts}
• **Approved Date:** {exception.approved_date.strftime('%Y-%m-%d')}
• **Approved By:** {exception.approved_by}"""

        if exception.approval_authority:
            output += f" ({exception.approval_authority})"

        if exception.expires_at:
            days_until_expiry = (exception.expires_at - datetime.utcnow()).days
            if days_until_expiry > 0:
                output += f"\n• **Expires In:** {days_until_expiry} days ({exception.expires_at.strftime('%Y-%m-%d')})"
            else:
                output += f"\n• **Status:** ⚠️ EXPIRED on {exception.expires_at.strftime('%Y-%m-%d')}"

        output += f"\n\n## Approved Role Combination ({len(exception.role_names)})\n\n"
        for i, role in enumerate(exception.role_names, 1):
            output += f"{i}. {role}\n"

        output += f"\n## Business Justification\n\n{exception.business_justification}\n"

        # Controls section
        if controls:
            output += f"\n## Compensating Controls ({len(controls)})\n\n"
            total_cost = 0
            total_prevented = 0
            total_occurred = 0

            for i, control in enumerate(controls, 1):
                output += f"**{i}. Control**\n"
                output += f"   • Status: {control.implementation_status.value}\n"
                if control.risk_reduction_percentage:
                    output += f"   • Risk Reduction: {control.risk_reduction_percentage}%\n"
                if control.estimated_annual_cost:
                    output += f"   • Estimated Cost: ${control.estimated_annual_cost:,.0f}/year\n"
                    total_cost += control.estimated_annual_cost
                if control.actual_annual_cost:
                    output += f"   • Actual Cost: ${control.actual_annual_cost:,.0f}/year\n"

                # Effectiveness
                prevented = control.violations_prevented or 0
                occurred = control.violations_occurred or 0
                total_prevented += prevented
                total_occurred += occurred

                if prevented + occurred > 0:
                    effectiveness = (prevented / (prevented + occurred)) * 100
                    output += f"   • Effectiveness: {effectiveness:.1f}% ({prevented} prevented, {occurred} occurred)\n"

                output += "\n"

            if total_cost > 0:
                output += f"**Total Annual Cost:** ${total_cost:,.0f}\n"

        else:
            output += "\n## Compensating Controls\n\n⚠️ No controls recorded\n"

        # Violations section
        if violations:
            output += f"\n## Violations ({len(violations)})\n\n"
            for i, violation in enumerate(violations, 1):
                severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}
                output += f"{severity_emoji.get(violation.severity, '•')} **{violation.violation_type}** ({violation.severity})\n"
                output += f"   • Date: {violation.detected_at.strftime('%Y-%m-%d %H:%M')}\n"
                output += f"   • Description: {violation.description}\n"
                if violation.failure_reason:
                    output += f"   • Failure Reason: {violation.failure_reason}\n"
                output += f"   • Remediation: {violation.remediation_status.value}\n"
                output += "\n"
        else:
            output += "\n## Violations\n\n✅ No violations recorded\n"

        # Reviews section
        if reviews:
            output += f"\n## Review History ({len(reviews)})\n\n"
            for i, review in enumerate(reviews, 1):
                outcome_emoji = {
                    "APPROVED_CONTINUE": "✅",
                    "APPROVED_MODIFY": "🔄",
                    "REVOKED": "⛔",
                    "ESCALATED": "⬆️"
                }
                output += f"{outcome_emoji.get(review.outcome.value, '•')} **Review #{i}**\n"
                output += f"   • Date: {review.review_date.strftime('%Y-%m-%d')}\n"
                output += f"   • Reviewer: {review.reviewer_name}\n"
                output += f"   • Outcome: {review.outcome.value}\n"
                if review.findings:
                    output += f"   • Findings: {review.findings}\n"
                output += "\n"

        # Next review
        if exception.next_review_date:
            days_until_review = (exception.next_review_date - datetime.utcnow()).days
            if days_until_review > 0:
                output += f"\n**Next Review:** {exception.next_review_date.strftime('%Y-%m-%d')} ({days_until_review} days)\n"
            else:
                output += f"\n⚠️ **Review Overdue:** {exception.next_review_date.strftime('%Y-%m-%d')}\n"

        return output

    except Exception as e:
        logger.error(f"Error in get_exception_details_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting exception details: {str(e)}"


async def list_approved_exceptions_handler(
    status: str = None,
    user_identifier: str = None,
    limit: int = 10,
    offset: int = 0
) -> str:
    """
    List approved exceptions with filters

    Returns:
        Paginated list of exceptions
    """
    try:
        logger.info(f"Listing exceptions: status={status}, user={user_identifier}, limit={limit}")

        from models.approved_exception import ExceptionStatus
        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository
        from repositories.user_repository import UserRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get user UUID if user_identifier provided
        user_id = None
        if user_identifier:
            user_repo = UserRepository(session)
            user = user_repo.get_user_by_email(user_identifier)
            if not user:
                user = user_repo.get_user_by_id(user_identifier)
            if user:
                user_id = user.id

        # Convert status string to enum if provided
        status_enum = None
        if status:
            status_enum = ExceptionStatus[status]

        # Get exceptions
        if user_id:
            exceptions = exception_repo.get_by_user(user_id, status=status_enum)
            exceptions = exceptions[offset:offset+limit]  # Apply pagination
        else:
            exceptions = exception_repo.list_all(status=status_enum, limit=limit, offset=offset)

        # Get total counts
        counts = exception_repo.count_by_status()
        total = sum(counts.values())

        # Format response
        output = "📋 **Approved SOD Exceptions**\n\n"
        output += f"**Total:** {total} exceptions\n"

        if counts:
            output += "**By Status:**\n"
            for st, count in sorted(counts.items()):
                status_emoji = {
                    "ACTIVE": "🟢",
                    "VIOLATED": "🔴",
                    "REMEDIATED": "🟡",
                    "EXPIRED": "⚪",
                    "REVOKED": "⛔"
                }
                output += f"  • {status_emoji.get(st, '•')} {st}: {count}\n"

        output += "\n---\n\n"

        if not exceptions:
            filter_desc = []
            if status:
                filter_desc.append(f"status={status}")
            if user_identifier:
                filter_desc.append(f"user={user_identifier}")

            output += "No exceptions found"
            if filter_desc:
                output += f" with filters: {', '.join(filter_desc)}"
            return output

        output += f"**Showing {len(exceptions)} result(s)** (offset {offset})\n\n"

        for i, exception in enumerate(exceptions, offset + 1):
            status_emoji = {
                "ACTIVE": "🟢",
                "VIOLATED": "🔴",
                "REMEDIATED": "🟡",
                "EXPIRED": "⚪",
                "REVOKED": "⛔"
            }

            output += f"{status_emoji.get(exception.status.value, '•')} **{i}. {exception.exception_code}**\n"
            output += f"   • User: {exception.user_name}\n"
            if exception.job_title:
                output += f"   • Job Title: {exception.job_title}\n"
            output += f"   • Status: {exception.status.value}\n"
            output += f"   • Conflicts: {exception.conflict_count} ({exception.critical_conflicts} critical)\n"
            output += f"   • Risk Score: {exception.risk_score:.1f}/100\n"
            output += f"   • Roles: {len(exception.role_names)}\n"
            output += f"   • Approved: {exception.approved_date.strftime('%Y-%m-%d')}\n"

            # Get control count
            controls = exception_repo.get_exception_controls(exception.exception_id)
            if controls:
                output += f"   • Controls: {len(controls)}\n"

            output += "\n"

        if offset + limit < total:
            output += f"_Use offset={offset + limit} to see more results_\n"

        output += "\n💡 Use `get_exception_details('<code>')` for full details of any exception.\n"

        return output

    except Exception as e:
        logger.error(f"Error in list_approved_exceptions_handler: {str(e)}", exc_info=True)
        return f"❌ Error listing exceptions: {str(e)}"


async def record_exception_violation_handler(
    exception_code: str,
    violation_type: str,
    severity: str,
    description: str,
    failed_control_name: str,
    failure_reason: str = None,
    detected_by: str = "Automated Monitoring",
    detection_method: str = None
) -> str:
    """
    Record a violation of an approved exception

    Returns:
        Confirmation of violation recording and status update
    """
    try:
        logger.info(f"Recording violation for exception: {exception_code}")

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get exception
        exception = exception_repo.get_by_code(exception_code)
        if not exception:
            return f"❌ Exception not found: {exception_code}\n\nUse `list_approved_exceptions()` to see available exceptions."

        # Find the control that failed
        controls = exception_repo.get_exception_controls(exception.exception_id)
        failed_control_id = None
        for control in controls:
            # Match by control name (in MVP, we don't have control names stored directly)
            # This would be improved in production with proper control references
            failed_control_id = control.exception_control_id
            break

        # Record violation
        violation = exception_repo.record_violation(
            exception_id=exception.exception_id,
            violation_type=violation_type,
            severity=severity,
            description=description,
            failed_control_id=failed_control_id,
            failure_reason=failure_reason,
            detected_by=detected_by,
            detection_method=detection_method
        )

        # Check if violation was recorded successfully
        if not violation:
            return f"❌ Failed to record violation for {exception_code}\n\nCheck logs for details. The exception may have integrity constraints or the session failed to commit."

        session.commit()

        # Refresh exception to get updated status
        session.refresh(exception)

        # Format response
        severity_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵"
        }

        output = f"""{severity_emoji.get(severity, '⚠️')} **Exception Violation Recorded**

**Exception:** {exception.exception_code}
**User:** {exception.user_name}
**Violation Type:** {violation_type}
**Severity:** {severity}

**What Happened:**
{description}

**Failed Control:** {failed_control_name}
"""

        if failure_reason:
            output += f"**Why It Failed:** {failure_reason}\n"

        output += "\n**Detection:**\n"
        output += f"• Detected By: {detected_by}\n"
        if detection_method:
            output += f"• Detection Method: {detection_method}\n"
        output += f"• Detected At: {violation.detected_at.strftime('%Y-%m-%d %H:%M')}\n"

        output += f"\n**Exception Status Updated:** {exception.status.value}\n"

        output += "\n⚠️ **Action Required:**\n"
        output += "• Investigate root cause immediately\n"
        output += "• Review all controls for this exception\n"
        output += "• Consider temporary revocation if pattern continues\n"
        output += "• Document remediation actions\n"

        output += f"\n💡 Use `get_exception_details('{exception.exception_code}')` to see full violation history.\n"

        return output

    except Exception as e:
        logger.error(f"Error in record_exception_violation_handler: {str(e)}", exc_info=True)
        return f"❌ Error recording violation: {str(e)}"


async def get_exception_effectiveness_stats_handler() -> str:
    """
    Get exception effectiveness dashboard statistics

    Returns:
        Comprehensive dashboard with costs, effectiveness, and ROI
    """
    try:
        logger.info("Getting exception effectiveness statistics")

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get statistics
        stats = exception_repo.get_effectiveness_stats()

        # Format response
        output = f"""📊 **EXCEPTION EFFECTIVENESS DASHBOARD**

## Overview

• **Total Exceptions:** {stats['total_exceptions']}
• **Total Annual Cost:** ${stats['total_annual_cost']:,.0f}
• **Total Violations:** {stats['total_violations']}

## Status Breakdown

"""

        status_order = ['ACTIVE', 'VIOLATED', 'REMEDIATED', 'EXPIRED', 'REVOKED']
        status_emoji = {
            "ACTIVE": "✅",
            "VIOLATED": "❌",
            "REMEDIATED": "🔄",
            "EXPIRED": "⏱️",
            "REVOKED": "⛔"
        }

        for status in status_order:
            count = stats['by_status'].get(status, 0)
            if stats['total_exceptions'] > 0:
                pct = (count / stats['total_exceptions']) * 100
                output += f"{status_emoji.get(status, '•')} **{status}:** {count} ({pct:.1f}%)\n"

        # Get exceptions needing review
        needs_review = exception_repo.get_exceptions_needing_review()
        if needs_review:
            output += f"\n## ⚠️ Exceptions Needing Review ({len(needs_review)})\n\n"
            for exception in needs_review[:5]:  # Show top 5
                days_overdue = (datetime.utcnow() - exception.next_review_date).days if exception.next_review_date else 0
                output += f"• {exception.exception_code} ({exception.user_name})"
                if days_overdue > 0:
                    output += f" - {days_overdue} days overdue"
                output += "\n"

            if len(needs_review) > 5:
                output += f"_...and {len(needs_review) - 5} more_\n"

        output += "\n## Control Effectiveness\n\n"

        # Calculate overall effectiveness
        total_prevented = 0
        total_occurred = 0

        all_exceptions = exception_repo.list_all(limit=1000)  # Get all for analysis
        for exception in all_exceptions:
            controls = exception_repo.get_exception_controls(exception.exception_id)
            for control in controls:
                total_prevented += control.violations_prevented or 0
                total_occurred += control.violations_occurred or 0

        if total_prevented + total_occurred > 0:
            overall_effectiveness = (total_prevented / (total_prevented + total_occurred)) * 100
            output += f"• **Overall Effectiveness:** {overall_effectiveness:.1f}%\n"
            output += f"• **Violations Prevented:** {total_prevented}\n"
            output += f"• **Violations Occurred:** {total_occurred}\n"
        else:
            output += "_No effectiveness data available yet_\n"

        output += "\n## Recommendations\n\n"

        violated_count = stats['by_status'].get('VIOLATED', 0)
        if violated_count > 0:
            output += f"⚠️ **{violated_count} exception(s) currently violated** - immediate review required\n"

        if len(needs_review) > 0:
            output += f"⚠️ **{len(needs_review)} exception(s) overdue for review** - schedule reviews promptly\n"

        if stats['total_violations'] > stats['total_exceptions'] * 0.1:  # More than 10% violation rate
            output += "⚠️ **High violation rate detected** - consider strengthening controls or revoking problematic exceptions\n"

        if stats['total_annual_cost'] > 1000000:  # Over $1M
            output += "💡 Consider cost optimization - review high-cost exceptions for potential consolidation\n"

        if violated_count == 0 and len(needs_review) == 0 and stats['total_violations'] == 0:
            output += "✅ **All exceptions performing well** - continue monitoring\n"

        output += "\n---\n\n"
        output += "💡 Use `list_approved_exceptions(status='VIOLATED')` to see problematic exceptions\n"

        return output

    except Exception as e:
        logger.error(f"Error in get_exception_effectiveness_stats_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting effectiveness stats: {str(e)}"


# ============================================================================
# PHASE 3: VIOLATION DETECTION AND REVIEW MANAGEMENT
# ============================================================================

async def detect_exception_violations_handler(
    check_all: bool = True,
    exception_codes: list[str] = None,
    auto_record: bool = False
) -> str:
    """
    Automatically detect violations of approved exceptions

    Checks:
    1. Users with exceptions still have the approved role combination
    2. No new critical conflicts beyond what was approved
    3. Controls are still in place and effective

    Returns:
        Report of detected violations
    """
    try:
        logger.info(f"Detecting exception violations: check_all={check_all}, auto_record={auto_record}")

        from models.approved_exception import ExceptionStatus
        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository
        from repositories.user_repository import UserRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)
        user_repo = UserRepository(session)

        # Get exceptions to check
        if exception_codes:
            exceptions = [exception_repo.get_by_code(code) for code in exception_codes]
            exceptions = [e for e in exceptions if e]  # Filter out None
        elif check_all:
            exceptions = exception_repo.list_all(status=ExceptionStatus.ACTIVE, limit=1000)
        else:
            return "❌ Must specify either check_all=true or provide exception_codes"

        if not exceptions:
            return "✅ No active exceptions to check"

        # Analyze each exception for violations
        violations_detected = []
        clean_exceptions = []

        for exception in exceptions:
            # Get current user info
            user = user_repo.get_user_by_uuid(str(exception.user_id))
            if not user:
                violations_detected.append({
                    'exception': exception,
                    'violation_type': 'User Not Found',
                    'severity': 'CRITICAL',
                    'description': f'User {exception.user_name} no longer exists in system'
                })
                continue

            # Get user's current roles
            current_roles = user_repo.get_user_roles(str(user.id))
            current_role_ids = [role.id for role in current_roles]
            current_role_ids_set = set(current_role_ids)
            approved_role_ids_set = set(exception.role_ids)

            # Check 1: User still has the approved role combination
            if not approved_role_ids_set.issubset(current_role_ids_set):
                missing_roles = approved_role_ids_set - current_role_ids_set
                violations_detected.append({
                    'exception': exception,
                    'violation_type': 'Unapproved Role Change',
                    'severity': 'HIGH',
                    'description': f'User no longer has all approved roles. Missing {len(missing_roles)} role(s). Exception should be closed.'
                })
                continue

            # Check 2: User hasn't gained additional high-risk roles
            additional_roles = current_role_ids_set - approved_role_ids_set
            if additional_roles:
                violations_detected.append({
                    'exception': exception,
                    'violation_type': 'Unauthorized Role Addition',
                    'severity': 'MEDIUM',
                    'description': f'User gained {len(additional_roles)} additional role(s) beyond exception approval. May create new conflicts.'
                })

            # Check 3: Controls are still implemented
            controls = exception_repo.get_exception_controls(exception.exception_id)
            inactive_controls = [c for c in controls if c.implementation_status.value != 'ACTIVE']

            if inactive_controls:
                violations_detected.append({
                    'exception': exception,
                    'violation_type': 'Control Not Active',
                    'severity': 'CRITICAL',
                    'description': f'{len(inactive_controls)} compensating control(s) not in ACTIVE status'
                })

            # If no violations found, mark as clean
            if not any(v['exception'].exception_id == exception.exception_id for v in violations_detected):
                clean_exceptions.append(exception)

        # Format output
        output = f"""🔍 **Exception Violation Detection Report**

**Scope:** {len(exceptions)} active exception(s) checked

**Results:**
• ✅ Clean: {len(clean_exceptions)}
• ⚠️ Violations Detected: {len(violations_detected)}

"""

        if violations_detected:
            output += f"## Violations Detected ({len(violations_detected)})\n\n"

            for i, violation in enumerate(violations_detected, 1):
                exc = violation['exception']
                severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🔵"}

                output += f"{severity_emoji.get(violation['severity'], '⚠️')} **{i}. {exc.exception_code}** - {violation['violation_type']}\n"
                output += f"   • User: {exc.user_name}\n"
                output += f"   • Severity: {violation['severity']}\n"
                output += f"   • Issue: {violation['description']}\n"
                output += "\n"

                # Auto-record if requested
                if auto_record:
                    recorded = exception_repo.record_violation(
                        exception_id=exc.exception_id,
                        violation_type=violation['violation_type'],
                        severity=violation['severity'],
                        description=violation['description'],
                        detected_by="Automated Violation Detection",
                        detection_method="Periodic exception compliance scan"
                    )

                    if recorded:
                        output += "   ✅ Violation auto-recorded\n\n"
                        session.commit()
                    else:
                        output += "   ❌ Failed to auto-record\n\n"

            if not auto_record:
                output += "\n💡 **Tip:** Run with `auto_record=true` to automatically record these violations\n"

        else:
            output += "✅ **All exceptions compliant** - No violations detected\n"

        if clean_exceptions:
            output += f"\n## Clean Exceptions ({len(clean_exceptions)})\n\n"
            for exc in clean_exceptions[:5]:  # Show first 5
                output += f"✅ {exc.exception_code} - {exc.user_name}\n"

            if len(clean_exceptions) > 5:
                output += f"_...and {len(clean_exceptions) - 5} more_\n"

        output += "\n---\n\n"
        output += "**Checks Performed:**\n"
        output += "1. ✓ User still has approved role combination\n"
        output += "2. ✓ No unauthorized additional roles\n"
        output += "3. ✓ All compensating controls still active\n"

        return output

    except Exception as e:
        logger.error(f"Error in detect_exception_violations_handler: {str(e)}", exc_info=True)
        return f"❌ Error detecting violations: {str(e)}"


async def conduct_exception_review_handler(
    exception_code: str,
    reviewer_name: str,
    outcome: str,
    findings: str = None,
    recommendations: str = None,
    control_modifications: list[dict[str, str]] = None
) -> str:
    """
    Conduct a periodic review of an approved exception

    Returns:
        Review confirmation and next steps
    """
    try:
        logger.info(f"Conducting review for exception: {exception_code}")

        from dateutil.relativedelta import relativedelta

        from models.approved_exception import ExceptionStatus, ReviewOutcome
        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get exception
        exception = exception_repo.get_by_code(exception_code)
        if not exception:
            return f"❌ Exception not found: {exception_code}"

        # Convert outcome string to enum
        outcome_enum = ReviewOutcome[outcome]

        # Create review record
        exception_repo.create_review(
            exception_id=exception.exception_id,
            reviewer_name=reviewer_name,
            outcome=outcome_enum,
            findings=findings,
            recommendations=recommendations,
            control_modifications=control_modifications
        )

        # Update exception based on outcome
        if outcome_enum == ReviewOutcome.REVOKED:
            exception_repo.update_status(
                exception.exception_id,
                ExceptionStatus.REVOKED,
                f"Revoked during {datetime.utcnow().strftime('%Y-%m-%d')} review"
            )
            next_review_date = None

        elif outcome_enum == ReviewOutcome.APPROVED_CONTINUE or outcome_enum == ReviewOutcome.APPROVED_MODIFY:
            # Schedule next review based on frequency
            frequency_map = {
                "Monthly": relativedelta(months=1),
                "Quarterly": relativedelta(months=3),
                "Annually": relativedelta(years=1)
            }

            delta = frequency_map.get(exception.review_frequency, relativedelta(months=3))
            next_review_date = datetime.utcnow() + delta
            exception.next_review_date = next_review_date
            exception.last_review_date = datetime.utcnow().date()

        elif outcome_enum == ReviewOutcome.ESCALATED:
            # Keep current schedule, add escalation note
            next_review_date = exception.next_review_date

        session.commit()

        # Format response
        outcome_emoji = {
            "APPROVED_CONTINUE": "✅",
            "APPROVED_MODIFY": "🔄",
            "REVOKED": "⛔",
            "ESCALATED": "⬆️"
        }

        output = f"""{outcome_emoji.get(outcome, '📋')} **Exception Review Completed**

**Exception:** {exception.exception_code}
**User:** {exception.user_name}
**Reviewer:** {reviewer_name}
**Review Date:** {datetime.utcnow().strftime('%Y-%m-%d')}
**Outcome:** {outcome}

"""

        if findings:
            output += f"**Findings:**\n{findings}\n\n"

        if recommendations:
            output += f"**Recommendations:**\n{recommendations}\n\n"

        if control_modifications:
            output += f"**Control Modifications ({len(control_modifications)}):**\n"
            for mod in control_modifications:
                output += f"• {mod.get('control_name', 'Unknown')}: {mod.get('modification', 'No details')}\n"
            output += "\n"

        # Next steps based on outcome
        if outcome_enum == ReviewOutcome.REVOKED:
            output += "**Status:** Exception REVOKED\n"
            output += "\n⚠️ **Action Required:**\n"
            output += "• Remove conflicting roles from user immediately\n"
            output += "• Notify user and manager\n"
            output += "• Update access control systems\n"
            output += "• Document reason for revocation\n"

        elif outcome_enum == ReviewOutcome.APPROVED_CONTINUE:
            output += f"**Next Review:** {next_review_date.strftime('%Y-%m-%d')} ({exception.review_frequency})\n"
            output += "\n✅ **Status:** Exception continues with current controls\n"

        elif outcome_enum == ReviewOutcome.APPROVED_MODIFY:
            output += f"**Next Review:** {next_review_date.strftime('%Y-%m-%d')} ({exception.review_frequency})\n"
            output += "\n🔄 **Action Required:**\n"
            output += "• Implement control modifications as specified\n"
            output += "• Update control status once implemented\n"
            output += "• Notify affected stakeholders\n"

        elif outcome_enum == ReviewOutcome.ESCALATED:
            output += "\n⬆️ **Escalated for Higher Authority Review**\n"
            output += "• Route to CFO/Audit Committee\n"
            output += "• Provide full context and recommendations\n"
            output += "• Await decision before next scheduled review\n"

        output += f"\n💡 Use `get_exception_details('{exception_code}')` to see full review history.\n"

        return output

    except Exception as e:
        logger.error(f"Error in conduct_exception_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error conducting review: {str(e)}"


async def get_exceptions_for_review_handler(
    include_upcoming: bool = True,
    days_ahead: int = 30
) -> str:
    """
    Get list of exceptions due or overdue for review

    Returns:
        List of exceptions needing review attention
    """
    try:
        logger.info(f"Getting exceptions for review: upcoming={include_upcoming}, days={days_ahead}")

        from models.database_config import DatabaseConfig
        from repositories.exception_repository import ExceptionRepository

        db_config = DatabaseConfig()
        session = db_config.get_session()

        exception_repo = ExceptionRepository(session)

        # Get exceptions needing review
        exceptions = exception_repo.get_exceptions_needing_review()

        # Separate into overdue and upcoming
        overdue = []
        upcoming = []
        today = datetime.utcnow().date()
        future_date = today + timedelta(days=days_ahead)

        for exception in exceptions:
            if not exception.next_review_date:
                continue

            if exception.next_review_date < today:
                days_overdue = (today - exception.next_review_date).days
                overdue.append((exception, days_overdue))
            elif include_upcoming and exception.next_review_date <= future_date:
                days_until = (exception.next_review_date - today).days
                upcoming.append((exception, days_until))

        # Format output
        output = f"""📅 **Exceptions Requiring Review**

**Summary:**
• 🔴 Overdue: {len(overdue)}
• 🟡 Upcoming ({days_ahead} days): {len(upcoming)}

"""

        if overdue:
            output += f"## 🔴 Overdue Reviews ({len(overdue)})\n\n"

            # Sort by most overdue first
            overdue.sort(key=lambda x: x[1], reverse=True)

            for exception, days_overdue in overdue:
                output += f"**{exception.exception_code}** - {exception.user_name}\n"
                output += f"   • Due Date: {exception.next_review_date}\n"
                output += f"   • **{days_overdue} days overdue** ⚠️\n"
                output += f"   • Frequency: {exception.review_frequency}\n"
                output += f"   • Risk Score: {exception.risk_score:.1f}/100\n"

                # Get control count
                controls = exception_repo.get_exception_controls(exception.exception_id)
                output += f"   • Controls: {len(controls)}\n"

                # Check for violations
                violations = exception_repo.get_exception_violations(exception.exception_id)
                if violations:
                    output += f"   • ⚠️ {len(violations)} violation(s) recorded\n"

                output += "\n"

            output += "⚠️ **Action Required:** Schedule reviews immediately for overdue exceptions\n\n"

        if upcoming:
            output += f"## 🟡 Upcoming Reviews (Next {days_ahead} Days)\n\n"

            # Sort by soonest first
            upcoming.sort(key=lambda x: x[1])

            for exception, days_until in upcoming[:10]:  # Show first 10
                output += f"**{exception.exception_code}** - {exception.user_name}\n"
                output += f"   • Due Date: {exception.next_review_date}\n"
                output += f"   • In {days_until} day(s)\n"
                output += f"   • Frequency: {exception.review_frequency}\n"
                output += "\n"

            if len(upcoming) > 10:
                output += f"_...and {len(upcoming) - 10} more_\n\n"

            output += "💡 **Tip:** Schedule review sessions for upcoming exceptions\n\n"

        if not overdue and not upcoming:
            output += f"✅ **All reviews current** - No overdue or upcoming reviews in the next {days_ahead} days\n\n"

        output += "---\n\n"
        output += "**To conduct a review:**\n"
        output += "```\n"
        output += "conduct_exception_review(\n"
        output += "  exception_code='EXC-2026-001',\n"
        output += "  reviewer_name='Your Name',\n"
        output += "  outcome='APPROVED_CONTINUE',  # or APPROVED_MODIFY, REVOKED, ESCALATED\n"
        output += "  findings='Review findings...',\n"
        output += "  recommendations='Recommendations...'\n"
        output += ")\n"
        output += "```\n"

        return output

    except Exception as e:
        logger.error(f"Error in get_exceptions_for_review_handler: {str(e)}", exc_info=True)
        return f"❌ Error getting exceptions for review: {str(e)}"


# ============================================================================
# PHASE 4: RBAC AND APPROVAL WORKFLOWS
# ============================================================================

async def initialize_session_handler(my_email: str) -> str:
    """
    Initialize session and provide personalized welcome with approval authority

    Returns:
        Friendly welcome message with user's permissions and what they can do
    """
    try:
        logger.info(f"Initializing session for: {my_email}")

        from models.database_config import DatabaseConfig
        from services.approval_service import ApprovalService

        db_config = DatabaseConfig()
        session = db_config.get_session()

        approval_service = ApprovalService(session)

        # Authenticate user
        user_info = approval_service.authenticate_user(my_email)

        if not user_info:
            return f"""❌ **Authentication Failed**

Unable to find user: {my_email}

Please ensure you're using your corporate email address.
Contact your administrator if you need access.
"""

        # Check authority for each level
        can_approve_low = approval_service.check_approval_authority(my_email, 30)[0]
        can_approve_medium = approval_service.check_approval_authority(my_email, 50)[0]
        can_approve_high = approval_service.check_approval_authority(my_email, 70)[0]
        can_approve_critical = approval_service.check_approval_authority(my_email, 85)[0]

        # Determine highest approval level
        approval_level = "NONE"
        if can_approve_critical:
            approval_level = "CRITICAL (All Levels)"
        elif can_approve_high:
            approval_level = "HIGH (+ MEDIUM/LOW)"
        elif can_approve_medium:
            approval_level = "MEDIUM (+ LOW)"
        elif can_approve_low:
            approval_level = "LOW Only"

        # Create welcome message
        output = f"""╔{'═'*78}╗
║{' '*20}🎯 COMPLIANCE SESSION INITIALIZED{' '*25}║
╚{'═'*78}╝

👤 **Welcome, {user_info['name']}!**

**Your Profile:**
• Email: {user_info['email']}
• Job Title: {user_info.get('job_title') or 'N/A'}
• Department: {user_info.get('department') or 'N/A'}
• Roles: {len(user_info['roles'])} NetSuite role(s)

**Your Approval Authority:** {'✅ ' + approval_level if approval_level != 'NONE' else '❌ No Approval Authority'}

"""

        if approval_level != "NONE":
            output += """**What You Can Do:**
"""
            if can_approve_low:
                output += "✅ Approve LOW risk exceptions (score < 40)\n"
            if can_approve_medium:
                output += "✅ Approve MEDIUM risk exceptions (score 40-59)\n"
            if can_approve_high:
                output += "✅ Approve HIGH risk exceptions (score 60-74)\n"
            if can_approve_critical:
                output += "✅ Approve CRITICAL risk exceptions (score ≥75)\n"

            output += """
**Available Actions:**
• Use `request_exception_approval` to approve exceptions with RBAC validation
• Use `record_exception_approval` to directly record pre-approved exceptions
• Use `list_approved_exceptions` to see existing exceptions
• Use `conduct_exception_review` to review periodic exceptions

"""
        else:
            output += """**Your Access:**
❌ You do not have approval authority for SOD exceptions

**What You Can Do:**
• Use `request_exception_approval` to submit requests (will escalate to authorized approver)
• Use `list_approved_exceptions` to view existing exceptions
• Use `get_user_violations` to check your own or others' SOD violations
• Use `analyze_access_request` to analyze potential role assignments

**To Get Approval:**
All exception requests from you will be automatically routed to an authorized approver
(typically CFO, Controller, or Director depending on risk level).

"""

        # Show key roles
        if user_info['roles']:
            output += "**Your NetSuite Roles:**\n"
            for i, role in enumerate(user_info['roles'][:5], 1):
                output += f"{i}. {role}\n"
            if len(user_info['roles']) > 5:
                output += f"... and {len(user_info['roles']) - 5} more\n"

        output += f"""
{'─'*80}
💡 **Tip:** Use `check_my_approval_authority` for detailed approval authority matrix
"""

        return output

    except Exception as e:
        logger.error(f"Error in initialize_session_handler: {str(e)}", exc_info=True)
        return f"❌ Error initializing session: {str(e)}"


async def check_my_approval_authority_handler(
    my_email: str,
    check_for_risk_score: float = None
) -> str:
    """
    Check user's approval authority based on their NetSuite roles

    Returns:
        Authority matrix and roles
    """
    try:
        logger.info(f"Checking approval authority for: {my_email}")

        from models.database_config import DatabaseConfig
        from services.approval_service import ApprovalService

        db_config = DatabaseConfig()
        session = db_config.get_session()

        approval_service = ApprovalService(session)

        # Authenticate user
        user_info = approval_service.authenticate_user(my_email)

        if not user_info:
            return f"❌ User not found or inactive: {my_email}\n\nPlease ensure you're using your corporate email address."

        # Format response
        output = f"""👤 **Approval Authority Check**

**User:** {user_info['name']}
**Email:** {user_info['email']}
**Status:** {user_info['status']}
**Job Title:** {user_info.get('job_title', 'N/A')}
**Department:** {user_info.get('department', 'N/A')}

**NetSuite Roles ({len(user_info['roles'])}):**
"""

        if user_info['roles']:
            for role in user_info['roles']:
                output += f"• {role}\n"
        else:
            output += "• No roles assigned\n"

        output += "\n**Approval Authority Matrix:**\n\n"

        # Check authority for each risk level
        risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        risk_scores = {"LOW": 30, "MEDIUM": 50, "HIGH": 70, "CRITICAL": 85}

        for level in risk_levels:
            score = risk_scores[level]
            has_authority, _, reason = approval_service.check_approval_authority(
                my_email,
                score
            )

            emoji = "✅" if has_authority else "❌"
            output += f"{emoji} **{level}** (Risk Score < {score + 15}): "

            if has_authority:
                output += "Can Approve\n"
            else:
                output += "Cannot Approve\n"

            # Show required roles
            required_roles = approval_service.get_required_approval_roles(score)
            output += f"   • Required: {', '.join(required_roles[:2])}{'...' if len(required_roles) > 2 else ''}\n"

        # If specific risk score provided, check that
        if check_for_risk_score is not None:
            output += f"\n---\n\n**Specific Check (Risk Score {check_for_risk_score}):**\n"

            has_authority, risk_level, reason = approval_service.check_approval_authority(
                my_email,
                check_for_risk_score
            )

            if has_authority:
                output += f"✅ **Authorized** to approve {risk_level} risk exceptions\n"
            else:
                output += f"❌ **Not Authorized** to approve {risk_level} risk exceptions\n\n"
                output += f"**Reason:** {reason}\n\n"

                # Find who can approve
                approver = approval_service.find_approver_in_chain(my_email, check_for_risk_score)
                if approver:
                    output += "**Escalation Path:**\n"
                    output += f"• Will route to: {approver['name']} ({approver['email']})\n"
                    output += f"• Levels Up: {approver['levels_up']}\n"
                    output += "• Jira ticket will be auto-created\n"

        output += "\n💡 **Usage:**\n"
        output += "• If authorized: Use `record_exception_approval` to approve directly\n"
        output += "• If not authorized: Use `request_exception_approval` to escalate via Jira\n"

        return output

    except Exception as e:
        logger.error(f"Error in check_my_approval_authority_handler: {str(e)}", exc_info=True)
        return f"❌ Error checking approval authority: {str(e)}"


async def request_exception_approval_handler(
    requester_email: str,
    user_identifier: str,
    user_name: str,
    role_names: list[str],
    conflict_count: int,
    risk_score: float,
    business_justification: str,
    job_title: str = None,
    department: str = None,
    critical_conflicts: int = 0,
    compensating_controls: list[dict[str, Any]] = None,
    review_frequency: str = "Quarterly",
    auto_approve_if_authorized: bool = False
) -> str:
    """
    Request exception approval with RBAC validation and automatic routing

    Returns:
        Approval result or escalation confirmation
    """
    try:
        logger.info(f"Processing approval request from: {requester_email}")

        from models.database_config import DatabaseConfig
        from services.approval_service import ApprovalService

        db_config = DatabaseConfig()
        session = db_config.get_session()

        approval_service = ApprovalService(session)

        # Prepare exception details
        exception_details = {
            "user_identifier": user_identifier,
            "user_name": user_name,
            "user_email": user_identifier if "@" in user_identifier else None,
            "role_names": role_names,
            "conflict_count": conflict_count,
            "critical_conflicts": critical_conflicts,
            "high_conflicts": 0,  # Could be passed as parameter
            "medium_conflicts": 0,
            "low_conflicts": 0,
            "risk_score": risk_score,
            "business_justification": business_justification,
            "job_title": job_title,
            "department": department,
            "compensating_controls": compensating_controls or [],
            "review_frequency": review_frequency
        }

        # Process approval request with RBAC
        result = approval_service.process_approval_request(
            requester_email,
            exception_details
        )

        # Check if authentication failed
        if result is None:
            return f"""❌ **Authentication Failed**

Unable to authenticate user: {requester_email}

**Possible Issues:**
• Email address not found in system
• User account is not active
• User does not have NetSuite access

**Next Steps:**
• Verify email address is correct
• Ensure user has an active NetSuite account
• Contact system administrator if issue persists
"""

        # Format response based on outcome
        if result['approved']:
            # User is authorized
            output = f"""✅ **Approval Authority Confirmed**

{result['message']}

**Exception Details:**
• User: {user_name} ({user_identifier})
• Roles: {len(role_names)}
• Conflicts: {conflict_count} ({critical_conflicts} critical)
• Risk Score: {risk_score:.1f}/100
• Risk Level: {result['risk_level']}
"""

            if auto_approve_if_authorized:
                # Auto-approve and record exception
                output += "\n🔄 **Auto-Approving Exception...**\n\n"

                # Call record_exception_approval
                approval_result = await record_exception_approval_handler(
                    user_identifier=user_identifier,
                    user_name=user_name,
                    role_names=role_names,
                    conflict_count=conflict_count,
                    critical_conflicts=critical_conflicts,
                    risk_score=risk_score,
                    business_justification=business_justification,
                    approved_by=result['approver']['name'],
                    approval_authority=result['approver'].get('job_title', 'Authorized Approver'),
                    job_title=job_title,
                    department=department,
                    compensating_controls=compensating_controls,
                    review_frequency=review_frequency
                )

                output += approval_result

            else:
                output += "\n💡 **Next Steps:**\n"
                output += "• Use `record_exception_approval` to formally record this exception\n"
                output += f"• Include your name ({result['approver']['name']}) as approved_by\n"
                output += f"• Reference your authority level: {result['risk_level']} approval rights\n"

        else:
            # User is NOT authorized - escalation needed
            output = f"""⚠️ **Approval Escalation Required**

{result['message']}

**Exception Request Details:**
• Requester: {requester_email}
• User: {user_name} ({user_identifier})
• Roles: {len(role_names)} - {', '.join(role_names[:2])}{'...' if len(role_names) > 2 else ''}
• Conflicts: {conflict_count} ({critical_conflicts} critical)
• Risk Score: {risk_score:.1f}/100
• Risk Level: {result['risk_level']}

"""

            if result['approver']:
                output += "**Approval Routed To:**\n"
                output += f"• Name: {result['approver']['name']}\n"
                output += f"• Email: {result['approver']['email']}\n"
                output += f"• Job Title: {result['approver'].get('job_title', 'N/A')}\n"
                output += f"• Relationship: {result['approver']['levels_up']} level(s) up in reporting chain\n\n"

            if result['jira_ticket']:
                output += "**Jira Ticket Created:**\n"
                output += f"• Ticket: {result['jira_ticket']}\n"
                output += f"• Assigned to: {result['approver']['name']}\n"
                output += f"• Priority: {approval_service._get_jira_priority(risk_score)}\n\n"

                output += "**Next Steps:**\n"
                output += f"1. Approver ({result['approver']['name']}) will review Jira ticket\n"
                output += "2. Once approved, use `record_exception_approval` with approver's name\n"
                output += f"3. Link Jira ticket: `ticket_reference='{result['jira_ticket']}'`\n"

            else:
                output += "**Jira Integration:**\n"
                output += "• Jira not configured (no ticket created)\n"
                if result.get('approver'):
                    output += f"• Please contact {result['approver']['name']} directly\n"
                output += "• Manual approval required before recording exception\n"

        output += f"\n**Business Justification:**\n{business_justification}\n"

        if compensating_controls:
            output += f"\n**Proposed Compensating Controls ({len(compensating_controls)}):**\n"
            for i, control in enumerate(compensating_controls, 1):
                output += f"{i}. {control.get('control_name')}\n"
                output += f"   • Risk Reduction: {control.get('risk_reduction_percentage', 0)}%\n"
                output += f"   • Annual Cost: ${control.get('estimated_annual_cost', 0):,.0f}\n"

        return output

    except Exception as e:
        logger.error(f"Error in request_exception_approval_handler: {str(e)}", exc_info=True)
        return f"❌ Error processing approval request: {str(e)}"


async def generate_violation_report_handler(
    user_email: str,
    format: str = "markdown",
    limit: int = 5,
    export_path: str | None = None
) -> str:
    """
    Generate a detailed violation report for a user

    Args:
        user_email: User's email address
        format: Report format (markdown, detailed, excel, csv)
        limit: Number of violations to show in console (for markdown/detailed)
        export_path: Optional path for Excel/CSV export

    Returns:
        Formatted violation report or export confirmation
    """
    try:
        from services.violation_report_service import ViolationReportService

        logger.info(f"Generating violation report for {user_email} in {format} format")

        # Get orchestrator
        orchestrator = get_orchestrator()

        # Get user from database
        user = orchestrator.user_repo.get_user_by_email(user_email)
        if not user:
            return f"❌ User not found: {user_email}"

        # Get all violations for the user
        violations = orchestrator.violation_repo.get_violations_by_user(
            user.id,
            status=None  # Get all violations regardless of status
        )

        if not violations:
            return f"✅ No violations found for {user.name} ({user_email})"

        # Convert violations to dictionaries
        violation_dicts = []
        for v in violations:
            violation_dicts.append({
                'id': str(v.id),
                'title': v.title,
                'severity': v.severity.value if hasattr(v.severity, 'value') else str(v.severity),
                'status': v.status.value if hasattr(v.status, 'value') else str(v.status),
                'risk_score': v.risk_score,
                'conflicting_roles': v.conflicting_roles,
                'conflicting_permissions': v.conflicting_permissions,
                'description': v.description,
                'detected_at': str(v.detected_at) if v.detected_at else None
            })

        # Initialize report service
        report_service = ViolationReportService()

        # Generate report based on format
        if format.lower() == "markdown":
            output = f"**SOD Violation Report: {user.name}**\n\n"
            output += f"📧 Email: {user_email}\n"
            output += f"🏢 Department: {user.department or 'N/A'}\n"
            output += f"📊 Total Violations: {len(violation_dicts)}\n\n"

            # Count by severity
            severity_counts = {}
            for v in violation_dicts:
                sev = v.get('severity', 'UNKNOWN')
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            output += "**Severity Breakdown:**\n"
            if severity_counts.get('CRITICAL', 0) > 0:
                output += f"🔴 CRITICAL: {severity_counts['CRITICAL']}\n"
            if severity_counts.get('HIGH', 0) > 0:
                output += f"🟠 HIGH: {severity_counts['HIGH']}\n"
            if severity_counts.get('MEDIUM', 0) > 0:
                output += f"🟡 MEDIUM: {severity_counts['MEDIUM']}\n"
            if severity_counts.get('LOW', 0) > 0:
                output += f"🟢 LOW: {severity_counts['LOW']}\n"

            output += "\n"
            output += report_service.generate_markdown_table(violation_dicts, limit=limit)

            # Add export suggestion for large lists
            if len(violation_dicts) > 10:
                output += f"\n\n💡 **Tip:** For {len(violation_dicts)} violations, consider exporting to Excel:\n"
                output += "   Use format='excel' and export_path='/path/to/file.xlsx'\n"

            return output

        elif format.lower() == "detailed":
            output = f"**SOD Violation Report: {user.name}**\n\n"
            output += f"📧 Email: {user_email}\n"
            output += f"📊 Total Violations: {len(violation_dicts)}\n\n"
            output += report_service.generate_detailed_table(violation_dicts, limit=limit)
            return output

        elif format.lower() == "excel":
            if not export_path:
                # Generate default path
                from pathlib import Path
                output_dir = Path("/tmp/compliance_reports")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = str(output_dir / f"violations_{user.name.replace(' ', '_')}_{timestamp}.xlsx")

            result = report_service.export_to_excel(
                violation_dicts,
                export_path,
                user_name=user.name
            )
            return result

        elif format.lower() == "csv":
            if not export_path:
                # Generate default path
                from pathlib import Path
                output_dir = Path("/tmp/compliance_reports")
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = str(output_dir / f"violations_{user.name.replace(' ', '_')}_{timestamp}.csv")

            result = report_service.export_to_csv(violation_dicts, export_path)
            return result

        else:
            return f"❌ Unknown format: {format}. Supported: markdown, detailed, excel, csv"

    except Exception as e:
        logger.error(f"Error in generate_violation_report_handler: {str(e)}", exc_info=True)
        return f"❌ Error generating violation report: {str(e)}"


async def list_violations_handler(
    department: str | None = None,
    severity: str | None = None,
    status: str = "OPEN",
    roles_only: bool = False,
    limit: int = 25
) -> str:
    """
    List SOD violations filtered by department and/or severity.

    roles_only=False  — returns per-user rows (name, email, roles, conflict)
    roles_only=True   — returns unique role-pair patterns with affected user
                        counts only; no names or emails ever appear.
    """
    try:
        from models.database_config import DatabaseConfig

        logger.info(
            f"list_violations: department={department!r} severity={severity!r} "
            f"status={status!r} roles_only={roles_only} limit={limit}"
        )

        db_config = DatabaseConfig()
        session = db_config.get_session()

        # ── Shared WHERE clause fragments ──────────────────────────────────────
        params: dict = {"limit": limit}

        severity_filter = ""
        if severity:
            severity_filter = "AND v.severity = :severity"
            params["severity"] = severity.upper()

        department_filter = ""
        if department:
            department_filter = "AND u.department ILIKE :department"
            params["department"] = f"%{department}%"

        status_filter = "AND v.status != 'RESOLVED'"
        if status and status.upper() != "OPEN":
            status_filter = "AND v.status = :status"
            params["status"] = status.upper()

        dept_label = f" — {department}" if department else ""
        sev_label  = f" [{severity}]" if severity else ""

        # ── MODE A: roles_only — aggregate by rule, no user names ─────────────
        if roles_only:
            sql = text(f"""
                SELECT
                    v.severity,
                    v.title                             AS rule_title,
                    v.conflicting_roles::text           AS roles_json,
                    v.conflicting_permissions::text     AS perms_json,
                    MAX(v.risk_score)                   AS max_risk,
                    COUNT(DISTINCT v.user_id)           AS affected_count
                FROM violations v
                JOIN users u ON u.id = v.user_id
                WHERE 1=1
                  {severity_filter}
                  {department_filter}
                  {status_filter}
                GROUP BY v.severity, v.title, v.conflicting_roles::text, v.conflicting_permissions::text
                ORDER BY
                    CASE v.severity
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH'     THEN 2
                        WHEN 'MEDIUM'   THEN 3
                        WHEN 'LOW'      THEN 4
                        ELSE 5
                    END,
                    MAX(v.risk_score) DESC
                LIMIT :limit
            """)

            rows = session.execute(sql, params).fetchall()

            if not rows:
                filter_str = ", ".join(
                    x for x in [department and f"department={department!r}", severity and f"severity={severity!r}"] if x
                ) or "no filters"
                return f"No role conflicts found ({filter_str})."

            # Deduplicate role pairs that differ only in array order
            import json as _json
            seen_pairs: set = set()
            deduped = []
            for row in rows:
                try:
                    roles = _json.loads(row.roles_json) if row.roles_json else []
                except Exception:
                    roles = []
                key = (row.severity, row.rule_title, frozenset(roles))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    deduped.append((row, roles))

            by_sev: dict = {}
            for row, roles in deduped:
                sev = row.severity if isinstance(row.severity, str) else row.severity.value
                by_sev.setdefault(sev, []).append((row, roles))

            total = sum(len(v) for v in by_sev.values())
            output = f"*Conflicting role patterns{dept_label}{sev_label}* — {total} unique pattern(s)\n\n"

            severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            for sev in severity_order:
                group = by_sev.get(sev, [])
                if not group:
                    continue
                output += f"*{sev}* ({len(group)})\n"
                for row, roles in group:
                    try:
                        perms = _json.loads(row.perms_json) if row.perms_json else []
                    except Exception:
                        perms = []

                    if len(roles) >= 2:
                        role_str = " ↔ ".join(f"`{r}`" for r in roles[:2])
                        if len(roles) > 2:
                            role_str += f" (+ {len(roles) - 2} more)"
                    elif len(roles) == 1:
                        role_str = f"`{roles[0]}`"
                    else:
                        role_str = "—"

                    if len(perms) >= 2:
                        perm_str = f"{perms[0]} ↔ {perms[1]}"
                    elif len(perms) == 1:
                        perm_str = perms[0]
                    else:
                        perm_str = "—"

                    count = row.affected_count
                    user_note = f"{count} affected user" + ("s" if count != 1 else "")
                    output += (
                        f"• *{row.rule_title}*\n"
                        f"  Roles: {role_str}\n"
                        f"  Conflict: {perm_str}\n"
                        f"  {user_note}\n"
                    )
                output += "\n"

            return output.rstrip()

        # ── MODE B: per-user rows ──────────────────────────────────────────────
        # DISTINCT ON (u.id, v.rule_id) collapses scan-duplicate rows,
        # keeping the highest-risk instance per user+rule.
        sql = text(f"""
            SELECT *
            FROM (
                SELECT DISTINCT ON (u.id, v.rule_id)
                    u.name          AS user_name,
                    u.email         AS user_email,
                    u.department    AS department,
                    v.severity      AS severity,
                    v.status        AS status,
                    v.risk_score    AS risk_score,
                    v.title         AS title,
                    v.conflicting_roles        AS conflicting_roles,
                    v.conflicting_permissions  AS conflicting_permissions,
                    v.detected_at   AS detected_at
                FROM violations v
                JOIN users u ON u.id = v.user_id
                WHERE 1=1
                  {severity_filter}
                  {department_filter}
                  {status_filter}
                ORDER BY u.id, v.rule_id, v.risk_score DESC
            ) deduped
            ORDER BY
                CASE severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH'     THEN 2
                    WHEN 'MEDIUM'   THEN 3
                    WHEN 'LOW'      THEN 4
                    ELSE 5
                END,
                risk_score DESC
            LIMIT :limit
        """)

        rows = session.execute(sql, params).fetchall()

        if not rows:
            filter_str = ", ".join(
                x for x in [department and f"department={department!r}", severity and f"severity={severity!r}"] if x
            ) or "no filters"
            return f"No violations found ({filter_str})."

        by_severity: dict = {}
        for row in rows:
            sev = row.severity if isinstance(row.severity, str) else row.severity.value
            by_severity.setdefault(sev, []).append(row)

        output = f"*SOD Violations{dept_label}{sev_label}* — {len(rows)} result(s)\n\n"

        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for sev in severity_order:
            group = by_severity.get(sev, [])
            if not group:
                continue
            output += f"*{sev}* ({len(group)})\n"
            for row in group:
                roles = row.conflicting_roles or []
                perms = row.conflicting_permissions or []

                if isinstance(roles, list) and len(roles) >= 2:
                    role_str = f"`{roles[0]}` ↔ `{roles[1]}`"
                elif isinstance(roles, list) and len(roles) == 1:
                    role_str = f"`{roles[0]}`"
                else:
                    role_str = str(roles) if roles else "—"

                if isinstance(perms, list) and len(perms) >= 2:
                    perm_str = f"{perms[0]} ↔ {perms[1]}"
                elif isinstance(perms, list) and len(perms) == 1:
                    perm_str = perms[0]
                else:
                    perm_str = str(perms) if perms else "—"

                dept_info = f" ({row.department})" if row.department else ""
                output += (
                    f"• *{row.user_name}*{dept_info} — {row.user_email}\n"
                    f"  Roles: {role_str}\n"
                    f"  Conflict: {perm_str}\n"
                    f"  Risk score: {row.risk_score:.0f}\n"
                )
            output += "\n"

        return output.rstrip()

    except Exception as e:
        logger.error(f"Error in list_violations_handler: {str(e)}", exc_info=True)
        return f"Error listing violations: {str(e)}"


async def get_role_risk_matrix_handler(
    role_name: str | None = None,
    severity: str | None = None,
    include_intra_role: bool = True,
    include_cross_role: bool = True,
    limit: int = 50
) -> str:
    """
    Query the precomputed role×role SOD conflict matrix (role_pair_conflicts table).
    Returns conflicts derived from actual permission+level analysis — not from real user
    assignments — so covers all 17 Fivetran roles and all 153 pairs.
    """
    try:
        logger.info(
            f"get_role_risk_matrix: role_name={role_name!r} severity={severity!r} "
            f"intra={include_intra_role} cross={include_cross_role} limit={limit}"
        )

        from models.database_config import DatabaseConfig

        severity_filter = "AND rpc.severity = :severity" if severity else ""
        intra_filter = ""
        if not include_intra_role and not include_cross_role:
            return "Both include_intra_role and include_cross_role are false — nothing to return."
        elif not include_intra_role:
            intra_filter = "AND rpc.is_intra_role = FALSE"
        elif not include_cross_role:
            intra_filter = "AND rpc.is_intra_role = TRUE"

        role_filter = ""
        if role_name:
            role_filter = "AND (LOWER(rpc.role_a_name) LIKE :role_pat OR LOWER(rpc.role_b_name) LIKE :role_pat)"

        sql = text(f"""
            SELECT
                rpc.role_a_name,
                rpc.role_b_name,
                rpc.is_intra_role,
                rpc.severity,
                rpc.rule_name,
                rpc.role_a_permission,
                rpc.role_a_level,
                rpc.role_b_permission,
                rpc.role_b_level,
                rpc.conflict_description
            FROM role_pair_conflicts rpc
            WHERE 1=1
              {severity_filter}
              {intra_filter}
              {role_filter}
            ORDER BY
                CASE rpc.severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH'     THEN 2
                    WHEN 'MEDIUM'   THEN 3
                    WHEN 'LOW'      THEN 4
                    ELSE 5
                END,
                rpc.role_a_name,
                rpc.role_b_name,
                rpc.rule_name
            LIMIT :limit
        """)

        params: dict = {"limit": limit}
        if severity:
            params["severity"] = severity
        if role_name:
            params["role_pat"] = f"%{role_name.lower()}%"

        db_config = DatabaseConfig()
        session = db_config.get_session()
        rows = session.execute(sql, params).fetchall()

        if not rows:
            msg = "No conflicts found"
            if role_name:
                msg += f" for role matching '{role_name}'"
            if severity:
                msg += f" at severity {severity}"
            return msg + "."

        # ── Group into summary blocks ─────────────────────────────────────────
        from collections import defaultdict
        pair_map: dict = defaultdict(list)
        for r in rows:
            key = (r.role_a_name, r.role_b_name, r.is_intra_role, r.severity)
            pair_map[key].append(r)

        lines = []
        lines.append(f"Role Risk Matrix — {len(rows)} conflict row(s) across {len(pair_map)} pair/severity group(s)\n")

        current_severity = None
        for (ra, rb, intra, sev), group_rows in sorted(
            pair_map.items(),
            key=lambda kv: (
                {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}.get(kv[0][3], 5),
                kv[0][0], kv[0][1]
            )
        ):
            if sev != current_severity:
                lines.append(f"\n{'─'*60}")
                lines.append(f"  {sev} conflicts")
                lines.append(f"{'─'*60}")
                current_severity = sev

            pair_type = "Intra-role" if intra else "Cross-role"
            if intra:
                lines.append(f"\n  [{pair_type}] {ra}")
            else:
                lines.append(f"\n  [{pair_type}] {ra}  +  {rb}")

            for gr in group_rows:
                if intra:
                    lines.append(
                        f"    • {gr.rule_name}: "
                        f"{gr.role_a_permission} ({gr.role_a_level})"
                        f"  ↔  {gr.role_b_permission} ({gr.role_b_level})"
                    )
                else:
                    lines.append(
                        f"    • {gr.rule_name}: "
                        f"{gr.role_a_permission} ({gr.role_a_level})"
                        f"  ×  {gr.role_b_permission} ({gr.role_b_level})"
                    )

        if len(rows) == limit:
            lines.append(f"\n(Showing first {limit} rows — use a role_name filter or increase limit for more)")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Error in get_role_risk_matrix_handler: {str(e)}", exc_info=True)
        return f"Error querying role risk matrix: {str(e)}"


# ============================================================================
# TOOL REGISTRY
# ============================================================================

TOOL_HANDLERS = {
    "list_systems": list_systems_handler,
    "perform_access_review": perform_access_review_handler,
    "get_user_violations": get_user_violations_handler,
    "remediate_violation": remediate_violation_handler,
    "schedule_review": schedule_review_handler,
    "get_violation_stats": get_violation_stats_handler,
    "start_collection_agent": start_collection_agent_handler,
    "stop_collection_agent": stop_collection_agent_handler,
    "get_collection_agent_status": get_collection_agent_status_handler,
    "trigger_manual_sync": trigger_manual_sync_handler,
    "list_all_users": list_all_users_handler,
    "analyze_access_request": analyze_access_request_handler,
    "query_sod_rules": query_sod_rules_handler,
    "get_compensating_controls": get_compensating_controls_handler,
    "validate_job_role": validate_job_role_handler,
    "check_permission_conflict": check_permission_conflict_handler,
    "get_permission_categories": get_permission_categories_handler,
    "search_permissions": search_permissions_handler,
    "query_knowledge_base": query_knowledge_base_handler,
    "recommend_roles_for_job_title": recommend_roles_for_job_title_handler,
    "analyze_role_permissions": analyze_role_permissions_handler,
    "get_role_conflicts": get_role_conflicts_handler,
    # Exception Management Tools (Phase 2)
    "record_exception_approval": record_exception_approval_handler,
    "find_similar_exceptions": find_similar_exceptions_handler,
    "get_exception_details": get_exception_details_handler,
    "list_approved_exceptions": list_approved_exceptions_handler,
    "record_exception_violation": record_exception_violation_handler,
    "get_exception_effectiveness_stats": get_exception_effectiveness_stats_handler,
    # Exception Management Tools (Phase 3)
    "detect_exception_violations": detect_exception_violations_handler,
    "conduct_exception_review": conduct_exception_review_handler,
    "get_exceptions_for_review": get_exceptions_for_review_handler,
    # RBAC and Approval Workflows (Phase 4)
    "initialize_session": initialize_session_handler,
    "check_my_approval_authority": check_my_approval_authority_handler,
    "request_exception_approval": request_exception_approval_handler,
    # Violation Reporting
    "generate_violation_report": generate_violation_report_handler,
    "list_violations": list_violations_handler,
    # Role Risk Matrix
    "get_role_risk_matrix": get_role_risk_matrix_handler,
}


# MCP-formatted tools list (for stdio transport)
TOOLS = [
    {
        "name": tool_name,
        "description": schema["description"],
        "inputSchema": schema["inputSchema"]
    }
    for tool_name, schema in TOOL_SCHEMAS.items()
]


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """Get schema for a specific tool"""
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> dict[str, Any]:
    """Get all tool schemas"""
    return TOOL_SCHEMAS


def get_tool_handler(tool_name: str):
    """Get handler function for a tool"""
    return TOOL_HANDLERS.get(tool_name)
