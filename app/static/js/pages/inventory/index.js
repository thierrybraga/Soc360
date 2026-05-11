'use strict';

const inventoryState = {
    page: 1,
    perPage: 50,
    totalItems: 0,
    totalPages: 1,
    sort: { column: null, direction: 'asc' },
    filters: {
        search: '',
        type: '',
        criticality: '',
        status: ''
    }
};

document.addEventListener('DOMContentLoaded', () => {
    bindInventoryEvents();
    syncInitialControls();
    loadAssets();
    loadStats();
});

function bindInventoryEvents() {
    document.getElementById('scan-all-btn')?.addEventListener('click', () => scanAssets());
    document.getElementById('clear-filters-btn')?.addEventListener('click', clearFilters);
    document.getElementById('manage-categories-btn')?.addEventListener('click', loadCategories);
    document.getElementById('create-category-form')?.addEventListener('submit', createCategory);
    document.getElementById('per-page-select')?.addEventListener('change', event => {
        inventoryState.perPage = Number(event.target.value) || 50;
        inventoryState.page = 1;
        loadAssets();
    });

    const searchInput = document.getElementById('asset-search');
    if (searchInput) {
        searchInput.addEventListener('input', OpenMonitor.utils.debounce(event => {
            inventoryState.filters.search = event.target.value.trim();
            inventoryState.page = 1;
            loadAssets();
        }, 300));
    }

    ['asset-type', 'asset-criticality', 'asset-status'].forEach(id => {
        document.getElementById(id)?.addEventListener('change', () => {
            inventoryState.filters.type = document.getElementById('asset-type')?.value || '';
            inventoryState.filters.criticality = document.getElementById('asset-criticality')?.value || '';
            inventoryState.filters.status = document.getElementById('asset-status')?.value || '';
            inventoryState.page = 1;
            updateActiveFilters();
            loadAssets();
        });
    });

    document.getElementById('assets-table-body')?.addEventListener('click', event => {
        const actionButton = event.target.closest('[data-action]');
        if (!actionButton) {
            return;
        }

        const assetId = actionButton.dataset.id;
        if (!assetId) {
            return;
        }

        if (actionButton.dataset.action === 'view') {
            window.location.href = `/assets/${assetId}`;
            return;
        }

        if (actionButton.dataset.action === 'scan') {
            scanAssets([Number(assetId)]);
        }
    });

    document.querySelectorAll('#assets-table thead .sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (!col) return;
            if (inventoryState.sort.column === col) {
                inventoryState.sort.direction = inventoryState.sort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                inventoryState.sort.column = col;
                inventoryState.sort.direction = 'asc';
            }
            updateSortIcons();
            loadAssets();
        });
    });

    document.getElementById('pagination')?.addEventListener('click', event => {
        const button = event.target.closest('[data-page-number]');
        if (!button) {
            return;
        }

        const nextPage = Number(button.dataset.pageNumber);
        if (!Number.isNaN(nextPage) && nextPage !== inventoryState.page) {
            inventoryState.page = nextPage;
            loadAssets();
        }
    });
}

function syncInitialControls() {
    const perPageSelect = document.getElementById('per-page-select');
    if (perPageSelect?.value) {
        inventoryState.perPage = Number(perPageSelect.value) || inventoryState.perPage;
    }
}

function updateSortIcons() {
    document.querySelectorAll('#assets-table thead .sortable').forEach(th => {
        const col = th.dataset.sort;
        if (col === inventoryState.sort.column) {
            th.setAttribute('data-sort-active', inventoryState.sort.direction);
            th.setAttribute('aria-sort', inventoryState.sort.direction === 'asc' ? 'ascending' : 'descending');
        } else {
            th.removeAttribute('data-sort-active');
            th.removeAttribute('aria-sort');
        }
    });
}

function sortItems(items, column, direction) {
    const getValue = (item) => {
        const map = {
            name: item.name || '',
            type: item.asset_type || item.type || '',
            criticality: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf((item.criticality || '').toUpperCase()),
            vuln_count: item.vulnerability_count ?? item.vulnerabilities_count ?? 0,
            risk_score: item.risk_score ?? -1,
            status: item.status || ''
        };
        return map[column] ?? '';
    };

    return [...items].sort((a, b) => {
        const va = getValue(a);
        const vb = getValue(b);
        let cmp = 0;
        if (typeof va === 'number' && typeof vb === 'number') {
            cmp = va - vb;
        } else {
            cmp = String(va).localeCompare(String(vb), 'pt-BR');
        }
        return direction === 'asc' ? cmp : -cmp;
    });
}

