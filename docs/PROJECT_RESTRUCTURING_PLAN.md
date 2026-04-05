# Open-Monitor - Plano de Reestruturação Completa

## 📋 OBJETIVO
Consolidar, padronizar e otimizar a estrutura do projeto Open-Monitor para suportar:
- ✅ Apache Airflow Integration
- ✅ Multi-environment deployment (Dev, Local, Heroku, Cloud, Docker)
- ✅ Clean Architecture
- ✅ Proper Documentation
- ✅ Interactive deployment menu (Linux, Windows, Oracle)

---

## 🔍 ANÁLISE ATUAL - PROBLEMAS ENCONTRADOS

### 1. **Estrutura Duplicada**
```
ROOT/
├── __init__.py                          ❌ Duplicado
├── controllers/                         ❌ Duplicado (deve estar em app/)
├── app/
│   ├── __init__.py                      ✅ Correto
│   ├── controllers/                     ✅ Correto
│   ├── forms/                           ✅ Correto
│   ├── models/                          ✅ Correto
│   └── ...mais pastas
├── extensions/                          ❌ Duplicado (deve estar em app/)
├── forms/                               ❌ Duplicado (deve estar em app/)
├── models/                              ❌ Duplicado (deve estar em app/)
└── ...
```

### 2. **Scripts .py Desorganizados na Raiz**
- `app.py` vs `run.py` - qual usar?
- `init_admin.py`, `init_db.py`, `init_postgres_db.py` - redundantes
- `auto_sync_check.py`, `force_full_nvd_sync.py`, `trigger_nvd_sync.py` - falta padronização
- `setup_local.py`, `seed_assets.py`, `seed_fortinet.py`, `seed_vulns.py` - sem organização

### 3. **Documentação Fragmentada**
- Múltiplos `.md` sem padronização
- Falta de README estruturado
- Sem ARCHITECTURE.md, CONTRIBUTING.md, DEPLOYMENT.md

### 4. **Arquivos Órfãos/Redundantes**
- Pasta `.claude/worktrees/` - estrutura de trabalho temporária
- `auth_controller.py` corrompido
- Múltiplos `conftest.py`
- Arquivos de teste duplicados

### 5. **Falta de Standardização**
- Requirements não consolidados
- Configurações espalhadas
- Variáveis de ambiente (.env) mal organizadas

---

## 📐 ESTRUTURA ALVO

