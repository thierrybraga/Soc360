"""
AIService factory — retorna o provedor de IA configurado.

Configuração via variável de ambiente AI_PROVIDER:
  openai → OpenAIService (padrão — usa demo mode se OPENAI_API_KEY ausente)
  ollama → OllamaService (inferência local, requer Ollama rodando)
"""
import logging
from flask import current_app

logger = logging.getLogger(__name__)


def get_ai_service():
    """
    Retorna a instância do serviço de IA conforme AI_PROVIDER.

    Ordem de prioridade:
    1. AI_PROVIDER=ollama → OllamaService (requer Ollama rodando)
    2. AI_PROVIDER=openai (padrão) → OpenAIService
       - Com OPENAI_API_KEY: respostas reais via API
       - Sem OPENAI_API_KEY: modo demo com respostas simuladas
    """
    provider = (current_app.config.get('AI_PROVIDER') or 'openai').lower().strip()

    if provider == 'ollama':
        from app.services.core.ollama_service import OllamaService
        logger.debug('AI provider: Ollama (local)')
        return OllamaService()

    # openai ou qualquer valor desconhecido → OpenAI (com demo fallback)
    from app.services.core.openai_service import OpenAIService
    logger.debug(f'AI provider: OpenAI (provider config={provider!r})')
    return OpenAIService()
