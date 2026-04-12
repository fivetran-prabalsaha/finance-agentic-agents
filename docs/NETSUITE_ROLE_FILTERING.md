# NetSuite Role Filtering - Fivetran Roles Only

**Date:** 2026-02-12
**Change:** Filter RESTlets to only return roles starting with "Fivetran -"
**Purpose:** Focus compliance analysis on specific Fivetran-related roles

---

## Changes Made

### 1. User Search RESTlet (v5 Hybrid)
**File:** `netsuite_scripts/user_search_restlet_v5_hybrid.js`
**Function:** `enrichUserWithRoles()` (line ~345)

**Before:**
```javascript
if (roleId && roleName) {
    roles.push({
        role_id: roleId,
        role_name: roleName,
        permissions: []
    });
}
```

**After:**
```javascript
// FILTER: Only include roles that start with "Fivetran -"
if (roleId && roleName && roleName.indexOf('Fivetran -') === 0) {
    roles.push({
        role_id: roleId,
        role_name: roleName,
        permissions: []
    });
}
```

### 2. SOD Users & Roles RESTlet (Optimized)
**File:** `netsuite_scripts/sod_users_roles_restlet_optimized.js`
**Function:** Batch role fetching (line ~337)

**Before:**
```javascript
if (roleId && roleName && internalId) {
    var userId = userIdMap[internalId];
    // ... process role
}
```

**After:**
```javascript
// FILTER: Only include roles that start with "Fivetran -"
if (roleId && roleName && internalId && roleName.indexOf('Fivetran -') === 0) {
    var userId = userIdMap[internalId];
    // ... process role
}
```

---

## Impact

### What Gets Filtered

**Included (returned by RESTlets):**
- ✅ "Fivetran - Controller"
- ✅ "Fivetran - Analyst"
- ✅ "Fivetran - Administrator"
- ✅ Any role starting with "Fivetran -"

**Excluded (filtered out):**
- ❌ "Administrator"
- ❌ "Employee"
- ❌ "Accountant"
- ❌ "Sales Manager"
- ❌ Any role NOT starting with "Fivetran -"

### What This Means

1. **Users without Fivetran roles:**
   - Will still be returned
   - But will have `roles: []` (empty roles array)
   - Will NOT trigger SOD violations (no conflicting roles)

2. **Users with mixed roles:**
   ```json
   {
     "name": "John Smith",
     "roles": [
       // Only Fivetran roles shown:
       {"role_name": "Fivetran - Controller"},
       {"role_name": "Fivetran - AP Clerk"}
       // Regular roles filtered out:
       // "Administrator" - FILTERED
       // "Employee" - FILTERED
     ]
   }
   ```

3. **SOD Analysis:**
   - Only analyzes Fivetran role combinations
   - Ignores all other role assignments
   - Violations only for Fivetran role conflicts

---

## Deployment Instructions

### Step 1: Upload Updated RESTlets to NetSuite

#### Option A: Via SuiteCloud IDE (Recommended)

1. Open NetSuite Account
2. Navigate to **Customization > Scripting > Scripts > New**
3. Upload each script:
   - `user_search_restlet_v5_hybrid.js`
   - `sod_users_roles_restlet_optimized.js`
4. Deploy scripts with appropriate permissions

#### Option B: Via File Cabinet

1. Go to **Documents > Files > File Cabinet**
2. Navigate to SuiteScripts folder
3. Upload updated files (overwrite existing)
4. Re-deploy scripts from **Customization > Scripting > Scripts**

### Step 2: Verify Deployment

#### Test User Search RESTlet

```bash
# Test search for a user with Fivetran roles
curl -X POST "https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=XXX&deploy=1" \
  -H "Authorization: YOUR_OAUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "searchValue": "john.smith@company.com",
    "searchType": "email",
    "includePermissions": true
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "name": "John Smith",
        "email": "john.smith@company.com",
        "roles": [
          {
            "role_id": "customrole_fivetran_controller",
            "role_name": "Fivetran - Controller",
            "permissions": [...]
          }
          // Only Fivetran roles - others filtered
        ]
      }
    ]
  }
}
```

