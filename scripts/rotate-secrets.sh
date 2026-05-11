#!/bin/bash
#
# Open-Monitor Secrets Rotation Script
# Rotates all secrets securely
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_DIR="$PROJECT_ROOT/secrets"
BACKUP_DIR="$PROJECT_ROOT/backups/secrets-$(date +%Y%m%d-%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Backup existing secrets
backup_existing() {
    if [ -d "$SECRETS_DIR" ]; then
        log_info "Backing up existing secrets..."
        mkdir -p "$BACKUP_DIR"
        cp -r "$SECRETS_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
        log_success "Backup created: $BACKUP_DIR"
    fi
}

# Generate new secret key
generate_secret_key() {
    log_info "Generating new Flask SECRET_KEY..."
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32 > "$SECRETS_DIR/secret_key.txt"
    else
        # Fallback
        head -c 64 /dev/urandom | xxd -p -c 64 | head -1 > "$SECRETS_DIR/secret_key.txt"
    fi
    chmod 600 "$SECRETS_DIR/secret_key.txt"
    log_success "New SECRET_KEY generated"
}

# Generate new Redis password
generate_redis_password() {
    log_info "Generating new Redis password..."
    if command -v openssl &> /dev/null; then
        openssl rand -hex 24 > "$SECRETS_DIR/redis_password.txt"
    else
        # Fallback - strong password
        tr -dc 'a-zA-Z0-9!@#$%^&*' < /dev/urandom | head -c 48 > "$SECRETS_DIR/redis_password.txt"
    fi
    chmod 600 "$SECRETS_DIR/redis_password.txt"
    log_success "New Redis password generated"
}

# Generate database password (for future PostgreSQL)
generate_db_password() {
    log_info "Generating new Database password..."
    if command -v openssl &> /dev/null; then
        openssl rand -hex 24 > "$SECRETS_DIR/db_password.txt"
    else
        tr -dc 'a-zA-Z0-9!@#$%^&*' < /dev/urandom | head -c 48 > "$SECRETS_DIR/db_password.txt"
    fi
    chmod 600 "$SECRETS_DIR/db_password.txt"
    log_success "New Database password generated"
}

# Create secrets directory
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

echo "=============================================="
echo "Open-Monitor Secrets Rotation"
echo "=============================================="
echo ""

# Confirm rotation
echo -e "${YELLOW}WARNING: This will rotate all secrets!${NC}"
echo "Existing sessions will be invalidated."
echo "Services will need to be restarted."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    log_info "Rotation cancelled"
    exit 0
fi

# Backup existing
backup_existing

# Generate new secrets
generate_secret_key
generate_redis_password
generate_db_password

# Set permissions
chmod 600 "$SECRETS_DIR"/*
chmod 700 "$SECRETS_DIR"

echo ""
log_success "All secrets rotated successfully!"
echo ""
log_info "Next steps:"
echo "  1. Review new secrets in: $SECRETS_DIR"
echo "  2. Restart services: ./scripts/deploy-linux.sh restart"
echo "  3. Verify application is working"
echo "  4. Remove old backup after verification: rm -rf $BACKUP_DIR"
echo ""
log_warn "IMPORTANT: Do NOT commit secrets/ to version control!"