# Architecture: Level-Based SOD Analysis

**Date**: 2026-02-12
**Status**: Proposed
**Priority**: HIGH

---

## Problem Statement

### Current State

Our SOD analysis currently detects conflicts at the **CATEGORY level** only:

```
Bills (transaction_entry) + Customer Payment (transaction_entry) = NO CONFLICT
```

But **we're ignoring permission LEVELS**:

```
Bills - View + Customer Payment - View = LOW risk (read-only)
Bills - Full + Customer Payment - Full = CRITICAL risk (can create bills and pay them)
```

### The Gap

**NetSuite Permission Levels**:
- **0 = None** - No access
- **1 = View** - Read-only access
- **2 = Create** - Can create new records
- **3 = Edit** - Can modify existing records
- **4 = Full** - Can create, edit, delete

**Current Analysis**:
- ❌ Treats all levels the same
- ❌ "Bills - View" + "Customer Payment - View" = flagged as CRITICAL
- ❌ False positives for read-only oversight roles
- ❌ Missing granular risk assessment

**What We Should Do**:
- ✅ Analyze conflicts based on LEVEL combinations
- ✅ View + View = Usually acceptable (oversight)
- ✅ Full + Full = Always CRITICAL (complete control)
- ✅ Edit + Full = HIGH risk (can modify + create)
- ✅ View + Full = MEDIUM risk (can see + act)

---

## Architectural Proposal

### Solution: Synthesize Configuration & Add Level-Based Rules

