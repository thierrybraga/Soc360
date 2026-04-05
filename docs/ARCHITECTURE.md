# Open-Monitor - Architecture

## Overview

Open-Monitor is an enterprise vulnerability management platform built with Flask, following the Application Factory pattern with a modular architecture.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Flask 3.0 (Python 3.11+) |
| Database | PostgreSQL 15 (dual-database) + SQLite (dev) |
| Cache | Redis 7 |
| Task Queue | Celery + Apache Airflow |
| Web Server | Gunicorn + Nginx |
| Containers | Docker + Docker Compose |

## Database Architecture

The application uses a **dual-database** design:

- **Core DB** (`openmonitor_core`): Users, roles, assets, monitoring rules, reports, audit logs
- **Public DB** (`openmonitor_public`): CVE/NVD vulnerability data, CVSS metrics, references, weaknesses

This separation allows the public vulnerability data to scale independently.

## Application Structure

```
app/
├── __init__.py          # Application Factory (create_app)
├── controllers/         # Route handlers (Blueprints)
│   ├── core/            # Dashboard, home
│   ├── auth/            # Authentication
│   ├── api/             # REST API v1
│   ├── nvd/             # NVD vulnerabilities
│   ├── inventory/       # Asset management
│   ├── monitoring/      # Monitoring rules
│   ├── reports/         # Report generation
│   ├── analytics/       # Analytics dashboard
│   ├── euvd/            # EU Vulnerability DB
│   ├── mitre/           # MITRE ATT&CK
│   └── fortinet/        # Fortinet integration
├── models/              # SQLAlchemy ORM models
│   ├── auth/            # User, Role, UserRole
│   ├── inventory/       # Asset, Vendor, Category
│   ├── nvd/             # Vulnerability, CVSS, Reference
│   ├── monitoring/      # MonitoringRule, Alert, Report
│   ├── mitre/           # MITRE ATT&CK models
│   └── system/          # BaseModel, SyncMetadata, Enums
├── services/            # Business logic layer
│   ├── core/            # Base sync, cache, email, AI
│   ├── nvd/             # NVD sync & bulk import
│   ├── inventory/       # Asset correlation
│   ├── monitoring/      # Alerts, risk reports
│   ├── mitre/           # MITRE enrichment
│   ├── fortinet/        # Fortinet matching
│   └── euvd/            # EUVD sync
├── forms/               # WTForms form classes
├── schemas/             # Marshmallow serialization
├── extensions/          # Flask extension init (db, login, csrf)
├── jobs/                # Background jobs (NVD, EUVD, MITRE fetchers)
├── tasks/               # Celery task definitions
├── utils/               # Helpers, security, decorators
├── settings/            # Environment configs (base, dev, prod)
├── templates/           # Jinja2 HTML templates
└── static/              # CSS, JS, images
```

## Data Flow

```
NVD/EUVD/MITRE APIs
       │
       ▼
  Airflow DAGs (scheduled)
       │
       ▼
  Flask API Endpoints
       │
       ▼
  Services Layer (sync, enrich, correlate)
       │
       ▼
  PostgreSQL (core + public)
       │
       ▼
  Controllers → Templates (user-facing)
```

## Key Integrations

- **NVD API** (NIST): CVE vulnerability data with incremental + full sync
- **EUVD**: European vulnerability database enrichment
- **MITRE ATT&CK**: Threat framework enrichment
- **Fortinet**: Vendor-specific advisory matching
- **OpenAI**: AI-powered risk reports and analysis
- **Redis**: Caching layer for API responses and sessions
