#!/bin/bash

# MCP Server Status Check Script
# Usage: ./scripts/check_mcp_status.sh

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/tmp/mcp_server.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
status_ok() {
    echo -e "   Status: ${GREEN}✅ $1${NC}"
}

status_warn() {
    echo -e "   Status: ${YELLOW}⚠️  $1${NC}"
}

status_error() {
    echo -e "   Status: ${RED}❌ $1${NC}"
}

status_info() {
    echo -e "   ${BLUE}$1${NC}"
}

# Header
echo "=========================================="
echo "MCP Server Status Check"
echo "=========================================="
echo "Time: $(date)"
echo "Project: $PROJECT_ROOT"
echo

# Initialize overall status
OVERALL_STATUS=0

# 1. Process Status Check
echo "1. Process Status:"
if pgrep -f "mcp.mcp_server" > /dev/null 2>&1; then
    PID=$(pgrep -f "mcp.mcp_server")
    UPTIME=$(ps -p $PID -o etime= 2>/dev/null | xargs)
    MEM=$(ps -p $PID -o rss= 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
    CPU=$(ps -p $PID -o %cpu= 2>/dev/null | xargs)

    status_ok "RUNNING"
    status_info "PID: $PID"
    status_info "Uptime: $UPTIME"
    status_info "Memory: $MEM"
    status_info "CPU: ${CPU}%"

    # Warn if high resource usage
    MEM_MB=$(ps -p $PID -o rss= 2>/dev/null | awk '{print int($1/1024)}')
    if [ "$MEM_MB" -gt 1000 ]; then
        status_warn "High memory usage (${MEM_MB} MB)"
        OVERALL_STATUS=1
    fi

    CPU_INT=$(echo "$CPU" | awk '{print int($1)}')
    if [ "$CPU_INT" -gt 80 ]; then
        status_warn "High CPU usage (${CPU}%)"
        OVERALL_STATUS=1
    fi
else
    status_error "NOT RUNNING"
    OVERALL_STATUS=2
fi
echo

# 2. Port Status Check
echo "2. Port 8080:"
if lsof -i :8080 > /dev/null 2>&1; then
    PORT_PID=$(lsof -i :8080 | grep LISTEN | awk '{print $2}' | head -1)
    status_ok "LISTENING"
    status_info "Process: $PORT_PID"
else
    status_error "NOT LISTENING"
    OVERALL_STATUS=2
fi
echo

# 3. Database Connection Check
echo "3. Database Connection:"
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Source .env to get DATABASE_URL
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep DATABASE_URL | xargs)

    if [ -n "$DATABASE_URL" ]; then
        if python3 -c "
from models.database_config import DatabaseConfig
import sys
try:
    db = DatabaseConfig()
    db.get_session().execute('SELECT 1')
    print('connected')
    sys.exit(0)
except Exception as e:
    print(f'error: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "connected"; then
            status_ok "CONNECTED"

            # Get database stats
            if command -v psql &> /dev/null && [ -n "$DATABASE_URL" ]; then
                USER_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM users" 2>/dev/null | xargs || echo "N/A")
                VIOLATION_COUNT=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM violations" 2>/dev/null | xargs || echo "N/A")
                status_info "Users: $USER_COUNT"
                status_info "Violations: $VIOLATION_COUNT"
            fi
        else
            status_error "DISCONNECTED"
            OVERALL_STATUS=2
        fi
    else
        status_warn "DATABASE_URL not found in .env"
        OVERALL_STATUS=1
    fi
else
    status_warn ".env file not found"
    OVERALL_STATUS=1
fi
echo

# 4. Log File Check
echo "4. Log File:"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(ls -lh "$LOG_FILE" | awk '{print $5}')
    LOG_MODIFIED=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null | cut -d'.' -f1)

    status_ok "EXISTS"
    status_info "Size: $LOG_SIZE"
    status_info "Modified: $LOG_MODIFIED"

    # Warn if log is too large (> 100MB)
    LOG_SIZE_MB=$(ls -l "$LOG_FILE" | awk '{print int($5/1024/1024)}')
    if [ "$LOG_SIZE_MB" -gt 100 ]; then
        status_warn "Log file is large (${LOG_SIZE_MB} MB), consider rotation"
        OVERALL_STATUS=1
    fi
else
    status_warn "NOT FOUND"
    status_info "Expected: $LOG_FILE"
    OVERALL_STATUS=1
fi
echo

