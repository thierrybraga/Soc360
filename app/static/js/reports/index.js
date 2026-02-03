/**
 * Open-Monitor Reports Module
 * Handles report generation, listing, and management.
 */

class ReportsModule {
    constructor() {
        this.generateModalEl = document.getElementById('generate-modal');
        this.generateModalInstance = null;
        
        this.init();
    }

    init() {
        // Initialize Bootstrap Modals
        if (this.generateModalEl && window.bootstrap) {
            this.generateModalInstance = new bootstrap.Modal(this.generateModalEl);
        }

        // Load initial data
        this.loadReports();
        this.loadStats();
        
        this.bindEvents();
    }

    bindEvents() {
        // Generate button
        document.getElementById('generate-btn')?.addEventListener('click', () => {
            this.openGenerateModal();
        });
        
        // Empty state generate button
        document.getElementById('empty-state-generate-btn')?.addEventListener('click', () => {
            this.openGenerateModal();
        });
        
        // Modal Generate button
        document.getElementById('modal-generate')?.addEventListener('click', () => {
            this.generateReport();
        });
        
        // Search
        let searchTimeout;
        document.getElementById('report-search')?.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => this.loadReports(1, e.target.value), 300);
        });

        // Pagination Delegation
        document.getElementById('pagination')?.addEventListener('click', (e) => {
            const link = e.target.closest('.page-link');
            if (link && !link.parentElement.classList.contains('disabled')) {
                e.preventDefault();
                const page = link.dataset.page;
                if (page) {
                    this.loadReports(parseInt(page));
                }
            }
        });

        // Report Type Change (for dynamic options)
        document.getElementById('report-type')?.addEventListener('change', (e) => {
            const optionsDiv = document.getElementById('type-options');
            if (optionsDiv) {
                // Show options for all types for now, or customize based on type
                optionsDiv.style.display = e.target.value ? 'block' : 'none';
            }
        });
    }

    openGenerateModal() {
        const form = document.getElementById('generate-form');
        form.reset();
        document.getElementById('type-options').style.display = 'none';
        this.generateModalInstance?.show();
    }

    async loadStats() {
        try {
            const data = await OpenMonitor.api.get('/reports/api/stats');
            
            const setStat = (id, value) => {
                const el = document.getElementById(id);
                if (el) {
                    el.textContent = value;
                    el.classList.remove('skeleton-text', 'w-50');
                }
            };

            setStat('stat-total', data.total || 0);
            
            // Map status/types to UI stats
            // Completed
            const completed = data.by_status?.COMPLETED || 0;
            setStat('stat-completed', completed);
            
            // Types
            setStat('stat-executive', data.by_type?.EXECUTIVE || 0);
            setStat('stat-technical', data.by_type?.TECHNICAL || 0);

        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async loadReports(page = 1, search = '') {
        const container = document.getElementById('reports-list');
        const loading = document.getElementById('table-loading');
        const emptyState = document.getElementById('empty-state');
        const pagination = document.getElementById('pagination-container');
        
        if (loading) loading.style.display = 'flex';
        if (container) container.innerHTML = '';
        if (emptyState) emptyState.style.display = 'none';
        if (pagination) pagination.style.display = 'none';
        
        try {
            const params = { page: page };
            if (search) params.search = search;
            
            const data = await OpenMonitor.api.get('/reports/api/list', params);
            
            if (data.items && data.items.length > 0) {
                container.innerHTML = `<div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Report</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.items.map(report => this.renderReportRow(report)).join('')}
                        </tbody>
                    </table>
                </div>`;
                
                this.renderPagination(data.page, data.pages);
            } else {
                if (emptyState) emptyState.style.display = 'block';
            }
        } catch (error) {
            console.error('Failed to load reports:', error);
            window.OpenMonitor?.showToast('Failed to load reports', 'error');
        } finally {
            if (loading) loading.style.display = 'none';
        }
    }

    renderReportRow(report) {
        const statusColors = {
            'COMPLETED': 'success',
            'PENDING': 'warning',
            'FAILED': 'danger',
            'GENERATING': 'info'
        };
        
        const typeLabels = {
            'EXECUTIVE': 'Executive Summary',
            'TECHNICAL': 'Technical Report',
            'RISK_ASSESSMENT': 'Risk Assessment',
            'COMPLIANCE': 'Compliance',
            'TREND': 'Trend Analysis',
            'INCIDENT': 'Incident Report',
            'EXECUTIVE_SUMMARY': 'Executive Summary',
            'TECHNICAL_REPORT': 'Technical Report',
            'COMPLIANCE_REPORT': 'Compliance',
            'TREND_ANALYSIS': 'Trend Analysis'
        };

        const statusBadge = `<span class="badge bg-${statusColors[report.status] || 'secondary'}">
            ${report.status}
        </span>`;

        // Actions
        let actions = '';
        if (report.status === 'COMPLETED') {
            actions = `
                <a href="/reports/api/${report.id}/download" class="btn btn-sm btn-outline-primary" target="_blank" title="Download PDF">
                    <i class="fas fa-download"></i>
                </a>
                <a href="/reports/${report.id}" class="btn btn-sm btn-outline-secondary" title="View Details">
                    <i class="fas fa-eye"></i>
                </a>
            `;
        } else if (report.status === 'FAILED') {
            actions = `
                <button class="btn btn-sm btn-outline-secondary" disabled title="Report Failed">
                    <i class="fas fa-exclamation-circle"></i>
                </button>
            `;
        } else {
             actions = `
                <button class="btn btn-sm btn-outline-secondary" disabled title="Generating...">
                    <i class="fas fa-spinner fa-spin"></i>
                </button>
            `;
        }

        return `
            <tr>
                <td>
                    <div class="fw-bold">${OpenMonitor.utils.escapeHtml(report.title)}</div>
                    <small class="text-muted">${OpenMonitor.utils.escapeHtml(report.description || '')}</small>
                </td>
                <td>
                    <span class="badge bg-light text-dark border">
                        ${typeLabels[report.report_type] || report.report_type}
                    </span>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <small class="text-muted">
                        <i class="far fa-clock me-1"></i>${OpenMonitor.utils.formatDate(report.created_at)}
                    </small>
                </td>
                <td>
                    <div class="btn-group">
                        ${actions}
                    </div>
                </td>
            </tr>
        `;
    }

    renderPagination(currentPage, totalPages) {
        const pagination = document.getElementById('pagination');
        const container = document.getElementById('pagination-container');
        
        if (!pagination || totalPages <= 1) {
            if (container) container.style.display = 'none';
            return;
        }

        container.style.display = 'block';
        let html = '';
        
        // Previous
        html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a>
        </li>`;
        
        // Pages (simplified range)
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
                html += `<li class="page-item ${i === currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>`;
            } else if (i === currentPage - 2 || i === currentPage + 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        // Next
        html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${currentPage + 1}">Next</a>
        </li>`;
        
        pagination.innerHTML = html;
    }

    async generateReport() {
        const title = document.getElementById('report-title').value;
        const type = document.getElementById('report-type').value;
        const days = document.getElementById('report-days').value;
        
        if (!title || !type) {
            window.OpenMonitor?.showToast('Please fill in all required fields', 'warning');
            return;
        }

        const btn = document.getElementById('modal-generate');
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

        try {
            const payload = {
                title: title,
                report_type: type,
                description: document.getElementById('report-description').value,
                parameters: {
                    time_range_days: parseInt(days) || 30,
                    include_charts: document.getElementById('opt-charts').checked,
                    include_details: document.getElementById('opt-details').checked
                }
            };

            await OpenMonitor.api.post('/reports/api/generate', payload);

            this.generateModalInstance?.hide();
            window.OpenMonitor?.showToast('Report generation started', 'success');
            this.loadReports();
            this.loadStats();
        } catch (error) {
            console.error('Generation failed:', error);
            window.OpenMonitor?.showToast(error.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

const reportsModule = new ReportsModule();
