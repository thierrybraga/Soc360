import os, re

BASE = os.path.join(os.path.dirname(__file__), '..')
CSS_DIR = os.path.join(BASE, 'app', 'static', 'css')

def read(path): return open(path, encoding='utf-8').read()
def write(path, content): open(path, 'w', encoding='utf-8', newline='\n').write(content)
def append_css(filename, content):
    path = os.path.join(CSS_DIR, filename)
    existing = read(path)
    write(path, existing.rstrip() + '\n\n' + content + '\n')
    print(f'  CSS appended to {filename}')

# === 1. umbrella.css ===
append_css('umbrella.css', """\
/* === Organization Detail page === */
[data-page="umbrella-org"] .card {
    background-color: var(--card-bg);
    color: var(--text-primary);
    border-color: var(--border-color);
}
[data-page="umbrella-org"] .table { color: var(--text-primary); }
[data-page="umbrella-org"] .table > :not(caption) > * > * { background: transparent; }
[data-page="umbrella-org"] .stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
}
[data-page="umbrella-org"] .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
}
[data-page="umbrella-org"] .status-active { background: rgba(16,185,129,.2); color: #10b981; }
[data-page="umbrella-org"] .status-inactive { background: rgba(239,68,68,.2); color: #ef4444; }
[data-page="umbrella-org"] code {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    padding: 0.2rem 0.4rem;
    border-radius: 0.25rem;
}
[data-page="umbrella-org"] .text-muted { color: var(--text-secondary) !important; }
#reportModal .modal-content { background-color: var(--card-bg); color: var(--text-primary); border-color: var(--border-color); }
#reportModal .modal-header,
#reportModal .modal-footer { border-color: var(--border-color); }
#reportModal .form-control { background-color: var(--input-bg, var(--card-bg)); color: var(--text-primary); border-color: var(--border-color); }
/* Status indicator dot icon */
.umb-status-dot { font-size: 0.5rem; }
""")

# === 2. admin.css ===
append_css('admin.css', """\
/* === Notification Settings page === */
.channel-config {
    display: none;
    margin-top: 15px;
    padding: 15px;
    background: var(--bg-secondary);
    border-radius: 5px;
    border-left: 4px solid var(--primary);
}
.channel-toggle:checked + .channel-config { display: block; }
.event-setting-card .card-header { background: var(--bg-secondary); border-bottom: 1px solid var(--border-color); }
.form-check-inline { margin-right: 20px; }
.test-notification-form .form-group { margin-bottom: 15px; }
.loading-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(255,255,255,.8);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}
""")

# === 3. reports.css - CVE link, meta val, pre block, risk report ===
append_css('reports.css', """\
/* === Inline mono helpers === */
.cve-link-mono { font-family: ui-monospace, monospace; font-size: .85rem; }
.meta-val-mono { font-family: ui-monospace, monospace; font-size: .78rem; }
.rpt-raw-pre { max-height: 400px; overflow: auto; }

/* === Risk Report page === */
.risk-report-container { max-width: 1200px; margin: 0 auto; padding: 1.5rem; }
.risk-report-header {
    background: linear-gradient(135deg, var(--primary, #007bff) 0%, var(--primary-600, #0056b3) 100%);
    color: white;
    padding: 2rem;
    border-radius: .75rem;
    margin-bottom: 2rem;
    box-shadow: 0 4px 24px rgba(0,0,0,.15);
}
.risk-report-content {
    background: var(--card-bg);
    border-radius: .75rem;
    padding: 2rem;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
    border: 1px solid var(--border-color);
}
.risk-report-content h1, .risk-report-content h2, .risk-report-content h3 { color: var(--text-primary); margin-top: 1.5rem; margin-bottom: 1rem; }
.risk-report-content h1 { font-size: 1.5rem; border-bottom: 2px solid var(--primary); padding-bottom: .5rem; }
.risk-report-content h2 { font-size: 1.25rem; color: var(--primary); }
.risk-report-content h3 { font-size: 1.1rem; }
.risk-report-content p { line-height: 1.6; margin-bottom: 1rem; color: var(--text-secondary); }
.risk-report-content ul, .risk-report-content ol { margin-bottom: 1rem; padding-left: 1.5rem; }
.risk-report-content li { margin-bottom: .25rem; color: var(--text-secondary); }
.risk-report-content strong { color: var(--text-primary); font-weight: 600; }
.risk-report-content code { background: var(--bg-secondary); padding: .1rem .35rem; border-radius: .25rem; font-family: ui-monospace,monospace; color: var(--primary); }
.risk-report-content pre { background: var(--bg-secondary); padding: 1rem; border-radius: .5rem; overflow-x: auto; border: 1px solid var(--border-color); }
.risk-report-actions { margin-top: 2rem; display: flex; gap: 1rem; flex-wrap: wrap; }
.btn-print { background: var(--success); border-color: var(--success); }
.btn-print:hover { filter: brightness(.9); }
.btn-export { background: var(--info); border-color: var(--info); }
.btn-export:hover { filter: brightness(.9); }
.risk-loading-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,.5); display: none; justify-content: center; align-items: center; z-index: 9999; }
.risk-loading-spinner { background: var(--card-bg); padding: 2rem; border-radius: .75rem; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,.2); }
.risk-spinner { border: 4px solid var(--border-color); border-top: 4px solid var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: riskSpin 1s linear infinite; margin: 0 auto 1rem; }
@keyframes riskSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
@media print {
    .risk-report-actions, .navbar, .footer { display: none !important; }
    .risk-report-container { max-width: none; margin: 0; padding: 0; }
    .risk-report-header, .risk-report-content { box-shadow: none; border: none; }
}
@media (max-width: 768px) {
    .risk-report-container { padding: 1rem; }
    .risk-report-header, .risk-report-content { padding: 1.5rem; }
    .risk-report-actions { flex-direction: column; }
    .risk-report-actions .btn { width: 100%; }
}
""")

