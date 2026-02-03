"""
Open-Monitor Inventory Controller
Rotas para gerenciamento de ativos e inventário.
"""
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models.inventory import Asset, AssetVulnerability, Vendor, Product
from app.models.nvd import Vulnerability
from app.models.system import AssetType, AssetStatus, VulnerabilityStatus
from app.utils.security import role_required, owner_or_admin_required


logger = logging.getLogger(__name__)


inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/')
@login_required
def index():
    """Lista de ativos."""
    return render_template('inventory/index.html')


@inventory_bp.route('/add')
@inventory_bp.route('/create')
@login_required
@role_required('ADMIN', 'ANALYST')
def create():
    """Página de criação de ativo."""
    return render_template('inventory/form.html')


@inventory_bp.route('/api/list')
@login_required
def list_assets():
    """API: Listar ativos com filtros e paginação."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    
    # Filtros
    asset_type = request.args.get('type')
    status = request.args.get('status')
    owner = request.args.get('owner')
    search = request.args.get('search')
    criticality = request.args.get('criticality')
    
    # Query base - filtrar por owner se não admin
    query = Asset.query
    if not current_user.is_admin:
        query = query.filter(Asset.owner_id == current_user.id)
    
    # Aplicar filtros
    if asset_type:
        try:
            query = query.filter(Asset.asset_type == AssetType(asset_type))
        except ValueError:
            pass
    
    if status:
        try:
            query = query.filter(Asset.status == AssetStatus(status))
        except ValueError:
            pass
    
    if owner and current_user.is_admin:
        query = query.filter(Asset.owner_id == int(owner))
    
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Asset.name.ilike(search_term),
                Asset.ip_address.cast(db.String).ilike(search_term),
                Asset.hostname.ilike(search_term)
            )
        )
    
    if criticality:
        query = query.filter(Asset.criticality == criticality.upper())
    
    # Ordenação por risco
    query = query.order_by(Asset.criticality.desc(), Asset.name.asc())
    
    # Paginação
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page
    })



@inventory_bp.route('/api/create', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def create_asset():
    """API: Criar novo ativo."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'asset_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Map legacy/short types to enum values
    type_mapping = {
        'NETWORK': 'NETWORK_DEVICE',
        'CLOUD': 'CLOUD_SERVICE',
        'IOT': 'IOT_DEVICE',
        'MOBILE': 'MOBILE_DEVICE'
    }
    
    raw_type = data['asset_type']
    if raw_type in type_mapping:
        raw_type = type_mapping[raw_type]
    
    # Validar tipo
    try:
        asset_type = AssetType(raw_type)
    except ValueError:
        return jsonify({'error': f'Invalid asset type: {data["asset_type"]}'}), 400
    
    # Verificar IP duplicado
    if data.get('ip_address'):
        existing = Asset.query.filter_by(
            ip_address=data['ip_address'],
            owner_id=current_user.id
        ).first()
        if existing:
            return jsonify({'error': 'IP address already registered'}), 409
    
    # Resolver vendor e product
    vendor_id = data.get('vendor_id')
    product_id = data.get('product_id')

    # Resolver vendor por nome se não veio ID
    if not vendor_id and data.get('vendor_name'):
        vendor = Vendor.get_by_name(data['vendor_name'])
        if vendor:
            vendor_id = vendor.id

    # Resolver product por nome se não veio ID
    if not product_id and data.get('product_name') and vendor_id:
        product = Product.get_by_name(data['product_name'], vendor_id=vendor_id)
        if product:
            product_id = product.id

    # Criar ativo
    asset = Asset(
        name=data['name'],
        asset_type=asset_type,
        ip_address=data.get('ip_address'),
        hostname=data.get('hostname'),
        mac_address=data.get('mac_address'),
        os_family=data.get('os_family'),
        os_name=data.get('os_name'),
        os_version=data.get('os_version'),
        location=data.get('location'),
        department=data.get('department'),
        owner_id=current_user.id,
        criticality=data.get('criticality', 'MEDIUM'),
        description=data.get('description'),
        tags=data.get('tags', []),
        # Vendor/Product/Version
        vendor_id=vendor_id,
        product_id=product_id,
        version=data.get('version'),
        # BIA fields
        rto_hours=data.get('rto_hours'),
        rpo_hours=data.get('rpo_hours'),
        operational_cost_per_hour=data.get('operational_cost_per_hour'),
        # Software
        installed_software=data.get('installed_software', [])
    )

    db.session.add(asset)
    db.session.commit()

    logger.info(f'Asset created: {asset.name} by {current_user.username}')

    return jsonify({
        'message': 'Asset created successfully',
        'asset': asset.to_dict()
    }), 201


@inventory_bp.route('/api/<int:asset_id>')
@login_required
def get_asset(asset_id):
    """API: Obter detalhes de um ativo."""
    asset = Asset.query.get_or_404(asset_id)
    
    # Verificar permissão
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    
    return jsonify(asset.to_dict())


