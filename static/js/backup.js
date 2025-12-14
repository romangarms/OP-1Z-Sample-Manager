// ===========================================
// Backup & Restore Page
// ===========================================

// Map track IDs to CSS variable names (for preview)
const TRACK_COLOR_VARS = {
    1: '--first-color',   // Green
    2: '--second-color',  // Blue
    3: '--third-color',   // Yellow
    4: '--fourth-color'   // Red
};

// State management
const state = {
    currentDevice: 'opz',
    backups: { opz: [], op1: [] },

    // Preview state (OP-1 only)
    previewWavesurfers: {},
    previewLoaded: {},
    previewVolumes: {},
    isPreviewPlaying: false,
    previewMasterDuration: 0,
    currentPreviewBackup: null
};

// ===========================================
// Initialization
// ===========================================

async function initBackupPage() {
    lucide.createIcons();

    // Check device configurations
    const hasDevice = await checkDeviceConfiguration();
    if (!hasDevice) {
        document.getElementById('device-error-container').hidden = false;
        document.getElementById('main-content').hidden = true;
        return;
    }

    document.getElementById('main-content').hidden = false;

    // Load saved device preference
    try {
        const res = await fetch('/get-config-setting?config_option=SELECTED_DEVICE');
        const data = await res.json();
        state.currentDevice = data.config_value || 'opz';
    } catch (error) {
        console.error('Error loading device preference:', error);
    }

    // Set up device tabs
    setupDeviceTabs();

    // Set up create backup buttons
    setupCreateBackupButtons();

    // Load initial backups
    await switchDevice(state.currentDevice);
}

async function checkDeviceConfiguration() {
    try {
        const [opzRes, op1Res] = await Promise.all([
            fetch('/get-config-setting?config_option=OPZ_MOUNT_PATH').then(r => r.json()),
            fetch('/get-config-setting?config_option=OP1_MOUNT_PATH').then(r => r.json())
        ]);

        const opzSet = opzRes.config_value && opzRes.config_value !== '';
        const op1Set = op1Res.config_value && op1Res.config_value !== '';

        return opzSet || op1Set;
    } catch (error) {
        console.error('Error checking device configuration:', error);
        return false;
    }
}

function setupDeviceTabs() {
    document.querySelectorAll('.device-tab').forEach(tab => {
        tab.addEventListener('click', () => switchDevice(tab.dataset.device));
    });
}

function setupCreateBackupButtons() {
    document.getElementById('opz-create-backup').addEventListener('click', () => createBackup('opz'));
    document.getElementById('op1-create-backup').addEventListener('click', () => createBackup('op1'));
}

async function switchDevice(device) {
    state.currentDevice = device;

    // Update tab UI
    document.querySelectorAll('.device-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.device === device);
    });

    // Toggle section visibility
    document.getElementById('opz-backup-section').hidden = device !== 'opz';
    document.getElementById('op1-backup-section').hidden = device !== 'op1';

    // Fetch backups for current device
    await fetchBackups(device);

    // Save preference
    try {
        await fetch('/set-config-setting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_option: 'SELECTED_DEVICE', config_value: device })
        });
    } catch (error) {
        console.error('Error saving device preference:', error);
    }
}

// ===========================================
// Backup List Management
// ===========================================

async function fetchBackups(device) {
    try {
        const response = await fetch(`/api/backup/list/${device}`);
        const data = await response.json();

        if (data.error) {
            console.error('Error fetching backups:', data.error);
            return;
        }

        state.backups[device] = data.backups;
        renderBackupList(device, data.backups);
    } catch (error) {
        console.error('Error fetching backups:', error);
    }
}

