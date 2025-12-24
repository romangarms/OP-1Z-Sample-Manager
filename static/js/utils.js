/**
 * Shared utility functions used across multiple pages
 */

// ===========================================
// HTML/Text Utilities
// ===========================================

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} HTML-escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===========================================
// Formatting Utilities
// ===========================================

/**
 * Format seconds to mm:ss display
 * @param {number} seconds - Time in seconds
 * @returns {string} Formatted time string
 */
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format bytes to human-readable size
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string (e.g., "1.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ===========================================
// UI Helpers
// ===========================================

/**
 * Run an async function with button loading state
 * Shows spinner while running, restores original content when done
 * @param {HTMLButtonElement} btn - The button element
 * @param {string} loadingText - Text to show while loading
 * @param {Function} asyncFn - Async function to execute
 */
async function withButtonLoading(btn, loadingText, asyncFn) {
    btn.disabled = true;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="spin"></i> ${loadingText}`;
    lucide.createIcons();

    try {
        await asyncFn();
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        lucide.createIcons();
    }
}
