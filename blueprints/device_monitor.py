"""
Device Monitor Blueprint

Handles USB device detection for OP-Z and OP-1 devices,
mount path resolution, and Server-Sent Events for real-time updates.
"""

import os
import sys
import time
import threading
import subprocess
from queue import Queue
from flask import Blueprint, Response, jsonify, current_app, request
from .config import get_config_setting, set_config_setting
from .devices import OP_Z, OP_1, get_device_by_id
from .constants import (
    CONFIG_DEVELOPER_MODE,
    CONFIG_OPZ_MOUNT_PATH,
    CONFIG_OP1_MOUNT_PATH,
    CONFIG_OPZ_DETECTED_PATH,
    CONFIG_OP1_DETECTED_PATH,
    DIR_SAMPLEPACKS,
    DIR_DRUM,
    DIR_SYNTH,
)

# Create Blueprint
device_monitor_bp = Blueprint('device_monitor', __name__)

# Teenage Engineering USB Identifiers (decimal values) - now imported from devices module
TE_VENDOR_ID = OP_Z.usb_vendor_id  # 0x2367 - same for both devices
OPZ_PRODUCT_ID = OP_Z.usb_product_ids[0]  # 0x000c - OP-Z (both normal and disk mode use same ID)
OP1_PRODUCT_ID = OP_1.usb_product_ids[0]  # 0x0002 - USB Storage mode
OP1_PRODUCT_ID_OTHER = OP_1.usb_product_ids[1]  # 0x0004 - Normal/MIDI mode (no disk access)

# USB class identifiers for distinguishing device modes
USB_CLASS_STORAGE = "USBSTOR"  # Mass storage class
USB_CLASS_MEDIA = "MEDIA"      # Audio/MIDI class (normal mode)

# Files/folders that indicate upgrade mode (not normal disk mode)
OPZ_UPGRADE_MODE_MARKERS = ["how_to_upgrade.txt", "systeminfo"]