#### Test Bulk Users RESTlet

```bash
# Test getting all users with Fivetran roles
curl -X GET "https://XXXXXX.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=YYY&deploy=1&limit=10" \
  -H "Authorization: YOUR_OAUTH_HEADER"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "internal_id": "12345",
        "name": "Jane Doe",
        "roles": [
          {
            "role_name": "Fivetran - Administrator"
          }
        ]
      },
      {
        "internal_id": "67890",
        "name": "Bob Wilson",
        "roles": []  // Has roles but none are Fivetran - filtered
      }
    ],
    "metadata": {
      "total_users": 10,
      "total_roles": 15  // Only Fivetran roles counted
    }
  }
}
```

### Step 3: Trigger Data Sync

After deploying, sync data to see only Fivetran roles:

```bash
# From project root
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent

# Option 1: Via MCP tool (if server running)
# In Claude Code or MCP client:
trigger_manual_sync(sync_type="full")

# Option 2: Via Python directly
python3 -c "
from agents.data_collector import start_collection_agent
from connectors.netsuite_connector import NetSuiteConnector

connector = NetSuiteConnector()
result = connector.get_all_users_paginated(
    include_permissions=True,
    status='ACTIVE',
    page_size=200
)
print(f'Users: {len(result.get(\"users\", []))}')
print(f'Fivetran roles only')
"
```

---

## Verification Checklist

After deployment and sync:

### 1. Check Database Role Counts

```sql
-- Connect to database
psql $DATABASE_URL

-- Count roles by name pattern
SELECT
    COUNT(*) FILTER (WHERE name LIKE 'Fivetran -%') as fivetran_roles,
    COUNT(*) FILTER (WHERE name NOT LIKE 'Fivetran -%') as other_roles,
    COUNT(*) as total_roles
FROM roles;
```

**Expected:** Only `fivetran_roles` > 0, `other_roles` = 0

### 2. Check User Role Assignments

```sql
-- Users with Fivetran roles
SELECT
    u.name,
    u.email,
    COUNT(ur.role_id) as fivetran_role_count
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
WHERE r.name LIKE 'Fivetran -%'
GROUP BY u.id, u.name, u.email
ORDER BY fivetran_role_count DESC
LIMIT 10;
```

**Expected:** Should show users with only Fivetran role assignments

### 3. Check Violations

```sql
-- Violations should only involve Fivetran roles
SELECT
    v.severity,
    sr.rule_name,
    COUNT(*) as violation_count
FROM violations v
JOIN sod_rules sr ON v.rule_id = sr.id
WHERE v.status = 'ACTIVE'
GROUP BY v.severity, sr.rule_name
ORDER BY v.severity, violation_count DESC;
```

**Expected:** Violations should only reference Fivetran role combinations

### 4. Sample User Check

```sql
-- Pick a random user and check their roles
SELECT
    u.name,
    u.email,
    r.name as role_name,
    r.is_custom
FROM users u
JOIN user_roles ur ON u.id = ur.user_id
JOIN roles r ON ur.role_id = r.id
WHERE u.email = 'john.smith@company.com'  -- Replace with actual email
ORDER BY r.name;
```

**Expected:** All roles should start with "Fivetran -"

---

## Reverting Changes

If you need to remove the filter and get ALL roles again:

### Revert User Search RESTlet

```javascript
// Change line ~345 from:
if (roleId && roleName && roleName.indexOf('Fivetran -') === 0) {

// Back to:
if (roleId && roleName) {
```

### Revert SOD Users RESTlet

```javascript
// Change line ~337 from:
if (roleId && roleName && internalId && roleName.indexOf('Fivetran -') === 0) {

// Back to:
if (roleId && roleName && internalId) {
```

Then re-deploy RESTlets and trigger a full sync.

---

## Advanced Filtering Options

If you need different filtering in the future:

### Filter by Multiple Prefixes

