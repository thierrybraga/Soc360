/**
 * Settings Page Scripts
 * Handles password visibility toggle, clipboard copying, and form interactions.
 */

// Toggle Password Visibility
function togglePassword(fieldId) {
    const input = document.getElementById(fieldId);
    // Find button with data-target matching fieldId
    const btn = document.querySelector(`button[data-target="${fieldId}"]`);
    const icon = btn ? btn.querySelector('i') : null;
    
    if (input) {
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
    }
}

// Copy to Clipboard
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    // Select text
    element.select();
    element.setSelectionRange(0, 99999); // For mobile devices

    // Copy
    try {
        navigator.clipboard.writeText(element.value).then(() => {
            window.OpenMonitor?.showToast('Copied to clipboard!', 'success');
        }).catch(err => {
            console.error('Failed to copy: ', err);
            // Fallback
            document.execCommand('copy');
            window.OpenMonitor?.showToast('Copied to clipboard!', 'success');
        });
    } catch (err) {
        console.error('Failed to copy: ', err);
        window.OpenMonitor?.showToast('Failed to copy', 'error');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // API Key Revoke Confirmation
    const revokeBtn = document.querySelector('button[name="api_key_revoke"]');
    if (revokeBtn) {
        revokeBtn.addEventListener('click', function(e) {
            if (!confirm('Are you sure? This will break any applications using this key.')) {
                e.preventDefault();
            }
        });
    }

    // Password Toggles (replacing inline onclicks if we remove them)
    // We can attach listeners to all toggle buttons
    document.querySelectorAll('.toggle-password-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            togglePassword(targetId);
        });
    });

    // Copy Buttons
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            copyToClipboard(targetId);
        });
    });
});
