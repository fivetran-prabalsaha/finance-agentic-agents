"""
build_role_risk_matrix.py
=========================
Builds the complete Fivetran role × role SOD conflict matrix.

Steps executed in order:
  1. Run DB migrations 008 + 009 (idempotent — IF NOT EXISTS).
  2. Populate sod_permission_map — the rosetta stone mapping abstract SOD
     permission names to actual NetSuite permission_name strings plus the
     minimum level at which each side of a conflict becomes active.
  3. Patch the 6 SOD rules that have empty conflicting_permissions.
  4. For every pair of Fivetran roles (153 unique pairs incl. self-pairs),
     evaluate every SOD rule conflict pair using level-aware logic and write
     results to role_pair_conflicts.

Level hierarchy:  None=0  View=1  Create=2  Edit=3  Full=4

Run:
    cd compliance-agent
    python3 scripts/build_role_risk_matrix.py

Re-running is safe — conflicts are upserted on the unique constraint.
"""

import json
import logging
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from models.database_config import DatabaseConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Level ordering
# ---------------------------------------------------------------------------
LEVEL_RANK = {"None": 0, "View": 1, "Create": 2, "Edit": 3, "Full": 4}

def level_gte(actual: str, minimum: str) -> bool:
    return LEVEL_RANK.get(actual, 0) >= LEVEL_RANK.get(minimum, 99)

