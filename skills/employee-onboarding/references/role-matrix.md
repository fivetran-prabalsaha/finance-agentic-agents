# Role Matrix — Standard Role Sets by Job Title

Use this reference to determine the correct Okta groups and NetSuite roles for a new employee
without making a tool call. For real-time validation, always confirm with
`recommend_roles_for_job_title(job_title, department)`.

---

## Finance Department

| Job Title | Okta Groups | NetSuite Roles | Superuser? |
|---|---|---|---|
| AP Analyst | finance-users, netsuite-ap | AP Processor, Vendor Viewer | No |
| AR Analyst | finance-users, netsuite-ar | AR Processor, Customer Viewer | No |
| Senior Accountant | finance-users, netsuite-accounting | AP Processor, GL Viewer, Journal Entry | No |
| Accounting Manager | finance-users, netsuite-accounting, finance-approvers | AP Processor, AP Approval, GL Viewer | No — requires SOD check |
| Controller | finance-users, finance-approvers, netsuite-controller | Controller, AP Approval, GL Full Access | Yes — ticket required |
| CFO | finance-users, finance-approvers, netsuite-executive | Full Access Finance, Reporting Full | Yes — ticket required |

---

## IT Department

| Job Title | Okta Groups | NetSuite Roles | Superuser? |
|---|---|---|---|
| IT Analyst | it-users, netsuite-readonly | Employee Center, Basic Viewer | No |
| IT Systems Admin | it-users, it-admins, netsuite-it | NetSuite Admin, Script Viewer | Yes — ticket required |
| NetSuite Developer | it-users, it-admins, netsuite-dev | SuiteScript Developer, Sandbox Access | Yes — ticket required |
| Security Engineer | it-users, it-security | Audit Log Viewer, Security Viewer | No |
| IT Director | it-users, it-admins, it-approvers | NetSuite Admin, Full System Access | Yes — ticket required |

---

## Sales Department

| Job Title | Okta Groups | NetSuite Roles | Superuser? |
|---|---|---|---|
| Sales Rep | sales-users, netsuite-crm | Sales Rep, CRM Full Access, Quote Creator | No |
| Sales Manager | sales-users, sales-managers, netsuite-crm | Sales Manager, CRM Full Access, Forecast Viewer | No |
| Sales Director | sales-users, sales-managers, netsuite-crm | Sales Director, Revenue Viewer | No |
| VP Sales | sales-users, sales-managers, netsuite-executive | Sales Full Access, Revenue Full Access | Yes — ticket required |

---

## Operations / Procurement

| Job Title | Okta Groups | NetSuite Roles | Superuser? |
|---|---|---|---|
| Procurement Analyst | ops-users, netsuite-procurement | PO Creator, Vendor Viewer | No |
| Procurement Manager | ops-users, ops-approvers, netsuite-procurement | PO Creator, PO Approval, Vendor Viewer | No — requires SOD check |
| Inventory Analyst | ops-users, netsuite-inventory | Inventory Viewer, Inventory Adjust | No |

---

## Compliance / Audit

| Job Title | Okta Groups | NetSuite Roles | Superuser? |
|---|---|---|---|
| Compliance Analyst | compliance-users, netsuite-audit | Audit Log Viewer, Report Viewer | No |
| Compliance Officer | compliance-users, compliance-approvers, netsuite-audit | Compliance Full Access, Audit Log Viewer | No — independence required |
| Internal Auditor | compliance-users, netsuite-audit | Audit Log Viewer, Read-Only Full | No |

---

## Superuser Definition

A user is classified as **superuser** if their role set includes any of:
- NetSuite Administrator
- Controller
- Full Access (any module)
- Script Developer / Deploy
- SuiteScript Developer
- CFO / Executive access roles

These require a Jira approval ticket before NetSuite enablement.

---

## SOD-Sensitive Role Combinations

Always run `analyze_access_request` before assigning these combinations — even if the matrix lists them as standard:

- Any role in Finance + AP Approval authority
- Accounting Manager (has both AP Processor and AP Approval)
- Procurement Manager (has both PO Creator and PO Approval)
- IT Admin + any Finance role
- Compliance Officer + any operational Finance role (independence violation)
