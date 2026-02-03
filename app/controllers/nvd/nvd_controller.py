"""
Open-Monitor NVD Controller
Rotas para visualização e gerenciamento de vulnerabilidades.
"""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric, Weakness, Reference, Mitigation, Credit, AffectedProduct
from app.services.nvd import NVDSyncService
from app.utils.security import role_required


logger = logging.getLogger(__name__)


nvd_bp = Blueprint('nvd', __name__)


@nvd_bp.route('/')
@login_required
def index():
    """Lista de vulnerabilidades."""
    return render_template('nvd/index.html')




@nvd_bp.route('/api/list')
@login_required
def list_vulnerabilities():
    """API: Listar vulnerabilidades com filtros e paginação."""
    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)

    # Filtros
    severity = request.args.get('severity')
    vendor = request.args.get('vendor')
    product = request.args.get('product')
    search = request.args.get('search')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    cisa_kev = request.args.get('cisa_kev')

    # Aceita ambos os nomes de parâmetros de ordenação
    sort_by = request.args.get('sort_by') or request.args.get('sort', 'published_date')
    sort_order = request.args.get('sort_order') or request.args.get('order', 'desc')

    # Mapear nomes JS -> campos do model
    sort_field_map = {
        'published': 'published_date',
        'published_date': 'published_date',
        'cve_id': 'cve_id',
        'cvss_score': 'cvss_score',
        'severity': 'base_severity',
        'base_severity': 'base_severity',
        'last_modified': 'last_modified_date',
    }
    sort_field = sort_field_map.get(sort_by, 'published_date')

    # Query base
    query = Vulnerability.query

    # Aplicar filtros
    if severity:
        query = query.filter(Vulnerability.base_severity == severity.upper())

    if vendor:
        # PostgreSQL JSONB containment
        query = query.filter(
            db.cast(
                Vulnerability.nvd_vendors_data, db.Text
            ).ilike(f'%{vendor}%')
        )

    if product:
        query = query.filter(
            db.cast(
                Vulnerability.nvd_products_data, db.Text
            ).ilike(f'%{product}%')
        )

    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Vulnerability.cve_id.ilike(search_term),
                Vulnerability.description.ilike(search_term)
            )
        )

    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(Vulnerability.published_date >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(Vulnerability.published_date <= to_date)
        except ValueError:
            pass

    if cisa_kev == 'true':
        query = query.filter(Vulnerability.is_in_cisa_kev.is_(True))

    # Ordenação
    sort_column = getattr(
        Vulnerability, sort_field, Vulnerability.published_date
    )
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    # Paginação
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Estatísticas de severidade (contagem global, não filtrada)
    severity_counts = db.session.query(
        Vulnerability.base_severity,
        db.func.count(Vulnerability.cve_id)
    ).group_by(Vulnerability.base_severity).all()

    severity_map = {}
    total_cves = 0
    for sev_name, count in severity_counts:
        key = (sev_name or 'NONE').upper()
        severity_map[key] = count
        total_cves += count

    return jsonify({
        'items': [v.to_list_dict() for v in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'stats': {
            'total': total_cves,
            'critical': severity_map.get('CRITICAL', 0),
            'high': severity_map.get('HIGH', 0),
            'medium': severity_map.get('MEDIUM', 0),
            'low': severity_map.get('LOW', 0),
        }
    })


@nvd_bp.route('/<cve_id>')
@login_required
def detail(cve_id):
    """Detalhes de uma vulnerabilidade."""
    vuln = Vulnerability.query.filter_by(cve_id=cve_id.upper()).first_or_404()

    # Carregar relacionamentos explicitamente
    cvss_metrics = CvssMetric.query.filter_by(cve_id=vuln.cve_id).all()
    weaknesses = Weakness.query.filter_by(cve_id=vuln.cve_id).all()
    references = Reference.query.filter_by(cve_id=vuln.cve_id).all()

    mitigations = Mitigation.query.filter_by(cve_id=vuln.cve_id).all()
    credits = Credit.query.filter_by(cve_id=vuln.cve_id).all()
    affected_products = AffectedProduct.query.filter_by(cve_id=vuln.cve_id).all()

    # Importar models de inventory (cross-db)
    from app.models.inventory.asset_vulnerability import AssetVulnerability
    affected_assets = AssetVulnerability.query.filter_by(
        cve_id=vuln.cve_id
    ).all()

    # Separar referências por tipo
    patch_refs = [r for r in references if r.is_patch]
    exploit_refs = [r for r in references if r.is_exploit]
    advisory_refs = [r for r in references if r.is_vendor_advisory]
    other_refs = [r for r in references if not r.is_patch and not r.is_exploit and not r.is_vendor_advisory]

    return render_template(
        'nvd/detail.html',
        vulnerability=vuln,
        cvss_metrics=cvss_metrics,
        weaknesses=weaknesses,
        references=references,
        patch_refs=patch_refs,
        exploit_refs=exploit_refs,
        advisory_refs=advisory_refs,
        other_refs=other_refs,
        mitigations=mitigations,
        credits=credits,
        affected_products=affected_products,
        affected_assets=affected_assets,
    )


@nvd_bp.route('/api/<cve_id>')
@login_required
def api_detail(cve_id):
    """API: Detalhes de uma vulnerabilidade."""
    vuln = Vulnerability.query.filter_by(cve_id=cve_id.upper()).first_or_404()
    
    # Carregar relacionamentos
    cvss_metrics = CvssMetric.query.filter_by(cve_id=cve_id.upper()).all()
    weaknesses = Weakness.query.filter_by(cve_id=cve_id.upper()).all()
    references = Reference.query.filter_by(cve_id=cve_id.upper()).all()
    
    return jsonify({
        'vulnerability': vuln.to_dict(),
        'cvss_metrics': [m.to_dict() for m in cvss_metrics],
        'weaknesses': [w.to_dict() for w in weaknesses],
        'references': [r.to_dict() for r in references]
    })


@nvd_bp.route('/api/stats')
@login_required
def stats():
    """API: Estatísticas de vulnerabilidades."""
    # Total por severidade
    severity_counts = db.session.query(
        Vulnerability.base_severity,
        db.func.count(Vulnerability.cve_id)
    ).group_by(Vulnerability.base_severity).all()
    
    # CVEs nas últimas 24h, 7 dias, 30 dias
    now = datetime.utcnow()
    
    last_24h = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(hours=24)
    ).count()
    
    last_7d = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(days=7)
    ).count()
    
    last_30d = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(days=30)
    ).count()
    
    # Total CISA KEV
    cisa_kev_count = Vulnerability.query.filter(
        Vulnerability.is_in_cisa_kev.is_(True)
    ).count()

    # Top vendors
    # Usando raw SQL para JSONB array unnest (PostgreSQL)
    try:
        with db.engines['public'].connect() as conn:
            top_vendors_query = conn.execute(
                db.text("""
                    SELECT vendor, COUNT(*) as count
                    FROM vulnerabilities,
                         jsonb_array_elements_text(nvd_vendors_data) as vendor
                    GROUP BY vendor
                    ORDER BY count DESC
                    LIMIT 10
                """)
            ).fetchall()
        top_vendors = [{'vendor': row[0], 'count': row[1]} for row in top_vendors_query]
    except Exception:
        top_vendors = []

    return jsonify({
        'total': Vulnerability.query.count(),
        'by_severity': {
            (sev or 'NONE'): count for sev, count in severity_counts
        },
        'last_24h': last_24h,
        'last_7d': last_7d,
        'last_30d': last_30d,
        'cisa_kev': cisa_kev_count,
        'top_vendors': top_vendors
    })