@inventory_bp.route('/api/<int:asset_id>', methods=['PUT'])
@login_required
@role_required('ADMIN', 'ANALYST')
def update_asset(asset_id):
    """API: Atualizar ativo."""
    asset = Asset.query.get_or_404(asset_id)
    
    # Verificar permissão
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Campos atualizáveis
    updatable_fields = [
        'name', 'hostname', 'mac_address', 'os_family', 'os_name', 'os_version',
        'location', 'department', 'criticality', 'description', 'tags',
        'rto_hours', 'rpo_hours', 'operational_cost_per_hour',
        'installed_software', 'status', 'version', 'vendor_id', 'product_id'
    ]

    # Resolver vendor por nome se fornecido
    if 'vendor_name' in data and 'vendor_id' not in data:
        vendor = Vendor.get_by_name(data['vendor_name'])
        if vendor:
            data['vendor_id'] = vendor.id

    # Resolver product por nome se fornecido
    if 'product_name' in data and 'product_id' not in data:
        vid = data.get('vendor_id') or asset.vendor_id
        if vid:
            product = Product.get_by_name(data['product_name'], vendor_id=vid)
            if product:
                data['product_id'] = product.id

    for field in updatable_fields:
        if field in data:
            if field == 'status':
                try:
                    setattr(asset, field, AssetStatus(data[field]))
                except ValueError:
                    continue
            else:
                setattr(asset, field, data[field])
    
    db.session.commit()
    
    logger.info(f'Asset updated: {asset.name} by {current_user.username}')
    
    return jsonify({
        'message': 'Asset updated successfully',
        'asset': asset.to_dict()
    })


@inventory_bp.route('/api/<int:asset_id>', methods=['DELETE'])
@login_required
@role_required('ADMIN')
def delete_asset(asset_id):
    """API: Deletar ativo."""
    asset = Asset.query.get_or_404(asset_id)
    
    db.session.delete(asset)
    db.session.commit()
    
    logger.info(f'Asset deleted: {asset.name} by {current_user.username}')
    
    return jsonify({'message': 'Asset deleted successfully'})


@inventory_bp.route('/api/<int:asset_id>/vulnerabilities')
@login_required
def asset_vulnerabilities(asset_id):
    """API: Vulnerabilidades associadas a um ativo."""
    asset = Asset.query.get_or_404(asset_id)
    
    # Verificar permissão
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    
    # Buscar associações
    associations = AssetVulnerability.query.filter_by(
        asset_id=asset_id
    ).order_by(AssetVulnerability.contextual_risk_score.desc()).all()
    
    result = []
    for assoc in associations:
        vuln = Vulnerability.query.get(assoc.cve_id)
        if vuln:
            result.append({
                'vulnerability': vuln.to_dict(),
                'status': assoc.status if assoc.status else None,
                'discovered_at': assoc.discovered_at.isoformat() if assoc.discovered_at else None,
                'due_date': assoc.due_date.isoformat() if assoc.due_date else None,
                'contextual_risk_score': assoc.contextual_risk_score,
                'notes': assoc.notes
            })
    
    return jsonify({'vulnerabilities': result})


