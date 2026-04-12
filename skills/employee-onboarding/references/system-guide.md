# System Integration Guide — Onboarding Workflow

API endpoints, field mappings, and error codes for each system in the onboarding chain.

---

## Okta

**Base URL:** `https://celigo.okta.com/api/v1`
**Auth:** Bearer token (OKTA_API_TOKEN env var)

### Key Endpoints

| Action | Method | Endpoint |
|---|---|---|
| Create user | POST | `/users?activate=true` |
| Get user by email | GET | `/users?q={email}` |
| Get user by ID | GET | `/users/{userId}` |
| Assign to group | PUT | `/groups/{groupId}/users/{userId}` |
| Deactivate user | POST | `/users/{userId}/lifecycle/deactivate` |

### Create User Payload

```json
{
  "profile": {
    "firstName": "Sarah",
    "lastName": "Chen",
    "email": "sarah.chen@celigo.com",
    "login": "sarah.chen@celigo.com",
    "title": "Senior Accountant",
    "department": "Finance",
    "manager": "mike.torres@celigo.com",
    "userType": "standard"
  },
  "credentials": {
    "password": { "hook": { "type": "default" } }
  }
}
```

### User Status Flow
`STAGED` → `PROVISIONED` → `ACTIVE` → `DEPROVISIONED`

New users land in `PROVISIONED` after activation email is sent.
`ACTIVE` once the user sets their password and logs in.

### Common Errors

| Error | Cause | Fix |
|---|---|---|
| `E0000001` | API key invalid | Rotate OKTA_API_TOKEN |
| `E0000095` | Login already exists | User already in Okta — look up and link |
| `E0000112` | Group not found | Check group ID in references/role-matrix.md |

---

## Workday

**Base URL:** `https://wd2-impl-services1.workday.com/ccx/service/celigo`
**Auth:** Basic auth (WORKDAY_USER / WORKDAY_PASSWORD env vars)
**API Type:** SOAP / REST hybrid — use REST for employee lookups, SOAP for worker creation

### Key Operations

| Action | Endpoint |
|---|---|
| Create worker | `POST /staffing/v1/workers` |
| Get worker by email | `GET /workers?email={email}` |
| Update worker status | `PUT /workers/{workerId}/status` |

### Required Fields for Worker Creation

```json
{
  "workerType": "Employee",
  "hireDate": "2026-03-01",
  "jobTitle": "Senior Accountant",
  "department": "Finance",
  "costCenter": "CC-1042",
  "manager": { "email": "mike.torres@celigo.com" },
  "externalId": "{oktaUserId}"
}
```

### Common Errors

| Error | Cause | Fix |
|---|---|---|
| `VALIDATION_ERROR: manager` | Manager not found in Workday | Verify manager has active Workday record |
| `DUPLICATE_EMPLOYEE` | Employee already exists | Search by email, link to existing record |
| `INVALID_COST_CENTER` | Cost center code wrong | Check with Finance for correct CC code |

---

## Celigo

**Console:** https://integrator.io
**Sync Flow:** `Workday Employee → NetSuite Employee`

### Triggering a Manual Sync

1. Log in to Celigo integrator.io
2. Navigate to: Integrations → Workday-NetSuite → Employee Sync
3. Click "Run" and filter by `workerId`
4. Monitor the run dashboard for success/error status

### Field Mappings (Workday → NetSuite)

| Workday Field | NetSuite Field | Notes |
|---|---|---|
| `firstName` | `firstName` | Direct map |
| `lastName` | `lastName` | Direct map |
| `email` | `email` | Used as unique key |
| `jobTitle` | `title` | Direct map |
| `department` | `department` | Must match NetSuite department list |
| `hireDate` | `hireDate` | ISO date format |
| `workerType` | `entityId` type | `Employee` maps to Employee record (not Contact) |
| `externalId` (Okta) | `custentity_okta_id` | Custom field — must be mapped in Celigo |

### Common Sync Errors

| Error | Cause | Fix |
|---|---|---|
| `INVALID_KEY: department` | Department name doesn't match NetSuite list | Check NetSuite department list, update Workday record |
| `DUPLICATE_ENTITY` | Email already exists in NetSuite | Search NetSuite for existing record, merge if needed |
| `FIELD_REQUIRED: custentity_okta_id` | Custom field not in Celigo mapping | Add field to Celigo flow field mapping |
| Record created as Contact not Employee | `workerType` not mapped correctly | Check `entityId` type mapping in Celigo flow |

---

## NetSuite

**Base URL:** `https://5260239-sb1.restlets.api.netsuite.com` (sandbox)
**Auth:** OAuth 1.0 (credentials in .env)
**MCP Tools:** Available via compliance MCP server at localhost:8080

### Key MCP Tools for Onboarding

| Tool | Use |
|---|---|
| `get_user_violations(user_identifier)` | Confirm employee record exists; get internal ID and current roles |
| `recommend_roles_for_job_title(job_title, department)` | Get standard role set |
| `analyze_access_request(user_id, requested_role, include_existing_roles=true)` | SOD check before role assignment |
| `validate_job_role(user_id, job_title, proposed_roles)` | Final validation of role set |

### Enabling a User in NetSuite

Set `isInactive: false` on the Employee record via SuiteScript or direct REST call:

```
PATCH /services/rest/record/v1/employee/{internalId}
{ "isinactive": false }
```

### NetSuite Employee Status

| Status | Meaning |
|---|---|
| `isInactive: true` | Account exists but cannot log in — default for new records |
| `isInactive: false` | Account active — user can log in |

**Important:** New employees synced via Celigo arrive as `isInactive: true` by default.
Enablement (setting `isInactive: false`) is a deliberate manual step — do not automate without SOD clearance.

---

## Jira — Superuser Ticket

**Project Key:** `NS-ONBOARD`
**Board:** IT Access Management
**Assignee default:** it-security@celigo.com

### Ticket Template Fields

| Field | Value |
|---|---|
| `project.key` | `NS-ONBOARD` |
| `issuetype.name` | `Access Request` |
| `priority.name` | `High` |
| `labels` | `onboarding`, `superuser`, `netsuite-access` |
| `duedate` | Employee start date |

### SLA

Superuser tickets must be resolved within 2 business days of creation.
If unresolved by start date, notify IT Director and employee's manager.
