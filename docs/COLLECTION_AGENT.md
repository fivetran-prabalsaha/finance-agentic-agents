# Autonomous Data Collection Agent

The Autonomous Data Collection Agent is a background service that proactively syncs user, role, and permission data from external systems (NetSuite, Okta, etc.) to the local PostgreSQL database.

## Overview

### Purpose

The collection agent ensures that:
- **Data is always fresh**: Automatic scheduled syncs keep data up-to-date
- **Queries are instant**: All queries hit the database (no slow API calls)
- **Data is complete**: Full syncs capture all users, roles, and permissions
- **Violations are detected**: SOD analysis runs after each sync

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Collection Agent                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │           APScheduler Background Jobs            │  │
│  │  • Full Sync: Daily at 2:00 AM                  │  │
│  │  • Incremental Sync: Every hour                 │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                                │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │              DataCollectionAgent                 │  │
│  │  • Fetch data from external systems              │  │
│  │  • Sync to PostgreSQL                            │  │
│  │  • Run SOD analysis                              │  │
│  │  • Track sync metadata                           │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                                │
└─────────────────────────┼────────────────────────────────┘
                          ▼
        ┌─────────────────────────────────────┐
        │        External Systems              │
        │  • NetSuite Connector                │
        │  • Okta Connector (future)           │
        │  • Salesforce Connector (future)     │
        └─────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │       PostgreSQL Database            │
        │  • users, roles, user_roles          │
        │  • violations, sod_rules             │
        │  • sync_metadata                     │
        └─────────────────────────────────────┘
```

## Features

### 1. Scheduled Syncs

- **Full Sync**: Daily at 2:00 AM
  - Fetches ALL users from external system
  - Includes all roles and permissions
  - Includes inactive users
  - Runs complete SOD analysis
  - Takes ~30-60 seconds for 100-200 users

- **Incremental Sync**: Every hour
  - Currently falls back to full sync (TODO: implement true incremental)
  - Future: Only fetch changed data since last sync

### 2. Manual Syncs

Trigger syncs on-demand via:
- CLI: `python manage_collector.py sync --type full`
- MCP Tools: `trigger_manual_sync` tool
- Python API: `agent.manual_sync()`

### 3. Sync Metadata Tracking

Every sync records:
- **Metrics**: Users fetched/synced, roles synced, violations detected
- **Timing**: Start time, end time, duration
- **Status**: Success/failed/running
- **Errors**: Error messages and details
- **Context**: Who triggered it (scheduler/manual/api)

### 4. SOD Analysis Integration

After each successful sync:
- Runs `SODAnalysisAgent.analyze_all_users()`
- Detects CRITICAL, HIGH, MEDIUM violations
- Updates violation status (new/existing/resolved)
- Records violations in database

### 5. Monitoring & Alerting

- Track sync success rate (7-day statistics)
- Average sync duration
- Total users/roles/violations synced
- Failed sync alerts (TODO: implement Slack/email)

## Usage

### Starting the Agent

**Option 1: Via CLI**
```bash
# Start agent and return immediately
python manage_collector.py start

# Start agent in daemon mode (keeps running)
python manage_collector.py start --daemon
```

**Option 2: Via MCP Tools**
Use the `start_collection_agent` tool from Claude UI

**Option 3: Automatic Startup**
The agent automatically starts when the MCP server starts

### Stopping the Agent

```bash
# Stop via CLI
python manage_collector.py stop
```

Or use the `stop_collection_agent` MCP tool

### Checking Status

**Via CLI:**
```bash
python manage_collector.py status
```

**Via MCP Tools:**
Use the `get_collection_agent_status` tool

**Example Output:**
```
📊 Autonomous Collection Agent Status

Agent Status: 🟢 Running

Last Successful Sync:
  • Completed: 2026-02-12T10:30:45
  • Duration: 42.5s
  • Users Synced: 156

Recent Syncs (Last 5):
  ✅ 2026-02-12T10:30:00 - FULL - SUCCESS
     Duration: 42.5s, Users: 156
  ✅ 2026-02-12T09:00:00 - INCREMENTAL - SUCCESS
     Duration: 38.2s, Users: 156
  ❌ 2026-02-12T08:00:00 - INCREMENTAL - FAILED
     Error: Connection timeout

