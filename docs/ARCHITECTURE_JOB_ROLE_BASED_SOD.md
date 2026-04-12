# Architecture: Job Role-Based SOD with Compensating Controls

**Date**: 2026-02-12
**Status**: Proposed - Enhancement to Level-Based SOD
**Priority**: HIGH

---

## Problem Statement

### Scenario: New Revenue Director Joins Fivetran

**User**: Jane Smith
**Job Title**: Revenue Director
**NetSuite Roles Requested**:
- Fivetran - Revenue Manager
- Fivetran - Revenue Approver

**Questions**:
1. Is there an **inherent conflict** between these roles?
2. What specific **permissions conflict** and at what **levels**?
3. Can the conflict be **resolved** (e.g., reduce permission levels)?
4. If not resolvable, what **compensating controls** should be implemented?
5. Is this combination **justifiable** for a Revenue Director?

### Current Gap

Our current analysis:
- ❌ Flags conflicts but doesn't suggest resolutions
- ❌ Doesn't consider job role context
- ❌ Doesn't provide compensating control options
- ❌ No risk acceptance workflow

---

## Enhanced Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SOD ANALYSIS WITH BUSINESS CONTEXT                │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
    ┌───────────────────────────┐  ┌─────────────────────────────┐
    │  INPUT: Access Request    │  │  CONFIGURATION              │
    │                           │  │                             │
    │  • User: Jane Smith       │  │  • Level-based conflict     │
    │  • Job Role: Rev Director │  │    matrices                 │
    │  • NS Roles:              │  │  • Job role to NS role      │
    │    - Revenue Manager      │  │    mappings                 │
    │    - Revenue Approver     │  │  • Compensating controls    │
    │  • Department: Finance    │  │    library                  │
    └───────────────────────────┘  └─────────────────────────────┘
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
            ┌──────────────────────────────────────┐
            │  STEP 1: Permission Level Analysis   │
            │                                      │
            │  Analyze each permission pair:       │
            │  • Revenue Manager permissions       │
            │  • Revenue Approver permissions      │
            │  • Check level conflict matrix       │
            │  • Calculate risk scores             │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │  STEP 2: Conflict Classification     │
            │                                      │
            │  Classify each conflict:             │
            │  • INHERENT (Full + Full)            │
            │  • RESOLVABLE (can reduce levels)    │
            │  • ACCEPTABLE (View + View)          │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │  STEP 3: Job Role Validation         │
            │                                      │
            │  Check business justification:       │
            │  • Is role combination typical for   │
            │    this job title?                   │
            │  • Are there precedents?             │
            │  • What's the business need?         │
            └──────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
    ┌───────────────────────────┐  ┌─────────────────────────────┐
    │  NO CONFLICTS             │  │  CONFLICTS FOUND            │
    │                           │  │                             │
    │  ✅ Approve automatically │  │  Proceed to resolution...   │
    └───────────────────────────┘  └─────────────────────────────┘
                                                   │
                    ┌──────────────────────────────┴─────────────┐
                    ▼                                            ▼
    ┌───────────────────────────┐              ┌─────────────────────────────┐
    │  STEP 4a: Resolution      │              │  STEP 4b: Compensating      │
    │  Options                  │              │  Controls                   │
    │                           │              │                             │
    │  For RESOLVABLE conflicts:│              │  For INHERENT conflicts:    │
    │  • Reduce permission      │              │  • Dual approval            │
    │    levels (Full → View)   │              │  • Segregated workflows     │
    │  • Split roles across     │              │  • Transaction limits       │
    │    different users        │              │  • Increased monitoring     │
    │  • Use separate sub-      │              │  • Manager review           │
    │    accounts               │              │  • Automated alerts         │
    └───────────────────────────┘              └─────────────────────────────┘
                    │                                            │
                    └──────────────┬─────────────────────────────┘
                                   ▼
            ┌──────────────────────────────────────┐
            │  STEP 5: Risk Acceptance Workflow    │
            │                                      │
            │  • Document business justification   │
            │  • Assign compensating controls      │
            │  • Require manager approval          │
            │  • Set review frequency              │
            │  • Generate monitoring alerts        │
            └──────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────┐
            │  OUTPUT: Access Decision + Controls  │
            │                                      │
            │  • APPROVED with conditions          │
            │  • Required compensating controls    │
            │  • Monitoring requirements           │
            │  • Review schedule                   │
            └──────────────────────────────────────┘
