# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ==========================================
# PRODUCTION STAGE
# ==========================================
FROM python:3.11-slim-bookworm AS production

LABEL maintainer="Open-Monitor Team" \
      version="3.0.0" \
      description="Enterprise Cybersecurity Vulnerability Management Platform"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    APP_HOME=/app \
    APP_USER=openmonitor \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_APP="app:create_app" \
    FLASK_DEBUG=0 \
    PORT=5000

# Dependências de runtime (incluindo requisitos do WeasyPrint)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libffi8 \
    libssl3 \
    curl \
    ca-certificates \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-pango-1.0 \
    fonts-liberation \
    fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Cria usuário não-root e estrutura de diretórios
RUN groupadd --gid 1000 ${APP_USER} && \
    useradd --uid 1000 --gid ${APP_USER} --shell /bin/bash --create-home ${APP_USER} && \
    mkdir -p ${APP_HOME}/{logs,uploads,reports,instance} && \
    chown -R ${APP_USER}:${APP_USER} ${APP_HOME}

# Copia venv otimizada do builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR ${APP_HOME}

# Copia código fonte
COPY --chown=${APP_USER}:${APP_USER} . .

# Entrypoint — strip CRLF (safety net for Windows checkouts)
COPY --chown=${APP_USER}:${APP_USER} infra/docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh && chown ${APP_USER}:${APP_USER} /entrypoint.sh

# Static file seed — copied to a path NOT covered by the soc360-static volume.
# The entrypoint syncs this into /app/app/static (the volume) on every startup,
# so rebuilt images automatically propagate CSS/JS/template changes without
# requiring a manual `docker volume rm open-cve-report_soc360-static`.
RUN cp -rp ${APP_HOME}/app/static ${APP_HOME}/app/static_seed && \
    chown -R ${APP_USER}:${APP_USER} ${APP_HOME}/app/static_seed

USER ${APP_USER}

EXPOSE 5000

# Healthcheck nativo
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://localhost:${PORT:-5000}/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--threads", "2", \
     "--worker-class", "gthread", \
     "--worker-tmp-dir", "/dev/shm", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance", \
     "app:create_app()"]