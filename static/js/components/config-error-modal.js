// ===========================================
// Config Error Modal System
// ===========================================

/**
 * Check config status on page load and show error modal if needed.
 * Also re-checks config when window regains focus (in error state only).
 */
(function() {
    let inErrorState = false;
    let modalInstance = null;

    document.addEventListener('DOMContentLoaded', function() {
        fetch('/config-status')
            .then(response => response.json())
            .then(data => {
                if (!data.ok) {
                    inErrorState = true;
                    showConfigErrorModal(data.error);
                }
            })
            .catch(error => {
                console.error('Failed to check config status:', error);
            });
    });

    // Re-check config when window regains focus (only in error state)
    window.addEventListener('focus', function() {
        if (inErrorState) {
            recheckConfig();
        }
    });

    function recheckConfig() {
        fetch('/reload-config', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.ok) {
                    // Config is now valid - reload the page
                    inErrorState = false;
                    toast.success('Configuration loaded successfully', 'Config Fixed');
                    setTimeout(() => window.location.reload(), 500);
                } else {
                    // Still invalid - update error details
                    const detailsEl = document.getElementById('configErrorDetails');
                    if (data.error && data.error.message) {
                        let details = data.error.message;
                        if (data.error.line) {
                            details += ` (line ${data.error.line}, column ${data.error.column})`;
                        }
                        detailsEl.textContent = details;
                    }
                }
            })
            .catch(error => {
                console.error('Failed to reload config:', error);
            });
    }

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
                        inErrorState = false;
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
        modalInstance = new bootstrap.Modal(modalEl);
        modalInstance.show();
    }
})();
