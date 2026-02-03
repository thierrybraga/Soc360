/**
 * Alerts Page Scripts
 * Handles alert listing, filtering, and management.
 */

document.addEventListener('DOMContentLoaded', function() {
    let currentPage = 1;
    let currentAlerts = [];
    const filters = {
        status: '',
        severity: ''
    };

    // DOM Elements
    const tableBody = document.getElementById('alerts-table-body');
    const loadingState = document.getElementById('loading-state');
    const emptyState = document.getElementById('empty-state');
    const alertsTable = document.getElementById('alerts-table');
    const paginationContainer = document.getElementById('pagination-container');
    
    // Modal Elements
    const modalEl = document.getElementById('alertDetailsModal');
    const modal = modalEl ? new bootstrap.Modal(modalEl) : null;

    // Load Alerts
    function loadAlerts() {
        if (!loadingState) return;
        
        loadingState.style.display = 'block';
        if (alertsTable) alertsTable.style.display = 'none';
        if (emptyState) emptyState.style.display = 'none';
        
        const params = new URLSearchParams({
            page: currentPage,
            ...filters
        });

        fetch(`/monitoring/api/alerts?${params}`)
            .then(response => response.json())
            .then(data => {
                renderAlerts(data.items);
                renderPagination(data);
            })
            .catch(error => {
                console.error('Error loading alerts:', error);
                window.OpenMonitor?.showToast('Failed to load alerts', 'error');
            })
            .finally(() => {
                loadingState.style.display = 'none';
            });
    }

    function renderAlerts(items) {
        if (!tableBody) return;
        tableBody.innerHTML = '';
        currentAlerts = items;
        
        if (items.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            return;
        }

        if (alertsTable) alertsTable.style.display = 'table';
        if (paginationContainer) paginationContainer.style.display = 'flex';

        items.forEach(alert => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${renderSeverityBadge(alert.severity)}</td>
                <td>${renderStatusBadge(alert.status)}</td>
                <td>
                    <div class="fw-bold">${escapeHtml(alert.title)}</div>
                    <div class="small text-muted text-truncate" style="max-width: 300px;">${escapeHtml(alert.description || '')}</div>
                </td>
                <td><span class="badge bg-light text-dark border">${escapeHtml(alert.rule_name || (alert.rule_id ? 'Rule #' + alert.rule_id : 'System'))}</span></td>
                <td class="small text-muted">${new Date(alert.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary view-alert-btn" data-id="${alert.id}">
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
            'CRITICAL': 'badge-critical',
            'HIGH': 'badge-high',
            'MEDIUM': 'badge-medium',
            'LOW': 'badge-low'
        };
        const badgeClass = classes[severity] || 'badge-none';
        return `<span class="badge ${badgeClass}">${severity}</span>`;
    }

    function renderStatusBadge(status) {
        const colors = {
            'NEW': 'danger',
            'ACKNOWLEDGED': 'warning',
            'RESOLVED': 'success',
            'DISMISSED': 'secondary'
        };
        const color = colors[status] || 'secondary';
        return `<span class="badge bg-${color}">${status}</span>`;
    }

    function renderActionButtons(alert) {
        if (alert.status === 'RESOLVED' || alert.status === 'DISMISSED') {
            return '';
        }
        
        let buttons = '';
        if (alert.status === 'NEW') {
            buttons += `
                <button class="btn btn-sm btn-outline-success action-btn ms-1" data-id="${alert.id}" data-action="ACKNOWLEDGED" title="Acknowledge">
                    <i class="fas fa-check"></i>
                </button>
            `;
        } else if (alert.status === 'ACKNOWLEDGED') {
            buttons += `
                <button class="btn btn-sm btn-outline-success action-btn ms-1" data-id="${alert.id}" data-action="RESOLVED" title="Resolve">
                    <i class="fas fa-check-double"></i>
                </button>
            `;
        }
        
        return buttons;
    }

    function renderPagination(data) {
        const pagination = document.getElementById('pagination');
        const info = document.getElementById('pagination-info');
        if (!pagination || !info) return;

        info.textContent = `Showing ${((data.page - 1) * 20) + 1} to ${Math.min(data.page * 20, data.total)} of ${data.total} alerts`;
        
        let html = '';
        
        // Previous
        html += `
            <li class="page-item ${!data.has_prev ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${data.prev_num}">&laquo;</button>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= data.pages; i++) {
            if (i === 1 || i === data.pages || (i >= data.page - 2 && i <= data.page + 2)) {
                 html += `
                    <li class="page-item ${i === data.page ? 'active' : ''}">
                        <button class="page-link page-link-action" data-page="${i}">${i}</button>
                    </li>
                `;
            } else if (i === data.page - 3 || i === data.page + 3) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }
        
        // Next
        html += `
            <li class="page-item ${!data.has_next ? 'disabled' : ''}">
                <button class="page-link page-link-action" data-page="${data.next_num}">&raquo;</button>
            </li>
        `;
        
        pagination.innerHTML = html;
    }

    // Modal Actions Delegation
    const modalActions = document.getElementById('modal-actions');
    if (modalActions) {
        modalActions.addEventListener('click', function(e) {
            const btn = e.target.closest('button');
            if (!btn) return;
            
            const id = btn.dataset.id;
            const status = btn.dataset.status;
            
            if (id && status) {
                updateAlertStatus(id, status);
            }
        });
    }

    function viewAlert(id) {
        const alert = currentAlerts.find(a => a.id == id);
        if (!alert) return;

        document.getElementById('modal-severity').innerHTML = renderSeverityBadge(alert.severity);
        document.getElementById('modal-status').innerHTML = renderStatusBadge(alert.status);
        document.getElementById('modal-title').textContent = alert.title;
        document.getElementById('modal-description').textContent = alert.description;
        document.getElementById('modal-details').textContent = JSON.stringify(alert.details || {}, null, 2);
        
        // Render actions in modal
        const actionsContainer = document.getElementById('modal-actions');
        if (actionsContainer) {
            actionsContainer.innerHTML = '';
            if (alert.status === 'NEW') {
                const ackBtn = document.createElement('button');
                ackBtn.className = 'btn btn-success';
                ackBtn.textContent = 'Acknowledge';
                ackBtn.dataset.id = alert.id;
                ackBtn.dataset.status = 'ACKNOWLEDGED';
                actionsContainer.appendChild(ackBtn);
            } else if (alert.status === 'ACKNOWLEDGED') {
                const resolveBtn = document.createElement('button');
                resolveBtn.className = 'btn btn-success';
                resolveBtn.textContent = 'Resolve';
                resolveBtn.dataset.id = alert.id;
                resolveBtn.dataset.status = 'RESOLVED';
                actionsContainer.appendChild(resolveBtn);
            }
        }

        modal.show();
    }

    function updateAlertStatus(id, status) {
        fetch(`/monitoring/api/alerts/${id}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ status: status })
        })
        .then(response => {
            if (response.ok) {
                loadAlerts();
                window.OpenMonitor?.showToast('Alert updated', 'success');
                modal.hide();
            } else {
                window.OpenMonitor?.showToast('Failed to update alert', 'error');
            }
        });
    }
    
    function escapeHtml(text) {
        // Use global utility if available
        if (window.OpenMonitor?.utils?.escapeHtml) {
            return window.OpenMonitor.utils.escapeHtml(text);
        }
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Event Delegation
    if (tableBody) {
        tableBody.addEventListener('click', function(e) {
            const viewBtn = e.target.closest('.view-alert-btn');
            if (viewBtn) {
                const id = viewBtn.getAttribute('data-id');
                viewAlert(id);
                return;
            }

            const actionBtn = e.target.closest('.action-btn');
            if (actionBtn) {
                const id = actionBtn.getAttribute('data-id');
                const action = actionBtn.getAttribute('data-action');
                updateAlertStatus(id, action);
                return;
            }
        });
    }

    const paginationEl = document.getElementById('pagination');
    if (paginationEl) {
        paginationEl.addEventListener('click', function(e) {
            const pageLink = e.target.closest('.page-link-action');
            if (pageLink && !pageLink.parentElement.classList.contains('disabled')) {
                const page = parseInt(pageLink.getAttribute('data-page'));
                if (!isNaN(page)) {
                    currentPage = page;
                    loadAlerts();
                }
            }
        });
    }

    // Filter Listeners
    document.getElementById('filter-status')?.addEventListener('change', (e) => {
        filters.status = e.target.value;
        currentPage = 1;
        loadAlerts();
    });

    document.getElementById('filter-severity')?.addEventListener('change', (e) => {
        filters.severity = e.target.value;
        currentPage = 1;
        loadAlerts();
    });

    document.getElementById('refresh-btn')?.addEventListener('click', loadAlerts);

    // Initial load
    loadAlerts();
import os
import sys
import logging
from app import create_app
from app.services.nvd import NVDSyncService
from app.services.nvd.nvd_sync_service import SyncMode

# Configurar logging para stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    app = create_app()
    with app.app_context():
        print("Starting FULL NVD Sync...")
        service = NVDSyncService()
        
        # Check status first
        progress = service.get_progress()
        if progress.get('status') == 'running':
            print(f"Sync is already running! Mode: {progress.get('mode')}")
            print(f"Progress: {progress.get('processed_cves')} / {progress.get('total_cves')}")
            return

        # Start sync in synchronous mode (blocking) so script doesn't exit immediately
        print("Initiating sync (this may take several hours)...")
        if service.start_sync(mode=SyncMode.FULL, async_mode=False):
            print("Sync completed successfully!")
        else:
            print("Sync failed to start.")

if __name__ == '__main__':
    main()});