```
┌─────────────────────────────────────────────────────────────────┐
│                  UNIFIED SOD CONFIGURATION                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  netsuite_permission_categories.json                   │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Permission Definitions                           │  │    │
│  │  │  • Category: transaction_entry                    │  │    │
│  │  │  • Description: Can create/enter transactions     │  │    │
│  │  │  • Base Risk: HIGH                                │  │    │
│  │  │  • Keywords: ["Bills", "Invoice", "Check"]        │  │    │
│  │  │                                                    │  │    │
│  │  │  ┌──────────────────────────────────────────┐    │  │    │
│  │  │  │  NEW: Level-Based Risk Matrix            │    │  │    │
│  │  │  │  level_risk_multipliers:                 │    │  │    │
│  │  │  │    0 (None):   0.0x (no access)          │    │  │    │
│  │  │  │    1 (View):   0.3x (read-only)          │    │  │    │
│  │  │  │    2 (Create): 0.7x (can create)         │    │  │    │
│  │  │  │    3 (Edit):   0.8x (can modify)         │    │  │    │
│  │  │  │    4 (Full):   1.0x (complete control)   │    │  │    │
│  │  │  └──────────────────────────────────────────┘    │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  sod_conflict_rules.json (ENHANCED)                    │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Conflict Definitions                             │  │    │
│  │  │  • Category 1: transaction_entry                  │  │    │
│  │  │  • Category 2: transaction_approval               │  │    │
│  │  │  • Base Severity: CRITICAL                        │  │    │
│  │  │                                                    │  │    │
│  │  │  ┌──────────────────────────────────────────┐    │  │    │
│  │  │  │  NEW: Level-Based Conflict Matrix        │    │  │    │
│  │  │  │                                           │    │  │    │
│  │  │  │       Cat2: None View Cre Edit Full      │    │  │    │
│  │  │  │  Cat1:                                    │    │  │    │
│  │  │  │  None    OK   OK   OK   OK   OK          │    │  │    │
│  │  │  │  View    OK   LOW  LOW  MED  MED         │    │  │    │
│  │  │  │  Create  OK   LOW  HIGH HIGH CRIT        │    │  │    │
│  │  │  │  Edit    OK   MED  HIGH CRIT CRIT        │    │  │    │
│  │  │  │  Full    OK   MED  CRIT CRIT CRIT        │    │  │    │
│  │  │  │                                           │    │  │    │
│  │  │  └──────────────────────────────────────────┘    │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Enhanced Data Model

### 1. Enhanced Permission Categories

**File**: `data/netsuite_sod_config.json` (unified config)

```json
{
  "version": "2.0",
  "permission_categories": {
    "transaction_entry": {
      "description": "Can create or enter transactions",
      "base_risk": "HIGH",
      "keywords": ["Bills", "Invoice", "Check", "Deposit"],
      "patterns": ["^(Bill|Invoice|Check|Deposit)$"],

      "level_risk_adjustments": {
        "0": {"risk": "NONE", "multiplier": 0.0, "description": "No access"},
        "1": {"risk": "LOW", "multiplier": 0.3, "description": "Read-only access"},
        "2": {"risk": "MEDIUM", "multiplier": 0.7, "description": "Can create new records"},
        "3": {"risk": "HIGH", "multiplier": 0.8, "description": "Can edit existing records"},
        "4": {"risk": "HIGH", "multiplier": 1.0, "description": "Full control"}
      },

      "conflicts_with": ["transaction_approval", "transaction_payment"]
    },

    "transaction_approval": {
      "description": "Can approve transactions",
      "base_risk": "HIGH",
      "keywords": ["Approve"],

      "level_risk_adjustments": {
        "0": {"risk": "NONE", "multiplier": 0.0},
        "1": {"risk": "LOW", "multiplier": 0.2, "description": "Can view approval status"},
        "2": {"risk": "CRITICAL", "multiplier": 0.9, "description": "Can approve own entries"},
        "3": {"risk": "CRITICAL", "multiplier": 0.9, "description": "Can approve own entries"},
        "4": {"risk": "CRITICAL", "multiplier": 1.0, "description": "Can approve anything"}
      },

      "conflicts_with": ["transaction_entry", "transaction_payment"]
    },

    "transaction_payment": {
      "description": "Can process payments",
      "base_risk": "CRITICAL",
      "keywords": ["Customer Payment", "Vendor Payment", "Payment"],

      "level_risk_adjustments": {
        "0": {"risk": "NONE", "multiplier": 0.0},
        "1": {"risk": "LOW", "multiplier": 0.2, "description": "Can view payment history"},
        "2": {"risk": "CRITICAL", "multiplier": 0.8, "description": "Can process payments"},
        "3": {"risk": "CRITICAL", "multiplier": 0.9, "description": "Can modify payments"},
        "4": {"risk": "CRITICAL", "multiplier": 1.0, "description": "Full payment control"}
      },

      "conflicts_with": ["transaction_entry", "transaction_approval", "vendor_setup", "bank_reconciliation"]
    }
  },

  "conflict_rules": {
    "transaction_entry_vs_transaction_approval": {
      "category1": "transaction_entry",
      "category2": "transaction_approval",
      "description": "Maker-Checker Segregation",
      "principle": "SOD-001: Separate transaction creation from approval",

      "level_conflict_matrix": {
        "comment": "Rows = Cat1 levels, Cols = Cat2 levels",
        "matrix": [
          ["OK",   "OK",   "OK",   "OK",   "OK"  ],
          ["OK",   "OK",   "LOW",  "LOW",  "MED" ],
          ["OK",   "LOW",  "HIGH", "HIGH", "CRIT"],
          ["OK",   "LOW",  "HIGH", "CRIT", "CRIT"],
          ["OK",   "MED",  "CRIT", "CRIT", "CRIT"]
        ],
        "row_labels": ["None", "View", "Create", "Edit", "Full"],
        "col_labels": ["None", "View", "Create", "Edit", "Full"]
      },

      "examples": {
        "OK": {
          "level1": "None", "level2": "Full",
          "explanation": "No transaction entry permission, approval is fine"
        },
        "LOW": {
          "level1": "View", "level2": "View",
          "explanation": "Both read-only, low risk for oversight roles"
        },
        "MED": {
          "level1": "View", "level2": "Full",
          "explanation": "Can view transactions and approve them - oversight acceptable"
        },
        "HIGH": {
          "level1": "Create", "level2": "Edit",
          "explanation": "Can create transactions and approve them - SOD violation"
        },
        "CRIT": {
          "level1": "Full", "level2": "Full",
          "explanation": "Complete control over entry and approval - major SOD violation"
        }
      }
    },

    "transaction_entry_vs_transaction_payment": {
      "category1": "transaction_entry",
      "category2": "transaction_payment",
      "description": "Payment Segregation",
      "principle": "SOD-002: Separate transaction creation from payment processing",

      "level_conflict_matrix": {
        "matrix": [
          ["OK",   "OK",   "OK",   "OK",   "OK"  ],
          ["OK",   "OK",   "LOW",  "MED",  "MED" ],
          ["OK",   "LOW",  "CRIT", "CRIT", "CRIT"],
          ["OK",   "MED",  "CRIT", "CRIT", "CRIT"],
          ["OK",   "MED",  "CRIT", "CRIT", "CRIT"]
        ],
        "row_labels": ["None", "View", "Create", "Edit", "Full"],
        "col_labels": ["None", "View", "Create", "Edit", "Full"]
      },

      "rationale": "Any ability to create transactions + process payments = fraud risk"
    },

    "transaction_payment_vs_bank_reconciliation": {
      "category1": "transaction_payment",
      "category2": "bank_reconciliation",
      "description": "Payment Oversight Segregation",
      "principle": "SOD-003: Separate payment processing from bank reconciliation",

      "level_conflict_matrix": {
        "matrix": [
          ["OK",   "OK",   "OK",   "OK",   "OK"  ],
          ["OK",   "OK",   "LOW",  "LOW",  "MED" ],
          ["OK",   "LOW",  "HIGH", "CRIT", "CRIT"],
          ["OK",   "LOW",  "CRIT", "CRIT", "CRIT"],
          ["OK",   "MED",  "CRIT", "CRIT", "CRIT"]
        ],
        "row_labels": ["None", "View", "Create", "Edit", "Full"],
        "col_labels": ["None", "View", "Create", "Edit", "Full"]
      },

      "rationale": "Can process payments and reconcile bank = can hide fraudulent payments"
    }
  }
}
```

---

## Implementation Plan

### Phase 1: Unified Configuration (1-2 hours)

1. **Create unified config**: `data/netsuite_sod_config.json`
   - Merge permission categories
   - Add level risk adjustments
   - Define level conflict matrices
   - Add SOD principles and rationale

2. **Deprecate old files** (keep for reference):
   - `data/sod_rules.json` → moved to unified config
   - `data/netsuite_permission_categories.json` → moved to unified config

### Phase 2: Enhanced Analysis Script (2-3 hours)

**File**: `scripts/analyze_fivetran_permissions_level_based.py`

```python
def analyze_conflict_with_levels(self, perm1, perm2, conflict_rule):
    """
    Analyze conflict considering permission levels

    Args:
        perm1: {permission_name, permission_level, permission_level_value, category}
        perm2: {permission_name, permission_level, permission_level_value, category}
        conflict_rule: Rule from unified config

    Returns:
        {severity, risk_score, explanation} or None
    """
    level1 = perm1['permission_level_value']  # 0-4
    level2 = perm2['permission_level_value']  # 0-4

    # Get conflict matrix from config
    matrix = conflict_rule['level_conflict_matrix']['matrix']

    # Look up severity based on levels
    severity = matrix[level1][level2]

    if severity == "OK":
        return None  # No conflict

    # Calculate risk score
    base_risk1 = self.get_base_risk(perm1['category'])
    base_risk2 = self.get_base_risk(perm2['category'])

    level_multiplier1 = self.get_level_multiplier(perm1['category'], level1)
    level_multiplier2 = self.get_level_multiplier(perm2['category'], level2)

    risk_score = (base_risk1 * level_multiplier1 + base_risk2 * level_multiplier2) / 2

    return {
        'severity': severity,
        'risk_score': risk_score,
        'level1': perm1['permission_level'],
        'level2': perm2['permission_level'],
        'explanation': self.get_conflict_explanation(conflict_rule, level1, level2),
        'principle': conflict_rule['principle']
    }
