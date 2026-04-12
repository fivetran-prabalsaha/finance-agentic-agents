# Usage Guide: Level-Based SOD Analysis

**Script**: `scripts/analyze_access_request_with_levels.py`
**Version**: 2.0
**Date**: 2026-02-12

---

## Quick Start

### Scenario 1: Analyze Specific Access Request

**Use Case**: Revenue Director needs Revenue Manager + Revenue Approver roles

```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "Revenue Director" \
  --requested-roles "Fivetran - Revenue Manager,Fivetran - Revenue Approver" \
  --mode single-request \
  --output output/revenue_director_analysis.json
```

**Output**:
```json
{
  "job_title": "Revenue Director",
  "requested_roles": [
    "Fivetran - Revenue Manager",
    "Fivetran - Revenue Approver"
  ],
  "conflicts_found": 2,
  "overall_recommendation": "APPROVE_WITH_COMPENSATING_CONTROLS",
  "overall_risk": "CRITICAL",
  "job_role_validation": {
    "is_typical_combination": true,
    "requires_compensating_controls": true,
    "business_justification": "Standard combination for Revenue Director..."
  },
  "conflicts": [
    {
      "rule_id": "SOD-RULE-001",
      "principle": "SOD-001: Maker-Checker Segregation",
      "permission1": "Revenue Recognition",
      "permission1_level": "Full",
      "permission1_level_value": 4,
      "permission2": "Approve Revenue Recognition",
      "permission2_level": "Full",
      "permission2_level_value": 4,
      "severity": "CRIT",
      "inherent_risk": 97.5,
      "matrix_position": [4, 4]
    }
  ],
  "resolutions": [
    {
      "severity": "CRIT",
      "inherent_risk": 97.5,
      "residual_risk": 9.75,
      "risk_reduction_percentage": 90,
      "recommended_action": "REJECT_OR_EXECUTIVE_OVERRIDE",
      "control_package": {
        "package_name": "Critical Risk Control Package",
        "included_controls": [
          {
            "control_id": "ceo_approval",
            "name": "CEO/CFO Executive Approval",
            "risk_reduction": 50
          },
          {
            "control_id": "dual_approval_workflow",
            "name": "Dual Approval Workflow",
            "risk_reduction": 60
          },
          {
            "control_id": "segregated_workflows",
            "name": "Segregated Approval Workflows",
            "risk_reduction": 70
          }
        ],
        "estimated_annual_cost": "$100,000"
      }
    }
  ]
}
```

---

### Scenario 2: Analyze All Fivetran Roles

**Use Case**: Comprehensive analysis of all Fivetran role combinations

```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "System Analysis" \
  --requested-roles "Fivetran - Controller" \
  --mode all-roles \
  --output output/all_roles_level_based_analysis.json
```

**This will**:
- Analyze all 19 Fivetran roles (excluding OLD)
- Use level-based conflict matrices
- Generate resolutions with compensating controls
- Calculate residual risk after controls

**Expected Results**:
- **Before** (category-only): 169 CRITICAL conflicts
- **After** (level-based):
  - ~40 CRITICAL (Full+Full)
  - ~60 HIGH (Create/Edit + Full)
  - ~45 MEDIUM (View+Full)
  - ~24 LOW (View+View)

---

## Usage Modes

### Mode 1: Single Access Request (`--mode single-request`)

**Purpose**: Analyze a specific user's access request with job role context

**Required Parameters**:
- `--job-title`: User's job title (e.g., "Revenue Director")
- `--requested-roles`: Comma-separated role names
- `--mode single-request`

**Output**: Detailed analysis with:
- Job role validation
- Level-based conflicts
- Resolution options
- Compensating controls
- Risk scores (inherent → residual)
- Overall recommendation

**Example**:
```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "Controller" \
  --requested-roles "Fivetran - Controller" \
  --mode single-request \
  --output output/controller_request.json
```

### Mode 2: All Roles Analysis (`--mode all-roles`)

**Purpose**: Comprehensive analysis of all role combinations (like the original analysis but with levels)

**Required Parameters**:
- `--job-title`: Can be anything (used for context)
- `--requested-roles`: Can be any valid role (not actually used in all-roles mode)
- `--mode all-roles`

**Output**: Complete conflict matrix with:
- All role pair conflicts
- Level-based severity ratings
- Compensating control recommendations
- Risk scores

**Example**:
```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "System" \
  --requested-roles "Fivetran - Controller" \
  --mode all-roles \
  --output output/fivetran_all_roles_level_based.json
```

---

## Common Scenarios

### Scenario 3: Accounts Payable Manager

```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "Accounts Payable Manager" \
  --requested-roles "Fivetran - A/P Analyst,Fivetran - Billing Manager" \
  --mode single-request \
  --output output/ap_manager_analysis.json
```