```

---

## Enhanced Data Model

### 1. Job Role to NetSuite Role Mappings

**File**: `data/job_role_mappings.json`

```json
{
  "job_roles": {
    "revenue_director": {
      "title": "Revenue Director",
      "department": "Finance",
      "level": "Director",
      "typical_netsuite_roles": [
        {
          "role": "Fivetran - Revenue Manager",
          "justification": "Need to oversee revenue recognition process",
          "common": true
        },
        {
          "role": "Fivetran - Revenue Approver",
          "justification": "Need to approve revenue transactions",
          "common": true,
          "conflicts_with": ["Fivetran - Revenue Manager"],
          "typical_resolution": "compensating_controls"
        },
        {
          "role": "Fivetran - Controller",
          "justification": "Too broad for Revenue Director role",
          "common": false,
          "recommendation": "Request more specific roles"
        }
      ],
      "typical_permissions": [
        {"permission": "Revenue Recognition", "typical_level": "Full"},
        {"permission": "Revenue Reports", "typical_level": "Full"},
        {"permission": "Invoice", "typical_level": "View"},
        {"permission": "Customer", "typical_level": "View"}
      ]
    },

    "accounts_payable_manager": {
      "title": "Accounts Payable Manager",
      "department": "Finance",
      "level": "Manager",
      "typical_netsuite_roles": [
        {
          "role": "Fivetran - A/P Analyst",
          "justification": "Core AP processing",
          "common": true
        },
        {
          "role": "Fivetran - Billing Manager",
          "justification": "Vendor bill management",
          "common": true,
          "conflicts_with": ["Fivetran - A/P Analyst"],
          "typical_resolution": "reduce_levels"
        }
      ]
    },

    "controller": {
      "title": "Controller",
      "department": "Finance",
      "level": "Executive",
      "typical_netsuite_roles": [
        {
          "role": "Fivetran - Controller",
          "justification": "Comprehensive financial oversight",
          "common": true
        }
      ],
      "high_privilege_justification": "Executive-level role requires broad access for financial oversight and reporting. Additional compensating controls required."
    }
  }
}
```

### 2. Conflict Resolution Strategies

**File**: `data/netsuite_sod_config.json` (enhanced)

```json
{
  "conflict_rules": {
    "transaction_entry_vs_transaction_approval": {
      "category1": "transaction_entry",
      "category2": "transaction_approval",
      "principle": "SOD-001: Maker-Checker Segregation",

      "level_conflict_matrix": {
        "matrix": [
          ["OK",   "OK",   "OK",   "OK",   "OK"  ],
          ["OK",   "OK",   "LOW",  "LOW",  "MED" ],
          ["OK",   "LOW",  "HIGH", "HIGH", "CRIT"],
          ["OK",   "LOW",  "HIGH", "CRIT", "CRIT"],
          ["OK",   "MED",  "CRIT", "CRIT", "CRIT"]
        ]
      },

      "resolution_strategies": {
        "LOW": {
          "classification": "ACCEPTABLE",
          "action": "APPROVE",
          "rationale": "Both read-only, no SOD violation"
        },
        "MED": {
          "classification": "RESOLVABLE",
          "actions": [
            {
              "strategy": "reduce_level",
              "description": "Reduce approval permission from Full to View",
              "example": "User can create transactions but only VIEW approval status (read-only oversight)",
              "risk_after": "LOW"
            },
            {
              "strategy": "compensating_control",
              "description": "Keep both Full, add manager approval",
              "controls_required": ["manager_approval", "dual_approval_workflow"],
              "risk_after": "MEDIUM"
            }
          ]
        },
        "HIGH": {
          "classification": "INHERENT",
          "recommended_action": "REJECT or COMPENSATING_CONTROLS",
          "resolution_options": [
            {
              "strategy": "split_roles",
              "description": "Assign roles to different users",
              "example": "User A: Transaction Entry (Create), User B: Transaction Approval (Full)"
            },
            {
              "strategy": "reduce_levels",
              "description": "Reduce one or both permissions to View",
              "example": "Entry: Create → View, Approval: Full → View",
              "risk_after": "LOW"
            },
            {
              "strategy": "compensating_controls",
              "description": "Multiple layers of control",
              "controls_required": [
                "dual_approval_workflow",
                "manager_review",
                "transaction_limits",
                "increased_audit_frequency"
              ],
              "risk_after": "MEDIUM"
            }
          ]
        },
        "CRIT": {
          "classification": "INHERENT",
          "recommended_action": "REJECT",
          "fallback_options": [
            {
              "strategy": "executive_override",
              "description": "Requires C-level approval with extensive compensating controls",
              "controls_required": [
                "dual_approval_workflow",
                "ceo_approval",
                "real_time_monitoring",
                "transaction_limits",
                "weekly_manager_review",
                "quarterly_audit_review"
              ],
              "risk_after": "HIGH",
              "review_frequency": "Monthly"
            }
          ]
        }
      }
    }
  }
}
```

### 3. Compensating Controls Library

**File**: `data/compensating_controls.json`

```json
{
  "controls": {
    "dual_approval_workflow": {
      "name": "Dual Approval Workflow",
      "type": "PREVENTIVE",
      "description": "All transactions above threshold require secondary approval from different user",
      "implementation": {
        "netsuite": "Configure workflow with approval routing",
        "threshold": "$10,000 or as defined by policy"
      },
      "effectiveness": "HIGH",
      "cost": "MEDIUM",
      "reduces_risk_by": 60
    },

    "manager_approval": {
      "name": "Manager Pre-Approval",
      "type": "PREVENTIVE",
      "description": "Direct manager must approve access request before provisioning",
      "implementation": {
        "workflow": "Access request → Manager approval → IT provisioning"
      },
      "effectiveness": "MEDIUM",
      "cost": "LOW",
      "reduces_risk_by": 30
    },

    "transaction_limits": {
      "name": "Transaction Amount Limits",
      "type": "PREVENTIVE",
      "description": "System enforced limits on transaction amounts per user",
      "implementation": {
        "netsuite": "Set approval thresholds in role configuration"
      },
      "effectiveness": "MEDIUM",
      "cost": "LOW",
      "reduces_risk_by": 40,
      "examples": {
        "payments": "Max $50,000 per transaction",
        "journal_entries": "Max $100,000 per entry"
      }
    },

    "segregated_workflows": {
      "name": "Segregated Approval Workflows",
      "type": "PREVENTIVE",
      "description": "User cannot approve transactions they created",
      "implementation": {
        "netsuite": "Workflow rules: IF creator = approver THEN route to manager"
      },
      "effectiveness": "HIGH",
      "cost": "MEDIUM",
      "reduces_risk_by": 70
    },

    "increased_audit_frequency": {
      "name": "Increased Audit Review",
      "type": "DETECTIVE",
      "description": "Monthly audit review of all transactions by internal audit",
      "implementation": {
        "frequency": "Monthly",
        "scope": "All transactions created and approved by same user role combination"
      },
      "effectiveness": "MEDIUM",
      "cost": "HIGH",
      "reduces_risk_by": 40
    },

    "real_time_monitoring": {
      "name": "Real-Time Transaction Monitoring",
      "type": "DETECTIVE",
      "description": "Automated alerts for suspicious activity patterns",
      "implementation": {
        "system": "Compliance monitoring dashboard",
        "alerts": [
          "Same user creates and approves transaction",
          "Transaction amount exceeds threshold",
          "After-hours transaction processing",
          "Unusual vendor payment patterns"
        ]
      },
      "effectiveness": "HIGH",
      "cost": "MEDIUM",
      "reduces_risk_by": 50
    },

    "manager_review": {
      "name": "Weekly Manager Review",
      "type": "DETECTIVE",
      "description": "Direct manager reviews all high-risk transactions weekly",
      "implementation": {
        "frequency": "Weekly",
        "scope": "Transactions above threshold or flagged as high-risk",
        "deliverable": "Manager sign-off on review"
      },
      "effectiveness": "MEDIUM",
      "cost": "MEDIUM",
      "reduces_risk_by": 35
    },

    "quarterly_audit_review": {
      "name": "Quarterly Audit Committee Review",
      "type": "DETECTIVE",
      "description": "Audit committee reviews all SOD exceptions quarterly",
      "implementation": {
        "frequency": "Quarterly",
        "scope": "All approved SOD exceptions with compensating controls",
        "deliverable": "Audit committee minutes documenting review"
      },
      "effectiveness": "MEDIUM",
      "cost": "HIGH",
      "reduces_risk_by": 30
    },

    "separate_accounts": {
      "name": "Separate User Accounts",
      "type": "PREVENTIVE",
      "description": "User has separate accounts for different functions (e.g., admin account vs. operational account)",
      "implementation": {
        "netsuite": "Two user accounts with different role assignments"
      },
      "effectiveness": "HIGH",
      "cost": "LOW",
      "reduces_risk_by": 80,
      "note": "Best practice but may not be practical for all users"
    },

    "ceo_approval": {
      "name": "CEO/CFO Pre-Approval",
      "type": "PREVENTIVE",
      "description": "Executive-level approval required for high-risk access combinations",
      "implementation": {
        "workflow": "Access request → Manager → CFO/CEO → IT"
      },
      "effectiveness": "HIGH",
      "cost": "LOW",
      "reduces_risk_by": 50
    }
  },

  "control_packages": {
    "low_risk_package": {
      "name": "Low Risk Controls",
      "applicable_to": ["LOW", "MEDIUM"],
      "controls": [
        "manager_approval",
        "transaction_limits"
      ],
      "total_risk_reduction": 70,
      "estimated_cost": "LOW"
    },

    "high_risk_package": {
      "name": "High Risk Controls",
      "applicable_to": ["HIGH"],
      "controls": [
        "dual_approval_workflow",
        "segregated_workflows",
        "transaction_limits",
        "real_time_monitoring",
        "manager_review"
      ],
      "total_risk_reduction": 85,
      "estimated_cost": "MEDIUM"
    },

    "critical_risk_package": {
      "name": "Critical Risk Controls",
      "applicable_to": ["CRITICAL"],
      "controls": [
        "ceo_approval",
        "dual_approval_workflow",
        "segregated_workflows",
        "transaction_limits",
        "real_time_monitoring",
        "manager_review",
        "quarterly_audit_review"
      ],
      "total_risk_reduction": 90,
      "estimated_cost": "HIGH",
      "note": "Should only be used when business justification is strong"
    }
  }
}
```

---

## Analysis Workflow: Revenue Director Example

### Scenario

**User**: Jane Smith
**Job Title**: Revenue Director
**Requested NetSuite Roles**:
- Fivetran - Revenue Manager
- Fivetran - Revenue Approver

### Step 1: Extract Permissions with Levels

```json
{
  "user": "Jane Smith",
  "job_title": "Revenue Director",
  "roles": [
    {
      "role": "Fivetran - Revenue Manager",
      "permissions": [
        {"name": "Revenue Recognition", "level": "Full", "level_value": 4, "category": "transaction_entry"},
        {"name": "Invoice", "level": "Full", "level_value": 4, "category": "transaction_entry"},
        {"name": "Customer", "level": "Edit", "level_value": 3, "category": "customer_setup"},
        {"name": "Revenue Reports", "level": "Full", "level_value": 4, "category": "financial_reporting"}
      ]
    },
    {
      "role": "Fivetran - Revenue Approver",
      "permissions": [
        {"name": "Approve Revenue Recognition", "level": "Full", "level_value": 4, "category": "transaction_approval"},
        {"name": "Approve Invoice", "level": "Full", "level_value": 4, "category": "transaction_approval"},
        {"name": "Revenue Reports", "level": "View", "level_value": 1, "category": "financial_reporting"}
      ]
    }
  ]
}
```

### Step 2: Analyze Conflicts with Levels

```json
{
  "conflicts_found": [
    {
      "conflict_id": "CONFLICT-001",
      "permission1": "Revenue Recognition",
      "permission1_level": "Full",
      "permission1_level_value": 4,
      "permission1_category": "transaction_entry",
      "permission1_role": "Fivetran - Revenue Manager",

      "permission2": "Approve Revenue Recognition",
      "permission2_level": "Full",
      "permission2_level_value": 4,
      "permission2_category": "transaction_approval",
      "permission2_role": "Fivetran - Revenue Approver",

      "severity": "CRITICAL",
      "risk_score": 100,
      "classification": "INHERENT",
      "principle": "SOD-001: Maker-Checker Segregation",
      "explanation": "User can create revenue recognition transactions AND approve them without oversight"
    },
    {
      "conflict_id": "CONFLICT-002",
      "permission1": "Invoice",
      "permission1_level": "Full",
      "permission1_level_value": 4,
      "permission1_category": "transaction_entry",
      "permission1_role": "Fivetran - Revenue Manager",

      "permission2": "Approve Invoice",
      "permission2_level": "Full",
      "permission2_level_value": 4,
      "permission2_category": "transaction_approval",
      "permission2_role": "Fivetran - Revenue Approver",

      "severity": "CRITICAL",
      "risk_score": 100,
      "classification": "INHERENT",
      "principle": "SOD-001: Maker-Checker Segregation",
      "explanation": "User can create invoices AND approve them without oversight"
    }
  ]
}
```

### Step 3: Check Job Role Justification

```json
{
  "job_role_analysis": {
    "job_title": "Revenue Director",
    "requested_roles": ["Fivetran - Revenue Manager", "Fivetran - Revenue Approver"],
    "is_typical_combination": true,
    "precedents": [
      {"user": "John Doe", "title": "Revenue Director", "same_roles": true, "controls_in_place": ["dual_approval_workflow", "manager_review"]}
    ],
    "business_justification": "Revenue Director role typically requires oversight of both revenue recognition process (manager role) and approval authority (approver role) for business operations efficiency",
    "recommendation": "APPROVE with COMPENSATING_CONTROLS"
  }
}
```

### Step 4: Generate Resolution Options

```json
{
  "resolution_options": [
    {
      "option_id": "OPTION-1",
      "strategy": "REJECT",
      "description": "Deny both roles, no access granted",
      "risk_after": "NONE",
      "business_impact": "HIGH - Cannot perform job duties",
      "recommended": false
    },
    {
      "option_id": "OPTION-2",
      "strategy": "SPLIT_ROLES",
      "description": "Assign roles to different users",
      "implementation": "Jane Smith: Revenue Manager only, Another user: Revenue Approver only",
      "risk_after": "NONE",
      "business_impact": "MEDIUM - Requires coordination with another employee",
      "recommended": false,
      "reason": "May not be practical for Revenue Director role"
    },
    {
      "option_id": "OPTION-3",
      "strategy": "REDUCE_LEVELS",
      "description": "Reduce approval permission from Full to View",
      "implementation": {
        "before": {
          "Revenue Manager": "Full",
          "Revenue Approver": "Full"
        },
        "after": {
          "Revenue Manager": "Full",
          "Revenue Approver": "View"
        }
      },
      "risk_after": "MEDIUM",
      "conflicts_remaining": 0,
      "business_impact": "MEDIUM - Can view approval status but cannot approve",
      "recommended": false,
      "reason": "Eliminates approval authority which is required for role"
    },
    {
      "option_id": "OPTION-4",
      "strategy": "COMPENSATING_CONTROLS",
      "description": "Approve both roles with extensive compensating controls",
      "implementation": {
        "roles_granted": ["Fivetran - Revenue Manager", "Fivetran - Revenue Approver"],
        "required_controls": [
          {
            "control": "segregated_workflows",
            "description": "User cannot approve transactions they created",
            "implementation": "NetSuite workflow: IF creator = approver THEN route to CFO"
          },
          {
            "control": "dual_approval_workflow",
            "description": "All revenue recognition > $50K requires secondary approval",
            "implementation": "NetSuite approval routing"
          },
          {
            "control": "real_time_monitoring",
            "description": "Automated alerts for same-user create+approve",
            "implementation": "Compliance dashboard with email alerts"
          },
          {
            "control": "manager_review",
            "description": "CFO reviews all revenue transactions weekly",
            "implementation": "Weekly report to CFO with sign-off requirement"
          },
          {
            "control": "transaction_limits",
            "description": "Max $100K per revenue recognition transaction",
            "implementation": "NetSuite role configuration"
          }
        ],
        "risk_after": "MEDIUM",
        "residual_risk_score": 35,
        "business_impact": "LOW - Can perform all job duties",
        "recommended": true,
        "total_risk_reduction": 65,
        "approval_required": "CFO",
        "review_frequency": "Quarterly"
      }
    }
  ]
}
```

### Step 5: Risk Acceptance Decision

```json
{
  "access_decision": {
    "decision": "APPROVED_WITH_CONDITIONS",
    "selected_option": "OPTION-4",
    "strategy": "COMPENSATING_CONTROLS",

    "approval_workflow": {
      "requested_by": "Jane Smith",
      "requested_date": "2026-02-12",
      "manager_approval": {
        "approver": "Bob Johnson (CFO)",
        "approved_date": "2026-02-13",
        "status": "APPROVED",
        "comments": "Revenue Director role requires both oversight and approval authority. Compensating controls adequately mitigate risk."
      },
      "compliance_review": {
        "reviewer": "Compliance Team",
        "reviewed_date": "2026-02-13",
        "status": "APPROVED",
        "comments": "Compensating controls meet SOD policy requirements"
      }
    },

    "granted_access": {
      "user": "Jane Smith",
      "roles": [
        "Fivetran - Revenue Manager",
        "Fivetran - Revenue Approver"
      ],
      "effective_date": "2026-02-14",
      "expiration_date": null,
      "review_date": "2026-05-14"
    },

    "compensating_controls_assigned": [
      {
        "control": "segregated_workflows",
        "status": "IMPLEMENTED",
        "implementation_date": "2026-02-14",
        "implemented_by": "NetSuite Admin",
        "validation": "Tested with sample transactions"
      },
      {
        "control": "dual_approval_workflow",
        "status": "IMPLEMENTED",
        "implementation_date": "2026-02-14",
        "threshold": "$50,000",
        "secondary_approver": "CFO"
      },
      {
        "control": "real_time_monitoring",
        "status": "IMPLEMENTED",
        "implementation_date": "2026-02-14",
        "alert_recipients": ["compliance@fivetran.com", "cfo@fivetran.com"]
      },
      {
        "control": "manager_review",
        "status": "SCHEDULED",
        "frequency": "Weekly",
        "reviewer": "Bob Johnson (CFO)",
        "next_review_date": "2026-02-21"
      },
      {
        "control": "transaction_limits",
        "status": "IMPLEMENTED",
        "implementation_date": "2026-02-14",
        "limit": "$100,000 per transaction"
      }
    ],

    "monitoring_requirements": {
      "alert_triggers": [
        "Jane Smith creates AND approves same transaction",
        "Revenue recognition transaction > $50K without secondary approval",
        "After-hours revenue transaction processing",
        "Transaction exceeds $100K limit"
      ],
      "review_schedule": {
        "frequency": "Quarterly",
        "next_review": "2026-05-14",
        "reviewer": "Internal Audit"
      }
    },

    "documentation": {
      "business_justification": "Revenue Director role requires comprehensive oversight of revenue recognition process including both management and approval authority for operational efficiency and strategic decision-making.",
      "risk_assessment": {
        "inherent_risk": "CRITICAL (100)",
        "residual_risk": "MEDIUM (35)",
        "risk_reduction": "65%"
      },
      "attestation": {
        "user_acknowledged": true,
        "user_signature": "Jane Smith",
        "date": "2026-02-14",
        "statement": "I acknowledge that I have been granted access with elevated privileges and understand that compensating controls are in place. I agree to comply with all monitoring and review requirements."
      }
    }
  }
}
```

---

## Implementation

### Phase 1: Configuration Files

1. **`data/job_role_mappings.json`** - Job titles to typical NetSuite roles
2. **`data/compensating_controls.json`** - Library of available controls
3. **`data/netsuite_sod_config.json`** (enhanced) - Add resolution strategies

### Phase 2: Enhanced Analysis Script

**File**: `scripts/analyze_access_request.py`

```python
def analyze_access_request(user_info, requested_roles):
    """
    Complete analysis for access request with job role context

    Args:
        user_info: {name, job_title, department, manager}
        requested_roles: [list of NetSuite role names]

    Returns:
        {
            conflicts_found: [...],
            resolution_options: [...],
            recommended_option: {...},
            risk_assessment: {...}
        }
    """

    # Step 1: Extract permissions with levels
    permissions = extract_permissions_for_roles(requested_roles)

    # Step 2: Analyze conflicts with level-based rules
    conflicts = analyze_conflicts_with_levels(permissions)

    # Step 3: Check job role justification
    job_role_analysis = validate_job_role_combination(
        user_info['job_title'],
        requested_roles
    )

    # Step 4: Generate resolution options
    resolution_options = generate_resolution_options(
        conflicts,
        job_role_analysis,
        user_info
    )

    # Step 5: Recommend best option
    recommended = recommend_best_option(
        resolution_options,
        user_info,
        job_role_analysis
    )

    return {
        'conflicts_found': conflicts,
        'resolution_options': resolution_options,
        'recommended_option': recommended,
        'risk_assessment': calculate_risk_assessment(conflicts, recommended)
    }
