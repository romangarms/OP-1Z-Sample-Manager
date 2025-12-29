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

    /**
     * Initialize SSE connection for device status updates
     */
    init: function() {
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

        // Track initial state to avoid duplicate toasts on first load
        if (this.isFirstLoad) {
            const prevState = this.initialDevices[device];
            this.initialDevices[device] = connected;

            // Only show toast on first load if device is connected
            if (prevState === null && connected) {
                this.showConnectToast(device, device_name, path, mode);
            }

            // Mark first load complete after both devices reported
            if (this.initialDevices.opz !== null && this.initialDevices.op1 !== null) {
                this.isFirstLoad = false;
            }

            // Update sidebar even on first load
            if (typeof updateDeviceSidebar === 'function') {
                updateDeviceSidebar(device, connected, path, mode);
            }
            return;
        }

        // After first load, show toasts for status changes
        if (connected) {
            this.showConnectToast(device, device_name, path, mode);
        } else if (usb_detected && !connected) {
            // USB detected but mount path not found
            this.showMountErrorToast(device_name);
        } else {
            // Fully disconnected
            this.showDisconnectToast(device_name);
        }

        // Update sidebar if on home page
        if (typeof updateDeviceSidebar === 'function') {
            updateDeviceSidebar(device, connected, path, mode);
        }

        // Auto-expand sidebar when device connects
        if (connected && typeof expandSidebar === 'function') {
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
     */
    openDeviceDirectory: function(device) {
        fetch(`/open-device-directory?device=${device}`)
            .then(res => res.json())
            .catch(err => console.error('Error opening device directory:', err));
    },

    /**
     * Get current device status from server
     */
    getStatus: async function() {
        try {
            const response = await fetch('/device-status');
            return await response.json();
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