@nvd_bp.route('/api/vendors')
@login_required
def list_vendors():
    """API: Listar vendors com contagem."""
    search = request.args.get('search', '')
    limit = min(request.args.get('limit', 50, type=int), 200)

    # Query JSONB array com contagem (PostgreSQL)
    try:
        with db.engines['public'].connect() as conn:
            result = conn.execute(
                db.text("""
                    SELECT vendor, COUNT(*) as count
                    FROM vulnerabilities,
                         jsonb_array_elements_text(nvd_vendors_data) as vendor
                    WHERE vendor ILIKE :search
                    GROUP BY vendor
                    ORDER BY count DESC
                    LIMIT :limit
                """),
                {'search': f'%{search}%', 'limit': limit}
            ).fetchall()
        vendors = [{'name': row[0], 'count': row[1]} for row in result]
    except Exception:
        vendors = []

    return jsonify({
        'vendors': vendors
    })


@nvd_bp.route('/api/products')
@login_required
def list_products():
    """API: Listar produtos (opcionalmente filtrado por vendor)."""
    vendor = request.args.get('vendor')
    search = request.args.get('search', '')
    limit = min(request.args.get('limit', 50, type=int), 200)

    try:
        with db.engines['public'].connect() as conn:
            if vendor:
                # Produtos de um vendor específico
                result = conn.execute(
                    db.text("""
                        SELECT product, COUNT(*) as count
                        FROM vulnerabilities v,
                             jsonb_array_elements_text(v.nvd_vendors_data) as vendor,
                             jsonb_array_elements_text(v.nvd_products_data) as product
                        WHERE vendor = :vendor
                        AND product ILIKE :search
                        GROUP BY product
                        ORDER BY count DESC
                        LIMIT :limit
                    """),
                    {'vendor': vendor, 'search': f'%{search}%', 'limit': limit}
                ).fetchall()
            else:
                # Todos os produtos
                result = conn.execute(
                    db.text("""
                        SELECT product, COUNT(*) as count
                        FROM vulnerabilities,
                             jsonb_array_elements_text(nvd_products_data) as product
                        WHERE product ILIKE :search
                        GROUP BY product
                        ORDER BY count DESC
                        LIMIT :limit
                    """),
                    {'search': f'%{search}%', 'limit': limit}
                ).fetchall()
        products = [{'name': row[0], 'count': row[1]} for row in result]
    except Exception:
        products = []

    return jsonify({
        'products': products
    })


