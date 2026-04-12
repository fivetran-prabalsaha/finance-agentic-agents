# Okta-NetSuite User Reconciliation - Implementation Plan

## 🎯 Feature Overview

**Goal**: Automate detection and deactivation of orphaned NetSuite users who have been terminated in Okta but remain active in NetSuite.

**Business Value**:
- Reduces security risk from terminated users with active access
- Ensures SOX compliance for user access management
- Automates manual quarterly access reviews
- Provides audit trail for user lifecycle management

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                             │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
│ DATA          │ │ RECON        │ │ DEACTIVATION     │
│ COLLECTION    │ │ AGENT        │ │ AGENT            │
│ AGENT         │ │              │ │                  │
│ (Enhanced)    │ │ (New)        │ │ (New)            │
└───────────────┘ └──────────────┘ └──────────────────┘
        │              │              │
        │              │              │
        ▼              ▼              ▼
┌──────────┐    ┌──────────┐   ┌─────────────────┐
│ Okta API │    │PostgreSQL│   │NetSuite Scripts │
│          │    │ Recon    │   │- RESTlet        │
│          │    │ Tables   │   │- Map/Reduce     │
└──────────┘    └──────────┘   └─────────────────┘
```

## 🏗️ Implementation Components

### 1. Enhanced Data Collection Agent

**Enhancements to `agents/data_collector.py`**:

```python
class DataCollectionAgent:
    """Enhanced with Okta integration"""

    def __init__(self, netsuite_client, okta_client):
        self.netsuite_client = netsuite_client
        self.okta_client = okta_client  # NEW

    # NEW: Okta data collection
    def collect_okta_users(self, status='ACTIVE') -> Dict[str, Any]:
        """Fetch users from Okta"""

    def sync_okta_to_database(self, okta_users: List[Dict]) -> int:
        """Store Okta users in database"""
```

**Features**:
- Fetch active users from Okta
- Fetch deprovisioned/suspended users from Okta
- Store in new `okta_users` table
- Track sync timestamp
- Handle pagination (Okta returns 200 users per page)

---

### 2. New Reconciliation Agent

**File**: `agents/reconciliation.py`

```python
class UserReconciliationAgent:
    """
    Compares Okta and NetSuite user states
    Identifies orphaned accounts
    """

    def __init__(self, user_repo, okta_user_repo, recon_repo):
        self.user_repo = user_repo
        self.okta_user_repo = okta_user_repo
        self.recon_repo = recon_repo

    def run_reconciliation(self) -> Dict[str, Any]:
        """
        Main reconciliation logic

        Returns:
            - orphaned_users: NetSuite active but Okta terminated
            - missing_users: Okta active but not in NetSuite
            - matched_users: Status matches
        """

    def identify_orphaned_accounts(self) -> List[Dict]:
        """
        Find users:
        - Status in NetSuite: ACTIVE
        - Status in Okta: DEPROVISIONED, SUSPENDED, or NOT_FOUND
        """

    def generate_reconciliation_report(self) -> Dict[str, Any]:
        """Generate detailed reconciliation report"""
```

**Logic**:

```python
# Reconciliation Algorithm
for netsuite_user in netsuite_users:
    okta_user = find_okta_user_by_email(netsuite_user.email)

    if not okta_user:
        # User not in Okta - flag for review
        flag_as_missing_in_okta(netsuite_user)

    elif netsuite_user.status == 'ACTIVE':
        if okta_user.status in ['DEPROVISIONED', 'SUSPENDED']:
            # ORPHANED ACCOUNT - flag for deactivation
            flag_as_orphaned(netsuite_user, okta_user)
        elif okta_user.status == 'ACTIVE':
            # Match - all good
            mark_as_reconciled(netsuite_user, okta_user)
