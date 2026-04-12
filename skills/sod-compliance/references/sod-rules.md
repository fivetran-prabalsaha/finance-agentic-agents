# SOD Rules Reference

18 active SOD rules in Celigo's compliance system.
Use this reference to quickly identify which rule applies without a tool call.
For full detail (conflicting permission pairs, compensating controls), call `get_sod_rule_details(rule_code=<code>)`.

---

## Financial Controls (8 rules)

| Code | Rule Name | Severity | Risk |
|------|-----------|----------|------|
| `AP_ENTRY_VS_AP_APPROVAL` | AP Entry vs AP Approval | CRITICAL | Same user creates and approves vendor invoices — direct payment fraud pathway |
| `VENDOR_CREATE_VS_VENDOR_APPROVE` | Vendor Master vs Vendor Approval | CRITICAL | Same user creates and approves new vendors — ghost vendor risk |
| `JOURNAL_ENTRY_VS_APPROVAL` | Journal Entry vs Journal Approval | CRITICAL | Same user posts and approves journal entries — financial misstatement risk |
| `PAYMENT_CREATE_VS_PAYMENT_APPROVE` | Payment Create vs Payment Approval | HIGH | Same user creates and approves outgoing payments |
| `PO_CREATE_VS_PO_APPROVE` | Purchase Order Create vs Approval | HIGH | Same user raises and approves purchase orders |
| `EXPENSE_SUBMIT_VS_APPROVE` | Expense Submit vs Expense Approval | HIGH | Same user submits and approves their own expense reports |
| `INVENTORY_ADJUST_VS_COUNT` | Inventory Adjustment vs Inventory Count | MEDIUM | Same user adjusts and physically counts inventory |
| `REVENUE_RECOGNIZE_VS_REVIEW` | Revenue Recognition vs Revenue Review | MEDIUM | Same user records and reviews revenue entries |

---

## Security Controls (5 rules)

| Code | Rule Name | Severity | Risk |
|------|-----------|----------|------|
| `ADMIN_VS_REGULAR_USER` | Admin Access vs Regular Operations | CRITICAL | Admin role combined with operational role — unlimited escalation risk |
| `SCRIPT_DEV_VS_PRODUCTION` | Script Development vs Production Deploy | HIGH | Same user writes and deploys NetSuite scripts to production |
| `USER_MGMT_VS_AUDIT_LOG` | User Management vs Audit Log Access | HIGH | Same user manages users and can access/modify audit logs |
| `ACCESS_GRANT_VS_ACCESS_REVIEW` | Access Grant vs Access Review | MEDIUM | Same user grants access and reviews access permissions |
| `SECURITY_CONFIG_VS_MONITORING` | Security Config vs Security Monitoring | MEDIUM | Same user configures and monitors security settings |

---

## Compliance Controls (5 rules)

| Code | Rule Name | Severity | Risk |
|------|-----------|----------|------|
| `COMPLIANCE_OFFICER_INDEPENDENCE` | Compliance Officer Role Independence | HIGH | Compliance officer also holds operational roles they are meant to audit |
| `AUDIT_LOG_ACCESS_VS_OPERATIONS` | Audit Log Access vs Operational Roles | HIGH | Same user performs transactions they can also access audit logs for |
| `SOX_CONTROL_OWNER_VS_TESTER` | SOX Control Owner vs Control Tester | HIGH | Same person owns and tests the same SOX control |
| `DATA_EXPORT_VS_DATA_MODIFY` | Data Export vs Data Modify | MEDIUM | Same user can export and modify sensitive data sets |
| `REPORT_CREATE_VS_REPORT_APPROVE` | Financial Report Create vs Approve | MEDIUM | Same user creates and approves financial reports sent to leadership |

---

## Severity Reference

| Severity | SLA | Action Required |
|----------|-----|-----------------|
| CRITICAL | Immediate | Block role assignment or escalate to CISO + CFO; remediate within 24h |
| HIGH | 30 days | Assign remediation owner; document compensating controls immediately |
| MEDIUM | 90 days | Schedule review; document compensating controls |
| LOW | 180 days | Document in next compliance cycle |

---

## Most Commonly Triggered Rules (by violation count in production)

1. `AP_ENTRY_VS_AP_APPROVAL` — Finance dept; legacy Controller + AP Processor role overlap
2. `JOURNAL_ENTRY_VS_APPROVAL` — Finance; Controller role grants both permissions
3. `ADMIN_VS_REGULAR_USER` — IT; power users with both NetSuite admin + operational access
4. `SCRIPT_DEV_VS_PRODUCTION` — IT; developers who also have production deploy rights
5. `COMPLIANCE_OFFICER_INDEPENDENCE` — Compliance; officers carrying legacy operational roles
