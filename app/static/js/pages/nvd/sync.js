/**
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * SYNC PAGE - Data Synchronization Management
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Handles NVD, EUVD, MITRE, and MITRE ATT&CK synchronization logic with real-time
 * status updates, progress tracking, and comprehensive error handling.
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Sync Page] Initializing...');

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 1. UI ELEMENTS CACHE
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
        },
        mitreAttack: {
            icon: document.getElementById('mitre-attack-status-icon'),
            text: document.getElementById('mitre-attack-status-text'),
            details: document.getElementById('mitre-attack-status-details'),
            container: document.getElementById('mitre-attack-progress-container'),
            bar: document.getElementById('mitre-attack-progress-bar'),
            lastSync: document.getElementById('mitre-attack-last-sync'),
            processed: document.getElementById('mitre-attack-processed'),
            inserted: document.getElementById('mitre-attack-inserted'),
            updated: document.getElementById('mitre-attack-updated'),
            errors: document.getElementById('mitre-attack-errors'),
            btns: {
                sync: document.getElementById('btn-mitre-attack-sync'),
                map: document.getElementById('btn-mitre-attack-map')
            }
        }
    };

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 2. API CLIENT PROXY
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 3. TOAST NOTIFICATION SYSTEM
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    /**
     * Show animated toast notification
     * @param {string} message - Notification message
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in milliseconds (default: 3000)
     */
    function showToast(message, type = 'info', duration = 3000) {
        // Use window OpenMonitor toast if available, otherwise create simple toast
        if (window.OpenMonitor?.showToast) {
            window.OpenMonitor.showToast(message, type);
            return;
        }

        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 9999;
            animation: slideInRight 0.3s ease-out;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#3b82f6'};
            color: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 4. NVD STATUS UPDATER
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    function updateNvdUI(data) {
        const el = elements.nvd;
        if (!el.lastSync) return;

        // Update last sync timestamp
        el.lastSync.textContent = data.last_updated ? new Date(data.last_updated).toLocaleString('pt-BR') : 'Nunca';
        el.total.textContent = `${data.processed_cves || 0} / ${data.total_cves || 0}`;
        if (el.firstSync) el.firstSync.textContent = data.first_sync_completed ? '✓ Concluído' : '○ Pendente';
        
        // Update statistics
        if(el.inserted) el.inserted.textContent = data.inserted || 0;
        if(el.updated) el.updated.textContent = data.updated || 0;
        if(el.skipped) el.skipped.textContent = data.skipped || 0;
        if(el.errors) el.errors.textContent = data.errors || 0;

        const status = (data.status || '').toUpperCase();
        
        // Default state
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
            
            if (data.total_cves === 0) {
                el.total.textContent = "Calculando...";
            }
            
            el.btns.incremental.disabled = true;
            el.btns.full.disabled = true;
            el.btns.cancel.classList.remove('d-none');
            
            startPolling('nvd');
        } else if (status === 'COMPLETED') {
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent = 'Sincronização Concluída';
            el.details.textContent = 'A base de dados está atualizada.';
            stopPolling('nvd');
            showToast('Sincronização NVD concluída com sucesso!', 'success');
        } else if (status === 'FAILED') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent = 'Erro na Sincronização';
            el.details.textContent = data.error || 'Falha ao processar dados. Verifique os logs.';
            stopPolling('nvd');
            showToast('Erro ao sincronizar NVD. Verifique os logs.', 'error', 5000);
        } else if (status === 'CANCELLED') {
            el.icon.innerHTML = '<i class="fas fa-stop-circle fa-3x text-warning animate-popIn"></i>';
            el.text.textContent = 'Sincronização Cancelada';
            el.details.textContent = 'A operação foi interrompida pelo usuário.';
            stopPolling('nvd');
            showToast('Sincronização cancelada pelo usuário.', 'warning');
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('nvd');
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 5. EUVD STATUS UPDATER
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    function updateEuvdUI(data) {
        const el = elements.euvd;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_sync ? new Date(data.last_sync).toLocaleString('pt-BR') : 'Nunca';
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
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent = 'Concluído';
            el.details.textContent = data.message || 'Dados atualizados.';
            stopPolling('euvd');
            showToast('Sincronização EUVD concluída com sucesso!', 'success');
        } else if (status === 'failed') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent = 'Erro';
            el.details.textContent = data.message || 'Falha na sincronização.';
            stopPolling('euvd');
            showToast('Erro ao sincronizar EUVD. Verifique os logs.', 'error', 5000);
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-secondary"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('euvd');
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 6. MITRE STATUS UPDATER
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    function updateMitreUI(data) {
        const el = elements.mitre;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_sync ? new Date(data.last_sync).toLocaleString('pt-BR') : 'Nunca';
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
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent = 'Concluído';
            el.details.textContent = data.message || 'Dados enriquecidos.';
            stopPolling('mitre');
            showToast('Enriquecimento MITRE concluído com sucesso!', 'success');
        } else if (status === 'failed') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent = 'Erro';
            el.details.textContent = data.message || 'Falha no enriquecimento.';
            stopPolling('mitre');
            showToast('Erro ao enriquecer dados MITRE. Verifique os logs.', 'error', 5000);
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-secondary"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma operação em andamento.';
            stopPolling('mitre');
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 7. MITRE ATT&CK STATUS UPDATER
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    function updateMitreAttackUI(data) {
        const el = elements.mitreAttack;
        if (!el.lastSync) return;

        el.lastSync.textContent = data.last_updated ? new Date(data.last_updated).toLocaleString('pt-BR') : 'Nunca';
        if(el.processed) el.processed.textContent = data.processed || 0;
        if(el.inserted) el.inserted.textContent = data.inserted || 0;
        if(el.updated) el.updated.textContent = data.updated || 0;
        if(el.errors) el.errors.textContent = data.errors || 0;

        const status = (data.status || 'idle').toLowerCase();
        
        el.container.classList.add('d-none');
        if(el.btns.sync) el.btns.sync.disabled = false;
        if(el.btns.map) el.btns.map.disabled = false;

        if (status === 'running') {
            el.icon.innerHTML = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent = 'Operação em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            
            const percent = (data.total > 0) ? (data.processed / data.total) * 100 : 0;
            el.bar.style.width = `${percent}%`;
            
            if(el.btns.sync) el.btns.sync.disabled = true;
            if(el.btns.map) el.btns.map.disabled = true;
            startPolling('mitreAttack');
        } else if (status === 'completed') {
            el.icon.innerHTML = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent = 'Concluído';
            el.details.textContent = data.message || 'Dados atualizados.';
            stopPolling('mitreAttack');
            showToast('Operação MITRE ATT&CK concluída com sucesso!', 'success');
        } else if (status === 'failed') {
            el.icon.innerHTML = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent = 'Erro';
            el.details.textContent = data.error || 'Falha na operação.';
            stopPolling('mitreAttack');
            showToast('Erro na operação MITRE ATT&CK. Verifique os logs.', 'error', 5000);
        } else {
            el.icon.innerHTML = '<i class="fas fa-clock fa-3x text-secondary"></i>';
            el.text.textContent = 'Aguardando';
            el.details.textContent = 'Nenhuma operação em andamento.';
            stopPolling('mitreAttack');
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 8. API ACTIONS
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    /**
     * Check status of a sync operation
     * @param {string} type - Type: 'nvd', 'euvd', 'mitre', 'mitreAttack'
     */
    async function checkStatus(type) {
        try {
            let url;
            if (type === 'nvd') url = '/vulnerabilities/api/sync/status';
            else if (type === 'euvd') url = '/api/euvd/sync/status';
            else if (type === 'mitre') url = '/api/mitre/sync/status';
            else if (type === 'mitreAttack') url = '/vulnerabilities/api/mitre-attack/status';
            
            const data = await api.get(url);
            
            if (type === 'nvd') updateNvdUI(data);
            else if (type === 'euvd') updateEuvdUI(data);
            else if (type === 'mitre') updateMitreUI(data);
            else if (type === 'mitreAttack') updateMitreAttackUI(data);

            console.log(`[Sync] ${type.toUpperCase()} status:`, data);
        } catch (error) {
            console.error(`[Sync] Error checking ${type} status:`, error);
            const el = elements[type];
            if (el && el.text) {
                if (el.text.textContent !== 'Sincronização em Andamento' && 
                    el.text.textContent !== 'Enriquecimento em Andamento' &&
                    el.text.textContent !== 'Operação em Andamento') {
                    el.icon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-warning"></i>';
                    el.text.textContent = 'Status Indisponível';
                    el.details.textContent = 'Não foi possível conectar ao servidor.';
                }
            }
        }
    }

    /**
     * Start a sync operation
     * @param {string} type - Type: 'nvd', 'euvd', 'mitre', 'mitreAttack'
     * @param {string} mode - Mode for NVD: 'incremental' or 'full'
     */
    async function startSync(type, mode) {
        const msg = mode 
            ? `Iniciar sincronização ${mode === 'incremental' ? 'incremental' : 'completa'}?` 
            : `Iniciar sincronização ${type.toUpperCase()}?`;
        
        if (!confirm(msg)) return;
        
        try {
            let url;
            if (type === 'nvd') url = '/vulnerabilities/api/sync/start';
            else if (type === 'euvd') url = '/api/euvd/sync/latest';
            else if (type === 'mitre') url = '/api/mitre/enrich';
            
            const body = mode ? { mode } : {};
            
            console.log(`[Sync] Starting ${type}${mode ? ` (${mode})` : ''}...`);
            await api.post(url, body);
            showToast('Operação iniciada!', 'success');
            
            await checkStatus(type);
            startPolling(type);
        } catch (error) {
            console.error(`[Sync] Error starting ${type}:`, error);
            showToast(error.message || `Erro ao iniciar sincronização ${type}`, 'error', 5000);
        }
    }

    /**
     * Cancel a sync operation
     * @param {string} type - Type: 'nvd', 'euvd', 'mitre', 'mitreAttack'
     */
    async function cancelSync(type) {
        if (!confirm('Deseja cancelar a sincronização?')) return;
        try {
            const url = type === 'nvd' ? '/vulnerabilities/api/sync/cancel' : `/api/${type}/sync/cancel`;
            console.log(`[Sync] Cancelling ${type}...`);
            await api.post(url, {});
            showToast('Cancelamento solicitado', 'info');
            await checkStatus(type);
        } catch (error) {
            console.error(`[Sync] Error cancelling ${type}:`, error);
            showToast(`Erro ao cancelar ${type}`, 'error');
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 9. POLLING MANAGEMENT
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    const intervals = { nvd: null, euvd: null, mitre: null, mitreAttack: null };

    function startPolling(type) {
        if (!intervals[type]) {
            console.log(`[Sync] Starting polling for ${type}`);
            intervals[type] = setInterval(() => checkStatus(type), 3000);
        }
    }

    function stopPolling(type) {
        if (intervals[type]) {
            console.log(`[Sync] Stopping polling for ${type}`);
            clearInterval(intervals[type]);
            intervals[type] = null;
        }
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 10. EVENT LISTENERS & INITIALIZATION
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    // NVD Button Listeners
    if (elements.nvd.btns.incremental) {
        elements.nvd.btns.incremental.addEventListener('click', function() {
            this.blur(); // Remove focus for accessibility
            startSync('nvd', 'incremental');
        });
        
        elements.nvd.btns.incremental.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    }

    if (elements.nvd.btns.full) {
        elements.nvd.btns.full.addEventListener('click', function() {
            this.blur();
            startSync('nvd', 'full');
        });
        
        elements.nvd.btns.full.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    }

    if (elements.nvd.btns.cancel) {
        elements.nvd.btns.cancel.addEventListener('click', function() {
            this.blur();
            cancelSync('nvd');
        });
    }

    // EUVD Button Listener
    if (elements.euvd.btn) {
        elements.euvd.btn.addEventListener('click', function() {
            this.blur();
            startSync('euvd');
        });
        
        elements.euvd.btn.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    }

    // MITRE Button Listener
    if (elements.mitre.btn) {
        elements.mitre.btn.addEventListener('click', async function() {
            this.blur();
            try {
                if (!confirm('Iniciar enriquecimento MITRE?')) return;
                await api.post('/api/mitre/sync');
                showToast('Enriquecimento iniciado!', 'success');
                checkStatus('mitre');
                startPolling('mitre');
            } catch (err) {
                console.error('[Sync] Error starting MITRE enrichment:', err);
                showToast('Erro ao iniciar enriquecimento MITRE: ' + err.message, 'error', 5000);
            }
        });
    }

    // MITRE ATT&CK Sync Button Listener
    if (elements.mitreAttack.btns.sync) {
        elements.mitreAttack.btns.sync.addEventListener('click', async function() {
            this.blur();
            try {
                if (!confirm('Sincronizar framework MITRE ATT&CK?')) return;
                await api.post('/vulnerabilities/api/mitre-attack/sync');
                showToast('Sincronização iniciada!', 'success');
                checkStatus('mitreAttack');
                startPolling('mitreAttack');
            } catch (err) {
                console.error('[Sync] Error starting MITRE ATT&CK sync:', err);
                showToast('Erro ao iniciar sincronização MITRE ATT&CK: ' + err.message, 'error', 5000);
            }
        });
    }

    // MITRE ATT&CK Map Button Listener
    if (elements.mitreAttack.btns.map) {
        elements.mitreAttack.btns.map.addEventListener('click', async function() {
            this.blur();
            try {
                if (!confirm('Mapear CVEs para técnicas MITRE ATT&CK?')) return;
                await api.post('/vulnerabilities/api/mitre-attack/map');
                showToast('Mapeamento iniciado!', 'success');
                checkStatus('mitreAttack');
                startPolling('mitreAttack');
            } catch (err) {
                console.error('[Sync] Error starting MITRE ATT&CK mapping:', err);
                showToast('Erro ao iniciar mapeamento MITRE ATT&CK: ' + err.message, 'error', 5000);
            }
        });
    }

    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    // 11. INITIAL STATUS CHECK
    // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    console.log('[Sync Page] Checking initial status...');
    checkStatus('nvd');
    checkStatus('euvd');
    checkStatus('mitre');
    checkStatus('mitreAttack');

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        Object.keys(intervals).forEach(type => stopPolling(type));
    });

    console.log('[Sync Page] Initialization complete');
});
            else if (type === 'mitre') url = '/api/mitre/sync/status';
            else if (type === 'mitreAttack') url = '/vulnerabilities/api/mitre-attack/status';
            
            const data = await api.get(url);
            
            if (type === 'nvd') updateNvdUI(data);
            else if (type === 'euvd') updateEuvdUI(data);
            else if (type === 'mitre') updateMitreUI(data);
            else if (type === 'mitreAttack') updateMitreAttackUI(data);
        } catch (error) {
            console.error(`Error checking ${type} status:`, error);
            const el = elements[type];
            if (el && el.text) {
                // If it was already working, just show a warning but don't stop
                if (el.text.textContent === 'Sincronização em Andamento') {
                    el.details.textContent = 'Aviso: Conexão instável... tentando reconectar.';
                } else if (el.text.textContent === 'Verificando...') {
                    el.icon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-warning"></i>';
                    el.text.textContent = 'Status Indisponível';
                    el.details.textContent = 'Não foi possível conectar ao servidor.';
                }
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
    const intervals = { nvd: null, euvd: null, mitre: null, mitreAttack: null };
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
        elements.mitre.btn.addEventListener('click', async () => {
            try {
                await api.post('/api/mitre/sync');
                checkStatus('mitre');
            } catch (err) {
                alert('Erro ao iniciar enriquecimento MITRE: ' + err.message);
            }
        });
    }

    if (elements.mitreAttack.btns.sync) {
        elements.mitreAttack.btns.sync.addEventListener('click', async () => {
            try {
                await api.post('/vulnerabilities/api/mitre-attack/sync');
                checkStatus('mitreAttack');
            } catch (err) {
                alert('Erro ao iniciar sincronização MITRE ATT&CK: ' + err.message);
            }
        });
    }

    if (elements.mitreAttack.btns.map) {
        elements.mitreAttack.btns.map.addEventListener('click', async () => {
            try {
                await api.post('/vulnerabilities/api/mitre-attack/map');
                checkStatus('mitreAttack');
            } catch (err) {
                alert('Erro ao iniciar mapeamento MITRE ATT&CK: ' + err.message);
            }
        });
    }

    // --- Init ---
    checkStatus('nvd');
    checkStatus('euvd');
    checkStatus('mitre');
    checkStatus('mitreAttack');
});