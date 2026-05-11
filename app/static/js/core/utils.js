/**
 * SOC360 v3.0 - Utilities
 * Helper functions used across the application
 * All utility functions are now consolidated in OpenMonitor.utils
 */

'use strict';

/**
 * Toggle password visibility
 * @param {string} inputId - The ID of the password input field
 */
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;

    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);

    // Toggle icon - find the button next to the input
    const btn = input.nextElementSibling;
    if (btn) {
        const icon = btn.querySelector('i');
        if (icon) {
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');
        }
    }
}

/**
 * Copy text to clipboard (legacy wrapper)
 * Uses OpenMonitor.utils.copyToClipboard internally
 * @param {string} elementId - The ID of the element to copy from
 */
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const text = element.value || element.textContent;

    if (window.OpenMonitor?.utils?.copyToClipboard) {
        window.OpenMonitor.utils.copyToClipboard(text).then(success => {
            if (success) showCopyFeedback(element);
        });
    } else {
        // Fallback for when OpenMonitor is not loaded yet
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(() => {
                showCopyFeedback(element);
            });
        } else {
            // Legacy fallback
            element.select?.();
            element.setSelectionRange?.(0, 99999);
            document.execCommand('copy');
            showCopyFeedback(element);
        }
    }
}

/**
 * Show visual feedback after copy
 * @param {HTMLElement} element - The element that was copied from
 */
function showCopyFeedback(element) {
    const btn = element.nextElementSibling;
    if (btn) {
        const icon = btn.querySelector('i');
        if (icon) {
            const originalClass = icon.className;
            icon.className = 'fas fa-check text-success';
            setTimeout(() => {
                icon.className = originalClass;
            }, 2000);
        }
    }

    // Also show toast if available
    if (window.OpenMonitor?.ui?.toast) {
        window.OpenMonitor.ui.toast('Copied to clipboard!', 'success', 2000);
    }
}

/**
 * Show a toast notification (legacy wrapper)
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, error, warning, info)
 */
function showToast(message, type = 'info') {
    if (window.OpenMonitor?.ui?.toast) {
        window.OpenMonitor.ui.toast(message, type);
    } else {
        // Fallback - use alert for critical messages
        if (type === 'error') {
            console.error(message);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// Expose showToast globally for backward compatibility
window.showToast = showToast;

// Also expose it on OpenMonitor for consistency
document.addEventListener('DOMContentLoaded', () => {
    if (window.OpenMonitor) {
        window.OpenMonitor.showToast = showToast;
    }
});
