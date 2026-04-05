/**
 * Open-Monitor v3.0 - NVD Module
 * Vulnerability list management, filtering, and detail views
 */

class NVDModule {
    constructor() {
        this.currentPage = 1;
        this.perPage = 50;
        this.totalPages = 1;
        this.totalItems = 0;
        this.filters = {
            search: '',
            severity: '',
            vendor: '',
            product: '',
            dateFrom: '',
            dateTo: '',
            cisaKev: false
        };
        this.sortField = 'published';
        this.sortOrder = 'desc';
        this.isLoading = false;
        this.syncCheckInterval = null;
        
        // Modal instances
        this.detailModalInstance = null;

        this.init();
    }
    
    init() {
        this.cacheElements();
        this.initModals();
        this.bindEvents();
        this.loadVendors();
        this.loadVulnerabilities();
        this.checkSyncStatus();
        this.startSyncStatusPolling();
    }
    
    cacheElements() {
        // Filter elements
        this.searchInput = document.getElementById('nvd-search');
        this.severitySelect = document.getElementById('nvd-severity');
        this.vendorSelect = document.getElementById('nvd-vendor');
        this.productSelect = document.getElementById('nvd-product');
        this.dateFromInput = document.getElementById('nvd-date-from');
        this.dateToInput = document.getElementById('nvd-date-to');
        this.cisaKevCheckbox = document.getElementById('nvd-cisa-kev');
        this.clearFiltersBtn = document.getElementById('nvd-clear-filters');
        
        // Table elements
        this.tableBody = document.getElementById('nvd-table-body');
        this.loadingOverlay = document.getElementById('nvd-loading');
        this.emptyState = document.getElementById('nvd-empty-state');
        
        // Pagination elements
        this.paginationContainer = document.getElementById('nvd-pagination');
        this.perPageSelect = document.getElementById('nvd-per-page');
        this.pageInfo = document.getElementById('nvd-page-info');
        
        // Stats elements
        this.statTotal = document.getElementById('stat-total');
        this.statCritical = document.getElementById('stat-critical');
        this.statHigh = document.getElementById('stat-high');
        this.statMedium = document.getElementById('stat-medium');
        this.statLow = document.getElementById('stat-low');
        
        // Sync elements
        this.syncStatus = document.getElementById('nvd-sync-status');

        // Modal elements
        this.detailModalEl = document.getElementById('nvd-detail-modal');
        this.modalContent = document.getElementById('nvd-modal-content');
        
        // Export button
        this.exportBtn = document.getElementById('nvd-export-btn');
    }

    initModals() {
        if (this.detailModalEl && window.bootstrap) {
            this.detailModalInstance = new bootstrap.Modal(this.detailModalEl);
        }
    }
    
