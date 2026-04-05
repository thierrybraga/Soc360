"""
Open-Monitor Chat Models
Models para sessoes de chat do chatbot.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.extensions.db import db
from app.models.system.base_model import CoreModel
import uuid


class ChatSession(CoreModel):
    """
    Modelo para sessoes de chat do chatbot.

    Representa uma sessao de conversa com o chatbot, permitindo
    rastrear conversas individuais e manter contexto.
    """
    __tablename__ = 'chat_sessions'

    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_ip = Column(String(45))  # IPv4 ou IPv6
    user_agent = Column(Text())
    is_active = Column(Boolean, default=True, nullable=False)

    # Relacionamento com mensagens
    messages = relationship('ChatMessage', back_populates='session', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatSession {self.session_id}>'

    @property
    def message_count(self):
        """Retorna o numero de mensagens na sessao."""
        return len(self.messages)

    @property
    def last_activity(self):
        """Retorna a data da ultima atividade na sessao."""
        if self.messages:
            return max(msg.created_at for msg in self.messages)
        return self.created_at

    def to_dict(self):
        """Converte a sessao para dicionario."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'message_count': self.message_count,
            'last_activity': self.last_activity.isoformat()
        }


class ChatMessage(CoreModel):
    """
    Modelo para mensagens individuais do chat.

    Armazena cada mensagem trocada entre o usuario e o chatbot,
    incluindo metadados sobre o processamento.
    """
    __tablename__ = 'chat_messages'

    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    message_type = Column(String(20), nullable=False)  # 'user' ou 'assistant'
    content = Column(Text(), nullable=False)

    # Metadados especificos do chatbot
    processing_time = Column(Integer)  # Tempo de processamento em ms
    tokens_used = Column(Integer)  # Tokens usados na resposta (se aplicavel)
    context_used = Column(Boolean, default=False)  # Se contexto CVE foi usado
    cve_references = Column(Text())  # CVEs referenciadas (JSON string)
    error_occurred = Column(Boolean, default=False)  # Se houve erro no processamento

    # Relacionamento com sessao
    session = relationship('ChatSession', back_populates='messages')

    def __repr__(self):
        return f'<ChatMessage {self.id} ({self.message_type})>'

    def to_dict(self):
        """Converte a mensagem para dicionario."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'message_type': self.message_type,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'processing_time': self.processing_time,
            'tokens_used': self.tokens_used,
            'context_used': self.context_used,
            'cve_references': self.cve_references,
            'error_occurred': self.error_occurred
        }

    @classmethod
    def create_user_message(cls, session_id: int, content: str):
        """Cria uma mensagem do usuario."""
        return cls(
            session_id=session_id,
            message_type='user',
            content=content
        )

    @classmethod
    def create_assistant_message(
        cls,
        session_id: int,
        content: str,
        processing_time: int = None,
        tokens_used: int = None,
        context_used: bool = False,
        cve_references: str = None,
        error_occurred: bool = False
    ):
        """Cria uma mensagem do assistente."""
        return cls(
            session_id=session_id,
            message_type='assistant',
            content=content,
            processing_time=processing_time,
            tokens_used=tokens_used,
            context_used=context_used,
            cve_references=cve_references,
            error_occurred=error_occurred
        )