function renderBackupList(device, backups) {
    const container = document.getElementById(`${device}-backup-list`);

    if (backups.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i data-lucide="hard-drive"></i>
                <h3>No Backups Yet</h3>
                <p>Create your first backup to get started.</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }

    container.innerHTML = backups.map(backup => `
        <div class="backup-card" data-timestamp="${escapeHtml(backup.timestamp)}">
            <div class="backup-card-header">
                <div class="backup-name-container">
                    <span class="backup-name">${escapeHtml(backup.name)}</span>
                    <button class="edit-name-btn" onclick="startRename('${device}', '${escapeHtml(backup.timestamp)}', '${escapeHtml(backup.name)}')" title="Edit name">
                        <i data-lucide="pencil" style="width: 16px; height: 16px;"></i>
                    </button>
                </div>
                <div class="backup-date">
                    <i data-lucide="calendar" style="width: 14px; height: 14px;"></i>
                    ${escapeHtml(backup.created)}
                </div>
            </div>
            <div class="backup-card-body">
                <div class="backup-info-row">
                    <span class="backup-info-label">Size</span>
                    <span class="backup-info-value">${formatFileSize(backup.size)}</span>
                </div>
                <div class="backup-info-row">
                    <span class="backup-info-label">Files</span>
                    <span class="backup-info-value">${backup.file_count.toLocaleString()}</span>
                </div>
            </div>
            <div class="backup-card-footer">
                ${device === 'op1' ? `
                    <button class="btn preview-btn" onclick="showPreview('${device}', '${escapeHtml(backup.timestamp)}')">
                        <i data-lucide="play"></i> Preview
                    </button>
                ` : ''}
                <button class="btn restore-btn" onclick="confirmRestore('${device}', '${escapeHtml(backup.timestamp)}', '${escapeHtml(backup.name)}')">
                    <i data-lucide="upload"></i> Restore
                </button>
                <button class="btn delete-backup-btn" onclick="confirmDelete('${device}', '${escapeHtml(backup.timestamp)}', '${escapeHtml(backup.name)}')">
                    <i data-lucide="trash-2"></i>
                </button>
            </div>
        </div>
    `).join('');

    lucide.createIcons();
}

// ===========================================
// Backup Operations
// ===========================================