```

**Key Changes**:

1. Load unified config instead of separate files
2. For each permission pair, check level conflict matrix
3. Calculate granular risk scores based on levels
4. Generate explanations with level details

### Phase 3: Enhanced Output (1 hour)

**New Output Format**:

```json
{
  "conflict_id": "SOD-FIVETRAN-001-LEVEL",
  "role1": "Fivetran - Accountant",
  "role2": "Fivetran - Controller",
  "severity": "CRITICAL",
  "risk_score": 95,

  "conflicts": [
    {
      "permission1": "Bills",
      "permission1_level": "Full",
      "permission1_level_value": 4,
      "permission1_category": "transaction_entry",

      "permission2": "Approve Bills",
      "permission2_level": "Full",
      "permission2_level_value": 4,
      "permission2_category": "transaction_approval",

      "conflict_severity": "CRITICAL",
      "risk_score": 100,
      "principle": "SOD-001: Separate transaction creation from approval",
      "explanation": "User has FULL control over both creating bills AND approving them. Can create fraudulent bills and approve them without oversight.",

      "level_analysis": {
        "matrix_position": [4, 4],
        "base_severity": "CRIT",
        "level1_risk": "HIGH (1.0x multiplier)",
        "level2_risk": "CRITICAL (1.0x multiplier)",
        "combined_risk": "CRITICAL"
      }
    }
  ]
}
```

---

## Benefits

### 1. Eliminates False Positives

**Before**:
```
User: Jane Doe
Roles: Fivetran - External View Only, Fivetran - FP&A
Violation: transaction_entry + transaction_approval = CRITICAL
```

**After**:
```
User: Jane Doe
Roles: Fivetran - External View Only, Fivetran - FP&A
Permissions:
  - Bills: View (level 1)
  - Approve Bills: View (level 1)
