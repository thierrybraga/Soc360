/* Wazuh SIEM — SOC Dashboard
 * Handles KPIs, charts, filters, alerts table, detail modal and workflow actions.
 */
(function () {
    'use strict';

    const API_BASE = '/integrations/wazuh/api';
    const CSRF = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

    // ---------- State ----------
    const state = {
        page: 1,
        perPage: 25,
        filters: {
            severity: '',
            status: '',
            bucket: 'open',
            agent: '',
            q: ''
        },
        hours: 24,
        currentAlertId: null,
        analysts: [],
        charts: { severity: null, timeline: null, rules: null, agents: null }
    };

    // ---------- Utils ----------
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    function toast(msg, type) {
        type = type || 'info';
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = msg;
        const c = document.getElementById('toastContainer');
        if (c) {
            c.appendChild(el);
            setTimeout(() => el.remove(), 4000);
        } else {
            console.log(`[${type}]`, msg);
        }
    }

    async function api(path, opts) {
        opts = opts || {};
        const headers = Object.assign({
            'Accept': 'application/json',
            'X-CSRFToken': CSRF
        }, opts.headers || {});
        if (opts.body && typeof opts.body !== 'string') {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(opts.body);
        }
        const res = await fetch(API_BASE + path, Object.assign({}, opts, { headers }));
        if (!res.ok) {
            let msg = `HTTP ${res.status}`;
            try { const j = await res.json(); if (j.error || j.message) msg = j.error || j.message; } catch (_) {}
            throw new Error(msg);
        }
        if (res.status === 204) return null;
        return res.json();
    }

    function fmtDate(s) {
        if (!s) return '—';
        try {
            const d = new Date(s);
            return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
        } catch (_) { return s; }
    }

    function severityBadge(sev) {
        const map = {
            CRITICAL: 'bg-danger',
            HIGH: 'bg-warning text-dark',
            MEDIUM: 'bg-info text-dark',
            LOW: 'bg-success'
        };
        return `<span class="badge ${map[sev] || 'bg-secondary'}">${sev || '—'}</span>`;
    }

    function statusBadge(st) {
        const cls = {
            NEW: 'bg-danger',
            TRIAGED: 'bg-info text-dark',
            IN_PROGRESS: 'bg-warning text-dark',
            ESCALATED: 'bg-dark',
            RESOLVED: 'bg-success',
            FALSE_POSITIVE: 'bg-secondary',
            DISMISSED: 'bg-light text-dark border'
        }[st] || 'bg-secondary';
        return `<span class="badge ${cls}">${st || '—'}</span>`;
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function buildQuery(extra) {
        const params = new URLSearchParams();
        Object.entries(state.filters).forEach(([k, v]) => { if (v) params.set(k, v); });
        if (extra) Object.entries(extra).forEach(([k, v]) => { if (v != null && v !== '') params.set(k, v); });
        return params.toString();
    }

    // ---------- KPIs + Charts ----------
    async function loadStats() {
        try {
            const s = await api(`/stats?hours=${state.hours}`);
            $('#kpi-window').textContent = s.total_window ?? 0;
            $('#kpi-open').textContent = s.open_count ?? 0;
            $('#kpi-mine').textContent = s.assigned_to_me_open ?? s.mine_open ?? 0;
            $('#kpi-total').textContent = s.total_all ?? 0;
            $('#kpi-window-label').textContent = `Últimas ${state.hours}h`;

            const bySev = s.by_severity || {};
            const total = Object.values(bySev).reduce((a, b) => a + b, 0);
            $('#pill-count-all').textContent = total;
            $('#pill-count-critical').textContent = bySev.CRITICAL || 0;
            $('#pill-count-high').textContent = bySev.HIGH || 0;
            $('#pill-count-medium').textContent = bySev.MEDIUM || 0;
            $('#pill-count-low').textContent = bySev.LOW || 0;

            // Only render charts if Chart.js is available
            if (typeof Chart !== 'undefined') {
                renderSeverityChart(bySev);
                renderTimelineChart(s.timeline || []);
                renderRulesChart(s.top_rules || []);
                renderAgentsChart(s.top_agents || []);
            } else {
                console.warn('Chart.js not available, charts will not render');
            }
        } catch (e) {
            // Only show error if it's not just Chart missing
            if (!e.message.includes('Chart')) {
                toast('Falha ao carregar estatísticas: ' + e.message, 'error');
            } else {
                console.warn('Chart.js loading issue:', e.message);
            }
        }
    }

    function makeChart(key, canvasId, cfg) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        // Wait for Chart to be available
        if (typeof Chart === 'undefined') {
            const parent = canvas.parentElement;
            parent.innerHTML = '<div style="padding:20px; text-align:center; color:#999;">Gráfico não disponível - biblioteca Chart.js não carregou</div>';
            return;
        }

        try {
            if (state.charts[key]) { state.charts[key].destroy(); }
            state.charts[key] = new Chart(canvas.getContext('2d'), cfg);
        } catch (e) {
            console.error(`Chart init failed for ${canvasId}:`, e.message);
            const parent = canvas.parentElement;
            parent.innerHTML = `<div style="padding:20px; text-align:center; color:#f66;">Erro ao renderizar gráfico: ${e.message}</div>`;
        }
    }

    function renderSeverityChart(bySev) {
        const labels = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
        const data = labels.map(l => bySev[l] || 0);
        const colors = ['#a70000', '#d9534f', '#f0ad4e', '#5cb85c'];
        makeChart('severity', 'chart-severity', {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0 }] },
            options: { plugins: { legend: { position: 'bottom' } }, maintainAspectRatio: false }
        });
    }

    function renderTimelineChart(points) {
        const labels = points.map(p => p.bucket);
        const data = points.map(p => p.count);
        makeChart('timeline', 'chart-timeline', {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Alertas',
                    data,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13,110,253,0.15)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                plugins: { legend: { display: false } },
                scales: { x: { ticks: { maxTicksLimit: 10 } }, y: { beginAtZero: true, precision: 0 } },
                maintainAspectRatio: false
            }
        });
    }

    function renderRulesChart(rules) {
        makeChart('rules', 'chart-rules', {
            type: 'bar',
            data: {
                labels: rules.map(r => r.rule_id),
                datasets: [{
                    label: 'Ocorrências',
                    data: rules.map(r => r.count),
                    backgroundColor: '#6f42c1'
                }]
            },
            options: {
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: (items) => rules[items[0].dataIndex]?.description?.slice(0, 80) || rules[items[0].dataIndex]?.rule_id
                        }
                    }
                },
                scales: { x: { beginAtZero: true, precision: 0 } },
                maintainAspectRatio: false
            }
        });
    }

    function renderAgentsChart(agents) {
        makeChart('agents', 'chart-agents', {
            type: 'bar',
            data: {
                labels: agents.map(a => a.agent_name || a.agent_id || '—'),
                datasets: [{
                    label: 'Alertas',
                    data: agents.map(a => a.count),
                    backgroundColor: '#20c997'
                }]
            },
            options: {
                indexAxis: 'y',
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true, precision: 0 } },
                maintainAspectRatio: false
            }
        });
    }

    // ---------- Alerts table ----------
    async function loadAlerts() {
        const tbody = $('#alerts-tbody');
        const table = $('#alerts-table');
        const loading = $('#loading-state');
        const empty = $('#empty-state');
        const pag = $('#pagination-container');

        loading.style.display = '';
        table.style.display = 'none';
        empty.style.display = 'none';
        pag.classList.add('d-none');
        pag.classList.remove('d-flex');

        try {
            const q = buildQuery({ page: state.page, per_page: state.perPage });
            const data = await api(`/alerts?${q}`);
            const items = data.items || [];

            loading.style.display = 'none';
            if (items.length === 0) {
                empty.style.display = '';
                return;
            }

            table.style.display = '';
            tbody.innerHTML = items.map(a => `
                <tr data-id="${a.id}" style="cursor:pointer;">
                    <td>${severityBadge(a.severity)}</td>
                    <td>${statusBadge(a.status)}</td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(a.rule_description || '—')}</div>
                        <div class="small text-muted">Rule ${escapeHtml(a.rule_id || '—')} · L${a.rule_level ?? '—'}</div>
                    </td>
                    <td class="small">
                        <div>${escapeHtml(a.agent_name || '—')}</div>
                        <div class="text-muted">${escapeHtml(a.agent_ip || '')}</div>
                    </td>
                    <td class="small">${escapeHtml(a.assigned_to_name || a.assigned_to?.username || '—')}</td>
                    <td class="small">${fmtDate(a.timestamp)}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-primary btn-open" data-id="${a.id}" title="Abrir">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                    </td>
                </tr>
            `).join('');

            tbody.querySelectorAll('tr').forEach(tr => {
                tr.addEventListener('click', (ev) => {
                    if (ev.target.closest('.btn-open') || !ev.target.closest('tr')) return;
                    openDetail(parseInt(tr.dataset.id, 10));
                });
            });
            tbody.querySelectorAll('.btn-open').forEach(b => {
                b.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    openDetail(parseInt(b.dataset.id, 10));
                });
            });

            renderPagination(data);
        } catch (e) {
            loading.style.display = 'none';
            empty.style.display = '';
            toast('Falha ao carregar alertas: ' + e.message, 'error');
        }
    }

    function renderPagination(data) {
        const total = data.total || 0;
        const pages = Math.max(1, Math.ceil(total / state.perPage));
        const info = $('#pagination-info');
        const pag = $('#pagination');
        const container = $('#pagination-container');
        if (pages <= 1) { container.classList.add('d-none'); container.classList.remove('d-flex'); return; }
        container.classList.remove('d-none');
        container.classList.add('d-flex');
        const from = (state.page - 1) * state.perPage + 1;
        const to = Math.min(state.page * state.perPage, total);
        info.textContent = `${from}–${to} de ${total}`;

        const mk = (p, label, disabled, active) => `
            <button class="btn btn-sm btn-outline-secondary ${active ? 'active' : ''}" ${disabled ? 'disabled' : ''} data-page="${p}">${label}</button>`;
        let html = mk(state.page - 1, '‹', state.page <= 1, false);
        const window = 2;
        const start = Math.max(1, state.page - window);
        const end = Math.min(pages, state.page + window);
        if (start > 1) html += mk(1, '1', false, state.page === 1);
        if (start > 2) html += `<span class="px-1">…</span>`;
        for (let i = start; i <= end; i++) html += mk(i, String(i), false, i === state.page);
        if (end < pages - 1) html += `<span class="px-1">…</span>`;
        if (end < pages) html += mk(pages, String(pages), false, state.page === pages);
        html += mk(state.page + 1, '›', state.page >= pages, false);
        pag.innerHTML = html;
        pag.querySelectorAll('button[data-page]').forEach(b => {
            b.addEventListener('click', () => {
                const p = parseInt(b.dataset.page, 10);
                if (!isNaN(p) && p >= 1 && p <= pages) {
                    state.page = p;
                    loadAlerts();
                }
            });
        });
    }

    // ---------- Detail Modal ----------
    let bsModal = null;
    function getModal() {
        if (!bsModal) bsModal = new bootstrap.Modal(document.getElementById('alertModal'));
        return bsModal;
    }

    async function openDetail(id) {
        state.currentAlertId = id;
        try {
            const d = await api(`/alerts/${id}`);
            const a = d.alert;
            const notes = d.notes || [];
            populateModal(a, notes);
            getModal().show();
        } catch (e) {
            toast('Falha ao carregar alerta: ' + e.message, 'error');
        }
    }

    function populateModal(a, notes) {
        $('#modal-rule-id').textContent = `#${a.id} · Rule ${a.rule_id || '—'} · L${a.rule_level ?? '—'}`;
        $('#modal-title').textContent = a.rule_description || '(sem descrição)';
        $('#modal-badges').innerHTML = [
            severityBadge(a.severity),
            statusBadge(a.status),
            a.assigned_to_name ? `<span class="badge bg-primary"><i class="fas fa-user me-1"></i>${escapeHtml(a.assigned_to_name)}</span>` : ''
        ].join(' ');

        const metaRows = [
            ['Agente', `${escapeHtml(a.agent_name || '—')} (${escapeHtml(a.agent_ip || '—')})`],
            ['Manager', escapeHtml(a.manager_name || '—')],
            ['Decoder', escapeHtml(a.decoder_name || '—')],
            ['Location', `<code>${escapeHtml(a.location || '—')}</code>`],
            ['src_ip / dst_ip', `${escapeHtml(a.src_ip || '—')} → ${escapeHtml(a.dst_ip || '—')}`],
            ['MITRE', (a.rule_mitre_ids || []).map(escapeHtml).join(', ') || '—'],
            ['Groups', (a.rule_groups || []).map(escapeHtml).join(', ') || '—'],
            ['Timestamp', fmtDate(a.timestamp)],
            ['Triado em', fmtDate(a.triaged_at)],
            ['Resolvido em', fmtDate(a.resolved_at)]
        ];
        $('#modal-meta').innerHTML = metaRows.map(([k, v]) =>
            `<dt class="col-sm-3">${k}</dt><dd class="col-sm-9">${v}</dd>`
        ).join('');

        $('#modal-status-select').value = a.status || 'NEW';

        // Assignee dropdown
        const sel = $('#modal-assignee');
        sel.innerHTML = '<option value="">— Não atribuído —</option>' +
            state.analysts.map(u => `<option value="${u.id}" ${a.assigned_to_id == u.id ? 'selected' : ''}>${escapeHtml(u.username)}</option>`).join('');

        // AI block
        if (a.ai_summary || (a.ai_recommendations && a.ai_recommendations.length)) {
            $('#ai-block').style.display = '';
            $('#ai-summary').textContent = a.ai_summary || '';
            $('#ai-recommendations').innerHTML = (a.ai_recommendations || []).map(r => `<li>${escapeHtml(r)}</li>`).join('');
        } else {
            $('#ai-block').style.display = 'none';
        }

        // Timeline
        $('#modal-timeline').innerHTML = notes.length
            ? notes.map(n => `
                <div class="border-start border-3 ps-2 mb-2">
                    <div class="d-flex justify-content-between">
                        <span class="fw-semibold">${escapeHtml(n.action)}</span>
                        <span class="text-muted">${fmtDate(n.created_at)}</span>
                    </div>
                    <div class="small text-muted">${escapeHtml(n.user_name || n.user?.username || 'sistema')}</div>
                    ${n.note ? `<div>${escapeHtml(n.note)}</div>` : ''}
                </div>
            `).join('')
            : '<div class="text-muted">Sem histórico.</div>';

        $('#modal-full-log').textContent = a.full_log || '(vazio)';
        $('#modal-raw').textContent = JSON.stringify(a.raw || {}, null, 2);

        $('#modal-footer-info').textContent = `UID ${a.alert_uid || '—'}`;
    }

    async function doStatusChange() {
        if (!state.currentAlertId) return;
        const status = $('#modal-status-select').value;
        try {
            await api(`/alerts/${state.currentAlertId}/status`, { method: 'PUT', body: { status } });
            toast('Status atualizado', 'success');
            await openDetail(state.currentAlertId);
            loadAlerts();
            loadStats();
        } catch (e) { toast('Erro: ' + e.message, 'error'); }
    }

    async function doAssign() {
        if (!state.currentAlertId) return;
        const v = $('#modal-assignee').value;
        try {
            await api(`/alerts/${state.currentAlertId}/assign`, {
                method: 'POST',
                body: { user_id: v ? parseInt(v, 10) : null }
            });
            toast('Atribuição atualizada', 'success');
            await openDetail(state.currentAlertId);
            loadAlerts();
        } catch (e) { toast('Erro: ' + e.message, 'error'); }
    }

    async function doAddNote() {
        if (!state.currentAlertId) return;
        const input = $('#modal-note');
        const note = (input.value || '').trim();
        if (!note) return;
        try {
            await api(`/alerts/${state.currentAlertId}/note`, { method: 'POST', body: { note } });
            input.value = '';
            await openDetail(state.currentAlertId);
        } catch (e) { toast('Erro: ' + e.message, 'error'); }
    }

    async function doAIAnalyze() {
        if (!state.currentAlertId) return;
        const btn = $('#btn-ai-analyze');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Analisando...';
        try {
            await api(`/alerts/${state.currentAlertId}/ai-analyze`, { method: 'POST', body: {} });
            toast('Análise de IA concluída', 'success');
            await openDetail(state.currentAlertId);
        } catch (e) {
            toast('Erro na IA: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-robot me-1"></i> Analisar com IA';
        }
    }

    // ---------- Dropdowns ----------
    async function loadAgents() {
        try {
            const d = await api('/agents');
            const sel = $('#filter-agent');
            const cur = sel.value;
            const list = d.agents || d.items || [];
            sel.innerHTML = '<option value="">Agente (todos)</option>' +
                list.map(a => `<option value="${escapeHtml(a.agent_name || a.agent_id)}">${escapeHtml(a.agent_name || a.agent_id)}</option>`).join('');
            sel.value = cur;
        } catch (_) {}
    }

    async function loadAnalysts() {
        try {
            const d = await api('/analysts');
            state.analysts = d.analysts || d.items || [];
        } catch (_) { state.analysts = []; }
    }

    // ---------- Sync ----------
    async function triggerSync() {
        const btn = $('#btn-sync');
        btn.disabled = true;
        const orig = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Sincronizando...';
        try {
            const r = await api('/sync', { method: 'POST', body: {} });
            toast(`Sync: ${r.count || 0} alertas`, 'success');
            loadSyncStatus();
            loadStats();
            loadAlerts();
        } catch (e) {
            toast('Sync falhou: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = orig;
        }
    }

    async function loadSyncStatus() {
        const strip = $('#sync-status-strip');
        try {
            const resp = await api('/sync/status');
            const s = (resp && resp.last_sync) ? resp.last_sync : resp;
            if (!s || !s.at) {
                if (strip) { strip.classList.add('d-none'); strip.classList.remove('d-flex'); }
                return;
            }
            strip.classList.remove('d-none');
            strip.classList.add('d-flex');
            strip.classList.remove('alert-secondary', 'alert-success', 'alert-warning');
            strip.classList.add(s.ok ? 'alert-success' : 'alert-warning');
            $('#sync-status-message').textContent = s.message || (s.ok ? 'OK' : 'Erro');
            $('#sync-status-time').textContent = fmtDate(s.at) + (s.count != null ? ` · ${s.count} alertas` : '');
        } catch (_) {
            if (strip) { strip.classList.add('d-none'); strip.classList.remove('d-flex'); }
        }
    }

    // ---------- Wire up ----------
    function wire() {
        // Severity pills
        $$('#severity-pills button').forEach(b => {
            b.addEventListener('click', () => {
                $$('#severity-pills button').forEach(x => x.classList.remove('active'));
                b.classList.add('active');
                state.filters.severity = b.dataset.sev || '';
                state.page = 1;
                loadAlerts();
            });
        });

        $('#filter-status').addEventListener('change', (e) => { state.filters.status = e.target.value; state.page = 1; loadAlerts(); });
        $('#filter-bucket').addEventListener('change', (e) => { state.filters.bucket = e.target.value; state.page = 1; loadAlerts(); });
        $('#filter-agent').addEventListener('change', (e) => { state.filters.agent = e.target.value; state.page = 1; loadAlerts(); });

        let qTimer;
        $('#filter-q').addEventListener('input', (e) => {
            clearTimeout(qTimer);
            qTimer = setTimeout(() => {
                state.filters.q = e.target.value.trim();
                state.page = 1;
                loadAlerts();
            }, 350);
        });

        $('#window-select').addEventListener('change', (e) => {
            state.hours = parseInt(e.target.value, 10) || 24;
            loadStats();
        });

        $('#btn-sync').addEventListener('click', triggerSync);
        $('#btn-refresh').addEventListener('click', () => { loadStats(); loadAlerts(); loadSyncStatus(); loadAgents(); });

        $('#btn-export-csv').addEventListener('click', (e) => {
            e.preventDefault();
            window.open(`${API_BASE}/report/csv?${buildQuery()}`, '_blank');
        });
        $('#btn-export-pdf').addEventListener('click', (e) => {
            e.preventDefault();
            window.open(`${API_BASE}/report/pdf?${buildQuery()}`, '_blank');
        });

        // Modal workflow
        $('#modal-status-select').addEventListener('change', doStatusChange);
        $('#modal-assignee').addEventListener('change', doAssign);
        $('#btn-add-note').addEventListener('click', doAddNote);
        $('#modal-note').addEventListener('keydown', (e) => { if (e.key === 'Enter') doAddNote(); });
        $('#btn-ai-analyze').addEventListener('click', doAIAnalyze);
    }

    // ---------- Boot ----------
    function waitForChart(timeout = 10000) {
        return new Promise((resolve) => {
            if (typeof Chart !== 'undefined') { resolve(); return; }
            const start = Date.now();
            const check = () => {
                if (typeof Chart !== 'undefined') { resolve(); }
                else if (Date.now() - start < timeout) { setTimeout(check, 100); }
                else { console.warn('Chart.js did not load in time'); resolve(); }
            };
            check();
        });
    }

    document.addEventListener('DOMContentLoaded', async () => {
        wire();
        await waitForChart();
        await Promise.all([loadAnalysts(), loadAgents(), loadSyncStatus()]);
        loadStats();
        loadAlerts();
    });
})();