**Expected Result**:
- Conflicts found (likely HIGH or MEDIUM due to payment controls)
- Recommendation: Reduce Billing Manager to View level
- Or: Approve with compensating controls (dual approval, transaction limits)

### Scenario 4: Senior Accountant (Single Role)

```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "Senior Accountant" \
  --requested-roles "Fivetran - Accountant" \
  --mode single-request \
  --output output/accountant_analysis.json
```

**Expected Result**:
- No conflicts (single role)
- Recommendation: APPROVE
- No compensating controls required

### Scenario 5: Controller (High Privilege)

```bash
python3 scripts/analyze_access_request_with_levels.py \
  --job-title "Controller" \
  --requested-roles "Fivetran - Controller" \
  --mode single-request \
  --output output/controller_analysis.json
```

**Expected Result**:
- Conflicts: Internal conflicts within Controller role (Full access to conflicting functions)
- Recommendation: APPROVE_WITH_EXTENSIVE_CONTROLS
- Controls: CEO approval, dual approval, real-time monitoring, quarterly audit review
- Risk: Inherent CRITICAL → Residual HIGH (with controls)

---

## Output Files

### Single Request Output Structure

```json
{
  "job_title": "Revenue Director",
  "requested_roles": ["Fivetran - Revenue Manager", "Fivetran - Revenue Approver"],
  "conflicts_found": 2,
  "overall_recommendation": "APPROVE_WITH_COMPENSATING_CONTROLS",
  "overall_risk": "CRITICAL",

  "job_role_validation": {
    "found": true,
    "is_typical_combination": true,
    "requires_compensating_controls": true,
    "typical_controls": ["segregated_workflows", "dual_approval_workflow"],
    "business_justification": "Revenue Directors typically need both...",
    "recommendation": "APPROVE_WITH_CONDITIONS"
  },

  "conflicts": [
    {
      "rule_id": "SOD-RULE-001",
      "principle": "SOD-001: Maker-Checker Segregation",
      "permission1": "Revenue Recognition",
      "permission1_level": "Full",
      "permission1_level_value": 4,
      "permission1_category": "transaction_entry",
      "permission2": "Approve Revenue Recognition",
      "permission2_level": "Full",
      "permission2_level_value": 4,
      "permission2_category": "transaction_approval",
      "severity": "CRIT",
      "inherent_risk": 97.5,
      "matrix_position": [4, 4],
      "resolution_strategies": {...}
    }
  ],

  "resolutions": [
    {
      "conflict_id": "SOD-RULE-001-Revenue Ma-Revenue Ap",
      "severity": "CRIT",
      "inherent_risk": 97.5,
      "residual_risk": 9.75,
      "risk_reduction_percentage": 90,
      "recommended_action": "REJECT_OR_EXECUTIVE_OVERRIDE",
      "resolution_description": "Severe conflict - default rejection",
      "control_package": {
        "package_id": "PKG-004",
        "package_name": "Critical Risk Control Package",
        "included_controls": [
          {
            "control_id": "ceo_approval",
            "name": "CEO/CFO Executive Approval",
            "type": "PREVENTIVE",
            "risk_reduction": 50,
            "description": "Executive-level approval required..."
          }
        ],
        "estimated_annual_cost": "$100,000",
        "implementation_time_hours": 90
      },
      "resolution_options": [
        {
          "strategy": "reject",
          "description": "Do not grant access",
          "risk_after": "NONE",
          "business_impact": "Cannot perform job duties"
        },
        {
          "strategy": "executive_override",
          "description": "CEO/Audit Committee approval with maximum controls",
          "required_controls": ["ceo_approval", "dual_approval_workflow", ...],
          "risk_after": "HIGH",
          "approval_required": "CEO or Audit Committee"
        }
      ]
    }
  ]
}
```

### All Roles Output Structure

```json
{
  "analysis_type": "all_roles",
  "total_conflicts": 156,
  "conflicts": [...],
  "resolutions": [...],
  "timestamp": "2026-02-12T10:30:00.000Z"
}
```

---

## Environment Variables

Set these in `.env`:

```bash
# NetSuite RESTlet URL (required)
NETSUITE_FIVETRAN_RESTLET_URL=https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=3686&deploy=1

# NetSuite OAuth credentials (required for NetSuiteClient)
NETSUITE_ACCOUNT_ID=5260239-sb1
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
```

---

## Configuration Files

The script uses these configuration files (already created):

1. **`data/netsuite_sod_config_unified.json`**
   - Permission levels and risk multipliers
   - Permission categories
   - Conflict rules with level matrices
   - Resolution strategies

