"""
Open-Monitor Auth Controller
Autenticação: login, logout, register, password reset, init-root.
"""
import secrets
import threading
from datetime import datetime, timedelta, timezone
from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, current_app, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models.auth import User, Role
from app.models.system import SyncMetadata
from app.forms.auth_forms import (
    LoginForm, RegisterForm, InitRootForm, 
    PasswordResetRequestForm, PasswordResetForm
)
from app.utils.security import rate_limit, validate_password_strength


auth_bp = Blueprint('auth', __name__)


# =============================================================================
# LOGIN / LOGOUT
# =============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window_seconds=300)
def login():
    """Página de login."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Verificar se usuário existe e senha correta
        if user is None or not user.check_password(form.password.data):
            # Incrementar contador de falhas
            if user:
                user.failed_login_count += 1
                
                # Bloquear após 5 tentativas
                if user.failed_login_count >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                    flash('Conta bloqueada por 15 minutos devido a múltiplas tentativas.', 'danger')
                else:
                    flash('Usuário ou senha inválidos.', 'danger')
                
                db.session.commit()
            else:
                flash('Usuário ou senha inválidos.', 'danger')
            
            return render_template('auth/login.html', form=form)
        
        # Verificar se conta está ativa
        if not user.is_active:
            flash('Esta conta está desativada.', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Verificar se conta está bloqueada
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
            flash(f'Conta bloqueada. Tente novamente em {remaining} minutos.', 'danger')
            return render_template('auth/login.html', form=form)
        
        # Login bem-sucedido
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
        
        login_user(user, remember=form.remember_me.data)
        
        current_app.logger.info(f'User {user.username} logged in successfully')
        
        # Redirecionar para página solicitada ou dashboard
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        return redirect(url_for('core.dashboard'))
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Fazer logout."""
    username = current_user.username
    logout_user()
    current_app.logger.info(f'User {username} logged out')
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('auth.login'))


# =============================================================================
# REGISTRO
# =============================================================================

@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(max_requests=3, window_seconds=3600)
def register():
    """Página de registro de novos usuários."""
    # Verificar se registro está habilitado
    if not current_app.config.get('REGISTRATION_ENABLED', True):
        flash('O registro de novos usuários está desabilitado.', 'warning')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        # Verificar unicidade
        if User.query.filter_by(username=form.username.data).first():
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Este e-mail já está registrado.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Validar força da senha
        is_valid, message = validate_password_strength(form.password.data)
        if not is_valid:
            flash(message, 'danger')
            return render_template('auth/register.html', form=form)
        
        # Criar usuário
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=False,
            is_active=True,
            email_confirmed=False  # Aguarda confirmação
        )
        user.set_password(form.password.data)
        
        # Associar role padrão (VIEWER)
        viewer_role = Role.query.filter_by(name='VIEWER').first()
        if viewer_role:
            user.roles.append(viewer_role)
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f'New user registered: {user.username}')
        
        # TODO: Enviar e-mail de confirmação
        
        flash('Conta criada com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


# =============================================================================
# INIT ROOT (PRIMEIRO USUÁRIO)
# =============================================================================

@auth_bp.route('/init-root', methods=['GET', 'POST'])
def init_root():
    """
    Configuração inicial - criar primeiro usuário admin.
    Só disponível se não existir nenhum usuário ativo.
    """
    # Verificar se já existe usuário
    active_users = User.query.filter_by(is_active=True).count()
    if active_users > 0:
        flash('Sistema já foi inicializado.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = InitRootForm()
    
    if form.validate_on_submit():
        # Validar força da senha
        is_valid, message = validate_password_strength(form.password.data)
        if not is_valid:
            flash(message, 'danger')
            return render_template('auth/init_root.html', form=form)
        
        # Gerar novo SECRET_KEY se não definido
        if current_app.config.get('SECRET_KEY') == 'dev-secret-key-change-me':
            new_secret = secrets.token_hex(32)
            current_app.logger.warning(
                f'Generated new SECRET_KEY. Please add to .env: SECRET_KEY={new_secret}'
            )
        
        # Salvar NVD API Key se fornecida
        if form.nvd_api_key.data:
            try:
                # Usar SyncMetadata para persistir a chave
                from app.models.system import SyncMetadata
                SyncMetadata.set_value('nvd_api_key', form.nvd_api_key.data)
                current_app.logger.info('NVD API Key saved to SyncMetadata')
            except Exception as e:
                current_app.logger.error(f'Error saving NVD API Key: {e}')
        
        # Criar roles padrão se não existirem
        _create_default_roles()
        
        # Criar usuário admin
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=True,
            is_active=True,
            email_confirmed=True
        )
        user.set_password(form.password.data)
        
        # Associar role ADMIN
        admin_role = Role.query.filter_by(name='ADMIN').first()
        if admin_role:
            user.roles.append(admin_role)
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f'Root admin user created: {user.username}')
        
        # Disparar sincronização NVD inicial APENAS se solicitado
        if form.start_sync.data:
            _trigger_initial_sync()
        else:
            current_app.logger.info('Initial NVD sync skipped by user')
            # Marcar como inicializado mas sem sync
            SyncMetadata.set_value('system_initialized', 'true')
        
        # Login automático
        login_user(user)
        
        flash('Sistema inicializado com sucesso!', 'success')
        
        # Redirecionar para página de loading se sync iniciou, ou dashboard se não
        if form.start_sync.data:
            return redirect(url_for('nvd.sync_page'))
        else:
            return redirect(url_for('core.dashboard'))
    
    # Debug: Se validação falhar, logar erros
    if form.errors:
        current_app.logger.warning(f'Init root form validation failed: {form.errors}')
    
    return render_template('auth/init_root.html', form=form)


