"""
Open-Monitor Core Controller
Rotas principais: home, dashboard, loading.
"""
from flask import Blueprint, render_template, redirect, url_for, jsonify, flash, request
from flask_login import login_required, current_user

from app.models.auth import User
from app.models.system import SyncMetadata
from app.extensions import db
from app.forms.auth_forms import ProfileForm, ChangePasswordForm, ApiKeyForm


core_bp = Blueprint('core', __name__)


@core_bp.route('/')
def index():
    """
    Rota raiz.
    Redireciona para init-root se nenhum usuário ativo,
    caso contrário para dashboard.
    """
    # Verificar se existe algum usuário ativo
    active_users = User.query.filter_by(is_active=True).count()

    if active_users == 0:
        # Primeiro acesso - redirecionar para criar admin
        return redirect(url_for('auth.init_root'))

    # Usuário logado - dashboard
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))

    # Não logado - login
    return redirect(url_for('auth.login'))


@core_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal com visão geral."""
    from app.models.nvd import Vulnerability
    from app.models.inventory import Asset, AssetVulnerability
    from app.models import Severity

    # Estatísticas básicas
    stats = {
        'total_vulnerabilities': Vulnerability.query.count(),
        'critical_count': Vulnerability.query.filter_by(
            base_severity=Severity.CRITICAL
        ).count(),
        'high_count': Vulnerability.query.filter_by(
            base_severity=Severity.HIGH
        ).count(),
        'total_assets': Asset.query.filter_by(
            owner_id=current_user.id
        ).count(),
        'affected_assets': db.session.query(
            AssetVulnerability.asset_id
        ).distinct().count()
    }

    # Últimas vulnerabilidades
    recent_vulns = Vulnerability.query.order_by(
        Vulnerability.published_date.desc()
    ).limit(10).all()

    # Status do sync
    sync_status = SyncMetadata.get_value('nvd_sync_progress_status', 'idle')
    sync_progress = {
        'status': sync_status,
        'current': SyncMetadata.get_value('nvd_sync_progress_current', '0'),
        'total': SyncMetadata.get_value('nvd_sync_progress_total', '0'),
        'last_sync': SyncMetadata.get_value('nvd_last_sync_date')
    }

    return render_template(
        'core/dashboard.html',
        stats=stats,
        recent_vulns=recent_vulns,
        sync_progress=sync_progress
    )


@core_bp.route('/loading')
def loading():
    """
    Página de loading (Redirecionada para Sync).
    Consolidada com a página de gerenciamento de sincronização.
    """
    return redirect(url_for('nvd.sync_page'))


@core_bp.route('/health')
def health_check():
    """Health check endpoint para Docker/Kubernetes."""
    health = {
        'status': 'healthy',
        'database': 'unknown',
        'redis': 'unknown',
        'sync': 'unknown'
    }

    # Verificar banco de dados
    try:
        db.session.execute(db.text('SELECT 1'))
        health['database'] = 'connected'
    except Exception as e:
        health['database'] = f'error: {str(e)}'
        health['status'] = 'degraded'

    # Verificar Redis
    try:
        from app.services.core import RedisCacheService
        cache = RedisCacheService()
        if cache.ping():
            health['redis'] = 'connected'
        else:
            health['redis'] = 'disconnected'
            health['status'] = 'degraded'
    except Exception as e:
        health['redis'] = f'error: {str(e)}'
        health['status'] = 'degraded'

    # Status do sync
    health['sync'] = SyncMetadata.get('nvd_sync_progress_status', 'unknown')

    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code


@core_bp.route('/about')
def about():
    """Página sobre o sistema."""
    return render_template('pages/about.html')


@core_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Configurações do usuário."""
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()
    api_key_form = ApiKeyForm()

    if request.method == 'POST':
        if 'profile_submit' in request.form:
            profile_form = ProfileForm()
            if profile_form.validate_on_submit():
                # Check if username exists and is not current user
                existing_user = User.query.filter_by(username=profile_form.username.data).first()
                if existing_user and existing_user.id != current_user.id:
                    flash('Nome de usuário já está em uso.', 'danger')
                else:
                    # Check if email exists and is not current user
                    existing_email = User.query.filter_by(email=profile_form.email.data).first()
                    if existing_email and existing_email.id != current_user.id:
                        flash('E-mail já está em uso.', 'danger')
                    else:
                        current_user.username = profile_form.username.data
                        current_user.email = profile_form.email.data
                        try:
                            current_user.save()
                            flash('Perfil atualizado com sucesso!', 'success')
                            return redirect(url_for('core.settings'))
                        except Exception as e:
                            flash(f'Erro ao atualizar perfil: {str(e)}', 'danger')
            
            # Reset password form to be clean
            password_form = ChangePasswordForm(formdata=None)

        elif 'password_submit' in request.form:
            password_form = ChangePasswordForm()
            if password_form.validate_on_submit():
                if current_user.check_password(password_form.current_password.data):
                    current_user.set_password(password_form.new_password.data)
                    try:
                        current_user.save()
                        flash('Senha alterada com sucesso!', 'success')
                        return redirect(url_for('core.settings'))
                    except Exception as e:
                        flash(f'Erro ao alterar senha: {str(e)}', 'danger')
                else:
                    flash('Senha atual incorreta.', 'danger')
            
            # Reset profile form to show current user data
            profile_form = ProfileForm(formdata=None, obj=current_user)
        
        elif 'api_key_generate' in request.form:
            current_user.generate_api_key()
            flash('Nova API Key gerada com sucesso!', 'success')
            return redirect(url_for('core.settings'))
            
        elif 'api_key_revoke' in request.form:
            current_user.revoke_api_key()
            flash('API Key revogada com sucesso!', 'success')
            return redirect(url_for('core.settings'))

    return render_template(
        'pages/settings.html',
        user=current_user,
        profile_form=profile_form,
        password_form=password_form,
        api_key_form=api_key_form
    )
