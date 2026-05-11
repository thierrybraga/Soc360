# Scripts — Open-Monitor v3.0 / SOC360

## Deploy

### Linux / Oracle Linux
```bash
chmod +x scripts/deploy-linux.sh

# Core stack (nginx, app, celery, redis)
./scripts/deploy-linux.sh start
./scripts/deploy-linux.sh stop
./scripts/deploy-linux.sh restart
./scripts/deploy-linux.sh rebuild     # sem cache
./scripts/deploy-linux.sh status
./scripts/deploy-linux.sh logs [service]
./scripts/deploy-linux.sh update      # pull base images + backup
./scripts/deploy-linux.sh rollback    # restaurar último backup
./scripts/deploy-linux.sh clean       # remove volumes

# Com overlays opcionais
./scripts/deploy-linux.sh start --with-ollama
./scripts/deploy-linux.sh start --with-airflow
./scripts/deploy-linux.sh start --with-ollama --with-airflow
```

### Windows (PowerShell)
```powershell
.\scripts\deploy-windows.ps1 start
.\scripts\deploy-windows.ps1 stop
.\scripts\deploy-windows.ps1 restart
.\scripts\deploy-windows.ps1 status
.\scripts\deploy-windows.ps1 rollback
```

## Secrets
```bash
# Gerar secrets iniciais (cria secrets/secret_key.txt e secrets/redis_password.txt)
python scripts/generate-secrets.py

# Rotacionar secrets em produção
chmod +x scripts/rotate-secrets.sh
./scripts/rotate-secrets.sh
```

## NVD Sync
```bash
# Sync incremental (últimos 30 dias)
python scripts/run_nvd_sync.py

# Full sync seguro (com controle de rate limit)
python scripts/run_full_sync_safe.py

# Resetar status de sync travado
python scripts/reset_sync_status.py
```

## Celery Worker (referência interna)
O arquivo `scripts/workers/celery_worker.py` é usado pelos containers Docker:
```bash
# Executado automaticamente pelo docker-compose
celery -A scripts.workers.celery_worker.celery worker --loglevel=info
celery -A scripts.workers.celery_worker.celery beat --loglevel=info
```

## Troubleshooting

**Permission denied no Linux:** `chmod +x scripts/deploy-linux.sh`

**Redis no Windows:** defina `REDIS_PASSWORD` no `.env` antes de subir o stack.

**Portas em uso:** o script verifica 80 e 443 automaticamente. Para Ollama/Airflow, as portas 11434/8080 são verificadas quando os overlays estão ativos.
