# Plano de Integração — Cisco Umbrella Reports

## 1. Objetivo
Incorporar ao SOC360 a funcionalidade de geração de relatórios Cisco Umbrella (originalmente standalone em `Relatorio Umbrela/`), utilizando o tema dark, sidebar, autenticação e padrões do sistema principal.

## 2. Análise do Subsistema Umbrella
| Componente | Descrição |
|------------|-----------|
| `umbrella_app/__init__.py` | Flask factory + rotas REST (`/api/organizations`, `/api/refresh-data`, `/api/generate-report`, `/api/reports`, `/download/<file>`) |
| `services/umbrella_api.py` | Cliente HTTP para API Cisco Umbrella com fallback mock |
| `services/report_generator.py` | Geração de relatórios `.docx` (python-docx) e conversão PDF via LibreOffice |
| `services/database.py` | SQLite puro (sqlite3) com tabelas: organizations, networks, roaming_computers, virtual_appliances, report_data, generated_reports |
| `templates/index.html` | UI standalone (não reutilizável diretamente) |
| `run.py` | Bootstrap do app standalone na porta 4447 |

## 3. Estratégia de Integração

### 3.1 Arquitetura
- **Blueprint**: `app/controllers/umbrella/` — segue o padrão dos controllers existentes (wazuh, fortinet).
- **Modelos**: Criar `app/models/umbrella/` com SQLAlchemy ORM para manter consistência com o restante da aplicação. Isso evita misturar SQLite puro com PostgreSQL/SQLite do Flask-SQLAlchemy.
- **Serviços**: `app/services/umbrella/` — adaptar `umbrella_api.py` e `report_generator.py` para usarem paths e configs do SOC360.
- **Templates**: `app/static/templates/umbrella/dashboard.html` — estende `base.html`, reutiliza cards, tabelas, modais e dark-theme do Wazuh.
- **Frontend JS**: `app/static/js/pages/umbrella/dashboard.js` — segue padrão do Wazuh (fetch API, Chart.js opcional).

### 3.2 Rotas (Blueprint `umbrella`, url_prefix=`/integrations/umbrella`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Dashboard principal (lista organizações + ações) |
| GET | `/api/organizations` | Lista organizações |
| GET | `/api/organization/<id>` | Detalhes de uma org |
| GET | `/api/refresh-data` | Busca dados (API ou mock) e persiste |
| POST | `/api/generate-report` | Gera relatório DOCX/PDF |
| GET | `/api/reports` | Lista relatórios gerados |
| GET | `/download/<filename>` | Download de arquivo |

### 3.3 Menu
Adicionar item na seção **Integrações** do `base.html`:
```html
<a href="{{ url_for('umbrella.dashboard') }}" class="nav-item nav-sub {% if request.blueprint == 'umbrella' %}active{% endif %}">
    <i class="fas fa-umbrella"></i>
    <span>Umbrella</span>
</a>
```

### 3.4 Modelos SQLAlchemy (novos)
- `UmbrellaOrganization`
- `UmbrellaNetwork`
- `UmbrellaRoamingComputer`
- `UmbrellaVirtualAppliance`
- `UmbrellaReportData`
- `UmbrellaGeneratedReport`

### 3.5 Configurações
Adicionar ao `BaseConfig`:
```python
UMBRELLA_USE_MOCK = os.environ.get('UMBRELLA_USE_MOCK', 'true').lower() == 'true'
UMBRELLA_API_KEY = os.environ.get('UMBRELLA_API_KEY', None)
UMBRELLA_API_SECRET = os.environ.get('UMBRELLA_API_SECRET', None)
UMBRELLA_REPORTS_DIR = os.environ.get('UMBRELLA_REPORTS_DIR', os.path.join(REPORTS_DIR, 'umbrella'))
```

### 3.6 Dependências
O `requirements.txt` do sistema principal já deve incluir (ou será adicionado):
- `python-docx`
- `requests` (já deve existir)

## 4. Fluxo de Uso Esperado
1. Usuário logado acessa **Integrações → Umbrella**
2. Dashboard exibe cards de organizações (mock ou API real)
3. Botão "Atualizar Dados" popula o banco via `/api/refresh-data`
4. Usuário seleciona organização, período e clica "Gerar Relatório"
5. Sistema coleta dados, gera `.docx` e tenta `.pdf`, lista para download

## 5. Checklist de Implementação
- [x] Analisar subsistema Umbrella
- [x] Analisar sistema principal (blueprints, models, templates, config)
- [ ] Criar modelos SQLAlchemy em `app/models/umbrella/`
- [ ] Criar serviços em `app/services/umbrella/`
- [ ] Criar controller blueprint em `app/controllers/umbrella/`
- [ ] Criar template `dashboard.html`
- [ ] Criar JS `dashboard.js`
- [ ] Atualizar `base.html` (menu)
- [ ] Registrar blueprint em `app/__init__.py`
- [ ] Adicionar configurações em `app/settings/base.py`
- [ ] Testar geração de relatório end-to-end
