"""
SOC360 Chatbot Controller
AI-powered chatbot — suporta Ollama (local) e OpenAI via AI_PROVIDER.
"""
import logging
from datetime import datetime, timezone

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chatbot')


@chatbot_bp.route('/')
@login_required
def index():
    return render_template('chatbot/chatbot.html')


@chatbot_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Envia mensagem para o provedor de IA configurado (Ollama ou OpenAI)."""
    data = request.get_json(silent=True) or {}
    user_message = (data.get('message') or '').strip()

    if not user_message:
        return jsonify({'success': False, 'error': 'Mensagem não pode estar vazia.'}), 400

    timestamp = datetime.now(timezone.utc).isoformat()
    
    logger.info(f'Chatbot: mensagem recebida de {current_user.username}: {user_message[:50]}...')

    try:
        from app.services.core.ai_service import get_ai_service
        service = get_ai_service()
        logger.info(f'Chatbot: usando serviço {service.__class__.__name__}, modelo {getattr(service, "model", "unknown")}')
        
        # Verificar se o cliente está inicializado
        if hasattr(service, 'client') and service.client is None:
            logger.error('Chatbot: cliente Ollama não inicializado')
            return jsonify({
                'success': False,
                'response': 'Serviço de IA não está disponível. Verifique se o Ollama está em execução.',
                'source': 'error',
                'timestamp': timestamp,
            }), 503
            
        response = service.generate_chat_response(user_message)
        logger.info(f'Chatbot: resposta gerada ({len(response)} chars)')
        return jsonify({
            'success': True,
            'response': response,
            'source': 'ai',
            'model': getattr(service, 'model', 'unknown'),
            'timestamp': timestamp,
        })
    except Exception as exc:
        import traceback
        logger.error(f'Chatbot error: {exc}')
        logger.error(f'Chatbot traceback: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'response': f'Erro: {str(exc)}',
            'source': 'error',
            'timestamp': timestamp,
        }), 500


@chatbot_bp.route('/api/health', methods=['GET'])
@login_required
def health():
    """Verifica o status do provedor de IA atual."""
    try:
        from app.services.core.ai_service import get_ai_service
        service = get_ai_service()
        result = service.check_health() if hasattr(service, 'check_health') else {'ok': True}
        result['provider'] = service.__class__.__name__
        result['model'] = getattr(service, 'model', None)
        return jsonify(result)
    except Exception as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 500


@chatbot_bp.route('/api/history', methods=['GET'])
@login_required
def history():
    return jsonify({'success': True, 'sessions': []})


@chatbot_bp.route('/api/clear', methods=['POST'])
@login_required
def clear():
    return jsonify({'success': True, 'message': 'Conversa limpa.'})