```
open-monitor/
│
├── 📂 .github/                          # GitHub Actions, ISSUE_TEMPLATE
├── 📂 .vscode/                          # Configurações VS Code
│
├── 📂 docs/                             # 📚 Documentação Consolidada
│   ├── ARCHITECTURE.md                  # Arquitetura do projeto
│   ├── CONTRIBUTING.md                  # Diretrizes de contribuição
│   ├── DEPLOYMENT.md                    # Guia de deployment
│   ├── API.md                           # Documentação de API
│   ├── DATABASE.md                      # Schema do banco
│   ├── AIRFLOW.md                       # Integração Airflow
│   └── TROUBLESHOOTING.md               # Resolução de problemas
│
├── 📂 infra/                            # 🏗️ Infraestrutura
│   ├── docker/
│   │   ├── Dockerfile                   # Build da aplicação
│   │   ├── Dockerfile.airflow           # Build do Airflow
│   │   └── docker-compose.yml
│   ├── k8s/                             # Kubernetes manifests (futuro)
│   └── terraform/                       # IaC (futuro)
│
├── 📂 scripts/                          # 🔧 Scripts Utilitários
│   ├── db/
│   │   ├── init_db.py                   # Inicializar BD
│   │   ├── migrate.py                   # Migrações
│   │   └── seed.py                      # Popular dados
│   ├── admin/
│   │   ├── create_admin.py              # Criar usuário admin
│   │   └── manage_roles.py              # Gerenciar roles
│   ├── airflow/
│   │   ├── setup_dags.py                # Configurar DAGs
│   │   └── validate_dags.py             # Validar DAGs
│   ├── docker/
│   │   ├── build.sh                     # Build local
│   │   └── cleanup.sh                   # Limpeza
│   ├── deploy.sh                        # 🚀 Menu interativo principal
│   └── utils.sh                         # Funções auxiliares
│
├── 📂 app/                              # 💻 Aplicação Principal (Flask)
│   ├── __init__.py
│   ├── config.py                        # Configuração centralizada
│   ├── wsgi.py                          # Entry point produção
│   │
│   ├── controllers/                     # 🎮 Rotas/Controllers
│   │   ├── __init__.py
│   │   ├── core.py                      # Home, Dashboard
│   │   ├── auth.py                      # Login, Logout, Register
│   │   ├── assets.py                    # Gerenciamento de Assets
│   │   ├── monitoring.py                # Monitoramento
│   │   ├── vulnerabilities.py           # Vulnerabilidades
│   │   ├── reports.py                   # Relatórios
│   │   ├── api/                         # API REST
│   │   │   ├── __init__.py
│   │   │   ├── v1.py                    # Endpoints v1
│   │   │   └── v2.py                    # Endpoints v2 (futuro)
│   │   └── admin.py                     # Admin panel
│   │
│   ├── models/                          # 🗄️ ORM Models
│   │   ├── __init__.py
│   │   ├── base.py                      # Base Model
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── asset.py
│   │   ├── vulnerability.py
│   │   ├── monitoring.py
│   │   └── ...
│   │
│   ├── schemas/                         # 📋 Marshmallow Schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── asset.py
│   │   └── ...
│   │
│   ├── forms/                           # 📝 WTForms
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── auth.py
│   │   ├── asset.py
│   │   └── ...
│   │
│   ├── services/                        # ⚙️ Business Logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── asset_service.py
│   │   ├── nvd_service.py               # NVD API integration
│   │   ├── monitoring_service.py
│   │   ├── email_service.py
│   │   └── ...
│   │
│   ├── tasks/                           # 📊 Celery/Airflow Tasks
│   │   ├── __init__.py
│   │   ├── nvd_sync.py                  # NVD Sync Task
│   │   ├── monitoring.py                # Monitoring Task
│   │   └── reports.py                   # Report Generation
│   │
│   ├── extensions/                      # 🔌 Flask Extensions
│   │   ├── __init__.py
│   │   ├── database.py                  # SQLAlchemy
│   │   ├── migrate.py                   # Alembic
│   │   ├── login.py                     # Flask-Login
│   │   ├── csrf.py                      # CSRF Protection
│   │   ├── cache.py                     # Redis/Caching
│   │   └── rate_limit.py                # Rate Limiting
│   │
│   ├── utils/                           # 🛠️ Utilitários
│   │   ├── __init__.py
│   │   ├── decorators.py
│   │   ├── validators.py
│   │   ├── security.py
│   │   ├── pagination.py
│   │   ├── logging.py
│   │   └── helpers.py
│   │
│   ├── templates/                       # 🎨 Jinja2 Templates
│   │   ├── base.html
│   │   ├── pages/
│   │   ├── components/
│   │   └── emails/
│   │
│   └── static/                          # 📦 Assets Estáticos
│       ├── css/
│       ├── js/
│       ├── images/
│       └── vendor/
│
├── 📂 airflow/                          # 🌬️ Apache Airflow DAGs & Config
│   ├── dags/
│   │   ├── __init__.py
│   │   ├── nvd_sync.py                  # DAG: NVD Sync
│   │   ├── monitoring.py                # DAG: Monitoring
│   │   ├── reports.py                   # DAG: Report Generation
│   │   └── helpers.py
│   ├── config/
│   │   ├── airflow.cfg
│   │   └── webserver.yml
│   ├── plugins/
│   │   ├── operators/
│   │   └── hooks/
│   └── requirements.txt
│
├── 📂 tests/                            # ✅ Testes Unitários & Integração
│   ├── __init__.py
│   ├── conftest.py                      # Configuração pytest
│   ├── unit/
│   │   ├── services/
│   │   ├── models/
│   │   ├── controllers/
│   │   └── utils/
│   ├── integration/
│   │   ├── api/
│   │   └── database/
│   ├── e2e/
│   │   └── workflows/
│   └── fixtures/
│
├── 📂 migrations/                       # 🔄 Database Migrations (Alembic)
│   ├── versions/
│   ├── alembic.ini
│   └── env.py
│
├── 📂 config/                           # ⚙️ Configurações
│   ├── __init__.py
│   ├── base.py                          # Base config
│   ├── development.py                   # Dev config
│   ├── testing.py                       # Test config
│   ├── production.py                    # Prod config
│   └── airflow.py                       # Airflow config
│
├── 📂 .env.example                      # Variáveis de ambiente exemplo
├── 📂 .env                              # Variáveis de ambiente (gitignored)
├── 📂 .gitignore                        # Git ignore
├── 📂 docker-compose.yml                # Docker Compose principal
├── 📂 Dockerfile                        # Dockerfile principal
│
├── 📄 README.md                         # 📖 README Principal
├── 📄 CHANGELOG.md                      # 📝 Log de mudanças
├── 📄 LICENSE                           # Licença
│
├── 📄 requirements.txt                  # 📦 Dependências Base
├── 📄 requirements-dev.txt              # 📦 Dependências Dev
├── 📄 requirements-airflow.txt          # 📦 Dependências Airflow
│
├── 📄 pyproject.toml                    # Python Project Config
├── 📄 setup.py                          # Setup (se necessário)
├── 📄 tox.ini                           # Tox config para testes
├── 📄 pytest.ini                        # Pytest config
│
├── 📄 Makefile                          # Comandos úteis
├── 📄 .flake8                           # Linting config
├── 📄 .pylintrc                         # Pylint config
│
└── 🚀 manage.py (futuro)                # CLI para administração (Click/Typer)
```

