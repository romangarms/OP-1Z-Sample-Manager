// ===========================================
// Toast Notification System
// ===========================================

/**
 * Toast notification system for the app.
 *
 * Usage:
 *   toast.success('Backup created successfully!');
 *   toast.error('Failed to restore backup');
 *   toast.warning('Device not connected');
 *   toast.info('Processing files...');
 *
 *   // With title:
 *   toast.success('Files exported to Downloads folder', 'Export Complete');
 *
 *   // With options:
 *   toast.success('Done!', null, { duration: 5000 });
 */

const toast = (function() {
    // Default settings
    const defaults = {
        duration: 4000,      // Auto-dismiss after 4 seconds
        position: 'top-right'
    };

    // Icon SVGs for each toast type
    const icons = {
        success: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
        error: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
        warning: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
        info: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
    };

    const closeIcon = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';

    let container = null;

    /**
     * Ensure the toast container exists
     */
    function ensureContainer() {
        if (!container) {
            container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'toast-container';
                document.body.appendChild(container);
            }
        }
        return container;
    }

    /**
     * Create and show a toast notification
     * @param {string} type - 'success', 'error', 'warning', 'info'
     * @param {string} message - The message to display
     * @param {string|null} title - Optional title
     * @param {object} options - Optional settings (duration, etc.)
     */
    function show(type, message, title = null, options = {}) {
        const settings = { ...defaults, ...options };
        const container = ensureContainer();

        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast toast-${type}`;

        // Build inner HTML
        const titleHtml = title ? `<div class="toast-title">${escapeHtml(title)}</div>` : '';

        toastEl.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                ${titleHtml}
                <div class="toast-message">${escapeHtml(message)}</div>
            </div>
            <button class="toast-close" aria-label="Close">${closeIcon}</button>
        `;

        // Add close button handler
        const closeBtn = toastEl.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => dismiss(toastEl));

        // Add to container
        container.appendChild(toastEl);

        // Auto-dismiss after duration
        if (settings.duration > 0) {
            setTimeout(() => dismiss(toastEl), settings.duration);
        }

        return toastEl;
    }

    /**
     * Dismiss a toast with animation
     */
    function dismiss(toastEl) {
        if (!toastEl || toastEl.classList.contains('toast-hiding')) return;

        toastEl.classList.add('toast-hiding');

        // Remove after animation completes
        setTimeout(() => {
            if (toastEl.parentNode) {
                toastEl.parentNode.removeChild(toastEl);
            }
        }, 300);
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Clear all toasts
     */
    function clearAll() {
        const container = ensureContainer();
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
    }

    // Public API
    return {
        success: (message, title = null, options = {}) => show('success', message, title, options),
        error: (message, title = null, options = {}) => show('error', message, title, options),
        warning: (message, title = null, options = {}) => show('warning', message, title, options),
        info: (message, title = null, options = {}) => show('info', message, title, options),
        dismiss,
        clearAll
    };
})();
