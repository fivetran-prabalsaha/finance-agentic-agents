# MCP Server Management Guide

**Version:** 1.0
**Last Updated:** 2026-02-12
**Maintainer:** Compliance Engineering Team

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Server Operations](#server-operations)
3. [Monitoring & Health Checks](#monitoring--health-checks)
4. [Troubleshooting](#troubleshooting)
5. [Configuration](#configuration)
6. [Maintenance Tasks](#maintenance-tasks)
7. [Production Deployment](#production-deployment)
8. [Emergency Procedures](#emergency-procedures)

---

## Quick Reference

### Most Common Commands

```bash
# Check if server is running
ps aux | grep mcp_server | grep -v grep

# Start server
nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# Stop server
pkill -f "mcp.mcp_server"

# Restart server (one command)
pkill -f "mcp.mcp_server" && sleep 2 && nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# View logs
tail -f /tmp/mcp_server.log

# Check port
lsof -i :8080
```

---

## Server Operations

### Starting the Server

#### Method 1: Background Process (Recommended)

```bash
# Start server in background with logging
nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# Get the process ID
echo $!

# Verify it started
sleep 3
tail -10 /tmp/mcp_server.log
```

**Expected output:**
```
✅ Autonomous Collection Agent started successfully
INFO: Uvicorn running on http://0.0.0.0:8080
```

#### Method 2: Foreground (Development)

```bash
# Run in foreground (see logs directly, Ctrl+C to stop)
python3 -m mcp.mcp_server
```

**Use this for:**
- Development and debugging
- Testing configuration changes
- Watching logs in real-time

#### Method 3: Using Screen (Persistent Session)

```bash
# Start in screen session
screen -S mcp_server
python3 -m mcp.mcp_server

# Detach with: Ctrl+A, then D

# Reattach later
screen -r mcp_server

# List all screen sessions
screen -ls
```

### Stopping the Server

#### Method 1: Graceful Shutdown

```bash
# Find the process
ps aux | grep mcp_server | grep -v grep

# Kill gracefully (SIGTERM)
pkill -f "mcp.mcp_server"

# Verify it stopped
sleep 2
ps aux | grep mcp_server | grep -v grep
# Should return nothing
```

#### Method 2: Force Kill (If Unresponsive)

```bash
# Force kill (SIGKILL)
pkill -9 -f "mcp.mcp_server"

# Or by PID
kill -9 <PID>
```

⚠️ **Warning**: Force kill may leave resources in inconsistent state. Use only if graceful shutdown fails.

### Restarting the Server

#### Method 1: One-Line Restart

```bash
pkill -f "mcp.mcp_server" && sleep 2 && nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
```

#### Method 2: Using Restart Script

Create `scripts/restart_mcp.sh`:

```bash
#!/bin/bash
set -e

LOG_FILE="${LOG_FILE:-/tmp/mcp_server.log}"
WAIT_TIME=3

echo "=========================================="
echo "MCP Server Restart Script"
echo "=========================================="
echo "Log file: $LOG_FILE"
echo

# Step 1: Stop existing server
echo "1. Stopping MCP server..."
if pkill -f "mcp.mcp_server"; then
    echo "   ✅ Server stopped"
else
    echo "   ℹ️  No server was running"
fi

sleep $WAIT_TIME

# Step 2: Verify port is free
echo "2. Checking port 8080..."
if lsof -i :8080 > /dev/null 2>&1; then
    echo "   ⚠️  Port 8080 still in use, waiting..."
    sleep $WAIT_TIME

    if lsof -i :8080 > /dev/null 2>&1; then
        echo "   ❌ Port 8080 still blocked!"
        lsof -i :8080
        exit 1
    fi
fi
echo "   ✅ Port 8080 available"

# Step 3: Start server
echo "3. Starting MCP server..."
nohup python3 -m mcp.mcp_server > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "   Started with PID: $SERVER_PID"

sleep $WAIT_TIME

# Step 4: Verify startup
echo "4. Verifying startup..."
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "   ✅ Server process running (PID: $SERVER_PID)"
else
    echo "   ❌ Server failed to start!"
    echo "   Check logs: cat $LOG_FILE"
    exit 1
fi

# Step 5: Check logs
echo "5. Recent logs:"
echo "=========================================="
tail -15 "$LOG_FILE"
echo "=========================================="
echo

# Step 6: Final status
if grep -q "Uvicorn running" "$LOG_FILE"; then
    echo "✅ MCP Server started successfully!"
    echo "   PID: $SERVER_PID"
    echo "   URL: http://0.0.0.0:8080"
    echo "   Logs: tail -f $LOG_FILE"
else
    echo "⚠️  Server started but may not be ready yet"
    echo "   Monitor logs: tail -f $LOG_FILE"
fi
```

Make it executable and use:

```bash
chmod +x scripts/restart_mcp.sh
./scripts/restart_mcp.sh
```

### When to Restart the Server

Restart the MCP server after:

- ✅ **Code changes**: Updates to MCP tools, orchestrator, agents, connectors
- ✅ **Database changes**: Schema updates, new tables, constraint modifications
- ✅ **Data sync**: After syncing new users/roles to database
- ✅ **Configuration changes**: .env file updates, environment variables
- ✅ **Dependency updates**: New Python packages installed
- ✅ **Server errors**: Unresponsive or stuck processes
- ✅ **Memory issues**: High memory usage or leaks

**Note**: Claude Desktop will automatically reconnect after restart.

---

## Monitoring & Health Checks

### Check Server Status

#### Quick Status Check

```bash
# Check if process is running
ps aux | grep mcp_server | grep -v grep

# Check port
lsof -i :8080 | grep LISTEN

# Check logs for errors
tail -50 /tmp/mcp_server.log | grep -i error
```

#### Detailed Status Script

Create `scripts/check_mcp_status.sh`:

```bash
#!/bin/bash

echo "=========================================="
echo "MCP Server Status Check"
echo "=========================================="
echo "Time: $(date)"
echo

# 1. Process check
echo "1. Process Status:"
if ps aux | grep -v grep | grep mcp_server > /dev/null; then
    PID=$(ps aux | grep -v grep | grep mcp_server | awk '{print $2}')
    UPTIME=$(ps -p $PID -o etime= | xargs)
    MEM=$(ps -p $PID -o rss= | awk '{printf "%.1f MB", $1/1024}')
    CPU=$(ps -p $PID -o %cpu= | xargs)

    echo "   Status: ✅ RUNNING"
    echo "   PID: $PID"
    echo "   Uptime: $UPTIME"
    echo "   Memory: $MEM"
    echo "   CPU: ${CPU}%"
else
    echo "   Status: ❌ NOT RUNNING"
    exit 1
fi
echo

# 2. Port check
echo "2. Port 8080:"
if lsof -i :8080 > /dev/null 2>&1; then
    echo "   Status: ✅ LISTENING"
else
    echo "   Status: ❌ NOT LISTENING"
fi
echo

# 3. Database connectivity
echo "3. Database Connection:"
if python3 -c "from models.database_config import DatabaseConfig; DatabaseConfig().get_session().execute('SELECT 1')" 2>/dev/null; then
    echo "   Status: ✅ CONNECTED"
else
    echo "   Status: ❌ DISCONNECTED"
fi
echo

# 4. Recent errors
echo "4. Recent Errors (last 10):"
ERROR_COUNT=$(tail -100 /tmp/mcp_server.log 2>/dev/null | grep -i "error" | wc -l | xargs)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No recent errors"
else
    echo "   ⚠️  Found $ERROR_COUNT errors:"
    tail -100 /tmp/mcp_server.log | grep -i "error" | tail -5 | sed 's/^/   /'
fi
echo

# 5. Autonomous agent
echo "5. Autonomous Collection Agent:"
if tail -50 /tmp/mcp_server.log | grep -q "DataCollectionAgent started successfully"; then
    echo "   Status: ✅ RUNNING"
else
    echo "   Status: ⚠️  Status unknown"
fi
echo

# 6. Database statistics
echo "6. Database Statistics:"
USER_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | xargs)
VIOLATION_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM violations" 2>/dev/null | xargs)
echo "   Users: ${USER_COUNT:-N/A}"
echo "   Violations: ${VIOLATION_COUNT:-N/A}"
echo

echo "=========================================="
echo "Status check complete"
echo "=========================================="
```

Run it:
```bash
chmod +x scripts/check_mcp_status.sh
./scripts/check_mcp_status.sh
```

### View Logs

#### Real-Time Log Monitoring

```bash
# Follow logs (Ctrl+C to stop)
tail -f /tmp/mcp_server.log

# Filter for errors only
tail -f /tmp/mcp_server.log | grep -i error

# Filter for specific component
tail -f /tmp/mcp_server.log | grep "agents.analyzer"
```

#### Search Logs

```bash
# Last 100 lines
tail -100 /tmp/mcp_server.log

# Search for specific text
grep "Full sync completed" /tmp/mcp_server.log

# Count errors
grep -i error /tmp/mcp_server.log | wc -l

# Show errors with context
grep -i -B 3 -A 3 error /tmp/mcp_server.log

# View logs from specific time
awk '/2026-02-12 14:00/,/2026-02-12 15:00/' /tmp/mcp_server.log
```

#### Log Rotation

Setup log rotation to prevent disk space issues:

Create `/etc/logrotate.d/mcp_server`:

```
/tmp/mcp_server.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 prabal.saha staff
    postrotate
        pkill -HUP -f "mcp.mcp_server"
    endscript
}
```

Test log rotation:
```bash
logrotate -d /etc/logrotate.d/mcp_server
```

### Performance Monitoring

#### CPU & Memory Usage

```bash
# Monitor resources
top -p $(pgrep -f mcp.mcp_server)

# Or use ps
ps -p $(pgrep -f mcp.mcp_server) -o %cpu,%mem,vsz,rss,etime
```

#### Database Connections

```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='compliance_db';"

# Check idle connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='compliance_db' AND state='idle';"
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Server Won't Start

**Symptoms:**
- Process starts but immediately exits
- "Address already in use" error
- "Permission denied" error

**Diagnostics:**
```bash
# Check if port is in use
lsof -i :8080

# Check recent logs
tail -50 /tmp/mcp_server.log

# Try starting in foreground to see errors
python3 -m mcp.mcp_server
```

**Solutions:**

1. **Port already in use:**
   ```bash
   # Find what's using the port
   lsof -i :8080

   # Kill it
   kill -9 <PID>

   # Or change port in code
   # Edit mcp/mcp_server.py: uvicorn.run(..., port=8081)
   ```

2. **Permission denied:**
   ```bash
   # Check file permissions
   ls -la mcp/mcp_server.py

   # Fix if needed
   chmod +x mcp/mcp_server.py
   ```

3. **Missing dependencies:**
   ```bash
   # Reinstall requirements
   pip3 install -r requirements.txt
   ```

#### Issue 2: Server Crashes or Hangs

**Symptoms:**
- Process exists but doesn't respond
- High CPU/memory usage
- No log activity

**Diagnostics:**
```bash
# Check if process is hung
ps -p $(pgrep -f mcp.mcp_server) -o stat,wchan

# Check resource usage
ps -p $(pgrep -f mcp.mcp_server) -o %cpu,%mem,rss

# Check for deadlocks
tail -100 /tmp/mcp_server.log | grep -i "lock\|deadlock"
```

**Solutions:**

1. **Force restart:**
   ```bash
   pkill -9 -f "mcp.mcp_server"
   sleep 2
   nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
   ```

2. **Check database connections:**
   ```bash
   psql $DATABASE_URL -c "SELECT pid, state, wait_event FROM pg_stat_activity WHERE datname='compliance_db';"
   ```

3. **Clear connection pool:**
   ```bash
   # Terminate idle connections
   psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='compliance_db' AND state='idle' AND pid != pg_backend_pid();"
   ```

#### Issue 3: Database Connection Errors

**Symptoms:**
- "No module named 'psycopg2'" error
- "Connection refused" error
- "Password authentication failed" error

**Diagnostics:**
```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1;"

# Check .env file
cat .env | grep DATABASE_URL

# Verify PostgreSQL is running
pg_isready
```

**Solutions:**

1. **Install database driver:**
   ```bash
   pip3 install psycopg2-binary
   ```

2. **Fix connection string:**
   ```bash
   # Verify format in .env
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   ```

3. **Start PostgreSQL:**
   ```bash
   # macOS
   brew services start postgresql

   # Linux
   sudo systemctl start postgresql
   ```

#### Issue 4: Tools Not Showing Up in Claude

**Symptoms:**
- Claude says "I don't have access to that tool"
- Tools missing from tool list
- Old data showing in responses

**Diagnostics:**
```bash
# Check tools loaded
grep "Available tools:" /tmp/mcp_server.log

# Check tool count
grep "Available tools:" /tmp/mcp_server.log | grep -oE '[0-9]+ tools'
```

**Solutions:**

1. **Restart MCP server:**
   ```bash
   ./scripts/restart_mcp.sh
   ```

2. **Restart Claude Desktop:**
   - Quit Claude Desktop completely
   - Restart Claude Desktop
   - Wait for MCP server to reconnect

3. **Check MCP configuration:**
   ```bash
   # View Claude's MCP config
   cat ~/.claude/config.json
   ```

#### Issue 5: Memory Leaks

**Symptoms:**
- Memory usage grows over time
- Server becomes slow
- Eventually crashes

**Diagnostics:**
```bash
# Monitor memory growth
watch -n 5 'ps -p $(pgrep -f mcp.mcp_server) -o rss,vsz'

# Check for database connection leaks
psql $DATABASE_URL -c "SELECT count(*), state FROM pg_stat_activity WHERE datname='compliance_db' GROUP BY state;"
```

**Solutions:**

1. **Regular restarts (temporary):**
   ```bash
   # Add to cron for daily restart
   0 3 * * * /path/to/scripts/restart_mcp.sh
   ```

2. **Close database sessions properly:**
   - Check code for unclosed sessions
   - Ensure try/finally blocks close sessions

3. **Reduce connection pool size:**
   ```python
   # In database_config.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=5,      # Reduce from 10
       max_overflow=10   # Reduce from 20
   )
   ```

---

## Configuration

### Environment Variables

The MCP server reads configuration from `.env` file:

```bash
# View current configuration
cat .env

# Edit configuration
nano .env  # or vim, code, etc.
```

**Key Configuration Options:**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/compliance_db

# NetSuite API
NETSUITE_CONSUMER_KEY=...
NETSUITE_CONSUMER_SECRET=...
NETSUITE_TOKEN_ID=...
NETSUITE_TOKEN_SECRET=...
NETSUITE_REALM=5260239_SB1
NETSUITE_RESTLET_URL=https://...

# Claude API
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL_FAST=claude-sonnet-4-5-20250929
CLAUDE_MODEL_REASONING=claude-opus-4-6

# Server
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO

# Scheduling
SCAN_INTERVAL_HOURS=4
SCAN_TIMEZONE=America/New_York
```

**After changing `.env`:**
```bash
# Always restart server
./scripts/restart_mcp.sh
```

### Port Configuration

To change the server port:

1. **Edit `mcp/mcp_server.py`:**
   ```python
   # Find the uvicorn.run() call
   uvicorn.run(
       app,
       host="0.0.0.0",
       port=8081,  # Change from 8080
       log_level="info"
   )
   ```

2. **Update Claude Desktop config** (`~/.claude/config.json`):
   ```json
   {
     "mcpServers": {
       "compliance": {
         "url": "http://localhost:8081"
       }
     }
   }
   ```

3. **Restart both:**
   ```bash
   ./scripts/restart_mcp.sh
   # Then restart Claude Desktop
   ```

---

## Maintenance Tasks

### Daily Tasks

```bash
# Check server status
./scripts/check_mcp_status.sh

# Review errors
tail -50 /tmp/mcp_server.log | grep -i error

# Check disk space
df -h /tmp
```

### Weekly Tasks

```bash
# Review sync statistics
psql $DATABASE_URL -c "
    SELECT
        DATE(started_at) as date,
        COUNT(*) as syncs,
        AVG(duration_seconds) as avg_duration,
        SUM(users_synced) as total_users
    FROM sync_metadata
    WHERE started_at > NOW() - INTERVAL '7 days'
    GROUP BY DATE(started_at)
    ORDER BY date DESC;
"

# Check violation trends
psql $DATABASE_URL -c "
    SELECT
        severity,
        COUNT(*) as count
    FROM violations
    WHERE status = 'OPEN'
    GROUP BY severity
    ORDER BY
        CASE severity
            WHEN 'CRITICAL' THEN 1
            WHEN 'HIGH' THEN 2
            WHEN 'MEDIUM' THEN 3
            WHEN 'LOW' THEN 4
        END;
"

# Rotate logs manually if needed
tail -10000 /tmp/mcp_server.log > /tmp/mcp_server.log.tmp
mv /tmp/mcp_server.log.tmp /tmp/mcp_server.log
```

### Monthly Tasks

```bash
# Vacuum database
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# Check database size
psql $DATABASE_URL -c "
    SELECT
        pg_size_pretty(pg_database_size('compliance_db')) as db_size,
        pg_size_pretty(pg_total_relation_size('users')) as users_table,
        pg_size_pretty(pg_total_relation_size('violations')) as violations_table;
"

# Review and cleanup old sync metadata
psql $DATABASE_URL -c "
    DELETE FROM sync_metadata
    WHERE started_at < NOW() - INTERVAL '90 days'
    AND status IN ('success', 'failed');
"
```

### Backup Procedures

```bash
# Backup database
pg_dump $DATABASE_URL > backups/compliance_db_$(date +%Y%m%d).sql

# Backup .env file
cp .env backups/env_$(date +%Y%m%d).backup

# Compress old backups
gzip backups/compliance_db_$(date -d '7 days ago' +%Y%m%d).sql
```

---

## Production Deployment

### Pre-Deployment Checklist

```markdown
## Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Code reviewed and approved
- [ ] .env file configured for production
- [ ] Database migrations applied
- [ ] Backup created
- [ ] Monitoring alerts configured
- [ ] Rollback plan documented
- [ ] Team notified of deployment
```

### Deployment Steps

```bash
# 1. Stop server
pkill -f "mcp.mcp_server"

# 2. Pull latest code
git pull origin main

# 3. Install dependencies
pip3 install -r requirements.txt

# 4. Run migrations (if any)
python3 scripts/run_migrations.py

# 5. Test configuration
python3 -c "from models.database_config import DatabaseConfig; DatabaseConfig().get_session().execute('SELECT 1')"

# 6. Start server
nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# 7. Verify startup
sleep 5
tail -20 /tmp/mcp_server.log

# 8. Health check
curl http://localhost:8080/health
```

### Rollback Procedure

```bash
# 1. Stop current server
pkill -f "mcp.mcp_server"

# 2. Revert code
git checkout <previous-commit-hash>

# 3. Restore database (if needed)
psql $DATABASE_URL < backups/compliance_db_YYYYMMDD.sql

# 4. Start server
nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &

# 5. Verify
./scripts/check_mcp_status.sh
```

### Production Monitoring

**Setup monitoring with systemd (Linux):**

Create `/etc/systemd/system/mcp-server.service`:

```ini
[Unit]
Description=MCP Compliance Server
After=network.target postgresql.service

[Service]
Type=simple
User=prabal.saha
WorkingDirectory=/path/to/compliance-agent
Environment="PATH=/usr/local/bin:/usr/bin"
ExecStart=/usr/bin/python3 -m mcp.mcp_server
Restart=always
RestartSec=10
StandardOutput=append:/var/log/mcp_server.log
StandardError=append:/var/log/mcp_server.error.log

[Install]
WantedBy=multi-user.target
```

Enable and manage:
```bash
# Enable service
sudo systemctl enable mcp-server

# Start service
sudo systemctl start mcp-server

# Check status
sudo systemctl status mcp-server

# View logs
sudo journalctl -u mcp-server -f

# Restart
sudo systemctl restart mcp-server
```

---

## Emergency Procedures

### Server Down - Critical

**Impact**: Claude Desktop cannot access compliance tools

**Steps:**

1. **Immediate restart:**
   ```bash
   pkill -9 -f "mcp.mcp_server"
   nohup python3 -m mcp.mcp_server > /tmp/mcp_server.log 2>&1 &
   ```

2. **Check logs for root cause:**
   ```bash
   tail -100 /tmp/mcp_server.log | grep -i error
   ```

3. **If still failing, check dependencies:**
   ```bash
   # Database
   pg_isready

   # Port availability
   lsof -i :8080
   ```

4. **Notify team:**
   ```bash
   # Send alert (implement as needed)
   ./scripts/send_alert.sh "MCP Server DOWN"
   ```

### Database Connection Lost

**Impact**: Server running but cannot access data

**Steps:**

1. **Check database:**
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

2. **Check connections:**
   ```bash
   psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname='compliance_db';"
   ```

3. **Restart server (will recreate connection pool):**
   ```bash
   ./scripts/restart_mcp.sh
   ```

4. **If database is down:**
   ```bash
   # macOS
   brew services restart postgresql

   # Linux
   sudo systemctl restart postgresql
   ```

### High Memory Usage

**Impact**: Server slow, potential crash

**Steps:**

1. **Check memory:**
   ```bash
   ps -p $(pgrep -f mcp.mcp_server) -o %mem,rss,vsz
   ```

2. **Check database connections:**
   ```bash
   psql $DATABASE_URL -c "SELECT count(*), state FROM pg_stat_activity WHERE datname='compliance_db' GROUP BY state;"
   ```

3. **Graceful restart:**
   ```bash
   ./scripts/restart_mcp.sh
   ```

4. **If persistent, investigate memory leak:**
   ```bash
   # Take heap dump (if py-spy installed)
   py-spy dump --pid $(pgrep -f mcp.mcp_server)
   ```

### Claude Desktop Not Connecting

**Impact**: Users cannot access MCP tools

**Steps:**

1. **Verify server is running:**
   ```bash
   ./scripts/check_mcp_status.sh
   ```

2. **Check Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/`
   - Look for MCP connection errors

3. **Restart MCP server:**
   ```bash
   ./scripts/restart_mcp.sh
   ```

4. **Restart Claude Desktop:**
   - Quit Claude Desktop completely
   - Start Claude Desktop
   - Wait for reconnection (30 seconds)

5. **Verify MCP config:**
   ```bash
   cat ~/.claude/config.json
   ```

---

## Appendix

### Useful Scripts Location

```
scripts/
├── restart_mcp.sh           # Restart server
├── check_mcp_status.sh      # Health check
├── view_logs.sh             # Log viewer
├── backup_db.sh             # Database backup
└── cleanup_old_data.sh      # Data maintenance
```

### Log File Locations

```
/tmp/mcp_server.log          # Main server log
/tmp/mcp_server.error.log    # Error log (if separate)
~/.claude/logs/              # Claude Desktop logs
/var/log/mcp_server/         # Production logs (systemd)
```

### Database Tables Reference

```sql
-- Key tables
users                    -- User records from NetSuite
roles                    -- Role definitions
user_roles              -- User-role assignments
violations              -- SOD violations
compliance_scans        -- Analysis runs
sync_metadata           -- Data sync history
sod_rules               -- SOD rule definitions
```

### Port Usage

```
8080  - MCP Server (default)
5432  - PostgreSQL
6379  - Redis (if using Celery)
```

### Related Documentation

- [Lessons Learned](./LESSONS_LEARNED.md) - All issues and solutions
- [Architecture](../SOD_COMPLIANCE_ARCHITECTURE.md) - System architecture
- [MCP Integration](../MCP_INTEGRATION_SPEC.md) - MCP tool specifications
- [Collection Agent](../COLLECTION_AGENT.md) - Autonomous agent details

---

**Document Version:** 1.0
**Last Updated:** 2026-02-12
**Next Review:** 2026-03-12

**Questions or Issues?**
Contact: Compliance Engineering Team
