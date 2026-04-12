# Approval Authority Matrix

Defines who can approve NetSuite role assignments based on requester authority level and SOD risk.

---

## Authority Levels

| Level | Title Examples | Can Approve |
|---|---|---|
| L1 | Regular Employee, IT Analyst, Contractor | Request only — cannot approve any role |
| L2 | Manager, Team Lead | LOW risk roles only |
| L3 | Senior Manager, Director | LOW and MEDIUM risk roles |
| L4 | Controller, VP Finance, IT Director | LOW, MEDIUM, and HIGH risk roles |
| L5 | CFO, CEO, C-Suite | All including CRITICAL |

---

## Role Risk Tiers → Minimum Approver Required

| Role Type | Examples | Min Approver |
|---|---|---|
| Read-only / Viewer | Report-Viewer, Employee-Center | L2 (Manager) |
| Operational | AP-Processor, PO-Creator, Sales-Rep | L2 (Manager) |
| Approval authority | AP-Approver, PO-Approver, Expense-Approver | L4 (Controller) |
| Financial full access | GL-Full-Access, Journal-Entry-Approval | L4 (Controller) |
| Controller / Executive | Fivetran-Controller, CFO-Access | L5 (CFO) |
| Admin / Script | NetSuite-Admin, SuiteScript-Developer | L4 (IT Director) |
| Compliance | Compliance-Full-Access, Audit-Log-Full | L4 (Compliance Officer) |

---

## SOD Risk Result → Minimum Approver Override

SOD risk always overrides the role tier if it requires a higher approver:

| SOD Result | Minimum Approver Override |
|---|---|
| CLEAR | No override — use role tier minimum |
| LOW | No override — use role tier minimum |
| MEDIUM | Minimum L3 (Director) |
| HIGH | Minimum L4 (Controller) |
| CRITICAL | Minimum L5 (CFO) — no exceptions |

---

## Special Rules (Pattern 5 — Domain Intelligence)

**Financial roles always route to Controller (L4) minimum**
Any role involving AP, GL, Journal Entry, or payment processing requires Controller approval
regardless of the requester's level or SOD result. This is a hard SOX control.

**Self-approval is never permitted**
If the requester and the target user are the same person, escalate to the requester's
direct manager minimum. Comment on the Jira ticket.

**Compliance Officer independence**
If the target user is a Compliance Officer, they cannot be assigned operational Finance roles.
Route to CFO + flag as a SOD independence violation.

**Dual approval for CRITICAL roles**
Controller-level and above roles require two approvals: the direct manager AND the Controller.
Both must comment "Approved" on the Jira ticket before the agent executes.

---

## Routing Quick Reference

```
Requester raises Jira ticket
         │
         ▼
Is it a financial/approval role?
  YES → Minimum: Controller (L4)
  NO  ↓
         ▼
What is the SOD result?
  CRITICAL → CFO (L5)
  HIGH     → Controller (L4)
  MEDIUM   → Director (L3)
  LOW/CLEAR → Manager (L2)
         │
         ▼
Is requester authority ≥ required level?
  YES → Requester approves + Controller cc'd for audit trail
  NO  → Route to next authority level above requester
```
