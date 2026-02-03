/**
 * NVD Sync Page Scripts
 * Handles NVD, EUVD, and MITRE synchronization logic.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sync page loaded');

    const elements = {
        nvd: {
            icon: document.getElementById('status-icon'),
            text: document.getElementById('status-text'),
            details: document.getElementById('status-details'),
            container: document.getElementById('progress-container'),
            bar: document.getElementById('progress-bar'),
            lastSync: document.getElementById('last-sync'),
            total: document.getElementById('total-processed'),
            firstSync: document.getElementById('first-sync-status'),
            inserted: document.getElementById('nvd-inserted'),
            updated: document.getElementById('nvd-updated'),
            skipped: document.getElementById('nvd-skipped'),
            errors: document.getElementById('nvd-errors'),
            btns: {
                incremental: document.getElementById('btn-incremental'),
                full: document.getElementById('btn-full'),
                cancel: document.getElementById('btn-cancel')
            }
        },
        euvd: {
            icon: document.getElementById('euvd-status-icon'),
            text: document.getElementById('euvd-status-text'),
            details: document.getElementById('euvd-status-details'),
            container: document.getElementById('euvd-progress-container'),
            bar: document.getElementById('euvd-progress-bar'),
            lastSync: document.getElementById('euvd-last-sync'),
            processed: document.getElementById('euvd-processed'),
            inserted: document.getElementById('euvd-inserted'),
            updated: document.getElementById('euvd-updated'),
            errors: document.getElementById('euvd-errors'),
            btn: document.getElementById('btn-euvd-sync')
        },
        mitre: {
            icon: document.getElementById('mitre-status-icon'),
            text: document.getElementById('mitre-status-text'),
            details: document.getElementById('mitre-status-details'),
            container: document.getElementById('mitre-progress-container'),
            bar: document.getElementById('mitre-progress-bar'),
            lastSync: document.getElementById('mitre-last-sync'),
            processed: document.getElementById('mitre-processed'),
            updated: document.getElementById('mitre-updated'),
            skipped: document.getElementById('mitre-skipped'),
            errors: document.getElementById('mitre-errors'),
            btn: document.getElementById('btn-mitre-enrich')
        }
    };

    const api = window.OpenMonitor?.api || {
        get: async (url) => {
            const res = await fetch(url);
            if (!res.ok) throw new Error(res.statusText);
            return res.json();
        },
        post: async (url, body) => {
            const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
                body: JSON.stringify(body)
            });
            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.error || res.statusText);
            }
            return res.json();
        }
    };

    // --- UI Updaters ---

    function updateNvdUI(data) {
        const el = elements.nvd;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_updated ? new Date(data.last_updated).toLocaleString() : 'Nunca';
        el.total.textContent = `${data.processed_cves || 0} / ${data.total_cves || 0}`;
        if (el.firstSync) el.firstSync.textContent = data.first_sync_completed ? 'Concluído' : 'Pendente';
        
        if(el.inserted) el.inserted.textContent = data.inserted || 0;
        if(el.updated) el.updated.textContent = data.updated || 0;
        if(el.skipped) el.skipped.textContent = data.skipped || 0;
        if(el.errors) el.errors.textContent = data.errors || 0;

        const status = (data.status || '').toUpperCase();
        
        el.container.classList.add('d-none');
        el.btns.cancel.classList.add('d-none');
        el.btns.incremental.disabled = false;
        el.btns.full.disabled = false;

        if (['RUNNING', 'STARTING'].includes(status)) {
            el.icon.innerHTML = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent = 'Sincronização em Andamento';
            el.details.textContent = data.message || (data.mode ? `Modo: ${data.mode}` : 'Processando...');
            
            el.container.classList.remove('d-none');
            const percent = data.total_cves > 0 ? Math.round((data.processed_cves / data.total_cves) * 100) : 0;
            el.bar.style.width = `${percent}%`;
            el.bar.textContent = `${percent}%`;
            
            // Show "Calculating..." if total is 0 but running
            if (data.total_cves === 0) {
                 el.total.textContent = "Calculando...";
            } else {
                 el.total.textContent = `${data.processed_cves || 0} / ${data.total_cves}`;
            }
            el.btns.incremental.disabled = true;
            el.btns.full.disabled = true;
            el.btns.cancel.classList.remove('d-none');
            
            startPolling('nvd');
        } else if (status === 'COMPLETED') {
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success"></i>';
            el.text.textContent = 'Sincronização Concluída';
            el.details.textContent = 'A base de dados está atualizada.';
            stopPolling('nvd');
        } else if (status === 'FAILED') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger"></i>';
            el.text.textContent = 'Erro na Sincronização';
            el.details.textContent = data.message || data.error || 'Verifique os logs.';
            stopPolling('nvd');
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('nvd');
        }
    }

    function updateEuvdUI(data) {
        const el = elements.euvd;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_sync ? new Date(data.last_sync).toLocaleString() : 'Nunca';
        if(el.processed) el.processed.textContent = data.stats?.processed || 0;
        if(el.inserted) el.inserted.textContent = data.stats?.inserted || 0;
        if(el.updated) el.updated.textContent = data.stats?.updated || 0;
        if(el.errors) el.errors.textContent = data.stats?.errors || 0;

        const status = (data.status || 'idle').toLowerCase();
        
        el.container.classList.add('d-none');
        if(el.btn) el.btn.disabled = false;

        if (status === 'running') {
            el.icon.innerHTML = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent = 'Sincronização em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            
            const percent = (data.stats && data.stats.total > 0) ? (data.stats.processed / data.stats.total) * 100 : 0;
            el.bar.style.width = `${percent}%`;
            
            if(el.btn) el.btn.disabled = true;
            startPolling('euvd');
        } else if (status === 'completed') {
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success"></i>';
            el.text.textContent = 'Concluído';
            el.details.textContent = data.message || 'Dados atualizados.';
            stopPolling('euvd');
        } else if (status === 'failed') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger"></i>';
            el.text.textContent = 'Erro';
            el.details.textContent = data.message || 'Falha na sincronização.';
            stopPolling('euvd');
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-secondary"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('euvd');
        }
    }

    function updateMitreUI(data) {
        const el = elements.mitre;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_sync ? new Date(data.last_sync).toLocaleString() : 'Nunca';
        if(el.processed) el.processed.textContent = data.stats?.processed || 0;
        if(el.updated) el.updated.textContent = data.stats?.updated || 0;
        if(el.skipped) el.skipped.textContent = data.stats?.skipped || 0;
        if(el.errors) el.errors.textContent = data.stats?.errors || 0;

        const status = (data.status || 'idle').toLowerCase();
        
        el.container.classList.add('d-none');
        if(el.btn) el.btn.disabled = false;

        if (status === 'running') {
            el.icon.innerHTML = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent = 'Enriquecimento em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            
            const percent = (data.stats && data.stats.total > 0) ? (data.stats.processed / data.stats.total) * 100 : 0;
            el.bar.style.width = `${percent}%`;
            
            if(el.btn) el.btn.disabled = true;
            startPolling('mitre');
        } else if (status === 'completed') {
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success"></i>';
            el.text.textContent = 'Concluído';
            el.details.textContent = data.message || 'Dados enriquecidos.';
            stopPolling('mitre');
        } else if (status === 'failed') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger"></i>';
            el.text.textContent = 'Erro';
            el.details.textContent = data.message || 'Falha no enriquecimento.';
            stopPolling('mitre');
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-secondary"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma operação em andamento.';
            stopPolling('mitre');
        }
    }

    // --- Actions ---

    async function checkStatus(type) {
        try {
            let url;
            if (type === 'nvd') url = '/vulnerabilities/api/sync/status';
            else if (type === 'euvd') url = '/api/euvd/sync/status';
            else if (type === 'mitre') url = '/api/mitre/sync/status';
            
            const data = await api.get(url);
            
            if (type === 'nvd') updateNvdUI(data);
            else if (type === 'euvd') updateEuvdUI(data);
            else if (type === 'mitre') updateMitreUI(data);
        } catch (error) {
            console.error(`Error checking ${type} status:`, error);
            const el = elements[type];
            if (el && el.text && el.text.textContent === 'Verificando...') {
                el.icon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-warning"></i>';
                el.text.textContent = 'Status Indisponível';
                el.details.textContent = 'Não foi possível conectar ao servidor.';
            }
        }
    }

    async function startSync(type, mode) {
        const msg = mode ? `Iniciar sincronização ${mode.toUpperCase()}?` : `Iniciar sincronização ${type.toUpperCase()}?`;
        if (!confirm(msg)) return;
        
        try {
            let url;
            if (type === 'nvd') url = '/vulnerabilities/api/sync/start';
            else if (type === 'euvd') url = '/api/euvd/sync/latest';
            else if (type === 'mitre') url = '/api/mitre/enrich';
            
            const body = mode ? { mode } : {};
            
            await api.post(url, body);
            window.OpenMonitor?.showToast && window.OpenMonitor.showToast('Operação iniciada!', 'success');
            
            checkStatus(type);
            startPolling(type);
        } catch (error) {
            console.error(error);
            window.OpenMonitor?.showToast && window.OpenMonitor.showToast(error.message || 'Erro ao iniciar', 'error');
        }
    }

    async function cancelSync(type) {
        if (!confirm('Cancelar sincronização?')) return;
        try {
            const url = type === 'nvd' ? '/vulnerabilities/api/sync/cancel' : `/api/${type}/sync/cancel`;
            await api.post(url, {});
            window.OpenMonitor?.showToast && window.OpenMonitor.showToast('Cancelamento solicitado', 'info');
        } catch (error) {
            window.OpenMonitor?.showToast && window.OpenMonitor.showToast('Erro ao cancelar', 'error');
        }
    }

    // --- Polling ---
    const intervals = { nvd: null, euvd: null, mitre: null };
    function startPolling(type) {
        if (!intervals[type]) intervals[type] = setInterval(() => checkStatus(type), 3000);
    }
    function stopPolling(type) {
        if (intervals[type]) { clearInterval(intervals[type]); intervals[type] = null; }
    }

    // --- Initialization ---
    if (elements.nvd.btns.incremental) {
        elements.nvd.btns.incremental.addEventListener('click', () => startSync('nvd', 'incremental'));
        elements.nvd.btns.full.addEventListener('click', () => startSync('nvd', 'full'));
        elements.nvd.btns.cancel.addEventListener('click', () => cancelSync('nvd'));
    }
    if (elements.euvd.btn) {
        elements.euvd.btn.addEventListener('click', () => startSync('euvd'));
    }
    if (elements.mitre.btn) {
        elements.mitre.btn.addEventListener('click', () => startSync('mitre'));
    }

    // Initial checks
    checkStatus('nvd');
    checkStatus('euvd');
    checkStatus('mitre');
});