# ---------------------------------------------------------------------------
# sod_permission_map seed data
#
# Format: (rule_id_str, conflict_index, side, abstract_name, ns_permission, min_level, note)
#   ns_permission=None  → permission not present in any Fivetran role; rule cannot fire.
#   min_level           → lowest level that activates this side as a conflict source.
# ---------------------------------------------------------------------------
PERMISSION_MAP_SEED = [
    # ── SOD-FIN-001  AP Entry vs. Approval Separation  (CRITICAL) ─────────
    ("SOD-FIN-001", 0, "left",  "Create Bill",
     "Bills", "Edit",
     "Bills at Edit/Full = can create or modify vendor bills"),
    ("SOD-FIN-001", 0, "right", "Approve Bill",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval at Edit/Full = can approve vendor bills"),
    ("SOD-FIN-001", 1, "left",  "Enter Vendor Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can initiate vendor payments"),
    ("SOD-FIN-001", 1, "right", "Approve Vendor Payment",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval at Edit/Full = authorises vendor payments"),

    # ── SOD-FIN-002  Journal Entry Creation vs. Approval  (CRITICAL) ──────
    ("SOD-FIN-002", 0, "left",  "Create Journal Entry",
     "Make Journal Entry", "Edit",
     "Make Journal Entry at Edit/Full = can create journal entries"),
    ("SOD-FIN-002", 0, "right", "Approve Journal Entry",
     "Journal Approval", "Edit",
     "Journal Approval at Edit/Full = can approve journal entries"),
    ("SOD-FIN-002", 1, "left",  "Edit Journal Entry",
     "Make Journal Entry", "Edit",
     "Same permission covers both create and edit"),
    ("SOD-FIN-002", 1, "right", "Approve Journal Entry",
     "Journal Approval", "Edit",
     "Journal Approval at Edit/Full = can approve journal entries"),

    # ── SOD-FIN-007  Payroll Processing vs. Employee Master Data  (CRITICAL)
    # No Fivetran roles have payroll processing permissions → left side = None
    ("SOD-FIN-007", 0, "left",  "Process Payroll",
     None, "Edit",
     "No Fivetran role holds payroll processing permissions"),
    ("SOD-FIN-007", 0, "right", "Create Employee",
     "Employee Record", "Edit",
     "Employee Record at Edit/Full = can create or modify employee records"),
    ("SOD-FIN-007", 1, "left",  "Process Payroll",
     None, "Edit",
     "No Fivetran role holds payroll processing permissions"),
    ("SOD-FIN-007", 1, "right", "Edit Employee Banking Details",
     "Employee Record", "Edit",
     "Employee Record at Edit/Full covers banking detail changes"),
    ("SOD-FIN-007", 2, "left",  "Run Payroll",
     None, "Edit",
     "No Fivetran role holds payroll processing permissions"),
    ("SOD-FIN-007", 2, "right", "Edit Employee Salary",
     "Employee Record", "Edit",
     "Employee Record at Edit/Full covers salary changes"),

    # ── SOD-PROC-002  Vendor Master Data vs. AP Processing  (CRITICAL) ────
    ("SOD-PROC-002", 0, "left",  "Create Vendor",
     "Vendors", "Edit",
     "Vendors at Edit/Full = can create new vendor records"),
    ("SOD-PROC-002", 0, "right", "Enter Vendor Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can initiate vendor payments"),
    ("SOD-PROC-002", 1, "left",  "Edit Vendor Banking Details",
     "Vendors", "Edit",
     "Vendors at Edit/Full covers banking detail changes on vendor"),
    ("SOD-PROC-002", 1, "right", "Enter Vendor Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can initiate vendor payments"),
    ("SOD-PROC-002", 2, "left",  "Edit Vendor",
     "Vendors", "Edit",
     "Vendors at Edit/Full = can modify vendor master data"),
    ("SOD-PROC-002", 2, "right", "Approve Bill",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval at Edit/Full = can approve bills to that vendor"),

    # ── SOD-COMP-002  Compliance Officer Independence  (CRITICAL) ─────────
    # These are role-category concepts without direct NetSuite permission mappings
    ("SOD-COMP-002", 0, "left",  "Compliance Officer",
     None, "Edit",
     "Compliance Officer is a role category, not a single NetSuite permission"),
    ("SOD-COMP-002", 0, "right", "Financial Approvals",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval is the closest single-permission proxy"),
    ("SOD-COMP-002", 1, "left",  "Internal Auditor",
     "Audit Trail", "View",
     "Audit Trail access is the key independence concern (any level)"),
    ("SOD-COMP-002", 1, "right", "Transaction Processing",
     "Bills", "Edit",
     "Bills at Edit/Full = processing financial transactions"),
    ("SOD-COMP-002", 2, "left",  "Risk Manager",
     None, "Edit",
     "Risk Manager is a role category without a direct permission mapping"),
    ("SOD-COMP-002", 2, "right", "Budget Approval",
     "Set Up Budgets", "Edit",
     "Set Up Budgets at Edit/Full = can approve / finalise budgets"),

    # ── SOD-COMP-001  Audit Log Access vs. Financial Transactions  (HIGH) ─
    # Special: View IS the minimum dangerous level for audit trail access
    ("SOD-COMP-001", 0, "left",  "View Audit Logs",
     "Audit Trail", "View",
     "Any Audit Trail access while also processing transactions = independence risk"),
    ("SOD-COMP-001", 0, "right", "Financial Transactions",
     "Bills", "Edit",
     "Bills at Edit/Full = processing financial transactions"),
    ("SOD-COMP-001", 1, "left",  "Clear Audit Logs",
     "Audit Trail", "Full",
     "Full Audit Trail = can clear/modify logs covering their own tracks"),
    ("SOD-COMP-001", 1, "right", "Any Transaction Processing",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = executing payments"),

    # ── SOD-FIN-003  Bank Reconciliation vs. Cash Transactions  (HIGH) ────
    ("SOD-FIN-003", 0, "left",  "Bank Reconciliation",
     "Reconcile", "Edit",
     "Reconcile at Edit/Full = can perform bank reconciliation"),
    ("SOD-FIN-003", 0, "right", "Create Check",
     "Check", "Edit",
     "Check at Edit/Full = can issue checks (cash transaction)"),
    ("SOD-FIN-003", 1, "left",  "Bank Reconciliation",
     "Reconcile", "Edit",
     "Reconcile at Edit/Full = can perform bank reconciliation"),
    ("SOD-FIN-003", 1, "right", "Create Deposit",
     "Customer Deposit", "Edit",
     "Customer Deposit at Edit/Full = can record deposits"),
    ("SOD-FIN-003", 2, "left",  "Bank Reconciliation",
     "Reconcile", "Edit",
     "Reconcile at Edit/Full = can perform bank reconciliation"),
    ("SOD-FIN-003", 2, "right", "Enter Vendor Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = executes payments that reconciler should verify"),

    # ── SOD-FIN-005  Revenue Recognition vs. Sales Order Entry  (HIGH) ────
    ("SOD-FIN-005", 0, "left",  "Revenue Recognition Override",
     "Revenue Arrangement Approval", "Edit",
     "Revenue Arrangement Approval at Edit/Full = can override revenue rules"),
    ("SOD-FIN-005", 0, "right", "Create Sales Order",
     None, "Edit",
     "No Fivetran role has Sales Order entry permission at qualifying level"),
    ("SOD-FIN-005", 1, "left",  "Revenue Recognition Override",
     "Revenue Arrangement Approval", "Edit",
     "Revenue Arrangement Approval at Edit/Full = can override revenue rules"),
    ("SOD-FIN-005", 1, "right", "Edit Sales Order",
     None, "Edit",
     "No Fivetran role has Sales Order edit permission at qualifying level"),
    ("SOD-FIN-005", 2, "left",  "Recognize Revenue",
     "Revenue Arrangement Approval", "Edit",
     "Revenue Arrangement Approval at Edit/Full = can finalise revenue recognition"),
    ("SOD-FIN-005", 2, "right", "Create Invoice",
     "Invoice Approval", "Edit",
     "Invoice Approval at Edit/Full = can create and approve invoices"),

    # ── SOD-IT-001  Administrator vs. Regular User Roles  (HIGH) ──────────
    # Administrator is a NetSuite role, not a permission. Maps to None.
    ("SOD-IT-001", 0, "left",  "Administrator",
     None, "Edit",
     "Administrator is a NetSuite role, not a permission within a role"),
    ("SOD-IT-001", 0, "right", "AP Clerk",
     "Bills", "Edit",
     "Bills at Edit = AP Clerk function proxy"),
    ("SOD-IT-001", 1, "left",  "Administrator",
     None, "Edit",
     "Administrator is a NetSuite role, not a permission within a role"),
    ("SOD-IT-001", 1, "right", "AR Clerk",
     "Invoice Approval", "Edit",
     "Invoice Approval at Edit = AR Clerk function proxy"),

    # ── SOD-IT-002  Script Development vs. Production Execution  (HIGH) ───
    ("SOD-IT-002", 0, "left",  "SuiteScript Developer",
     "SuiteScript", "Edit",
     "SuiteScript at Edit = can write/modify scripts"),
    ("SOD-IT-002", 0, "right", "SuiteScript Deploy",
     "SuiteScript", "Full",
     "SuiteScript at Full = can deploy scripts to production"),
    ("SOD-IT-002", 1, "left",  "Customize SuiteScript",
     "SuiteScript", "Edit",
     "SuiteScript at Edit = can customise scripts"),
    ("SOD-IT-002", 1, "right", "Production Script Execution",
     "SuiteScript", "Full",
     "SuiteScript at Full = production execution rights"),

    # ── SOD-PROC-001  Purchase Order Creation vs. Approval  (HIGH) ────────
    ("SOD-PROC-001", 0, "left",  "Create Purchase Order",
     "Purchase Order", "Edit",
     "Purchase Order at Edit/Full = can create POs"),
    ("SOD-PROC-001", 0, "right", "Approve Purchase Order",
     "Bill Purchase Orders", "Edit",
     "Bill Purchase Orders at Edit/Full = converts PO to bill (acts as approval)"),
    ("SOD-PROC-001", 1, "left",  "Edit Purchase Order",
     "Purchase Order", "Edit",
     "Purchase Order at Edit/Full = can modify POs"),
    ("SOD-PROC-001", 1, "right", "Approve Purchase Order",
     "Bill Purchase Orders", "Edit",
     "Bill Purchase Orders at Edit/Full = converts PO to bill (acts as approval)"),

    # ── SOD-SALES-002  Sales Commission Setup vs. Processing  (HIGH) ──────
    ("SOD-SALES-002", 0, "left",  "Edit Commission Plan",
     None, "Edit",
     "No Fivetran role has commission plan edit permissions"),
    ("SOD-SALES-002", 0, "right", "Process Commission",
     None, "Edit",
     "No Fivetran role has commission processing permissions"),
    ("SOD-SALES-002", 1, "left",  "Override Commission Rate",
     None, "Edit",
     "No Fivetran role has commission rate override permissions"),
    ("SOD-SALES-002", 1, "right", "Approve Commission Payment",
     None, "Edit",
     "No Fivetran role has commission payment approval permissions"),

    # ── SOD-FIN-004  Customer Credit Management vs. Collections  (MEDIUM) ─
    ("SOD-FIN-004", 0, "left",  "Edit Customer Credit Limit",
     "Customers", "Edit",
     "Customers at Edit/Full = can modify credit limits"),
    ("SOD-FIN-004", 0, "right", "Apply Customer Payment",
     "Customer Payment", "Edit",
     "Customer Payment at Edit/Full = can apply payments (collections function)"),
    ("SOD-FIN-004", 1, "left",  "Edit Customer Credit Limit",
     "Customers", "Edit",
     "Customers at Edit/Full = can modify credit limits"),
    ("SOD-FIN-004", 1, "right", "Create Credit Memo",
     "Credit Memo", "Edit",
     "Credit Memo at Edit/Full = can create credit memos"),

    # ── SOD-FIN-006  Inventory Adjustments vs. Warehouse Operations  (MEDIUM)
    ("SOD-FIN-006", 0, "left",  "Inventory Adjustment",
     None, "Edit",
     "No Fivetran role has inventory adjustment permissions"),
    ("SOD-FIN-006", 0, "right", "Fulfill Sales Order",
     None, "Edit",
     "No Fivetran role has order fulfillment permissions"),
    ("SOD-FIN-006", 1, "left",  "Inventory Adjustment",
     None, "Edit",
     "No Fivetran role has inventory adjustment permissions"),
    ("SOD-FIN-006", 1, "right", "Receive Purchase Order",
     None, "Edit",
     "No Fivetran role has PO receipt permissions"),

    # ── SOD-FIN-008  Budget Creation vs. Budget Approval  (MEDIUM) ────────
    ("SOD-FIN-008", 0, "left",  "Create Budget",
     "Set Up Budgets", "Edit",
     "Set Up Budgets at Edit/Full = can create budgets"),
    ("SOD-FIN-008", 0, "right", "Approve Budget",
     "Budget", "Edit",
     "Budget at Edit/Full = can approve/finalize budgets"),
    ("SOD-FIN-008", 1, "left",  "Edit Budget",
     "Set Up Budgets", "Edit",
     "Set Up Budgets at Edit/Full = can modify budgets"),
    ("SOD-FIN-008", 1, "right", "Finalize Budget",
     "Budget", "Edit",
     "Budget at Edit/Full = can finalize budgets"),

    # ── SOD-IT-003  User Administration vs. Business Operations  (MEDIUM) ─
    ("SOD-IT-003", 0, "left",  "User Administration",
     None, "Edit",
     "No Fivetran role has user administration permissions"),
    ("SOD-IT-003", 0, "right", "Financial Transactions",
     "Bills", "Edit",
     "Bills at Edit/Full = financial transaction processing"),
    ("SOD-IT-003", 1, "left",  "Create User",
     None, "Edit",
     "No Fivetran role has user creation permissions"),
    ("SOD-IT-003", 1, "right", "Process Payments",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = processing payments"),
    ("SOD-IT-003", 2, "left",  "Edit User Roles",
     None, "Edit",
     "No Fivetran role has role assignment permissions"),
    ("SOD-IT-003", 2, "right", "Approve Financial Documents",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval at Edit/Full = approving financial documents"),

    # ── SOD-IT-004  Custom Record Definition vs. Data Entry  (MEDIUM) ─────
    ("SOD-IT-004", 0, "left",  "Customize Custom Records",
     "Custom Record Types", "Edit",
     "Custom Record Types at Edit/Full = can define custom record schemas"),
    ("SOD-IT-004", 0, "right", "Mass Update Records",
     None, "Edit",
     "No Fivetran role has mass update permissions at qualifying level"),
    ("SOD-IT-004", 1, "left",  "Define Custom Record Type",
     "Custom Record Types", "Edit",
     "Custom Record Types at Edit/Full = can define custom record schemas"),
    ("SOD-IT-004", 1, "right", "CSV Import",
     None, "Edit",
     "No Fivetran role has CSV import permissions at qualifying level"),

    # ── SOD-SALES-001  Pricing Maintenance vs. Sales Order Entry  (MEDIUM) ─
    ("SOD-SALES-001", 0, "left",  "Edit Item Price",
     None, "Edit",
     "No Fivetran role has item pricing permissions"),
    ("SOD-SALES-001", 0, "right", "Create Sales Order",
     None, "Edit",
     "No Fivetran role has sales order entry permissions"),
    ("SOD-SALES-001", 1, "left",  "Edit Pricing Discounts",
     None, "Edit",
     "No Fivetran role has discount edit permissions"),
    ("SOD-SALES-001", 1, "right", "Apply Manual Discount",
     None, "Edit",
     "No Fivetran role has manual discount permissions"),

    # ── SOD-RULE-001  Transaction Entry vs. Transaction Approval  (CRITICAL)
    ("SOD-RULE-001", 0, "left",  "Transaction Entry",
     "Make Journal Entry", "Edit",
     "Make Journal Entry at Edit/Full = primary transaction entry permission"),
    ("SOD-RULE-001", 0, "right", "Transaction Approval",
     "Journal Approval", "Edit",
     "Journal Approval at Edit/Full = transaction approval permission"),
    ("SOD-RULE-001", 1, "left",  "Transaction Entry",
     "Bills", "Edit",
     "Bills at Edit/Full = AP transaction entry"),
    ("SOD-RULE-001", 1, "right", "Transaction Approval",
     "Vendor Bill Approval", "Edit",
     "Vendor Bill Approval at Edit/Full = AP transaction approval"),

    # ── SOD-RULE-002  Transaction Entry vs. Transaction Payment  (CRITICAL) ─
    ("SOD-RULE-002", 0, "left",  "Transaction Entry",
     "Bills", "Edit",
     "Bills at Edit/Full = can enter/create vendor bills"),
    ("SOD-RULE-002", 0, "right", "Transaction Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can pay those same bills"),

    # ── SOD-RULE-003  Transaction Payment vs. Bank Reconciliation  (CRITICAL)
    ("SOD-RULE-003", 0, "left",  "Transaction Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = initiates payments"),
    ("SOD-RULE-003", 0, "right", "Bank Reconciliation",
     "Reconcile", "Edit",
     "Reconcile at Edit/Full = reconciles the accounts affected by those payments"),

    # ── SOD-RULE-004  Vendor Setup vs. Transaction Payment  (CRITICAL) ────
    ("SOD-RULE-004", 0, "left",  "Vendor Setup",
     "Vendors", "Edit",
     "Vendors at Edit/Full = can create or modify vendor records"),
    ("SOD-RULE-004", 0, "right", "Transaction Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can pay bills to vendors they just set up"),

    # ── SOD-RULE-005  User Admin vs. Transaction Payment  (CRITICAL) ──────
    ("SOD-RULE-005", 0, "left",  "User Administration",
     None, "Edit",
     "No Fivetran role has user administration permissions"),
    ("SOD-RULE-005", 0, "right", "Transaction Payment",
     "Pay Bills", "Edit",
     "Pay Bills at Edit/Full = can execute payments"),

    # ── SOD-RULE-006  User Admin vs. Role Admin  (CRITICAL) ───────────────
    ("SOD-RULE-006", 0, "left",  "User Administration",
     None, "Edit",
     "No Fivetran role has user administration permissions"),
    ("SOD-RULE-006", 0, "right", "Role Administration",
     None, "Edit",
     "No Fivetran role has role administration permissions"),
]


def run_migrations(session):
    """Run migrations 008 and 009 (idempotent via IF NOT EXISTS)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for num in ("008_add_sod_permission_map", "009_add_role_pair_conflicts"):
        path = os.path.join(base, "database", "migrations", f"{num}.sql")
        log.info(f"Running migration: {num}")
        with open(path) as f:
            sql = f.read()
        # Split on semicolons and execute each statement.
        # Strip leading comment lines from each block before checking if it
        # contains executable SQL (a block that starts with "--" comments but
        # also contains a DDL statement must not be silently dropped).
        for raw_stmt in sql.split(";"):
            lines = [ln for ln in raw_stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
            stmt = "\n".join(lines).strip()
            if stmt:
                session.execute(text(stmt))
    session.commit()
    log.info("Migrations complete")


def populate_permission_map(session):
    """Populate sod_permission_map from seed data."""
    log.info("Populating sod_permission_map...")

    # Build rule_id lookup by rule_id string
    rules = session.execute(text("SELECT id, rule_id FROM sod_rules")).fetchall()
    rule_uuid = {r.rule_id: str(r.id) for r in rules}

    inserted = 0
    skipped = 0
    for (rule_id_str, conflict_idx, side, abstract_name,
         ns_perm, min_level, note) in PERMISSION_MAP_SEED:

        if rule_id_str not in rule_uuid:
            log.warning(f"  Rule not found: {rule_id_str} — skipping")
            skipped += 1
            continue

        session.execute(text("""
            INSERT INTO sod_permission_map
                (rule_id, conflict_index, side, abstract_name,
                 ns_permission, min_level, note)
            VALUES
                (:rule_id, :conflict_index, :side, :abstract_name,
                 :ns_permission, :min_level, :note)
            ON CONFLICT (rule_id, conflict_index, side) DO UPDATE SET
                abstract_name  = EXCLUDED.abstract_name,
                ns_permission  = EXCLUDED.ns_permission,
                min_level      = EXCLUDED.min_level,
                note           = EXCLUDED.note
        """), {
            "rule_id": rule_uuid[rule_id_str],
            "conflict_index": conflict_idx,
            "side": side,
            "abstract_name": abstract_name,
            "ns_permission": ns_perm,
            "min_level": min_level,
            "note": note,
        })
        inserted += 1

    session.commit()
    log.info(f"  sod_permission_map: {inserted} rows upserted, {skipped} skipped")


def patch_empty_sod_rules(session):
    """
    Fill conflicting_permissions for the 6 SOD-RULE-00x rules that have
    empty JSON. These are used for display/context; the permission_map is
    the authoritative source for analysis.
    """
    patches = {
        "SOD-RULE-001": {"conflicts": [
            ["Transaction Entry", "Transaction Approval"]
        ]},
        "SOD-RULE-002": {"conflicts": [
            ["Transaction Entry", "Transaction Payment"]
        ]},
        "SOD-RULE-003": {"conflicts": [
            ["Transaction Payment", "Bank Reconciliation"]
        ]},
        "SOD-RULE-004": {"conflicts": [
            ["Vendor Setup", "Transaction Payment"]
        ]},
        "SOD-RULE-005": {"conflicts": [
            ["User Administration", "Transaction Payment"]
        ]},
        "SOD-RULE-006": {"conflicts": [
            ["User Administration", "Role Administration"]
        ]},
    }
    for rule_id_str, perms in patches.items():
        session.execute(text("""
            UPDATE sod_rules
            SET conflicting_permissions = :perms
            WHERE rule_id = :rule_id
            AND (conflicting_permissions IS NULL
                 OR conflicting_permissions::text = '{}')
        """), {"rule_id": rule_id_str, "perms": json.dumps(perms)})
    session.commit()
    log.info(f"  Patched {len(patches)} empty SOD rules")


def load_fivetran_roles(session):
    """
    Returns dict: role_id → {name, permissions: {perm_name: level}}
    """
    rows = session.execute(text("""
        SELECT role_id, role_name, permissions
        FROM roles
        WHERE role_name ILIKE 'Fivetran%'
        ORDER BY role_name
    """)).fetchall()

    roles = {}
    for row in rows:
        perm_map = {}
        if row.permissions:
            perms = row.permissions if isinstance(row.permissions, list) else json.loads(row.permissions)
            for p in perms:
                pname = p.get("permission_name", "")
                level = p.get("level", "None")
                if pname:
                    perm_map[pname] = level
        roles[row.role_id] = {"name": row.role_name, "permissions": perm_map}

    log.info(f"  Loaded {len(roles)} Fivetran roles")
    return roles


def load_sod_rules_with_map(session):
    """
    Returns list of rules, each with their permission_map entries:
    [{rule_uuid, rule_id_str, rule_name, severity,
      pairs: [(left_ns, left_min, right_ns, right_min), ...]}, ...]
    """
    rules_raw = session.execute(text("""
        SELECT id, rule_id, rule_name, severity
        FROM sod_rules
        WHERE is_active = true
        ORDER BY rule_id
    """)).fetchall()

    map_rows = session.execute(text("""
        SELECT rule_id, conflict_index, side, ns_permission, min_level
        FROM sod_permission_map
        ORDER BY rule_id, conflict_index, side
    """)).fetchall()

    # Group map rows by (rule_id, conflict_index)
    from collections import defaultdict
    pair_map = defaultdict(dict)
    for r in map_rows:
        pair_map[(str(r.rule_id), r.conflict_index)][r.side] = (r.ns_permission, r.min_level)

    rules = []
    for rule in rules_raw:
        # Find all conflict_index values for this rule
        rule_pairs = []
        idx = 0
        while True:
            key = (str(rule.id), idx)
            if key not in pair_map:
                break
            entry = pair_map[key]
            left_ns, left_min = entry.get("left", (None, "Edit"))
            right_ns, right_min = entry.get("right", (None, "Edit"))
            rule_pairs.append((left_ns, left_min, right_ns, right_min))
            idx += 1

        if rule_pairs:
            rules.append({
                "uuid": str(rule.id),
                "rule_id": rule.rule_id,
                "name": rule.rule_name,
                "severity": rule.severity if isinstance(rule.severity, str) else rule.severity.value,
                "pairs": rule_pairs,
            })

    log.info(f"  Loaded {len(rules)} active SOD rules with permission map entries")
    return rules


def check_conflict(role_a_perms, role_b_perms,
                   left_ns, left_min, right_ns, right_min):
    """
    Returns (a_level, b_level) if role_a has left permission at ≥ left_min
    AND role_b has right permission at ≥ right_min. Otherwise None.
    Both ns_permission values must be non-None.
    """
    if left_ns is None or right_ns is None:
        return None
    a_level = role_a_perms.get(left_ns)
    b_level = role_b_perms.get(right_ns)
    if a_level is None or b_level is None:
        return None
    if level_gte(a_level, left_min) and level_gte(b_level, right_min):
        return (a_level, b_level)
    return None


def build_matrix(session, roles, rules):
    """
    For every pair (A, B) — including self-pairs — evaluate every SOD rule
    and write conflicts to role_pair_conflicts.
    """
    log.info("Building role pair conflict matrix...")

    role_ids = list(roles.keys())
    # Generate all unique pairs including self-pairs
    pairs = []
    for i, a in enumerate(role_ids):
        for b in role_ids[i:]:          # b >= a alphabetically (by list order)
            pairs.append((a, b))

    log.info(f"  Evaluating {len(pairs)} role pairs × {len(rules)} rules...")

    conflicts_written = 0
    for role_a_id, role_b_id in pairs:
        role_a = roles[role_a_id]
        role_b = roles[role_b_id]
        is_intra = (role_a_id == role_b_id)

        for rule in rules:
            for (left_ns, left_min, right_ns, right_min) in rule["pairs"]:

                # Direction 1: A holds left side, B holds right side
                result = check_conflict(
                    role_a["permissions"], role_b["permissions"],
                    left_ns, left_min, right_ns, right_min
                )
                if result:
                    a_level, b_level = result
                    _upsert_conflict(
                        session,
                        role_a_id, role_a["name"],
                        role_b_id, role_b["name"],
                        rule, left_ns, a_level, right_ns, b_level,
                        is_intra
                    )
                    conflicts_written += 1

                # Direction 2: A holds right side, B holds left side
                # (skip for self-pairs — already covered above)
                if not is_intra:
                    result2 = check_conflict(
                        role_b["permissions"], role_a["permissions"],
                        left_ns, left_min, right_ns, right_min
                    )
                    if result2:
                        b_level2, a_level2 = result2
                        # Normalise: store with lexically-first role as role_a
                        if role_a_id <= role_b_id:
                            _upsert_conflict(
                                session,
                                role_a_id, role_a["name"],
                                role_b_id, role_b["name"],
                                rule, right_ns, a_level2, left_ns, b_level2,
                                False
                            )
                        else:
                            _upsert_conflict(
                                session,
                                role_b_id, role_b["name"],
                                role_a_id, role_a["name"],
                                rule, left_ns, b_level2, right_ns, a_level2,
                                False
                            )
                        conflicts_written += 1

    session.commit()
    log.info(f"  Wrote {conflicts_written} conflict rows to role_pair_conflicts")
    return conflicts_written


def _upsert_conflict(session, role_a_id, role_a_name,
                     role_b_id, role_b_name,
                     rule, perm_a, level_a, perm_b, level_b, is_intra):
    if is_intra:
        desc = (f"{role_a_name}: {perm_a}({level_a}) conflicts with "
                f"{perm_b}({level_b}) — {rule['name']}")
    else:
        desc = (f"{role_a_name}.{perm_a}({level_a}) ↔ "
                f"{role_b_name}.{perm_b}({level_b}) — {rule['name']}")

    session.execute(text("""
        INSERT INTO role_pair_conflicts
            (role_a_id, role_b_id, role_a_name, role_b_name,
             rule_id, rule_name, severity,
             role_a_permission, role_a_level,
             role_b_permission, role_b_level,
             is_intra_role, conflict_description, analyzed_at)
        VALUES
            (:role_a_id, :role_b_id, :role_a_name, :role_b_name,
             :rule_id, :rule_name, :severity,
             :perm_a, :level_a, :perm_b, :level_b,
             :is_intra, :desc, NOW())
        ON CONFLICT (role_a_id, role_b_id, rule_id, role_a_permission, role_b_permission)
        DO UPDATE SET
            role_a_level         = EXCLUDED.role_a_level,
            role_b_level         = EXCLUDED.role_b_level,
            conflict_description = EXCLUDED.conflict_description,
            analyzed_at          = EXCLUDED.analyzed_at
    """), {
        "role_a_id": role_a_id, "role_b_id": role_b_id,
        "role_a_name": role_a_name, "role_b_name": role_b_name,
        "rule_id": rule["uuid"], "rule_name": rule["name"],
        "severity": rule["severity"],
        "perm_a": perm_a, "level_a": level_a,
        "perm_b": perm_b, "level_b": level_b,
        "is_intra": is_intra, "desc": desc,
    })


def print_summary(session):
    """Print a quick summary of what was built."""
    rows = session.execute(text("""
        SELECT
            role_a_name,
            role_b_name,
            is_intra_role,
            severity,
            COUNT(*) as conflict_count
        FROM role_pair_conflicts
        GROUP BY role_a_name, role_b_name, is_intra_role, severity
        ORDER BY
            CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                          WHEN 'MEDIUM' THEN 3 ELSE 4 END,
            role_a_name, role_b_name
    """)).fetchall()

    log.info("\n=== ROLE RISK MATRIX SUMMARY ===")
    current_pair = None
    for r in rows:
        pair = (r.role_a_name, r.role_b_name)
        if pair != current_pair:
            kind = "INTRA-ROLE" if r.is_intra_role else "CROSS-ROLE"
            log.info(f"\n  [{kind}] {r.role_a_name}"
                     + ("" if r.is_intra_role else f" + {r.role_b_name}"))
            current_pair = pair
        log.info(f"    {r.severity}: {r.conflict_count} conflict(s)")

    total = session.execute(text("SELECT COUNT(*) FROM role_pair_conflicts")).scalar()
    intra = session.execute(text("SELECT COUNT(*) FROM role_pair_conflicts WHERE is_intra_role")).scalar()
    cross = total - intra
    log.info(f"\n  Total: {total} rows  |  Intra-role: {intra}  |  Cross-role: {cross}")


def main():
    log.info("=== build_role_risk_matrix.py starting ===")
    start = datetime.utcnow()

    db = DatabaseConfig()
    session = db.get_session()

    try:
        log.info("Step 1/5: Running migrations...")
        run_migrations(session)

        log.info("Step 2/5: Populating sod_permission_map...")
        populate_permission_map(session)

        log.info("Step 3/5: Patching empty SOD rules...")
        patch_empty_sod_rules(session)

        log.info("Step 4/5: Loading roles and rules...")
        roles = load_fivetran_roles(session)
        rules = load_sod_rules_with_map(session)

        log.info("Step 5/5: Building role pair conflict matrix...")
        # Clear old rows first for a clean rebuild
        session.execute(text("TRUNCATE TABLE role_pair_conflicts"))
        session.commit()
        n = build_matrix(session, roles, rules)

        print_summary(session)

        elapsed = (datetime.utcnow() - start).total_seconds()
        log.info(f"\n=== Complete in {elapsed:.1f}s — {n} conflict rows written ===")

    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
