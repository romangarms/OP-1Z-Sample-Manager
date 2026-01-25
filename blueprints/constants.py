"""
Application Constants

Centralized constants for config setting names, directory paths, file names,
and other magic strings used throughout the application.
"""

# ===================================================================
# Config Setting Names
# ===================================================================
# These constants represent keys used in the application config dictionary

CONFIG_SELECTED_DEVICE = "SELECTED_DEVICE"
CONFIG_DEVELOPER_MODE = "DEVELOPER_MODE"
CONFIG_WORKING_DIRECTORY = "WORKING_DIRECTORY"
CONFIG_LOGGER_LEVEL = "LOGGER_LEVEL"

# Device mount path config keys
CONFIG_OPZ_MOUNT_PATH = "OPZ_MOUNT_PATH"
CONFIG_OP1_MOUNT_PATH = "OP1_MOUNT_PATH"
CONFIG_OPZ_DETECTED_PATH = "OPZ_DETECTED_PATH"
CONFIG_OP1_DETECTED_PATH = "OP1_DETECTED_PATH"


# ===================================================================
# Directory Names
# ===================================================================

# OP-Z directories
DIR_SAMPLEPACKS = "samplepacks"
DIR_CONFIG = "config"

# OP-1 directories
DIR_DRUM = "drum"
DIR_SYNTH = "synth"
DIR_TAPE = "tape"
DIR_ALBUM = "album"

# Special directory
DIR_USER = "user"  # Read-only directory on OP-1


# ===================================================================
# File Names and Extensions
# ===================================================================

# OP-Z config files
FILE_GENERAL_JSON = "general.json"
FILE_MIDI_JSON = "midi.json"
FILE_DMX_JSON = "dmx.json"

# OP-1 file prefixes
FILE_TAPE_TRACK_PREFIX = "track_"
FILE_ALBUM_SIDE_PREFIX = "side_"

# File extensions
EXT_AIF = ".aif"
EXT_AIFF = ".aiff"
EXT_JSON = ".json"


# ===================================================================
# Sample Type Constants
# ===================================================================

SAMPLE_TYPE_DRUM = "drum"
SAMPLE_TYPE_SYNTH = "synth"


# ===================================================================
# OP-1 Tape and Album Constants
# ===================================================================

TAPE_TRACK_IDS = [1, 2, 3, 4]
ALBUM_SIDE_IDS = ["a", "b"]

# For backward compatibility with existing code
# Export these alongside the new constants
TAPE_DIR = DIR_TAPE
ALBUM_DIR = DIR_ALBUM
TAPE_TRACK_PREFIX = FILE_TAPE_TRACK_PREFIX
ALBUM_SIDE_PREFIX = FILE_ALBUM_SIDE_PREFIX
AIFF_EXTENSION = EXT_AIF
