"""
Fix all remaining HTML templates:
 - Remove style blocks (move to external CSS)
 - Add {% block extra_css %} links where needed
 - Replace static inline styles with CSS classes
"""
import os, re

BASE = os.path.join(os.path.dirname(__file__), '..')
TPL = os.path.join(BASE, 'app', 'static', 'templates')

def path(*parts): return os.path.join(TPL, *parts)
def read(p): return open(p, encoding='utf-8').read()
def write(p, c): open(p, 'w', encoding='utf-8', newline='\n').write(c)

def remove_style_block(content):
    """Remove <style ...>...</style> block(s) from content."""
    return re.sub(r'\n?[ \t]*<style[^>]*>[\s\S]*?</style>\n?', '\n', content).strip('\n')

def add_extra_css_block(content, css_link):
    """Insert {% block extra_css %} before {% block content %} if not present."""
    if '{% block extra_css %}' in content:
        # Already has extra_css block — insert link inside it
        content = re.sub(
            r'({% block extra_css %}\n?)',
            r'\1' + f'  <link rel="stylesheet" href="{css_link}">\n',
            content, count=1
        )
    else:
        # Insert new block before {% block content %}
        block = (
            f'\n{{% block extra_css %}}\n'
            f'  <link rel="stylesheet" href="{css_link}">\n'
            f'{{% endblock %}}\n'
        )
        content = content.replace('{% block content %}', block + '{% block content %}', 1)
    return content


# ============================================================
# 1. umbrella/organization_detail.html
# ============================================================
p = path('umbrella', 'organization_detail.html')
c = read(p)
# Remove style block
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>\n?', '\n', c, count=1)
# Add extra_css block
css_url = "{{ url_for('static', filename='css/umbrella.css') }}"
c = add_extra_css_block(c, css_url)
# Fix inline style: style="font-size: 0.5rem;" -> class="umb-status-dot"
c = c.replace(
    '<i class="fas fa-circle" style="font-size: 0.5rem;"></i>',
    '<i class="fas fa-circle umb-status-dot"></i>'
)
write(p, c)
print('Fixed: umbrella/organization_detail.html')


# ============================================================
# 2. admin/notifications.html
# ============================================================
p = path('admin', 'notifications.html')
c = read(p)
# Remove the <style> block from extra_css block
c = re.sub(r'[ \t]*<style[^>]*>[\s\S]*?</style>\n?', '', c, count=1)
# Add link to admin.css
css_url = "{{ url_for('static', filename='css/admin.css') }}"
# Check if admin.css link already in extra_css
if 'admin.css' not in c:
    c = re.sub(
        r'({% block extra_css %}\n?)',
        r'\1' + f'  <link rel="stylesheet" href="{css_url}">\n',
        c, count=1
    )
write(p, c)
print('Fixed: admin/notifications.html')


# ============================================================
# 3. pages/search.html
# ============================================================
p = path('pages', 'search.html')
c = read(p)
# Remove the <style> block inside extra_css
c = re.sub(r'[ \t]*<style[^>]*>[\s\S]*?</style>\n?', '', c, count=1)
# Add search.css link to extra_css (vulnerabilities.css is already there)
css_url = "{{ url_for('static', filename='css/search.css') }}"
if 'search.css' not in c:
    c = re.sub(
        r'({% block extra_css %}\n?)',
        r'\1' + f'  <link rel="stylesheet" href="{css_url}">\n',
        c, count=1
    )
write(p, c)
print('Fixed: pages/search.html')


# ============================================================
# 4. reports/risk_report.html
# ============================================================
p = path('reports', 'risk_report.html')
c = read(p)
# Remove style block from extra_css
c = re.sub(r'[ \t]*<style[^>]*>[\s\S]*?</style>\n?', '', c, count=1)
# Add reports.css link
css_url = "{{ url_for('static', filename='css/reports.css') }}"
if 'reports.css' not in c:
    c = re.sub(
        r'({% block extra_css %}\n?)',
        r'\1' + f'  <link rel="stylesheet" href="{css_url}">\n',
        c, count=1
    )
# Replace class names to match new CSS
c = c.replace('class="report-header"', 'class="risk-report-header"')
c = c.replace('class="report-content"', 'class="risk-report-content"')
c = c.replace('class="report-actions"', 'class="risk-report-actions"')
c = c.replace('class="loading-overlay"', 'class="risk-loading-overlay"')
c = c.replace('class="loading-spinner"', 'class="risk-loading-spinner"')
c = c.replace('class="spinner"', 'class="risk-spinner"')
write(p, c)
print('Fixed: reports/risk_report.html')


