/**
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * SYNC PAGE — Data Synchronization Management
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * Handles NVD, EUVD, MITRE, and MITRE ATT&CK synchronization with real-time
 * status updates, progress tracking, and modal-based confirmations.
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 */

document.addEventListener('DOMContentLoaded', function () {

    // ─────────────────────────────────────────────────────────────
    // 1. UI ELEMENTS CACHE
    // ─────────────────────────────────────────────────────────────

    const elements = {
        nvd: {
            icon:      document.getElementById('status-icon'),
            text:      document.getElementById('status-text'),
            details:   document.getElementById('status-details'),
            container: document.getElementById('progress-container'),
            bar:       document.getElementById('progress-bar'),
            lastSync:  document.getElementById('last-sync'),
            total:     document.getElementById('total-processed'),
            firstSync: document.getElementById('first-sync-status'),
            inserted:  document.getElementById('nvd-inserted'),
            updated:   document.getElementById('nvd-updated'),
            skipped:   document.getElementById('nvd-skipped'),
            errors:    document.getElementById('nvd-errors'),
            btns: {
                incremental: document.getElementById('btn-incremental'),
                full:        document.getElementById('btn-full'),
                cancel:      document.getElementById('btn-cancel')
            }
        },
        euvd: {
            icon:      document.getElementById('euvd-status-icon'),
            text:      document.getElementById('euvd-status-text'),
            details:   document.getElementById('euvd-status-details'),
            container: document.getElementById('euvd-progress-container'),
            bar:       document.getElementById('euvd-progress-bar'),
            lastSync:  document.getElementById('euvd-last-sync'),
            processed: document.getElementById('euvd-processed'),
            inserted:  document.getElementById('euvd-inserted'),
            updated:   document.getElementById('euvd-updated'),
            errors:    document.getElementById('euvd-errors'),
            btn:       document.getElementById('btn-euvd-sync')
        },
        mitre: {
            icon:      document.getElementById('mitre-status-icon'),
            text:      document.getElementById('mitre-status-text'),
            details:   document.getElementById('mitre-status-details'),
            container: document.getElementById('mitre-progress-container'),
            bar:       document.getElementById('mitre-progress-bar'),
            lastSync:  document.getElementById('mitre-last-sync'),
            processed: document.getElementById('mitre-processed'),
            updated:   document.getElementById('mitre-updated'),
            skipped:   document.getElementById('mitre-skipped'),
            errors:    document.getElementById('mitre-errors'),
            btn:       document.getElementById('btn-mitre-enrich')
        },
        mitreAttack: {
            icon:      document.getElementById('mitre-attack-status-icon'),
            text:      document.getElementById('mitre-attack-status-text'),
            details:   document.getElementById('mitre-attack-status-details'),
            container: document.getElementById('mitre-attack-progress-container'),
            bar:       document.getElementById('mitre-attack-progress-bar'),
            lastSync:  document.getElementById('mitre-attack-last-sync'),
            processed: document.getElementById('mitre-attack-processed'),
            inserted:  document.getElementById('mitre-attack-inserted'),
            updated:   document.getElementById('mitre-attack-updated'),
            errors:    document.getElementById('mitre-attack-errors'),
            btns: {
                sync: document.getElementById('btn-mitre-attack-sync'),
                map:  document.getElementById('btn-mitre-attack-map')
            }
        }
    };

    // ─────────────────────────────────────────────────────────────
    // 2. API CLIENT
    // ─────────────────────────────────────────────────────────────

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

    // ─────────────────────────────────────────────────────────────
    // 3. TOAST NOTIFICATIONS
    // ─────────────────────────────────────────────────────────────

    function showToast(message, type = 'info', duration = 3500) {
        if (window.OpenMonitor?.showToast) {
            window.OpenMonitor.showToast(message, type);
            return;
        }
        const colors = {
            success: '#10b981', error: '#ef4444',
            warning: '#f59e0b', info: '#3b82f6'
        };
        const toast = document.createElement('div');
        toast.style.cssText = `
            position:fixed; bottom:24px; right:24px; z-index:9999;
            padding:12px 20px; border-radius:10px; font-size:14px; font-weight:500;
            background:${colors[type] || colors.info}; color:#fff;
            box-shadow:0 8px 24px rgba(0,0,0,0.25);
            animation:slideInRight 0.3s ease-out;
            max-width:360px; line-height:1.4;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out forwards';
            setTimeout(() => toast.remove(), 320);
        }, duration);
    }

    // ─────────────────────────────────────────────────────────────
    // 4. CONFIRMATION MODAL (replaces browser confirm())
    // ─────────────────────────────────────────────────────────────

    /**
     * Show a professional modal confirmation dialog.
     * @param {string} message - Question to ask the user
     * @param {string} [title]  - Modal title (default: 'Confirmar Ação')
     * @returns {Promise<boolean>} Resolves true if confirmed, false if cancelled
     */
    function showConfirmModal(message, title = 'Confirmar Ação') {
        return new Promise((resolve) => {
            const modalEl  = document.getElementById('confirmModal');
            const titleEl  = document.getElementById('confirmModalTitle');
            const msgEl    = document.getElementById('confirmModalMessage');
            const okBtn    = document.getElementById('confirmModalOk');

            if (!modalEl) {
                // Fallback if modal HTML is missing
                resolve(window.confirm(message));
                return;
            }

            if (titleEl) titleEl.textContent = title;
            if (msgEl)   msgEl.textContent = message;

            // Clone ok button to remove any previous listeners
            const freshOk = okBtn.cloneNode(true);
            okBtn.parentNode.replaceChild(freshOk, okBtn);

            let resolved = false;

            function done(value) {
                if (resolved) return;
                resolved = true;
                bsModal.hide();
                resolve(value);
            }

            freshOk.addEventListener('click', () => done(true));

            // Resolve false when modal is dismissed (Escape, backdrop, Cancel button)
            modalEl.addEventListener('hidden.bs.modal', () => {
                if (!resolved) done(false);
            }, { once: true });

            const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
            bsModal.show();
        });
    }

    // ─────────────────────────────────────────────────────────────
    // 5. NVD STATUS UPDATER
    // ─────────────────────────────────────────────────────────────

    function updateNvdUI(data) {
        const el = elements.nvd;
        if (!el.lastSync) return;

        // Stats
        el.lastSync.textContent  = data.last_updated
            ? new Date(data.last_updated).toLocaleString('pt-BR') : 'Nunca';
        el.total.textContent     = `${data.processed_cves || 0} / ${data.total_cves || 0}`;
        if (el.firstSync) el.firstSync.textContent = data.first_sync_completed ? '✓ Concluído' : '○ Pendente';
        if (el.inserted) el.inserted.textContent   = data.inserted || 0;
        if (el.updated)  el.updated.textContent    = data.updated  || 0;
        if (el.skipped)  el.skipped.textContent    = data.skipped  || 0;
        if (el.errors)   el.errors.textContent     = data.errors   || 0;

        const status = (data.status || '').toUpperCase();

        // Reset button/progress state
        el.container.classList.add('d-none');
        el.btns.cancel.classList.add('d-none');
        el.btns.incremental.disabled = false;
        el.btns.full.disabled        = false;

        if (['RUNNING', 'STARTING'].includes(status)) {
            el.icon.innerHTML  = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent    = 'Sincronização em Andamento';
            el.details.textContent = data.message || (data.mode ? `Modo: ${data.mode}` : 'Processando...');

            el.container.classList.remove('d-none');
            const pct = data.total_cves > 0
                ? Math.round((data.processed_cves / data.total_cves) * 100) : 0;
            el.bar.style.width  = `${pct}%`;
            el.bar.textContent  = `${pct}%`;
            if (data.total_cves === 0) el.total.textContent = 'Calculando...';

            el.btns.incremental.disabled = true;
            el.btns.full.disabled        = true;
            el.btns.cancel.classList.remove('d-none');
            startPolling('nvd');

        } else if (status === 'COMPLETED') {
            el.icon.innerHTML      = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent    = 'Sincronização Concluída';
            el.details.textContent = 'A base de dados está atualizada.';
            stopPolling('nvd');
            showToast('Sincronização NVD concluída com sucesso!', 'success');

        } else if (status === 'FAILED') {
            el.icon.innerHTML      = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent    = 'Erro na Sincronização';
            el.details.textContent = data.error || 'Falha ao processar dados. Verifique os logs.';
            stopPolling('nvd');
            showToast('Erro ao sincronizar NVD. Verifique os logs.', 'error', 6000);

        } else if (status === 'CANCELLED') {
            el.icon.innerHTML      = '<i class="fas fa-stop-circle fa-3x text-warning animate-popIn"></i>';
            el.text.textContent    = 'Sincronização Cancelada';
            el.details.textContent = 'Operação interrompida pelo usuário.';
            stopPolling('nvd');
            showToast('Sincronização cancelada.', 'warning');

        } else {
            el.icon.innerHTML      = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent    = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('nvd');
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 6. EUVD STATUS UPDATER
    // ─────────────────────────────────────────────────────────────

    function updateEuvdUI(data) {
        const el = elements.euvd;
        if (!el.lastSync) return;

        el.lastSync.textContent  = data.last_sync
            ? new Date(data.last_sync).toLocaleString('pt-BR') : 'Nunca';
        if (el.processed) el.processed.textContent = data.stats?.processed || 0;
        if (el.inserted)  el.inserted.textContent  = data.stats?.inserted  || 0;
        if (el.updated)   el.updated.textContent   = data.stats?.updated   || 0;
        if (el.errors)    el.errors.textContent    = data.stats?.errors    || 0;

        const status = (data.status || 'idle').toLowerCase();

        el.container.classList.add('d-none');
        if (el.btn) el.btn.disabled = false;

        if (status === 'running') {
            el.icon.innerHTML      = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent    = 'Sincronização em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            const pct = (data.stats?.total > 0) ? (data.stats.processed / data.stats.total) * 100 : 0;
            el.bar.style.width = `${pct}%`;
            if (el.btn) el.btn.disabled = true;
            startPolling('euvd');

        } else if (status === 'completed') {
            el.icon.innerHTML      = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent    = 'Concluído';
            el.details.textContent = data.message || 'Dados atualizados.';
            stopPolling('euvd');
            showToast('Sincronização EUVD concluída!', 'success');

        } else if (status === 'failed') {
            el.icon.innerHTML      = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent    = 'Erro';
            el.details.textContent = data.message || 'Falha na sincronização.';
            stopPolling('euvd');
            showToast('Erro ao sincronizar EUVD.', 'error', 6000);

        } else {
            el.icon.innerHTML      = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent    = 'Aguardando';
            el.details.textContent = 'Nenhuma sincronização em andamento.';
            stopPolling('euvd');
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 7. MITRE STATUS UPDATER
    // ─────────────────────────────────────────────────────────────

    function updateMitreUI(data) {
        const el = elements.mitre;
        if (!el.lastSync) return;

        el.lastSync.textContent  = data.last_sync
            ? new Date(data.last_sync).toLocaleString('pt-BR') : 'Nunca';
        if (el.processed) el.processed.textContent = data.stats?.processed || 0;
        if (el.updated)   el.updated.textContent   = data.stats?.updated   || 0;
        if (el.skipped)   el.skipped.textContent   = data.stats?.skipped   || 0;
        if (el.errors)    el.errors.textContent    = data.stats?.errors    || 0;

        const status = (data.status || 'idle').toLowerCase();

        el.container.classList.add('d-none');
        if (el.btn) el.btn.disabled = false;

        if (status === 'running') {
            el.icon.innerHTML      = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent    = 'Enriquecimento em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            const pct = (data.stats?.total > 0) ? (data.stats.processed / data.stats.total) * 100 : 0;
            el.bar.style.width = `${pct}%`;
            if (el.btn) el.btn.disabled = true;
            startPolling('mitre');

        } else if (status === 'completed') {
            el.icon.innerHTML      = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent    = 'Concluído';
            el.details.textContent = data.message || 'Dados enriquecidos.';
            stopPolling('mitre');
            showToast('Enriquecimento MITRE concluído!', 'success');

        } else if (status === 'failed') {
            el.icon.innerHTML      = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent    = 'Erro';
            el.details.textContent = data.message || 'Falha no enriquecimento.';
            stopPolling('mitre');
            showToast('Erro no enriquecimento MITRE.', 'error', 6000);

        } else {
            el.icon.innerHTML      = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent    = 'Aguardando';
            el.details.textContent = 'Nenhuma operação em andamento.';
            stopPolling('mitre');
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 8. MITRE ATT&CK STATUS UPDATER
    // ─────────────────────────────────────────────────────────────

    function updateMitreAttackUI(data) {
        const el = elements.mitreAttack;
        if (!el.lastSync) return;

        el.lastSync.textContent  = data.last_updated
            ? new Date(data.last_updated).toLocaleString('pt-BR') : 'Nunca';
        if (el.processed) el.processed.textContent = data.processed || 0;
        if (el.inserted)  el.inserted.textContent  = data.inserted  || 0;
        if (el.updated)   el.updated.textContent   = data.updated   || 0;
        if (el.errors)    el.errors.textContent    = data.errors    || 0;

        const status = (data.status || 'idle').toLowerCase();

        el.container.classList.add('d-none');
        if (el.btns.sync) el.btns.sync.disabled = false;
        if (el.btns.map)  el.btns.map.disabled  = false;

        if (status === 'running') {
            el.icon.innerHTML      = '<i class="fas fa-sync fa-spin fa-3x text-primary"></i>';
            el.text.textContent    = 'Operação em Andamento';
            el.details.textContent = data.message || 'Processando...';
            el.container.classList.remove('d-none');
            const pct = data.total > 0 ? (data.processed / data.total) * 100 : 0;
            el.bar.style.width = `${pct}%`;
            if (el.btns.sync) el.btns.sync.disabled = true;
            if (el.btns.map)  el.btns.map.disabled  = true;
            startPolling('mitreAttack');

        } else if (status === 'completed') {
            el.icon.innerHTML      = '<i class="fas fa-check-circle fa-3x text-success animate-popIn"></i>';
            el.text.textContent    = 'Concluído';
            el.details.textContent = data.message || 'Dados atualizados.';
            stopPolling('mitreAttack');
            showToast('Operação MITRE ATT&CK concluída!', 'success');

        } else if (status === 'failed') {
            el.icon.innerHTML      = '<i class="fas fa-times-circle fa-3x text-danger animate-popIn"></i>';
            el.text.textContent    = 'Erro';
            el.details.textContent = data.error || 'Falha na operação.';
            stopPolling('mitreAttack');
            showToast('Erro na operação MITRE ATT&CK.', 'error', 6000);

        } else {
            el.icon.innerHTML      = '<i class="fas fa-clock fa-3x text-muted"></i>';
            el.text.textContent    = 'Aguardando';
            el.details.textContent = 'Nenhuma operação em andamento.';
            stopPolling('mitreAttack');
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 9. STATUS CHECK
    // ─────────────────────────────────────────────────────────────

    const STATUS_URLS = {
        nvd:         '/vulnerabilities/api/sync/status',
        euvd:        '/api/euvd/sync/status',
        mitre:       '/api/mitre/sync/status',
        mitreAttack: '/vulnerabilities/api/mitre-attack/status'
    };

    async function checkStatus(type) {
        try {
            const data = await api.get(STATUS_URLS[type]);
            if      (type === 'nvd')         updateNvdUI(data);
            else if (type === 'euvd')        updateEuvdUI(data);
            else if (type === 'mitre')       updateMitreUI(data);
            else if (type === 'mitreAttack') updateMitreAttackUI(data);
        } catch (err) {
            console.error(`[Sync] ${type} status error:`, err);
            const el = elements[type];
            if (el?.text && !['Sincronização em Andamento', 'Enriquecimento em Andamento',
                               'Operação em Andamento'].includes(el.text.textContent)) {
                if (el.icon) el.icon.innerHTML = '<i class="fas fa-exclamation-triangle fa-3x text-warning"></i>';
                el.text.textContent    = 'Status Indisponível';
                el.details.textContent = 'Não foi possível conectar ao servidor.';
            }
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 10. START / CANCEL SYNC
    // ─────────────────────────────────────────────────────────────

    const START_URLS = {
        nvd:         '/vulnerabilities/api/sync/start',
        euvd:        '/api/euvd/sync/latest',
        mitre:       '/api/mitre/sync',
        mitreAttack: '/vulnerabilities/api/mitre-attack/sync'
    };

    async function startSync(type, mode) {
        const label = {
            nvd: mode === 'incremental' ? 'sincronização incremental NVD' : 'sincronização completa NVD',
            euvd: 'sincronização EUVD',
            mitre: 'enriquecimento MITRE',
            mitreAttack: 'sincronização MITRE ATT&CK'
        }[type] || `operação ${type}`;

        const confirmed = await showConfirmModal(
            `Deseja iniciar a ${label}?`,
            'Confirmar Operação'
        );
        if (!confirmed) return;

        try {
            const body = mode ? { mode } : {};
            await api.post(START_URLS[type], body);
            showToast('Operação iniciada!', 'success');
            await checkStatus(type);
            startPolling(type);
        } catch (err) {
            console.error(`[Sync] Error starting ${type}:`, err);
            showToast(err.message || `Erro ao iniciar ${type}`, 'error', 6000);
        }
    }

    async function startMitreAttackMap() {
        const confirmed = await showConfirmModal(
            'Deseja mapear CVEs para técnicas MITRE ATT&CK?',
            'Confirmar Mapeamento'
        );
        if (!confirmed) return;

        try {
            await api.post('/vulnerabilities/api/mitre-attack/map', {});
            showToast('Mapeamento iniciado!', 'success');
            await checkStatus('mitreAttack');
            startPolling('mitreAttack');
        } catch (err) {
            console.error('[Sync] Error starting MITRE ATT&CK mapping:', err);
            showToast(err.message || 'Erro ao iniciar mapeamento', 'error', 6000);
        }
    }

    async function cancelSync(type) {
        const confirmed = await showConfirmModal(
            'Deseja cancelar a sincronização em andamento?',
            'Cancelar Operação'
        );
        if (!confirmed) return;

        try {
            const url = type === 'nvd'
                ? '/vulnerabilities/api/sync/cancel'
                : `/api/${type}/sync/cancel`;
            await api.post(url, {});
            showToast('Cancelamento solicitado.', 'info');
            await checkStatus(type);
        } catch (err) {
            console.error(`[Sync] Error cancelling ${type}:`, err);
            showToast(`Erro ao cancelar ${type}`, 'error');
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 11. POLLING
    // ─────────────────────────────────────────────────────────────

    const intervals = { nvd: null, euvd: null, mitre: null, mitreAttack: null };

    function startPolling(type) {
        if (!intervals[type]) {
            intervals[type] = setInterval(() => checkStatus(type), 3000);
        }
    }

    function stopPolling(type) {
        if (intervals[type]) {
            clearInterval(intervals[type]);
            intervals[type] = null;
        }
    }

    // ─────────────────────────────────────────────────────────────
    // 12. EVENT LISTENERS
    // ─────────────────────────────────────────────────────────────

    // NVD
    elements.nvd.btns.incremental?.addEventListener('click', () => startSync('nvd', 'incremental'));
    elements.nvd.btns.full?.addEventListener('click',        () => startSync('nvd', 'full'));
    elements.nvd.btns.cancel?.addEventListener('click',      () => cancelSync('nvd'));

    // EUVD
    elements.euvd.btn?.addEventListener('click', () => startSync('euvd'));

    // MITRE
    elements.mitre.btn?.addEventListener('click', () => startSync('mitre'));

    // MITRE ATT&CK
    elements.mitreAttack.btns.sync?.addEventListener('click', () => startSync('mitreAttack'));
    elements.mitreAttack.btns.map?.addEventListener('click',  () => startMitreAttackMap());

    // ─────────────────────────────────────────────────────────────
    // 13. INITIALISATION
    // ─────────────────────────────────────────────────────────────

    ['nvd', 'euvd', 'mitre', 'mitreAttack'].forEach(checkStatus);

    window.addEventListener('beforeunload', () => {
        Object.keys(intervals).forEach(stopPolling);
    });

    console.log('[Sync Page] Ready.');
});
