#!/bin/bash
#
# Open-Monitor Deployment Menu
# Interactive deployment script for all environments
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Project root (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════╗"
    echo "║       Open-Monitor Deployment Menu         ║"
    echo "║              v3.0.0                        ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_separator() {
    echo -e "${BLUE}──────────────────────────────────────────────${NC}"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed"
        return 1
    fi
    return 0
}

check_env_file() {
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_warning ".env file not found"
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            read -p "Copy .env.example to .env? (y/n): " answer
            if [ "$answer" = "y" ]; then
                cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
                print_success ".env file created from .env.example"
                print_warning "Please edit .env with your settings before running"
            fi
        fi
    fi
}

# ============================================================================
# DEPLOYMENT OPTIONS
# ============================================================================

dev_local() {
    print_info "Starting Local Development Server..."
    print_separator
    check_command python3 || check_command python || { print_error "Python not found"; return 1; }
    check_env_file

    PYTHON=$(command -v python3 || command -v python)

    # Check/create virtual environment
    if [ ! -d "$PROJECT_ROOT/.venv" ]; then
        print_info "Creating virtual environment..."
        $PYTHON -m venv .venv
    fi

    # Activate venv
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    fi

    # Install dependencies
    print_info "Installing dependencies..."
    pip install -r requirements.txt -q

    # Run Flask dev server
    print_success "Starting Flask development server..."
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    $PYTHON run.py
}

python_full() {
    print_info "Starting Full Python Stack (PostgreSQL + Redis)..."
    print_separator
    check_command python3 || check_command python || { print_error "Python not found"; return 1; }
    check_env_file

    PYTHON=$(command -v python3 || command -v python)

    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    fi

    pip install -r requirements.txt -q

    print_info "Checking PostgreSQL connection..."
    $PYTHON -c "from app import create_app; app = create_app('production'); print('Database OK')" 2>/dev/null || {
        print_error "Database connection failed. Check .env settings"
        return 1
    }

    print_success "Starting application..."
    export FLASK_ENV=production
    gunicorn "app:create_app()" --bind 0.0.0.0:5000 --workers 4 --threads 2
}

docker_local() {
    print_info "Starting Docker Compose (Full Stack)..."
    print_separator
    check_command docker || { print_error "Docker not found"; return 1; }
    check_command docker-compose || check_command "docker compose" || { print_error "Docker Compose not found"; return 1; }
    check_env_file

    print_info "Building and starting containers..."
    docker compose up --build -d

    print_success "Containers started"
    print_info "Application: http://localhost:80"
    print_info "Airflow UI:  http://localhost:8080"
    echo ""
    print_info "View logs: docker compose logs -f app"
    print_info "Stop: docker compose down"
}

docker_build() {
    print_info "Building Docker Image..."
    print_separator
    check_command docker || { print_error "Docker not found"; return 1; }

    read -p "Image tag [open-monitor:latest]: " TAG
    TAG=${TAG:-open-monitor:latest}

    docker build -t "$TAG" -f Dockerfile .
    print_success "Image built: $TAG"
    echo ""
    print_info "Run: docker run -p 5000:5000 --env-file .env $TAG"
}

heroku_deploy() {
    print_info "Deploying to Heroku..."
    print_separator
    check_command heroku || { print_error "Heroku CLI not found"; return 1; }
    check_command git || { print_error "Git not found"; return 1; }

    read -p "Heroku app name: " APP_NAME
    if [ -z "$APP_NAME" ]; then
        print_error "App name required"
        return 1
    fi

    print_info "Pushing to Heroku..."
    git push heroku main

    print_success "Deployed to: https://$APP_NAME.herokuapp.com"
}

cloud_deploy() {
    print_info "Cloud Deployment (AWS/GCP/Azure)..."
    print_separator
    echo ""
    echo "  [1] AWS (ECR + ECS)"
    echo "  [2] Google Cloud (GCR + Cloud Run)"
    echo "  [3] Azure (ACR + App Service)"
    echo "  [0] Back"
    echo ""
    read -p "  Choose cloud provider (0-3): " cloud_choice

    case $cloud_choice in
        1)
            print_info "Building for AWS ECR..."
            read -p "ECR Repository URI: " ECR_URI
            docker build -t "$ECR_URI:latest" -f Dockerfile .
            docker push "$ECR_URI:latest"
            print_success "Pushed to ECR: $ECR_URI"
            ;;
        2)
            print_info "Building for Google Cloud..."
            read -p "GCR Image path (gcr.io/project/image): " GCR_PATH
            docker build -t "$GCR_PATH:latest" -f Dockerfile .
            docker push "$GCR_PATH:latest"
            print_success "Pushed to GCR: $GCR_PATH"
            ;;
        3)
            print_info "Building for Azure..."
            read -p "ACR Login Server: " ACR_SERVER
            docker build -t "$ACR_SERVER/open-monitor:latest" -f Dockerfile .
            docker push "$ACR_SERVER/open-monitor:latest"
            print_success "Pushed to ACR: $ACR_SERVER"
            ;;
        0) return ;;
        *) print_error "Invalid option" ;;
    esac
}

airflow_setup() {
    print_info "Airflow Setup..."
    print_separator
    echo ""
    echo "  [1] Initialize Airflow (Docker)"
    echo "  [2] Validate DAGs"
    echo "  [3] Start Scheduler Only"
    echo "  [0] Back"
    echo ""
    read -p "  Choose option (0-3): " af_choice

    case $af_choice in
        1)
            print_info "Initializing Airflow..."
            docker compose up airflow-init
            docker compose up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer
            print_success "Airflow started at http://localhost:8080"
            ;;
        2)
            print_info "Validating DAGs..."
            if check_command python3 || check_command python; then
                PYTHON=$(command -v python3 || command -v python)
                $PYTHON -c "