@nvd_bp.route('/sync')
@login_required
@role_required('ADMIN', 'ANALYST')
def sync_page():
    """Página de gerenciamento de sincronização."""
    from app.models.system import SyncMetadata
    import os
    
    api_key = SyncMetadata.get_value('nvd_api_key') or os.environ.get('NVD_API_KEY')
    api_key_configured = bool(api_key)
    
    return render_template(
        'nvd/sync.html',
        api_key_configured=api_key_configured
    )


@nvd_bp.route('/api/sync/status')
@login_required
def sync_status():
    """API: Status da sincronização."""
    service = NVDSyncService()
    return jsonify(service.get_progress())


@nvd_bp.route('/api/sync/start', methods=['POST'])
@login_required
@role_required('ADMIN')
def start_sync():
    """API: Iniciar sincronização."""
    from app.services.nvd.nvd_sync_service import SyncMode
    
    data = request.get_json() or {}
    mode = data.get('mode', 'incremental')
    
    try:
        sync_mode = SyncMode(mode)
    except ValueError:
        return jsonify({'error': f'Invalid mode: {mode}'}), 400
    
    service = NVDSyncService()

    if service.start_sync(mode=sync_mode):
        logger.info(
            f'NVD sync started by {current_user.username}: mode={mode}'
        )
        return jsonify({
            'message': f'Sync started in {mode} mode',
            'status': 'running'
        })
    else:
        return jsonify({'error': 'Sync already running'}), 409


@nvd_bp.route('/api/sync/cancel', methods=['POST'])
@login_required
@role_required('ADMIN')
def cancel_sync():
    """API: Cancelar sincronização."""
    service = NVDSyncService()

    if service.cancel_sync():
        logger.info(f'NVD sync cancelled by {current_user.username}')
        return jsonify({'message': 'Sync cancellation requested'})
    else:
        return jsonify({'error': 'No sync running'}), 400


@nvd_bp.route('/api/search')
@login_required
def search_cves():
    """API: Busca avançada de CVEs."""
    query_text = request.args.get('q', '')

    if not query_text or len(query_text) < 3:
        return jsonify(
            {'error': 'Query must be at least 3 characters'}
        ), 400

    # Busca em CVE ID e descrição
    results = Vulnerability.query.filter(
        db.or_(
            Vulnerability.cve_id.ilike(f'%{query_text}%'),
            Vulnerability.description.ilike(f'%{query_text}%')
        )
    ).order_by(Vulnerability.cvss_score.desc()).limit(20).all()

    return jsonify({
        'results': [
            {
                'cve_id': v.cve_id,
                'description': (
                    v.description[:200] + '...'
                    if len(v.description) > 200 else v.description
                ),
                'cvss_score': v.cvss_score,
                'severity': v.base_severity
            }
            for v in results
        ]
    })


@nvd_bp.route('/api/timeline')
@login_required
def timeline():
    """API: Timeline de CVEs por data."""
    days = request.args.get('days', 30, type=int)
    severity = request.args.get('severity')
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.session.query(
        db.func.date(Vulnerability.published_date).label('date'),
        db.func.count(Vulnerability.cve_id).label('count')
    ).filter(
        Vulnerability.published_date >= start_date
    )
    
    if severity:
        query = query.filter(Vulnerability.base_severity == severity.upper())
    
    results = query.group_by(
        db.func.date(Vulnerability.published_date)
    ).order_by('date').all()
    
    return jsonify({
        'timeline': [
            {'date': str(row.date), 'count': row.count}
            for row in results
        ]
    })


@nvd_bp.route('/api/import/bulk', methods=['POST'])
@login_required
@role_required('ADMIN')
def bulk_import():
    """API: Importar CVEs em massa (JSON)."""
    from app.tasks.nvd import bulk_import_task
    
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({'error': 'File path required'}), 400
        
    task = bulk_import_task.delay(file_path)
    
    return jsonify({
        'message': 'Bulk import started',
        'task_id': task.id
    }), 202