"""
Backup & Restore Module

Handles backup and restore functionality for OP-1 and OP-Z devices.
"""

import os
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from .config import get_config_setting, get_device_mount_path, read_json_from_path, write_json_to_path
from .utils import (
    TAPE_TRACK_IDS,
    TAPE_DIR,
    TAPE_TRACK_PREFIX,
    AIFF_EXTENSION,
)

# Create Blueprint
backup_bp = Blueprint('backup', __name__)

# Cache directory for backup preview audio
BACKUP_AUDIO_CACHE_DIR = os.path.join(tempfile.gettempdir(), "opz_sample_manager_backup_cache")
os.makedirs(BACKUP_AUDIO_CACHE_DIR, exist_ok=True)

# Files/directories to ignore during backup
IGNORE_PATTERNS = ['.DS_Store', '.Spotlight-V100', '.Trashes', '._*']


def get_backups_base_path(device):
    """Get the base path for backups: WORKING_DIRECTORY/backups/{device}/"""
    working_dir = get_config_setting("WORKING_DIRECTORY")
    return os.path.join(working_dir, "backups", device)


def get_backup_path(device, timestamp):
    """Get the full path to a specific backup folder."""
    return os.path.join(get_backups_base_path(device), timestamp)


def load_backup_metadata(backup_path):
    """Load metadata.json from a backup folder."""
    metadata_path = os.path.join(backup_path, "metadata.json")
    if os.path.exists(metadata_path):
        try:
            return read_json_from_path(metadata_path)
        except Exception:
            return None
    return None


def save_backup_metadata(backup_path, metadata):
    """Save metadata.json to a backup folder."""
    metadata_path = os.path.join(backup_path, "metadata.json")
    write_json_to_path(metadata_path, metadata)


def get_folder_size(path):
    """Calculate total size of a folder in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except OSError:
                pass
    return total_size


def count_files(path):
    """Count total number of files in a folder."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(path):
        count += len(filenames)
    return count


def should_ignore(name):
    """Check if a file/folder should be ignored during backup."""
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith('._') and name.startswith('._'):
            return True
        if name == pattern:
            return True
    return False


def copy_tree_filtered(src, dst):
    """Copy directory tree, filtering out ignored files."""
    os.makedirs(dst, exist_ok=True)

    for item in os.listdir(src):
        if should_ignore(item):
            continue

        src_path = os.path.join(src, item)
        dst_path = os.path.join(dst, item)

        if os.path.isdir(src_path):
            copy_tree_filtered(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)


