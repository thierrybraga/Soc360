(function() {
  'use strict';

  const BASE = '/integrations/umbrella';
  const API = {
    orgs: `${BASE}/api/organizations`,
    refresh: `${BASE}/api/refresh-data`,
    generate: `${BASE}/api/generate-report`,
    reports: `${BASE}/api/reports`,
    download: (f) => `${BASE}/download/${f}`,
    orgDetail: (id) => `${BASE}/organization/${id}`,
  };

  const els = {
    orgsContainer: document.getElementById('orgs-container'),
    reportsTable: document.getElementById('reports-table'),
    reportsTbody: document.getElementById('reports-tbody'),
    reportsLoading: document.getElementById('reports-loading'),
    reportsEmpty: document.getElementById('reports-empty'),
    btnRefresh: document.getElementById('btn-refresh-data'),
    btnReload: document.getElementById('btn-reload'),
    btnSubmitReport: document.getElementById('btn-submit-report'),
    reportModalEl: document.getElementById('reportModal'),
    downloadModalEl: document.getElementById('downloadModal'),
    reportForm: document.getElementById('reportForm'),
    reportOrgId: document.getElementById('report-org-id'),
    reportOrgName: document.getElementById('report-org-name'),
    reportStart: document.getElementById('report-start'),
    reportEnd: document.getElementById('report-end'),
    downloadPdf: document.getElementById('downloadPdf'),
    downloadDocx: document.getElementById('downloadDocx'),
    downloadPeriod: document.getElementById('downloadPeriod'),
  };

  let reportModal = null;
  let downloadModal = null;

  function init() {
    if (els.reportModalEl) {
      reportModal = new bootstrap.Modal(els.reportModalEl);
    }
    if (els.downloadModalEl) {
      downloadModal = new bootstrap.Modal(els.downloadModalEl);
    }
    bindEvents();
    loadOrganizations();
    loadReports();
  }

  function bindEvents() {
    els.btnRefresh && els.btnRefresh.addEventListener('click', refreshData);
    els.btnReload && els.btnReload.addEventListener('click', () => { loadOrganizations(); loadReports(); });
    els.btnSubmitReport && els.btnSubmitReport.addEventListener('click', submitReport);
  }

  // ---------------------------------------------------------------------------
  // Orgs
  // ---------------------------------------------------------------------------
  async function loadOrganizations() {
    if (!els.orgsContainer) return;
    try {
      const res = await fetch(API.orgs, { headers: { 'Accept': 'application/json' } });
      const data = await res.json();
      renderOrganizations(data || []);
    } catch (e) {
      showToast('Erro ao carregar organizações', 'danger');
      console.error(e);
    }
  }

  function renderOrganizations(orgs) {
    if (!orgs.length) {
      els.orgsContainer.innerHTML = `
        <div class="col-12">
          <div class="alert alert-secondary">
            <i class="fas fa-info-circle me-2"></i>
            Nenhuma organização carregada. Clique em <strong>Atualizar Dados</strong> para buscar da API (ou mock).
          </div>
        </div>`;
      return;
    }
    els.orgsContainer.innerHTML = orgs.map(o => {
      const orgId = o.organization_id;
      const orgName = escapeHtml(o.organization_name);
      const orgStatus = o.status === 'active' ? 'success' : 'secondary';
      const networkCount = o.network_count || 0;
      const activeNetworks = o.active_networks || 0;
      
      const detailUrl = API.orgDetail(orgId);
      return `
      <div class="col-12 col-md-6 col-xl-4">
        <div class="card h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <h5 class="card-title mb-0 text-truncate" title="${orgName}">
                <a href="${detailUrl}" class="text-decoration-none">
                  ${orgName}
                </a>
              </h5>
              <span class="badge bg-${orgStatus}">${o.status}</span>
            </div>
            <div class="small text-muted mb-3">
              <div>ID: ${orgId}</div>
              <div>Redes: ${networkCount} (${activeNetworks} ativas)</div>
            </div>
            <div class="d-flex gap-2">
              <a href="${detailUrl}" class="btn btn-outline-secondary btn-sm">
                <i class="fas fa-eye me-1"></i> Detalhes
              </a>
              <button class="btn btn-primary btn-sm" onclick="openReportModal(${orgId}, '${orgName.replace(/'/g, "\\'")}')">
                <i class="fas fa-file-alt me-1"></i> Relatório
              </button>
            </div>
          </div>
        </div>
      </div>
    `}).join('');
  }

  // ---------------------------------------------------------------------------
  // Refresh data
  // ---------------------------------------------------------------------------
  async function refreshData() {
    setLoading(els.btnRefresh, true);
    try {
      const res = await fetch(API.refresh, { headers: { 'Accept': 'application/json' } });
      const data = await res.json();
      if (data.success) {
        showToast(data.message || 'Dados atualizados', 'success');
        await loadOrganizations();
        await loadReports();
      } else {
        showToast(data.error || 'Erro ao atualizar dados', 'danger');
      }
    } catch (e) {
      showToast('Erro ao atualizar dados', 'danger');
      console.error(e);
    } finally {
      setLoading(els.btnRefresh, false);
    }
  }

  // ---------------------------------------------------------------------------
  // Generate report
  // ---------------------------------------------------------------------------
  window.openReportModal = function(orgId, orgName) {
    console.log('openReportModal called:', orgId, orgName);
    if (els.reportOrgId) els.reportOrgId.value = orgId;
    if (els.reportOrgName) els.reportOrgName.value = orgName;
    // Default dates: last 30 days
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - 30);
    if (els.reportEnd) els.reportEnd.value = end.toISOString().split('T')[0];
    if (els.reportStart) els.reportStart.value = start.toISOString().split('T')[0];
    if (reportModal) {
      reportModal.show();
    } else {
      console.error('Modal not initialized');
      // Fallback: try to create modal
      try {
        const modalEl = document.getElementById('reportModal');
        if (modalEl) {
          const bsModal = new bootstrap.Modal(modalEl);
          bsModal.show();
        }
      } catch (e) {
        console.error('Failed to show modal:', e);
        alert('Erro ao abrir modal. Recarregue a página.');
      }
    }
  };

  async function submitReport() {
    const payload = {
      organization_id: parseInt(els.reportOrgId.value, 10),
      organization_name: els.reportOrgName.value,
      period_start: els.reportStart.value,
      period_end: els.reportEnd.value,
    };
    if (!payload.period_start || !payload.period_end) {
      showToast('Informe o período', 'warning');
      return;
    }
    setLoading(els.btnSubmitReport, true);
    try {
      const res = await fetch(API.generate, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        showToast(data.message || 'Relatório gerado', 'success');
        reportModal && reportModal.hide();
        
        // Show download modal
        if (data.pdf_url) {
          els.downloadPdf.href = data.pdf_url;
          els.downloadPdf.classList.remove('d-none');
        } else {
          els.downloadPdf.classList.add('d-none');
        }
        if (data.docx_url) {
          els.downloadDocx.href = data.docx_url;
        }
        const startDate = new Date(payload.period_start).toLocaleDateString('pt-BR');
        const endDate = new Date(payload.period_end).toLocaleDateString('pt-BR');
        els.downloadPeriod.textContent = `Período: ${startDate} a ${endDate}`;
        downloadModal && downloadModal.show();
        
        await loadReports();
      } else {
        showToast(data.error || 'Erro ao gerar relatório', 'danger');
      }
    } catch (e) {
      showToast('Erro ao gerar relatório', 'danger');
      console.error(e);
    } finally {
      setLoading(els.btnSubmitReport, false);
    }
  }

  // ---------------------------------------------------------------------------
  // Reports list
  // ---------------------------------------------------------------------------
  async function loadReports() {
    if (els.reportsLoading) els.reportsLoading.style.display = '';
    if (els.reportsTable) els.reportsTable.style.display = 'none';
    if (els.reportsEmpty) els.reportsEmpty.style.display = 'none';
    try {
      const res = await fetch(API.reports, { headers: { 'Accept': 'application/json' } });
      const data = await res.json();
      renderReports(data || []);
    } catch (e) {
      showToast('Erro ao carregar relatórios', 'danger');
      console.error(e);
    } finally {
      if (els.reportsLoading) els.reportsLoading.style.display = 'none';
    }
  }

  function renderReports(reports) {
    if (!reports.length) {
      if (els.reportsTable) els.reportsTable.style.display = 'none';
      if (els.reportsEmpty) els.reportsEmpty.style.display = '';
      return;
    }
    if (els.reportsTable) els.reportsTable.style.display = 'table';
    if (els.reportsEmpty) els.reportsEmpty.style.display = 'none';
    els.reportsTbody.innerHTML = reports.map(r => `
      <tr>
        <td>${escapeHtml(r.organization_name)}</td>
        <td>${r.period_start} → ${r.period_end}</td>
        <td>
          <span class="badge bg-${r.status === 'completed' ? 'success' : (r.status === 'docx_only' ? 'info' : 'secondary')}">
            ${r.status}
          </span>
        </td>
        <td>${r.created_at ? new Date(r.created_at).toLocaleString('pt-BR') : '-'}</td>
        <td class="text-end">
          ${r.docx_filename ? `<a class="btn btn-sm btn-outline-light me-1" href="${API.download(r.docx_filename)}" title="DOCX"><i class="fas fa-file-word"></i></a>` : ''}
          ${r.pdf_filename ? `<a class="btn btn-sm btn-outline-light" href="${API.download(r.pdf_filename)}" title="PDF"><i class="fas fa-file-pdf"></i></a>` : ''}
        </td>
      </tr>
    `).join('');
  }

  // ---------------------------------------------------------------------------
  // Utils
  // ---------------------------------------------------------------------------
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    const original = btn.dataset.originalText || btn.innerHTML;
    if (loading) {
      btn.dataset.originalText = original;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Aguarde...';
    } else {
      btn.innerHTML = btn.dataset.originalText || original;
    }
  }

  function showToast(message, type) {
    if (window.showToast) {
      window.showToast(message, type);
      return;
    }
    // fallback
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