def _create_default_roles():
    """Criar roles padrão se não existirem."""
    default_roles = [
        {
            'name': 'ADMIN',
            'description': 'Administrador com acesso total',
            'permissions': {
                'users': ['read', 'write', 'delete'],
                'assets': ['read', 'write', 'delete'],
                'vulnerabilities': ['read'],
                'reports': ['read', 'write', 'delete'],
                'monitoring': ['read', 'write', 'delete'],
                'settings': ['read', 'write']
            }
        },
        {
            'name': 'ANALYST',
            'description': 'Analista de segurança',
            'permissions': {
                'assets': ['read', 'write'],
                'vulnerabilities': ['read'],
                'reports': ['read', 'write'],
                'monitoring': ['read', 'write']
            }
        },
        {
            'name': 'VIEWER',
            'description': 'Visualizador (somente leitura)',
            'permissions': {
                'assets': ['read'],
                'vulnerabilities': ['read'],
                'reports': ['read'],
                'monitoring': ['read']
            }
        },
        {
            'name': 'API_USER',
            'description': 'Acesso via API',
            'permissions': {
                'api': ['read', 'write']
            }
        }
    ]
    
    for role_data in default_roles:
        if not Role.query.filter_by(name=role_data['name']).first():
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            db.session.add(role)
    
    db.session.commit()


