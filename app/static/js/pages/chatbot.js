class ChatbotPage {
    constructor() {
        this.messagesEl = document.getElementById('chatMessages');
        this.formEl = document.getElementById('chatForm');
        this.inputEl = document.getElementById('chatInput');
        this.sendBtnEl = document.getElementById('sendBtn');
        this.clearBtnEl = document.getElementById('clearChatBtn');
        this.statusEl = document.getElementById('chatStatus');
        this.typingMessageEl = null;

        if (!this.messagesEl || !this.formEl || !this.inputEl || !this.sendBtnEl || !this.clearBtnEl || !this.statusEl) {
            return;
        }

        this.bindEvents();
        this.resizeInput();
        this.inputEl.focus();
    }

    bindEvents() {
        this.formEl.addEventListener('submit', (event) => {
            event.preventDefault();
            this.handleSubmit();
        });

        this.inputEl.addEventListener('input', () => this.resizeInput());
        this.inputEl.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                this.handleSubmit();
            }
        });

        this.clearBtnEl.addEventListener('click', () => this.clearConversation());

        document.querySelectorAll('[data-suggestion]').forEach((button) => {
            button.addEventListener('click', () => {
                this.inputEl.value = button.dataset.suggestion || '';
                this.resizeInput();
                this.inputEl.focus();
            });
        });
    }

    resizeInput() {
        this.inputEl.style.height = 'auto';
        this.inputEl.style.height = `${Math.min(this.inputEl.scrollHeight, 180)}px`;
    }

    async handleSubmit() {
        const message = this.inputEl.value.trim();
        if (!message || this.sendBtnEl.disabled) {
            return;
        }

        this.appendMessage({
            sender: 'user',
            author: 'Você',
            text: message,
            timestamp: new Date().toISOString()
        });

        this.inputEl.value = '';
        this.resizeInput();
        this.setSendingState(true);
        this.showTyping();

        try {
            const data = await OpenMonitor.api.post('/chatbot/api/chat', { message });
            this.hideTyping();

            this.appendMessage({
                sender: 'bot',
                author: this.resolveAuthor(data.source),
                text: data.response || 'Não foi possível gerar uma resposta agora.',
                timestamp: data.timestamp || new Date().toISOString()
            });

            this.setStatus(data.source === 'system' ? 'Modo informativo' : 'Resposta recebida', data.source === 'system' ? 'busy' : 'ready');
        } catch (error) {
            this.hideTyping();
            this.appendMessage({
                sender: 'bot',
                author: 'SecuriBot',
                text: 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente em alguns instantes.',
                timestamp: new Date().toISOString()
            });
            this.setStatus('Falha ao enviar mensagem', 'error');
            window.OpenMonitor?.showToast('Não foi possível enviar a mensagem.', 'error');
        } finally {
            this.setSendingState(false);
            this.inputEl.focus();
        }
    }

    appendMessage({ sender, author, text, timestamp }) {
        const article = document.createElement('article');
        article.className = `chat-message ${sender === 'user' ? 'chat-message--user' : 'chat-message--bot'}`;

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.setAttribute('aria-hidden', 'true');

        const avatarIcon = document.createElement('i');
        avatarIcon.className = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        avatar.appendChild(avatarIcon);

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';

        const meta = document.createElement('div');
        meta.className = 'chat-bubble__meta';

        const authorEl = document.createElement('strong');
        authorEl.textContent = author;

        const timeEl = document.createElement('span');
        timeEl.textContent = this.formatTime(timestamp);

        meta.appendChild(authorEl);
        meta.appendChild(timeEl);

        const textEl = document.createElement('div');
        textEl.className = 'chat-bubble__text';
        textEl.textContent = text;

        bubble.appendChild(meta);
        bubble.appendChild(textEl);
        article.appendChild(avatar);
        article.appendChild(bubble);

        this.messagesEl.appendChild(article);
        this.scrollMessagesToBottom();
    }

    showTyping() {
        if (this.typingMessageEl) {
            return;
        }

        const article = document.createElement('article');
        article.className = 'chat-message chat-message--bot';
        article.id = 'chatTypingMessage';

        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.setAttribute('aria-hidden', 'true');
        avatar.innerHTML = '<i class="fas fa-robot"></i>';

        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble';

        const meta = document.createElement('div');
        meta.className = 'chat-bubble__meta';
        meta.innerHTML = '<strong>SecuriBot</strong><span>Digitando...</span>';

        const typing = document.createElement('div');
        typing.className = 'chat-bubble__text';
        typing.innerHTML = '<span class="chat-typing" aria-hidden="true"><span></span><span></span><span></span></span>';

        bubble.appendChild(meta);
        bubble.appendChild(typing);
        article.appendChild(avatar);
        article.appendChild(bubble);

        this.messagesEl.appendChild(article);
        this.typingMessageEl = article;
        this.scrollMessagesToBottom();
    }

    hideTyping() {
        if (this.typingMessageEl) {
            this.typingMessageEl.remove();
            this.typingMessageEl = null;
        }
    }

    async clearConversation() {
        this.setSendingState(true);

        try {
            await OpenMonitor.api.post('/chatbot/api/clear', {});
            this.resetConversationUI();
            this.setStatus('Conversa limpa', 'ready');
            window.OpenMonitor?.showToast('Conversa limpa com sucesso.', 'success');
        } catch (error) {
            this.setStatus('Falha ao limpar conversa', 'error');
            window.OpenMonitor?.showToast('Não foi possível limpar a conversa.', 'error');
        } finally {
            this.setSendingState(false);
            this.inputEl.focus();
        }
    }

    resetConversationUI() {
        Array.from(this.messagesEl.querySelectorAll('.chat-message')).forEach((message) => {
            if (!message.dataset.staticMessage) {
                message.remove();
            }
        });
        this.hideTyping();
        this.scrollMessagesToBottom();
    }

    setSendingState(isSending) {
        this.inputEl.disabled = isSending;
        this.sendBtnEl.disabled = isSending;
        this.clearBtnEl.disabled = isSending;
        this.sendBtnEl.setAttribute('aria-busy', isSending ? 'true' : 'false');

        const idle = this.sendBtnEl.querySelector('.chat-send-btn__idle');
        const loading = this.sendBtnEl.querySelector('.chat-send-btn__loading');

        if (idle && loading) {
            idle.classList.toggle('d-none', isSending);
            loading.classList.toggle('d-none', !isSending);
        }

        this.setStatus(isSending ? 'SecuriBot está respondendo' : 'Pronto para conversar', isSending ? 'busy' : 'ready');
    }

    setStatus(text, tone = 'ready') {
        this.statusEl.classList.remove('is-busy', 'is-error');
        if (tone === 'busy') {
            this.statusEl.classList.add('is-busy');
        }
        if (tone === 'error') {
            this.statusEl.classList.add('is-error');
        }
        this.statusEl.innerHTML = '<i class="fas fa-circle"></i>';
        this.statusEl.append(document.createTextNode(` ${text}`));
    }

    resolveAuthor(source) {
        if (source === 'system') {
            return 'SecuriBot (sistema)';
        }
        if (source === 'error') {
            return 'SecuriBot (erro)';
        }
        return 'SecuriBot';
    }

    formatTime(timestamp) {
        const date = timestamp ? new Date(timestamp) : new Date();
        return new Intl.DateTimeFormat('pt-BR', {
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    }

    scrollMessagesToBottom() {
        this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatbotPage();
});
