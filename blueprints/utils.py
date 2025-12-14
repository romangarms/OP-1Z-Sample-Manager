"""Shared utilities for blueprint modules."""
import os


# OP-1 Tape Constants
TAPE_TRACK_IDS = [1, 2, 3, 4]
ALBUM_SIDE_IDS = ["a", "b"]
TAPE_DIR = "tape"
ALBUM_DIR = "album"
TAPE_TRACK_PREFIX = "track_"
ALBUM_SIDE_PREFIX = "side_"
AIFF_EXTENSION = ".aif"
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