async function createBackup(device) {
    const btn = document.getElementById(`${device}-create-backup`);
    btn.disabled = true;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<i data-lucide="loader-2" class="spin"></i> Creating...`;
    lucide.createIcons();

    try {
        const response = await fetch('/api/backup/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device })
        });

        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Backup Failed');
        } else {
            toast.success(`${result.files_copied} files (${formatFileSize(result.size)})`, 'Backup Created');
            await fetchBackups(device);
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        toast.error(error.message, 'Backup Failed');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
        lucide.createIcons();
    }
}

function confirmRestore(device, timestamp, name) {
    // Store for the confirm button
    window.pendingRestore = { device, timestamp };

    // Update modal content
    document.getElementById('restore-backup-name').textContent = name;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('restoreModal'));
    modal.show();
}

async function executeRestore() {
    const { device, timestamp } = window.pendingRestore;

    // Hide modal
    bootstrap.Modal.getInstance(document.getElementById('restoreModal')).hide();

    // Show loading
    showLoading('Restoring backup...');

    try {
        const response = await fetch('/api/backup/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device, timestamp })
        });

        const result = await response.json();

        hideLoading();

        if (result.error) {
            toast.error(result.error, 'Restore Failed');
        } else {
            toast.success(`${result.files_restored} files restored`, 'Restore Complete');
        }
    } catch (error) {
        hideLoading();
        console.error('Error restoring backup:', error);
        toast.error(error.message, 'Restore Failed');
    }

    window.pendingRestore = null;
}

function confirmDelete(device, timestamp, name) {
    showConfirmModal(
        'Delete Backup',
        `Are you sure you want to delete "<strong>${escapeHtml(name)}</strong>"?<br><br>This action cannot be undone.`,
        () => deleteBackup(device, timestamp)
    );
}

async function deleteBackup(device, timestamp) {
    try {
        const response = await fetch('/api/backup/delete', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device, timestamp })
        });

        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Delete Failed');
        } else {
            toast.success('Backup deleted', 'Deleted');
            await fetchBackups(device);
        }
    } catch (error) {
        console.error('Error deleting backup:', error);
        toast.error(error.message, 'Delete Failed');
    }
}

// ===========================================
// Rename Backup
// ===========================================

function startRename(device, timestamp, currentName) {
    const card = document.querySelector(`.backup-card[data-timestamp="${timestamp}"]`);
    const nameContainer = card.querySelector('.backup-name-container');

    nameContainer.innerHTML = `
        <input type="text" class="backup-name-input" value="${escapeHtml(currentName)}"
               onkeydown="handleRenameKeydown(event, '${device}', '${timestamp}')"
               onblur="cancelRename('${device}', '${timestamp}', '${escapeHtml(currentName)}')" />
        <button class="btn btn-sm btn-primary" onmousedown="saveRename('${device}', '${timestamp}')">Save</button>
    `;

    const input = nameContainer.querySelector('input');
    input.focus();
    input.select();
}

function handleRenameKeydown(event, device, timestamp) {
    if (event.key === 'Enter') {
        event.preventDefault();
        saveRename(device, timestamp);
    } else if (event.key === 'Escape') {
        fetchBackups(device); // Re-render to cancel
    }
}

function cancelRename(device, timestamp, originalName) {
    // Small delay to allow save button click to process
    setTimeout(() => {
        const card = document.querySelector(`.backup-card[data-timestamp="${timestamp}"]`);
        if (card && card.querySelector('.backup-name-input')) {
            fetchBackups(device);
        }
    }, 150);
}

async function saveRename(device, timestamp) {
    const card = document.querySelector(`.backup-card[data-timestamp="${timestamp}"]`);
    const input = card.querySelector('.backup-name-input');
    const newName = input.value.trim();

    if (!newName) {
        toast.warning('Name cannot be empty');
        return;
    }

    try {
        const response = await fetch('/api/backup/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device, timestamp, name: newName })
        });

        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Rename Failed');
        }

        await fetchBackups(device);
    } catch (error) {
        console.error('Error renaming backup:', error);
        toast.error(error.message, 'Rename Failed');
    }
}

// ===========================================
// OP-1 Preview
// ===========================================

async function showPreview(device, timestamp) {
    if (device !== 'op1') return;

    state.currentPreviewBackup = { device, timestamp };

    // Reset preview state
    cleanupPreview();

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('previewModal'));
    modal.show();

    // Show loading, hide content
    document.getElementById('preview-loading').hidden = false;
    document.getElementById('preview-content').hidden = true;

    try {
        // Prepare audio files
        const response = await fetch(`/api/backup/preview/prepare/${device}/${timestamp}`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Preview Failed');
            modal.hide();
            return;
        }

        // Build track UI
        renderPreviewTracks(result.tracks, device, timestamp);

        // Initialize WaveSurfer instances
        await initPreviewWavesurfers(result.tracks, device, timestamp);

        // Show content
        document.getElementById('preview-loading').hidden = true;
        document.getElementById('preview-content').hidden = false;

        // Setup controls
        setupPreviewControls();

        lucide.createIcons();

    } catch (error) {
        console.error('Error showing preview:', error);
        toast.error(error.message, 'Preview Failed');
        modal.hide();
    }
}

function renderPreviewTracks(tracks, device, timestamp) {
    const container = document.getElementById('preview-tracks');

    container.innerHTML = tracks.map(track => `
        <div class="preview-track ${track.exists ? '' : 'not-found'}" data-track="${track.id}">
            <div class="preview-track-header">
                <span class="preview-track-label">Track ${track.id}</span>
            </div>
            <div class="preview-waveform" id="preview-waveform-${track.id}">
                ${track.exists ? '' : 'No audio file'}
            </div>
        </div>
    `).join('');
}

function darkenColor(hex, factor) {
    hex = hex.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const newR = Math.round(r * (1 - factor));
    const newG = Math.round(g * (1 - factor));
    const newB = Math.round(b * (1 - factor));
    return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
}

function getTrackColors(trackId) {
    const varName = TRACK_COLOR_VARS[trackId];
    const style = getComputedStyle(document.documentElement);
    const wave = style.getPropertyValue(varName).trim();
    return { wave, progress: darkenColor(wave, 0.3) };
}

async function initPreviewWavesurfers(tracks, device, timestamp) {
    state.previewWavesurfers = {};
    state.previewLoaded = {};
    state.previewVolumes = {};
    state.previewMasterDuration = 0;

    const loadPromises = [];

    for (const track of tracks) {
        if (!track.exists || !track.ready) continue;

        const trackId = track.id;
        state.previewLoaded[trackId] = false;
        state.previewVolumes[trackId] = 1.0;

        const colors = getTrackColors(trackId);

        const ws = WaveSurfer.create({
            container: `#preview-waveform-${trackId}`,
            waveColor: colors.wave,
            progressColor: colors.progress,
            cursorColor: '#333',
            cursorWidth: 2,
            height: 50,
            normalize: true,
            barWidth: 2,
            barGap: 1,
            barRadius: 1
        });

        const loadPromise = new Promise((resolve) => {
            ws.on('ready', () => {
                state.previewLoaded[trackId] = true;
                const duration = ws.getDuration();
                if (duration > state.previewMasterDuration) {
                    state.previewMasterDuration = duration;
                    updatePreviewTimeDisplay(0, duration);
                }
                resolve();
            });

            ws.on('error', (err) => {
                console.error(`Error loading preview track ${trackId}:`, err);
                resolve();
            });
        });

        ws.on('timeupdate', (currentTime) => {
            if (state.isPreviewPlaying) {
                updatePreviewTimeDisplay(currentTime, state.previewMasterDuration);
            }
        });

        ws.load(`/api/backup/preview/audio/${device}/${timestamp}/${trackId}`);

        state.previewWavesurfers[trackId] = ws;
        loadPromises.push(loadPromise);
    }

    await Promise.all(loadPromises);
}