```

### Phase 3: Risk Acceptance Workflow

**File**: `mcp/tools/access_request_approval.py`

```python
def submit_access_request(user_info, requested_roles, justification):
    """
    Submit access request for approval

    Workflow:
    1. Analyze conflicts and generate options
    2. If CRITICAL conflicts, require manager pre-approval
    3. Route to compliance for review
    4. Assign compensating controls
    5. Provision access
    6. Schedule reviews
    """
    pass

def approve_with_compensating_controls(request_id, controls):
    """
    Approve request with specified compensating controls

    Actions:
    1. Validate controls are appropriate for risk level
    2. Implement controls in NetSuite
    3. Set up monitoring alerts
    4. Schedule manager reviews
    5. Document in audit log
    """
    pass
```

---

## Benefits

### 1. Business-Aligned Decisions

**Before**: "CRITICAL violation - REJECT"

**After**: "CRITICAL violation - But typical for Revenue Director role. APPROVE with compensating controls."

### 2. Practical Resolution Options

Instead of just flagging conflicts, provide actionable paths:
- Reduce permission levels (if business allows)
- Split roles across users (if practical)
- Implement compensating controls (if justifiable)
- Accept risk with executive approval (last resort)

### 3. Audit-Ready Documentation

Every decision documented with:
- Business justification
- Risk assessment (inherent vs residual)
- Compensating controls implemented
- Approval workflow
- Review schedule

### 4. Ongoing Monitoring

Automated alerts for:
- User creates AND approves same transaction
- Transaction exceeds limits
- After-hours activity
- Unusual patterns

---

## Example: Complete Flow

```
REQUEST: Jane Smith (Revenue Director) requests Revenue Manager + Revenue Approver

