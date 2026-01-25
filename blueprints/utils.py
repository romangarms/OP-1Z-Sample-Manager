"""Shared utilities for blueprint modules."""
import os
import sys
from .constants import (
    TAPE_TRACK_IDS,
    ALBUM_SIDE_IDS,
    TAPE_DIR,
    ALBUM_DIR,
    TAPE_TRACK_PREFIX,
    ALBUM_SIDE_PREFIX,
    AIFF_EXTENSION,
)

# Export tape constants for backward compatibility
EXPORT_TAPE_PREFIX = "op1_tape_track_"
EXPORT_ALBUM_PREFIX = "op1_album_side_"


def get_unique_filepath(base_path: str) -> str:
    """Return unique filepath by appending counter if file exists.

    If base_path doesn't exist, returns it unchanged.
    If it exists, appends _1, _2, etc. before the extension until unique.

    Example:
        get_unique_filepath("/downloads/track.aif")
        -> "/downloads/track.aif" (if doesn't exist)
        -> "/downloads/track_1.aif" (if track.aif exists)
    """
    if not os.path.exists(base_path):
        return base_path

    base, ext = os.path.splitext(base_path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def get_ffmpeg_path():
    """Get the path to the FFMPEG executable.

    When running as a bundled app (frozen), returns the path to the bundled
    FFMPEG binary. In development mode, returns 'ffmpeg' to use system PATH.

    Returns:
        str: Path to FFMPEG executable
    """
    if getattr(sys, 'frozen', False):
        # Running as bundled app
        if sys.platform == 'darwin':
            return os.path.join(sys._MEIPASS, 'bin', 'ffmpeg')
        else:  # Windows
            return os.path.join(sys._MEIPASS, 'bin', 'ffmpeg.exe')
    else:
        # Development mode - use system ffmpeg
        return 'ffmpeg'


def run_ffmpeg(args, **kwargs):
    """Run FFMPEG with the correct path and platform-specific settings.

    Args:
        args: List of arguments to pass to FFMPEG (without the ffmpeg command itself)
        **kwargs: Additional arguments to pass to subprocess.run()

    Returns:
        subprocess.CompletedProcess result
    """
    import subprocess

    ffmpeg_path = get_ffmpeg_path()
    cmd = [ffmpeg_path] + args

    # Hide console window on Windows
    if sys.platform == 'win32':
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)

    return subprocess.run(cmd, **kwargs)