function setupPreviewControls() {
    document.getElementById('preview-play').onclick = playAllPreviewTracks;
    document.getElementById('preview-pause').onclick = pauseAllPreviewTracks;
    document.getElementById('preview-stop').onclick = stopAllPreviewTracks;
}

function playAllPreviewTracks() {
    const loadedTracks = Object.keys(state.previewWavesurfers).filter(id => state.previewLoaded[id]);
    if (loadedTracks.length === 0) return;

    // Get current position from first track
    const firstTrack = state.previewWavesurfers[loadedTracks[0]];
    const currentTime = firstTrack.getCurrentTime();

    // Sync and play all
    loadedTracks.forEach(id => {
        const ws = state.previewWavesurfers[id];
        const duration = ws.getDuration();
        if (duration > 0) {
            ws.seekTo(currentTime / duration);
        }
        ws.setVolume(state.previewVolumes[id]);
        ws.play();
    });

    state.isPreviewPlaying = true;
}

function pauseAllPreviewTracks() {
    Object.keys(state.previewWavesurfers).forEach(id => {
        if (state.previewLoaded[id]) {
            state.previewWavesurfers[id].pause();
        }
    });
    state.isPreviewPlaying = false;
}

function stopAllPreviewTracks() {
    Object.keys(state.previewWavesurfers).forEach(id => {
        if (state.previewLoaded[id]) {
            const ws = state.previewWavesurfers[id];
            ws.pause();
            ws.seekTo(0);
        }
    });
    state.isPreviewPlaying = false;
    updatePreviewTimeDisplay(0, state.previewMasterDuration);
}

function cleanupPreview() {
    // Destroy existing wavesurfers
    Object.values(state.previewWavesurfers).forEach(ws => {
        if (ws) {
            try {
                ws.destroy();
            } catch (e) {
                // Ignore cleanup errors
            }
        }
    });

    state.previewWavesurfers = {};
    state.previewLoaded = {};
    state.isPreviewPlaying = false;
    state.previewMasterDuration = 0;
}

// Cleanup when modal closes
document.addEventListener('DOMContentLoaded', () => {
    const previewModal = document.getElementById('previewModal');
    if (previewModal) {
        previewModal.addEventListener('hidden.bs.modal', cleanupPreview);
    }
});

// ===========================================
// Loading UI
// ===========================================

function showLoading(message) {
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.getElementById('loading-status').textContent = message || 'Loading...';
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// ===========================================
// Utility Functions
// ===========================================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function updatePreviewTimeDisplay(current, total) {
    document.getElementById('preview-current-time').textContent = formatTime(current);
    document.getElementById('preview-total-time').textContent = formatTime(total);
}

async function openBackupsFolder() {
    try {
        const response = await fetch('/api/backup/open-folder');
        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Failed to Open Folder');
        }
    } catch (error) {
        console.error('Error opening backups folder:', error);
        toast.error(error.message, 'Failed to Open Folder');
    }
}

// ===========================================
// Initialize on DOM Ready
// ===========================================

document.addEventListener('DOMContentLoaded', initBackupPage);