# 5. Recent Errors Check
echo "5. Recent Errors (last 100 lines):"
if [ -f "$LOG_FILE" ]; then
    ERROR_COUNT=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -i "error" | grep -v "NotOpenSSLWarning" | wc -l | xargs)

    if [ "$ERROR_COUNT" -eq 0 ]; then
        status_ok "No recent errors"
    else
        status_warn "Found $ERROR_COUNT errors"
        echo
        echo "   Recent errors (last 3):"
        tail -100 "$LOG_FILE" | grep -i "error" | grep -v "NotOpenSSLWarning" | tail -3 | sed 's/^/   /'
        OVERALL_STATUS=1
    fi
else
    status_warn "Cannot check (log file not found)"
fi
echo

# 6. Autonomous Collection Agent Status
echo "6. Autonomous Collection Agent:"
if [ -f "$LOG_FILE" ]; then
    if tail -50 "$LOG_FILE" 2>/dev/null | grep -q "DataCollectionAgent started successfully"; then
        status_ok "RUNNING"

        # Check scheduled jobs
        if tail -50 "$LOG_FILE" 2>/dev/null | grep -q "Full sync: Daily at 2:00 AM"; then
            status_info "Full sync: Daily at 2:00 AM"
        fi
        if tail -50 "$LOG_FILE" 2>/dev/null | grep -q "Incremental sync: Every hour"; then
            status_info "Incremental sync: Every hour"
        fi
    else
        status_warn "Status unknown"
        OVERALL_STATUS=1
    fi
else
    status_warn "Cannot check (log file not found)"
fi
echo

# 7. MCP Tools Status
echo "7. MCP Tools:"
if [ -f "$LOG_FILE" ]; then
    if grep -q "Available tools:" "$LOG_FILE" 2>/dev/null; then
        TOOL_COUNT=$(grep "Available tools:" "$LOG_FILE" | tail -1 | grep -oE '[0-9]+')
        status_ok "LOADED"
        status_info "Tools: $TOOL_COUNT"

        # Show tool list
        echo
        echo "   Tool List:"
        grep -A 20 "Available tools:" "$LOG_FILE" | grep "•" | tail -11 | sed 's/^/   /'
    else
        status_warn "No tools information found"
        OVERALL_STATUS=1
    fi
else
    status_warn "Cannot check (log file not found)"
fi
echo

# 8. Recent Sync Activity
echo "8. Recent Sync Activity:"
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep DATABASE_URL | xargs)

    if command -v psql &> /dev/null && [ -n "$DATABASE_URL" ]; then
        LAST_SYNC=$(psql "$DATABASE_URL" -t -c "
            SELECT
                TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI:SS') || ' (' || status || ')'
            FROM sync_metadata
            WHERE status IN ('success', 'failed')
            ORDER BY completed_at DESC
            LIMIT 1
        " 2>/dev/null | xargs)

        if [ -n "$LAST_SYNC" ]; then
            status_ok "Recent sync found"
            status_info "Last sync: $LAST_SYNC"
        else
            status_warn "No sync records found"
        fi
    else
        status_warn "Cannot query (psql not available)"
    fi
else
    status_warn "Cannot check (.env not found)"
fi
echo

# Summary
echo "=========================================="
echo "Summary:"
echo "=========================================="

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ All systems operational${NC}"
    echo
    echo "Quick actions:"
    echo "  View logs:    tail -f $LOG_FILE"
    echo "  Restart:      ./scripts/restart_mcp.sh"
    exit 0
elif [ $OVERALL_STATUS -eq 1 ]; then
    echo -e "${YELLOW}⚠️  Some issues detected${NC}"
    echo
    echo "Recommended actions:"
    echo "  1. Review errors in logs: tail -100 $LOG_FILE | grep -i error"
    echo "  2. Check resource usage: top -p \$(pgrep -f mcp.mcp_server)"
    echo "  3. Consider restart: ./scripts/restart_mcp.sh"
    exit 1
else
    echo -e "${RED}❌ Critical issues - server not operational${NC}"
    echo
    echo "Required actions:"
    echo "  1. Check if server is running: ps aux | grep mcp_server"
    echo "  2. Review logs: cat $LOG_FILE"
    echo "  3. Restart server: ./scripts/restart_mcp.sh"
    echo "  4. If still failing, check:"
    echo "     - Database: psql \$DATABASE_URL -c 'SELECT 1;'"
    echo "     - Port 8080: lsof -i :8080"
    echo "     - Python environment: python3 -m mcp.mcp_server"
    exit 2
fi
