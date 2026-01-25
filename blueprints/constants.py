"""
Application Constants

Centralized constants for config setting names, directory paths, file names,
and other magic strings used throughout the application.
"""


# ===================================================================
# Config Setting Names
# ===================================================================

class Config:
    """Configuration setting names used in the application config dictionary."""

    # General settings
    SELECTED_DEVICE = "SELECTED_DEVICE"
    DEVELOPER_MODE = "DEVELOPER_MODE"
    WORKING_DIRECTORY = "WORKING_DIRECTORY"
    LOGGER_LEVEL = "LOGGER_LEVEL"

    # Device mount path config keys
    class MountPaths:
        """Device mount path configuration keys."""
        OPZ = "OPZ_MOUNT_PATH"
        OP1 = "OP1_MOUNT_PATH"
        OPZ_DETECTED = "OPZ_DETECTED_PATH"
        OP1_DETECTED = "OP1_DETECTED_PATH"


# ===================================================================
# Directory Names
# ===================================================================

class Directories:
    """Directory names for OP-Z and OP-1 devices."""

    class OPZ:
        """OP-Z specific directories."""
        SAMPLEPACKS = "samplepacks"
        CONFIG = "config"

    class OP1:
        """OP-1 specific directories."""
        DRUM = "drum"
        SYNTH = "synth"
        TAPE = "tape"
        ALBUM = "album"
        USER = "user"  # Read-only directory on OP-1


# ===================================================================
# File Names and Prefixes
# ===================================================================

class Files:
    """File names and prefixes for device-specific files."""

    class OPZ:
        """OP-Z config file names."""
        class Config:
            """OP-Z configuration files."""
            GENERAL = "general.json"
            MIDI = "midi.json"
            DMX = "dmx.json"

    class OP1:
        """OP-1 file prefixes."""
        TAPE_TRACK_PREFIX = "track_"
        ALBUM_SIDE_PREFIX = "side_"


# ===================================================================
# File Extensions
# ===================================================================

class Extensions:
    """File extensions used throughout the application."""
    AIF = ".aif"
    AIFF = ".aiff"
    JSON = ".json"


# ===================================================================
# Sample Type Constants
# ===================================================================

class SampleTypes:
    """Sample type identifiers."""
    DRUM = "drum"
    SYNTH = "synth"


# ===================================================================
# OP-1 Tape and Album Constants
# ===================================================================

class TapeAlbum:
    """OP-1 tape and album track/side identifiers."""
    TRACK_IDS = [1, 2, 3, 4]
    SIDE_IDS = ["a", "b"]