# === 4. dashboard.css ===
append_css('dashboard.css', """\
/* === Dashboard icon/value color helpers === */
.dash-icon-critical  { color: var(--critical); }
.dash-icon-warning   { color: var(--warning); }
.dash-icon-danger    { color: var(--danger); }
.dash-sla-value--danger  { color: var(--danger); }
.dash-sla-value--warning { color: var(--warning); }
.dash-time-range     { min-width: 150px; }
""")

# === 5. assets.css ===
append_css('assets.css', """\
/* === Asset list empty-state icon === */
.ast-empty-icon { font-size: 4rem; color: var(--text-muted, #6c757d); }
""")

# === 6. monitoring.css ===
append_css('monitoring.css', """\
/* === Monitoring search input group width === */
.mon-search-group { width: 250px; }
""")

# === 7. Create search.css ===
search_css_path = os.path.join(CSS_DIR, 'search.css')
search_css = """\
/* === Search / IP Lookup page === */
.search-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08);
  transition: all .3s ease;
}
.search-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.12); transform: translateY(-2px); }
.search-card .card-header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark, var(--primary)) 100%);
  color: white;
  border-radius: 12px 12px 0 0;
  padding: 1rem 1.5rem;
  border: none;
}
.search-card .card-title { margin: 0; font-size: 1.1rem; font-weight: 600; display: flex; align-items: center; }
.search-card .card-body { padding: 2rem; }
.quick-examples { background: var(--bg-secondary); border-radius: 8px; padding: 1rem; border: 1px solid var(--border-color); }
.quick-examples h6 { font-size: .875rem; font-weight: 600; margin-bottom: .75rem; }
.example-btn { font-size: .8rem; padding: .375rem .75rem; border-radius: 6px; transition: all .2s ease; text-align: left; }
.example-btn:hover { transform: translateX(4px); }
.recent-searches { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; max-height: 200px; overflow-y: auto; }
.recent-searches h6 { font-size: .875rem; font-weight: 600; margin-bottom: .75rem; }
.recent-search-item {
  display: flex;
  align-items: center;
  padding: .5rem .75rem;
  margin-bottom: .25rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  transition: all .2s ease;
  font-size: .875rem;
}
.recent-search-item:hover { background: var(--bg-secondary); border-color: var(--primary); transform: translateX(2px); }
.recent-search-item span { flex: 1; margin-left: .5rem; }
.recent-search-item .remove-recent { opacity: 0; transition: opacity .2s ease; padding: .125rem .25rem; font-size: .75rem; }
.recent-search-item:hover .remove-recent { opacity: 1; }
.input-group .btn { border-left: none; }
.input-group-text { background: var(--bg-secondary); border-color: var(--border-color); color: var(--text-muted); }
.btn-loading .spinner-border { width: 1rem; height: 1rem; }
@media (max-width: 768px) {
  .search-card .card-body { padding: 1.5rem; }
  .quick-examples, .recent-searches { margin-top: 1rem; }
  .form-actions .d-grid { margin-top: 1rem; }
}
"""
write(search_css_path, search_css)
print('  CSS created: search.css')

