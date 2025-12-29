/**
 * Homepage JavaScript
 *
 * Handles device sidebar updates and other home page functionality.
 */

/**
 * Load sidebar state from config and check device status
 */
async function loadSidebarState() {
    const sidebar = document.getElementById('device-sidebar');
    if (!sidebar) return;

    try {
        // First check if any device is connected - if so, expand
        const status = await deviceStatus.getStatus();
        if (status && (status.opz.connected || status.op1.connected)) {
            sidebar.classList.remove('collapsed');
            updateToggleButton(false);
            return;
        }

        // No devices connected - check saved preference
        const response = await fetch('/get-config-setting?config_option=SIDEBAR_EXPANDED');
        const data = await response.json();
        if (data.config_value === true) {
            sidebar.classList.remove('collapsed');
            updateToggleButton(false);
        }
    } catch (e) {
        console.error('Error loading sidebar state:', e);
    }
}

/**
 * Toggle sidebar visibility and save preference
 */
async function toggleSidebar() {
    const sidebar = document.getElementById('device-sidebar');
    if (!sidebar) return;

    const isCollapsed = sidebar.classList.toggle('collapsed');
    updateToggleButton(isCollapsed);

    try {
        await fetch('/set-config-setting', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_option: 'SIDEBAR_EXPANDED', config_value: !isCollapsed })
        });
    } catch (e) {
        console.error('Error saving sidebar state:', e);
    }
}

/**
 * Update toggle button appearance based on sidebar state
 */
function updateToggleButton(isCollapsed) {
    const button = document.getElementById('sidebar-toggle');
    if (!button) return;
    button.classList.toggle('active', !isCollapsed);
}

/**
 * Expand sidebar (called when device connects)
 */
function expandSidebar() {
    const sidebar = document.getElementById('device-sidebar');
    if (!sidebar || !sidebar.classList.contains('collapsed')) return;

    sidebar.classList.remove('collapsed');
    updateToggleButton(false);

    // Save expanded state
    fetch('/set-config-setting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config_option: 'SIDEBAR_EXPANDED', config_value: true })
    }).catch(e => console.error('Error saving sidebar state:', e));
}

/**
 * Update device sidebar card with current status
 */
function updateDeviceSidebar(device, connected, path, mode) {
    const indicator = document.getElementById(`${device}-indicator`);
    const statusText = document.getElementById(`${device}-status-text`);
    const pathText = document.getElementById(`${device}-path-text`);
    const card = document.getElementById(`${device}-status-card`);

    if (!indicator || !statusText || !pathText || !card) {
        return;
    }

    if (connected && mode === 'storage' && path) {
        // Storage mode with path - fully connected
        indicator.classList.remove('disconnected');
        indicator.classList.add('connected');
        statusText.textContent = 'Connected';
        pathText.textContent = path;
        pathText.classList.remove('mode-hint');
        card.classList.remove('disabled');
    } else if (connected && mode === 'other') {
        // Non-storage mode (MIDI/normal) - connected but no disk access
        indicator.classList.remove('disconnected');
        indicator.classList.add('connected');
        statusText.textContent = 'Connected';
        pathText.textContent = 'Switch to disk mode';
        pathText.classList.add('mode-hint');
        card.classList.add('disabled');
    } else if (connected && mode === 'storage' && !path) {
        // Storage mode but path not found yet
        indicator.classList.remove('disconnected');
        indicator.classList.add('connected');
        statusText.textContent = 'Connected';
        pathText.textContent = 'Mounting...';
        pathText.classList.remove('mode-hint');
        card.classList.add('disabled');
    } else {
        // Not connected
        indicator.classList.remove('connected');
        indicator.classList.add('disconnected');
        statusText.textContent = 'Not connected';
        pathText.textContent = '';
        pathText.classList.remove('mode-hint');
        card.classList.add('disabled');
    }
}

/**
 * Initialize sidebar with current device status
 */
async function initDeviceSidebar() {
    try {
        const status = await deviceStatus.getStatus();
        if (status) {
            updateDeviceSidebar('opz', status.opz.connected, status.opz.path, status.opz.mode);
            updateDeviceSidebar('op1', status.op1.connected, status.op1.path, status.op1.mode);
        }
    } catch (e) {
        console.error('Error initializing device sidebar:', e);
    }
}

/**
 * Open external links in system browser
 */
function openExternalLink(url) {
    fetch(`/open-external-link?url=${encodeURIComponent(url)}`)
        .then(response => response.json())
        .catch(err => console.error('Error opening link:', err));
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();

    // Load sidebar state (checks devices and config)
    loadSidebarState();

    // Initialize device sidebar status
    initDeviceSidebar();
});
