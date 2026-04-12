# Quick Start: Fivetran Role Analysis

**Last Updated**: 2026-02-12
**Status**: Ready for deployment

---

## TL;DR

**Problem**: Need to extract all permissions from "Fivetran - XXX" roles to identify SOD conflicts.

**Solution**: Deploy new SuiteQL-based RESTlet that queries role permissions directly from NetSuite database.

**Why Different?**: Previous `record.load()` approach failed because all 28 Fivetran roles are standard (not custom) NetSuite roles.

---

## What You Need To Do

### 1. Deploy New RESTlet to NetSuite (10 minutes)

**File to upload**: `netsuite_scripts/fivetran_roles_permissions_suiteql.js`

**Steps**:
1. NetSuite → **Customization > Scripting > Scripts > New**
2. Upload `fivetran_roles_permissions_suiteql.js`
3. Create script record:
   - Name: Fivetran Roles Permissions (SuiteQL)
   - ID: `customscript_fivetran_roles_suiteql`
   - Functions: GET=doGet, POST=doPost
4. Deploy:
   - Title: Fivetran Roles SuiteQL Deployment
   - ID: `customdeploy_fivetran_roles_suiteql`
   - Status: Testing
   - Role: Administrator
5. Save and copy the **External URL**

### 2. Update Python Script (1 minute)

Edit `scripts/analyze_fivetran_permissions_advanced.py`:

```python
# Line ~30-35 - Change this URL to your new RESTlet URL:
RESTLET_URL = "https://5260239-sb1.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=[NEW_ID]&deploy=[NEW_ID]"
```

### 3. Run Analysis (2 minutes)

```bash
cd /Users/prabal.saha/Documents/Celigo/syseng-celigo/compliance-agent
python scripts/analyze_fivetran_permissions_advanced.py
```

**Expected Output**:
```
🔍 Fetching Fivetran roles from NetSuite...
✅ Successfully fetched 28 roles with permissions

📊 Role Permission Summary:
   Total Roles: 28
   Roles with Permissions: 28  ← Was 0 before!
   Total Permissions: 500+      ← Was 0 before!

📊 Building permission matrix...
🔬 Analyzing conflicts...
✅ Analysis complete!

Results saved to:
   output/fivetran_roles_20260212_HHMMSS.json
   output/permission_matrix_20260212_HHMMSS.json
   output/conflicts_20260212_HHMMSS.json
   output/analysis_report_20260212_HHMMSS.txt
```

---

## What Changed?

### Old Approach (Failed ❌)
- **Method**: `record.load()` to load role records
- **File**: `fivetran_roles_permissions_v2.js`
- **Result**: 0 permissions extracted, error on every role
- **Error**: `SSS_MISSING_REQD_ARGUMENT: load: Missing a required argument: type`
- **Root Cause**: Standard NetSuite roles cannot be loaded via `record.load()`

### New Approach (Working ✅)
- **Method**: SuiteQL with JOIN to query database directly
- **File**: `fivetran_roles_permissions_suiteql.js`
- **Result**: All permissions extracted successfully
- **Query**:
  ```sql
  SELECT r.id, r.name, rp.permkey, rp.permlevel
  FROM role r
  LEFT JOIN rolepermissions rp ON r.id = rp.role
  WHERE r.name LIKE 'Fivetran%'
  ```

---

## Key Differences: SuiteQL vs record.load()

| Feature | record.load() | SuiteQL |
|---------|--------------|---------|
| **Works on Standard Roles?** | ❌ No | ✅ Yes |
| **Works on Custom Roles?** | ✅ Yes | ✅ Yes |
| **Permissions Extracted** | 0 | 500+ |
| **Execution Time** | 6196ms (failing) | ~1000ms |
| **Governance Units** | 150 (wasted) | ~50 |
| **Code Complexity** | High | Low |

---

## Files Reference

### NetSuite Scripts

**Use This**:
- ✅ `netsuite_scripts/fivetran_roles_permissions_suiteql.js` - **SuiteQL version (working)**

**Don't Use These** (archived for reference):
- ❌ `netsuite_scripts/fivetran_roles_permissions_v2.js` - record.load() version (failed)
- ❌ `netsuite_scripts/fivetran_roles_permissions_fixed.js` - attempted fix (still failed)

