/**
 * Open-Monitor Monitoring Module
 * Handles monitoring rules list, stats, and recent alerts.
 */

class MonitoringModule {
    constructor() {
        this.init();
    }

    init() {
        this.loadRules();
        this.loadStats();
        this.loadRecentAlerts();
        this.bindEvents();
    }

    bindEvents() {
        // Search
        let searchTimeout;
        document.getElementById('rule-search')?.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => this.loadRules(e.target.value), 300);
        });

        // Event Delegation for Rules List
        const rulesList = document.getElementById('rules-list');
        if (rulesList) {
            rulesList.addEventListener('click', (e) => {
                const editBtn = e.target.closest('.btn-edit-rule');
                if (editBtn) {
                    const id = editBtn.dataset.id;
                    if (id) window.location.href = `/monitoring/rules/${id}/edit`;
                    return;
                }

                const deleteBtn = e.target.closest('.btn-delete-rule');
                if (deleteBtn) {
                    const id = deleteBtn.dataset.id;
                    if (id) this.deleteRule(id);
                    return;
                }
            });

            rulesList.addEventListener('change', (e) => {
                if (e.target.classList.contains('rule-toggle')) {
                    const id = e.target.dataset.id;
                    const enabled = e.target.checked;
                    if (id) this.toggleRule(id, enabled);
                }
            });
        }

        // Templates button
        document.getElementById('templates-btn')?.addEventListener('click', () => {
            window.location.href = '/monitoring/rules/create';
        });
    }

    async loadRules(search = '') {
        const container = document.getElementById('rules-list');
        const loading = document.getElementById('table-loading');
        const emptyState = document.getElementById('empty-state');

        if (loading) loading.style.display = 'flex';
        if (container) container.innerHTML = '';
        if (emptyState) emptyState.style.display = 'none';

        try {
            const params = {};
            if (search) params.search = search;

            const data = await OpenMonitor.api.get('/monitoring/api/rules', params);

            if (data.items && data.items.length > 0) {
                container.innerHTML = `<div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Status</th>
                                <th>Name</th>
                                <th>Type</th>
                                <th>Channel</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.items.map(rule => this.renderRuleRow(rule)).join('')}
                        </tbody>
                    </table>
                </div>`;
            } else {
                if (emptyState) emptyState.style.display = 'block';
            }
        } catch (error) {
            console.error('Failed to load rules:', error);
            window.OpenMonitor?.showToast('Failed to load rules', 'error');
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    renderRuleRow(rule) {
        const typeLabels = {
            'NEW_CVE': 'New CVE',
            'SEVERITY_THRESHOLD': 'Severity',
            'VENDOR_SPECIFIC': 'Vendor',
            'CISA_KEV': 'CISA KEV'
        };

        const typeBadges = {
            'NEW_CVE': 'bg-info',
            'SEVERITY_THRESHOLD': 'bg-danger',
            'VENDOR_SPECIFIC': 'bg-primary',
            'CISA_KEV': 'bg-warning text-dark'
        };

        return `
            <tr>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input rule-toggle" type="checkbox"
                               data-id="${rule.id}"
                               ${rule.enabled ? 'checked' : ''}>
                    </div>
                </td>
                <td>
                    <div class="fw-bold">${OpenMonitor.utils.escapeHtml(rule.name)}</div>
                    <small class="text-muted">${OpenMonitor.utils.escapeHtml(rule.description || '')}</small>
                </td>
                <td>
                    <span class="badge ${typeBadges[rule.rule_type] || 'bg-secondary'}">
                        ${typeLabels[rule.rule_type] || rule.rule_type}
                    </span>
                </td>
                <td>
                    <i class="fas fa-bell text-muted me-1"></i>
                    ${rule.notification_channels?.join(', ') || 'None'}
                </td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-secondary btn-edit-rule" data-id="${rule.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-delete-rule" data-id="${rule.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    async loadStats() {
        try {
            const data = await OpenMonitor.api.get('/monitoring/api/stats');

            const setStat = (id, value) => {
                const el = document.getElementById(id);
                if (el) {
                    el.textContent = value;
                    el.classList.remove('skeleton-text', 'w-50');
                }
            };

            setStat('stat-total-rules', data.total || 0);
            setStat('stat-active-rules', data.active || 0);
            setStat('stat-alerts-today', data.recent_triggers?.length || 0);
            setStat('stat-critical-alerts', data.by_type?.SEVERITY_THRESHOLD || 0);
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async loadRecentAlerts() {
        try {
            const data = await OpenMonitor.api.get('/monitoring/api/stats');

            const container = document.getElementById('alerts-list');
            if (!container) return;

            if (data.recent_triggers && data.recent_triggers.length > 0) {
                container.innerHTML = `<div class="list-group list-group-flush">
                    ${data.recent_triggers.map(trigger => this.renderAlertItem(trigger)).join('')}
                </div>`;
            } else {
                container.innerHTML = '<div class="text-center p-3 text-muted">No recent alerts</div>';
            }
        } catch (error) {
            console.error('Failed to load alerts:', error);
        }
    }

    renderAlertItem(trigger) {
        return `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <div class="fw-bold">${OpenMonitor.utils.escapeHtml(trigger.rule_name)}</div>
                    <small class="text-muted">
                        <i class="far fa-clock me-1"></i>${window.OpenMonitor?.utils?.formatRelativeTime(trigger.triggered_at) || trigger.triggered_at}
                    </small>
                </div>
                <span class="badge bg-primary rounded-pill">${trigger.trigger_count}</span>
            </div>
        `;
    }

    async toggleRule(id, enabled) {
        try {
            await OpenMonitor.api.post(`/monitoring/api/rules/${id}/toggle`);
            window.OpenMonitor?.showToast(`Rule ${enabled ? 'enabled' : 'disabled'}`, 'success');
            this.loadStats();
        } catch (error) {
            console.error('Toggle failed:', error);
            window.OpenMonitor?.showToast(error.message, 'error');
            this.loadRules();
        }
    }

    async deleteRule(id) {
        if (!confirm('Are you sure you want to delete this rule?')) return;

        try {
            await OpenMonitor.api.delete(`/monitoring/api/rules/${id}`);
            window.OpenMonitor?.showToast('Rule deleted successfully', 'success');
            this.loadRules();
            this.loadStats();
        } catch (error) {
            console.error('Delete failed:', error);
            window.OpenMonitor?.showToast(error.message, 'error');
        }
    }
}

// Initialize
const monitoringModule = new MonitoringModule();