def _trigger_initial_sync():
    """Disparar sincronização inicial de TODAS as fontes (NVD, EUVD, MITRE)."""
    app = current_app._get_current_object()
    
    # 1. Trigger NVD Sync (Already async internally)
    try:
        # Marcar sync como iniciando
        SyncMetadata.set_value('nvd_sync_progress_status', 'starting')
        SyncMetadata.set_value('nvd_first_sync_completed', 'false')
        
        # Importar e disparar job (Modo FULL explícito)
        from app.services.nvd.nvd_sync_service import NVDSyncService, SyncMode
        service = NVDSyncService()
        service.start_sync(mode=SyncMode.FULL, async_mode=True)
        
        app.logger.info('Initial NVD sync triggered (FULL mode)')
    except Exception as e:
        app.logger.error(f'Failed to trigger initial NVD sync: {e}')
        SyncMetadata.set_value('nvd_sync_progress_status', 'error')

    # 2. Trigger EUVD and MITRE Syncs (in a separate thread)
    def run_secondary_syncs(app_obj):
        with app_obj.app_context():
            from app.services.euvd.euvd_service import EUVDService
            from app.services.mitre.mitre_service import MitreService
            
            # EUVD
            try:
                app_obj.logger.info('Starting initial EUVD sync...')
                euvd = EUVDService()
                # Tenta sincronizar as mais recentes para popular a base inicial
                euvd.sync_latest()
                app_obj.logger.info('Initial EUVD sync completed')
            except Exception as e:
                app_obj.logger.error(f'Initial EUVD sync failed: {e}')
            
            # MITRE (Enrichment)
            try:
                app_obj.logger.info('Starting initial MITRE enrichment...')
                mitre = MitreService()
                # Limite inicial conservador para não sobrecarregar
                mitre.enrich_existing_vulnerabilities(limit=100) 
                app_obj.logger.info('Initial MITRE enrichment completed')
            except Exception as e:
                app_obj.logger.error(f'Initial MITRE enrichment failed: {e}')

    # Start secondary syncs in background thread
    try:
        secondary_thread = threading.Thread(target=run_secondary_syncs, args=(app,))
        secondary_thread.daemon = True
        secondary_thread.start()
        app.logger.info('Secondary syncs (EUVD, MITRE) scheduled in background')
    except Exception as e:
        app.logger.error(f'Failed to start secondary sync thread: {e}')


# =============================================================================
# PASSWORD RESET
# =============================================================================

@auth_bp.route('/password-reset-request', methods=['GET', 'POST'])
@rate_limit(max_requests=3, window_seconds=3600)
def password_reset_request():
    """Solicitar reset de senha."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            # Gerar token
            token = secrets.token_urlsafe(32)
            user.password_reset_token = token
            user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=24)
            db.session.commit()
            
            # TODO: Enviar e-mail com link de reset
            # send_password_reset_email(user, token)
            
            current_app.logger.info(f'Password reset requested for {user.email}')
        
        # Sempre mostrar mensagem de sucesso (segurança - não revelar se e-mail existe)
        flash(
            'Se este e-mail estiver cadastrado, você receberá instruções para redefinir sua senha.',
            'info'
        )
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset_request.html', form=form)


@auth_bp.route('/password-reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    """Redefinir senha com token."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    # Buscar usuário pelo token
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user:
        flash('Token inválido ou expirado.', 'danger')
        return redirect(url_for('auth.password_reset_request'))
    
    # Verificar expiração
    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc):
        flash('Token expirado. Solicite um novo reset.', 'danger')
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        return redirect(url_for('auth.password_reset_request'))
    
    form = PasswordResetForm()
    
    if form.validate_on_submit():
        # Validar força da senha
        is_valid, message = validate_password_strength(form.password.data)
        if not is_valid:
            flash(message, 'danger')
            return render_template('auth/password_reset.html', form=form)
        
        # Atualizar senha
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        
        current_app.logger.info(f'Password reset completed for {user.email}')
        
        flash('Senha redefinida com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset.html', form=form, token=token)


# =============================================================================
# API ENDPOINTS (para chamadas AJAX)
# =============================================================================

@auth_bp.route('/api/check-username', methods=['POST'])
def check_username():
    """Verificar disponibilidade de username (AJAX)."""
    username = request.json.get('username', '')
    
    if len(username) < 3:
        return jsonify({'available': False, 'message': 'Mínimo 3 caracteres'})
    
    exists = User.query.filter_by(username=username).first() is not None
    
    return jsonify({
        'available': not exists,
        'message': 'Disponível' if not exists else 'Username já em uso'
    })


@auth_bp.route('/api/check-email', methods=['POST'])
def check_email():
    """Verificar disponibilidade de e-mail (AJAX)."""
    email = request.json.get('email', '')
    
    exists = User.query.filter_by(email=email).first() is not None
    
    return jsonify({
        'available': not exists,
        'message': 'Disponível' if not exists else 'E-mail já registrado'
    })