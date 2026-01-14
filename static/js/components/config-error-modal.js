// ===========================================
// Config Error Modal System
// ===========================================

/**
 * Check config status on page load and show error modal if needed.
 */
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        fetch('/config-status')
            .then(response => response.json())
            .then(data => {
                if (!data.ok) {
                    showConfigErrorModal(data.error);
                }
            })
            .catch(error => {
                console.error('Failed to check config status:', error);
            });
    });

    function showConfigErrorModal(error) {
        const modalEl = document.getElementById('configErrorModal');
        const detailsEl = document.getElementById('configErrorDetails');
        const editBtn = document.getElementById('configErrorEditBtn');
        const resetBtn = document.getElementById('configErrorResetBtn');

        // Show error details if available
        if (error && error.message) {
            let details = error.message;
            if (error.line) {
                details += ` (line ${error.line}, column ${error.column})`;
            }
            detailsEl.textContent = details;
        }

        // Wire up Edit Config button
        editBtn.addEventListener('click', function() {
            fetch('/open-config-in-editor', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'opened') {
                        toast.success('Config file opened', 'Editor Launched');
                    }
                })
                .catch(error => {
                    toast.error('Failed to open config file');
                    console.error(error);
                });
        });

        // Wire up Reset Config button
        resetBtn.addEventListener('click', function() {
            fetch('/reset-config', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        toast.success('Configuration has been reset', 'Config Reset');
                        // Reload the page after a short delay
                        setTimeout(() => window.location.reload(), 500);
                    }
                })
                .catch(error => {
                    toast.error('Failed to reset config');
                    console.error(error);
                });
        });

        // Show the modal
        new bootstrap.Modal(modalEl).show();
    }
})();
