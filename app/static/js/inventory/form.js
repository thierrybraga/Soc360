/**
 * Inventory Form Management JavaScript
 * Handles asset creation/editing
 */

'use strict';

document.addEventListener('DOMContentLoaded', function() {
    console.log('Inventory Form module loaded');
    
    // Add software button
    document.getElementById('add-software-btn')?.addEventListener('click', function() {
        addSoftwareRow();
    });

    // Form submission
    document.getElementById('asset-form')?.addEventListener('submit', saveAsset);

    // Event delegation for software list removal
    document.getElementById('software-list')?.addEventListener('click', function(e) {
        const removeBtn = e.target.closest('.btn-remove-software');
        if (removeBtn) {
            removeBtn.closest('.software-row').remove();
        }
    });

    // Add initial software row if empty
    if (document.getElementById('software-list')?.children.length === 0) {
        // Optional: Start empty or with one row? Keeping empty is cleaner.
    }
});

function addSoftwareRow(vendor = '', product = '', version = '') {
    const container = document.getElementById('software-list');
    const row = document.createElement('div');
    row.className = 'software-row d-flex gap-2 mb-2 align-items-center';
    row.innerHTML = `
        <div class="flex-grow-1 row g-2">
            <div class="col-md-4">
                <input type="text" class="form-input software-vendor" placeholder="Vendor" value="${vendor}" required>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-input software-product" placeholder="Product" value="${product}" required>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-input software-version" placeholder="Version" value="${version}">
            </div>
        </div>
        <button type="button" class="btn btn-icon btn-ghost text-danger btn-remove-software" title="Remove">
            <i class="fas fa-trash"></i>
        </button>
    `;
    container.appendChild(row);
}

async function saveAsset(e) {
    e.preventDefault();
    
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    
    // Collect software data
    const software = [];
    document.querySelectorAll('.software-row').forEach(row => {
        const vendor = row.querySelector('.software-vendor').value;
        const product = row.querySelector('.software-product').value;
        if (vendor && product) {
            software.push({
                vendor: vendor,
                product: product,
                version: row.querySelector('.software-version').value
            });
        }
    });
    
    const data = {
        name: document.getElementById('asset-name').value,
        asset_type: document.getElementById('asset-type').value,
        ip_address: document.getElementById('asset-ip').value,
        hostname: document.getElementById('asset-hostname').value,
        operating_system: document.getElementById('asset-os').value,
        criticality: document.getElementById('asset-criticality').value,
        description: document.getElementById('asset-description').value,
        rto_hours: document.getElementById('asset-rto').value ? parseFloat(document.getElementById('asset-rto').value) : null,
        rpo_hours: document.getElementById('asset-rpo').value ? parseFloat(document.getElementById('asset-rpo').value) : null,
        operational_cost_per_hour: document.getElementById('asset-cost').value ? parseFloat(document.getElementById('asset-cost').value) : null,
        installed_software: software
    };
    
    try {
        // Assume creation for now as we are on the Add page
        const url = '/assets/api/create';
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            window.OpenMonitor?.showToast('Asset created successfully', 'success');
            // Redirect to inventory list after short delay
            setTimeout(() => {
                window.location.href = '/assets/';
            }, 1000);
        } else {
            throw new Error(result.error || 'Failed to create asset');
        }
    } catch (error) {
        console.error('Error saving asset:', error);
        window.OpenMonitor?.showToast(error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}
