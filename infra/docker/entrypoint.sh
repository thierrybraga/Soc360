#!/bin/bash
# Open-Monitor v3.0 - Docker Entrypoint Script
# Handles database initialization, migrations, and application startup

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_HOME="${APP_HOME:-/app}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
WAIT_FOR_DB="${WAIT_FOR_DB:-true}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-60}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# =============================================================================
# Database Connection Check
# =============================================================================
wait_for_database() {
    local db_url=$1
    local db_name=$2
    local timeout=$DB_WAIT_TIMEOUT
    local counter=0

    log_info "Waiting for $db_name database to be ready..."

    # Extract host and port from database URL
    # Format: postgresql://user:pass@host:port/dbname
    local host=$(echo $db_url | sed -e 's/.*@\([^:]*\):.*/\1/')
    local port=$(echo $db_url | sed -e 's/.*:\([0-9]*\)\/.*/\1/')

    log_info "Connecting to $db_name at $host:$port (timeout: ${timeout}s)"

    while [ $counter -lt $timeout ]; do
        if python -c "
import socket
import sys
try:
    host = '$host'.strip()
    port = int('$port')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((host, port))
    sock.close()
    sys.exit(0 if result == 0 else 1)
except Exception as e:
    # print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            log_success "$db_name database is ready!"
            return 0
        fi

        counter=$((counter + 1))
        sleep 1
    done

    log_error "$db_name database connection timeout after ${timeout}s"
    return 1
}

check_database_connection() {
    local db_url=$1
    local db_name=$2

    log_info "Checking $db_name database connection..."

    if python -c "
from sqlalchemy import create_engine
try:
    engine = create_engine('$db_url')
    conn = engine.connect()
    conn.close()
    print('Connection successful')
except Exception as e:
    print(f'Connection failed: {e}')
    exit(1)
" 2>&1; then
        log_success "$db_name database connection verified!"
        return 0
    else
        log_error "Failed to connect to $db_name database"
        return 1
    fi
}

# =============================================================================
# Database Initialization
# =============================================================================
initialize_databases() {
    log_info "Initializing databases..."

    cd $APP_HOME

    # Run database initialization
    python -c "
from app import create_app
from app.extensions.db import db

app = create_app()
with app.app_context():
    # Create all tables
    db.create_all()
    print('Database tables created successfully')
" 2>&1

    if [ $? -eq 0 ]; then
        log_success "Database initialization completed!"
    else
        log_error "Database initialization failed"
        return 1
    fi
}

# =============================================================================
# Run Migrations
# =============================================================================
run_migrations() {
    if [ "$RUN_MIGRATIONS" != "true" ]; then
        log_info "Skipping migrations (RUN_MIGRATIONS=$RUN_MIGRATIONS)"
        return 0
    fi

    log_info "Running database migrations..."

    cd $APP_HOME

    # Check if migrations directory exists
    if [ -d "migrations" ]; then
        flask db upgrade 2>&1
        if [ $? -eq 0 ]; then
            log_success "Migrations completed successfully!"
        else
            log_warning "Migration failed, attempting to initialize..."
            initialize_databases
        fi
    else
        log_info "No migrations directory found, initializing database..."
        initialize_databases
    fi
}

# =============================================================================
# Create Initial Admin User & Trigger Sync
# =============================================================================
create_admin_and_sync() {
    log_info "Initializing Admin User..."

    cd $APP_HOME

    # 1. Create Admin User (using init_admin.py)
    python scripts/admin/create_admin.py 2>&1
    if [ $? -eq 0 ]; then
        log_success "Admin initialization script executed."
    else
        log_error "Admin initialization failed."
    fi

    # 2. Trigger Auto Sync Check in Background
    log_info "Triggering Auto-Sync Check (background)..."
    nohup python scripts/airflow/sync_check.py > /var/log/auto_sync.log 2>&1 &
}

# =============================================================================
# Health Check Endpoint
# =============================================================================
setup_health_endpoint() {
    log_info "Setting up health check..."
    # Health check is handled by the Flask app at /health endpoint
}

# =============================================================================
# Static Assets Check
# =============================================================================
check_static_assets() {
    log_info "Checking static assets..."

    if [ -d "$APP_HOME/app/static" ]; then
        log_success "Static assets directory found"
    else
        log_warning "Static assets directory not found"
    fi
}

# =============================================================================
# Environment Validation
# =============================================================================
validate_environment() {
    log_info "Validating environment..."

    local required_vars=(
        "SECRET_KEY"
        "CORE_DATABASE_URL"
        "PUBLIC_DATABASE_URL"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        exit 1
    fi

    log_success "Environment validation passed!"
}

# =============================================================================
# Startup Banner
# =============================================================================
print_banner() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║     ██████╗ ██████╗ ███████╗███╗   ██╗                           ║"
    echo "║    ██╔═══██╗██╔══██╗██╔════╝████╗  ██║                           ║"
    echo "║    ██║   ██║██████╔╝█████╗  ██╔██╗ ██║                           ║"
    echo "║    ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║                           ║"
    echo "║    ╚██████╔╝██║     ███████╗██║ ╚████║                           ║"
    echo "║     ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝                           ║"
    echo "║                                                                   ║"
    echo "║    ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗    ║"
    echo "║    ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗   ║"
    echo "║    ██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝   ║"
    echo "║    ██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗   ║"
    echo "║    ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║   ║"
    echo "║    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ║"
    echo "║                                                                   ║"
    echo "║                    Version 3.0.0                                  ║"
    echo "║       Enterprise Cybersecurity Vulnerability Management           ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo ""
}

# =============================================================================
# Main Entrypoint
# =============================================================================
main() {
    print_banner

    log_info "Starting Open-Monitor initialization..."
    log_info "Environment: ${FLASK_ENV:-production}"
    log_info "Log Level: ${LOG_LEVEL}"

    # Validate environment
    validate_environment

    # Wait for databases if enabled
    if [ "$WAIT_FOR_DB" = "true" ]; then
        wait_for_database "$CORE_DATABASE_URL" "Core"
        wait_for_database "$PUBLIC_DATABASE_URL" "Public"
    fi

    # Check database connections
    check_database_connection "$CORE_DATABASE_URL" "Core"
    check_database_connection "$PUBLIC_DATABASE_URL" "Public"

    # Run migrations
    run_migrations

    # Create admin and sync
    create_admin_and_sync

    # Check static assets
    check_static_assets

    # Setup health endpoint
    setup_health_endpoint

    log_success "Initialization complete! Starting application..."
    echo ""

    # Execute the main command
    exec "$@"
}

# Run main function with all arguments
main "$@"