async function loadAssets() {
    const tableBody = document.getElementById('assets-table-body');
    const loading = document.getElementById('table-loading');
    const emptyState = document.getElementById('empty-state');

    if (loading) {
        loading.style.display = 'flex';
    }

    OpenMonitor.page.setBusy(tableBody, true);

    try {
        const data = await OpenMonitor.api.get('/assets/api/list', {
            page: inventoryState.page,
            per_page: inventoryState.perPage,
            search: inventoryState.filters.search,
            type: inventoryState.filters.type,
            criticality: inventoryState.filters.criticality,
            status: inventoryState.filters.status
        });

        inventoryState.totalItems = data.total || 0;
        inventoryState.totalPages = data.pages || 1;

        let items = Array.isArray(data.items) ? data.items : [];
        if (inventoryState.sort.column) {
            items = sortItems(items, inventoryState.sort.column, inventoryState.sort.direction);
        }

        if (items.length > 0) {
            tableBody.innerHTML = items.map(renderAssetRow).join('');
            if (emptyState) {
                emptyState.style.display = 'none';
            }
        } else {
            tableBody.innerHTML = '';
            if (emptyState) {
                emptyState.style.display = 'flex';
            }
        }

        renderFilterSummary();
        renderPagination();
    } catch (error) {
        console.error('Failed to load assets:', error);
        OpenMonitor.showToast('Falha ao carregar os ativos', 'error');
    } finally {
        OpenMonitor.page.setBusy(tableBody, false);
        if (loading) {
            loading.style.display = 'none';
        }
    }
}

async function loadStats() {
    try {
        const data = await OpenMonitor.api.get('/assets/api/stats');
        setStat('stat-total-assets', data.total);
        setStat('stat-critical-vulns', data.critical_vulnerabilities || 0);
        setStat('stat-pending', data.open_vulnerabilities || 0);
        setStat('stat-mitigated', data.mitigated_vulnerabilities || 0);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function setStat(id, value) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }

    element.textContent = value || 0;
    element.classList.remove('skeleton-text', 'w-50');
}

function clearFilters() {
    inventoryState.filters = {
        search: '',
        type: '',
        criticality: '',
        status: ''
    };
    inventoryState.page = 1;

    document.getElementById('asset-search').value = '';
    document.getElementById('asset-type').value = '';
    document.getElementById('asset-criticality').value = '';
    document.getElementById('asset-status').value = '';

    updateActiveFilters();
    loadAssets();
}

function renderFilterSummary() {
    const summary = document.getElementById('active-filters');
    if (!summary) {
        return;
    }

    const active = [];
    if (inventoryState.filters.search) {
        active.push(`Busca: "${inventoryState.filters.search}"`);
    }
    if (inventoryState.filters.type) {
        active.push(`Tipo: ${inventoryState.filters.type}`);
    }
    if (inventoryState.filters.criticality) {
        active.push(`Criticidade: ${inventoryState.filters.criticality}`);
    }
    if (inventoryState.filters.status) {
        active.push(`Status: ${inventoryState.filters.status}`);
    }

    summary.textContent = active.length > 0 ? `Filtros aplicados: ${active.join(' • ')}` : 'Nenhum filtro aplicado';
}

function updateActiveFilters() {
    renderFilterSummary();
}

function renderPagination() {
    const paginationContainer = document.getElementById('pagination');
    const infoContainer = document.getElementById('pagination-info');

    if (!paginationContainer) {
        return;
    }

    if (infoContainer) {
        if (inventoryState.totalItems > 0) {
            const start = (inventoryState.page - 1) * inventoryState.perPage + 1;
            const end = Math.min(inventoryState.page * inventoryState.perPage, inventoryState.totalItems);
            infoContainer.textContent = `Exibindo ${start}-${end} de ${inventoryState.totalItems} ativos`;
        } else {
            infoContainer.textContent = 'Nenhum ativo encontrado';
        }
    }

    if (inventoryState.totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    const pages = buildPageRange(inventoryState.page, inventoryState.totalPages);
    paginationContainer.innerHTML = `
        <ul class="pagination mb-0 gap-1">
            ${renderPageButton(inventoryState.page - 1, '<i class="fas fa-chevron-left"></i>', inventoryState.page === 1)}
            ${pages.map(page => page === '...' ? '<li class="page-item disabled"><span class="page-link">...</span></li>' : renderPageButton(page, page, false, page === inventoryState.page)).join('')}
            ${renderPageButton(inventoryState.page + 1, '<i class="fas fa-chevron-right"></i>', inventoryState.page === inventoryState.totalPages)}
        </ul>
    `;
}

function buildPageRange(currentPage, totalPages) {
    if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_, index) => index + 1);
    }

    if (currentPage <= 4) {
        return [1, 2, 3, 4, 5, '...', totalPages];
    }

    if (currentPage >= totalPages - 3) {
        return [1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
    }

    return [1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages];
}

function renderPageButton(pageNumber, label, disabled = false, active = false) {
    return `
        <li class="page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}">
            <button class="page-link" type="button" data-page-number="${pageNumber}" ${disabled ? 'disabled' : ''}>${label}</button>
        </li>
    `;
}

