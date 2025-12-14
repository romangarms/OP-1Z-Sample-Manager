// ===========================================
// OP-1 Tape Export - Audio Player
// ===========================================

// Map track IDs to CSS variable names
const TRACK_COLOR_VARS = {
    1: '--first-color',   // Green
    2: '--second-color',  // Blue
    3: '--third-color',   // Yellow
    4: '--fourth-color'   // Red
};

/**
 * Darken a hex color by a given factor (0-1)
 */
function darkenColor(hex, factor) {
    // Remove # if present
    hex = hex.replace('#', '');

    // Parse RGB values
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    // Darken each component
    const newR = Math.round(r * (1 - factor));
    const newG = Math.round(g * (1 - factor));
    const newB = Math.round(b * (1 - factor));

    // Convert back to hex
    return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
}

/**
 * Get track colors from CSS variables
 */
function getTrackColors(trackId) {
    const varName = TRACK_COLOR_VARS[trackId];
    const style = getComputedStyle(document.documentElement);
    const wave = style.getPropertyValue(varName).trim();
    return { wave, progress: darkenColor(wave, 0.3) };
}

// State management
const state = {
    // Tape tracks
    tapeWavesurfers: {},      // { 1: WaveSurfer, 2: WaveSurfer, ... }
    tapeLoaded: {},           // { 1: true, 2: false, ... }
    tapeMuted: {},            // { 1: false, 2: false, ... }
    tapeVolumes: {},          // { 1: 1.0, 2: 1.0, ... }
    soloTrack: null,          // Track ID that's solo'd, or null
    isPlaying: false,
    masterDuration: 0,
    isSyncing: false,         // Flag to prevent recursive seeking

    // Album
    albumWavesurfers: {},     // { a: WaveSurfer, b: WaveSurfer }
    albumLoaded: {},          // { a: true, b: false }

    // Track info from API
    tapeTracksInfo: [],
    albumTracksInfo: []
};

// ===========================================
// Loading UI
// ===========================================

function showLoading(message) {
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.getElementById('loading-status').textContent = message || 'Loading...';
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
    document.getElementById('main-content').hidden = false;
}

function updateLoadingProgress(percent) {
    document.getElementById('loading-progress').style.width = `${percent}%`;
}

// ===========================================
// Initialization
// ===========================================

async function initTapeExport() {
    // Initialize Lucide icons for loading screen
    lucide.createIcons();

    // Check OP-1 configuration
    const configured = await checkOP1Configuration();
    if (!configured) {
        document.getElementById('loading-overlay').classList.add('hidden');
        return;
    }

    // Show loading and prepare audio files
    showLoading('Checking audio files...');
    updateLoadingProgress(10);

    // Get track metadata first
    await loadTrackMetadata();
    updateLoadingProgress(20);

    // Prepare (convert) audio files
    showLoading('Converting audio for playback (this may take a moment)...');
    const prepareResult = await prepareAudioFiles();
    updateLoadingProgress(80);

    if (prepareResult.error) {
        showLoading(`Error: ${prepareResult.error}`);
        return;
    }

    // Now initialize the waveform players
    showLoading('Loading waveforms...');
    await initializePlayers();
    updateLoadingProgress(100);

    // Set up event listeners
    setupMasterControls();
    setupExportButtons();

    // Hide loading and show main content
    hideLoading();

    // Re-initialize icons for main content
    lucide.createIcons();
}

async function checkOP1Configuration() {
    try {
        const res = await fetch('/get-config-setting?config_option=OP1_MOUNT_PATH');
        const data = await res.json();
        const isSet = data.config_value && data.config_value !== '';

        if (!isSet) {
            document.getElementById('device-error-container').hidden = false;
            return false;
        }
        return true;
    } catch (error) {
        console.error('Error checking device configuration:', error);
        return false;
    }
}

async function loadTrackMetadata() {
    try {
        const [tapeRes, albumRes] = await Promise.all([
            fetch('/api/tape/tracks'),
            fetch('/api/tape/album')
        ]);

        const tapeData = await tapeRes.json();
        const albumData = await albumRes.json();

        if (!tapeData.error) {
            state.tapeTracksInfo = tapeData.tracks;
        }
        if (!albumData.error) {
            state.albumTracksInfo = albumData.sides;
        }
    } catch (error) {
        console.error('Error loading track metadata:', error);
    }
}

