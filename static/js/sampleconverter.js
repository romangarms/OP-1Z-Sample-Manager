function setupDragDrop(id, type) {
    const dropArea = document.getElementById(id);
    const samplePackBox = dropArea.parentElement;
    let dragCounter = 0;

    // Create hidden file input
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.multiple = true;
    fileInput.style.display = 'none';
    document.body.appendChild(fileInput);

    // When the user clicks the drop area, trigger the input
    dropArea.addEventListener('click', () => fileInput.click());

    // When files are selected via the file picker
    fileInput.addEventListener('change', async (event) => {
        await handleFiles(event.target.files, type);
    });

    // Drag & Drop behavior - use samplePackBox to avoid child element issues
    samplePackBox.addEventListener('dragenter', (event) => {
        event.preventDefault();
        dragCounter++;
        samplePackBox.classList.add('dragover');
    });

    samplePackBox.addEventListener('dragover', (event) => {
        event.preventDefault();
    });

    samplePackBox.addEventListener('dragleave', (event) => {
        event.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            samplePackBox.classList.remove('dragover');
        }
    });

    samplePackBox.addEventListener('drop', async (event) => {
        event.preventDefault();
        dragCounter = 0;
        samplePackBox.classList.remove('dragover');
        await handleFiles(event.dataTransfer.files, type);
    });
}

function showConvertingProgress(current, total, filename, indeterminate = false) {
    const overlay = document.getElementById('converting-overlay');
    const status = document.getElementById('converting-status');
    const progress = document.getElementById('converting-progress');

    overlay.classList.remove('hidden');

    if (indeterminate) {
        // For parallel processing, show pulsing animation
        status.textContent = filename;
        progress.style.width = '100%';
        progress.classList.add('progress-bar-animated', 'progress-bar-striped');
    } else {
        status.textContent = `Converting ${current} of ${total}: ${filename}`;
        progress.style.width = `${(current / total) * 100}%`;
        progress.classList.remove('progress-bar-animated', 'progress-bar-striped');
    }
}

function hideConvertingProgress() {
    const overlay = document.getElementById('converting-overlay');
    const progress = document.getElementById('converting-progress');

    overlay.classList.add('hidden');
    progress.style.width = '0%';
    progress.classList.remove('progress-bar-animated', 'progress-bar-striped');
}

function getNearestNote(hz) {
    const notes = {
        110: 'A2',
        220: 'A3',
        440: 'A4',
        880: 'A5',
        1760: 'A6'
    };
    return notes[hz] || `${hz}Hz`;
}

// Settings management
async function loadSettings() {
    const settings = {
        autoPitch: true // default
    };

    try {
        const res = await fetch('/get-config-setting?config_option=AUTO_PITCH_SYNTH_SAMPLES');
        const data = await res.json();
        if (data.config_value !== undefined && data.config_value !== null && data.config_value !== '') {
            settings.autoPitch = data.config_value;
        }
    } catch (e) {
        console.warn('Failed to load settings:', e);
    }

    return settings;
}

async function saveSettings(settings) {
    try {
        await fetch('/set-config-setting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config_option: 'AUTO_PITCH_SYNTH_SAMPLES',
                config_value: settings.autoPitch
            })
        });
    } catch (e) {
        console.warn('Failed to save settings:', e);
    }
}

async function openSettingsModal() {
    const settings = await loadSettings();
    document.getElementById('setting-auto-pitch').checked = settings.autoPitch;

    const modal = new bootstrap.Modal(document.getElementById('settingsModal'));
    modal.show();
}

