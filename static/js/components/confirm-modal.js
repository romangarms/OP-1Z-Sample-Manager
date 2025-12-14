// ===========================================
// Confirmation Modal System
// ===========================================

/**
 * Show a confirmation modal dialog.
 *
 * Usage:
 *   showConfirmModal('Delete Item', 'Are you sure?', () => {
 *       // Code to run on confirm
 *   });
 *
 *   // With options:
 *   showConfirmModal('Remove User', 'This will remove the user.', onConfirm, {
 *       confirmText: 'Remove',
 *       btnClass: 'warning'
 *   });
 *
 * @param {string} title - Modal title
 * @param {string} message - Modal body (HTML allowed)
 * @param {function} onConfirm - Callback when user confirms
 * @param {object} options - Optional settings (confirmText, btnClass)
 */
function showConfirmModal(title, message, onConfirm, options = {}) {
    const modalEl = document.getElementById('confirmModal');
    const titleEl = document.getElementById('confirmModalTitle');
    const bodyEl = document.getElementById('confirmModalBody');
    const confirmBtn = document.getElementById('confirmModalBtn');

    // Set content
    titleEl.textContent = title;
    bodyEl.innerHTML = message;

    // Configure button
    confirmBtn.textContent = options.confirmText || 'Delete';
    confirmBtn.className = `btn btn-${options.btnClass || 'danger'}`;

    // Remove old event listeners by cloning the button
    const newBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

    // Add new click handler
    newBtn.addEventListener('click', () => {
        const modal = bootstrap.Modal.getInstance(modalEl);
        modal.hide();
        onConfirm();
    });

    // Show the modal
    new bootstrap.Modal(modalEl).show();
}