ANALYSIS:
  ✓ Extract 125 permissions (Full, Edit, View levels)
  ✓ Identify 2 CRITICAL conflicts (Full + Full)
  ✓ Check job role: Typical for Revenue Director ✓
  ✓ Generate 4 resolution options

RECOMMENDATION:
  Option: APPROVE with COMPENSATING_CONTROLS
  Controls: 5 controls (segregated workflows, dual approval, monitoring, limits, reviews)
  Residual Risk: MEDIUM (35/100)
  Risk Reduction: 65%

APPROVAL WORKFLOW:
  ✓ Manager (CFO) approval
  ✓ Compliance review
  ✓ Risk acceptance documented

IMPLEMENTATION:
  ✓ Grant both roles
  ✓ Implement 5 compensating controls
  ✓ Set up monitoring alerts
  ✓ Schedule weekly CFO review
  ✓ Schedule quarterly audit review

MONITORING:
  • Real-time alerts if Jane creates+approves same transaction
  • Weekly CFO review of all revenue transactions
  • Quarterly internal audit review
  • Automatic review reminder in 90 days
```

---

## Recommendation

**Implement this comprehensive job role-based architecture** because:

1. **Business-Aligned**: Considers actual job functions, not just technical conflicts
2. **Practical**: Provides resolution options, not just flags
3. **Risk-Based**: Allows risk acceptance with appropriate controls
4. **Audit-Ready**: Complete documentation and approval workflow
5. **Continuous**: Ongoing monitoring and periodic reviews

**Effort**: 8-12 hours
**Impact**: CRITICAL - Enables practical SOD compliance that supports business operations

Would you like me to start implementing the configuration files and analysis scripts?
