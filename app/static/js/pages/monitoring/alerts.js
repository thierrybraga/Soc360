/**
 * Alerts Page Scripts
 * Handles alert listing, filtering, and management.
 */

document.addEventListener('DOMContentLoaded', () => {
    let currentPage = 1;
    let currentAlerts = [];
    let currentRequestId = 0;
    let activeController = null;
    const updatingIds = new Set();
    const filters = {
        status: '',
        severity: ''
    };

    const tableBody = document.getElementById('alerts-table-body');
    const loadingState = document.getElementById('loading-state');
    const emptyState = document.getElementById('empty-state');
    const alertsTable = document.getElementById('alerts-table');
    const paginationContainer = document.getElementById('pagination-container');
    const paginationEl = document.getElementById('pagination');
    const paginationInfo = document.getElementById('pagination-info');
    const modalEl = document.getElementById('alertDetailsModal');
    const modal = modalEl && window.bootstrap ? new window.bootstrap.Modal(modalEl) : null;

    function showToast(message, type = 'info') {
        if (window.OpenMonitor?.showToast) {
            window.OpenMonitor.showToast(message, type);
        }
    }

    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || '';
    }

    function escapeHtml(text) {
        if (window.OpenMonitor?.utils?.escapeHtml) {
            return window.OpenMonitor.utils.escapeHtml(text);
        }

        const div = document.createElement('div');
        div.textContent = text ?? '';
        return div.innerHTML;
    }

    function formatDate(value) {
        if (!value) {
            return '-';
        }

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return '-';
        }

        return date.toLocaleString();
    }

    async function parseJsonResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            throw new Error(`Resposta inesperada: ${response.status}`);
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || data.message || `Erro ${response.status}`);
        }

        return data;
    }

    function setLoadingState(isLoading) {
        if (loadingState) {
            loadingState.style.display = isLoading ? 'block' : 'none';
        }

        if (isLoading) {
            if (alertsTable) {
                alertsTable.style.display = 'none';
            }
            if (emptyState) {
                emptyState.style.display = 'none';
            }
            if (paginationContainer) {
                paginationContainer.style.display = 'none';
            }
        }
    }

    async function loadAlerts() {
        if (!loadingState) {
            return;
        }

        if (activeController) {
            activeController.abort();
        }

        activeController = new AbortController();
        currentRequestId += 1;
        const requestId = currentRequestId;

        setLoadingState(true);

        const params = new URLSearchParams({
            page: String(currentPage)
        });

        Object.entries(filters).forEach(([key, value]) => {
            if (value) {
                params.set(key, value);
            }
        });

        try {
            const response = await fetch(`/monitoring/api/alerts?${params.toString()}`, {
                headers: {
                    'Accept': 'application/json'
                },
                signal: activeController.signal
            });

            const data = await parseJsonResponse(response);

            if (requestId !== currentRequestId) {
                return;
            }

            renderAlerts(Array.isArray(data.items) ? data.items : []);
            renderPagination(data);
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }

            currentAlerts = [];
            if (tableBody) {
                tableBody.innerHTML = '';
            }
            if (alertsTable) {
                alertsTable.style.display = 'none';
            }
            if (paginationContainer) {
                paginationContainer.style.display = 'none';
            }
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            console.error('Error loading alerts:', error);
            showToast(error.message || 'Falha ao carregar alertas', 'error');
        } finally {
            if (requestId === currentRequestId) {
                setLoadingState(false);
            }
        }
    }

    function renderAlerts(items) {
        if (!tableBody) {
            return;
        }

        currentAlerts = items;
        tableBody.innerHTML = '';

        if (!items.length) {
            if (alertsTable) {
                alertsTable.style.display = 'none';
            }
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            if (paginationContainer) {
                paginationContainer.style.display = 'none';
            }
            return;
        }

        if (alertsTable) {
            alertsTable.style.display = 'table';
        }
        if (emptyState) {
            emptyState.style.display = 'none';
        }

        items.forEach((alert) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${renderSeverityBadge(alert.severity)}</td>
                <td>${renderStatusBadge(alert.status)}</td>
                <td>
                    <div class="fw-bold">${escapeHtml(alert.title || 'Sem título')}</div>
                    <div class="small text-muted text-truncate" style="max-width: 300px;">${escapeHtml(alert.description || '')}</div>
                </td>
                <td><span class="badge bg-light text-dark border">${escapeHtml(alert.rule_name || (alert.rule_id ? `Rule #${alert.rule_id}` : 'System'))}</span></td>
                <td class="small text-muted">${formatDate(alert.created_at)}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary view-alert-btn" data-id="${alert.id}" type="button">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${renderActionButtons(alert)}
                </td>
            `;
            tableBody.appendChild(tr);
        });
    }

    function renderSeverityBadge(severity) {
        const classes = {
            CRITICAL: 'badge-critical',
            HIGH: 'badge-high',
            MEDIUM: 'badge-medium',
            LOW: 'badge-low'
        };

        const label = severity || 'UNKNOWN';
        const badgeClass = classes[label] || 'bg-secondary';
        return `<span class="badge ${badgeClass}">${escapeHtml(label)}</span>`;
    }

    function renderStatusBadge(status) {
        const colors = {
            NEW: 'danger',
            ACKNOWLEDGED: 'warning',
            RESOLVED: 'success',
            DISMISSED: 'secondary'
        };

        const label = status || 'UNKNOWN';
        const color = colors[label] || 'secondary';
        return `<span class="badge bg-${color}">${escapeHtml(label)}</span>`;
    }

    function renderActionButtons(alert) {
        if (alert.status === 'RESOLVED' || alert.status === 'DISMISSED') {
            return '';
        }

        const disabled = updatingIds.has(String(alert.id)) ? 'disabled' : '';
        const buttons = [];

        if (alert.status === 'NEW') {
            buttons.push(`
                <button class="btn btn-sm btn-outline-success action-btn ms-1" data-id="${alert.id}" data-action="ACKNOWLEDGED" title="Reconhecer" type="button" ${disabled}>
                    <i class="fas fa-check"></i>
                </button>
            `);
        }

        if (alert.status === 'NEW' || alert.status === 'ACKNOWLEDGED') {
            buttons.push(`
                <button class="btn btn-sm btn-outline-success action-btn ms-1" data-id="${alert.id}" data-action="RESOLVED" title="Resolver" type="button" ${disabled}>
                    <i class="fas fa-check-double"></i>
                </button>
            `);
            buttons.push(`
                <button class="btn btn-sm btn-outline-secondary action-btn ms-1" data-id="${alert.id}" data-action="DISMISSED" title="Descartar" type="button" ${disabled}>
                    <i class="fas fa-times"></i>
                </button>
            `);
        }

        return buttons.join('');
    }

    function renderPagination(data) {
        if (!paginationEl || !paginationInfo || !paginationContainer) {
            return;
        }

        const total = Number(data.total || 0);
        const page = Number(data.page || 1);
        const pages = Number(data.pages || 0);
        const perPage = Number(data.per_page || 20);

        if (!total || !pages) {
            paginationEl.innerHTML = '';
            paginationInfo.textContent = '';
            paginationContainer.style.display = 'none';
            return;
        }

        const start = ((page - 1) * perPage) + 1;
        const end = Math.min(page * perPage, total);
        paginationInfo.textContent = `Mostrando ${start}–${end} de ${total} alertas`;
        paginationContainer.style.display = 'flex';

        const parts = [];
        parts.push(`
            <li class="page-item ${!data.has_prev ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${data.prev_num || ''}" type="button">&laquo;</button>
            </li>
        `);

        let ellipsisAdded = false;
        for (let i = 1; i <= pages; i += 1) {
            const visible = i === 1 || i === pages || (i >= page - 2 && i <= page + 2);
            if (visible) {
                ellipsisAdded = false;
                parts.push(`
                    <li class="page-item ${i === page ? 'active' : ''}">
                        <button class="page-link page-link-action" data-page="${i}" type="button">${i}</button>
                    </li>
                `);
            } else if (!ellipsisAdded) {
                ellipsisAdded = true;
                parts.push('<li class="page-item disabled"><span class="page-link">...</span></li>');
            }
        }

        parts.push(`
            <li class="page-item ${!data.has_next ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${data.next_num || ''}" type="button">&raquo;</button>
            </li>
        `);

        paginationEl.innerHTML = parts.join('');
    }

    function renderModalActions(alert) {
        const actionsContainer = document.getElementById('modal-actions');
        if (!actionsContainer) {
            return;
        }

        actionsContainer.innerHTML = '';

        if (alert.status === 'RESOLVED' || alert.status === 'DISMISSED') {
            return;
        }

        if (alert.status === 'NEW') {
            actionsContainer.insertAdjacentHTML(
                'beforeend',
                `<button class="btn btn-success" data-id="${alert.id}" data-status="ACKNOWLEDGED" type="button">Reconhecer</button>`
            );
        }

        if (alert.status === 'NEW' || alert.status === 'ACKNOWLEDGED') {
            actionsContainer.insertAdjacentHTML(
                'beforeend',
                `<button class="btn btn-outline-success" data-id="${alert.id}" data-status="RESOLVED" type="button">Resolver</button>`
            );
            actionsContainer.insertAdjacentHTML(
                'beforeend',
                `<button class="btn btn-outline-secondary" data-id="${alert.id}" data-status="DISMISSED" type="button">Descartar</button>`
            );
        }
    }

    function viewAlert(id) {
        const alert = currentAlerts.find((item) => String(item.id) === String(id));
        if (!alert) {
            showToast('Alerta não encontrado', 'error');
            return;
        }

        const severityEl = document.getElementById('modal-severity');
        const statusEl = document.getElementById('modal-status');
        const titleEl = document.getElementById('modal-title');
        const descriptionEl = document.getElementById('modal-description');
        const detailsEl = document.getElementById('modal-details');

        if (!severityEl || !statusEl || !titleEl || !descriptionEl || !detailsEl || !modal) {
            return;
        }

        severityEl.innerHTML = renderSeverityBadge(alert.severity);
        statusEl.innerHTML = renderStatusBadge(alert.status);
        titleEl.textContent = alert.title || 'Sem título';
        descriptionEl.textContent = alert.description || 'Sem descrição';
        detailsEl.textContent = JSON.stringify(alert.details || {}, null, 2);

        renderModalActions(alert);
        modal.show();
    }

    async function updateAlertStatus(id, status) {
        const requestKey = String(id);
        if (updatingIds.has(requestKey)) {
            return;
        }

        updatingIds.add(requestKey);

        try {
            const response = await fetch(`/monitoring/api/alerts/${id}/status`, {
                method: 'PUT',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ status })
            });

            await parseJsonResponse(response);
            if (modal) {
                modal.hide();
            }
            showToast('Alerta atualizado com sucesso', 'success');
            await loadAlerts();
        } catch (error) {
            console.error('Error updating alert:', error);
            showToast(error.message || 'Falha ao atualizar alerta', 'error');
        } finally {
            updatingIds.delete(requestKey);
        }
    }

    const modalActions = document.getElementById('modal-actions');
    if (modalActions) {
        modalActions.addEventListener('click', (event) => {
            const button = event.target.closest('button[data-id][data-status]');
            if (!button) {
                return;
            }

            updateAlertStatus(button.dataset.id, button.dataset.status);
        });
    }

    if (tableBody) {
        tableBody.addEventListener('click', (event) => {
            const viewButton = event.target.closest('.view-alert-btn');
            if (viewButton) {
                viewAlert(viewButton.dataset.id);
                return;
            }

            const actionButton = event.target.closest('.action-btn');
            if (actionButton) {
                updateAlertStatus(actionButton.dataset.id, actionButton.dataset.action);
            }
        });
    }

    if (paginationEl) {
        paginationEl.addEventListener('click', (event) => {
            const pageLink = event.target.closest('.page-link-action');
            if (!pageLink || pageLink.parentElement.classList.contains('disabled')) {
                return;
            }

            const page = Number(pageLink.dataset.page);
            if (!page) {
                return;
            }

            currentPage = page;
            loadAlerts();
        });
    }

    document.getElementById('filter-status')?.addEventListener('change', (event) => {
        filters.status = event.target.value;
        currentPage = 1;
        loadAlerts();
    });

    document.getElementById('filter-severity')?.addEventListener('change', (event) => {
        filters.severity = event.target.value;
        currentPage = 1;
        loadAlerts();
    });

    document.getElementById('refresh-btn')?.addEventListener('click', () => {
        loadAlerts();
    });

    loadAlerts();
});
