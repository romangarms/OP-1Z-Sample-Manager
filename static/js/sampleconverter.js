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

function showConvertingProgress(current, total, filename) {
    const overlay = document.getElementById('converting-overlay');
    const status = document.getElementById('converting-status');
    const progress = document.getElementById('converting-progress');

    overlay.classList.remove('hidden');
    status.textContent = `Converting ${current} of ${total}: ${filename}`;
    progress.style.width = `${(current / total) * 100}%`;
}

function hideConvertingProgress() {
    document.getElementById('converting-overlay').classList.add('hidden');
    document.getElementById('converting-progress').style.width = '0%';
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
    const results = [];
    const total = files.length;

    // Check if auto-pitch is enabled for synth samples from settings
    const settings = await loadSettings();
    const autoPitch = type === 'synth' && settings.autoPitch;

    console.log('Settings loaded:', settings);
    console.log('Auto-pitch enabled:', autoPitch);

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        showConvertingProgress(i + 1, total, file.name);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type); // "drum" or "synth"
        formData.append('auto_pitch', autoPitch ? 'true' : 'false');

        try {
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            console.log('Conversion result:', result);

            if (!response.ok) {
                results.push(`${file.name}: Error - ${result.error || 'Conversion failed'}`);
                toast.error(`${file.name}: ${result.error || 'Conversion failed'}`);
            } else {
                // Display pitch correction info if available
                if (result.pitch_corrected && result.pitch_info) {
                    const info = result.pitch_info;
                    const note = getNearestNote(info.target_hz);
                    const message = `Converted and tuned to ${note} (${info.detected_hz.toFixed(1)}Hz → ${info.target_hz}Hz)`;
                    results.push(`${file.name}: ${message}`);
                    toast.success(message, file.name);
                } else {
                    const message = result.message || 'Converted';
                    results.push(`${file.name}: ${message}`);
                    toast.success(message, file.name);
                }
            }
        } catch (err) {
            console.error('Conversion error:', err);
            results.push(`${file.name}: Error - ${err.message}`);
            toast.error(`${file.name}: ${err.message}`);
        }
    }

    hideConvertingProgress();

    // Show summary toast for multiple files
    if (total > 1) {
        const successCount = results.filter(r => r.includes('Converted')).length;
        const errorCount = results.length - successCount;

        if (errorCount === 0) {
            toast.success(`All ${successCount} file(s) converted successfully`, 'Batch Complete');
        } else if (successCount === 0) {
            toast.error(`All ${errorCount} file(s) failed`, 'Batch Failed');
        } else {
            toast.warning(`${successCount} converted, ${errorCount} failed`, 'Batch Partial');
        }
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