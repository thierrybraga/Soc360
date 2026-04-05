const TEMPLATE_METADATA = {
    EXECUTIVE: {
        name: 'Resumo executivo',
        description: 'Visão de alto nível com foco em impacto, volume e prioridades para liderança.',
        audience: 'Executivos, gestão e comitês',
        outcome: 'Resumo claro para tomada de decisão e priorização.',
        highlights: ['Panorama geral', 'Indicadores-chave', 'Leitura rápida'],
        icon: 'fa-chart-line',
        defaultDays: 30,
        accent: 'primary'
    },
    TECHNICAL: {
        name: 'Relatório técnico',
        description: 'Detalhamento das vulnerabilidades e insumos para investigação e remediação.',
        audience: 'Analistas, SOC e times de infraestrutura',
        outcome: 'Base operacional para análise e correção.',
        highlights: ['Mais contexto técnico', 'Maior profundidade', 'Apoio à remediação'],
        icon: 'fa-code',
        defaultDays: 30,
        accent: 'warning'
    },
    RISK_ASSESSMENT: {
        name: 'Avaliação de risco',
        description: 'Cruza exposição, criticidade e impacto nos ativos para apoiar priorização.',
        audience: 'Gestão de risco e segurança',
        outcome: 'Leitura orientada a impacto e risco do negócio.',
        highlights: ['Ativos expostos', 'Risco agregado', 'Foco em priorização'],
        icon: 'fa-triangle-exclamation',
        defaultDays: 30,
        accent: 'danger'
    },
    COMPLIANCE: {
        name: 'Compliance',
        description: 'Apresenta aderência e lacunas com recorte para controles e auditoria.',
        audience: 'Governança, auditoria e compliance',
        outcome: 'Visão estruturada para evidências e acompanhamento.',
        highlights: ['Leitura de conformidade', 'Uso em auditoria', 'Acompanhamento de lacunas'],
        icon: 'fa-shield-alt',
        defaultDays: 90,
        accent: 'success'
    },
    TREND: {
        name: 'Análise de tendência',
        description: 'Mostra evolução de volume e severidade ao longo do tempo.',
        audience: 'Liderança técnica e times de melhoria contínua',
        outcome: 'Comparação histórica para medir progresso e sazonalidade.',
        highlights: ['Histórico comparativo', 'Detecção de padrões', 'Leitura temporal'],
        icon: 'fa-chart-bar',
        defaultDays: 90,
        accent: 'info'
    },
    INCIDENT: {
        name: 'Relatório de incidente',
        description: 'Estrutura um registro resumido do evento com contexto para resposta.',
        audience: 'Resposta a incidentes e liderança operacional',
        outcome: 'Base para comunicação do incidente e alinhamento das ações.',
        highlights: ['Contexto do evento', 'Comunicação objetiva', 'Registro de resposta'],
        icon: 'fa-bullhorn',
        defaultDays: 7,
        accent: 'secondary'
    }
};

class ReportsModule {
    constructor() {
        this.generateModalEl = document.getElementById('generate-modal');
        this.generateModalInstance = null;
        this.templates = [];
        this.lastStats = null;
        this.pollInterval = null;
        this.titleTouched = false;
        this.isSyncingTitle = false;
        this.state = { page: 1, search: '', type: '', status: '' };
        this.init();
    }

    async init() {
        if (this.generateModalEl && window.bootstrap) {
            this.generateModalInstance = new bootstrap.Modal(this.generateModalEl);
        }

        this.bindEvents();
        await this.loadTemplates();
        await Promise.all([this.loadStats(), this.loadReports()]);
        this.updateModalState();
    }

