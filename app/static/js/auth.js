/**
 * Authentication Pages JavaScript
 * Handles password visibility toggling, strength metering, and validation
 */

'use strict';

document.addEventListener('DOMContentLoaded', function() {
    // =========================================================================
    // Password Visibility Toggle
    // =========================================================================
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const container = this.closest('.password-input');
            if (!container) return;
            
            const input = container.querySelector('input');
            if (!input) return;
            
            const icon = this.querySelector('i');
            
            if (input.type === 'password') {
                input.type = 'text';
                if (icon) {
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                }
            } else {
                input.type = 'password';
                if (icon) {
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            }
        });
    });

    // =========================================================================
    // Password Strength Indicator
    // =========================================================================
    const passwordInput = document.getElementById('password');
    const strengthDiv = document.getElementById('passwordStrength');
    
    if (passwordInput && strengthDiv) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            
            let strength = 0;
            let feedback = [];
            
            if (password.length >= 12) strength++;
            else feedback.push('Mínimo 12 caracteres');
            
            if (/[A-Z]/.test(password)) strength++;
            else feedback.push('Uma letra maiúscula');
            
            if (/[a-z]/.test(password)) strength++;
            else feedback.push('Uma letra minúscula');
            
            if (/[0-9]/.test(password)) strength++;
            else feedback.push('Um número');
            
            if (/[^A-Za-z0-9]/.test(password)) strength++;
            else feedback.push('Um caractere especial');
            
            let strengthText = '';
            let strengthClass = '';
            
            if (password.length === 0) {
                strengthDiv.innerHTML = '';
                return;
            }

            if (strength < 2) {
                strengthText = 'Fraca';
                strengthClass = 'weak';
            } else if (strength < 4) {
                strengthText = 'Média';
                strengthClass = 'medium';
            } else {
                strengthText = 'Forte';
                strengthClass = 'strong';
            }
            
            strengthDiv.innerHTML = `
                <div class="strength-bar ${strengthClass}">
                    <div class="strength-fill" style="width: ${strength * 20}%"></div>
                </div>
                <div class="strength-info">
                    <span class="strength-text ${strengthClass}">${strengthText}</span>
                    ${feedback.length > 0 && strength < 5 ? `<span class="strength-feedback">Falta: ${feedback.join(', ')}</span>` : ''}
                </div>
            `;
        });
    }

    // =========================================================================
    // Password Match Validation
    // =========================================================================
    const formsWithPasswordConfirm = document.querySelectorAll('form');
    
    formsWithPasswordConfirm.forEach(form => {
        form.addEventListener('submit', function(e) {
            const password = form.querySelector('input[name="password"]');
            const confirm = form.querySelector('input[name="password_confirm"]') || form.querySelector('input[name="confirm_password"]');
            
            if (password && confirm && password.value !== confirm.value) {
                e.preventDefault();
                
                // Create or update error message
                let errorDiv = form.querySelector('.password-match-error');
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger mt-2 password-match-error';
                    errorDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> As senhas não coincidem!';
                    confirm.parentElement.insertAdjacentElement('afterend', errorDiv);
                }
                
                // Highlight error
                confirm.classList.add('error');
                confirm.focus();
                return false;
            }
        });
        
        // Submit buttons use native browser behavior
        
        // Use comportamento nativo para Enter
        
        // Enter key submits the form (single listener)
    });
});
