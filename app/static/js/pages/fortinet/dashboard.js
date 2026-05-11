/* ── Fortinet Security Dashboard — client-side data loader ─────────── */
(function () {
  'use strict';

  /* ── helpers ─────────────────────────────────────────────── */
  function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function sevBadge(sev) {
    if (!sev) return '<span class="sev-badge sev-LOW">—</span>';
    return `<span class="sev-badge sev-${sev}">${sev}</span>`;
  }

  function kevBadge() {
    return '<span class="kev-badge"><i class="fas fa-flag"></i>KEV</span>';
  }

  function fmtDate(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function productsList(arr) {
    if (!arr || !arr.length) return '<span style="color:var(--text-muted)">—</span>';
    return arr.slice(0, 3).map(p =>
      `<span style="font-size:.7rem; background:rgba(255,255,255,.06); border:1px solid var(--border-color);
        border-radius:3px; padding:.1rem .35rem; color:var(--text-secondary); white-space:nowrap; text-transform:capitalize;">${p}</span>`
    ).join(' ') + (arr.length > 3 ? ` <span style="color:var(--text-muted); font-size:.7rem;">+${arr.length - 3}</span>` : '');
  }

  function criticalityBadge(c) {
    const map = {
      CRITICAL: '#f87171', HIGH: '#fbbf24', MEDIUM: '#fb923c', LOW: '#4ade80'
    };
    const color = map[c] || 'var(--text-muted)';
    return `<span style="font-size:.7rem; font-weight:700; color:${color};">${c || '—'}</span>`;
  }

  /* ── Stats ───────────────────────────────────────────────── */
  fetch('/fortinet/api/dashboard/stats')
    .then(r => r.json())
    .then(d => {
      set('st-assets',     d.total_assets ?? '—');
      set('st-critical',   d.by_severity?.CRITICAL ?? '—');
      set('st-total',      d.total_cves ?? '—');
      set('st-kev',        d.cisa_kev_count ?? '—');
      set('st-recent',     d.recent_30_days ?? '—');
      set('st-open-vulns', d.assets_with_open_vulns ?? '—');

      /* Top Products bar chart */
      const products = d.top_products || [];
      const prodEl = document.getElementById('products-container');
      if (prodEl) {
        if (products.length === 0) {
          prodEl.innerHTML = '<p class="text-muted" style="font-size:.8rem; margin:0;">Nenhum produto encontrado.</p>';
        } else {
          const max = Math.max(...products.map(p => p.count), 1);
          prodEl.innerHTML = `<div class="products-bar">${
            products.filter(p => p.count > 0).map(p => `
              <div class="product-bar-row">
                <span class="product-bar-row__name" title="${p.product}">${p.product}</span>
                <div class="product-bar-row__track">
                  <div class="product-bar-row__fill" style="width:${Math.round(p.count / max * 100)}%"></div>
                </div>
                <span class="product-bar-row__count">${p.count}</span>
              </div>
            `).join('')
          }</div>`;
        }
      }

      /* Known Critical CVEs */
      const knownEl = document.getElementById('known-cves-container');
      if (knownEl) {
        const known = d.known_critical_cves || [];
        if (known.length === 0) {
          knownEl.innerHTML = '<p class="text-muted" style="font-size:.8rem; margin:0;">—</p>';
        } else {
          knownEl.innerHTML = `<div class="known-cve-list">${
            known.map(id => `<a href="/vulnerabilities/${id}" class="known-cve-tag">${id}</a>`).join('')
          }</div>`;
        }
      }
    })
    .catch(err => console.error('[Fortinet] Stats error:', err));

  /* ── Critical CVEs ───────────────────────────────────────── */
  fetch('/fortinet/api/cves/critical')
    .then(r => r.json())
    .then(d => {
      const tbody = document.getElementById('critical-cves-tbody');
      if (!tbody) return;
      const items = d.items || [];

      if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:2rem;">Nenhuma CVE crítica encontrada.</td></tr>';
        return;
      }

      tbody.innerHTML = items.slice(0, 15).map(c => `
        <tr>
          <td><a href="/vulnerabilities/${c.cve_id}">${c.cve_id}</a></td>
          <td><strong style="color:${c.cvss_score >= 9 ? '#f87171' : c.cvss_score >= 7 ? '#fbbf24' : 'var(--text-secondary)'}">
            ${c.cvss_score != null ? c.cvss_score.toFixed(1) : '—'}
          </strong></td>
          <td>${productsList(c.products)}</td>
          <td style="white-space:nowrap;">
            ${sevBadge(c.base_severity)}
            ${c.is_in_cisa_kev ? ' ' + kevBadge() : ''}
            ${c.exploit_available ? ' <span class="kev-badge" style="background:rgba(234,179,8,.12);color:#fbbf24;border-color:rgba(234,179,8,.25);"><i class="fas fa-bomb"></i>Exploit</span>' : ''}
          </td>
          <td style="white-space:nowrap; color:var(--text-muted);">${fmtDate(c.published_date)}</td>
        </tr>
      `).join('');
    })
    .catch(err => {
      const tbody = document.getElementById('critical-cves-tbody');
      if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#f87171; padding:1.5rem;">Erro ao carregar CVEs.</td></tr>';
      console.error('[Fortinet] Critical CVEs error:', err);
    });

  /* ── Assets ─────────────────────────────────────────────── */
  fetch('/fortinet/api/assets?limit=10')
    .then(r => r.json())
    .then(d => {
      const tbody = document.getElementById('assets-tbody');
      if (!tbody) return;
      const items = d.items || [];

      if (items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted); padding:2rem;">Nenhum asset Fortinet encontrado.</td></tr>';
        return;
      }

      tbody.innerHTML = items.map(a => {
        const isActive = a.status === 'ACTIVE';
        const vulnCount = a.vulnerability_count || 0;
        const openVulns = a.open_vulnerabilities || 0;
        const vulnColor = vulnCount === 0 ? 'var(--text-muted)' : vulnCount >= 20 ? '#f87171' : vulnCount >= 5 ? '#fbbf24' : '#fb923c';
        return `
          <tr>
            <td><a href="/assets/${a.id}" style="font-weight:600;">${a.name}</a></td>
            <td>
              <span style="color:var(--text-secondary); text-transform:capitalize;">${a.product_name || a.os_name || '—'}</span>
              ${a.vendor_name ? `<small style="display:block; color:var(--text-muted); font-size:.7rem;">${a.vendor_name}</small>` : ''}
            </td>
            <td>
              <code style="font-size:.78rem; color:var(--text-secondary);">${a.os_version || a.version || '—'}</code>
              ${a.version_eol ? '<span class="sev-badge sev-CRITICAL" style="font-size:.62rem; margin-left:.25rem;">EOL</span>' : ''}
              ${!a.version_eol && !a.version_supported && (a.os_version || a.version) ? '<span class="sev-badge sev-HIGH" style="font-size:.62rem; margin-left:.25rem;">Desatualizado</span>' : ''}
            </td>
            <td><code style="font-size:.78rem;">${a.ip_address || '—'}</code></td>
            <td>${criticalityBadge(a.criticality)}</td>
            <td>
              <span style="font-weight:700; color:${vulnColor};">${vulnCount}</span>
              ${openVulns > 0 ? `<small style="color:#f87171; font-size:.7rem; margin-left:.25rem;">(${openVulns} abertas)</small>` : ''}
            </td>
            <td>
              <span style="display:inline-flex; align-items:center;">
                <span class="status-dot ${isActive ? 'status-dot--active' : 'status-dot--inactive'}"></span>
                <span style="font-size:.78rem; color:var(--text-muted);">${a.status || '—'}</span>
              </span>
            </td>
          </tr>
        `;
      }).join('');
    })
    .catch(err => {
      const tbody = document.getElementById('assets-tbody');
      if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#f87171; padding:1.5rem;">Erro ao carregar assets.</td></tr>';
      console.error('[Fortinet] Assets error:', err);
    });
}());