```

---

### 3. New Deactivation Agent

**File**: `agents/deactivation.py`

```python
class UserDeactivationAgent:
    """
    Handles user deactivation with approval workflow
    """

    def __init__(self, netsuite_client, recon_repo, approval_repo):
        self.netsuite_client = netsuite_client
        self.recon_repo = recon_repo
        self.approval_repo = approval_repo

    def request_deactivation_approval(
        self,
        orphaned_users: List[Dict]
    ) -> str:
        """
        Create approval request

        Returns:
            approval_request_id
        """

    def check_approval_status(self, request_id: str) -> Dict:
        """Check if request was approved/rejected"""

    def deactivate_users(
        self,
        user_ids: List[str],
        method: str = 'restlet'  # or 'mapreduce'
    ) -> Dict[str, Any]:
        """
        Deactivate users in NetSuite

        Args:
            user_ids: List of NetSuite internal IDs
            method: 'restlet' for <10 users, 'mapreduce' for bulk
        """

    def _deactivate_via_restlet(self, user_ids: List[str]) -> Dict:
        """Deactivate via RESTlet (synchronous)"""

    def _deactivate_via_mapreduce(self, user_ids: List[str]) -> Dict:
        """Deactivate via Map/Reduce (asynchronous, bulk)"""
```

---

### 4. Database Schema Changes

**New Tables**:

#### A. `okta_users` Table

```sql
CREATE TABLE okta_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    okta_id VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    status VARCHAR(50) NOT NULL,  -- ACTIVE, DEPROVISIONED, SUSPENDED
    activated_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    last_login TIMESTAMP,

    -- Okta metadata
    okta_profile JSON,
    okta_groups TEXT[],

    -- Sync metadata
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_okta_email (email),
    INDEX idx_okta_status (status)
);
```

#### B. `user_reconciliations` Table

```sql
CREATE TABLE user_reconciliations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User references
    netsuite_user_id UUID REFERENCES users(id),
    okta_user_id UUID REFERENCES okta_users(id),
    email VARCHAR(255) NOT NULL,

    -- Status comparison
    netsuite_status VARCHAR(50),
    okta_status VARCHAR(50),
    reconciliation_status VARCHAR(50) NOT NULL,
        -- MATCHED, ORPHANED, MISSING_IN_OKTA, MISSING_IN_NETSUITE

    -- Details
    discrepancy_reason TEXT,
    risk_level VARCHAR(20),  -- HIGH, MEDIUM, LOW

    -- Action tracking
    requires_action BOOLEAN DEFAULT FALSE,
    action_required VARCHAR(100),  -- DEACTIVATE_NETSUITE, INVESTIGATE, etc.

    -- Metadata
    reconciled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scan_id UUID,

    INDEX idx_recon_status (reconciliation_status),
    INDEX idx_recon_email (email),
    INDEX idx_recon_requires_action (requires_action)
);
```

#### C. `deactivation_approvals` Table

```sql
CREATE TABLE deactivation_approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Request details
    request_id VARCHAR(100) UNIQUE NOT NULL,
    user_ids TEXT[] NOT NULL,  -- Array of NetSuite user IDs to deactivate
    user_count INTEGER NOT NULL,

    -- Approval workflow
    status VARCHAR(50) DEFAULT 'PENDING',
        -- PENDING, APPROVED, REJECTED, EXPIRED
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    approved_by VARCHAR(255),
    approved_at TIMESTAMP,

    rejected_by VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,

    -- Execution tracking
    execution_status VARCHAR(50),  -- NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED
    execution_method VARCHAR(50),  -- RESTLET, MAPREDUCE
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP,

    -- Results
    users_deactivated INTEGER DEFAULT 0,
    users_failed INTEGER DEFAULT 0,
    execution_errors JSON,

    -- Metadata
    expires_at TIMESTAMP,  -- Auto-reject after 48 hours

    INDEX idx_approval_status (status),
    INDEX idx_approval_requested_at (requested_at)
);
```

#### D. `deactivation_logs` Table

```sql
CREATE TABLE deactivation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User reference
    netsuite_user_id UUID REFERENCES users(id),
    netsuite_internal_id VARCHAR(100),
    email VARCHAR(255) NOT NULL,

    -- Approval reference
    approval_request_id UUID REFERENCES deactivation_approvals(id),

    -- Action details
    action VARCHAR(50) NOT NULL,  -- DEACTIVATE, REACTIVATE
    method VARCHAR(50),  -- RESTLET, MAPREDUCE, MANUAL

    -- Status
    status VARCHAR(50) NOT NULL,  -- SUCCESS, FAILED, PENDING
    error_message TEXT,

    -- Metadata
    performed_by VARCHAR(255),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Audit trail
    reason TEXT,
    okta_status_at_time VARCHAR(50),
    netsuite_status_before VARCHAR(50),
    netsuite_status_after VARCHAR(50),

    INDEX idx_deactivation_email (email),
    INDEX idx_deactivation_status (status),
    INDEX idx_deactivation_performed_at (performed_at)
);
```

---

### 5. Okta Client Service

**File**: `services/okta_client.py`

```python
"""
Okta API Client

Handles authentication and API calls to Okta
"""