---

## 📝 PLANO DE EXECUÇÃO (FASES)

### **FASE 1: Preparação & Análise (30 min)**
- [ ] Backup completo do projeto
- [ ] Criar estrutura de pastas alvo
- [ ] Documentar arquivos órfãos
- [ ] Listar duplicatas

### **FASE 2: Consolidação de Código (1-2 horas)**
- [ ] Eliminar estrutura root duplicada (controllers/, forms/, models/, etc.)
- [ ] Fazer consolidação correta em app/
- [ ] Organizar scripts em scripts/
- [ ] Corrigir auth_controller.py corrompido
- [ ] Atualizar todos os imports

### **FASE 3: Organização de Documentação (30 min)**
- [ ] Consolidar docs em docs/
- [ ] Criar ARCHITECTURE.md, CONTRIBUTING.md, DEPLOYMENT.md
- [ ] Padronizar README

### **FASE 4: Airflow Integration (1 hora)**
- [ ] Estruturar airflow/ com dags/
- [ ] Criar operadores customizados
- [ ] Documentação Airflow

### **FASE 5: Scripts & Menu Interativo (1 hora)**
- [ ] Consolidar scripts em scripts/
- [ ] Criar deploy.sh interativo com suporte:
  - Windows (Git Bash ou WSL)
  - Linux/Oracle Linux
  - macOS
- [ ] Criar submenu para cada opção

### **FASE 6: Docker & Infraestrutura (1 hora)**
- [ ] Reorganizar Dockerfile
- [ ] docker-compose.yml completo
- [ ] Build scripts para cada ambiente

### **FASE 7: Configurações & Requirements (30 min)**
- [ ] Consolidar requirements
- [ ] Centralizar configs em config/
- [ ] Setup .env.example

### **FASE 8: Testes & Validação (30 min)**
- [ ] Reorganizar testes
- [ ] Corrigir imports
- [ ] Validar toda a estrutura

---

## 🔐 RISCOS & MITIGAÇÃO

| Risco | Impacto | Mitigação |
|-------|--------|-----------|
| Breaking imports | 🔴 Alto | Validar todos imports antes de mover |
| Perda de código | 🔴 Alto | Backup completo inicial |
| Conflitos duplicatas | 🔴 Alto | Script para identificar diferenças |
| Downtime | 🟡 Médio | Teste em branch separada |

---

## ✅ CRITÉRIOS DE SUCESSO

- ✅ Sem arquivos órfãos
- ✅ Sem duplicatas
- ✅ Todos imports funcionando
- ✅ Documentação consolidada
- ✅ Deploy menu funcional
- ✅ Airflow integrado
- ✅ Testes passando
- ✅ Projeto executável

---

## 📊 ESTIMATIVA

| Fase | Tempo |
|------|-------|
| 1 - Preparação | 30 min |
| 2 - Consolidação | 2 horas |
| 3 - Documentação | 30 min |
| 4 - Airflow | 1 hora |
| 5 - Scripts | 1 hora |
| 6 - Docker | 1 hora |
| 7 - Configs | 30 min |
| 8 - Testes | 30 min |
| **TOTAL** | **~7 horas** |

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ Revisar este plano
2. ⏳ Aprovar a estratégia
3. 🔨 Executar Fases 1-8 sequencialmente
4. 📊 Documentar todo progresso
5. ✓ Validação final

---

**Prepared:** 2026-04-03
**Status:** 🟡 PLANNING
**Next:** Aguardando aprovação para iniciar Fase 1