async function prepareAudioFiles() {
    try {
        const response = await fetch('/api/tape/prepare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        return await response.json();
    } catch (error) {
        console.error('Error preparing audio:', error);
        return { error: error.message };
    }
}

async function initializePlayers() {
    // Initialize tape tracks
    for (const track of state.tapeTracksInfo) {
        const trackId = track.id;
        state.tapeLoaded[trackId] = false;
        state.tapeMuted[trackId] = false;
        state.tapeVolumes[trackId] = 1.0;

        if (track.exists) {
            initTapeWavesurfer(trackId);
        } else {
            const container = document.getElementById(`waveform-track-${trackId}`);
            container.classList.add('not-found');
            container.querySelector('.waveform-loading').style.display = 'none';
        }

        setupTrackControls(trackId);
    }

    // Initialize album tracks
    for (const side of state.albumTracksInfo) {
        const sideId = side.id;
        state.albumLoaded[sideId] = false;

        if (side.exists) {
            initAlbumWavesurfer(sideId);
        } else {
            const container = document.getElementById(`waveform-side-${sideId}`);
            container.classList.add('not-found');
            container.querySelector('.waveform-loading').style.display = 'none';
        }

        setupAlbumControls(sideId);
    }
}

// ===========================================
// Tape Tracks Initialization
// ===========================================

function initTapeWavesurfer(trackId) {
    const colors = getTrackColors(trackId);
    const container = document.getElementById(`waveform-track-${trackId}`);

    const ws = WaveSurfer.create({
        container: `#waveform-track-${trackId}`,
        waveColor: colors.wave,
        progressColor: colors.progress,
        cursorColor: '#333',
        cursorWidth: 2,
        height: 80,
        normalize: true,
        barWidth: 2,
        barGap: 1,
        barRadius: 1
    });

    ws.load(`/api/tape/audio/tape/${trackId}`);

    ws.on('ready', () => {
        state.tapeLoaded[trackId] = true;
        container.classList.add('loaded');

        // Update master duration if this track is longer
        const duration = ws.getDuration();
        if (duration > state.masterDuration) {
            state.masterDuration = duration;
            updateTapeTimeDisplay(0, duration);
        }
    });

    // Use timeupdate for reliable time updates during playback
    ws.on('timeupdate', (currentTime) => {
        if (state.isPlaying && !state.isSyncing) {
            updateTapeTimeDisplay(currentTime, state.masterDuration);
        }
    });

    // Handle user clicking on waveform to seek
    ws.on('interaction', () => {
        if (state.isSyncing) return;

        // Get the current time after user clicked
        const currentTime = ws.getCurrentTime();
        const duration = ws.getDuration();

        if (duration > 0) {
            const progress = currentTime / duration;
            syncAllTapeTracks(progress, trackId);
        }
    });

    ws.on('finish', () => {
        // Check if all tracks finished
        const allFinished = Object.keys(state.tapeWavesurfers).every(id => {
            const wsTrack = state.tapeWavesurfers[id];
            return !wsTrack || wsTrack.getCurrentTime() >= wsTrack.getDuration() - 0.1;
        });

        if (allFinished) {
            state.isPlaying = false;
        }
    });

    ws.on('error', (err) => {
        console.error(`Error loading track ${trackId}:`, err);
        container.classList.add('error');
        container.querySelector('.waveform-loading').textContent = 'Error loading audio';
    });

    state.tapeWavesurfers[trackId] = ws;
}

function setupTrackControls(trackId) {
    const container = document.querySelector(`.track-container[data-track="${trackId}"]`);
    if (!container) return;

    const muteBtn = container.querySelector('.mute-btn');
    const soloBtn = container.querySelector('.solo-btn');
    const volumeSlider = container.querySelector('.volume-slider');

    muteBtn.addEventListener('click', () => toggleMute(trackId));
    soloBtn.addEventListener('click', () => toggleSolo(trackId));
    volumeSlider.addEventListener('input', (e) => setTrackVolume(trackId, parseInt(e.target.value)));
}

// ===========================================
// Album Tracks Initialization
// ===========================================

function initAlbumWavesurfer(sideId) {
    const container = document.getElementById(`waveform-side-${sideId}`);

    const ws = WaveSurfer.create({
        container: `#waveform-side-${sideId}`,
        waveColor: '#0186bb',
        progressColor: '#027340',
        cursorColor: '#333',
        cursorWidth: 2,
        height: 100,
        normalize: true,
        barWidth: 2,
        barGap: 1,
        barRadius: 1
    });

    ws.load(`/api/tape/audio/album/${sideId}`);

    ws.on('ready', () => {
        state.albumLoaded[sideId] = true;
        container.classList.add('loaded');
        updateAlbumTimeDisplay(sideId, 0, ws.getDuration());
    });

    // Use timeupdate for reliable time updates
    ws.on('timeupdate', (currentTime) => {
        updateAlbumTimeDisplay(sideId, currentTime, ws.getDuration());
    });

    ws.on('finish', () => {
        updateAlbumTimeDisplay(sideId, ws.getDuration(), ws.getDuration());
    });

    ws.on('error', (err) => {
        console.error(`Error loading album side ${sideId}:`, err);
        container.classList.add('error');
        container.querySelector('.waveform-loading').textContent = 'Error loading audio';
    });

    state.albumWavesurfers[sideId] = ws;
}

function setupAlbumControls(sideId) {
    const container = document.querySelector(`.album-side[data-side="${sideId}"]`);
    if (!container) return;

    const playBtn = container.querySelector('.play-btn');
    const pauseBtn = container.querySelector('.pause-btn');
    const stopBtn = container.querySelector('.stop-btn');
    const volumeSlider = container.querySelector('.volume-slider');

    playBtn.addEventListener('click', () => {
        const ws = state.albumWavesurfers[sideId];
        if (ws && state.albumLoaded[sideId]) {
            ws.play();
        }
    });

    pauseBtn.addEventListener('click', () => {
        const ws = state.albumWavesurfers[sideId];
        if (ws) {
            ws.pause();
        }
    });

    stopBtn.addEventListener('click', () => {
        const ws = state.albumWavesurfers[sideId];
        if (ws) {
            ws.pause();
            ws.seekTo(0);
            updateAlbumTimeDisplay(sideId, 0, ws.getDuration());
        }
    });

    volumeSlider.addEventListener('input', (e) => {
        const ws = state.albumWavesurfers[sideId];
        if (ws) {
            ws.setVolume(parseInt(e.target.value) / 100);
        }
    });
}

// ===========================================
// Master Controls (Tape)
// ===========================================

function setupMasterControls() {
    document.getElementById('tape-play').addEventListener('click', playAllTapeTracks);
    document.getElementById('tape-pause').addEventListener('click', pauseAllTapeTracks);
    document.getElementById('tape-stop').addEventListener('click', stopAllTapeTracks);
}

function playAllTapeTracks() {
    const loadedTracks = Object.keys(state.tapeWavesurfers).filter(id => state.tapeLoaded[id]);
    if (loadedTracks.length === 0) return;

    // Get current position from the first loaded track
    const firstTrack = state.tapeWavesurfers[loadedTracks[0]];
    const currentTime = firstTrack.getCurrentTime();

    // Sync all tracks to the same position and play
    loadedTracks.forEach(id => {
        const ws = state.tapeWavesurfers[id];
        const duration = ws.getDuration();

        if (duration > 0) {
            ws.seekTo(currentTime / duration);
        }

        applyVolumeState(id);
        ws.play();
    });

    state.isPlaying = true;
}

function pauseAllTapeTracks() {
    Object.keys(state.tapeWavesurfers).forEach(id => {
        if (state.tapeLoaded[id]) {
            state.tapeWavesurfers[id].pause();
        }
    });
    state.isPlaying = false;
}

function stopAllTapeTracks() {
    state.isSyncing = true;

    Object.keys(state.tapeWavesurfers).forEach(id => {
        if (state.tapeLoaded[id]) {
            const ws = state.tapeWavesurfers[id];
            ws.pause();
            ws.seekTo(0);
        }
    });

    state.isPlaying = false;
    state.isSyncing = false;
    updateTapeTimeDisplay(0, state.masterDuration);
}

function syncAllTapeTracks(progress, sourceTrackId) {
    if (state.isSyncing) return;

    state.isSyncing = true;

    Object.keys(state.tapeWavesurfers).forEach(id => {
        // Skip the source track since it already seeked
        if (id === String(sourceTrackId)) return;

        if (state.tapeLoaded[id]) {
            state.tapeWavesurfers[id].seekTo(progress);
        }
    });

    const time = progress * state.masterDuration;
    updateTapeTimeDisplay(time, state.masterDuration);

    state.isSyncing = false;
}

// ===========================================
// Volume / Mute / Solo
// ===========================================

function applyVolumeState(trackId) {
    const ws = state.tapeWavesurfers[trackId];
    if (!ws) return;

    const isMuted = state.tapeMuted[trackId];
    let volume = state.tapeVolumes[trackId];

    if (state.soloTrack !== null) {
        if (parseInt(trackId) !== state.soloTrack) {
            volume = 0;
        }
    } else if (isMuted) {
        volume = 0;
    }

    ws.setVolume(volume);
}

function toggleMute(trackId) {
    state.tapeMuted[trackId] = !state.tapeMuted[trackId];

    const container = document.querySelector(`.track-container[data-track="${trackId}"]`);
    const muteBtn = container.querySelector('.mute-btn');
    const icon = muteBtn.querySelector('i');

    if (state.tapeMuted[trackId]) {
        muteBtn.classList.add('active');
        icon.setAttribute('data-lucide', 'volume-x');
    } else {
        muteBtn.classList.remove('active');
        icon.setAttribute('data-lucide', 'volume-2');
    }

    lucide.createIcons();
    applyVolumeState(trackId);
}

function toggleSolo(trackId) {
    const numTrackId = parseInt(trackId);

    if (state.soloTrack === numTrackId) {
        state.soloTrack = null;
    } else {
        state.soloTrack = numTrackId;
    }

    document.querySelectorAll('.track-container').forEach(container => {
        const tid = container.dataset.track;
        const soloBtn = container.querySelector('.solo-btn');

        if (parseInt(tid) === state.soloTrack) {
            soloBtn.classList.add('active');
        } else {
            soloBtn.classList.remove('active');
        }
    });

    Object.keys(state.tapeWavesurfers).forEach(id => applyVolumeState(id));
}

function setTrackVolume(trackId, value) {
    state.tapeVolumes[trackId] = value / 100;
    applyVolumeState(trackId);
}

// ===========================================
// Time Display
// ===========================================

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function updateTapeTimeDisplay(current, total) {
    document.getElementById('tape-current-time').textContent = formatTime(current);
    document.getElementById('tape-total-time').textContent = formatTime(total);
}

function updateAlbumTimeDisplay(sideId, current, total) {
    const container = document.querySelector(`.album-side[data-side="${sideId}"]`);
    if (!container) return;

    container.querySelector('.current-time').textContent = formatTime(current);
    container.querySelector('.total-time').textContent = formatTime(total);
}

// ===========================================
// Export Functions
// ===========================================

/**
 * Run an async function with button loading state
 * Shows spinner while running, restores original content when done
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

function setupExportButtons() {
    document.getElementById('export-tape').addEventListener('click', exportTapeTracks);
    document.getElementById('export-album').addEventListener('click', exportAlbumTracks);
}

async function exportTapeTracks() {
    const btn = document.getElementById('export-tape');

    await withButtonLoading(btn, 'Exporting...', async () => {
        const response = await fetch('/api/tape/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'tape' })
        });

        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Export Failed');
        } else if (result.status === 'success') {
            toast.success(`${result.exported.length} file(s) exported to Downloads`, 'Export Complete');
        } else if (result.status === 'partial') {
            toast.warning(`Exported ${result.exported.length} file(s) with some errors`, 'Partial Export');
        }
    });
}

async function exportAlbumTracks() {
    const btn = document.getElementById('export-album');

    await withButtonLoading(btn, 'Exporting...', async () => {
        const response = await fetch('/api/tape/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'album' })
        });

        const result = await response.json();

        if (result.error) {
            toast.error(result.error, 'Export Failed');
        } else if (result.status === 'success') {
            toast.success(`${result.exported.length} file(s) exported to Downloads`, 'Export Complete');
        } else if (result.status === 'partial') {
            toast.warning(`Exported ${result.exported.length} file(s) with some errors`, 'Partial Export');
        }
    });
}

// ===========================================
// Initialize on DOM Ready
// ===========================================

document.addEventListener('DOMContentLoaded', initTapeExport);