def normalize_usb_id(value):
    """Convert USB ID from any format (int, hex string, decimal string) to int.

    On Windows, USB vendor/product IDs are reported as 4-character hex strings
    without the '0x' prefix (e.g., '2367' for 0x2367). We detect this pattern
    and parse as hex.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip().lower()
        if not value:
            return None
        # Try hex format (with 0x prefix)
        if value.startswith('0x'):
            return int(value, 16)
        # USB IDs on Windows are typically 4-char hex strings (e.g., '2367', '000c')
        # If it's exactly 4 chars and valid hex, treat as hex
        if len(value) == 4:
            try:
                return int(value, 16)
            except ValueError:
                pass
        # Try as decimal string
        try:
            return int(value)
        except ValueError:
            # Last resort: try as hex without prefix
            try:
                return int(value, 16)
            except ValueError:
                return None
    return None

# Device status tracking
# mode: "storage" (disk accessible), "other" (MIDI/normal mode), "standby" (connected but off), or None
device_status = {
    "opz": {"connected": False, "path": None, "usb_detected": False, "mode": None},
    "op1": {"connected": False, "path": None, "usb_detected": False, "mode": None}
}
device_status_lock = threading.Lock()

# SSE event queue for broadcasting updates to clients
sse_clients = []
sse_clients_lock = threading.Lock()

# USB Monitor instance (initialized on startup)
usb_monitor = None
monitor_thread = None


def validate_device_folder_structure(device, mount_path):
    """
    Validate that the provided path contains the expected device folder structure.
    Copied from sample_manager.py to avoid circular imports.
    """
    SAMPLE_CATEGORIES = [
        "1-kick", "2-snare", "3-perc", "4-fx",
        "5-bass", "6-lead", "7-arpeggio", "8-chord"
    ]

    device_obj = get_device_by_id(device)
    device_name = device_obj.name if device_obj else ("OP-1" if device == "op1" else "OP-Z")

    if not mount_path:
        return False, f"Please connect your {device_name} and try again. If it isn't being detected, go to Utility Settings, enable developer mode, and select the device path."

    if not os.path.exists(mount_path):
        return False, f"{device_name} mount path does not exist: {mount_path}"

    if device == "op1":
        # OP-1: Check for drum/ and synth/ directories
        drum_path = os.path.join(mount_path, DIR_DRUM)
        synth_path = os.path.join(mount_path, DIR_SYNTH)

        if not os.path.exists(drum_path) or not os.path.isdir(drum_path):
            return False, "Invalid OP-1 folder: 'drum' directory not found."

        if not os.path.exists(synth_path) or not os.path.isdir(synth_path):
            return False, "Invalid OP-1 folder: 'synth' directory not found."
    else:
        # OP-Z: Check for samplepacks/ directory with category folders
        samplepacks_path = os.path.join(mount_path, DIR_SAMPLEPACKS)
        if not os.path.exists(samplepacks_path):
            return False, "Invalid OP-Z folder: 'samplepacks' directory not found."

        if not os.path.isdir(samplepacks_path):
            return False, "Invalid OP-Z folder: 'samplepacks' exists but is not a directory."

        # Check if at least some expected category folders exist
        missing_categories = []
        for category in SAMPLE_CATEGORIES:
            category_path = os.path.join(samplepacks_path, category)
            if not os.path.exists(category_path):
                missing_categories.append(category)

        # If all categories are missing, it's probably not an OP-Z folder
        if len(missing_categories) == len(SAMPLE_CATEGORIES):
            return False, "Invalid OP-Z folder: No sample category folders found."

    return True, None


def check_opz_upgrade_mode(path):
    """Check if an OP-Z mount path is in upgrade mode.

    Upgrade mode is detected by the presence of how_to_upgrade.txt and/or
    the systeminfo folder, which are present instead of the samplepacks folder.

    Returns:
        True if in upgrade mode, False otherwise
    """
    if not path or not os.path.exists(path):
        return False

    # Check for upgrade mode markers
    for marker in OPZ_UPGRADE_MODE_MARKERS:
        marker_path = os.path.join(path, marker)
        if os.path.exists(marker_path):
            return True

    return False


def find_device_mount_macos(device):
    """Scan /Volumes for a valid OP-Z or OP-1 mount on macOS.

    Returns:
        tuple: (path, mode) where mode is "storage" or "upgrade", or (None, None) if not found
    """
    volumes_path = "/Volumes"
    if not os.path.exists(volumes_path):
        return None, None

    for volume in os.listdir(volumes_path):
        path = os.path.join(volumes_path, volume)
        if os.path.isdir(path):
            # For OP-Z, check for upgrade mode first
            if device == "opz" and check_opz_upgrade_mode(path):
                return path, "upgrade"

            is_valid, _ = validate_device_folder_structure(device, path)
            if is_valid:
                return path, "storage"
    return None, None


def find_device_mount_windows(device):
    """Scan drive letters for a valid OP-Z or OP-1 mount on Windows.

    Returns:
        tuple: (path, mode) where mode is "storage" or "upgrade", or (None, None) if not found
    """
    import string
    for letter in string.ascii_uppercase:
        path = f"{letter}:\\"
        if os.path.exists(path):
            # For OP-Z, check for upgrade mode first
            if device == "opz" and check_opz_upgrade_mode(path):
                return path, "upgrade"

            is_valid, _ = validate_device_folder_structure(device, path)
            if is_valid:
                return path, "storage"
    return None, None


def find_device_mount(device):
    """Find device mount path based on current OS.

    Returns:
        tuple: (path, mode) where mode is "storage" or "upgrade", or (None, None) if not found
    """
    if sys.platform == "darwin":
        return find_device_mount_macos(device)
    elif sys.platform == "win32":
        return find_device_mount_windows(device)
    return None, None


def broadcast_sse_event(event_type, data):
    """Broadcast an SSE event to all connected clients."""
    import json
    event_data = json.dumps({"type": event_type, **data})
    message = f"data: {event_data}\n\n"

    with sse_clients_lock:
        # Create a copy to iterate safely
        clients_copy = sse_clients.copy()
        for queue in clients_copy:
            try:
                queue.put(message)
            except Exception:
                # Client queue might be closed
                pass


def update_device_status(device, connected, path=None, usb_detected=False, mode=None):
    """Update device status and broadcast SSE event.

    Args:
        device: "opz" or "op1"
        connected: True if device is connected
        path: Mount path (only for storage mode)
        usb_detected: True if USB device was detected
        mode: "storage" (disk accessible), "other" (MIDI/normal), or None
    """
    with device_status_lock:
        old_status = device_status[device].copy()
        device_status[device] = {
            "connected": connected,
            "path": path,
            "usb_detected": usb_detected,
            "mode": mode
        }
        new_status = device_status[device].copy()

    # Only broadcast if status changed
    if old_status != new_status:
        device_obj = get_device_by_id(device)
        device_name = device_obj.name if device_obj else ("OP-1" if device == "op1" else "OP-Z")
        print(f"Broadcasting SSE: {device_name} connected={connected}, path={path}, mode={mode}")
        broadcast_sse_event("device_status", {
            "device": device,
            "device_name": device_name,
            "connected": connected,
            "path": path,
            "usb_detected": usb_detected,
            "mode": mode
        })

        # Update config if not in developer mode
        if not get_config_setting(CONFIG_DEVELOPER_MODE, False):
            if connected and path and mode == "storage":
                config_key = CONFIG_OPZ_DETECTED_PATH if device == "opz" else CONFIG_OP1_DETECTED_PATH
                set_config_setting(config_key, path)
            elif not connected:
                config_key = CONFIG_OPZ_DETECTED_PATH if device == "opz" else CONFIG_OP1_DETECTED_PATH
                set_config_setting(config_key, "")


def on_usb_connect(device_id, device_info):
    """Callback when a USB device is connected."""
    try:
        # Debug: log what we receive
        print(f"USB Connect - device_id: {device_id}, device_info: {device_info}")

        # Get vendor and product IDs (try multiple possible key names)
        vendor_id = normalize_usb_id(
            device_info.get("ID_VENDOR_ID") or
            device_info.get("idVendor") or
            device_info.get("vendor_id")
        )
        product_id = normalize_usb_id(
            device_info.get("ID_MODEL_ID") or
            device_info.get("idProduct") or
            device_info.get("product_id")
        )

        # Get USB class to distinguish between storage and audio/MIDI modes
        usb_class = device_info.get("ID_USB_CLASS_FROM_DATABASE", "")

        print(f"Normalized IDs - vendor: {vendor_id}, product: {product_id}, class: {usb_class}")

        # Check if it's a Teenage Engineering device
        if vendor_id != TE_VENDOR_ID:
            return

        # Determine device type and mode
        device = None
        mode = None

        if product_id == OPZ_PRODUCT_ID:
            device = "opz"
            # OP-Z uses the same product ID for both modes, distinguish by USB class
            # - MEDIA class = Normal/MIDI mode (device is ON)
            # - Other class without mount = Standby mode (device is OFF but connected)
            # - Other class with mount = Storage/disk mode
            if usb_class == USB_CLASS_MEDIA:
                mode = "other"  # Normal/MIDI mode - no disk access
            else:
                mode = "pending_storage"  # Will be resolved to "storage" or "standby"
        elif product_id == OP1_PRODUCT_ID:
            device = "op1"
            mode = "storage"
        elif product_id == OP1_PRODUCT_ID_OTHER:
            device = "op1"
            mode = "other"  # Normal/MIDI mode - no disk access
        else:
            print(f"Unknown TE product ID: {product_id}")
            return

        print(f"Detected Teenage Engineering {device.upper()} in {mode} mode")

        if mode == "storage" or mode == "pending_storage":
            # Storage mode - try to find mount path
            # Wait a bit for the device to mount
            time.sleep(1.5)

            mount_path, detected_mode = find_device_mount(device)

            if mount_path:
                print(f"Found mount path: {mount_path} (mode: {detected_mode})")
                update_device_status(device, connected=True, path=mount_path, usb_detected=True, mode=detected_mode)
            elif mode == "pending_storage":
                # OP-Z: No mount path found - device is likely off (standby mode)
                # Start polling but set initial state to standby
                print(f"No mount path for {device}, device appears to be in standby mode")
                update_device_status(device, connected=True, path=None, usb_detected=True, mode="standby")
                poll_for_mount_path(device)
            else:
                # OP-1 or other: USB detected but mount path not found yet - start polling
                print(f"Mount path not found for {device}, starting background polling...")
                update_device_status(device, connected=True, path=None, usb_detected=True, mode="storage")
                poll_for_mount_path(device)
        else:
            # Non-storage mode (MIDI/normal) - no disk access
            print(f"{device.upper()} connected in non-storage mode")
            update_device_status(device, connected=True, path=None, usb_detected=True, mode="other")

    except Exception as e:
        print(f"Error in on_usb_connect: {e}")
        import traceback
        traceback.print_exc()


def on_usb_disconnect(device_id, device_info):
    """Callback when a USB device is disconnected."""
    try:
        # Debug: log what we receive
        print(f"USB Disconnect - device_id: {device_id}, device_info: {device_info}")

        # Get vendor and product IDs (try multiple possible key names)
        vendor_id = normalize_usb_id(
            device_info.get("ID_VENDOR_ID") or
            device_info.get("idVendor") or
            device_info.get("vendor_id")
        )
        product_id = normalize_usb_id(
            device_info.get("ID_MODEL_ID") or
            device_info.get("idProduct") or
            device_info.get("product_id")
        )

        # Check if it's a Teenage Engineering device
        if vendor_id != TE_VENDOR_ID:
            return

        # Determine device type
        if product_id == OPZ_PRODUCT_ID:
            device = "opz"
        elif product_id == OP1_PRODUCT_ID or product_id == OP1_PRODUCT_ID_OTHER:
            device = "op1"
        else:
            return

        print(f"Disconnected Teenage Engineering {device.upper()}")
        update_device_status(device, connected=False, path=None, usb_detected=False, mode=None)

    except Exception as e:
        print(f"Error in on_usb_disconnect: {e}")
        import traceback
        traceback.print_exc()


def poll_for_mount_path(device, max_attempts=30, interval=1.0):
    """Poll for mount path in a background thread.

    Args:
        device: "opz" or "op1"
        max_attempts: Maximum number of polling attempts (default 30 = 30 seconds)
        interval: Seconds between attempts
    """
    def poll():
        for attempt in range(max_attempts):
            # Check if device is still connected and waiting for mount
            with device_status_lock:
                status = device_status[device]
                if not status["connected"] or status["path"] is not None:
                    # Device disconnected or path already found
                    return

            mount_path, detected_mode = find_device_mount(device)
            if mount_path:
                print(f"Found mount path on attempt {attempt + 1}: {mount_path} (mode: {detected_mode})")
                update_device_status(device, connected=True, path=mount_path, usb_detected=True, mode=detected_mode)
                return

            time.sleep(interval)

        print(f"Mount path polling timed out for {device} after {max_attempts} attempts")

    thread = threading.Thread(target=poll, daemon=True)
    thread.start()


def scan_for_connected_devices():
    """Scan for already-connected devices on startup."""
    print("Scanning for connected devices...")

    # First check for devices in storage mode (with mount paths)
    for device in ["opz", "op1"]:
        mount_path, detected_mode = find_device_mount(device)
        print(f"  {device}: mount_path={mount_path}, mode={detected_mode}")
        if mount_path:
            update_device_status(device, connected=True, path=mount_path, usb_detected=True, mode=detected_mode)

    # Also scan for USB devices in normal/MIDI mode (no mount path)
    try:
        from usbmonitor import USBMonitor
        monitor = USBMonitor()
        devices = monitor.get_available_devices()

        for device_id, device_info in devices.items():
            vendor_id = normalize_usb_id(device_info.get("ID_VENDOR_ID"))
            product_id = normalize_usb_id(device_info.get("ID_MODEL_ID"))
            usb_class = device_info.get("ID_USB_CLASS_FROM_DATABASE", "")

            if vendor_id != TE_VENDOR_ID:
                continue

            # Check for OP-Z
            if product_id == OPZ_PRODUCT_ID:
                with device_status_lock:
                    already_connected = device_status["opz"]["connected"]
                if not already_connected:
                    if usb_class == USB_CLASS_MEDIA:
                        # OP-Z in normal mode (device is ON)
                        print(f"Found OP-Z in normal mode on startup")
                        update_device_status("opz", connected=True, path=None, usb_detected=True, mode="other")
                    else:
                        # OP-Z with non-MEDIA class and no mount = standby mode (device is OFF)
                        print(f"Found OP-Z in standby mode on startup (connected but off)")
                        update_device_status("opz", connected=True, path=None, usb_detected=True, mode="standby")

            # Check for OP-1 in normal/MIDI mode
            elif product_id == OP1_PRODUCT_ID_OTHER:
                with device_status_lock:
                    already_connected = device_status["op1"]["connected"]
                if not already_connected:
                    print(f"Found OP-1 in normal mode on startup")
                    update_device_status("op1", connected=True, path=None, usb_detected=True, mode="other")

    except ImportError:
        pass  # USBMonitor not available
    except Exception as e:
        print(f"Error scanning for USB devices: {e}")


def start_usb_monitoring():
    """Start the USB monitoring thread."""
    global usb_monitor, monitor_thread

    try:
        from usbmonitor import USBMonitor
        from usbmonitor.attributes import ID_VENDOR_ID, ID_MODEL_ID

        usb_monitor = USBMonitor()

        # Set up callbacks
        usb_monitor.start_monitoring(
            on_connect=on_usb_connect,
            on_disconnect=on_usb_disconnect
        )

        print("USB monitoring started")

    except ImportError as e:
        print(f"USBMonitor not available: {e}")
        print("USB device monitoring disabled. Install usb-monitor package for auto-detection.")
    except Exception as e:
        print(f"Error starting USB monitoring: {e}")


def stop_usb_monitoring():
    """Stop the USB monitoring."""
    global usb_monitor

    if usb_monitor:
        try:
            usb_monitor.stop_monitoring()
            print("USB monitoring stopped")
        except Exception as e:
            print(f"Error stopping USB monitoring: {e}")


device_monitor_initialized = False
device_monitor_init_lock = threading.Lock()


def initialize_device_monitor():
    """Initialize device monitoring (called lazily when homepage loads)."""
    global device_monitor_initialized

    with device_monitor_init_lock:
        if device_monitor_initialized:
            return  # Already initialized
        device_monitor_initialized = True

    print("Initializing device monitor...")

    # Scan for devices already connected
    scan_for_connected_devices()

    # Start USB monitoring for hot-plug detection
    start_usb_monitoring()


# Flask Routes

@device_monitor_bp.route('/device-status')
def get_device_status():
    """Get current status of both devices."""
    # Initialize device monitoring lazily on first request
    initialize_device_monitor()

    with device_status_lock:
        status = {
            "opz": device_status["opz"].copy(),
            "op1": device_status["op1"].copy()
        }

    # Add device display names
    status["opz"]["device_name"] = OP_Z.name
    status["op1"]["device_name"] = OP_1.name

    return jsonify(status)


@device_monitor_bp.route('/device-events')
def device_events():
    """SSE endpoint for real-time device status updates."""
    # Initialize device monitoring lazily on first request
    initialize_device_monitor()

    def generate():
        # Create a queue for this client
        client_queue = Queue()

        with sse_clients_lock:
            sse_clients.append(client_queue)

        try:
            # Send initial status
            with device_status_lock:
                import json
                for device in ["opz", "op1"]:
                    status = device_status[device].copy()
                    device_obj = get_device_by_id(device)
                    device_name = device_obj.name if device_obj else device.upper()
                    event_data = json.dumps({
                        "type": "device_status",
                        "device": device,
                        "device_name": device_name,
                        **status
                    })
                    yield f"data: {event_data}\n\n"

            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for new events with timeout
                    message = client_queue.get(timeout=30)
                    yield message
                except Exception:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

        except GeneratorExit:
            pass
        finally:
            with sse_clients_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@device_monitor_bp.route('/open-device-directory')
def open_device_directory():
    """Open the device directory in the system file manager."""
    device = request.args.get("device", "opz")

    with device_status_lock:
        path = device_status.get(device, {}).get("path")

    if not path:
        # Try to get from config
        if get_config_setting(CONFIG_DEVELOPER_MODE, False):
            config_key = CONFIG_OPZ_MOUNT_PATH if device == "opz" else CONFIG_OP1_MOUNT_PATH
        else:
            config_key = CONFIG_OPZ_DETECTED_PATH if device == "opz" else CONFIG_OP1_DETECTED_PATH
        path = get_config_setting(config_key)

    if not path or not os.path.exists(path):
        return jsonify({"error": "Device path not found"}), 404

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@device_monitor_bp.route('/refresh-device-scan')
def refresh_device_scan():
    """Manually trigger a device scan."""
    scan_for_connected_devices()

    with device_status_lock:
        status = {
            "opz": device_status["opz"].copy(),
            "op1": device_status["op1"].copy()
        }

    return jsonify(status)