    bindEvents() {
        // Search with debounce
        if (this.searchInput) {
            this.searchInput.addEventListener('input', this.debounce(() => {
                this.filters.search = this.searchInput.value;
                this.currentPage = 1;
                this.loadVulnerabilities();
            }, 300));
        }
        
        // Filter selects
        if (this.severitySelect) {
            this.severitySelect.addEventListener('change', () => {
                this.filters.severity = this.severitySelect.value;
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        if (this.vendorSelect) {
            this.vendorSelect.addEventListener('change', () => {
                this.filters.vendor = this.vendorSelect.value;
                this.filters.product = '';
                if (this.productSelect) {
                    this.productSelect.value = '';
                    this.loadProducts(this.filters.vendor);
                }
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        if (this.productSelect) {
            this.productSelect.addEventListener('change', () => {
                this.filters.product = this.productSelect.value;
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        // Date filters
        if (this.dateFromInput) {
            this.dateFromInput.addEventListener('change', () => {
                this.filters.dateFrom = this.dateFromInput.value;
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        if (this.dateToInput) {
            this.dateToInput.addEventListener('change', () => {
                this.filters.dateTo = this.dateToInput.value;
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        // CISA KEV checkbox
        if (this.cisaKevCheckbox) {
            this.cisaKevCheckbox.addEventListener('change', () => {
                this.filters.cisaKev = this.cisaKevCheckbox.checked;
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        // Clear filters
        if (this.clearFiltersBtn) {
            this.clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }
        
        // Per page select
        if (this.perPageSelect) {
            this.perPageSelect.addEventListener('change', () => {
                this.perPage = parseInt(this.perPageSelect.value);
                this.currentPage = 1;
                this.loadVulnerabilities();
            });
        }
        
        // Sort headers
        document.querySelectorAll('[data-sort]').forEach(header => {
            header.addEventListener('click', () => {
                const field = header.dataset.sort;
                if (this.sortField === field) {
                    this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortField = field;
                    this.sortOrder = 'desc';
                }
                this.updateSortIndicators();
                this.loadVulnerabilities();
            });
        });
        
        // Export button
        if (this.exportBtn) {
            this.exportBtn.addEventListener('click', () => this.exportData());
        }

        // Table delegation
        if (this.tableBody) {
            this.tableBody.addEventListener('click', (e) => {
                // If clicking a link or button, let default action happen (navigation or other handlers)
                if (e.target.closest('a') || e.target.closest('button')) return;

                // Handle row click - Navigate to details page
                const row = e.target.closest('tr[data-cve-id]');
                if (row) {
                    const cveId = row.dataset.cveId;
                    if (cveId) {
                        window.location.href = `/vulnerabilities/${cveId}`;
                    }
                }
            });
        }

        // Pagination delegation
        if (this.paginationContainer) {
            this.paginationContainer.addEventListener('click', (e) => {
                const pageLink = e.target.closest('.page-link-action');
                if (pageLink) {
                    e.preventDefault();
                    const page = parseInt(pageLink.dataset.page);
                    if (!isNaN(page)) this.goToPage(page);
                }
            });
        }

        // Modal delegation
        if (this.modalContent) {
            this.modalContent.addEventListener('click', (e) => {
                const addAssetBtn = e.target.closest('.action-add-asset');
                if (addAssetBtn) {
                    e.preventDefault();
                    const cveId = addAssetBtn.dataset.cveId;
                    if (cveId) this.addToAsset(cveId);
                }
            });
        }

    }
    
    async loadVulnerabilities() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading(true);
        
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                sort: this.sortField,
                order: this.sortOrder
            });
            
            if (this.filters.search) params.append('search', this.filters.search);
            if (this.filters.severity) params.append('severity', this.filters.severity);
            if (this.filters.vendor) params.append('vendor', this.filters.vendor);
            if (this.filters.product) params.append('product', this.filters.product);
            if (this.filters.dateFrom) params.append('date_from', this.filters.dateFrom);
            if (this.filters.dateTo) params.append('date_to', this.filters.dateTo);
            if (this.filters.cisaKev) params.append('cisa_kev', 'true');
            
            const response = await fetch(`/vulnerabilities/api/list?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            this.totalItems = data.total;
            this.totalPages = data.pages;
            
            this.renderTable(data.items);
            this.renderPagination();
            this.updateStats(data.stats);
            
        } catch (error) {
            console.error('Failed to load vulnerabilities:', error);
            window.OpenMonitor?.showToast('Failed to load vulnerabilities', 'error');
            this.renderEmptyState('Error loading data. Please try again.');
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }
    
    renderTable(items) {
        if (!this.tableBody) return;
        
        if (!items || items.length === 0) {
            this.renderEmptyState('No vulnerabilities found matching your criteria.');
            return;
        }
        
        if (this.emptyState) {
            this.emptyState.style.display = 'none';
        }
        
        this.tableBody.innerHTML = items.map(vuln => this.renderRow(vuln)).join('');
    }
    
    renderRow(vuln) {
        const severityClass = this.getSeverityClass(vuln.severity);
        const publishedDate = this.formatDate(vuln.published);
        const description = this.truncateText(vuln.description, 120);
        
        return `
            <tr data-cve-id="${vuln.cve_id}" style="cursor: pointer;">
                <td class="fw-medium">
                    <a href="/vulnerabilities/${vuln.cve_id}" class="text-decoration-none fw-bold">
                        ${vuln.cve_id}
                    </a>
                    ${vuln.cisa_kev ? '<span class="badge bg-danger ms-1" title="CISA KEV">KEV</span>' : ''}
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div class="fw-bold ${this.getTextColorClass(severityClass)}">${vuln.cvss_score ? vuln.cvss_score.toFixed(1) : 'N/A'}</div>
                        <span class="badge bg-light text-secondary border">${vuln.cvss_version || ''}</span>
                    </div>
                </td>
                <td>
                    <span class="badge ${this.getBadgeClass(severityClass)}">
                        ${vuln.severity || 'NONE'}
                    </span>
                </td>
                <td>
                    ${this.renderVendorProducts(vuln.vendors)}
                </td>
                <td class="text-nowrap text-muted">
                    ${publishedDate}
                </td>
                <td>
                    <span class="text-muted text-truncate d-inline-block" style="max-width: 300px;" title="${this.escapeHtml(vuln.description)}">
                        ${description}
                    </span>
                </td>
                <td class="text-end">
                    <a href="/vulnerabilities/${vuln.cve_id}" class="btn btn-sm btn-ghost text-primary" title="View Details">
                        <i class="fas fa-eye"></i>
                    </a>
                </td>
            </tr>
        `;
    }
    
    renderVendorProducts(vendors) {
        if (!vendors || vendors.length === 0) {
            return '<span class="text-muted small">—</span>';
        }
        
        const maxDisplay = 2;
        const displayed = vendors.slice(0, maxDisplay);
        const remaining = vendors.length - maxDisplay;
        
        let html = displayed.map(v => 
            `<span class="badge bg-secondary me-1 mb-1 fw-normal">${this.escapeHtml(v)}</span>`
        ).join('');
        
        if (remaining > 0) {
            html += `<span class="badge bg-light text-secondary border fw-normal">+${remaining}</span>`;
        }
        
        return html;
    }
    
    renderEmptyState(message) {
        if (this.tableBody) {
            this.tableBody.innerHTML = '';
        }
        
        if (this.emptyState) {
            this.emptyState.style.display = 'block';
            const msgEl = this.emptyState.querySelector('h5');
            if (msgEl) msgEl.textContent = message;
        }
    }
    
    renderPagination() {
        if (!this.paginationContainer) return;
        
        const start = (this.currentPage - 1) * this.perPage + 1;
        const end = Math.min(this.currentPage * this.perPage, this.totalItems);
        
        if (this.pageInfo) {
            this.pageInfo.textContent = `Showing ${start}-${end} of ${this.totalItems.toLocaleString()}`;
        }
        
        let paginationHtml = '<ul class="pagination mb-0 gap-1">';
        
        // Previous button
        paginationHtml += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${this.currentPage - 1}">
                    <i class="fas fa-chevron-left"></i>
                </button>
            </li>
        `;
        
        // Page numbers
        const pageNumbers = this.getPageNumbers();
        pageNumbers.forEach(page => {
            if (page === '...') {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            } else {
                paginationHtml += `
                    <li class="page-item ${page === this.currentPage ? 'active' : ''}">
                        <button class="page-link page-link-action" data-page="${page}">
                            ${page}
                        </button>
                    </li>
                `;
            }
        });
        
        // Next button
        paginationHtml += `
            <li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${this.currentPage + 1}">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </li>
        `;
        
        paginationHtml += '</ul>';
        this.paginationContainer.innerHTML = paginationHtml;
    }
    
    getPageNumbers() {
        const pages = [];
        const maxVisible = 7;
        
        if (this.totalPages <= maxVisible) {
            for (let i = 1; i <= this.totalPages; i++) {
                pages.push(i);
            }
        } else {
            pages.push(1);
            
            if (this.currentPage > 3) {
                pages.push('...');
            }
            
            const start = Math.max(2, this.currentPage - 1);
            const end = Math.min(this.totalPages - 1, this.currentPage + 1);
            
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            
            if (this.currentPage < this.totalPages - 2) {
                pages.push('...');
            }
            
            pages.push(this.totalPages);
        }
        
        return pages;
    }
    
    goToPage(page) {
        if (page < 1 || page > this.totalPages || page === this.currentPage) return;
        this.currentPage = page;
        this.loadVulnerabilities();
        
        // Scroll to top of table
        this.tableBody?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    updateStats(stats) {
        if (!stats) return;
        
        const updateStat = (el, value) => {
            if (el) {
                el.textContent = value?.toLocaleString() || '0';
                el.classList.remove('skeleton-text', 'w-50');
            }
        };

        updateStat(this.statTotal, stats.total);
        updateStat(this.statCritical, stats.critical);
        updateStat(this.statHigh, stats.high);
        updateStat(this.statMedium, stats.medium);
        updateStat(this.statLow, stats.low);
    }
    
    updateSortIndicators() {
        document.querySelectorAll('[data-sort]').forEach(header => {
            const icon = header.querySelector('.sort-icon');
            if (icon) {
                icon.className = 'sort-icon fas fa-sort text-muted';
            }
        });
        
        const activeHeader = document.querySelector(`[data-sort="${this.sortField}"]`);
        if (activeHeader) {
            const icon = activeHeader.querySelector('.sort-icon');
            if (icon) {
                icon.className = `sort-icon fas fa-sort-${this.sortOrder === 'asc' ? 'up' : 'down'} text-primary`;
            }
        }
    }
    
    async loadVendors() {
        try {
            const response = await fetch('/vulnerabilities/api/vendors');
            if (!response.ok) throw new Error('Failed to load vendors');
            
            const data = await response.json();
            
            if (this.vendorSelect && data.vendors) {
                const currentValue = this.vendorSelect.value;
                this.vendorSelect.innerHTML = '<option value="">All Vendors</option>';
                
                data.vendors.forEach(vendor => {
                    const option = document.createElement('option');
                    option.value = vendor.name;
                    option.textContent = `${vendor.name} (${vendor.count})`;
                    this.vendorSelect.appendChild(option);
                });
                
                if (currentValue) {
                    this.vendorSelect.value = currentValue;
                }
            }
        } catch (error) {
            console.error('Failed to load vendors:', error);
        }
    }
    
    async loadProducts(vendor) {
        if (!this.productSelect) return;
        
        this.productSelect.innerHTML = '<option value="">All Products</option>';
        
        if (!vendor) return;
        
        try {
            const response = await fetch(`/vulnerabilities/api/products?vendor=${encodeURIComponent(vendor)}`);
            if (!response.ok) throw new Error('Failed to load products');
            
            const data = await response.json();
            
            if (data.products) {
                data.products.forEach(product => {
                    const option = document.createElement('option');
                    option.value = product.name;
                    option.textContent = `${product.name} (${product.count})`;
                    this.productSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load products:', error);
        }
    }
    
    clearFilters() {
        this.filters = {
            search: '',
            severity: '',
            vendor: '',
            product: '',
            dateFrom: '',
            dateTo: '',
            cisaKev: false
        };
        
        if (this.searchInput) this.searchInput.value = '';
        if (this.severitySelect) this.severitySelect.value = '';
        if (this.vendorSelect) this.vendorSelect.value = '';
        if (this.productSelect) {
            this.productSelect.value = '';
            this.productSelect.innerHTML = '<option value="">All Products</option>';
        }
        if (this.dateFromInput) this.dateFromInput.value = '';
        if (this.dateToInput) this.dateToInput.value = '';
        if (this.cisaKevCheckbox) this.cisaKevCheckbox.checked = false;
        
        this.currentPage = 1;
        this.loadVulnerabilities();
    }
    
    async showDetail(cveId) {
        if (!this.modalContent) return;

        if (this.detailModalInstance) {
            this.detailModalInstance.show();
        } else {
            const modal = document.getElementById('nvd-detail-modal');
            if (modal) new bootstrap.Modal(modal).show();
        }

        this.modalContent.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2 text-muted">Loading vulnerability details...</p>
            </div>
        `;

        try {
            const response = await fetch(`/vulnerabilities/api/${cveId}`);
            if (!response.ok) throw new Error('Failed to load CVE details');

            // API returns { vulnerability, cvss_metrics, weaknesses, references }
            const data = await response.json();
            const vuln = data.vulnerability || data;
            // Attach related data so renderDetailModal has everything
            vuln._cvss_metrics = data.cvss_metrics || [];
            vuln._weaknesses = data.weaknesses || [];
            vuln._references = data.references || [];
            this.renderDetailModal(vuln);

        } catch (error) {
            console.error('Failed to load CVE details:', error);
            this.modalContent.innerHTML = `
                <div class="text-center py-5 text-danger">
                    <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                    <p>Failed to load vulnerability details</p>
                    <button class="btn btn-secondary mt-2" data-bs-dismiss="modal">Close</button>
                </div>
            `;
        }
    }

    renderDetailModal(vuln) {
        const severityClass = this.getSeverityClass(vuln.base_severity || vuln.severity);
        // Normalise field names — backend uses snake_case from to_dict()
        const severity = vuln.base_severity || vuln.severity || 'NONE';
        const cvssScore = vuln.cvss_score;
        const cvssVersion = vuln.cvss_version || '';
        const publishedDate = vuln.published_date || vuln.published;
        const lastModifiedDate = vuln.last_modified_date || vuln.last_modified;
        const isKev = vuln.is_in_cisa_kev || vuln.cisa_kev || false;
        const vendors = vuln.vendors || vuln.nvd_vendors_data || [];
        // Weaknesses come from _weaknesses (dicts with cwe_id) or flat array
        const weaknesses = (vuln._weaknesses && vuln._weaknesses.length)
            ? vuln._weaknesses.map(w => w.cwe_id || w)
            : (vuln.weaknesses || []);
        const references = (vuln._references && vuln._references.length)
            ? vuln._references
            : (vuln.references || []);
        // Build CVSS object from first metric if available
        let cvssObj = vuln.cvss || null;
        if (!cvssObj && vuln._cvss_metrics && vuln._cvss_metrics.length) {
            cvssObj = vuln._cvss_metrics[0];
        }

        this.modalContent.innerHTML = `
            <div class="d-flex justify-content-between align-items-start mb-4">
                <div>
                    <h4 class="mb-1 d-flex align-items-center gap-2">
                        ${this.escapeHtml(vuln.cve_id)}
                        ${isKev ? '<span class="badge bg-danger">CISA KEV</span>' : ''}
                    </h4>
                    <div class="d-flex align-items-center gap-2 mt-2">
                        <span class="badge ${this.getBadgeClass(severityClass)} fs-6">
                            ${severity}
                        </span>
                        <span class="text-muted">|</span>
                        <div class="fw-bold ${this.getTextColorClass(severityClass)}">CVSS: ${cvssScore ? cvssScore.toFixed(1) : 'N/A'}</div>
                        <span class="text-muted small">(${cvssVersion})</span>
                    </div>
                </div>
                <div class="d-flex gap-2">
                    <a href="https://nvd.nist.gov/vuln/detail/${vuln.cve_id}"
                       target="_blank"
                       class="btn btn-outline-secondary btn-sm">
                        <i class="fas fa-external-link-alt"></i> NVD
                    </a>
                    <button class="btn btn-primary btn-sm action-add-asset" data-cve-id="${vuln.cve_id}">
                        <i class="fas fa-plus"></i> Add to Asset
                    </button>
                </div>
            </div>

            <div class="mb-4">
                <h6 class="fw-bold border-bottom pb-2">Description</h6>
                <p class="text-secondary">${this.escapeHtml(vuln.description || '')}</p>
            </div>

            ${this.renderCVSSSection(cvssObj)}

            <div class="row g-4 mb-4">
                <div class="col-md-6">
                    <h6 class="fw-bold border-bottom pb-2">Timeline</h6>
                    <ul class="list-unstyled">
                        <li class="mb-2"><i class="fas fa-calendar-plus text-muted me-2"></i> Published: ${this.formatDate(publishedDate)}</li>
                        <li><i class="fas fa-calendar-check text-muted me-2"></i> Last Modified: ${this.formatDate(lastModifiedDate)}</li>
                    </ul>
                </div>
                <div class="col-md-6">
                    ${this.renderWeaknessesSection(weaknesses)}
                </div>
            </div>

            ${this.renderVendorsSection(vendors)}
            ${this.renderReferencesSection(references)}
        `;
    }
    
    renderCVSSSection(cvss) {
        if (!cvss) return '';
        
        return `
            <div class="mb-4">
                <h6 class="fw-bold border-bottom pb-2">CVSS ${cvss.version || ''} Metrics</h6>
                <div class="row g-2">
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Attack Vector</small>
                            <div class="fw-medium">${cvss.attack_vector || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Complexity</small>
                            <div class="fw-medium">${cvss.attack_complexity || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Privileges</small>
                            <div class="fw-medium">${cvss.privileges_required || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">User Interaction</small>
                            <div class="fw-medium">${cvss.user_interaction || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Scope</small>
                            <div class="fw-medium">${cvss.scope || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Confidentiality</small>
                            <div class="fw-medium">${cvss.confidentiality_impact || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Integrity</small>
                            <div class="fw-medium">${cvss.integrity_impact || 'N/A'}</div>
                        </div>
                    </div>
                    <div class="col-6 col-md-3">
                        <div class="p-2 border rounded bg-light">
                            <small class="d-block text-muted">Availability</small>
                            <div class="fw-medium">${cvss.availability_impact || 'N/A'}</div>
                        </div>
                    </div>
                </div>
                ${cvss.vector_string ? `<div class="mt-2"><code class="text-muted small bg-light px-2 py-1 rounded">${cvss.vector_string}</code></div>` : ''}
            </div>
        `;
    }
    
    renderVendorsSection(vendors) {
        if (!vendors || vendors.length === 0) return '';
        
        return `
            <div class="mb-4">
                <h6 class="fw-bold border-bottom pb-2">Affected Vendors & Products</h6>
                <div class="d-flex flex-wrap gap-2">
                    ${vendors.map(v => `<span class="badge bg-secondary fw-normal">${this.escapeHtml(v)}</span>`).join('')}
                </div>
            </div>
        `;
    }
    
    renderWeaknessesSection(weaknesses) {
        if (!weaknesses || weaknesses.length === 0) return '';
        
        return `
            <h6 class="fw-bold border-bottom pb-2">Weaknesses (CWE)</h6>
            <div class="d-flex flex-wrap gap-2">
                ${weaknesses.map(w => `
                    <a href="https://cwe.mitre.org/data/definitions/${w.replace('CWE-', '')}.html" 
                        target="_blank" 
                        class="badge bg-light text-primary border text-decoration-none">
                        ${this.escapeHtml(w)}
                    </a>
                `).join('')}
            </div>
        `;
    }
    
    renderReferencesSection(references) {
        if (!references || references.length === 0) return '';
        
        const maxRefs = 5;
        const displayRefs = references.slice(0, maxRefs);
        
        return `
            <div class="mb-4">
                <h6 class="fw-bold border-bottom pb-2">References</h6>
                <ul class="list-unstyled">
                    ${displayRefs.map(ref => `
                        <li class="mb-1 text-truncate">
                            <a href="${this.escapeHtml(ref.url)}" target="_blank" rel="noopener" class="text-decoration-none small">
                                <i class="fas fa-link text-muted me-1"></i>
                                ${this.escapeHtml(ref.url)}
                            </a>
                            ${ref.tags?.length ? `<span class="badge bg-light text-secondary border ms-2" style="font-size: 0.7em;">${ref.tags.join(', ')}</span>` : ''}
                        </li>
                    `).join('')}
                </ul>
                ${references.length > maxRefs ? `<p class="text-muted small">And ${references.length - maxRefs} more references...</p>` : ''}
            </div>
        `;
    }
    
    async addToAsset(cveId) {
        // Redirect to asset selection page
        window.location.href = `/assets?add_cve=${cveId}`;
    }
    
    // Sync Management
    async checkSyncStatus() {
        try {
            const response = await fetch('/vulnerabilities/api/sync/status');
            if (!response.ok) return;
            
            const data = await response.json();
            this.updateSyncUI(data);
            
        } catch (error) {
            console.error('Failed to check sync status:', error);
        }
    }
    
    startSyncStatusPolling() {
        this.syncCheckInterval = setInterval(() => {
            this.checkSyncStatus();
        }, 5000); // Check every 5 seconds
    }
    
    stopSyncStatusPolling() {
        if (this.syncCheckInterval) {
            clearInterval(this.syncCheckInterval);
            this.syncCheckInterval = null;
        }
    }
    
    updateSyncUI(status) {
        if (this.syncStatus && status.last_sync) {
            this.syncStatus.textContent = `Last sync: ${this.formatDate(status.last_sync)}`;
        }
    }
    
    // Export
    async exportData() {
        try {
            const params = new URLSearchParams();
            
            if (this.filters.search) params.append('search', this.filters.search);
            if (this.filters.severity) params.append('severity', this.filters.severity);
            if (this.filters.vendor) params.append('vendor', this.filters.vendor);
            if (this.filters.dateFrom) params.append('date_from', this.filters.dateFrom);
            if (this.filters.dateTo) params.append('date_to', this.filters.dateTo);
            if (this.filters.cisaKev) params.append('cisa_kev', 'true');
            
            const url = `/analytics/api/export?${params}`;
            
            const link = document.createElement('a');
            link.href = url;
            link.download = `vulnerabilities_export_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            window.OpenMonitor?.showToast('Export started', 'success');
            
        } catch (error) {
            console.error('Export failed:', error);
            window.OpenMonitor?.showToast('Export failed', 'error');
        }
    }
    
    // Utility Methods - Use OpenMonitor.utils when available for consistency
    showLoading(show) {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = show ? 'flex' : 'none';
        }
    }

    getSeverityClass(severity) {
        if (!severity) return 'none';
        return severity.toLowerCase();
    }

    getBadgeClass(severityClass) {
        const map = {
            'critical': 'badge-critical',
            'high': 'badge-high',
            'medium': 'badge-medium',
            'low': 'badge-low',
            'none': 'badge-none'
        };
        return map[severityClass] || 'badge-none';
    }

    getTextColorClass(severityClass) {
        const map = {
            'critical': 'text-danger',
            'high': 'text-warning',
            'medium': 'text-info',
            'low': 'text-success',
            'none': 'text-muted'
        };
        return map[severityClass] || 'text-muted';
    }

    formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    escapeHtml(text) {
        // Use global utility if available
        if (window.OpenMonitor?.utils?.escapeHtml) {
            return window.OpenMonitor.utils.escapeHtml(text);
        }
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debounce(func, wait) {
        // Use global utility if available
        if (window.OpenMonitor?.utils?.debounce) {
            return window.OpenMonitor.utils.debounce(func, wait);
        }
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Cleanup
    destroy() {
        this.stopSyncStatusPolling();
    }
}

// Initialize when DOM is ready
let nvdModule;
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('nvd-table-body')) {
        nvdModule = new NVDModule();
        window.nvdModule = nvdModule;
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (nvdModule) {
        nvdModule.destroy();
    }
});