# === 8. Create newsletter.css ===
newsletter_css_path = os.path.join(CSS_DIR, 'newsletter.css')
newsletter_css = """\
/* === Newsletter Admin pages === */
.nl-avatar-sm { width: 32px; height: 32px; object-fit: cover; border-radius: 50%; }
[data-page="newsletter-dashboard"] .card { transition: transform .2s ease-in-out; }
[data-page="newsletter-dashboard"] .card:hover { transform: translateY(-2px); }
[data-page="newsletter-subscribers"] .table th { font-weight: 600; color: var(--text-secondary); border-bottom: 2px solid var(--border-color); }
[data-page="newsletter-subscribers"] .table td { vertical-align: middle; }
[data-page="newsletter-send"] .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 .2rem rgba(13,110,253,.25); }
[data-page="newsletter-send"] #previewContent { min-height: 200px; line-height: 1.6; }
[data-page="newsletter-send"] .toast { min-width: 300px; }
[data-page="newsletter-unsubscribe"] .card { border: none; border-radius: 15px; }
[data-page="newsletter-unsubscribe"] .card-header { border-bottom: 2px solid #ffc107; }
[data-page="newsletter-unsubscribe"] .btn { border-radius: 8px; font-weight: 500; }
/* Preview modal content area */
.newsletter-preview-body { background: var(--bg-secondary); }
"""
write(newsletter_css_path, newsletter_css)
print('  CSS created: newsletter.css')

# === 9. Create coming-soon.css ===
coming_soon_css_path = os.path.join(CSS_DIR, 'coming-soon.css')
coming_soon_css = """\
/* === Coming Soon landing page === */
.coming-soon-container {
    min-height: 100vh;
    background: linear-gradient(135deg, var(--primary, #007bff) 0%, var(--primary-600, #0056b3) 100%);
    display: flex;
    align-items: center;
    position: relative;
    overflow: hidden;
}
.coming-soon-container::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
}
.coming-soon-card {
    background: rgba(255,255,255,.1);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,.2);
    border-radius: 24px;
    padding: 3rem;
    box-shadow: 0 20px 40px rgba(0,0,0,.1);
    position: relative;
    z-index: 1;
}
.coming-soon-icon { font-size: 4rem; color: var(--warning, #ffc107); text-shadow: 0 0 20px rgba(255,193,7,.3); }
.coming-soon-title { font-size: 2.5rem; font-weight: 700; color: white; margin-bottom: 1rem; text-shadow: 0 2px 4px rgba(0,0,0,.1); }
.coming-soon-subtitle { font-size: 1.1rem; color: rgba(255,255,255,.9); line-height: 1.6; }
.countdown-timer { margin: 2rem 0; }
.countdown-item { background: rgba(255,255,255,.15); border-radius: 16px; padding: 1.5rem 1rem; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,.2); min-width: 100px; }
.countdown-number { font-size: 2rem; font-weight: 700; color: white; line-height: 1; }
.countdown-label { font-size: .875rem; color: rgba(255,255,255,.8); margin-top: .5rem; text-transform: uppercase; letter-spacing: .5px; }
.wishlist-form-container { background: rgba(255,255,255,.1); border-radius: 20px; padding: 2rem; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,.2); }
.form-title { color: white; font-weight: 600; margin-bottom: 1.5rem; }
.wishlist-form .form-control { background: rgba(255,255,255,.9); border: 1px solid rgba(255,255,255,.3); border-radius: 12px; padding: .75rem 1rem; font-size: 1rem; }
.wishlist-form .form-control:focus { background: white; border-color: var(--warning, #ffc107); box-shadow: 0 0 0 .2rem rgba(255,193,7,.25); }
.wishlist-form .input-group-text { background: rgba(255,255,255,.9); border: 1px solid rgba(255,255,255,.3); border-left: none; border-radius: 0 12px 12px 0; }
.features-preview { border-top: 1px solid rgba(255,255,255,.2); padding-top: 2rem; }
.features-title { color: white; font-weight: 600; margin-bottom: 1.5rem; }
.feature-item { display: flex; align-items: center; gap: .75rem; color: rgba(255,255,255,.9); font-size: .95rem; padding: .75rem; background: rgba(255,255,255,.1); border-radius: 12px; backdrop-filter: blur(5px); border: 1px solid rgba(255,255,255,.1); transition: all .3s ease; }
.feature-item:hover { background: rgba(255,255,255,.15); transform: translateY(-2px); }
.feature-item i { font-size: 1.25rem; color: var(--warning, #ffc107); }
@media (max-width: 768px) {
    .coming-soon-card { padding: 2rem 1.5rem; margin: 1rem; }
    .coming-soon-title { font-size: 2rem; }
    .countdown-item { padding: 1rem .75rem; min-width: 80px; }
    .countdown-number { font-size: 1.5rem; }
}
"""
write(coming_soon_css_path, coming_soon_css)
print('  CSS created: coming-soon.css')

# === 10. utilities.css ===
append_css('utilities.css', """\
/* === Z-index utility === */
.z-1055 { z-index: 1055 !important; }
/* === Badge small text === */
.badge-sm-text { font-size: .7em; }
/* === Column min-widths === */
.col-min-250 { min-width: 250px; }
/* === Profile picture size === */
.profile-pic-sm { width: 80px; height: 80px; object-fit: cover; }
/* === Spinner size override === */
.spinner-lg { width: 3rem !important; height: 3rem !important; }
""")

print('\nAll CSS additions complete.')
