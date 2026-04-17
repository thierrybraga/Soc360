"""
AIService factory — retorna o provedor de IA configurado.

Configuração via variável de ambiente AI_PROVIDER:
  ollama  → OllamaService (padrão quando não há OPENAI_API_KEY)
  openai  → OpenAIService
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def get_ai_service():
    """
    Retorna a instância do serviço de IA conforme AI_PROVIDER.

    Ordem de prioridade:
    1. AI_PROVIDER=ollama  → OllamaService
    2. AI_PROVIDER=openai (ou qualquer outro) + OPENAI_API_KEY → OpenAIService
    3. Fallback → OllamaService (funciona offline, sem chave)
    """
    provider = (current_app.config.get('AI_PROVIDER') or 'ollama').lower().strip()

    if provider == 'openai':
        from app.services.core.openai_service import OpenAIService
        logger.debug('AI provider: OpenAI')
        return OpenAIService()

    # ollama ou qualquer valor desconhecido → Ollama local
    from app.services.core.ollama_service import OllamaService
    logger.debug(f'AI provider: Ollama (provider config={provider!r})')
    return OllamaService()