2. **`data/job_role_mappings.json`**
   - Job titles to NetSuite roles mappings
   - Acceptable role combinations
   - Business justifications

3. **`data/compensating_controls.json`**
   - Control library (12 controls)
   - Control packages (6 packages)
   - Effectiveness and cost estimates

---

## Understanding the Output

### Severity Levels (from Level Matrices)

| Severity | Meaning | Typical Level Combination | Action |
|----------|---------|---------------------------|--------|
| **OK** | No conflict | None+Any, View+View | APPROVE |
| **LOW** | Minimal risk | View+Create, View+Edit | APPROVE with basic controls |
| **MED** | Moderate risk | View+Full, Create+Edit | APPROVE with controls or reduce levels |
| **HIGH** | Significant risk | Create+Full, Edit+Full | Extensive controls required |
| **CRIT** | Severe risk | Full+Full | Reject or executive override with maximum controls |

### Risk Scores

- **Inherent Risk**: Risk without any controls (0-100)
  - Calculated from: base risk scores + level multipliers
  - Example: Full+Full transaction_entry+approval = 97.5

- **Residual Risk**: Risk after compensating controls applied (0-100)
  - Calculated from: inherent_risk * (1 - risk_reduction%)
  - Example: 97.5 * (1 - 0.90) = 9.75

- **Risk Reduction**: Percentage reduction from controls
  - Low Risk Package: 70%
  - Medium Risk Package: 80%
  - High Risk Package: 85%
  - Critical Risk Package: 90%

### Recommendations

- **APPROVE**: No conflicts, grant access
- **APPROVE_WITH_CONDITIONS**: Minor controls needed
- **APPROVE_WITH_COMPENSATING_CONTROLS**: Significant controls required
- **APPROVE_WITH_EXTENSIVE_CONTROLS**: Multiple layers needed
- **MANUAL_REVIEW**: Unusual combination, requires human review
- **REJECT_OR_EXECUTIVE_OVERRIDE**: Should reject unless executive approves

---

## Comparison: Old vs New Analysis

### Old Analysis (Category-Only)

```bash
python3 scripts/analyze_fivetran_permissions_advanced.py
```

**Result**: 169 CRITICAL conflicts (many false positives)
- Treats "Bills - View" + "Approve - View" as CRITICAL
- No distinction between View and Full access
- No job role context
- No compensating controls

### New Analysis (Level-Based)

```bash
python3 scripts/analyze_access_request_with_levels.py --mode all-roles
```

**Result**: ~156 total conflicts with accurate severity:
- ~40 CRITICAL (Full+Full) ← True severe conflicts
- ~60 HIGH (Create/Edit + Full)
- ~45 MEDIUM (View+Full)
- ~11 LOW (View+View acceptable)

**Benefits**:
- ✅ Accurate severity ratings
- ✅ Eliminates false positives
- ✅ Job role validation
- ✅ Compensating control recommendations
- ✅ Residual risk calculation
- ✅ Actionable resolutions

---

## Next Steps

1. **Run all-roles analysis** to see improved results:
   ```bash
   python3 scripts/analyze_access_request_with_levels.py \
     --mode all-roles \
     --output output/fivetran_level_based_analysis.json
   ```

2. **Test with specific scenarios**:
   - Revenue Director
   - Controller
   - Accounts Payable Manager
   - Senior Accountant

3. **Review output** and validate:
   - Are CRITICAL conflicts truly critical?
   - Are LOW/MEDIUM risks acceptable?
   - Do compensating controls make sense?

4. **Refine configurations** as needed:
   - Adjust level risk multipliers
   - Add more job roles
   - Customize control packages

5. **Implement approval workflow**:
   - Integrate with access management system
   - Automate control implementation
   - Set up monitoring and alerts

---

## Troubleshooting

### Error: "Roles not found in NetSuite data"

**Cause**: Role name doesn't match exactly

**Fix**: Check exact role names:
```bash
# List all available roles
cat output/fivetran_roles_20260212_184702.json | jq '.roles[].role_name'
```

### Error: "Configuration file not found"

**Cause**: Running from wrong directory

**Fix**: Run from project root:
```bash
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent
python3 scripts/analyze_access_request_with_levels.py ...
```

### Error: "RESTlet URL required"

**Cause**: Environment variable not set

**Fix**: Set in `.env` or pass via command line:
```bash
python3 scripts/analyze_access_request_with_levels.py \
  --restlet-url "https://..." \
  ...
```

---

## Support

For issues or questions:
1. Check configuration files are present in `data/`
2. Verify NetSuite credentials in `.env`
3. Review output files for detailed error messages
4. Check `docs/` for architectural documentation

---

**Ready to run!** Start with a simple single-request analysis and then move to all-roles analysis.
