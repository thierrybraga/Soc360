/**
 * Settings Page Scripts
 * Handles password visibility toggle, clipboard copying, form validation, and interactions.
 * Enhanced UX with real-time validation and visual feedback.
 */

// ============================================================================
// PASSWORD VALIDATION UTILITIES
// ============================================================================

/**
 * Valida força da senha
 * @param {string} password - Senha para validar
 * @returns {object} Objeto com informações de força
 */
function validatePasswordStrength(password) {
    const strength = {
        score: 0,
        feedback: [],
        isValid: false,
        level: 'weak'
    };

    if (!password) return strength;

    // Comprimento
    if (password.length >= 12) strength.score += 2;
    else if (password.length >= 8) strength.score += 1;
    else strength.feedback.push('Mínimo 12 caracteres recomendado');

    // Maiúsculas
    if (/[A-Z]/.test(password)) strength.score += 1;
    else strength.feedback.push('Adicione letras maiúsculas');

    // Minúsculas
    if (/[a-z]/.test(password)) strength.score += 1;
    else strength.feedback.push('Adicione letras minúsculas');

    // Números
    if (/[0-9]/.test(password)) strength.score += 1;
    else strength.feedback.push('Adicione números');

    // Símbolos
    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) strength.score += 2;
    else strength.feedback.push('Adicione símbolos especiais');

    // Nivel final
    if (strength.score >= 6) strength.level = 'strong';
    else if (strength.score >= 4) strength.level = 'medium';
    else strength.level = 'weak';

    strength.isValid = strength.score >= 5;

    return strength;
}

// ============================================================================
// TOGGLE PASSWORD VISIBILITY
// ============================================================================

/**
 * Alternancia visibilidade da senha
 * @param {string} fieldId - ID do campo de input
 */
function togglePassword(fieldId) {
    const input = document.getElementById(fieldId);
    const btn = document.querySelector(`button[data-target="${fieldId}"]`);
    const icon = btn ? btn.querySelector('i') : null;
    
    if (input) {
        const isPassword = input.type === 'password';
        
        input.type = isPassword ? 'text' : 'password';
        
        if (icon) {
            icon.classList.remove(isPassword ? 'fa-eye' : 'fa-eye-slash');
            icon.classList.add(isPassword ? 'fa-eye-slash' : 'fa-eye');
        }

        // Acessibilidade
        if (btn) {
            btn.setAttribute('aria-pressed', isPassword ? 'true' : 'false');
            btn.setAttribute('aria-label', isPassword ? 'Ocultar Senha' : 'Mostrar Senha');
        }
    }
}

// ============================================================================
// COPY TO CLIPBOARD
// ============================================================================

/**
 * Copia para área de transferência
 * @param {string} elementId - ID do elemento para copiar
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    // Seleciona o texto
    element.select();
    element.setSelectionRange(0, 99999);

    // Copia usando Clipboard API (com fallback)
    try {
        navigator.clipboard.writeText(element.value).then(() => {
            showCopyFeedback(elementId, 'success');
            if (window.OpenMonitor?.showToast) {
                window.OpenMonitor.showToast('✓ Copiado para área de transferência!', 'success');
            }
        }).catch(err => {
            console.error('Clipboard API failed:', err);
            fallbackCopy(elementId);
        });
    } catch (err) {
        console.error('Copy failed:', err);
        fallbackCopy(elementId);
    }
}

/**
 * Fallback para cópia (browsers antigos)
 * @param {string} elementId - ID do elemento
 */
function fallbackCopy(elementId) {
    const element = document.getElementById(elementId);
    document.execCommand('copy');
    showCopyFeedback(elementId, 'success');
    if (window.OpenMonitor?.showToast) {
        window.OpenMonitor.showToast('✓ Copiado para área de transferência!', 'success');
    }
}

/**
 * Mostra feedback visual de cópia
 * @param {string} elementId - ID do elemento
 * @param {string} status - Status (success, error)
 */
function showCopyFeedback(elementId, status = 'success') {
    const btn = document.querySelector(`button[data-target="${elementId}"]`);
    if (!btn) return;

    // Remove classe anterior
    btn.classList.remove('copied', 'failed');
    
    // Força reflow
    void btn.offsetWidth;
    
    // Adiciona classe apropriada
    btn.classList.add(status === 'success' ? 'copied' : 'failed');

    // Remove após animação
    setTimeout(() => {
        btn.classList.remove(status === 'success' ? 'copied' : 'failed');
    }, 1500);
}