def generate_timestamp():
    """Generate a timestamp string for backup folder names."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_timestamp_for_display(timestamp):
    """Convert timestamp string to readable format."""
    try:
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp


# Preview audio helpers (reused from tape_export patterns)
def get_backup_cache_path(device, timestamp, track_id):
    """Get the cache file path for a backup preview track."""
    return os.path.join(BACKUP_AUDIO_CACHE_DIR, f"backup_{device}_{timestamp}_{track_id}.wav")


def get_backup_source_path(backup_path, track_id):
    """Get the source AIFF file path for a tape track in a backup."""
    return os.path.join(backup_path, TAPE_DIR, f"{TAPE_TRACK_PREFIX}{track_id}{AIFF_EXTENSION}")


def needs_conversion(source_path, cache_path):
    """Check if source file needs to be converted (cache missing or stale)."""
    if not os.path.exists(source_path):
        return False
    if not os.path.exists(cache_path):
        return True
    return os.path.getmtime(source_path) > os.path.getmtime(cache_path)


def convert_to_wav(source_path, cache_path):
    """Convert AIFF to WAV using FFmpeg."""
    ffmpeg_path = get_config_setting("FFMPEG_PATH", "ffmpeg")
    subprocess.run(
        [ffmpeg_path, "-y", "-i", source_path, cache_path],
        capture_output=True,
        check=True
    )


# API Routes

@backup_bp.route("/api/backup/list/<device>")
def list_backups(device):
    """List all backups for a device with metadata."""
    if device not in ["op1", "opz"]:
        return jsonify({"error": "Invalid device"}), 400

    backups_path = get_backups_base_path(device)

    if not os.path.exists(backups_path):
        return jsonify({"backups": []})

    backups = []

    try:
        for folder_name in os.listdir(backups_path):
            folder_path = os.path.join(backups_path, folder_name)

            if not os.path.isdir(folder_path):
                continue

            # Load metadata
            metadata = load_backup_metadata(folder_path)

            # Build backup info
            backup_info = {
                "timestamp": folder_name,
                "name": metadata.get("name", folder_name) if metadata else folder_name,
                "created": metadata.get("created", format_timestamp_for_display(folder_name)) if metadata else format_timestamp_for_display(folder_name),
                "path": folder_path,
                "size": get_folder_size(folder_path),
                "file_count": count_files(folder_path)
            }

            backups.append(backup_info)

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

    except Exception as e:
        current_app.logger.error(f"Error listing backups: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"backups": backups})


@backup_bp.route("/api/backup/create", methods=["POST"])
def create_backup():
    """Create a new backup (copies all files from device to backup folder)."""
    data = request.get_json()
    device = data.get("device")
    name = data.get("name", "")  # Optional display name

    if device not in ["op1", "opz"]:
        return jsonify({"error": "Invalid device"}), 400

    mount_path = get_device_mount_path(device)

    if not mount_path or not os.path.exists(mount_path):
        return jsonify({"error": f"{device.upper()} not mounted or path not configured"}), 400

    # Generate timestamp for folder name
    timestamp = generate_timestamp()
    backup_path = get_backup_path(device, timestamp)

    # Create backup directory
    os.makedirs(backup_path, exist_ok=True)

    try:
        # Copy all files from device to backup
        copy_tree_filtered(mount_path, backup_path)

        # Create metadata
        metadata = {
            "name": name if name else timestamp,
            "created": datetime.now().isoformat(),
            "device": device
        }
        save_backup_metadata(backup_path, metadata)

        return jsonify({
            "status": "success",
            "timestamp": timestamp,
            "path": backup_path,
            "files_copied": count_files(backup_path),
            "size": get_folder_size(backup_path)
        })

    except Exception as e:
        current_app.logger.error(f"Error creating backup: {e}")
        # Clean up on failure
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path, ignore_errors=True)
        return jsonify({"error": str(e)}), 500


@backup_bp.route("/api/backup/restore", methods=["POST"])
def restore_backup():
    """Restore a backup (wipes device and copies backup files to device)."""
    data = request.get_json()
    device = data.get("device")
    timestamp = data.get("timestamp")

    if device not in ["op1", "opz"]:
        return jsonify({"error": "Invalid device"}), 400

    if not timestamp:
        return jsonify({"error": "Missing timestamp"}), 400

    mount_path = get_device_mount_path(device)
    backup_path = get_backup_path(device, timestamp)

    if not mount_path or not os.path.exists(mount_path):
        return jsonify({"error": f"{device.upper()} not mounted or path not configured"}), 400

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    try:
        # Clear device contents (but keep the mount point)
        for item in os.listdir(mount_path):
            if should_ignore(item):
                continue
            item_path = os.path.join(mount_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        # Copy backup contents to device (excluding metadata.json)
        for item in os.listdir(backup_path):
            if item == "metadata.json" or should_ignore(item):
                continue

            src_path = os.path.join(backup_path, item)
            dst_path = os.path.join(mount_path, item)

            if os.path.isdir(src_path):
                copy_tree_filtered(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

        return jsonify({
            "status": "success",
            "files_restored": count_files(mount_path)
        })

    except Exception as e:
        current_app.logger.error(f"Error restoring backup: {e}")
        return jsonify({"error": str(e)}), 500


@backup_bp.route("/api/backup/rename", methods=["POST"])
def rename_backup():
    """Update the display name in a backup's metadata.json."""
    data = request.get_json()
    device = data.get("device")
    timestamp = data.get("timestamp")
    name = data.get("name")

    if device not in ["op1", "opz"]:
        return jsonify({"error": "Invalid device"}), 400

    if not timestamp or not name:
        return jsonify({"error": "Missing timestamp or name"}), 400

    backup_path = get_backup_path(device, timestamp)

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    try:
        metadata = load_backup_metadata(backup_path)
        if metadata is None:
            metadata = {
                "created": format_timestamp_for_display(timestamp),
                "device": device
            }
        metadata["name"] = name
        save_backup_metadata(backup_path, metadata)

        return jsonify({"status": "success"})

    except Exception as e:
        current_app.logger.error(f"Error renaming backup: {e}")
        return jsonify({"error": str(e)}), 500


