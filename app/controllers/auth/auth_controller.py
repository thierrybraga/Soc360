"""
Open-Monitor Auth Controller
Sistema de autenticação: login, logout, register, password reset, admin init.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, current_app, jsonify
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_, func

from app.extensions import db
from app.models.auth import User, Role
from app.forms.auth_forms import LoginForm, RegisterForm, PasswordResetForm, InitRootForm
from app.utils.security import validate_password_strength, admin_required


# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def send_reset_email(user, token):
    """Send password reset email asynchronously."""
    def send_async():
        try:
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            # TODO: Implement email sending
            current_app.logger.info(f"Password reset link for {user.email}: {reset_url}")
        except Exception as e:
            current_app.logger.error(f"Error sending reset email: {e}")
    
    thread = threading.Thread(target=send_async)
    thread.daemon = True
    thread.start()


# =============================================================================
# LOGIN / LOGOUT / REGISTER
# =============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter(
            or_(
                func.lower(User.username) == func.lower(form.username.data),
                func.lower(User.email) == func.lower(form.username.data)
            )
        ).first()
        
        if user and user.check_password(form.password.data):
            # Check if user is active
            if not user.is_active:
                flash('This account has been deactivated.', 'danger')
                return render_template('auth/login.html', form=form)
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
                flash(f'Account locked. Try again in {remaining} minutes.', 'danger')
                return render_template('auth/login.html', form=form)
            
            # Successful login
            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()
            
            login_user(user, remember=form.remember_me.data)
            current_app.logger.info(f'User {user.username} logged in successfully')
            
            # Check if admin needs to reset password
            if user.is_admin and user.force_password_reset:
                flash('Please reset your password for security reasons.', 'warning')
                return redirect(url_for('core.settings'))
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('core.dashboard'))
        else:
            # Failed login
            if user:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                if user.failed_login_count >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                    flash('Account locked due to multiple failed attempts. Try again in 15 minutes.', 'danger')
                    db.session.commit()
                else:
                    flash('Invalid username or password.', 'danger')
                    db.session.commit()
            else:
                flash('Invalid username or password.', 'danger')
            
            return render_template('auth/login.html', form=form)
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    username = current_user.username
    logout_user()
    current_app.logger.info(f'User {username} logged out')
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    if not current_app.config.get('REGISTRATION_ENABLED', True):
        flash('Registration is currently disabled.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        # Check if username exists
        if User.query.filter_by(username=form.username.data.lower()).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Check if email exists
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Validate password strength
        is_strong, msg = validate_password_strength(form.password.data)
        if not is_strong:
            flash(msg, 'danger')
            return render_template('auth/register.html', form=form)
        
        # Create user
        user = User(
            username=form.username.data.lower(),
            email=form.email.data.lower(),
            is_active=True,
            email_confirmed=False
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        current_app.logger.info(f'New user registered: {user.username}')
        flash('Account created successfully. You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/init-root', methods=['GET', 'POST'])
def init_root():
    """System initialization: creates first admin user."""
    # Check if there are any active users.
    active_users = User.query.filter_by(is_active=True).count()
    if active_users > 0:
        flash('System already initialized.', 'info')
        return redirect(url_for('auth.login'))
        
    form = InitRootForm()
    
    if form.validate_on_submit():
        is_strong, msg = validate_password_strength(form.password.data)
        if not is_strong:
            flash(msg, 'danger')
            return render_template('auth/init_root.html', form=form)
            
        user = User(
            username=form.username.data.lower(),
            email=form.email.data.lower(),
            is_active=True,
            is_admin=True,
            email_confirmed=True
        )
        user.set_password(form.password.data)
        
        admin_role = Role.query.filter_by(name='ADMIN').first()
        if admin_role:
            user.roles.append(admin_role)
            
        db.session.add(user)
        
        # Save NVD API KEY if requested
        if form.nvd_api_key.data:
            from app.models.system import SyncMetadata
            SyncMetadata.set_value('nvd_api_key', form.nvd_api_key.data)
            
        db.session.commit()
        
        current_app.logger.info(f'Root admin created: {user.username}')
        flash('System initialized. You can now login.', 'success')
        
        if form.start_sync.data:
            try:
                from app.jobs import trigger_nvd_sync
                trigger_nvd_sync()
                flash('Initial synchronization started in background.', 'info')
            except ImportError:
                current_app.logger.warning("trigger_nvd_sync unavailable")
            except Exception as e:
                current_app.logger.error(f"Failed to start sync: {e}")
                
        return redirect(url_for('auth.login'))
        
    return render_template('auth/init_root.html', form=form)


# =============================================================================
# PASSWORD RESET
# =============================================================================

@auth_bp.route('/reset-request', methods=['GET', 'POST'])
def password_reset_request():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').lower()
        user = User.query.filter_by(email=email).first()
        
        if user:
            token = user.get_reset_token()
            send_reset_email(user, token)
            flash('Check your email for password reset instructions.', 'info')
        else:
            # Don't reveal if email exists (security)
            flash('If email is registered, you will receive reset instructions.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset_request.html')


@auth_bp.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        is_strong, msg = validate_password_strength(form.password.data)
        if not is_strong:
            flash(msg, 'danger')
            return render_template('auth/password_reset.html', form=form)
        
        user.set_password(form.password.data)
        db.session.commit()
        
        current_app.logger.info(f'User {user.username} reset password')
        flash('Your password has been reset. You can now login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/password_reset.html', form=form)