function renderAssetRow(asset) {
    const criticality = (asset.criticality || 'LOW').toUpperCase();
    const vulnerabilities = asset.vulnerabilities_count ?? asset.vulnerability_count ?? 0;
    const riskScore = asset.risk_score ?? asset.contextual_risk_score;

    return `
        <tr data-id="${asset.id}">
            <td>
                <div class="d-flex align-items-center gap-2">
                    <i class="fas fa-${getAssetIcon(asset.asset_type || asset.type)} text-muted"></i>
                    <div>
                        <div class="fw-semibold">${OpenMonitor.utils.escapeHtml(asset.name || 'Sem nome')}</div>
                        <small>${OpenMonitor.utils.escapeHtml(asset.hostname || asset.ip_address || '')}</small>
                    </div>
                </div>
            </td>
            <td>${OpenMonitor.utils.escapeHtml(asset.asset_type || asset.type || '-')}</td>
            <td><span class="badge badge-${getCriticalityClass(criticality)}">${criticality}</span></td>
            <td><span class="badge badge-secondary">${vulnerabilities} CVEs</span></td>
            <td><span class="fw-bold text-${getRiskTone(riskScore)}">${typeof riskScore === 'number' ? riskScore.toFixed(1) : 'N/A'}</span></td>
            <td><span class="badge badge-${asset.status === 'ACTIVE' ? 'success' : 'secondary'}">${OpenMonitor.utils.escapeHtml(asset.status || 'UNKNOWN')}</span></td>
            <td>${asset.last_scan_date ? OpenMonitor.utils.formatDateTime(asset.last_scan_date) : 'Nunca'}</td>
            <td class="text-end">
                <div class="d-flex justify-content-end gap-1">
                    <button class="btn btn-icon btn-ghost btn-sm" type="button" data-action="view" data-id="${asset.id}" title="Visualizar">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-icon btn-ghost btn-sm" type="button" data-action="scan" data-id="${asset.id}" title="Correlacionar CVEs">
                        <i class="fas fa-shield-virus"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function getCriticalityClass(criticality) {
    return {
        CRITICAL: 'critical',
        HIGH: 'high',
        MEDIUM: 'medium',
        LOW: 'low'
    }[criticality] || 'low';
}

function getAssetIcon(type) {
    return {
        SERVER: 'server',
        WORKSTATION: 'desktop',
        NETWORK_DEVICE: 'network-wired',
        FIREWALL: 'shield-halved',
        APPLICATION: 'cube',
        DATABASE: 'database',
        CLOUD_SERVICE: 'cloud',
        CONTAINER: 'box',
        IOT_DEVICE: 'microchip',
        MOBILE_DEVICE: 'mobile-screen-button'
    }[type] || 'server';
}

function getRiskTone(score) {
    if (typeof score !== 'number') {
        return 'muted';
    }
    if (score >= 9) {
        return 'danger';
    }
    if (score >= 7) {
        return 'warning';
    }
    if (score >= 4) {
        return 'info';
    }
    return 'success';
}

async function scanAssets(assetIds = []) {
    const scanAll = assetIds.length === 0;
    const confirmed = await OpenMonitor.confirm(
        scanAll ? 'Iniciar correlação de CVEs para todos os ativos?' : 'Iniciar correlação de CVEs para este ativo?',
        {
            title: 'Executar correlação',
            confirmText: 'Executar',
            cancelText: 'Cancelar'
        }
    );

    if (!confirmed) {
        return;
    }

    try {
        await OpenMonitor.api.post('/assets/api/scan', scanAll ? { scan_all: true } : { asset_ids: assetIds });
        OpenMonitor.showToast(scanAll ? 'Correlação iniciada para todos os ativos' : 'Correlação iniciada com sucesso', 'success');
        loadAssets();
        loadStats();
    } catch (error) {
        console.error('Scan error:', error);
        OpenMonitor.showToast(error.message || 'Falha ao iniciar a correlação', 'error');
    }
}

async function loadCategories() {
    const list = document.getElementById('categories-list');
    if (!list) {
        return;
    }

    list.innerHTML = '<div class="text-center p-3"><div class="spinner-border spinner-border-sm text-primary"></div></div>';

    try {
        const categories = await OpenMonitor.api.get('/assets/api/categories');
        if (!Array.isArray(categories) || categories.length === 0) {
            list.innerHTML = '<div class="text-center p-3 text-muted">Nenhuma categoria cadastrada</div>';
            return;
        }

        list.innerHTML = categories.map(category => `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <div class="fw-bold">${OpenMonitor.utils.escapeHtml(category.name)}</div>
                    <small class="text-muted">${OpenMonitor.utils.escapeHtml(category.description || 'Sem descrição')}</small>
                </div>
                <span class="badge bg-primary rounded-pill">${category.id}</span>
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = '<div class="alert alert-danger p-2">Erro ao carregar categorias</div>';
    }
}

async function createCategory(event) {
    event.preventDefault();
    const nameInput = document.getElementById('new-category-name');
    const name = nameInput?.value.trim();

    if (!name) {
        OpenMonitor.showToast('Informe o nome da categoria', 'warning');
        return;
    }

    try {
        await OpenMonitor.api.post('/assets/api/categories', { name });
        nameInput.value = '';
        OpenMonitor.showToast('Categoria criada com sucesso', 'success');
        loadCategories();
    } catch (error) {
        console.error('Error creating category:', error);
        OpenMonitor.showToast(error.message || 'Falha ao criar categoria', 'error');
    }
}
