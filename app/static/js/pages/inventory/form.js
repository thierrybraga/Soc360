/**
 * Inventory Form Management JavaScript
 * Handles asset creation/editing
 */

'use strict';

let vendorProfiles = {};

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

    // Handle vendor profile change to update product options
    document.getElementById('asset-vendor-profile')?.addEventListener('change', function() {
        updateProductOptions();
        applyVendorProfile();
    });

    document.getElementById('asset-model')?.addEventListener('input', applyVendorProfile);
    
    loadVendorProfiles();
    loadCategories();
    loadParentAssets();
});

function updateProductOptions() {
    const profileKey = document.getElementById('asset-vendor-profile')?.value;
    const productInput = document.getElementById('asset-product-name');
    const profile = vendorProfiles[profileKey];
    
    // If we have a product list for this profile, we could turn the input into a datalist or just suggest
    // For now, let's keep it as an input but maybe add a datalist
    let datalist = document.getElementById('product-suggestions');
    if (!datalist) {
        datalist = document.createElement('datalist');
        datalist.id = 'product-suggestions';
        document.body.appendChild(datalist);
        productInput.setAttribute('list', 'product-suggestions');
    }
    
    datalist.innerHTML = '';
    if (profile && profile.products) {
        profile.products.forEach(product => {
            const option = document.createElement('option');
            option.value = product.key;
            option.textContent = product.label;
            datalist.appendChild(option);
        });
    }
}

function addSoftwareRow(vendor = '', product = '', version = '') {
    const container = document.getElementById('software-list');
    const row = document.createElement('div');
    row.className = 'software-row d-flex gap-2 mb-2 align-items-center';
    row.innerHTML = `
        <div class="flex-grow-1 row g-2">
            <div class="col-md-4">
                <input type="text" class="form-input software-vendor" placeholder="Fabricante" value="${vendor}" required>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-input software-product" placeholder="Produto" value="${product}" required>
            </div>
            <div class="col-md-4">
                <input type="text" class="form-input software-version" placeholder="Versão" value="${version}">
            </div>
        </div>
        <button type="button" class="btn btn-icon btn-ghost text-danger btn-remove-software" title="Remover">
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
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando…';
    
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
        vendor_profile: document.getElementById('asset-vendor-profile')?.value || '',
        vendor_name: document.getElementById('asset-vendor-name')?.value || '',
        product_name: document.getElementById('asset-product-name')?.value || '',
        model: document.getElementById('asset-model')?.value || '',
        os_name: document.getElementById('asset-os-name')?.value || '',
        os_version: document.getElementById('asset-os-version')?.value || '',
        criticality: document.getElementById('asset-criticality').value,
        category_id: document.getElementById('asset-category')?.value || null,
        parent_id: document.getElementById('asset-parent')?.value || null,
        client_id: document.getElementById('asset-client')?.value || '',
        environment: document.getElementById('asset-environment')?.value || 'PRODUCTION',
        exposure: document.getElementById('asset-exposure')?.value || 'INTERNAL',
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
        
        console.log('Sending asset data:', data);
        
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
            window.OpenMonitor?.showToast(result.message || 'Ativo criado com sucesso!', 'success');

            // Log correlation results if any
            if (result.correlation) {
                console.log('Correlation results:', result.correlation);
                if (result.correlation.matched_cves > 0) {
                    window.OpenMonitor?.showToast(`${result.correlation.matched_cves} CVE(s) correspondente(s) encontrada(s).`, 'info');
                }
            }
            
            // Redirect to inventory list after short delay
            setTimeout(() => {
                window.location.href = '/assets/';
            }, 2000);
        } else {
            throw new Error(result.error || result.message || 'Falha ao criar ativo.');
        }
    } catch (error) {
        console.error('Error saving asset:', error);
        window.OpenMonitor?.showToast(error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
    }
}

async function loadVendorProfiles() {
    try {
        const response = await fetch('/assets/api/vendor-profiles');
        if (!response.ok) return;
        const data = await response.json();
        const select = document.getElementById('asset-vendor-profile');
        if (!select || !Array.isArray(data.profiles)) return;
        data.profiles.forEach(profile => {
            vendorProfiles[profile.key] = profile;
            const option = document.createElement('option');
            option.value = profile.key;
            option.textContent = profile.label;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load vendor profiles:', error);
    }
}

async function loadCategories() {
    try {
        const response = await fetch('/assets/api/categories');
        if (!response.ok) return;
        const data = await response.json();
        const select = document.getElementById('asset-category');
        if (!select || !Array.isArray(data)) return;
        data.forEach(cat => {
            const option = document.createElement('option');
            option.value = cat.id;
            option.textContent = cat.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

async function loadParentAssets() {
    try {
        const response = await fetch('/assets/api/list?per_page=100');
        if (!response.ok) return;
        const data = await response.json();
        const select = document.getElementById('asset-parent');
        if (!select || !Array.isArray(data.items)) return;
        data.items.forEach(asset => {
            const option = document.createElement('option');
            option.value = asset.id;
            option.textContent = asset.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load parent assets:', error);
    }
}

function applyVendorProfile() {
    const profileKey = document.getElementById('asset-vendor-profile')?.value;
    const profile = vendorProfiles[profileKey];
    if (!profile) return;
    const vendorInput = document.getElementById('asset-vendor-name');
    const productInput = document.getElementById('asset-product-name');
    const modelInput = document.getElementById('asset-model');
    if (vendorInput && !vendorInput.value) {
        vendorInput.value = profile.vendor_name;
    }
    const osNameInput = document.getElementById('asset-os-name');
    if (profile.key === 'fortinet' && osNameInput && !osNameInput.value) {
        osNameInput.value = 'FortiOS';
    } else if (profile.key === 'cisco_meraki' && osNameInput && !osNameInput.value) {
        osNameInput.value = 'Meraki Firmware';
    }
    if (productInput && !productInput.value && Array.isArray(profile.products) && profile.products.length > 0) {
        const modelValue = (modelInput?.value || '').toLowerCase();
        if (profile.key === 'fortinet') {
            if (modelValue.includes('fg') || modelValue.includes('fortigate')) {
                productInput.value = 'fortigate';
            } else if (modelValue.includes('fmg') || modelValue.includes('fortimanager')) {
                productInput.value = 'fortimanager';
            } else if (modelValue.includes('faz') || modelValue.includes('fortianalyzer')) {
                productInput.value = 'fortianalyzer';
            } else if (modelValue.includes('fsw') || modelValue.includes('fortiswitch')) {
                productInput.value = 'fortiswitch';
            } else if (modelValue.includes('fap') || modelValue.includes('fortiap')) {
                productInput.value = 'fortiap';
            } else if (modelValue.includes('fml') || modelValue.includes('fortimail')) {
                productInput.value = 'fortimail';
            } else if (modelValue.includes('fwb') || modelValue.includes('fortiweb')) {
                productInput.value = 'fortiweb';
            } else {
                productInput.value = 'fortios'; // Default for Fortinet
            }
            return;
        }
        if (profile.key === 'cisco_meraki') {
            if (modelValue.startsWith('mx')) {
                productInput.value = 'meraki_mx';
                return;
            }
            if (modelValue.startsWith('mr')) {
                productInput.value = 'meraki_mr';
                return;
            }
            if (modelValue.startsWith('ms')) {
                productInput.value = 'meraki_ms';
                return;
            }
            if (modelValue.startsWith('mv')) {
                productInput.value = 'meraki_mv';
                return;
            }
        }
        productInput.value = profile.products[0].key;
    }
}