7-Day Statistics:
  • Total Syncs: 48
  • Success Rate: 95.8%
  • Avg Duration: 41.2s
  • Total Users Synced: 7,488
  • Total Roles Synced: 312
  • Total Violations Detected: 234
```

### Triggering Manual Sync

**Via CLI:**
```bash
# Full sync
python manage_collector.py sync --type full

# Incremental sync
python manage_collector.py sync --type incremental
```

**Via MCP Tools:**
Use the `trigger_manual_sync` tool with parameters:
- `system_name`: "netsuite" (default)
- `sync_type`: "full" or "incremental"

### Viewing Sync History

```bash
# Show last 20 syncs
python manage_collector.py history

# Show last 50 syncs
python manage_collector.py history --limit 50

# Filter by system
python manage_collector.py history --system netsuite
```

### Viewing Statistics

```bash
# Last 7 days (default)
python manage_collector.py stats

# Last 30 days
python manage_collector.py stats --days 30

# Specific system
python manage_collector.py stats --system netsuite
```

## Configuration

### Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance

# NetSuite credentials
NETSUITE_ACCOUNT_ID=your_account_id
NETSUITE_CONSUMER_KEY=your_consumer_key
NETSUITE_CONSUMER_SECRET=your_consumer_secret
NETSUITE_TOKEN_ID=your_token_id
NETSUITE_TOKEN_SECRET=your_token_secret
```

### Sync Schedule Customization

Edit `agents/data_collector.py` to change schedules:

```python
# Change full sync time (currently 2 AM daily)
self.scheduler.add_job(
    func=self.full_sync,
    trigger=CronTrigger(hour=2, minute=0),  # Modify hour here
    id='full_sync_daily'
)

# Change incremental sync frequency (currently hourly)
self.scheduler.add_job(
    func=self.incremental_sync,
    trigger=IntervalTrigger(hours=1),  # Modify hours here
    id='incremental_sync_hourly'
)
```

## Deployment

### Production Deployment

**1. Systemd Service (Linux)**

Create `/etc/systemd/system/compliance-collector.service`:

```ini
[Unit]
Description=Compliance Collection Agent
After=network.target postgresql.service

[Service]
Type=simple
User=compliance
WorkingDirectory=/opt/compliance-agent
ExecStart=/opt/compliance-agent/venv/bin/python manage_collector.py start --daemon
Restart=always
RestartSec=10
Environment="DATABASE_URL=postgresql://..."
Environment="NETSUITE_ACCOUNT_ID=..."

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl enable compliance-collector
sudo systemctl start compliance-collector
sudo systemctl status compliance-collector
```

**2. Docker Container**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "manage_collector.py", "start", "--daemon"]
```

Run container:
```bash
docker build -t compliance-collector .
docker run -d --name collector \
  --env-file .env \
  --restart unless-stopped \
  compliance-collector
```

**3. Kubernetes Deployment**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-collector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: compliance-collector
  template:
    metadata:
      labels:
        app: compliance-collector
    spec:
      containers:
      - name: collector
        image: compliance-collector:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: compliance-secrets
              key: database-url
```

### Monitoring

**1. Health Checks**

Check if agent is running:
```bash
python manage_collector.py status | grep "Running"
```

**2. Log Monitoring**

Logs are written to stdout/stderr. Configure your deployment to capture:
- Failed syncs
- Error messages
- Sync durations > threshold

**3. Metrics**

Query `sync_metadata` table for metrics:
```sql
-- Success rate last 7 days
SELECT
  COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate,
  AVG(duration_seconds) as avg_duration,
  SUM(users_synced) as total_users_synced
FROM sync_metadata
WHERE started_at > NOW() - INTERVAL '7 days';

-- Failed syncs
SELECT id, started_at, error_message
FROM sync_metadata
WHERE status = 'failed'
ORDER BY started_at DESC
LIMIT 10;
```

**4. Alerting (TODO)**

Future alert channels:
- Slack webhook on failed syncs
- Email on repeated failures
- PagerDuty for critical errors

## Troubleshooting

### Agent Won't Start

**Problem**: Agent fails to start

**Solutions**:
1. Check database connection:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

2. Check logs for errors:
   ```bash
   python manage_collector.py start --daemon 2>&1 | tee collector.log
   ```