    bindEvents() {
        document.getElementById('generate-btn')?.addEventListener('click', () => this.openGenerateModal());
        document.getElementById('manual-generate-btn')?.addEventListener('click', () => this.openGenerateModal());
        document.getElementById('refresh-reports-btn')?.addEventListener('click', () => this.refreshReports());
        document.getElementById('modal-generate')?.addEventListener('click', () => this.generateReport());
        document.getElementById('empty-state')?.addEventListener('click', (event) => this.handleEmptyStateClick(event));
        document.getElementById('template-grid')?.addEventListener('click', (event) => this.handleTemplateClick(event));

        if (this.generateModalEl) {
            this.generateModalEl.addEventListener('hidden.bs.modal', () => this.resetGenerateForm());
        }

        let searchTimeout;
        document.getElementById('report-search')?.addEventListener('input', (event) => {
            clearTimeout(searchTimeout);
            this.state.search = event.target.value.trim();
            this.toggleSearchClear();
            searchTimeout = setTimeout(() => this.loadReports(1), 250);
        });

        document.getElementById('clear-search-btn')?.addEventListener('click', () => {
            const searchInput = document.getElementById('report-search');
            if (searchInput) {
                searchInput.value = '';
            }
            this.state.search = '';
            this.toggleSearchClear();
            this.loadReports(1);
        });

        document.getElementById('filter-type')?.addEventListener('change', (event) => {
            this.state.type = event.target.value;
            this.loadReports(1);
        });

        document.getElementById('filter-status')?.addEventListener('change', (event) => {
            this.state.status = event.target.value;
            this.loadReports(1);
        });

        document.getElementById('clear-filters-btn')?.addEventListener('click', () => this.clearFilters());

        document.getElementById('pagination')?.addEventListener('click', (event) => {
            const link = event.target.closest('.page-link');
            if (!link || link.parentElement.classList.contains('disabled')) {
                return;
            }

            event.preventDefault();
            const page = Number.parseInt(link.dataset.page, 10);
            if (!Number.isNaN(page)) {
                this.loadReports(page);
            }
        });

        document.getElementById('report-type')?.addEventListener('change', () => {
            this.syncTitleIfNeeded();
            this.applyTemplateDefaults();
            this.updateModalState();
        });

        document.getElementById('report-title')?.addEventListener('input', () => {
            if (!this.isSyncingTitle) {
                this.titleTouched = true;
            }
            this.updateModalState();
        });

        document.getElementById('report-description')?.addEventListener('input', () => this.updateModalState());
        document.getElementById('report-days')?.addEventListener('input', () => {
            this.syncPresetButtons();
            this.syncTitleIfNeeded();
            this.updateModalState();
        });

        document.getElementById('days-presets')?.addEventListener('click', (event) => {
            const button = event.target.closest('.days-preset');
            if (!button) {
                return;
            }

            const days = Number.parseInt(button.dataset.days, 10);
            const daysInput = document.getElementById('report-days');
            if (daysInput && !Number.isNaN(days)) {
                daysInput.value = days;
            }
            this.syncPresetButtons();
            this.syncTitleIfNeeded();
            this.updateModalState();
        });

        document.getElementById('opt-charts')?.addEventListener('change', () => this.updateModalState());
        document.getElementById('opt-details')?.addEventListener('change', () => this.updateModalState());

        document.getElementById('generate-form')?.addEventListener('submit', (event) => {
            event.preventDefault();
            this.generateReport();
        });

        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopAutoRefresh();
                return;
            }

