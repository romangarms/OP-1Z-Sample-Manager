/**
 * Device Status SSE Client
 *
 * Handles real-time device status updates via Server-Sent Events.
 * Shows toast notifications on device connect/disconnect.
 */

const deviceStatus = {
    eventSource: null,
    isFirstLoad: true,
    initialDevices: { opz: null, op1: null },
    // Track current device state for click handling
    currentState: {
        opz: { connected: false, mode: null, path: null },
        op1: { connected: false, mode: null, path: null }
    },
    // Track last known connected state across page navigations (persisted in sessionStorage)
    lastKnownState: { opz: false, op1: false },

    /**
     * Initialize SSE connection for device status updates
     */
    init: function() {
        // Restore last known state from sessionStorage to avoid showing toast on page navigation
        this.loadLastKnownState();
        this.connect();

        // Reconnect when page becomes visible again
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !this.eventSource) {
                this.connect();
            }
        });

        // Clean up on page unload
        window.addEventListener('beforeunload', () => {
            this.disconnect();
        });
    },

    /**
     * Load last known device state from sessionStorage
     */
    loadLastKnownState: function() {
        try {
            const stored = sessionStorage.getItem('deviceLastKnownState');
            if (stored) {
                this.lastKnownState = JSON.parse(stored);
            }
        } catch (e) {
            console.warn('Failed to load device state from sessionStorage:', e);
        }
    },

    /**
     * Save current device state to sessionStorage
     */
    saveLastKnownState: function() {
        try {
            sessionStorage.setItem('deviceLastKnownState', JSON.stringify(this.lastKnownState));
        } catch (e) {
            console.warn('Failed to save device state to sessionStorage:', e);
        }
    },

    /**
     * Connect to SSE endpoint
     */
    connect: function() {
        if (this.eventSource) {
            return; // Already connected
        }

        try {
            this.eventSource = new EventSource('/device-events');

            this.eventSource.onopen = () => {
                console.log('Device status SSE connected');
            };

            this.eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleEvent(data);
                } catch (e) {
                    console.error('Error parsing SSE data:', e);
                }
            };

            this.eventSource.onerror = (error) => {
                console.warn('Device status SSE error, reconnecting...', error);
                this.disconnect();
                // Reconnect after delay
                setTimeout(() => this.connect(), 3000);
            };

        } catch (e) {
            console.error('Failed to create EventSource:', e);
        }
    },

    /**
     * Disconnect from SSE
     */
    disconnect: function() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    },

    /**
     * Handle incoming SSE event
     */
    handleEvent: function(data) {
        if (data.type === 'device_status') {
            this.handleDeviceStatus(data);
        }
    },

    /**
     * Handle device status update
     */
    handleDeviceStatus: function(data) {
        const { device, device_name, connected, path, usb_detected, mode } = data;

        // Update current state for click handling
        this.currentState[device] = { connected, mode, path };

        // Check if this is a genuine state change by comparing to persisted state
        const wasConnected = this.lastKnownState[device];
        const isNewConnection = connected && !wasConnected;
        const isDisconnection = !connected && wasConnected;

        // Track initial state for first-load logic (to know when both devices reported)
        if (this.isFirstLoad) {
            const prevState = this.initialDevices[device];
            this.initialDevices[device] = connected;

            // Only show toast on first load if device is NEWLY connected
            // (not already known from previous page navigation)
            if (prevState === null && isNewConnection) {
                this.showConnectToast(device, device_name, path, mode);
            }

            // Mark first load complete after both devices reported
            if (this.initialDevices.opz !== null && this.initialDevices.op1 !== null) {
                this.isFirstLoad = false;
            }

            // Update last known state and persist it
            this.lastKnownState[device] = connected;
            this.saveLastKnownState();

            // Update sidebar even on first load
            if (typeof updateDeviceSidebar === 'function') {
                updateDeviceSidebar(device, connected, path, mode);
            }
            return;
        }

        // After first load, show toasts for actual status changes
        if (isNewConnection) {
            this.showConnectToast(device, device_name, path, mode);
        } else if (isDisconnection) {
            if (usb_detected) {
                // USB detected but mount path not found
                this.showMountErrorToast(device_name);
            } else {
                // Fully disconnected
                this.showDisconnectToast(device_name);
            }
        }

        // Update last known state and persist it
        this.lastKnownState[device] = connected;
        this.saveLastKnownState();

        // Update sidebar if on home page
        if (typeof updateDeviceSidebar === 'function') {
            updateDeviceSidebar(device, connected, path, mode);
        }

        // Auto-expand sidebar when device connects
        if (isNewConnection && typeof expandSidebar === 'function') {
            expandSidebar();
        }
    },

    /**
     * Show toast when device connects
     */
    showConnectToast: function(device, deviceName, path, mode) {
        let message, toastElement;

        if (mode === 'storage' && path) {
            // Storage mode with mount path
            message = `Mounted at ${path}`;
            toastElement = toast.success(
                message,
                `Device connected: ${deviceName}`,
                { duration: 5000 }
            );

            // Make toast clickable to open device directory
            if (toastElement) {
                toastElement.style.cursor = 'pointer';
                toastElement.addEventListener('click', (e) => {
                    // Don't trigger if clicking close button
                    if (e.target.closest('.toast-close')) return;
                    this.openDeviceDirectory(device);
                    toast.dismiss(toastElement);
                });
            }
        } else if (mode === 'upgrade') {
            // Upgrade mode - device is in firmware update mode
            message = 'Device is in upgrade mode';
            toastElement = toast.warning(
                message,
                `Device connected: ${deviceName}`,
                { duration: 5000 }
            );
        } else if (mode === 'other') {
            // Non-storage mode (MIDI/normal) - no disk access
            message = 'Switch to disk mode for file access';
            toastElement = toast.info(
                message,
                `Device connected: ${deviceName}`,
                { duration: 5000 }
            );
        } else if (mode === 'storage' && !path) {
            // Storage mode but mount path not found yet
            message = 'Mounting...';
            toastElement = toast.info(
                message,
                `Device connected: ${deviceName}`,
                { duration: 3000 }
            );
        }
    },

    /**
     * Show toast when device disconnects
     */
    showDisconnectToast: function(deviceName) {
        toast.info(
            `${deviceName} has been disconnected`,
            'Device disconnected'
        );
    },

    /**
     * Show toast when USB detected but mount failed
     */
    showMountErrorToast: function(deviceName) {
        toast.warning(
            `${deviceName} detected but mount path could not be determined`,
            'Mount Error'
        );
    },

    /**
     * Open device directory in system file manager
     * If device is not in storage mode, shows instructions modal instead
     */
    openDeviceDirectory: function(device) {
        const state = this.currentState[device];
        const deviceName = device === 'op1' ? 'OP-1' : 'OP-Z';

        // If not connected or not in storage mode with path, show instructions
        if (!state.connected || state.mode !== 'storage' || !state.path) {
            this.showDiskModeModal(device, deviceName, state.connected, state.mode);
            return;
        }

        // Device is in storage mode with valid path - open directory
        fetch(`/open-device-directory?device=${device}`)
            .then(res => res.json())
            .catch(err => console.error('Error opening device directory:', err));
    },

    /**
     * Show modal with instructions for switching to disk mode
     */
    showDiskModeModal: function(device, deviceName, connected, mode) {
        const modalEl = document.getElementById('diskModeModal');
        const titleEl = document.getElementById('diskModeModalTitle');
        const bodyEl = document.getElementById('diskModeModalBody');

        if (!modalEl || !titleEl || !bodyEl) return;

        titleEl.textContent = `${deviceName} - Switch to Disk Mode`;

        let instructions = '';

        if (!connected) {
            instructions = `
                <p>Your <strong>${deviceName}</strong> is not currently connected.</p>
                <p>Connect your device via USB and switch it to disk mode to access files.</p>
            `;
        } else if (mode === 'upgrade') {
            titleEl.textContent = `${deviceName} - Upgrade Mode`;
            instructions = `
                <p>Your <strong>${deviceName}</strong> is in <strong>upgrade mode</strong>.</p>
                <p>This mode is used for firmware updates. To access samples, you need to switch to disk mode:</p>
            `;
        } else if (mode === 'other') {
            instructions = `
                <p>Your <strong>${deviceName}</strong> is connected but not in disk mode.</p>
                <p>To access files, you need to switch to disk mode:</p>
            `;
        } else {
            instructions = `
                <p>Your <strong>${deviceName}</strong> is connected but the mount path is not available yet.</p>
                <p>Please wait a moment for the device to finish mounting.</p>
            `;
        }

        // Add device-specific instructions
        if (device === 'opz') {
            instructions += `
                <div class="disk-mode-steps">
                    <h6>OP-Z Disk Mode:</h6>
                    <ol>
                        <li>Power off the device</li>
                        <li>Hold <strong>TRACK</strong> and turn the yellow volume knob power on the device</li>
                        <li>Wait for the OP-Z to switch modes and connect</li>
                    </ol>
                </div>
            `;
        } else if (device === 'op1') {
            instructions += `
                <div class="disk-mode-steps">
                    <h6>OP-1 Disk Mode:</h6>
                    <ol>
                        <li>Press <strong>COM</strong> (shift + mixer)</li>
                        <li>Press the track 3 button to select <strong>disk</strong></li>
                        <li>Wait for the OP-1 to switch modes and reconnect</li>
                    </ol>
                </div>
            `;
        }

        bodyEl.innerHTML = instructions;
        new bootstrap.Modal(modalEl).show();
    },

    /**
     * Get current device status from server
     */
    getStatus: async function() {
        try {
            const response = await fetch('/device-status');
            const status = await response.json();

            // Update current state for click handling
            if (status) {
                if (status.opz) {
                    this.currentState.opz = {
                        connected: status.opz.connected,
                        mode: status.opz.mode,
                        path: status.opz.path
                    };
                }
                if (status.op1) {
                    this.currentState.op1 = {
                        connected: status.op1.connected,
                        mode: status.op1.mode,
                        path: status.op1.path
                    };
                }
            }

            return status;
        } catch (e) {
            console.error('Error fetching device status:', e);
            return null;
        }
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    deviceStatus.init();
});