3. Verify migrations are applied:
   ```bash
   psql $DATABASE_URL -f migrations/001_add_sync_metadata.sql
   ```

### Syncs Failing

**Problem**: All syncs fail with connection errors

**Solutions**:
1. Test NetSuite connection:
   ```python
   from connectors.netsuite_connector import NetSuiteConnector
   connector = NetSuiteConnector()
   users = connector.fetch_users_with_roles_sync(limit=1)
   print(f"Fetched {len(users)} users")
   ```

2. Check NetSuite credentials in `.env`

3. Verify NetSuite API access is enabled

### Slow Syncs

**Problem**: Syncs take too long (>60s for 200 users)

**Solutions**:
1. Check database performance:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM users;
   ```

2. Verify indexes exist:
   ```sql
   SELECT tablename, indexname FROM pg_indexes
   WHERE schemaname = 'public';
   ```

3. Check NetSuite API rate limits

4. Consider pagination/batching for large datasets

### Duplicate Users

**Problem**: Users synced multiple times

**Solution**: The sync uses upsert (INSERT ... ON CONFLICT UPDATE) which should prevent duplicates. If this happens:
1. Check for unique constraint on `users.external_id`
2. Verify `system_name` is consistent
3. Check sync logs for errors

## Database Schema

### sync_metadata Table

```sql
CREATE TABLE sync_metadata (
    id UUID PRIMARY KEY,
    sync_type VARCHAR(50),           -- 'full', 'incremental', 'manual'
    system_name VARCHAR(100),        -- 'netsuite', 'okta', etc.
    status VARCHAR(50),              -- 'pending', 'running', 'success', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    users_fetched INTEGER,
    users_synced INTEGER,
    users_updated INTEGER,
    users_created INTEGER,
    roles_synced INTEGER,
    violations_detected INTEGER,
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER,
    metadata JSONB,
    triggered_by VARCHAR(255),       -- 'scheduler', 'manual', 'api'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Key Queries

```sql
-- Get last successful sync
SELECT * FROM sync_metadata
WHERE status = 'success' AND system_name = 'netsuite'
ORDER BY completed_at DESC
LIMIT 1;

-- Get sync statistics
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE status = 'success') as successful,
  COUNT(*) FILTER (WHERE status = 'failed') as failed,
  AVG(duration_seconds) as avg_duration,
  SUM(users_synced) as total_users_synced
FROM sync_metadata
WHERE started_at > NOW() - INTERVAL '7 days';
```

## API Reference

### Python API

```python
from agents.data_collector import (
    get_collection_agent,
    start_collection_agent,
    stop_collection_agent
)

# Get agent instance
agent = get_collection_agent()

# Start agent
start_collection_agent()

# Trigger manual sync
result = agent.manual_sync(system_name='netsuite', sync_type='full')
print(f"Synced {result['users_synced']} users")

# Get status
status = agent.get_sync_status('netsuite')
print(f"Last sync: {status['last_successful_sync']}")

# Stop agent
stop_collection_agent()
```

### MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `start_collection_agent` | Start the agent | None |
| `stop_collection_agent` | Stop the agent | None |
| `get_collection_agent_status` | Get status | `system_name` (optional) |
| `trigger_manual_sync` | Trigger sync | `system_name`, `sync_type` |

## Future Enhancements

### Phase 2: True Incremental Sync

- Implement `lastModifiedDate` filtering
- Only fetch changed records since last sync
- Reduce sync time from 40s to <5s

### Phase 3: Multi-System Support

- Add Okta connector
- Add Salesforce connector
- Support parallel syncs for multiple systems

### Phase 4: Smart Alerting

- Slack webhooks for failed syncs
- Email digests for weekly statistics
- PagerDuty integration for critical failures
- Teams/Discord notifications

### Phase 5: Advanced Monitoring

- Prometheus metrics exporter
- Grafana dashboards
- Real-time sync progress tracking
- Historical trend analysis

## References

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [migrations/001_add_sync_metadata.sql](../migrations/001_add_sync_metadata.sql) - Database migration
- [agents/data_collector.py](../agents/data_collector.py) - Agent implementation
- [repositories/sync_metadata_repository.py](../repositories/sync_metadata_repository.py) - Repository layer