@inventory_bp.route('/api/<int:asset_id>/vulnerabilities/<cve_id>', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def associate_vulnerability(asset_id, cve_id):
    """API: Associar vulnerabilidade a um ativo."""
    asset = Asset.query.get_or_404(asset_id)
    vuln = Vulnerability.query.get_or_404(cve_id.upper())
    
    # Verificar permissão
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    
    # Verificar se já existe
    existing = AssetVulnerability.query.filter_by(
        asset_id=asset_id,
        cve_id=cve_id.upper()
    ).first()
    
    if existing:
        return jsonify({'error': 'Association already exists'}), 409
    
    # Criar associação
    data = request.get_json() or {}
    
    assoc = AssetVulnerability(
        asset_id=asset_id,
        cve_id=cve_id.upper(),
        status=VulnerabilityStatus(data.get('status', 'OPEN')).value,
        discovered_at=datetime.utcnow(),
        notes=data.get('notes')
    )
    
    # Calcular risco contextual
    assoc.calculate_contextual_risk()
    
    db.session.add(assoc)
    db.session.commit()
    
    logger.info(f'Vulnerability {cve_id} associated to asset {asset.name}')
    
    return jsonify({
        'message': 'Vulnerability associated successfully',
        'contextual_risk_score': assoc.contextual_risk_score
    }), 201


@inventory_bp.route('/api/<int:asset_id>/vulnerabilities/<cve_id>', methods=['PUT'])
@login_required
@role_required('ADMIN', 'ANALYST')
def update_vulnerability_status(asset_id, cve_id):
    """API: Atualizar status de vulnerabilidade."""
    assoc = AssetVulnerability.query.filter_by(
        asset_id=asset_id,
        cve_id=cve_id.upper()
    ).first_or_404()
    
    asset = Asset.query.get(asset_id)
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    
    data = request.get_json() or {}
    
    if 'status' in data:
        try:
            assoc.update_status(VulnerabilityStatus(data['status']).value, current_user.id)
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if 'notes' in data:
        assoc.notes = data['notes']
    
    if 'due_date' in data:
        try:
            assoc.due_date = datetime.fromisoformat(data['due_date'])
        except ValueError:
            pass
    
    db.session.commit()
    
    return jsonify({'message': 'Vulnerability status updated'})


@inventory_bp.route('/api/scan', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def scan_assets():
    """API: Escanear ativos em busca de vulnerabilidades."""
    data = request.get_json() or {}
    asset_ids = data.get('asset_ids', [])
    scan_all = data.get('scan_all', False)
    
    if not asset_ids and not scan_all:
        return jsonify({'error': 'No assets specified'}), 400
    
    # Buscar ativos
    if scan_all:
        if current_user.is_admin:
            assets = Asset.query.all()
        else:
            assets = Asset.query.filter_by(owner_id=current_user.id).all()
    else:
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
    
    matches = []
    for asset in assets:
        # Verificar permissão
        if not current_user.is_admin and asset.owner_id != current_user.id:
            continue
        
        # Buscar vulnerabilidades por software instalado e vendors
        asset_vendors = set()
        asset_products = set()
        
        for software in asset.installed_software or []:
            if isinstance(software, dict):
                asset_vendors.add(software.get('vendor', '').lower())
                asset_products.add(software.get('product', '').lower())
        
        # Buscar CVEs que afetam esses vendors/products
        for vendor in asset_vendors:
            if not vendor:
                continue
            
            vulns = Vulnerability.query.filter(
                Vulnerability.nvd_vendors_data.contains([vendor])
            ).limit(100).all()
            
            for vuln in vulns:
                matches.append({
                    'asset_id': asset.id,
                    'asset_name': asset.name,
                    'cve_id': vuln.cve_id,
                    'cvss_score': vuln.cvss_score,
                    'severity': vuln.base_severity,
                    'matched_vendor': vendor
                })
    
    return jsonify({
        'matches': matches,
        'total': len(matches)
    })


@inventory_bp.route('/api/stats')
@login_required
def stats():
    """API: Estatísticas de ativos."""
    # Query base
    query = Asset.query
    if not current_user.is_admin:
        query = query.filter(Asset.owner_id == current_user.id)
    
    # Total por tipo
    type_counts = db.session.query(
        Asset.asset_type,
        db.func.count(Asset.id)
    ).filter(Asset.owner_id == current_user.id if not current_user.is_admin else True)\
     .group_by(Asset.asset_type).all()
    
    # Total por criticidade
    criticality_counts = db.session.query(
        Asset.criticality,
        db.func.count(Asset.id)
    ).filter(Asset.owner_id == current_user.id if not current_user.is_admin else True)\
     .group_by(Asset.criticality).all()
    
    # Total com vulnerabilidades
    assets_with_vulns = db.session.query(
        db.func.count(db.distinct(AssetVulnerability.asset_id))
    ).scalar()
    
    # Vulnerabilidades abertas
    open_vulns = AssetVulnerability.query.filter(
        AssetVulnerability.status == VulnerabilityStatus.OPEN.value
    ).count()

    # Vulnerabilidades mitigadas
    mitigated_vulns = AssetVulnerability.query.filter(
        AssetVulnerability.status == VulnerabilityStatus.MITIGATED.value
    ).count()

    critical_cves = [v.cve_id for v in Vulnerability.query.filter(
        Vulnerability.base_severity == 'CRITICAL'
    ).all()]
    critical_vulns = AssetVulnerability.query.filter(
        AssetVulnerability.status == VulnerabilityStatus.OPEN.value,
        AssetVulnerability.cve_id.in_(critical_cves)
    ).count()

    return jsonify({
        'total': query.count(),
        'by_type': {str(row[0]): row[1] for row in type_counts},
        'by_criticality': {row[0]: row[1] for row in criticality_counts},
        'with_vulnerabilities': assets_with_vulns,
        'open_vulnerabilities': open_vulns,
        'mitigated_vulnerabilities': mitigated_vulns,
        'critical_vulnerabilities': critical_vulns
    })


@inventory_bp.route('/<int:asset_id>')
@login_required
def detail(asset_id):
    """Detalhes de um ativo."""
    asset = Asset.query.get_or_404(asset_id)
    
    if not current_user.is_admin and asset.owner_id != current_user.id:
        abort(403)
    from sqlalchemy import func
    from app.models.inventory.asset_vulnerability import AssetVulnerability
    from app.models.nvd.vulnerability import Vulnerability
    status_counts = AssetVulnerability.count_by_status(asset_id=asset_id)
    associations = AssetVulnerability.query.filter_by(asset_id=asset_id).all()
    cve_ids = [a.cve_id for a in associations]
    severity_counts = {}
    if cve_ids:
        vulns = Vulnerability.query.filter(Vulnerability.cve_id.in_(cve_ids)).all()
        for v in vulns:
            key = v.base_severity or 'UNKNOWN'
            severity_counts[key] = severity_counts.get(key, 0) + 1
    total_associations = len(associations)
    return render_template(
        'inventory/detail.html',
        asset=asset,
        status_counts=status_counts,
        severity_counts=severity_counts,
        total_associations=total_associations
    )
