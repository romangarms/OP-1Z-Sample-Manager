"""
OP-1 Tape Export Module

Handles tape track and album playback/export functionality.
"""

import os
import subprocess
import shutil
import tempfile
from flask import Blueprint, request, jsonify, current_app, send_file
from .config import get_config_setting, get_device_mount_path
from .utils import (
    TAPE_TRACK_IDS,
    ALBUM_SIDE_IDS,
    TAPE_DIR,
    ALBUM_DIR,
    TAPE_TRACK_PREFIX,
    ALBUM_SIDE_PREFIX,
    AIFF_EXTENSION,
    EXPORT_TAPE_PREFIX,
    EXPORT_ALBUM_PREFIX,
    get_unique_filepath,
)

# Create Blueprint
tape_export_bp = Blueprint('tape_export', __name__)

# Cache directory for converted audio files
AUDIO_CACHE_DIR = os.path.join(tempfile.gettempdir(), "opz_sample_manager_audio_cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


def get_op1_mount_path():
    """Get and validate OP-1 mount path."""
    path = get_device_mount_path("op1")
    if not path or not os.path.exists(path):
        return None
    return path


def find_ffmpeg():
    """Find ffmpeg, checking common installation paths."""
    # Check config first
    configured = get_config_setting("FFMPEG_PATH")
    if configured and os.path.isfile(configured):
        return configured

    # Common locations on macOS/Linux
    common_paths = [
        "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
        "/usr/local/bin/ffmpeg",      # Intel Homebrew
        "/usr/bin/ffmpeg",            # System
    ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    # Fallback to PATH (works when running from terminal)
    if shutil.which("ffmpeg"):
        return "ffmpeg"

    return None


def get_source_path(track_type, track_id, mount_path):
    """Get the source AIFF file path for a track."""
    if track_type == "tape":
        return os.path.join(mount_path, TAPE_DIR, f"{TAPE_TRACK_PREFIX}{track_id}{AIFF_EXTENSION}")
    elif track_type == "album":
        return os.path.join(mount_path, ALBUM_DIR, f"{ALBUM_SIDE_PREFIX}{track_id}{AIFF_EXTENSION}")
    return None


def get_cache_path(track_type, track_id):
    """Get the cache file path for a converted track."""
    return os.path.join(AUDIO_CACHE_DIR, f"{track_type}_{track_id}.wav")


def needs_conversion(source_path, cache_path):
    """Check if source file needs to be converted (cache missing or stale)."""
    if not os.path.exists(source_path):
        return False  # Source doesn't exist
    if not os.path.exists(cache_path):
        return True  # Cache doesn't exist
    return os.path.getmtime(source_path) > os.path.getmtime(cache_path)


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg is not found on the system."""
    pass


def convert_to_wav(source_path, cache_path):
    """Convert AIFF to WAV using FFmpeg."""
    ffmpeg_path = find_ffmpeg()

    if not ffmpeg_path:
        raise FFmpegNotFoundError("FFmpeg not found. Please install FFmpeg to use this feature.")

    subprocess.run(
        [ffmpeg_path, "-y", "-i", source_path, cache_path],
        capture_output=True,
        check=True
    )


@tape_export_bp.route("/api/tape/tracks")
def get_tape_tracks():
    """Get tape track file information."""
    mount_path = get_op1_mount_path()

    if not mount_path:
        return jsonify({"error": "OP-1 not mounted"}), 400

    tape_path = os.path.join(mount_path, TAPE_DIR)
    tracks = []

    for i in TAPE_TRACK_IDS:
        filename = f"{TAPE_TRACK_PREFIX}{i}{AIFF_EXTENSION}"
        track_file = os.path.join(tape_path, filename)
        if os.path.exists(track_file):
            tracks.append({
                "id": i,
                "name": f"Track {i}",
                "filename": filename,
                "path": track_file,
                "size": os.path.getsize(track_file),
                "exists": True
            })
        else:
            tracks.append({
                "id": i,
                "name": f"Track {i}",
                "filename": filename,
                "exists": False
            })

    return jsonify({"tracks": tracks, "tape_path": tape_path})


@tape_export_bp.route("/api/tape/album")
def get_album_tracks():
    """Get album side file information."""
    mount_path = get_op1_mount_path()

    if not mount_path:
        return jsonify({"error": "OP-1 not mounted"}), 400

    album_path = os.path.join(mount_path, ALBUM_DIR)
    sides = []

    for side in ALBUM_SIDE_IDS:
        filename = f"{ALBUM_SIDE_PREFIX}{side}{AIFF_EXTENSION}"
        side_file = os.path.join(album_path, filename)
        if os.path.exists(side_file):
            sides.append({
                "id": side,
                "name": f"Side {side.upper()}",
                "filename": filename,
                "path": side_file,
                "size": os.path.getsize(side_file),
                "exists": True
            })
        else:
            sides.append({
                "id": side,
                "name": f"Side {side.upper()}",
                "filename": filename,
                "exists": False
            })

    return jsonify({"sides": sides, "album_path": album_path})


@tape_export_bp.route("/api/tape/prepare", methods=["POST"])
def prepare_audio():
    """
    Pre-convert all AIFF files to WAV for browser playback.
    Returns progress info so frontend can show a loading bar.
    """
    mount_path = get_op1_mount_path()

    if not mount_path:
        return jsonify({"error": "OP-1 not mounted"}), 400

    # Build list of all files to potentially convert
    files_to_check = []

    # Tape tracks
    for i in TAPE_TRACK_IDS:
        files_to_check.append(("tape", str(i)))

    # Album sides
    for side in ALBUM_SIDE_IDS:
        files_to_check.append(("album", side))

    # Check which files need conversion
    files_to_convert = []
    already_cached = []
    not_found = []

    for track_type, track_id in files_to_check:
        source_path = get_source_path(track_type, track_id, mount_path)
        cache_path = get_cache_path(track_type, track_id)

        if not os.path.exists(source_path):
            not_found.append(f"{track_type}_{track_id}")
        elif needs_conversion(source_path, cache_path):
            files_to_convert.append((track_type, track_id, source_path, cache_path))
        else:
            already_cached.append(f"{track_type}_{track_id}")

    # Convert files that need it
    converted = []
    errors = []

    for track_type, track_id, source_path, cache_path in files_to_convert:
        try:
            convert_to_wav(source_path, cache_path)
            converted.append(f"{track_type}_{track_id}")
        except FFmpegNotFoundError as e:
            current_app.logger.error(f"FFmpeg not found: {e}")
            return jsonify({"error": str(e)}), 500
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            current_app.logger.error(f"FFmpeg error converting {track_type}_{track_id}: {error_msg}")
            errors.append(f"{track_type}_{track_id}")

    return jsonify({
        "status": "ready" if not errors else "partial",
        "converted": converted,
        "cached": already_cached,
        "not_found": not_found,
        "errors": errors,
        "total_files": len(files_to_check),
        "ready_files": len(converted) + len(already_cached)
    })


@tape_export_bp.route("/api/tape/audio/<track_type>/<track_id>")
def serve_tape_audio(track_type, track_id):
    """Serve cached WAV audio files for browser playback."""
    mount_path = get_op1_mount_path()

    if not mount_path:
        return jsonify({"error": "OP-1 not configured"}), 400

    # Validate track type and ID
    if track_type == "tape":
        if track_id not in [str(i) for i in TAPE_TRACK_IDS]:
            return jsonify({"error": "Invalid track ID"}), 400
    elif track_type == "album":
        if track_id not in ALBUM_SIDE_IDS:
            return jsonify({"error": "Invalid side ID"}), 400
    else:
        return jsonify({"error": "Invalid track type"}), 400

    # Check if source exists
    source_path = get_source_path(track_type, track_id, mount_path)
    if not os.path.exists(source_path):
        return jsonify({"error": "File not found"}), 404

    # Get cached file
    cache_path = get_cache_path(track_type, track_id)

    # If cache doesn't exist, convert now (fallback)
    if not os.path.exists(cache_path):
        try:
            convert_to_wav(source_path, cache_path)
        except FFmpegNotFoundError as e:
            current_app.logger.error(f"FFmpeg not found: {e}")
            return jsonify({"error": str(e)}), 500
        except subprocess.CalledProcessError as e:
            current_app.logger.error(f"FFmpeg conversion error: {e.stderr.decode() if e.stderr else str(e)}")
            return jsonify({"error": "Audio conversion failed"}), 500

    return send_file(cache_path, mimetype="audio/wav")


@tape_export_bp.route("/api/tape/export", methods=["POST"])
def export_tape():
    """Export tape tracks or album sides to Downloads folder."""
    data = request.get_json()
    export_type = data.get("type")  # "tape" or "album"

    mount_path = get_op1_mount_path()

    if not mount_path:
        return jsonify({"error": "OP-1 not mounted"}), 400

    downloads_path = os.path.expanduser("~/Downloads")

    if not os.path.exists(downloads_path):
        return jsonify({"error": "Downloads folder not found"}), 400

    exported_files = []
    errors = []

    if export_type == "tape":
        source_dir = os.path.join(mount_path, TAPE_DIR)
        for i in TAPE_TRACK_IDS:
            src = os.path.join(source_dir, f"{TAPE_TRACK_PREFIX}{i}{AIFF_EXTENSION}")
            if os.path.exists(src):
                base_dst = os.path.join(downloads_path, f"{EXPORT_TAPE_PREFIX}{i}{AIFF_EXTENSION}")
                dst = get_unique_filepath(base_dst)
                try:
                    shutil.copy2(src, dst)
                    exported_files.append(os.path.basename(dst))
                except Exception as e:
                    errors.append(f"{TAPE_TRACK_PREFIX}{i}{AIFF_EXTENSION}: {str(e)}")

    elif export_type == "album":
        source_dir = os.path.join(mount_path, ALBUM_DIR)
        for side in ALBUM_SIDE_IDS:
            src = os.path.join(source_dir, f"{ALBUM_SIDE_PREFIX}{side}{AIFF_EXTENSION}")
            if os.path.exists(src):
                base_dst = os.path.join(downloads_path, f"{EXPORT_ALBUM_PREFIX}{side}{AIFF_EXTENSION}")
                dst = get_unique_filepath(base_dst)
                try:
                    shutil.copy2(src, dst)
                    exported_files.append(os.path.basename(dst))
                except Exception as e:
                    errors.append(f"{ALBUM_SIDE_PREFIX}{side}{AIFF_EXTENSION}: {str(e)}")
    else:
        return jsonify({"error": "Invalid export type"}), 400

    return jsonify({
        "status": "success" if not errors else "partial",
        "exported": exported_files,
        "errors": errors,
        "destination": downloads_path
    })
