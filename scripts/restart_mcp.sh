#!/bin/bash
set -e

# MCP Server Restart Script
# Usage: ./scripts/restart_mcp.sh [log_file]

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${1:-/tmp/mcp_server.log}"
WAIT_TIME=3
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
echo "=========================================="
echo "MCP Server Restart Script"
echo "=========================================="
log_info "Project root: $PROJECT_ROOT"
log_info "Log file: $LOG_FILE"
log_info "Time: $(date)"
echo

# Change to project directory
cd "$PROJECT_ROOT"

# Step 1: Stop existing server
log_info "Step 1: Stopping MCP server..."
if pgrep -f "mcp.mcp_server" > /dev/null; then
    if pkill -f "mcp.mcp_server"; then
        log_success "Server stop signal sent"
        sleep 2

        # Check if still running
        if pgrep -f "mcp.mcp_server" > /dev/null; then
            log_warning "Server still running, force killing..."
            pkill -9 -f "mcp.mcp_server"
            sleep 1
        fi

        log_success "Server stopped"
    else
        log_error "Failed to stop server"
        exit 1
    fi
else
    log_info "No server was running"
fi
echo

# Step 2: Verify port is free
log_info "Step 2: Checking port 8080..."
RETRY_COUNT=0
while lsof -i :8080 > /dev/null 2>&1; do
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        log_error "Port 8080 still blocked after $MAX_RETRIES attempts!"
        lsof -i :8080
        exit 1
    fi

    log_warning "Port 8080 still in use, waiting... (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    sleep $WAIT_TIME
    RETRY_COUNT=$((RETRY_COUNT + 1))
done
log_success "Port 8080 available"
echo

# Step 3: Verify Python environment
log_info "Step 3: Verifying Python environment..."
if ! command -v python3 &> /dev/null; then
    log_error "python3 not found in PATH"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
log_info "Python version: $PYTHON_VERSION"

# Check if mcp module exists
if ! python3 -c "import mcp.mcp_server" 2>/dev/null; then
    log_warning "Cannot import mcp.mcp_server module"
    log_info "Make sure you're in the correct directory and dependencies are installed"
fi
echo

# Step 4: Start server
log_info "Step 4: Starting MCP server..."
nohup python3 -m mcp.mcp_server > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
log_info "Started with PID: $SERVER_PID"
echo

# Step 5: Wait for startup
log_info "Step 5: Waiting for server to start..."
sleep $WAIT_TIME

# Step 6: Verify startup
log_info "Step 6: Verifying startup..."
if ps -p $SERVER_PID > /dev/null 2>&1; then
    log_success "Server process running (PID: $SERVER_PID)"
else
    log_error "Server failed to start!"
    log_error "Check logs: cat $LOG_FILE"
    echo
    echo "Last 20 lines of log:"
    tail -20 "$LOG_FILE"
    exit 1
fi
echo

# Step 7: Check logs for successful startup
log_info "Step 7: Checking startup logs..."
STARTUP_CHECK=0
for i in {1..10}; do
    if grep -q "Uvicorn running" "$LOG_FILE" 2>/dev/null; then
        STARTUP_CHECK=1
        break
    fi
    sleep 1
done

echo "=========================================="
echo "Recent Logs:"
echo "=========================================="
tail -15 "$LOG_FILE"
echo "=========================================="
echo

# Step 8: Final status
log_info "Step 8: Final status check..."
if [ $STARTUP_CHECK -eq 1 ]; then
    log_success "✅ MCP Server started successfully!"
    echo
    echo "Server Details:"
    echo "  PID:  $SERVER_PID"
    echo "  URL:  http://0.0.0.0:8080"
    echo "  Logs: tail -f $LOG_FILE"
    echo

    # Show component status
    if grep -q "Autonomous Collection Agent started successfully" "$LOG_FILE" 2>/dev/null; then
        log_success "✅ Autonomous Collection Agent: RUNNING"
    else
        log_warning "⚠️  Autonomous Collection Agent: Status unknown"
    fi

    if grep -q "Available tools:" "$LOG_FILE" 2>/dev/null; then
        TOOL_COUNT=$(grep "Available tools:" "$LOG_FILE" | tail -1 | grep -oE '[0-9]+')
        log_success "✅ MCP Tools: $TOOL_COUNT tools loaded"
    fi

    echo
    echo "=========================================="
    log_success "Restart completed successfully!"
    echo "=========================================="
    exit 0
else
    log_warning "⚠️  Server started but may not be ready yet"
    log_info "Monitor logs: tail -f $LOG_FILE"
    echo
    echo "If server doesn't become ready in 30 seconds, check:"
    echo "  1. Database connection: psql \$DATABASE_URL -c 'SELECT 1;'"
    echo "  2. Python dependencies: pip3 list | grep -E 'fastapi|uvicorn'"
    echo "  3. Full logs: cat $LOG_FILE"
    exit 1
fi