# ============================================================
# 5. pages/coming_soon.html  - move style+script out of content
# ============================================================
p = path('pages', 'coming_soon.html')
c = read(p)

# Extract style block content
style_match = re.search(r'<style[^>]*>([\s\S]*?)</style>', c)
# Extract script block content
script_match = re.search(r'<script[^>]*>([\s\S]*?)</script>', c)

# Remove the style block from content
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>', '', c)
# Remove the script block from content
c = re.sub(r'\n?<script[^>]*>[\s\S]*?</script>', '', c)

# Fix inline style: style="z-index: 1055;" on toast container
c = c.replace(
    'class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1055;"',
    'class="toast-container position-fixed top-0 end-0 p-3 z-1055"'
)

# Add extra_css block before block content
css_url = "{{ url_for('static', filename='css/coming-soon.css') }}"
c = add_extra_css_block(c, css_url)

# Add extra_js block at end (before final endblock)
if '{% block extra_js %}' not in c and script_match:
    script_content = script_match.group(1)
    js_block = (
        '\n{% block extra_js %}\n'
        '<script nonce="{{ csp_nonce() }}">\n'
        + script_content +
        '</script>\n'
        '{% endblock %}'
    )
    # Find last {% endblock %} and insert js_block before it
    last_endblock = c.rfind('{% endblock %}')
    if last_endblock != -1:
        c = c[:last_endblock] + js_block + '\n' + c[last_endblock:]

write(p, c)
print('Fixed: pages/coming_soon.html')


# ============================================================
# 6. newsletter/admin/send_newsletter.html
# ============================================================
p = path('newsletter', 'admin', 'send_newsletter.html')
c = read(p)

# Remove style block
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>', '', c)

# Fix inline style: style="background-color: #f8f9fa;" in preview modal
c = c.replace(
    'class="border rounded p-3" style="background-color: #f8f9fa;"',
    'class="border rounded p-3 newsletter-preview-body"'
)

# Add extra_css block with newsletter.css
css_url = "{{ url_for('static', filename='css/newsletter.css') }}"
c = add_extra_css_block(c, css_url)

# Add data-page attribute to main container if possible
c = c.replace(
    'class="container-fluid py-4">',
    'class="container-fluid py-4" data-page="newsletter-send">',
    1
)
write(p, c)
print('Fixed: newsletter/admin/send_newsletter.html')


# ============================================================
# 7. newsletter/admin/dashboard.html
# ============================================================
p = path('newsletter', 'admin', 'dashboard.html')
c = read(p)
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>', '', c)
css_url = "{{ url_for('static', filename='css/newsletter.css') }}"
c = add_extra_css_block(c, css_url)
c = c.replace(
    'class="container-fluid py-4">',
    'class="container-fluid py-4" data-page="newsletter-dashboard">',
    1
)
# Replace avatar-sm -> nl-avatar-sm if present
c = c.replace('class="avatar-sm', 'class="nl-avatar-sm')
write(p, c)
print('Fixed: newsletter/admin/dashboard.html')


# ============================================================
# 8. newsletter/admin/subscribers.html
# ============================================================
p = path('newsletter', 'admin', 'subscribers.html')
c = read(p)
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>', '', c)
css_url = "{{ url_for('static', filename='css/newsletter.css') }}"
c = add_extra_css_block(c, css_url)
c = c.replace(
    'class="container-fluid py-4">',
    'class="container-fluid py-4" data-page="newsletter-subscribers">',
    1
)
# Fix style="display: inline;" on form — this is a static layout style
c = c.replace(
    ' style="display: inline;" onsubmit=',
    ' class="d-inline" onsubmit='
)
c = c.replace('class="avatar-sm', 'class="nl-avatar-sm')
write(p, c)
print('Fixed: newsletter/admin/subscribers.html')


# ============================================================
# 9. newsletter/unsubscribe.html
# ============================================================
p = path('newsletter', 'unsubscribe.html')
c = read(p)
c = re.sub(r'\n?<style[^>]*>[\s\S]*?</style>', '', c)
css_url = "{{ url_for('static', filename='css/newsletter.css') }}"
c = add_extra_css_block(c, css_url)
# Add data-page
c = c.replace('class="container mt-5">', 'class="container mt-5" data-page="newsletter-unsubscribe">', 1)
write(p, c)
print('Fixed: newsletter/unsubscribe.html')


