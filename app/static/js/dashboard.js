/**
 * Open-Monitor v3.0 - Dashboard JavaScript
 * Chart.js integration and dashboard functionality
 */

'use strict';

OpenMonitor.dashboard = {
    charts: {},
    data: null,
    refreshInterval: null,
    
    /**
     * Initialize dashboard
     */
    async init() {
        // Load Chart.js defaults
        this.configureChartDefaults();
        
        // Load initial data
        await this.loadDashboardData();
        
        // Initialize charts
        this.initTrendsChart();
        this.initSeverityChart();
        this.initVendorsChart();
        this.initRemediationChart();
        
        // Setup refresh
        this.setupAutoRefresh();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load additional data
        this.loadRiskMatrixData();
        this.loadRemediationData();
    },

    /**
     * Configure Chart.js defaults
     */
    configureChartDefaults() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not loaded');
            return;
        }

        Chart.defaults.color = '#94a3b8';
        Chart.defaults.borderColor = 'rgba(148, 163, 184, 0.1)';
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 20;
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = '#f1f5f9';
        Chart.defaults.plugins.tooltip.bodyColor = '#cbd5e1';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(59, 130, 246, 0.3)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.padding = 12;
    },

    /**
     * Load dashboard data from API
     */
    async loadDashboardData() {
        try {
            const timeRange = this.getTimeRange();
            const data = await OpenMonitor.api.get('/analytics/api/dashboard', { 
                days: timeRange 
            });
            
            this.data = data;
            this.updateStatCards(data);
            this.updateCriticalList(data.vulnerabilities?.critical_recent || []);
            this.updateSeverityChart(); // Update severity chart with new data
            
            return data;
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            OpenMonitor.ui.toast('Failed to load dashboard data', 'error');
        }
    },

    /**
     * Get selected time range
     */
    getTimeRange() {
        const selector = document.querySelector('[data-time-range]');
        return selector?.value || '30';
    },

    /**
     * Update stat cards
     */
    updateStatCards(data) {
        const updateCard = (selector, value, trend = null, inverse = false) => {
            const el = document.querySelector(selector);
            if (el) {
                const valueEl = el.querySelector('.stat-value');
                if (valueEl) {
                    valueEl.textContent = OpenMonitor.utils.formatNumber(value);
                    valueEl.classList.remove('skeleton-text', 'w-50');
                }
                
                const changeEl = el.querySelector('.stat-change');
                if (changeEl && trend) {
                    const direction = trend.direction; // 'up', 'down', 'neutral'
                    const percent = Math.abs(trend.percent);
                    const changeValue = Math.abs(trend.change);
                    
                    let colorClass = 'text-muted';
                    let icon = 'fa-minus';
                    
                    if (direction === 'up') {
                        colorClass = inverse ? 'text-danger' : 'text-success';
                        icon = 'fa-arrow-up';
                    } else if (direction === 'down') {
                        colorClass = inverse ? 'text-success' : 'text-danger';
                        icon = 'fa-arrow-down';
                    }
                    
                    // For assets (not inverse), we might want neutral or specific logic
                    // But using inverse=false means Up=Green (Good), Down=Red (Bad)
                    // Using inverse=true means Up=Red (Bad), Down=Green (Good)
                    
                    changeEl.innerHTML = `
                        <span class="${colorClass} small fw-medium">
                            <i class="fas ${icon} me-1"></i>${percent}%
                        </span>
                        <span class="text-muted small ms-1">(${trend.change > 0 ? '+' : ''}${changeValue} this month)</span>
                    `;
                    changeEl.classList.remove('skeleton-text', 'w-25');
                } else if (changeEl) {
                     changeEl.innerHTML = '<span class="text-muted small">No change data</span>';
                     changeEl.classList.remove('skeleton-text', 'w-25');
                }
            }
        };

        updateCard('[data-stat="total"]', data.vulnerabilities?.total || 0, data.vulnerabilities?.trend, true);
        updateCard('[data-stat="critical"]', data.vulnerabilities?.by_severity?.CRITICAL || 0, data.vulnerabilities?.critical_trend, true);
        updateCard('[data-stat="cisa-kev"]', data.vulnerabilities?.cisa_kev || 0, data.vulnerabilities?.cisa_trend, true);
        updateCard('[data-stat="assets"]', data.assets?.total || 0, data.assets?.trend, false);
    },

    /**
     * Update critical CVEs list
     */
    updateCriticalList(cves) {
        const tbody = document.querySelector('#critical-vulns-table tbody');
        if (!tbody) return;

        if (cves.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center p-4 text-muted">No critical vulnerabilities found</td></tr>`;
            return;
        }

        tbody.innerHTML = cves.map(cve => `
            <tr>
                <td>
                    <a href="/vulnerabilities/${cve.cve_id}" class="text-primary fw-medium">${cve.cve_id}</a>
                </td>
                <td>${OpenMonitor.utils.formatRelativeTime(cve.published)}</td>
                <td>
                    <span class="badge badge-critical">${cve.cvss_score?.toFixed(1) || 'N/A'}</span>
                </td>
                <td class="text-muted text-truncate" style="max-width: 200px;" title="${OpenMonitor.utils.escapeHtml(cve.description || '')}">
                    ${OpenMonitor.utils.escapeHtml(cve.description || '').substring(0, 80)}...
                </td>
            </tr>
        `).join('');
    },

    /**
     * Initialize trends chart (line chart)
     */
    initTrendsChart() {
        const ctx = document.getElementById('trendsChart')?.getContext('2d');
        if (!ctx) return;

        this.charts.trends = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Critical',
                        data: [],
                        borderColor: '#dc2626', // var(--critical)
                        backgroundColor: 'rgba(220, 38, 38, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'High',
                        data: [],
                        borderColor: '#ea580c', // var(--high)
                        backgroundColor: 'rgba(234, 88, 12, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Medium',
                        data: [],
                        borderColor: '#ca8a04', // var(--medium)
                        backgroundColor: 'rgba(202, 138, 4, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Low',
                        data: [],
                        borderColor: '#16a34a', // var(--low)
                        backgroundColor: 'rgba(22, 163, 74, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        }
                    }
                }
            }
        });

        this.loadTrendsData();
    },

    /**
     * Load trends data
     */
    async loadTrendsData() {
        try {
            const timeRange = this.getTimeRange();
            const data = await OpenMonitor.api.get('/analytics/api/trends', { 
                days: timeRange,
                group_by: timeRange > 30 ? 'week' : 'day'
            });

            if (this.charts.trends && data.timeline) {
                // Ensure labels match the timeline
                const labels = data.timeline.map(t => new Date(t.period).toLocaleDateString());
                
                // Helper to get counts for a severity aligned with labels
                const getCounts = (severity) => {
                    const sevData = data.by_severity[severity] || [];
                    const countMap = new Map(sevData.map(item => [new Date(item.period).toLocaleDateString(), item.count]));
                    return labels.map(label => countMap.get(label) || 0);
                };

                this.charts.trends.data.labels = labels;
                this.charts.trends.data.datasets[0].data = getCounts('CRITICAL');
                this.charts.trends.data.datasets[1].data = getCounts('HIGH');
                this.charts.trends.data.datasets[2].data = getCounts('MEDIUM');
                this.charts.trends.data.datasets[3].data = getCounts('LOW');
                this.charts.trends.update();
            }
        } catch (error) {
            console.error('Failed to load trends:', error);
        }
    },

    /**
     * Initialize severity distribution chart (doughnut)
     */
    initSeverityChart() {
        const ctx = document.getElementById('severityChart')?.getContext('2d');
        if (!ctx) return;

        this.charts.severity = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#dc2626',
                        '#ea580c',
                        '#ca8a04',
                        '#16a34a'
                    ],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: {
                        display: false // We use custom legend
                    }
                }
            }
        });
        
        // Initial update if data is already loaded
        this.updateSeverityChart();
    },

    /**
     * Update severity chart and legend
     */
    updateSeverityChart() {
        if (this.charts.severity && this.data?.vulnerabilities?.by_severity) {
            const breakdown = this.data.vulnerabilities.by_severity;
            const data = [
                breakdown.CRITICAL || 0,
                breakdown.HIGH || 0,
                breakdown.MEDIUM || 0,
                breakdown.LOW || 0
            ];
            
            this.charts.severity.data.datasets[0].data = data;
            this.charts.severity.update();
            
            this.updateSeverityLegend(breakdown);
        }
    },
    
    /**
     * Update custom severity legend
     */
    updateSeverityLegend(breakdown) {
        const legend = document.getElementById('severityLegend');
        if (!legend) return;
        
        const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
        
        const items = [
            { label: 'Critical', value: breakdown.CRITICAL || 0, color: 'var(--critical)' },
            { label: 'High', value: breakdown.HIGH || 0, color: 'var(--high)' },
            { label: 'Medium', value: breakdown.MEDIUM || 0, color: 'var(--medium)' },
            { label: 'Low', value: breakdown.LOW || 0, color: 'var(--low)' }
        ];
        
        legend.innerHTML = `
            <div class="d-flex flex-wrap gap-4 justify-content-center">
                ${items.map(item => `
                    <div class="d-flex align-items-center gap-2">
                        <span class="d-block rounded-circle" style="width: 8px; height: 8px; background-color: ${item.color}"></span>
                        <span class="text-muted small">${item.label}</span>
                        <span class="fw-bold small">${item.value} (${Math.round(item.value / total * 100)}%)</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    /**
     * Initialize top vendors chart (horizontal bar)
     */
    initVendorsChart() {
        const ctx = document.getElementById('vendorsChart')?.getContext('2d');
        if (!ctx) return;

        this.charts.vendors = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Vulnerabilities',
                    data: [],
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(148, 163, 184, 0.1)'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });

        this.loadVendorsData();
    },

    /**
     * Load top vendors data
     */
    async loadVendorsData() {
        try {
            const data = await OpenMonitor.api.get('/analytics/api/top-vendors', { limit: 10 });

            if (this.charts.vendors && data.vendors) {
                this.charts.vendors.data.labels = data.vendors.map(v => v.vendor);
                this.charts.vendors.data.datasets[0].data = data.vendors.map(v => v.count);
                this.charts.vendors.update();
            }
        } catch (error) {
            console.error('Failed to load vendors:', error);
        }
    },

    /**
     * Initialize remediation chart (doughnut)
     */
    initRemediationChart() {
        const ctx = document.getElementById('remediationChart')?.getContext('2d');
        if (!ctx) return;

        this.charts.remediation = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Open', 'Mitigated', 'False Positive', 'Risk Accepted'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#dc2626', // Open (Red)
                        '#16a34a', // Mitigated (Green)
                        '#94a3b8', // False Positive (Gray)
                        '#ca8a04'  // Risk Accepted (Yellow)
                    ],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    },

    /**
     * Load remediation status data
     */
    async loadRemediationData() {
        try {
            const data = await OpenMonitor.api.get('/analytics/api/remediation-status');
            
            if (this.charts.remediation && data.by_status) {
                const breakdown = data.by_status;
                const chartData = [
                    breakdown.OPEN || 0,
                    breakdown.MITIGATED || 0,
                    breakdown.FALSE_POSITIVE || 0,
                    breakdown.RISK_ACCEPTED || 0
                ];
                
                this.charts.remediation.data.datasets[0].data = chartData;
                this.charts.remediation.update();
                
                this.updateRemediationLegend(breakdown);
            }
            
            // Update stats
            const overdueEl = document.getElementById('remediation-overdue');
            if (overdueEl) overdueEl.textContent = data.overdue || 0;
            
            const slaEl = document.getElementById('remediation-sla');
            if (slaEl) slaEl.textContent = data.upcoming_due || 0;
            
        } catch (error) {
            console.error('Failed to load remediation:', error);
        }
    },

    /**
     * Update remediation legend
     */
    updateRemediationLegend(breakdown) {
        const legend = document.getElementById('remediationLegend');
        if (!legend) return;
        
        const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
        
        const items = [
            { label: 'Open', value: breakdown.OPEN || 0, color: '#dc2626' },
            { label: 'Mitigated', value: breakdown.MITIGATED || 0, color: '#16a34a' },
            { label: 'False Positive', value: breakdown.FALSE_POSITIVE || 0, color: '#94a3b8' },
            { label: 'Risk Accepted', value: breakdown.RISK_ACCEPTED || 0, color: '#ca8a04' }
        ];
        
        legend.innerHTML = `
            <div class="d-flex flex-wrap gap-3 justify-content-center">
                ${items.map(item => `
                    <div class="d-flex align-items-center gap-2">
                        <span class="d-block rounded-circle" style="width: 8px; height: 8px; background-color: ${item.color}"></span>
                        <span class="text-muted small">${item.label}</span>
                        <span class="fw-bold small">${item.value}</span>
                    </div>
                `).join('')}
            </div>
        `;
    },

    /**
     * Load and render risk matrix
     */
    async loadRiskMatrixData() {
        try {
            const data = await OpenMonitor.api.get('/analytics/api/asset-risk-matrix');
            const tbody = document.querySelector('#risk-matrix-table tbody');
            
            if (!tbody) return;

            if (this.data?.assets?.total === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-muted">Não há assets sendo monitorados</td></tr>`;
                return;
            }
            
            if (!data.matrix || data.matrix.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="text-center p-4 text-muted">No high risk assets found</td></tr>`;
                return;
            }
            
            const topAssets = data.matrix.slice(0, 5);
            tbody.innerHTML = topAssets.map(asset => `
                <tr id="asset-row-${asset.asset_id}">
                    <td>
                        <div class="d-flex align-items-center">
                            <div class="avatar avatar-xs me-2 bg-light text-primary rounded-circle d-flex align-items-center justify-content-center" style="width: 32px; height: 32px;">
                                <i class="fas fa-server" style="font-size: 0.8rem;"></i>
                            </div>
                            <span class="fw-medium">${OpenMonitor.utils.escapeHtml(asset.name)}</span>
                        </div>
                    </td>
                    <td><span class="badge bg-light text-dark border">${asset.type}</span></td>
                    <td>
                        <span class="fw-bold ${asset.risk_score > 800 ? 'text-danger' : (asset.risk_score > 500 ? 'text-warning' : 'text-success')}">
                            ${asset.risk_score}
                        </span>
                    </td>
                    <td>
                        <span class="badge badge-critical me-1" title="Critical">${asset.vulnerabilities?.CRITICAL || 0}</span>
                        <span class="badge badge-high" title="High">${asset.vulnerabilities?.HIGH || 0}</span>
                    </td>
                    <td>
                        <a href="/inventory/${asset.asset_id}" class="btn btn-sm btn-light">
                            <i class="fas fa-arrow-right"></i>
                        </a>
                    </td>
                </tr>
            `).join('');

            // Listar CVEs associadas abaixo do nome do ativo
            for (const asset of topAssets) {
                try {
                    const resp = await OpenMonitor.api.get(`/assets/api/${asset.asset_id}/vulnerabilities`);
                    const cves = (resp?.vulnerabilities || [])
                        .map(v => v?.vulnerability?.cve_id)
                        .filter(Boolean);
                    
                    const nameCell = document.querySelector(`#asset-row-${asset.asset_id} td:first-child`);
                    if (nameCell) {
                        const cveLine = document.createElement('div');
                        cveLine.className = 'small text-muted mt-1';
                        cveLine.textContent = cves.length > 0 
                            ? `CVEs: ${cves.slice(0, 5).join(', ')}${cves.length > 5 ? '…' : ''}`
                            : 'CVEs: nenhuma associada';
                        nameCell.appendChild(cveLine);
                    }
                } catch (err) {
                    console.error(`Erro ao carregar CVEs do asset ${asset.asset_id}:`, err);
                }
            }
            
        } catch (error) {
            console.error('Failed to load risk matrix:', error);
        }
    },

    /**
     * Setup auto refresh
     */
    setupAutoRefresh() {
        // Refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.refresh();
        }, 5 * 60 * 1000);
    },

    /**
     * Refresh all dashboard data
     */
    async refresh() {
        await this.loadDashboardData();
        await this.loadTrendsData();
        await this.loadVendorsData();
        await this.loadRiskMatrixData();
        await this.loadRemediationData();
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Time range selector
        const rangeSelector = document.querySelector('[data-time-range]');
        if (rangeSelector) {
            rangeSelector.addEventListener('change', () => {
                this.loadDashboardData();
                this.loadTrendsData();
            });
        }

        // Refresh button
        document.getElementById('dashboard-refresh-btn')?.addEventListener('click', () => {
            this.loadDashboardData();
        });

        // Export button
        document.getElementById('dashboard-export-btn')?.addEventListener('click', () => {
            this.exportData();
        });
    },

    /**
     * Export dashboard data
     */
    async exportData() {
        try {
            OpenMonitor.ui.showLoading('Exporting data...');
            
            const timeRange = this.getTimeRange();
            
            // Calculate date_from based on days
            const date = new Date();
            date.setDate(date.getDate() - parseInt(timeRange));
            const dateFrom = date.toISOString().split('T')[0];
            
            const response = await OpenMonitor.api.get('/analytics/api/export', {
                date_from: dateFrom,
                format: 'csv'
            }, {
                responseType: 'text'
            });

            // Create download link
            const blob = new Blob([response], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `vulnerabilities-export-${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            OpenMonitor.ui.toast('Export completed', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            OpenMonitor.ui.toast('Export failed', 'error');
        } finally {
            OpenMonitor.ui.hideLoading();
        }
    },

    /**
     * Destroy charts and cleanup
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
};

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.querySelector('[data-page="dashboard"]')) {
        OpenMonitor.dashboard.init();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    OpenMonitor.dashboard.destroy();
});