async function handleFiles(files, type) {
    const total = files.length;

    if (total === 0) return;

    // Check if auto-pitch is enabled for synth samples from settings
    const settings = await loadSettings();
    const autoPitch = type === 'synth' && settings.autoPitch;

    console.log('Settings loaded:', settings);
    console.log('Auto-pitch enabled:', autoPitch);

    // Build FormData with all files
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }
    formData.append('type', type);
    formData.append('auto_pitch', autoPitch ? 'true' : 'false');

    // Show initial progress
    showConvertingProgress(0, total, `Converting 0 of ${total}...`);

    try {
        const response = await fetch('/convert-batch', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const data = await response.json();
            hideConvertingProgress();
            toast.error(data.error || 'Batch conversion failed');
            return;
        }

        // Handle SSE stream for progress updates
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResults = null;

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // Keep incomplete message in buffer

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));

                    if (data.type === 'progress') {
                        // Update progress bar
                        showConvertingProgress(
                            data.completed,
                            data.total,
                            `Converting ${data.completed} of ${data.total}...`
                        );
                        console.log(`Progress: ${data.completed}/${data.total}`, data.result);
                    } else if (data.type === 'complete') {
                        finalResults = data.results;
                    }
                }
            }
        }

        hideConvertingProgress();

        if (!finalResults) {
            toast.error('Conversion failed - no results received');
            return;
        }

        // Process final results
        let successCount = 0;
        let errorCount = 0;
        const failedFiles = [];

        for (const result of finalResults) {
            if (result.success) {
                successCount++;
            } else {
                errorCount++;
                failedFiles.push(result.filename);
            }
        }

        // Show single toast with appropriate message
        if (total === 1) {
            // Single file - show detailed result
            const result = finalResults[0];
            if (result.success) {
                if (result.pitch_corrected && result.pitch_info) {
                    const info = result.pitch_info;
                    const note = getNearestNote(info.target_hz);
                    toast.success(`Converted and tuned to ${note} (${info.detected_hz.toFixed(1)}Hz → ${info.target_hz}Hz)`, result.filename);
                } else {
                    toast.success('Converted successfully', result.filename);
                }
            } else {
                toast.error(result.error || 'Conversion failed', result.filename);
            }
        } else {
            // Multiple files - show summary only
            if (errorCount === 0) {
                toast.success(`All ${successCount} files converted successfully`, 'Batch Complete');
            } else if (successCount === 0) {
                toast.error(`All ${errorCount} files failed`, 'Batch Failed');
            } else {
                const failedList = failedFiles.length <= 3
                    ? failedFiles.join(', ')
                    : `${failedFiles.slice(0, 3).join(', ')} and ${failedFiles.length - 3} more`;
                toast.warning(`${successCount} converted, ${errorCount} failed: ${failedList}`, 'Batch Partial');
            }
        }
    } catch (err) {
        hideConvertingProgress();
        console.error('Batch conversion error:', err);
        toast.error(`Batch conversion failed: ${err.message}`);
    }
}


function openExplorer() {
    fetch("/open-explorer", { method: "POST" })
        .then(response => {
            if (!response.ok) throw new Error("Request failed");
            return response.json();
        })
        .catch(err => {
            console.error("Error:", err);
        });
}

function deleteAllConverted() {
    showConfirmModal(
        'Delete All Converted Samples',
        'Are you sure you want to delete all converted samples? This cannot be undone.',
        () => {
            fetch("/delete-all-converted", { method: "DELETE" })
                .then(response => {
                    if (!response.ok) throw new Error("Request failed");
                    return response.json();
                })
                .then(data => {
                    if (data.count === 0) {
                        toast.info('No files to delete', 'Folder Empty');
                    } else {
                        toast.success(`Deleted ${data.count} file(s)`, 'Samples Deleted');
                    }
                })
                .catch(err => {
                    toast.error('Failed to delete samples');
                    console.error("Error:", err);
                });
        }
    );
}

document.addEventListener('DOMContentLoaded', () => {
    setupDragDrop('drum-samples', 'drum');
    setupDragDrop('synth-samples', 'synth');

    // Setup settings event listener
    document.getElementById('setting-auto-pitch').addEventListener('change', async (e) => {
        const settings = await loadSettings();
        settings.autoPitch = e.target.checked;
        await saveSettings(settings);
    });

    // Initialize Lucide icons
    lucide.createIcons();
});

// Prevent default drag-and-drop behavior on the whole page
window.addEventListener("dragover", (e) => {
    e.preventDefault();
});

window.addEventListener("drop", (e) => {
    e.preventDefault();
});