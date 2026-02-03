/**
 * Inventory Management JavaScript
 */

'use strict';

let currentPage = 1;
let perPage = 20;
let totalItems = 0;
let totalPages = 1;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize inventory management
    console.log('Inventory module loaded');
    
    // Scan all button
    document.getElementById('scan-all-btn')?.addEventListener('click', scanAllAssets);
    
    // Load initial data
    loadAssets();
    loadStats();

    // Event delegation for table actions
    document.getElementById('assets-table-body')?.addEventListener('click', function(e) {
        const btn = e.target.closest('button');
        if (!btn) return;
        
        const id = btn.dataset.id;
        if (!id) return;

        if (btn.classList.contains('action-view')) {
            viewAsset(id);
        } else if (btn.classList.contains('action-scan')) {
            scanAsset(id);
        }
    });
});

async function loadAssets(page = 1) {
    currentPage = page;
    const tableBody = document.getElementById('assets-table-body');
    const loading = document.getElementById('table-loading');
    const emptyState = document.getElementById('empty-state');
    
    if (loading) loading.style.display = 'flex';
    
    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: perPage
        });

        const response = await fetch(`/assets/api/list?${params}`);
        const data = await response.json();
        
        if (data.items && data.items.length > 0) {
            tableBody.innerHTML = data.items.map(renderAssetRow).join('');
            if (emptyState) emptyState.style.display = 'none';
            
            // Update pagination state
            totalItems = data.total;
            totalPages = data.pages;
            renderPagination();
        } else {
            tableBody.innerHTML = '';
            if (emptyState) emptyState.style.display = 'flex';
            
            // Reset pagination
            totalItems = 0;
            totalPages = 1;
            renderPagination();
        }
    } catch (error) {
        console.error('Failed to load assets:', error);
        window.OpenMonitor?.showToast('Failed to load assets', 'error');
    } finally {
        if (loading) loading.style.display = 'none';
    }
}

async function loadStats() {
    try {
        const response = await fetch('/assets/api/stats');
        const data = await response.json();
        
        const setStat = (id, value) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value || 0;
                el.classList.remove('skeleton-text', 'w-50');
            }
        };

        setStat('stat-total-assets', data.total);
        setStat('stat-critical-vulns', data.critical_vulnerabilities || 0);
        setStat('stat-pending', data.open_vulnerabilities || 0);
        setStat('stat-mitigated', data.mitigated_vulnerabilities || 0);
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderPagination() {
    const paginationContainer = document.getElementById('pagination');
    const infoContainer = document.getElementById('pagination-info');
    
    if (!paginationContainer) return;
    
    // Update info text
    if (infoContainer) {
        const start = (currentPage - 1) * perPage + 1;
        const end = Math.min(currentPage * perPage, totalItems);
        infoContainer.textContent = totalItems > 0 
            ? `Showing ${start}-${end} of ${totalItems} assets`
            : 'No assets found';
    }
    
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }
    
    let html = '<ul class="pagination mb-0 gap-1">';
    
    // Previous
    html += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <button class="page-link" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
        </li>
    `;
    
    // Page numbers
    const range = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) range.push(i);
    } else {
        if (currentPage <= 4) {
            range.push(1, 2, 3, 4, 5, '...', totalPages);
        } else if (currentPage >= totalPages - 3) {
            range.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
        } else {
            range.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
        }
    }
    
    range.forEach(p => {
        if (p === '...') {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        } else {
            html += `
                <li class="page-item ${p === currentPage ? 'active' : ''}">
                    <button class="page-link" onclick="goToPage(${p})">${p}</button>
                </li>
            `;
        }
    });
    
    // Next
    html += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <button class="page-link" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        </li>
    `;
    
    html += '</ul>';
    paginationContainer.innerHTML = html;
}

function goToPage(page) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    loadAssets(page);
}

// Make goToPage global so it can be called from onclick attributes
window.goToPage = goToPage;

function renderAssetRow(asset) {
    const criticalityClass = {
        'CRITICAL': 'critical',
        'HIGH': 'high',
        'MEDIUM': 'medium',
        'LOW': 'low'
    }[asset.criticality] || 'low';
    
    return `
        <tr data-id="${asset.id}">
            <td>
                <div class="d-flex align-items-center gap-2">
                    <i class="fas fa-${getAssetIcon(asset.asset_type || asset.type)} text-muted"></i>
                    <span class="font-weight-medium">${escapeHtml(asset.name)}</span>
                </div>
            </td>
            <td>${asset.asset_type || asset.type}</td>
            <td><span class="badge badge-${criticalityClass}">${asset.criticality}</span></td>
            <td>
                <div class="d-flex gap-1">
                    <span class="badge badge-secondary">${asset.vulnerabilities_count || 0} Vulns</span>
                </div>
            </td>
            <td>
                <div style="color: var(--${getRiskColor(asset.risk_score)})" class="fw-bold">
                    ${asset.risk_score?.toFixed(1) || 'N/A'}
                </div>
            </td>
            <td><span class="badge badge-${asset.status === 'ACTIVE' ? 'success' : 'secondary'}">${asset.status}</span></td>
            <td>${asset.last_scan_at ? formatDate(asset.last_scan_at) : 'Never'}</td>
            <td class="text-end">
                <div class="d-flex justify-content-end gap-1">
                    <button class="btn btn-icon btn-ghost btn-sm action-view" data-id="${asset.id}" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-icon btn-ghost btn-sm action-scan" data-id="${asset.id}" title="Scan">
                        <i class="fas fa-search"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
}

function getAssetIcon(type) {
    const icons = {
        'SERVER': 'server',
        'WORKSTATION': 'desktop',
        'NETWORK': 'network-wired',
        'APPLICATION': 'cube',
        'DATABASE': 'database',
        'CLOUD': 'cloud',
        'CONTAINER': 'docker',
        'IOT': 'microchip'
    };
    return icons[type] || 'server';
}

function getRiskColor(score) {
    if (!score) return 'text-muted';
    if (score >= 9) return 'danger';
    if (score >= 7) return 'warning';
    if (score >= 4) return 'info';
    return 'success';
}

function escapeHtml(text) {
    // Use global utility if available
    if (window.OpenMonitor?.utils?.escapeHtml) {
        return window.OpenMonitor.utils.escapeHtml(text);
    }
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    // Use global utility if available
    if (window.OpenMonitor?.utils?.formatDate) {
        return window.OpenMonitor.utils.formatDate(dateStr, {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function viewAsset(id) {
    window.location.href = `/assets/${id}`;
}

async function scanAsset(id) {
        if (!confirm('Start vulnerability scan for this asset?')) return;
    
    try {
        const response = await fetch('/assets/api/scan', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            },
            body: JSON.stringify({ asset_ids: [id] })
        });
        
        if (response.ok) {
            window.OpenMonitor?.showToast('Scan started successfully', 'success');
            loadAssets();
        } else {
            throw new Error('Scan failed');
        }
    } catch (error) {
        console.error('Scan error:', error);
        window.OpenMonitor?.showToast('Failed to start scan', 'error');
    }
};

async function scanAllAssets() {
    if (!confirm('Start vulnerability scan for ALL assets? This may take a while.')) return;
    
    try {
                const response = await fetch('/assets/api/scan', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
                    },
                    body: JSON.stringify({ scan_all: true })
                });
        
        if (response.ok) {
            window.OpenMonitor?.showToast('Full scan started successfully', 'success');
            loadAssets();
        } else {
            throw new Error('Scan failed');
        }
    } catch (error) {
        console.error('Scan error:', error);
        window.OpenMonitor?.showToast('Failed to start full scan', 'error');
    }
}
