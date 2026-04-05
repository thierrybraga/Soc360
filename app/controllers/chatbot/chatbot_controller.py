"""
Open-Monitor Chatbot Controller
AI-powered chatbot for vulnerability analysis.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required

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
    data = request.get_json(silent=True) or {}
    if 'message' not in data:
        return jsonify({
            'success': False,
            'error': 'Message is required'
        }), 400

    user_message = data['message'].strip()
    if not user_message:
        return jsonify({
            'success': False,
            'error': 'Message cannot be empty'
        }), 400

    openai_key = current_app.config.get('OPENAI_API_KEY')
    timestamp = datetime.now(timezone.utc).isoformat()

    if not openai_key:
        return jsonify({
            'success': True,
            'response': 'The AI chatbot is not configured. Please set OPENAI_API_KEY in your environment.',
            'source': 'system',
            'timestamp': timestamp
        })

    try:
        from app.services.core.openai_service import OpenAIService
        service = OpenAIService()
        response = service.generate_chat_response(user_message)
        return jsonify({
            'success': True,
            'response': response,
            'source': 'ai',
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error(f'Chatbot error: {e}')
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request. Please try again.',
            'response': 'An error occurred while processing your request. Please try again.',
            'source': 'error',
            'timestamp': timestamp
        }), 500


@chatbot_bp.route('/api/history', methods=['GET'])
@login_required
def history():
    """API: Get chat history for current user."""
    return jsonify({
        'success': True,
        'sessions': []
    })


@chatbot_bp.route('/api/clear', methods=['POST'])
@login_required
def clear():
    """API: Clear chat history."""
    return jsonify({
        'success': True,
        'message': 'Chat history cleared'
    })
