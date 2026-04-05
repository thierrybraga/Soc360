"""
Open-Monitor Chatbot Controller
AI-powered chatbot for vulnerability analysis.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app.extensions import db

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')


@chatbot_bp.route('/')
@login_required
def index():
    """Chatbot page."""
    return render_template('chatbot/chatbot.html')


@chatbot_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """API: Send message to chatbot."""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400

    user_message = data['message'].strip()
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400

    openai_key = current_app.config.get('OPENAI_API_KEY')

    if not openai_key:
        return jsonify({
            'response': 'The AI chatbot is not configured. Please set OPENAI_API_KEY in your environment.',
            'source': 'system'
        })

    try:
        from app.services.core.openai_service import OpenAIService
        service = OpenAIService()
        response = service.chat(user_message)
        return jsonify({
            'response': response,
            'source': 'ai',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f'Chatbot error: {e}')
        return jsonify({
            'response': 'An error occurred while processing your request. Please try again.',
            'source': 'error'
        }), 500


@chatbot_bp.route('/api/history', methods=['GET'])
@login_required
def history():
    """API: Get chat history for current user."""
    try:
        from app.models.system.chat import ChatSession
        sessions = ChatSession.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatSession.created_at.desc()).limit(20).all()

        return jsonify({
            'sessions': [{
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'message_count': len(s.messages) if hasattr(s, 'messages') else 0
            } for s in sessions]
        })
    except Exception:
        return jsonify({'sessions': []})


@chatbot_bp.route('/api/clear', methods=['POST'])
@login_required
def clear():
    """API: Clear chat history."""
    try:
        from app.models.system.chat import ChatSession
        ChatSession.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        return jsonify({'message': 'Chat history cleared'})
    except Exception:
        db.session.rollback()
        return jsonify({'message': 'Chat history cleared'})