            if (this.getActiveGenerationCount() > 0) {
                this.startAutoRefresh();
                this.refreshReports({ silent: true });
            }
        });
    }

    async loadTemplates() {
        try {
            const data = await OpenMonitor.api.get('/reports/api/templates');
            const templates = Array.isArray(data.templates) ? data.templates : [];
            this.templates = templates.map((template) => this.normalizeTemplate(template));
        } catch (error) {
            console.error('Failed to load templates:', error);
            this.templates = this.getFallbackTemplates();
        }

        if (this.templates.length === 0) {
            this.templates = this.getFallbackTemplates();
        }

        this.renderTemplateGrid();
    }

    normalizeTemplate(template) {
        const reportType = this.normalizeReportType(template.report_type);
        const meta = TEMPLATE_METADATA[reportType] || TEMPLATE_METADATA.EXECUTIVE;

        return {
            reportType,
            name: meta.name,
            description: template.description || meta.description,
            audience: meta.audience,
            outcome: meta.outcome,
            highlights: meta.highlights,
            icon: meta.icon,
            accent: meta.accent,
            defaultDays: template.parameters?.time_range_days || meta.defaultDays
        };
    }

    getFallbackTemplates() {
        return Object.entries(TEMPLATE_METADATA).map(([reportType, meta]) => ({
            reportType,
            name: meta.name,
            description: meta.description,
            audience: meta.audience,
            outcome: meta.outcome,
            highlights: meta.highlights,
            icon: meta.icon,
            accent: meta.accent,
            defaultDays: meta.defaultDays
        }));
    }

    renderTemplateGrid() {
        const container = document.getElementById('template-grid');
        if (!container) {
            return;
        }

        container.innerHTML = this.templates.map((template) => `
            <article class="template-card template-card--${template.accent}">
                <div class="template-card__icon">
                    <i class="fas ${template.icon}"></i>
                </div>
                <div class="template-card__body">
                    <div class="template-card__topline">
                        <h3>${template.name}</h3>
                        <span>${template.defaultDays} dias</span>
                    </div>
                    <p>${template.description}</p>
                    <ul class="template-card__meta">
                        ${template.highlights.map((item) => `<li>${item}</li>`).join('')}
                    </ul>
                </div>
                <div class="template-card__footer">
                    <small>${template.audience}</small>
                    <button class="btn btn-primary btn-sm" type="button" data-template="${template.reportType}">
                        Usar modelo
                    </button>
                </div>
            </article>
        `).join('');
    }

    handleTemplateClick(event) {
        const button = event.target.closest('[data-template]');
        if (!button) {
            return;
        }

        this.openGenerateModal(button.dataset.template);
    }

    handleEmptyStateClick(event) {
        const action = event.target.closest('[data-empty-action]');
        if (!action) {
            return;
        }

        if (action.dataset.emptyAction === 'generate') {
            this.openGenerateModal();
        }

        if (action.dataset.emptyAction === 'clear') {
            this.clearFilters();
        }
    }

    openGenerateModal(reportType = '') {
        this.resetGenerateForm();

        if (reportType) {
            const typeSelect = document.getElementById('report-type');
            if (typeSelect) {
                typeSelect.value = reportType;
            }
            this.applyTemplateDefaults();
        }

        this.updateModalState();
        this.generateModalInstance?.show();
    }

    resetGenerateForm() {
        const form = document.getElementById('generate-form');
        form?.reset();
        this.titleTouched = false;

        const typeSelect = document.getElementById('report-type');
        if (typeSelect) {
            typeSelect.value = '';
        }

        const daysInput = document.getElementById('report-days');
        if (daysInput) {
            daysInput.value = 30;
        }

        const chartsInput = document.getElementById('opt-charts');
        if (chartsInput) {
            chartsInput.checked = true;
        }

        const detailsInput = document.getElementById('opt-details');
        if (detailsInput) {
            detailsInput.checked = true;
        }

        this.syncPresetButtons();
        this.updateModalState();
    }

    applyTemplateDefaults() {
        const reportType = document.getElementById('report-type')?.value;
        const template = this.findTemplate(reportType);
        const daysInput = document.getElementById('report-days');

        if (template && daysInput) {
            daysInput.value = template.defaultDays;
        }

        this.setSuggestedTitle();
        this.syncPresetButtons();
    }

    findTemplate(reportType) {
        return this.templates.find((template) => template.reportType === reportType) || null;
    }

    syncPresetButtons() {
        const days = Number.parseInt(document.getElementById('report-days')?.value || '0', 10);

        document.querySelectorAll('.days-preset').forEach((button) => {
            const presetDays = Number.parseInt(button.dataset.days, 10);
            button.classList.toggle('is-active', presetDays === days);
        });
    }

    syncTitleIfNeeded() {
        const titleInput = document.getElementById('report-title');
        if (!titleInput) {
            return;
        }

        if (!this.titleTouched || !titleInput.value.trim()) {
            this.setSuggestedTitle();
        }
    }

    setSuggestedTitle() {
        const titleInput = document.getElementById('report-title');
        const reportType = document.getElementById('report-type')?.value;
        const template = this.findTemplate(reportType);

        if (!titleInput || !reportType || !template) {
            return;
        }

        const days = Number.parseInt(document.getElementById('report-days')?.value || template.defaultDays, 10) || template.defaultDays;
        const monthLabel = new Intl.DateTimeFormat('pt-BR', {
            month: 'short',
            year: 'numeric'
        }).format(new Date());

        this.isSyncingTitle = true;
        titleInput.value = `${template.name} - ${days} dias - ${monthLabel}`;
        this.isSyncingTitle = false;
    }

    updateModalState() {
        const reportType = document.getElementById('report-type')?.value || '';
        const title = document.getElementById('report-title')?.value.trim() || '';
        const description = document.getElementById('report-description')?.value.trim() || '';
        const days = Number.parseInt(document.getElementById('report-days')?.value || '30', 10) || 30;
        const includeCharts = Boolean(document.getElementById('opt-charts')?.checked);
        const includeDetails = Boolean(document.getElementById('opt-details')?.checked);
        const template = this.findTemplate(reportType);
        const metadata = template || TEMPLATE_METADATA[reportType] || null;

        const helperBadge = document.getElementById('template-badge');
        const helperTitle = document.getElementById('type-helper-title');
        const helperText = document.getElementById('type-helper-text');
        const helperList = document.getElementById('type-helper-list');

        if (metadata) {
            helperBadge.textContent = metadata.audience;
            helperTitle.textContent = metadata.name;
            helperText.textContent = metadata.description;
            helperList.innerHTML = metadata.highlights.map((item) => `<li>${item}</li>`).join('');
        } else {
            helperBadge.textContent = 'Selecione um modelo';
            helperTitle.textContent = 'Ainda sem modelo definido';
            helperText.textContent = 'Ao selecionar um tipo, mostramos o foco, a audiência e o resultado esperado.';
            helperList.innerHTML = '';
        }

        document.getElementById('preview-type-pill').textContent = metadata ? metadata.name : 'Tipo não definido';
        document.getElementById('preview-title').textContent = title || 'Defina um título para visualizar o resumo';
        document.getElementById('preview-description').textContent = description || (metadata ? metadata.description : 'O relatório aparecerá aqui com um resumo do escopo e das opções selecionadas.');
        document.getElementById('preview-audience').textContent = metadata ? metadata.audience : 'Selecione um tipo';
        document.getElementById('preview-days').textContent = `${days} dias`;
        document.getElementById('preview-includes').textContent = this.formatIncludedOptions(includeCharts, includeDetails);
        document.getElementById('preview-outcome').textContent = metadata ? metadata.outcome : 'Histórico atualizado e relatório pronto para revisão.';
        document.getElementById('preview-note').textContent = metadata
            ? `Ideal para ${metadata.audience.toLowerCase()}.`
            : 'Use um título objetivo para identificar rapidamente a finalidade do relatório no histórico.';
    }

    formatIncludedOptions(includeCharts, includeDetails) {
        const items = [];
        if (includeCharts) {
            items.push('gráficos');
        }
        if (includeDetails) {
            items.push('detalhamento técnico');
        }
        if (items.length === 0) {
            return 'Resumo enxuto';
        }
        if (items.length === 1) {
            return items[0];
        }
        return `${items[0]} e ${items[1]}`;
    }

    async loadStats() {
        try {
            const data = await OpenMonitor.api.get('/reports/api/stats');
            this.lastStats = data;

            const setStat = (id, value) => {
                const element = document.getElementById(id);
                if (!element) {
                    return;
                }
                element.textContent = value;
                element.classList.remove('skeleton-text', 'w-50');
            };

            setStat('stat-total', data.total || 0);
            setStat('stat-completed', data.by_status?.COMPLETED || 0);
            setStat('stat-executive', data.by_type?.EXECUTIVE || 0);
            setStat('stat-technical', data.by_type?.TECHNICAL || 0);

            this.updateGenerationBanner();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async loadReports(page = this.state.page, options = {}) {
        const container = document.getElementById('reports-list');
        const loading = document.getElementById('table-loading');
        const emptyState = document.getElementById('empty-state');
        const pagination = document.getElementById('pagination-container');
        const showLoader = !options.silent;

        this.state.page = page;

        if (showLoader && loading) {
            loading.style.display = 'flex';
        }
        if (!options.preserveTable && container && showLoader) {
            container.innerHTML = '';
        }
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        if (pagination) {
            pagination.style.display = 'none';
        }

        try {
            const params = { page: this.state.page };
            if (this.state.search) {
                params.search = this.state.search;
            }
            if (this.state.type) {
                params.type = this.state.type;
            }
            if (this.state.status) {
                params.status = this.state.status;
            }

            const data = await OpenMonitor.api.get('/reports/api/list', params);
            const items = Array.isArray(data.items) ? data.items : [];

            if (items.length > 0) {
                if (container) {
                    container.innerHTML = this.renderReportsTable(items);
                }
                this.renderPagination(data.page, data.pages);
            } else {
                this.renderEmptyState();
            }

            this.updateResultsSummary(data.total || 0, items.length);
            this.updateRefreshLabel();
        } catch (error) {
            console.error('Failed to load reports:', error);
            window.OpenMonitor?.showToast('Não foi possível carregar os relatórios.', 'error');
        } finally {
            if (loading) {
                loading.style.display = 'none';
            }
        }
    }

    renderReportsTable(items) {
        return `
            <div class="table-responsive">
                <table class="table table-hover align-middle reports-table">
                    <thead class="table-light">
                        <tr>
                            <th>Relatório</th>
                            <th>Tipo</th>
                            <th>Status</th>
                            <th>Escopo</th>
                            <th>Criado em</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${items.map((report) => this.renderReportRow(report)).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    renderReportRow(report) {
        const normalizedType = this.normalizeReportType(report.report_type);
        const template = this.findTemplate(normalizedType) || TEMPLATE_METADATA[normalizedType] || {};
        const status = this.getStatusMeta(report.status);
        const timeRange = report.filters?.time_range_days;
        const generationTime = report.generation_time_seconds ? `${Math.round(report.generation_time_seconds)}s` : 'n/d';
        const actions = [
            `
                <a href="/reports/${report.id}" class="btn btn-sm btn-outline-secondary" title="Abrir detalhes">
                    <i class="fas fa-eye"></i>
                </a>
            `
        ];

        if (report.has_pdf) {
            actions.push(`
                <a href="/reports/api/${report.id}/download" class="btn btn-sm btn-outline-primary" target="_blank" title="Baixar PDF">
                    <i class="fas fa-download"></i>
                </a>
            `);
        } else if (report.status === 'COMPLETED') {
            actions.push(`
                <button class="btn btn-sm btn-outline-secondary" type="button" disabled title="PDF ainda indisponível">
                    <i class="fas fa-ban"></i>
                </button>
            `);
        } else {
            actions.push(`
                <button class="btn btn-sm btn-outline-secondary" type="button" disabled title="Aguardando conclusão">
                    <i class="fas fa-spinner fa-spin"></i>
                </button>
            `);
        }

        return `
            <tr>
                <td data-label="Relatório">
                    <div class="report-title-cell">
                        <strong>${OpenMonitor.utils.escapeHtml(report.title)}</strong>
                        <small>${OpenMonitor.utils.escapeHtml(report.description || 'Sem descrição adicional.')}</small>
                    </div>
                </td>
                <td data-label="Tipo">
                    <span class="report-type-pill">
                        <i class="fas ${template.icon || 'fa-file-alt'}"></i>
                        ${template.name || report.report_type}
                    </span>
                </td>
                <td data-label="Status">
                    <span class="report-status report-status--${status.tone}">
                        <i class="fas ${status.icon}"></i>
                        ${status.label}
                    </span>
                </td>
                <td data-label="Escopo">
                    <div class="report-scope">
                        <strong>${timeRange ? `${timeRange} dias` : 'Escopo padrão'}</strong>
                        <small>Tempo de geração: ${generationTime}</small>
                    </div>
                </td>
                <td data-label="Criado em">
                    <small class="text-muted">
                        <i class="far fa-clock me-1"></i>${OpenMonitor.utils.formatDate(report.created_at)}
                    </small>
                </td>
                <td data-label="Ações">
                    <div class="btn-group" role="group" aria-label="Ações do relatório">
                        ${actions.join('')}
                    </div>
                </td>
            </tr>
        `;
    }

    renderEmptyState() {
        const emptyState = document.getElementById('empty-state');
        if (!emptyState) {
            return;
        }

        const hasFilters = Boolean(this.state.search || this.state.type || this.state.status);
        emptyState.innerHTML = hasFilters ? `
            <div class="empty-state-icon">
                <i class="fas fa-filter"></i>
            </div>
            <h5 class="empty-state-title">Nenhum relatório corresponde aos filtros atuais</h5>
            <p class="empty-state-text">Ajuste os filtros ou limpe a busca para voltar a ver o histórico completo.</p>
            <div class="empty-state__actions">
                <button class="btn btn-outline-secondary btn-sm" type="button" data-empty-action="clear">
                    <i class="fas fa-broom"></i>
                    Limpar filtros
                </button>
            </div>
        ` : `
            <div class="empty-state-icon">
                <i class="fas fa-file-alt"></i>
            </div>
            <h5 class="empty-state-title">Seu histórico de relatórios começa aqui</h5>
            <p class="empty-state-text">Use um dos modelos acima ou crie um relatório manualmente para iniciar o fluxo.</p>
            <div class="empty-state__actions">
                <button class="btn btn-primary btn-sm" type="button" data-empty-action="generate">
                    <i class="fas fa-plus"></i>
                    Gerar primeiro relatório
                </button>
            </div>
        `;
        emptyState.style.display = 'block';
    }

    updateResultsSummary(total, currentCount) {
        const summary = document.getElementById('results-summary');
        if (!summary) {
            return;
        }

        if (total === 0) {
            summary.textContent = this.state.search || this.state.type || this.state.status
                ? 'Nenhum resultado encontrado com os filtros atuais.'
                : 'Nenhum relatório gerado até o momento.';
            return;
        }

        const appliedFilters = [];
        if (this.state.search) {
            appliedFilters.push(`busca "${this.state.search}"`);
        }
        if (this.state.type) {
            appliedFilters.push(`tipo ${this.getTypeLabel(this.state.type).toLowerCase()}`);
        }
        if (this.state.status) {
            appliedFilters.push(`status ${this.getStatusMeta(this.state.status).label.toLowerCase()}`);
        }

        const filterSuffix = appliedFilters.length > 0 ? ` com ${appliedFilters.join(', ')}` : '';
        summary.textContent = `Mostrando ${currentCount} de ${total} relatório(s)${filterSuffix}.`;
    }

    renderPagination(currentPage, totalPages) {
        const pagination = document.getElementById('pagination');
        const container = document.getElementById('pagination-container');

        if (!pagination || !container || totalPages <= 1) {
            if (container) {
                container.style.display = 'none';
            }
            return;
        }

        container.style.display = 'block';
        let html = `
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage - 1}">Anterior</a>
            </li>
        `;

        for (let page = 1; page <= totalPages; page += 1) {
            if (page === 1 || page === totalPages || (page >= currentPage - 1 && page <= currentPage + 1)) {
                html += `
                    <li class="page-item ${page === currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" data-page="${page}">${page}</a>
                    </li>
                `;
            } else if (page === currentPage - 2 || page === currentPage + 2) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        html += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${currentPage + 1}">Próxima</a>
            </li>
        `;
        pagination.innerHTML = html;
    }

    clearFilters() {
        this.state = { ...this.state, page: 1, search: '', type: '', status: '' };

        const searchInput = document.getElementById('report-search');
        const typeSelect = document.getElementById('filter-type');
        const statusSelect = document.getElementById('filter-status');

        if (searchInput) {
            searchInput.value = '';
        }
        if (typeSelect) {
            typeSelect.value = '';
        }
        if (statusSelect) {
            statusSelect.value = '';
        }

        this.toggleSearchClear();
        this.loadReports(1);
    }

    toggleSearchClear() {
        const clearButton = document.getElementById('clear-search-btn');
        if (clearButton) {
            clearButton.style.display = this.state.search ? 'inline-flex' : 'none';
        }
    }

    updateGenerationBanner() {
        const banner = document.getElementById('generation-banner');
        const title = document.getElementById('generation-banner-title');
        const text = document.getElementById('generation-banner-text');
        if (!banner || !title || !text) {
            return;
        }

        const activeCount = this.getActiveGenerationCount();
        const failedCount = this.lastStats?.by_status?.FAILED || 0;

        if (activeCount > 0) {
            title.textContent = `${activeCount} relatório(s) em processamento`;
            text.textContent = 'A atualização automática está ativa para que você acompanhe o andamento sem recarregar a página.';
            banner.style.display = 'grid';
            this.startAutoRefresh();
            return;
        }

        this.stopAutoRefresh();

        if (failedCount > 0) {
            title.textContent = 'Nenhuma geração em andamento';
            text.textContent = `${failedCount} relatório(s) falharam recentemente. Revise o histórico para identificar e tentar novamente.`;
            banner.style.display = 'grid';
            return;
        }

        banner.style.display = 'none';
    }

    updateRefreshLabel() {
        const label = document.getElementById('last-refresh-label');
        if (!label) {
            return;
        }

        const time = new Intl.DateTimeFormat('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date());
        label.textContent = `Atualizado às ${time}`;
    }

    getActiveGenerationCount() {
        if (!this.lastStats?.by_status) {
            return 0;
        }
        return (this.lastStats.by_status.PENDING || 0) + (this.lastStats.by_status.GENERATING || 0);
    }

    startAutoRefresh() {
        if (this.pollInterval) {
            return;
        }
        this.pollInterval = window.setInterval(() => {
            this.refreshReports({ silent: true });
        }, 10000);
    }

    stopAutoRefresh() {
        if (!this.pollInterval) {
            return;
        }
        window.clearInterval(this.pollInterval);
        this.pollInterval = null;
    }

    async refreshReports(options = {}) {
        await Promise.all([
            this.loadStats(),
            this.loadReports(this.state.page, { silent: options.silent })
        ]);
    }

    async generateReport() {
        const title = document.getElementById('report-title')?.value.trim();
        const type = document.getElementById('report-type')?.value;
        const days = Number.parseInt(document.getElementById('report-days')?.value || '30', 10) || 30;

        if (!title || !type) {
            window.OpenMonitor?.showToast('Preencha o título e selecione um tipo de relatório.', 'warning');
            return;
        }

        const button = document.getElementById('modal-generate');
        const originalText = button?.innerHTML || '';
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando relatório...';
        }

        try {
            const payload = {
                title,
                report_type: type,
                description: document.getElementById('report-description')?.value.trim() || '',
                parameters: {
                    time_range_days: days,
                    include_charts: Boolean(document.getElementById('opt-charts')?.checked),
                    include_details: Boolean(document.getElementById('opt-details')?.checked)
                }
            };

            const response = await OpenMonitor.api.post('/reports/api/generate', payload);
            this.generateModalInstance?.hide();

            const wasCompleted = response?.report?.status === 'COMPLETED';
            window.OpenMonitor?.showToast(
                wasCompleted ? 'Relatório gerado com sucesso.' : 'A geração do relatório foi iniciada.',
                'success'
            );

            await this.refreshReports();
        } catch (error) {
            console.error('Generation failed:', error);
            window.OpenMonitor?.showToast(error.message || 'Não foi possível gerar o relatório.', 'error');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
        }
    }

    normalizeReportType(reportType) {
        const typeMap = {
            EXECUTIVE_SUMMARY: 'EXECUTIVE',
            TECHNICAL_REPORT: 'TECHNICAL',
            COMPLIANCE_REPORT: 'COMPLIANCE',
            TREND_ANALYSIS: 'TREND'
        };
        return typeMap[reportType] || reportType;
    }

    getTypeLabel(reportType) {
        const normalized = this.normalizeReportType(reportType);
        return TEMPLATE_METADATA[normalized]?.name || normalized;
    }

    getStatusMeta(status) {
        const map = {
            COMPLETED: { label: 'Concluído', tone: 'success', icon: 'fa-circle-check' },
            PENDING: { label: 'Pendente', tone: 'warning', icon: 'fa-hourglass-half' },
            FAILED: { label: 'Falhou', tone: 'danger', icon: 'fa-circle-exclamation' },
            GENERATING: { label: 'Gerando', tone: 'info', icon: 'fa-spinner' }
        };
        return map[status] || { label: status, tone: 'secondary', icon: 'fa-circle' };
    }
}

const reportsModule = new ReportsModule();