import sys
sys.path.insert(0, '.')
from airflow.dags import nvd_sync, euvd_sync, mitre_sync, daily_report, nvd_bulk_import
print('All DAGs validated successfully')
" 2>/dev/null || print_warning "DAG validation requires Airflow installed"
            fi
            ;;
        3)
            docker compose up -d airflow-scheduler
            print_success "Airflow scheduler started"
            ;;
        0) return ;;
        *) print_error "Invalid option" ;;
    esac
}

database_setup() {
    print_info "Database Setup..."
    print_separator
    echo ""
    echo "  [1] Initialize Database (SQLite/Dev)"
    echo "  [2] Initialize PostgreSQL"
    echo "  [3] Run Migrations"
    echo "  [4] Create Admin User"
    echo "  [5] Seed Sample Data"
    echo "  [6] Diagnose Database"
    echo "  [0] Back"
    echo ""
    read -p "  Choose option (0-6): " db_choice

    PYTHON=$(command -v python3 || command -v python)

    case $db_choice in
        1)
            print_info "Initializing database..."
            $PYTHON scripts/db/init_db.py
            print_success "Database initialized"
            ;;
        2)
            print_info "Initializing PostgreSQL..."
            $PYTHON scripts/db/init_postgres.py
            print_success "PostgreSQL initialized"
            ;;
        3)
            print_info "Running migrations..."
            flask db upgrade
            print_success "Migrations complete"
            ;;
        4)
            print_info "Creating admin user..."
            $PYTHON scripts/admin/create_admin.py
            print_success "Admin user created"
            ;;
        5)
            print_info "Seeding sample data..."
            $PYTHON scripts/db/seed_vulns.py
            $PYTHON scripts/db/seed_assets.py
            print_success "Sample data seeded"
            ;;
        6)
            print_info "Diagnosing database..."
            $PYTHON scripts/db/diagnose.py
            ;;
        0) return ;;
        *) print_error "Invalid option" ;;
    esac
}

cleanup_reset() {
    print_info "Cleanup & Reset..."
    print_separator
    echo ""
    echo "  [1] Stop all containers"
    echo "  [2] Remove containers + volumes"
    echo "  [3] Clear Python cache"
    echo "  [4] Reset SQLite database"
    echo "  [5] Full cleanup (all of the above)"
    echo "  [0] Back"
    echo ""
    read -p "  Choose option (0-5): " cl_choice

    case $cl_choice in
        1)
            docker compose down 2>/dev/null || true
            print_success "Containers stopped"
            ;;
        2)
            docker compose down -v 2>/dev/null || true
            print_success "Containers and volumes removed"
            ;;
        3)
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name "*.pyc" -delete 2>/dev/null || true
            rm -rf .pytest_cache 2>/dev/null || true
            print_success "Python cache cleared"
            ;;
        4)
            rm -f app.db instance/*.db 2>/dev/null || true
            print_success "SQLite database reset"
            ;;
        5)
            docker compose down -v 2>/dev/null || true
            find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
            find . -type f -name "*.pyc" -delete 2>/dev/null || true
            rm -rf .pytest_cache 2>/dev/null || true
            rm -f app.db instance/*.db 2>/dev/null || true
            print_success "Full cleanup complete"
            ;;
        0) return ;;
        *) print_error "Invalid option" ;;
    esac
}

# ============================================================================
# MAIN MENU
# ============================================================================

main_menu() {
    while true; do
        clear 2>/dev/null || true
        print_banner
        echo ""
        echo -e "  ${BOLD}[1]${NC} Desenvolvimento Local"
        echo -e "      └─ Python + SQLite + Hot reload"
        echo ""
        echo -e "  ${BOLD}[2]${NC} Python Local Completo"
        echo -e "      └─ Python + PostgreSQL + Gunicorn"
        echo ""
        echo -e "  ${BOLD}[3]${NC} Docker Local"
        echo -e "      └─ Docker Compose + All services"
        echo ""
        echo -e "  ${BOLD}[4]${NC} Docker Build"
        echo -e "      └─ Build container image"
        echo ""
        echo -e "  ${BOLD}[5]${NC} Heroku Deploy"
        echo -e "      └─ Git push heroku main"
        echo ""
        echo -e "  ${BOLD}[6]${NC} Cloud Deploy (AWS/GCP/Azure)"
        echo -e "      └─ Docker image push + Deploy"
        echo ""
        echo -e "  ${BOLD}[7]${NC} Airflow Setup"
        echo -e "      └─ Initialize DAGs + Scheduler"
        echo ""
        echo -e "  ${BOLD}[8]${NC} Database Setup"
        echo -e "      └─ Migrate + Seed + Admin create"
        echo ""
        echo -e "  ${BOLD}[9]${NC} Cleanup & Reset"
        echo -e "      └─ Remove containers, clear DB"
        echo ""
        echo -e "  ${BOLD}[0]${NC} Exit"
        echo ""
        print_separator
        read -p "  Choose an option (0-9): " choice

        case $choice in
            1) dev_local ;;
            2) python_full ;;
            3) docker_local ;;
            4) docker_build ;;
            5) heroku_deploy ;;
            6) cloud_deploy ;;
            7) airflow_setup ;;
            8) database_setup ;;
            9) cleanup_reset ;;
            0) echo "Goodbye!"; exit 0 ;;
            *) print_error "Invalid option. Try again." ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run
main_menu