Analysis: Both read-only = LOW risk (oversight role acceptable)
```

### 2. Accurate Risk Scoring

**Before**: All conflicts = CRITICAL

**After**: Granular scoring based on actual capabilities

| Level Combination | Severity | Risk Score | Explanation |
|-------------------|----------|------------|-------------|
| View + View | LOW | 15 | Both read-only, oversight acceptable |
| View + Create | LOW | 35 | Can view + create, limited risk |
| View + Full | MEDIUM | 55 | Can view + act, moderate oversight |
| Create + Edit | HIGH | 75 | Can create + approve, SOD violation |
| Full + Full | CRITICAL | 100 | Complete control, major fraud risk |

### 3. Better Compliance Reporting

**Report Output**:
```
CRITICAL Violations (Full + Full): 12 users
  • Can create AND approve transactions
  • Recommended action: Remove one role immediately

HIGH Violations (Create/Edit + Edit/Full): 8 users
  • Can create AND approve/modify
  • Recommended action: Mitigating controls required

MEDIUM Violations (View + Full): 15 users
  • Can view AND act
  • Recommended action: Review for business justification

LOW Risk (View + View): 45 users
  • Read-only oversight roles
  • Recommended action: No action required
```

---

## Migration Path

### Step 1: Create Unified Config (Now)

Create `data/netsuite_sod_config.json` with:
- All permission categories
- Level risk adjustments
- Level conflict matrices
- SOD principles

### Step 2: Update Analysis Script (Next)

Modify `analyze_fivetran_permissions_advanced.py`:
- Load unified config
- Add level-based conflict detection
- Calculate granular risk scores
- Generate level-aware explanations

### Step 3: Re-run Analysis (Test)

Run analysis with level-based logic:
```bash
python scripts/analyze_fivetran_permissions_level_based.py
```

Expected results:
- Fewer total conflicts (eliminate false positives)
- More accurate severity ratings
- Granular risk scores
- Level-specific recommendations

### Step 4: Compare Results (Validation)

Compare old vs new:
- How many conflicts reduced?
- Which ones were false positives?
- Are CRITICAL conflicts truly critical?

### Step 5: Update Documentation (Final)

Update all docs to reference level-based analysis:
- LESSONS_LEARNED.md - add Issue #17
- FIVETRAN_ANALYSIS_SUMMARY.md - update with level analysis
- NETSUITE_PERMISSION_EXTRACTION_ISSUE.md - mention level granularity

---

## Example: Before vs After

### Scenario: Accounting Manager Role

**Permissions**:
- Bills: Full (level 4)
- Customer Payment: View (level 1)
- Approve Bills: View (level 1)
- Reconcile: View (level 1)

### Before (Category-Only Analysis)

```
Conflicts found: 4 CRITICAL violations

1. transaction_entry + transaction_approval = CRITICAL
   (Bills + Approve Bills)

2. transaction_entry + transaction_payment = CRITICAL
   (Bills + Customer Payment)

3. transaction_entry + bank_reconciliation = CRITICAL
   (Bills + Reconcile)

4. transaction_payment + bank_reconciliation = CRITICAL
   (Customer Payment + Reconcile)
```

### After (Level-Based Analysis)

```
Conflicts found: 0 violations requiring action

Analysis:
1. Bills (Full) + Approve Bills (View) = LOW
   • Can create bills but only VIEW approval status
   • No approval capability = No SOD violation
   • Risk Score: 25/100

2. Bills (Full) + Customer Payment (View) = MEDIUM
   • Can create bills and VIEW payments (read-only)
   • Cannot process payments = Limited risk
   • Risk Score: 45/100
   • Acceptable for oversight roles

3. Bills (Full) + Reconcile (View) = LOW
   • Can create bills, VIEW reconciliation status
   • Cannot reconcile = No hiding capability
   • Risk Score: 35/100

4. Customer Payment (View) + Reconcile (View) = OK
   • Both read-only
   • Risk Score: 10/100
```

**Result**: Role is acceptable for an accounting manager with oversight responsibilities.

---

## Recommendation

**IMPLEMENT THIS ARCHITECTURE**

**Why**:
1. **Eliminates false positives** - Current analysis flags 169 conflicts, many are likely View+View
2. **Accurate risk assessment** - Level-based risk scores reflect actual capabilities
3. **Better business alignment** - Supports legitimate oversight roles (View+View)
4. **Audit-ready** - Can explain WHY something is/isn't a violation
5. **Industry standard** - SOD analysis should always consider privilege levels

**Effort**: 4-6 hours total
**Impact**: HIGH - Transforms analysis from noisy to actionable

**Next Step**: Create the unified config and I'll implement the enhanced analysis script.