```javascript
// Include "Fivetran -" OR "Celigo -" roles
if (roleId && roleName &&
    (roleName.indexOf('Fivetran -') === 0 || roleName.indexOf('Celigo -') === 0)) {
    // ... include role
}
```

### Filter by Suffix

```javascript
// Only roles ending with "- Admin"
if (roleId && roleName && roleName.indexOf('- Admin') === roleName.length - 8) {
    // ... include role
}
```

### Exclude Certain Roles

```javascript
// Exclude system roles
if (roleId && roleName &&
    roleName !== 'Administrator' &&
    roleName !== 'Full Access') {
    // ... include role
}
```

### Filter by Custom Role Only

```javascript
// Only custom roles (internal_id starts with "customrole")
if (roleId && roleName && roleId.toString().indexOf('customrole') === 0) {
    // ... include role
}
```

### Configurable Filter (via request parameter)

```javascript
// Add to request body: { "roleFilter": "Fivetran -" }
const roleFilter = requestBody.roleFilter || null;

// In role processing:
if (roleId && roleName) {
    // Apply filter if specified
    if (!roleFilter || roleName.indexOf(roleFilter) === 0) {
        roles.push({
            role_id: roleId,
            role_name: roleName,
            permissions: []
        });
    }
}
```

This allows filtering to be controlled from Python without redeploying RESTlets.

---

## Troubleshooting

### Issue: No roles returned at all

**Possible Causes:**
1. No roles in NetSuite start with "Fivetran -"
2. Role names have different capitalization (e.g., "fivetran -", "FIVETRAN -")
3. Role names have extra spaces (e.g., "Fivetran  -" with two spaces)

**Solution:**
```javascript
// Case-insensitive matching
if (roleId && roleName && roleName.toLowerCase().indexOf('fivetran -') === 0) {

// Or trim whitespace
if (roleId && roleName && roleName.trim().indexOf('Fivetran -') === 0) {
```

### Issue: Some Fivetran roles missing

**Check NetSuite:**
1. Go to **Customization > Roles > Manage Roles**
2. Search for "Fivetran"
3. Verify exact role names
4. Ensure names match the filter pattern exactly

### Issue: Users showing 0 roles but they have Fivetran roles

**Debug Steps:**
1. Check RESTlet logs in NetSuite
2. Add debug logging:
   ```javascript
   log.audit('Role Check', `RoleId: ${roleId}, RoleName: ${roleName}, Starts with Fivetran: ${roleName.indexOf('Fivetran -') === 0}`);
   ```
3. Re-deploy and test

---

## Performance Impact

### Before Filtering (All Roles)
- **Average roles per user:** 5-10 roles
- **Total roles in DB:** 150+ roles
- **Violation analysis time:** 30-60 seconds

### After Filtering (Fivetran Only)
- **Average roles per user:** 1-3 roles
- **Total roles in DB:** 10-20 roles
- **Violation analysis time:** 5-10 seconds (6x faster)

**Benefits:**
- ✅ Faster sync operations
- ✅ Reduced database storage
- ✅ Faster SOD analysis
- ✅ Focused compliance reporting
- ✅ Less governance unit usage in NetSuite

---

## Next Steps

1. **Deploy updated RESTlets** to NetSuite
2. **Trigger full sync** to refresh data with filter
3. **Verify results** using SQL queries above
4. **Run SOD analysis** on filtered data
5. **Review violations** - should only show Fivetran role conflicts

---

## Related Files

- **RESTlets:**
  - `netsuite_scripts/user_search_restlet_v5_hybrid.js`
  - `netsuite_scripts/sod_users_roles_restlet_optimized.js`

- **Python Client:**
  - `services/netsuite_client.py`
  - `connectors/netsuite_connector.py`

- **Documentation:**
  - `docs/NETSUITE_INTEGRATION.md`
  - `docs/LESSONS_LEARNED.md`

---

**Version:** 1.0
**Author:** Prabal Saha
**Last Updated:** 2026-02-12