import os
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OktaClient:
    """Client for Okta API integration"""

    def __init__(
        self,
        domain: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        """
        Initialize Okta client

        Args:
            domain: Okta domain (e.g., 'mycompany.okta.com')
            api_token: Okta API token
        """
        self.domain = domain or os.getenv('OKTA_DOMAIN')
        self.api_token = api_token or os.getenv('OKTA_API_TOKEN')

        if not self.domain or not self.api_token:
            raise ValueError("OKTA_DOMAIN and OKTA_API_TOKEN required")

        self.base_url = f"https://{self.domain}/api/v1"
        self.headers = {
            'Authorization': f'SSWS {self.api_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def get_users(
        self,
        status: str = 'ACTIVE',
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Get users from Okta

        Args:
            status: ACTIVE, DEPROVISIONED, SUSPENDED, etc.
            limit: Results per page (max 200)

        Returns:
            Dict with users list and pagination info
        """
        users = []
        url = f"{self.base_url}/users"
        params = {
            'limit': limit,
            'filter': f'status eq "{status}"' if status else None
        }

        while url:
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params if url == f"{self.base_url}/users" else None,
                    timeout=30
                )
                response.raise_for_status()

                batch = response.json()
                users.extend(batch)

                # Check for next page
                links = response.links
                url = links['next']['url'] if 'next' in links else None

                logger.info(f"Fetched {len(batch)} users from Okta (total: {len(users)})")

            except requests.exceptions.RequestException as e:
                logger.error(f"Okta API error: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'users': []
                }

        return {
            'success': True,
            'users': users,
            'count': len(users)
        }

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get single user by email

        Args:
            email: User email address

        Returns:
            User object or None
        """
        url = f"{self.base_url}/users/{email}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Okta API error: {str(e)}")
            raise

    def get_deprovisioned_users(self) -> Dict[str, Any]:
        """Get all deprovisioned users"""
        return self.get_users(status='DEPROVISIONED')

    def get_suspended_users(self) -> Dict[str, Any]:
        """Get all suspended users"""
        return self.get_users(status='SUSPENDED')
```

---

### 6. NetSuite Deactivation Scripts

#### A. RESTlet (Single/Small Batch Deactivation)

**File**: `netsuite_scripts/user_deactivation_restlet.js`

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType Restlet
 * @NModuleScope SameAccount
 */

define(['N/record', 'N/error'], function(record, error) {

    /**
     * POST handler - Deactivate user(s)
     */
    function post(requestBody) {
        log.audit('Deactivation Request', JSON.stringify(requestBody));

        const userIds = requestBody.user_ids || [];
        const dryRun = requestBody.dry_run || false;

        if (!userIds || userIds.length === 0) {
            throw error.create({
                name: 'MISSING_REQUIRED_PARAMETER',
                message: 'user_ids array is required'
            });
        }

        if (userIds.length > 10) {
            throw error.create({
                name: 'TOO_MANY_USERS',
                message: 'Use Map/Reduce for more than 10 users'
            });
        }

        const results = {
            success: true,
            dry_run: dryRun,
            total: userIds.length,
            deactivated: 0,
            failed: 0,
            errors: []
        };

        for (let i = 0; i < userIds.length; i++) {
            const userId = userIds[i];

            try {
                if (!dryRun) {
                    // Load employee record
                    const employeeRecord = record.load({
                        type: record.Type.EMPLOYEE,
                        id: userId
                    });

                    // Set inactive
                    employeeRecord.setValue({
                        fieldId: 'isinactive',
                        value: true
                    });

                    // Save
                    employeeRecord.save();

                    log.audit('User Deactivated', `User ID: ${userId}`);
                    results.deactivated++;
                } else {
                    log.audit('Dry Run', `Would deactivate user: ${userId}`);
                    results.deactivated++;
                }

            } catch (e) {
                log.error('Deactivation Failed', `User ID: ${userId}, Error: ${e.message}`);
                results.failed++;
                results.errors.push({
                    user_id: userId,
                    error: e.message
                });
            }
        }

        results.success = results.failed === 0;

        return results;
    }

    return {
        post: post
    };
});
```

#### B. Map/Reduce (Bulk Deactivation)

**File**: `netsuite_scripts/user_deactivation_mapreduce.js`

```javascript
/**
 * @NApiVersion 2.1
 * @NScriptType MapReduceScript
 * @NModuleScope SameAccount
 */

define(['N/record', 'N/search', 'N/runtime'], function(record, search, runtime) {

    /**
     * getInputData stage
     * Returns users to deactivate
     */
    function getInputData() {
        // Get user IDs from script parameter
        const script = runtime.getCurrentScript();
        const userIdsParam = script.getParameter({
            name: 'custscript_user_ids_to_deactivate'
        });

        if (!userIdsParam) {
            log.error('Missing Parameter', 'custscript_user_ids_to_deactivate is required');
            return [];
        }

        // Parse comma-separated IDs
        const userIds = userIdsParam.split(',').map(id => id.trim());

        log.audit('Input Data', `Processing ${userIds.length} users`);

        // Return as array of objects for map stage
        return userIds.map(id => ({ id: id }));
    }

    /**
     * map stage
     * Process each user
     */
    function map(context) {
        const userData = JSON.parse(context.value);
        const userId = userData.id;

        try {
            // Load employee record
            const employeeRecord = record.load({
                type: record.Type.EMPLOYEE,
                id: userId
            });

            const email = employeeRecord.getValue({ fieldId: 'email' });
            const name = employeeRecord.getValue({ fieldId: 'entityid' });

            // Set inactive
            employeeRecord.setValue({
                fieldId: 'isinactive',
                value: true
            });

            // Save
            employeeRecord.save();

            log.audit('User Deactivated', `ID: ${userId}, Name: ${name}, Email: ${email}`);

            // Write success to reduce stage
            context.write({
                key: 'success',
                value: {
                    user_id: userId,
                    email: email,
                    name: name,
                    status: 'deactivated'
                }
            });

        } catch (e) {
            log.error('Deactivation Failed', `User ID: ${userId}, Error: ${e.message}`);

            // Write failure to reduce stage
            context.write({
                key: 'failed',
                value: {
                    user_id: userId,
                    error: e.message
                }
            });
        }
    }

    /**
     * reduce stage
     * Aggregate results
     */
    function reduce(context) {
        const results = context.values.map(v => JSON.parse(v));

        context.write({
            key: context.key,
            value: results
        });
    }

    /**
     * summarize stage
     * Final results
     */
    function summarize(summary) {
        log.audit('Summary', 'Map/Reduce execution complete');

        let successCount = 0;
        let failedCount = 0;

        summary.output.iterator().each(function(key, value) {
            const results = JSON.parse(value);

            if (key === 'success') {
                successCount += results.length;
            } else if (key === 'failed') {
                failedCount += results.length;
            }

            return true;
        });

        log.audit('Final Results', {
            total_processed: successCount + failedCount,
            successful: successCount,
            failed: failedCount
        });
    }

    return {
        getInputData: getInputData,
        map: map,
        reduce: reduce,
        summarize: summarize
    };
});
```

---

## 📋 Implementation Steps

### Phase 1: Foundation (Week 1)
- [ ] Create database schema (4 new tables)
- [ ] Create Okta client service
- [ ] Create Okta user repository
- [ ] Add environment variables (.env.example)
- [ ] Write unit tests for Okta client

### Phase 2: Data Collection (Week 1-2)
- [ ] Enhance Data Collection Agent with Okta integration
- [ ] Add `collect_okta_users()` method
- [ ] Add `sync_okta_to_database()` method
- [ ] Test Okta data collection with real API
- [ ] Add demo script for Okta sync

### Phase 3: Reconciliation Agent (Week 2)
- [ ] Create Reconciliation Agent
- [ ] Implement reconciliation logic
- [ ] Create reconciliation repository
- [ ] Generate reconciliation reports
- [ ] Add unit tests for reconciliation logic
- [ ] Create demo script for reconciliation

### Phase 4: Deactivation Agent (Week 3)
- [ ] Create Deactivation Agent
- [ ] Implement approval workflow
- [ ] Create deactivation repository
- [ ] Add RESTlet integration
- [ ] Add Map/Reduce integration
- [ ] Test dry-run mode

### Phase 5: NetSuite Scripts (Week 3)
- [ ] Deploy deactivation RESTlet to NetSuite
- [ ] Deploy Map/Reduce script to NetSuite
- [ ] Test RESTlet with sample users
- [ ] Test Map/Reduce with sample users
- [ ] Add error handling and logging

### Phase 6: Orchestration (Week 4)
- [ ] Update orchestrator to include new agents
- [ ] Create end-to-end workflow
- [ ] Add approval UI/CLI interface
- [ ] Implement notification for approvals
- [ ] Test complete workflow

### Phase 7: Testing & Documentation (Week 4)
- [ ] Comprehensive integration tests
- [ ] Load testing with large user sets
- [ ] Update technical specification
- [ ] Create user guide
- [ ] Record demo video

---

## 🔐 Environment Variables

Add to `.env`:

```bash
# Okta Configuration
OKTA_DOMAIN=yourcompany.okta.com
OKTA_API_TOKEN=00xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# NetSuite Deactivation Scripts
NETSUITE_DEACTIVATION_RESTLET_URL=https://1234567.restlets.api.netsuite.com/app/site/hosting/restlet.nl?script=125&deploy=1
NETSUITE_DEACTIVATION_MAPREDUCE_SCRIPT_ID=customscript_user_deactivation_mr
NETSUITE_DEACTIVATION_MAPREDUCE_DEPLOY_ID=customdeploy_user_deactivation_mr

# Approval Settings
APPROVAL_EXPIRATION_HOURS=48
APPROVAL_NOTIFICATION_EMAIL=compliance-approvers@company.com
APPROVAL_SLACK_CHANNEL=#user-deactivation-approvals

# Deactivation Settings
BULK_DEACTIVATION_THRESHOLD=10  # Use Map/Reduce above this
DRY_RUN_MODE=true  # Set to false for actual deactivation
```

---

## 🎯 Usage Examples

### 1. Collect Okta Users

```python
from services.okta_client import OktaClient
from agents.data_collector import DataCollectionAgent

okta_client = OktaClient()
data_collector = DataCollectionAgent(
    netsuite_client=netsuite_client,
    okta_client=okta_client
)

# Sync Okta users
result = data_collector.collect_okta_users()
print(f"Synced {result['count']} users from Okta")
```

### 2. Run Reconciliation

```python
from agents.reconciliation import UserReconciliationAgent

recon_agent = UserReconciliationAgent(
    user_repo=user_repo,
    okta_user_repo=okta_user_repo,
    recon_repo=recon_repo
)

# Run reconciliation
result = recon_agent.run_reconciliation()

print(f"Orphaned accounts: {len(result['orphaned_users'])}")
print(f"Missing in Okta: {len(result['missing_users'])}")
print(f"Matched: {len(result['matched_users'])}")
```

### 3. Request Deactivation

```python
from agents.deactivation import UserDeactivationAgent

deactivation_agent = UserDeactivationAgent(
    netsuite_client=netsuite_client,
    recon_repo=recon_repo,
    approval_repo=approval_repo
)

# Get orphaned users
orphaned = recon_agent.identify_orphaned_accounts()

# Request approval
request_id = deactivation_agent.request_deactivation_approval(
    orphaned_users=orphaned
)

print(f"Approval request created: {request_id}")
print("Waiting for human approval...")
```

### 4. Execute Deactivation (After Approval)

```python
# Check approval status
approval = deactivation_agent.check_approval_status(request_id)

if approval['status'] == 'APPROVED':
    user_ids = approval['user_ids']

    # Choose method based on count
    method = 'mapreduce' if len(user_ids) > 10 else 'restlet'

    # Deactivate users
    result = deactivation_agent.deactivate_users(
        user_ids=user_ids,
        method=method
    )

    print(f"Deactivated: {result['deactivated']}")
    print(f"Failed: {result['failed']}")
```

---

## 📊 Reporting & Monitoring

### Reconciliation Dashboard Metrics

- **Total Users**: NetSuite vs Okta count
- **Matched Users**: Status aligned across both systems
- **Orphaned Accounts**: Active in NetSuite, terminated in Okta
- **Missing in Okta**: NetSuite users not found in Okta
- **Missing in NetSuite**: Okta users not found in NetSuite
- **High Risk**: Orphaned accounts with sensitive roles

### Deactivation Metrics

- **Pending Approvals**: Awaiting human review
- **Approved This Week**: Number of approved requests
- **Users Deactivated**: Total users deactivated
- **Success Rate**: Deactivation success percentage
- **Avg Approval Time**: Time from request to approval

---

## 🚨 Security Considerations

1. **Approval Required**: All deactivations require human approval
2. **Dry Run Mode**: Test deactivations without actual changes
3. **Audit Trail**: Complete logging of all actions
4. **Approval Expiration**: Auto-reject after 48 hours
5. **Role-Based Access**: Only authorized users can approve
6. **Notification**: Alert on all deactivation activities
7. **Reversibility**: Document process to reactivate if needed

---

## 🔄 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     DAILY AUTOMATED SCAN                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │ Sync Okta Users  │
                   │ (Active +        │
                   │  Deprovisioned)  │
                   └─────────┬────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │ Sync NetSuite    │
                   │ Users (Active +  │
                   │ Inactive)        │
                   └─────────┬────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │ Run              │
                   │ Reconciliation   │
                   └─────────┬────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
                   ▼                   ▼
          ┌────────────────┐   ┌──────────────┐
          │ No Issues      │   │ Orphaned     │
          │ (End)          │   │ Accounts     │
          └────────────────┘   │ Found        │
                               └──────┬───────┘
                                      │
                                      ▼
                           ┌─────────────────────┐
                           │ Create Approval     │
                           │ Request             │
                           │ - Send email        │
                           │ - Send Slack alert  │
                           └──────────┬──────────┘
                                      │
                           ┌──────────┴──────────┐
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐    ┌───────────────┐
                    │ APPROVED     │    │ REJECTED      │
                    │              │    │ (End)         │
                    └──────┬───────┘    └───────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Choose Method│
                    └──────┬───────┘
                           │
               ┌───────────┴────────────┐
               │                        │
               ▼                        ▼
        ┌─────────────┐         ┌──────────────┐
        │ < 10 users  │         │ >= 10 users  │
        │ Use RESTlet │         │ Use M/R      │
        └──────┬──────┘         └──────┬───────┘
               │                       │
               └───────────┬───────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Deactivate      │
                  │ Users           │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ Log Results     │
                  │ Send Report     │
                  └─────────────────┘
```

---

## ✅ Success Criteria

- [ ] Okta users sync successfully (1000+ users in < 30 seconds)
- [ ] Reconciliation identifies orphaned accounts correctly
- [ ] Approval workflow functions properly
- [ ] RESTlet deactivates users (success rate > 95%)
- [ ] Map/Reduce handles bulk deactivations (100+ users)
- [ ] Complete audit trail of all actions
- [ ] Comprehensive test coverage (>80%)
- [ ] Documentation complete
- [ ] Production deployment successful

---

## 📈 Future Enhancements

1. **Auto-Reactivation**: Detect and reactivate if user returns in Okta
2. **Grace Period**: Wait N days before deactivating (in case of Okta sync delays)
3. **Scheduled Deactivation**: Approve now, execute later
4. **Batch Approval**: Approve multiple requests at once
5. **Self-Service Portal**: Web UI for approval workflow
6. **Slack Integration**: Approve/reject from Slack
7. **Analytics**: Track deactivation trends over time
8. **Cost Savings Report**: Calculate license savings from deactivations

---

**Status**: Ready for Implementation
**Priority**: High (Security & Compliance)
**Estimated Timeline**: 4 weeks
**Owner**: Prabal Saha

