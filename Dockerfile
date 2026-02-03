# Open-Monitor v3.0 - Production Dockerfile
# Multi-stage build for optimized image size

# =============================================================================
# Stage 1: Builder - Install dependencies and build assets
# =============================================================================
FROM python:3.11-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# =============================================================================
# Stage 2: Production - Minimal runtime image
# =============================================================================
FROM python:3.11-slim-bookworm AS production

# Labels for container metadata
LABEL maintainer="Open-Monitor Team" \
      version="3.0.0" \
      description="Enterprise Cybersecurity Vulnerability Management Platform"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    APP_HOME=/app \
    APP_USER=openmonitor \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libssl3 \
    curl \
    wget \
    ca-certificates \
    # WeasyPrint dependencies for PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-pango-1.0 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 ${APP_USER} && \
    useradd --uid 1000 --gid ${APP_USER} --shell /bin/bash --create-home ${APP_USER}

# Create application directories
RUN mkdir -p ${APP_HOME} \
             ${APP_HOME}/logs \
             ${APP_HOME}/uploads \
             ${APP_HOME}/reports \
             ${APP_HOME}/instance && \
    chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR ${APP_HOME}

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . .

# Copy entrypoint script
COPY --chown=${APP_USER}:${APP_USER} docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create healthcheck script
RUN echo '#!/bin/bash\ncurl -sf http://localhost:${PORT:-5000}/health || exit 1' > /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /healthcheck.sh

# Set default environment
ENV FLASK_APP=app:create_app \
    FLASK_ENV=production \
    PORT=5000

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command: run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", \
     "--worker-class", "gthread", "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", \
     "--max-requests-jitter", "50", "--access-logfile", "-", \
     "--error-logfile", "-", "--capture-output", "--enable-stdio-inheritance", \
     "app:create_app()"]

# =============================================================================
# Stage 3: Development - Full development environment
# =============================================================================
FROM production AS development

# Switch to root for package installation
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    less \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install \
    pytest \
    pytest-cov \
    pytest-flask \
    pytest-asyncio \
    black \
    flake8 \
    isort \
    mypy \
    ipython \
    watchdog

# Switch back to app user
USER ${APP_USER}

# Development environment
ENV FLASK_ENV=development \
    FLASK_DEBUG=1

# Override command for development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]