# ============================================================
# 10. core/dashboard.html - inline styles
# ============================================================
p = path('core', 'dashboard.html')
c = read(p)
# select min-width -> class already has dash-time-range (CSS handles it now)
c = c.replace(
    'class="form-control dash-time-range" data-time-range style="min-width:150px;"',
    'class="form-control dash-time-range" data-time-range'
)
# Icon colors
c = c.replace(
    '<i class="fas fa-radiation me-2" style="color: var(--critical)"></i>',
    '<i class="fas fa-radiation me-2 dash-icon-critical"></i>'
)
c = c.replace(
    '<i class="fas fa-exclamation-circle me-2" style="color: var(--warning)"></i>',
    '<i class="fas fa-exclamation-circle me-2 dash-icon-warning"></i>'
)
# SLA span colors
c = c.replace(
    'class="dash-sla-value" style="color: var(--danger)"',
    'class="dash-sla-value dash-sla-value--danger"'
)
c = c.replace(
    'class="dash-sla-value" style="color: var(--warning)"',
    'class="dash-sla-value dash-sla-value--warning"'
)
write(p, c)
print('Fixed: core/dashboard.html')


# ============================================================
# 11. assets/asset_list.html - inline styles
# ============================================================
p = path('assets', 'asset_list.html')
c = read(p)
c = c.replace(
    'class="form-select" style="width: auto;" id="status-filter"',
    'class="form-select w-auto" id="status-filter"'
)
c = c.replace(
    'class="form-select" style="width: auto;" id="page-size"',
    'class="form-select w-auto" id="page-size"'
)
c = c.replace(
    '<i class="bi bi-server" style="font-size: 4rem; color: #6c757d;"></i>',
    '<i class="bi bi-server ast-empty-icon"></i>'
)
write(p, c)
print('Fixed: assets/asset_list.html')


# ============================================================
# 12. monitoring/index.html + monitoring/monitoring.html
# ============================================================
for fname in ('index.html', 'monitoring.html'):
    p = path('monitoring', fname)
    c = read(p)
    c = c.replace(
        'class="input-group input-group-sm" style="width: 250px;"',
        'class="input-group input-group-sm mon-search-group"'
    )
    write(p, c)
    print(f'Fixed: monitoring/{fname}')


# ============================================================
# 13. account/account.html
# ============================================================
p = path('account', 'account.html')
c = read(p)
c = c.replace(
    'class="rounded-circle" style="width: 80px; height: 80px;"',
    'class="rounded-circle profile-pic-sm"'
)
write(p, c)
print('Fixed: account/account.html')


# ============================================================
# 14. analytics/analytics.html
# ============================================================
p = path('analytics', 'analytics.html')
c = read(p)
c = c.replace(
    '<th scope="col" style="min-width: 250px;">',
    '<th scope="col" class="col-min-250">'
)
write(p, c)
print('Fixed: analytics/analytics.html')


# ============================================================
# 15. pages/loading.html
# ============================================================
p = path('pages', 'loading.html')
c = read(p)
c = c.replace(
    'class="spinner-border text-primary mb-4" role="status" style="width: 3rem; height: 3rem;"',
    'class="spinner-border text-primary mb-4 spinner-lg" role="status"'
)
# style="width: 0%" is JS-controlled (updated by JS) — keep as-is
write(p, c)
print('Fixed: pages/loading.html')


# ============================================================
# 16. auth/init_root.html
# ============================================================
p = path('auth', 'init_root.html')
c = read(p)
c = c.replace(
    'class="badge badge-secondary ml-2" style="font-size: 0.7em;"',
    'class="badge badge-secondary ml-2 badge-sm-text"'
)
write(p, c)
print('Fixed: auth/init_root.html')


# ============================================================
# 17. assets/asset_form.html + monitoring/monitoring_rule_form.html
#     (z-index: 1055 on toast containers)
# ============================================================
for fpath in (
    path('assets', 'asset_form.html'),
    path('monitoring', 'monitoring_rule_form.html'),
):
    c = read(fpath)
    c = c.replace(
        'class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1055;"',
        'class="toast-container position-fixed top-0 end-0 p-3 z-1055"'
    )
    write(fpath, c)
    print(f'Fixed: {os.path.relpath(fpath, TPL)}')


# ============================================================
# 18. reports/detail.html - remaining mono inline styles
# ============================================================
p = path('reports', 'detail.html')
c = read(p)
c = c.replace(
    'class="text-primary fw-medium" style="font-family:ui-monospace,monospace;font-size:.85rem;"',
    'class="text-primary fw-medium cve-link-mono"'
)
c = c.replace(
    'class="bg-dark text-light p-3 rounded small" style="max-height:400px;overflow:auto;">',
    'class="bg-dark text-light p-3 rounded small rpt-raw-pre">'
)
c = c.replace(
    'class="report-meta-value" style="font-family:ui-monospace,monospace;font-size:.78rem;"',
    'class="report-meta-value meta-val-mono"'
)
write(p, c)
print('Fixed: reports/detail.html')


print('\nAll HTML fixes complete.')