// ============================================================================
// FORM VALIDATION & HANDLERS
// ============================================================================

/**
 * Valida correspondência de senhas
 * @param {string} fieldId1 - Primeiro campo
 * @param {string} fieldId2 - Segundo campo
 * @returns {boolean} True se correspondem
 */
function validatePasswordMatch(fieldId1, fieldId2) {
    const field1 = document.getElementById(fieldId1);
    const field2 = document.getElementById(fieldId2);
    
    if (!field1 || !field2) return true;
    
    return field1.value === field2.value;
}

/**
 * Valida email
 * @param {string} email - Email para validar
 * @returns {boolean} True se email válido
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Adiciona validações em tempo real ao formulário
 */
function setupFormValidation() {
    const passwordForm = document.getElementById('passwordForm');
    if (!passwordForm) return;

    const newPasswordField = document.querySelector('[name="new_password"]');
    const confirmPasswordField = document.querySelector('[name="confirm_new_password"]');

    // Validação de força de senha em tempo real
    if (newPasswordField) {
        newPasswordField.addEventListener('input', function() {
            const strength = validatePasswordStrength(this.value);
            
            // Atualiza border color baseado em força
            if (this.value) {
                this.classList.remove('is-invalid');
                // Aqui pode adicionar visual de força (ex: barra de progresso)
            }
        });
    }

    // Validação de correspondência de senhas
    if (confirmPasswordField) {
        confirmPasswordField.addEventListener('blur', function() {
            if (newPasswordField && this.value && newPasswordField.value !== this.value) {
                this.classList.add('is-invalid');
                let feedback = this.parentElement.querySelector('.invalid-feedback');
                if (!feedback) {
                    feedback = document.createElement('div');
                    feedback.className = 'invalid-feedback';
                    this.parentElement.appendChild(feedback);
                }
                feedback.textContent = '✗ Senhas não correspondem';
                feedback.innerHTML = '<i class="fas fa-info-circle"></i> Senhas não correspondem';
            } else {
                this.classList.remove('is-invalid');
            }
        });
    }
}

/**
 * Configurar handler para confirmação de ações perigosas
 */
function setupDangerousActionHandlers() {
    const revokeBtn = document.querySelector('button[name="api_key_revoke"]');
    if (revokeBtn) {
        revokeBtn.addEventListener('click', function(e) {
            if (!confirm('⚠️ Tem certeza? Todas as aplicações usando essa chave deixarão de funcionar.')) {
                e.preventDefault();
            }
        });
    }
}

/**
 * Adiciona feedback visual nos botões
 */
function setupButtonFeedback() {
    const buttons = document.querySelectorAll('button[data-action]');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            
            // Feedback visual
            this.style.pointerEvents = 'none';
            this.style.opacity = '0.6';
            
            // Restaura após envio do form (assumindo que página recarrega)
            setTimeout(() => {
                this.style.pointerEvents = 'auto';
                this.style.opacity = '1';
            }, 2000);
        });
    });
}

/**
 * Animações ao carregar página
 */
function setupPageAnimations() {
    const cards = document.querySelectorAll('.card');
    
    cards.forEach((card, index) => {
        card.style.animation = `slideInDown 0.3s ease-out ${index * 0.1}s backwards`;
    });
}

// ============================================================================
// INICIALIZAÇÃO
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('⚙️ Settings Page Initialized');

    // Setup Password Toggle Buttons
    document.querySelectorAll('.toggle-password-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            togglePassword(targetId);
        });
    });

    // Setup Copy Buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-target');
            copyToClipboard(targetId);
        });
    });

    // Setup Form Validations
    setupFormValidation();

    // Setup Dangerous Action Handlers
    setupDangerousActionHandlers();

    // Setup Button Feedback
    setupButtonFeedback();

    // Setup Page Animations
    setupPageAnimations();

    // Keyboard Accessibility
    document.querySelectorAll('.toggle-password-btn').forEach(btn => {
        btn.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });

    // Log para debugging
    console.log('✓ All handlers attached successfully');
});

// ============================================================================
// UTILITY: Show Toast (se OpenMonitor global não existir)
// ============================================================================

if (!window.OpenMonitor) {
    window.OpenMonitor = {
        showToast: function(message, type = 'info') {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    };
}