@backup_bp.route("/api/backup/delete", methods=["DELETE"])
def delete_backup():
    """Delete a backup folder."""
    data = request.get_json()
    device = data.get("device")
    timestamp = data.get("timestamp")

    if device not in ["op1", "opz"]:
        return jsonify({"error": "Invalid device"}), 400

    if not timestamp:
        return jsonify({"error": "Missing timestamp"}), 400

    backup_path = get_backup_path(device, timestamp)

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    try:
        shutil.rmtree(backup_path)
        return jsonify({"status": "success"})

    except Exception as e:
        current_app.logger.error(f"Error deleting backup: {e}")
        return jsonify({"error": str(e)}), 500


# OP-1 Preview Audio Routes

@backup_bp.route("/api/backup/preview/prepare/<device>/<timestamp>", methods=["POST"])
def prepare_backup_preview(device, timestamp):
    """Convert backup tape AIFF files to WAV for browser playback."""
    if device != "op1":
        return jsonify({"error": "Preview only available for OP-1"}), 400

    backup_path = get_backup_path(device, timestamp)

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    tracks = []

    for track_id in TAPE_TRACK_IDS:
        source_path = get_backup_source_path(backup_path, track_id)
        cache_path = get_backup_cache_path(device, timestamp, track_id)

        track_info = {
            "id": track_id,
            "exists": os.path.exists(source_path)
        }

        if track_info["exists"]:
            try:
                if needs_conversion(source_path, cache_path):
                    convert_to_wav(source_path, cache_path)
                track_info["ready"] = True
            except subprocess.CalledProcessError as e:
                current_app.logger.error(f"FFmpeg error: {e}")
                track_info["ready"] = False
                track_info["error"] = "Conversion failed"

        tracks.append(track_info)

    return jsonify({
        "status": "ready",
        "tracks": tracks
    })


@backup_bp.route("/api/backup/preview/audio/<device>/<timestamp>/<int:track_id>")
def serve_backup_audio(device, timestamp, track_id):
    """Serve cached WAV audio files from backup for browser playback."""
    if device != "op1":
        return jsonify({"error": "Preview only available for OP-1"}), 400

    if track_id not in TAPE_TRACK_IDS:
        return jsonify({"error": "Invalid track ID"}), 400

    backup_path = get_backup_path(device, timestamp)

    if not os.path.exists(backup_path):
        return jsonify({"error": "Backup not found"}), 404

    source_path = get_backup_source_path(backup_path, track_id)
    cache_path = get_backup_cache_path(device, timestamp, track_id)

    if not os.path.exists(source_path):
        return jsonify({"error": "Track not found"}), 404

    # Convert if needed
    if not os.path.exists(cache_path):
        try:
            convert_to_wav(source_path, cache_path)
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"FFmpeg conversion error: {e}")
            return jsonify({"error": "Audio conversion failed"}), 500

    return send_file(cache_path, mimetype="audio/wav")


@backup_bp.route("/api/backup/open-folder")
def open_backups_folder():
    """Open the backups folder in the file explorer."""
    import platform

    backups_base = os.path.join(get_config_setting("WORKING_DIRECTORY"), "backups")

    # Create the folder if it doesn't exist
    os.makedirs(backups_base, exist_ok=True)

    try:
        system = platform.system()

        if system == "Windows":
            os.startfile(backups_base)
        elif system == "Darwin":  # macOS
            subprocess.run(["open", backups_base])
        else:  # Linux
            subprocess.run(["xdg-open", backups_base])

        return jsonify({"status": "opened", "path": backups_base})
    except Exception as e:
        current_app.logger.error(f"Error opening backups folder: {e}")
        return jsonify({"error": "Failed to open folder"}), 500
