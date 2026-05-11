"""
SOC360 Account Controller
Manage user account: profile, password change, settings.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models.auth import User
from app.utils.security import validate_password_strength

logger = logging.getLogger(__name__)

account_bp = Blueprint('account', __name__, url_prefix='/account')


@account_bp.route('/')
@login_required
def index():
    """Account profile page."""
    return render_template('account/account.html')


@account_bp.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """API: Get current user profile."""
    user = current_user
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'is_admin': user.is_admin,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
    })


@account_bp.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    """API: Update current user profile."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user = current_user

    if 'first_name' in data:
        user.first_name = data['first_name'][:50] if data['first_name'] else None
    if 'last_name' in data:
        user.last_name = data['last_name'][:50] if data['last_name'] else None
    if 'email' in data:
        new_email = data['email'].lower().strip()
        existing = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing:
            return jsonify({'error': 'Email already in use'}), 409
        user.email = new_email

    db.session.commit()
    logger.info(f'User {user.username} updated profile')

    return jsonify({'message': 'Profile updated successfully'})


@account_bp.route('/api/password', methods=['PUT'])
@login_required
def change_password():
    """API: Change current user password."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Both current and new password are required'}), 400

    user = current_user

    if not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    is_strong, msg = validate_password_strength(new_password)
    if not is_strong:
        return jsonify({'error': msg}), 400

    user.set_password(new_password)
    user.force_password_reset = False
    db.session.commit()

    logger.info(f'User {user.username} changed password')
    return jsonify({'message': 'Password changed successfully'})


@account_bp.route('/api/delete', methods=['DELETE'])
@login_required
def delete_account():
    """API: Delete current user account."""
    data = request.get_json() or {}
    password = data.get('password')

    if not password:
        return jsonify({'error': 'Password confirmation required'}), 400

    user = current_user
    if not user.check_password(password):
        return jsonify({'error': 'Password is incorrect'}), 401

    if user.is_admin:
        return jsonify({'error': 'Admin accounts cannot be self-deleted'}), 403

    username = user.username
    user.is_active = False
    db.session.commit()

    logger.info(f'User {username} deactivated their account')
    return jsonify({'message': 'Account deactivated successfully'})
