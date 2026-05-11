/**
 * SecuriBot — Chatbot page controller
 * Self-contained: handles UI state, markdown rendering, copy, scroll FAB.
 */

/* ── Minimal markdown renderer ───────────────────────────────────────────── */

const Markdown = (() => {
    function escHtml(s) {
        return s
            .replace(/&/g, '&')
            .replace(/</g, '<')
            .replace(/>/g, '>')
            .replace(/"/g, '"');
    }

    function inlineFmt(s) {
        s = escHtml(s);
        // Inline code
        s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold
        s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
        s = s.replace(/__([^_\n]+)__/g, '<strong>$1</strong>');
        // Italic
        s = s.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
        // CVE auto-links (safe relative URL)
        s = s.replace(
            /\b(CVE-\d{4}-\d{4,})\b/g,
            '<a href="/vulnerabilities/$1" class="md-cve" target="_blank" rel="noopener noreferrer">' +
            '$1<i class="fas fa-external-link-alt"></i></a>'
        );
        return s;
    }

    function render(raw) {
        if (!raw) return '';

        // Extract fenced code blocks to protect from inline processing
        const codeBlocks = [];
        let text = raw.replace(/```(\w*)\r?\n?([\s\S]*?)```/g, (_, lang, code) => {
            const idx = codeBlocks.length;
            const cls = lang ? ` class="lang-${escHtml(lang)}"` : '';
            codeBlocks.push(
                `<pre class="md-pre"><code${cls}>${escHtml(code.trim())}</code></pre>`
            );
            return `\x00BLK${idx}\x00`;
        });

        const lines = text.split(/\r?\n/);
        const out = [];
        let inUl = false, inOl = false;

        const closeList = () => {
            if (inUl) { out.push('</ul>'); inUl = false; }
            if (inOl) { out.push('</ol>'); inOl = false; }
        };

        for (let i = 0; i < lines.length; i++) {
            const raw_line = lines[i];
            const t = raw_line.trim();

            // Code block placeholder
            if (/^\x00BLK\d+\x00$/.test(t)) {
                closeList();
                out.push(t);
                continue;
            }

            // Blank line — close lists, skip
            if (!t) {
                closeList();
                continue;
            }

            // Headings
            let m;
            if ((m = t.match(/^###\s+(.*)/))) { closeList(); out.push(`<h4>${inlineFmt(m[1])}</h4>`); continue; }
            if ((m = t.match(/^##\s+(.*)/)))  { closeList(); out.push(`<h3>${inlineFmt(m[1])}</h3>`); continue; }
            if ((m = t.match(/^#\s+(.*)/)))   { closeList(); out.push(`<h2>${inlineFmt(m[1])}</h2>`); continue; }

            // HR
            if (/^---+$/.test(t)) { closeList(); out.push('<hr>'); continue; }

            // Unordered list
            if ((m = t.match(/^[-*+]\s+(.*)/))) {
                if (inOl) { out.push('</ol>'); inOl = false; }
                if (!inUl) { out.push('<ul>'); inUl = true; }
                out.push(`<li>${inlineFmt(m[1])}</li>`);
                continue;
            }

            // Ordered list
            if ((m = t.match(/^\d+\.\s+(.*)/))) {
                if (inUl) { out.push('</ul>'); inUl = false; }
                if (!inOl) { out.push('<ol>'); inOl = true; }
                out.push(`<li>${inlineFmt(m[1])}</li>`);
                continue;
            }

            // Regular paragraph
            closeList();
            out.push(`<p>${inlineFmt(t)}</p>`);
        }

        closeList();

        let html = out.join('');
        codeBlocks.forEach((blk, idx) => {
            html = html.replace(`\x00BLK${idx}\x00`, blk);
        });
        return html;
    }

    // Plain-text extractor for clipboard copy
    function toPlainText(raw) {
        return raw
            .replace(/```[\s\S]*?```/g, m => m.replace(/```\w*\n?/, '').replace(/```$/, '').trim())
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/^#{1,6}\s+/gm, '')
            .replace(/^[-*+]\s+/gm, '• ')
            .replace(/^\d+\.\s+/gm, '')
            .trim();
    }

    return { render, toPlainText };
})();

/* ── API helper (fallback if OpenMonitor.api not available) ──────────────── */

const API = {
    async post(url, data) {
        // Try OpenMonitor.api first
        if (window.OpenMonitor?.api?.post) {
            return await window.OpenMonitor.api.post(url, data);
        }
        // Fallback to fetch
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify(data),
        });
        if (!resp.ok) {
            const err = new Error(`HTTP ${resp.status}`);
            err.response = await resp.json().catch(() => ({}));
            throw err;
        }
        return await resp.json();
    }
};

/* ── ChatbotPage ─────────────────────────────────────────────────────────── */

class ChatbotPage {
    static MAX_CHARS = 4000;

    constructor() {
        this.els = {
            messages:    document.getElementById('chatMessages'),
            form:        document.getElementById('chatForm'),
            input:       document.getElementById('chatInput'),
            sendBtn:     document.getElementById('sendBtn'),
            clearBtn:    document.getElementById('clearChatBtn'),
            status:      document.getElementById('chatStatus'),
            statusLabel: document.querySelector('#chatStatus .chat-status__label'),
            suggestions: document.getElementById('chatSuggestions'),
            scrollFab:   document.getElementById('scrollFab'),
            charCount:   document.getElementById('charCount'),
        };

        if (!this.els.messages || !this.els.form || !this.els.input) return;

        this._typing = null;
        this._busy   = false;
        this._msgRaw = new WeakMap(); // bubble el → raw text for copy

        this._init();
    }

    _init() {
        const { form, input, clearBtn, suggestions, messages, scrollFab } = this.els;

        // Form submit
        form.addEventListener('submit', e => { e.preventDefault(); this._send(); });

        // Enter to send, Shift+Enter for newline
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._send();
            }
        });

        // Auto-resize + char count + send btn state
        input.addEventListener('input', () => {
            this._resizeInput();
            this._updateCharCount();
            this._updateSendBtn();
        });

        // Clear conversation
        clearBtn.addEventListener('click', () => this._clear());

        // Suggestion chips
        suggestions.querySelectorAll('[data-suggestion]').forEach(btn => {
            btn.addEventListener('click', () => {
                input.value = btn.dataset.suggestion || '';
                this._resizeInput();
                this._updateCharCount();
                this._updateSendBtn();
                input.focus();
            });
        });

        // Scroll FAB
        messages.addEventListener('scroll', () => this._onScroll(), { passive: true });
        scrollFab.addEventListener('click', () => this._scrollToBottom(true));

        // Initial state
        this._resizeInput();
        this._updateSendBtn();
        input.focus();
    }

    /* ── Input helpers ──────────────────────────────────────────────────── */

    _resizeInput() {
        const el = this.els.input;
        el.style.height = 'auto';
        el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
    }

    _updateCharCount() {
        const { input, charCount } = this.els;
        if (!charCount) return;
        const len = input.value.length;
        const max = ChatbotPage.MAX_CHARS;
        charCount.textContent = `${len.toLocaleString('pt-BR')} / ${max.toLocaleString('pt-BR')}`;
        charCount.classList.toggle('is-near-limit', len >= max * 0.85 && len < max);
        charCount.classList.toggle('is-at-limit', len >= max);
    }

    _updateSendBtn() {
        const { input, sendBtn } = this.els;
        sendBtn.disabled = this._busy || !input.value.trim();
    }

    /* ── Send message ───────────────────────────────────────────────────── */

    async _send() {
        const { input } = this.els;
        const text = input.value.trim();
        if (!text || this._busy) return;

        // Hide suggestions permanently after first message
        this.els.suggestions.classList.add('is-hidden');

        this._appendUserMsg(text);

        input.value = '';
        this._resizeInput();
        this._updateCharCount();
        this._setBusy(true);
        this._showTyping();

        try {
            const data = await API.post('/chatbot/api/chat', { message: text });
            this._hideTyping();
            this._appendBotMsg(data.response || 'Não foi possível gerar uma resposta.', data.source);
            this._setStatus('Pronto', 'ready');
        } catch (err) {
            console.error('Chat error:', err);
            this._hideTyping();
            const errorMsg = err?.response?.response || err?.message || 'Erro de conexão';
            this._appendBotMsg(`Erro: ${errorMsg}`, 'error');
            this._setStatus('Erro de conexão', 'error');
            window.OpenMonitor?.showToast(`Erro: ${errorMsg}`, 'error');
        } finally {
            this._setBusy(false);
            this.els.input.focus();
        }
    }

    /* ── Message rendering ──────────────────────────────────────────────── */

    _appendUserMsg(text) {
        const article = this._createMsgShell('user', 'Você');
        const body = article.querySelector('.chat-msg__body');
        body.textContent = text; // user input: plain text, no markdown
        this._addCopyBtn(article, text);
        this.els.messages.appendChild(article);
        this._scrollToBottom();
    }

    _appendBotMsg(raw, source) {
        const isError = source === 'error';
        const article = this._createMsgShell('bot', 'SecuriBot', isError);
        const body = article.querySelector('.chat-msg__body');
        body.innerHTML = Markdown.render(raw);
        this._addCopyBtn(article, raw);
        this.els.messages.appendChild(article);
        this._scrollToBottom();
    }

    _createMsgShell(sender, authorLabel, isError = false) {
        const time = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(new Date());
        const isBot = sender === 'bot';

        const article = document.createElement('article');
        article.className = [
            'chat-msg',
            `chat-msg--${sender}`,
            isError ? 'chat-msg--error' : ''
        ].filter(Boolean).join(' ');

        article.innerHTML = `
            <div class="chat-msg__avatar">
                <i class="fas fa-${isBot ? 'robot' : 'user'}"></i>
            </div>
            <div class="chat-msg__bubble">
                <header class="chat-msg__meta">
                    <strong class="chat-msg__author">${authorLabel}</strong>
                    <time class="chat-msg__time" datetime="${new Date().toISOString()}">${time}</time>
                </header>
                <div class="chat-msg__body"></div>
            </div>
        `;

        return article;
    }

    _addCopyBtn(article, rawText) {
        const bubble = article.querySelector('.chat-msg__bubble');
        const btn = document.createElement('button');
        btn.className = 'chat-msg__copy';
        btn.type = 'button';
        btn.setAttribute('aria-label', 'Copiar mensagem');
        btn.innerHTML = '<i class="fas fa-copy"></i>';

        btn.addEventListener('click', async () => {
            const plain = Markdown.toPlainText(rawText);
            try {
                await navigator.clipboard.writeText(plain);
                btn.innerHTML = '<i class="fas fa-check"></i>';
                btn.classList.add('copied');
                setTimeout(() => {
                    btn.innerHTML = '<i class="fas fa-copy"></i>';
                    btn.classList.remove('copied');
                }, 2000);
            } catch {
                // fallback: select text
                const range = document.createRange();
                range.selectNodeContents(article.querySelector('.chat-msg__body'));
                window.getSelection()?.removeAllRanges();
                window.getSelection()?.addRange(range);
            }
        });

        bubble.appendChild(btn);
    }

    /* ── Typing indicator ───────────────────────────────────────────────── */

    _showTyping() {
        if (this._typing) return;

        const article = document.createElement('article');
        article.className = 'chat-msg chat-msg--bot';
        article.id = 'chatTyping';
        article.innerHTML = `
            <div class="chat-msg__avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="chat-msg__bubble">
                <header class="chat-msg__meta">
                    <strong class="chat-msg__author">SecuriBot</strong>
                    <span class="chat-msg__time">Digitando...</span>
                </header>
                <div class="chat-msg__body">
                    <span class="chat-typing" aria-label="SecuriBot está digitando">
                        <span class="chat-typing__dot"></span>
                        <span class="chat-typing__dot"></span>
                        <span class="chat-typing__dot"></span>
                    </span>
                </div>
            </div>
        `;

        this.els.messages.appendChild(article);
        this._typing = article;
        this._scrollToBottom();
    }

    _hideTyping() {
        this._typing?.remove();
        this._typing = null;
    }

    /* ── Status ─────────────────────────────────────────────────────────── */

    _setStatus(label, tone = 'ready') {
        const { status, statusLabel } = this.els;
        status.classList.remove('is-busy', 'is-error');
        if (tone === 'busy')  status.classList.add('is-busy');
        if (tone === 'error') status.classList.add('is-error');
        if (statusLabel) statusLabel.textContent = label;
    }

    _setBusy(busy) {
        const { sendBtn, input, clearBtn } = this.els;
        this._busy = busy;

        input.disabled = busy;
        clearBtn.disabled = busy;
        sendBtn.disabled = busy;
        sendBtn.classList.toggle('is-loading', busy);
        sendBtn.setAttribute('aria-busy', busy ? 'true' : 'false');

        const spinner = sendBtn.querySelector('.chat-send-btn__spinner');
        if (spinner) spinner.classList.toggle('d-none', !busy);

        this._setStatus(
            busy ? 'SecuriBot está respondendo' : 'Pronto',
            busy ? 'busy' : 'ready'
        );
    }

    /* ── Scroll FAB ─────────────────────────────────────────────────────── */

    _scrollToBottom(smooth = false) {
        const el = this.els.messages;
        el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'instant' });
    }

    _onScroll() {
        const el = this.els.messages;
        const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
        this.els.scrollFab.hidden = distFromBottom < 80;
    }

    /* ── Clear ──────────────────────────────────────────────────────────── */

    async _clear() {
        this._setBusy(true);
        try {
            await API.post('/chatbot/api/clear');
            this.els.messages.innerHTML = '';
            // Re-add welcome message
            const welcome = document.createElement('article');
            welcome.className = 'chat-msg chat-msg--bot';
            welcome.setAttribute('data-static', 'welcome');
            welcome.innerHTML = `
                <div class="chat-msg__avatar"><i class="fas fa-robot"></i></div>
                <div class="chat-msg__bubble">
                    <header class="chat-msg__meta"><strong class="chat-msg__author">SecuriBot</strong></header>
                    <div class="chat-msg__body">
                        <p>Conversa limpa. Como posso ajudar?</p>
                    </div>
                </div>
            `;
            this.els.messages.appendChild(welcome);
            this.els.suggestions.classList.remove('is-hidden');
            window.OpenMonitor?.showToast('Conversa limpa.', 'success');
        } catch (err) {
            console.error('Clear error:', err);
            window.OpenMonitor?.showToast('Erro ao limpar conversa.', 'error');
        } finally {
            this._setBusy(false);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => { new ChatbotPage(); });