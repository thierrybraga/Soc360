# app/services/core/openai_service.py

import os
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from flask import current_app

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Servico para integracao com a API da OpenAI.

    Fornece metodos para gerar respostas de chat usando modelos GPT,
    com configuracoes flexiveis e tratamento de erros.
    """

    def __init__(self):
        """
        Inicializa o servico OpenAI com configuracoes da aplicacao.
        """
        self.api_key = current_app.config.get('OPENAI_API_KEY')
        self.model = current_app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        self.max_tokens = current_app.config.get('OPENAI_MAX_TOKENS', 1000)
        self.temperature = current_app.config.get('OPENAI_TEMPERATURE', 0.7)

        if not self.api_key:
            logger.warning("OPENAI_API_KEY nao configurada - modo demo ativo")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"OpenAI Service inicializado com modelo: {self.model}")
            except Exception as e:
                logger.warning(f"Erro ao inicializar OpenAI client: {e} - modo demo ativo")
                self.client = None

    def generate_chat_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Gera uma resposta de chat usando a API da OpenAI.
        """
        if not self.client:
            logger.info("Modo demo ativo - retornando resposta simulada")
            return self._generate_demo_response(user_message, context)

        try:
            messages = self._build_messages(
                user_message,
                context,
                conversation_history
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            assistant_message = response.choices[0].message.content

            logger.info(f"Resposta gerada com sucesso. Tokens usados: {response.usage.total_tokens}")
            return assistant_message

        except Exception as e:
            logger.error(f"Erro ao gerar resposta OpenAI: {str(e)} - usando modo demo")
            return self._generate_demo_response(user_message, context)

    def _build_messages(
        self,
        user_message: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Constroi a lista de mensagens para enviar a API.
        """
        messages = []

        system_prompt = self._get_system_prompt(context)
        messages.append({
            "role": "system",
            "content": system_prompt
        })

        if conversation_history:
            recent_history = conversation_history[-10:]
            for msg in recent_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def _get_system_prompt(self, context: Optional[str] = None) -> str:
        """
        Gera o prompt do sistema para o chatbot de seguranca.
        """
        base_prompt = """
Voce e o SecuriBot, um assistente especializado em seguranca cibernetica e vulnerabilidades CVE.

Suas responsabilidades:
1. Fornecer informacoes precisas sobre vulnerabilidades CVE
2. Explicar conceitos de seguranca de forma clara
3. Sugerir medidas de mitigacao e correcao
4. Analisar riscos e impactos de vulnerabilidades
5. Responder em portugues brasileiro

Diretrizes:
- Seja preciso e tecnico, mas acessivel
- Sempre cite fontes quando possivel
- Priorize a seguranca nas recomendacoes
- Se nao souber algo, admita e sugira onde buscar informacoes
- Mantenha um tom profissional e util
"""

        if context:
            base_prompt += f"\n\nContexto adicional:\n{context}"

        return base_prompt

    def generate_cve_summary(self, cve_data: Dict[str, Any]) -> str:
        """
        Gera um resumo detalhado de uma CVE usando IA.
        """
        try:
            cve_context = self._format_cve_data(cve_data)

            prompt = f"""
Analise a seguinte vulnerabilidade CVE e forneca um resumo detalhado:

{cve_context}

Por favor, forneca:
1. Resumo da vulnerabilidade
2. Impacto potencial
3. Sistemas/produtos afetados
4. Recomendacoes de mitigacao
5. Prioridade de correcao
"""

            return self.generate_chat_response(prompt)

        except Exception as e:
            logger.error(f"Erro ao gerar resumo CVE: {str(e)}")
            return "Erro ao gerar resumo da vulnerabilidade."

    def _format_cve_data(self, cve_data: Dict[str, Any]) -> str:
        """
        Formata dados da CVE para uso em prompts.
        """
        formatted = f"""
CVE ID: {cve_data.get('cve_id', 'N/A')}
Descricao: {cve_data.get('description', 'N/A')}
Severidade: {cve_data.get('base_severity', 'N/A')}
CVSS Score: {cve_data.get('cvss_score', 'N/A')}
Data de Publicacao: {cve_data.get('published_date', 'N/A')}
Patch Disponivel: {'Sim' if cve_data.get('patch_available') else 'Nao'}
"""

        return formatted

    def _generate_demo_response(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Gera uma resposta de demonstracao quando a API da OpenAI nao esta disponivel.
        """
        user_lower = user_message.lower()

        if any(word in user_lower for word in ['cve', 'vulnerabilidade', 'vulnerability', 'seguranca', 'security']):
            if context:
                return f"Com base nos dados de vulnerabilidades disponiveis, posso ajudar com informacoes sobre seguranca. Contexto encontrado: {context[:200]}..."
            else:
                return "Sou um assistente especializado em vulnerabilidades de seguranca. Posso ajudar com informacoes sobre CVEs, analise de riscos e recomendacoes de seguranca. Como posso ajudar?"

        elif any(word in user_lower for word in ['ola', 'oi', 'hello', 'hi']):
            return "Ola! Sou o assistente de seguranca do Open Monitor. Posso ajudar com informacoes sobre vulnerabilidades, CVEs e analise de riscos. O que voce gostaria de saber?"

        elif any(word in user_lower for word in ['ajuda', 'help']):
            return "Posso ajudar com:\n- Informacoes sobre vulnerabilidades (CVEs)\n- Analise de riscos de seguranca\n- Recomendacoes de patches\n- Consultas sobre produtos e fornecedores\n\nO que voce gostaria de saber?"

        else:
            return f"Entendi sua pergunta sobre '{user_message}'. Como assistente de seguranca, posso fornecer informacoes sobre vulnerabilidades e riscos. Para uma resposta mais precisa, uma chave valida da API OpenAI seria necessaria. Como posso ajudar com questoes de seguranca?"

    def check_api_health(self) -> bool:
        """
        Verifica se a API da OpenAI esta acessivel.
        """
        if not self.client:
            logger.warning("OpenAI client nao inicializado")
            return False

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"API OpenAI nao esta acessivel: {str(e)}")
            return False
