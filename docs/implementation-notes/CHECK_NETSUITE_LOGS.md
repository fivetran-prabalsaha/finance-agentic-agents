# Check NetSuite Execution Logs

We need to see what's happening inside the RESTlet when it tries to fetch roles.

## 📋 Steps to Check Logs

### 1. Open NetSuite Execution Log

```
1. Navigate to: Customization → Scripting → Script Execution Log
2. Filter by:
   - Script: User Search RESTlet (or script ID 3685)
   - Type: All
   - Date: Today
   - Time: Last hour
3. Click "Refresh"
```

### 2. Look for These Messages

**Should see:**
```
AUDIT | Fetching Roles | For 1 user(s)
AUDIT | Roles Fetched | X users with roles
```

**If you see:**
```
ERROR | Error enriching users with roles | ...
```

That's the problem! The role search is failing.

### 3. Common Error Messages

#### Error: "Invalid field 'role'"
```
The 'role' field doesn't exist on Employee records
```
**Solution:** Roles might be in a different field or table

#### Error: "Search type not supported"
```
Cannot use summary: GROUP with this field
```
**Solution:** Need to use a different search approach

#### Error: "Permission denied"
```
OAuth credentials don't have access to role data
```
**Solution:** Need to grant role permissions to integration

---

## 🔧 Alternative Approaches to Try

### Option 1: Use Record.load() Instead of Search

Instead of searching for roles, load the employee record directly:

```javascript
function getUserRoles(internalId) {
    var empRecord = record.load({
        type: record.Type.EMPLOYEE,
        id: internalId
    });

    var roleCount = empRecord.getLineCount({ sublistId: 'roles' });
    var roles = [];

    for (var i = 0; i < roleCount; i++) {
        var roleId = empRecord.getSublistValue({
            sublistId: 'roles',
            fieldId: 'selectrecord',
            line: i
        });

        var roleName = empRecord.getSublistText({
            sublistId: 'roles',
            fieldId: 'selectrecord',
            line: i
        });

        roles.push({ role_id: roleId, role_name: roleName });
    }

    return roles;
}
```

**Cons:** Uses 10 governance units per user (expensive)
**Pros:** Guaranteed to work if permissions are correct

---

### Option 2: Check Field Name

The field might not be called 'role'. Try these:

```javascript
// Try different field names
columns: [
    search.createColumn({ name: 'role' }),          // Standard
    search.createColumn({ name: 'roleselect' }),    // Alternative 1
    search.createColumn({ name: 'rolelist' }),      // Alternative 2
    search.createColumn({ name: 'loginrole' })      // Alternative 3
]
```

---

### Option 3: Use SuiteQL for Everything

Maybe we can query roles via SuiteQL after all:

```javascript
const sql =
    'SELECT ' +
    '    e.id as employee_id, ' +
    '    e.entityid as user_id, ' +
    '    er.role as role_id, ' +
    '    r.name as role_name ' +
    'FROM ' +
    '    Employee e, ' +
    '    EntityRoleMapping er, ' +  // Different table name?
    '    Role r ' +
    'WHERE ' +
    '    er.entity = e.id ' +
    '    AND er.role = r.id ' +
    '    AND e.id IN (...)';
```

---

## 🎯 What to Do Next

### Step 1: Check NetSuite Logs

Look for error messages in script execution log

### Step 2: Test Role Field

Create a simple saved search in NetSuite UI:
1. Lists → Search → Saved Searches → New
2. Type: Employee
3. Add Column: "Role"
4. Run search

**If it works:** Role field is accessible
**If it fails:** Need different approach

### Step 3: Check OAuth Permissions

Verify integration has these permissions:
- ✅ Employee: View
- ✅ Role: View
- ✅ Lists: View

### Step 4: Try record.load() Approach

If search doesn't work, use record.load() despite governance cost

---

## 📞 Need Help?

Share the NetSuite execution log errors and I can provide a fix specific to your NetSuite configuration.
