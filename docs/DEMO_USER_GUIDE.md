# Demo User Guide for External Presentations

**Purpose:** Sanitized test user for external demos without company branding.

---

## Demo User Details

| Field | Value | Notes |
|-------|-------|-------|
| **Name** | Test User | Generic name |
| **Email** | test_user@xyz.com | Sanitized domain |
| **Department** | G&A : Finance | No "Fivetran" prefix |
| **Title** | Assistant Controller | Unchanged |
| **Roles** | 3 roles | Sanitized names |
| **Violations** | 384 total | Same count as Robin Turner |

### Roles (Sanitized)

| Original Role | Sanitized Role |
|--------------|----------------|
| Fivetran - Controller | **Controller** |
| Administrator | Administrator |
| NetSuite 360 – Plus Financials | NetSuite 360 – Plus Financials |

### Violations Breakdown

- 🔴 **CRITICAL**: 96
- 🟠 **HIGH**: 128
- 🟡 **MEDIUM**: 160
- 🟢 **LOW**: 0

---

## Usage in Demos

### External Demo (Sanitized Data)

Use `test_user@xyz.com` for external presentations:

```
"Show me violations for test_user@xyz.com"
"Generate violation report for Test User"
"What are the top SOD violations for test_user@xyz.com?"
"Export Test User's violations to Excel"
```

**Result:** All data shows without "Fivetran" branding ✅

### Internal Demo (Real Data)

Use real user emails for internal demos:

```
"Show me violations for robin.turner@fivetran.com"
"Generate violation report for Robin Turner"
"What are Finance department violations?"
```

**Result:** Shows actual company data with "Fivetran" branding ✅

---

## Comparison: Real vs Demo User

### Robin Turner (Real User)
```json
{
  "name": "Robin Turner",
  "email": "robin.turner@fivetran.com",
  "department": "Fivetran : G&A : Finance",
  "roles": [
    "Fivetran - Controller",
    "Administrator",
    "NetSuite 360 – Plus Financials"
  ],
  "violations": 384
}
```

### Test User (Demo User)
```json
{
  "name": "Test User",
  "email": "test_user@xyz.com",
  "department": "G&A : Finance",
  "roles": [
    "Controller",
    "Administrator",
    "NetSuite 360 – Plus Financials"
  ],
  "violations": 384
}
```

---

## Sample Demo Script

### 1. Show User Overview
```
"Who is Test User and what roles do they have?"
```

**Expected Output:**
- Name: Test User
- Email: test_user@xyz.com
- Department: G&A : Finance
- Roles: Controller, Administrator, NetSuite 360
- Status: Active

### 2. Show Violation Report
```
"Generate a violation report for test_user@xyz.com"
```

**Expected Output:**
- Top 5 violations in markdown table
- Severity breakdown (96 CRITICAL, 128 HIGH, 160 MEDIUM)
- No "Fivetran" anywhere in output

### 3. Export to Excel
```
"Export Test User's violations to Excel"
```

**Expected Output:**
- Excel file: `/tmp/compliance_reports/violations_Test_User_[timestamp].xlsx`
- All 384 violations
- Color-coded by severity
- Sanitized role names throughout

### 4. Compare with Department
```
"List users in Finance department"
```

**Expected Output:**
- Shows both Test User (sanitized) and real users
- Test User appears with sanitized data
- Real users appear with actual data

---

## Management Commands

### Create Demo User
```bash
cd compliance-agent
python3 scripts/create_demo_user.py --create
```

**Options:**
```bash
# Custom name and email
python3 scripts/create_demo_user.py --create \
  --name "Jane Smith" \
  --email "jane.smith@acme.com" \
  --source "robin.turner@fivetran.com"

# Copy from different source user
python3 scripts/create_demo_user.py --create \
  --source "chase.roles@fivetran.com"
```

### Delete Demo User
```bash
python3 scripts/create_demo_user.py --delete --email "test_user@xyz.com"
```

### Recreate Demo User
```bash
# Delete and recreate (updates to latest data)
python3 scripts/create_demo_user.py --delete
python3 scripts/create_demo_user.py --create
```

---

## What Gets Sanitized

### Text Replacements

| Original | Sanitized |
|----------|-----------|
| `Fivetran -` | _(removed)_ |
| `Fivetran :` | _(removed)_ |
| `fivetran.com` | `xyz.com` |
| `Fivetran` | `Company` |

### Data Sanitized

✅ **User Profile:**
- Email domain
- Department name
- Company references

✅ **Roles:**
- Role names (prefix removed)
- Role references in violations

✅ **Violations:**
- Violation descriptions
- Conflicting role names
- Conflicting permission names

❌ **NOT Sanitized:**
- Job titles (kept as-is)
- Violation types (generic already)
- Severity levels
- Risk scores

---

## Best Practices

### For External Demos

1. **Always use test_user@xyz.com** to avoid showing real employee data
2. **Clear browser cache** before demo to avoid autofill of real emails
3. **Test the demo flow** beforehand to ensure sanitization works
4. **Prepare screenshots** in advance for presentations
5. **Don't export to shared drives** - Excel files may contain traces

### For Internal Demos

1. **Use real user emails** to show actual compliance status
2. **Explain RBAC features** with real role names for context
3. **Show both sanitized and real** data to demonstrate flexibility
4. **Highlight violation patterns** relevant to your organization

### Security Notes

⚠️ **Demo user is NOT for production use**
- Contains copied data from real users
- Does not sync with NetSuite
- Manually managed (not auto-updated)
- Should be deleted after demo if security is a concern

---

## Troubleshooting

### Issue: Demo user shows "Fivetran" in output

**Cause:** Old data not sanitized properly

**Fix:**
```bash
# Recreate demo user
python3 scripts/create_demo_user.py --delete
python3 scripts/create_demo_user.py --create
```

### Issue: Violation count doesn't match

**Cause:** Source user's violations changed since demo user creation

**Fix:** Recreate demo user to sync with latest data

### Issue: Can't find demo user

**Check if user exists:**
```sql
psql $DATABASE_URL -c "SELECT name, email FROM users WHERE email = 'test_user@xyz.com';"
```

**Recreate if missing:**
```bash
python3 scripts/create_demo_user.py --create
```

---

## Quick Reference

### Test Commands

```bash
# In Claude UI
"Show violations for test_user@xyz.com"
"List Finance users"
"Generate report for test_user@xyz.com format=markdown"
"Export test_user@xyz.com violations to Excel"
```

### Management Commands

```bash
# Create
python3 scripts/create_demo_user.py --create

# Delete
python3 scripts/create_demo_user.py --delete

# Custom
python3 scripts/create_demo_user.py --create \
  --name "Demo User" \
  --email "demo@example.com" \
  --source "robin.turner@fivetran.com"
```

---

**Last Updated:** 2026-02-14
**Status:** ✅ Production Ready
**Demo User:** test_user@xyz.com