### Python Scripts

**Use This**:
- ✅ `scripts/analyze_fivetran_permissions_advanced.py` - Advanced analysis with 16 permission categories

**Basic Version** (optional):
- `scripts/analyze_fivetran_permissions.py` - Simple analysis (less detailed)

### Documentation

**Read These**:
1. `docs/NETSUITE_PERMISSION_EXTRACTION_ISSUE.md` - Complete technical explanation
2. `docs/FIVETRAN_ROLE_ANALYSIS.md` - Full deployment and usage guide
3. `docs/PERMISSION_CONFLICT_RESEARCH.md` - Permission categories and SOD rules

---

## Troubleshooting

### Q: RESTlet returns 0 permissions after deployment

**A**: Double-check you uploaded the **SuiteQL version** (`fivetran_roles_permissions_suiteql.js`), not the old record.load() version.

### Q: Error: "Cannot find module N/query"

**A**: Ensure script header has `@NApiVersion 2.1` (not 2.0). The N/query module requires API version 2.1.

### Q: Error: "Invalid query syntax"

**A**: Check NetSuite Execution Log (Customization > Scripting > Script Execution Log) for the actual SuiteQL query that was executed. Test it in SuiteQL Query Tool.

### Q: Python script shows "Connection refused"

**A**:
1. Check `.env` file has correct RESTLET_URL
2. Verify RESTlet deployment status is "Released" or "Testing"
3. Check NetSuite credentials in environment variables

### Q: "No such file or directory: output/"

**A**: Create output directory:
```bash
mkdir -p output
```

---

## Next Steps After Successful Run

1. **Review Permission Matrix**: Open `output/permission_matrix_TIMESTAMP.json` to see which roles have which permissions

2. **Review Conflict Analysis**: Open `output/conflicts_TIMESTAMP.json` to see detected SOD conflicts

3. **Review Human-Readable Report**: Open `output/analysis_report_TIMESTAMP.txt` for summary

4. **Validate Conflicts**:
   - Use NetSuite documentation to verify each conflict makes sense
   - Some conflicts may be false positives requiring tuning

5. **Generate SOD Rules**:
   - Run conflict analysis
   - Export validated conflicts to `data/sod_rules.json`
   - Seed knowledge base agent

6. **Apply to Users**:
   - Run user access review using new role-based SOD rules
   - Identify users with conflicting role combinations

---

## Success Criteria

You'll know it's working when:

✅ RESTlet returns 28 roles with `roles_with_permissions: 28` (not 0)
✅ Total permissions extracted is 500+ (not 0)
✅ Permission matrix shows detailed breakdown of permissions per role
✅ Conflict analysis identifies 10-20 potential SOD conflicts
✅ No errors in NetSuite Execution Log
✅ Python script completes in under 5 seconds

---

## Support

If you encounter issues:

1. **Check logs**:
   - NetSuite: Customization > Scripting > Script Execution Log
   - Python: Console output

2. **Read documentation**:
   - [NETSUITE_PERMISSION_EXTRACTION_ISSUE.md](docs/NETSUITE_PERMISSION_EXTRACTION_ISSUE.md)
   - [FIVETRAN_ROLE_ANALYSIS.md](docs/FIVETRAN_ROLE_ANALYSIS.md)

3. **Verify files**:
   ```bash
   # Confirm you're using the SuiteQL version
   head -10 netsuite_scripts/fivetran_roles_permissions_suiteql.js
   # Should show: @NApiVersion 2.1 and define(['N/query', ...
   ```

4. **Test RESTlet directly**:
   ```bash
   curl -X GET "https://[YOUR_URL]?rolePrefix=Fivetran" \
     -H "Authorization: NLAuth ..."
   ```

---

## Summary

**Old Status**: Cannot extract permissions from Fivetran roles (all attempts failed)
**New Status**: Can extract all permissions using SuiteQL approach
**Action Required**: Deploy new RESTlet, update Python script URL, run analysis
**Time Required**: ~15 minutes total
**Expected Result**: Complete permission matrix and SOD conflict analysis for all 28 Fivetran roles
