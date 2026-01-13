import os
import sys
import json
import logging
import subprocess
from flask import Blueprint, request, jsonify, current_app

# Create Blueprint for config routes
config_bp = Blueprint('config', __name__)

# Project name constant - change this when renaming the project
PROJECT_NAME = "OP-1Z-Sample-Manager"


def get_config_dir():
    """Get the appropriate config directory for the current OS."""
    if sys.platform == 'darwin':
        config_dir = os.path.expanduser('~/Library/Application Support/OP-1Z Sample Manager')
    elif sys.platform == 'win32':
        config_dir = os.path.join(os.environ.get('APPDATA', ''), 'OP-1Z Sample Manager')
    else:
        config_dir = os.path.expanduser('~/.config/OP-1Z Sample Manager')
    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_path():
    """Get the full path to the config file."""
    return os.path.join(get_config_dir(), 'op-1z_sm_config.json')


CONFIG_PATH = get_config_path()
app_config = {}


def get_default_working_directory(*, project_name):
    """Return default working directory: ~/Documents/<project_name>/"""
    if sys.platform == 'win32':
        # On Windows, use registry or USERPROFILE to find actual Documents folder
        # This handles OneDrive redirection and custom locations
        try:
            import winreg
            # Query Windows registry for the actual Documents folder location
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
            )
            documents = winreg.QueryValueEx(key, "Personal")[0]
            winreg.CloseKey(key)
        except Exception:
            # Fallback to USERPROFILE if registry fails
            documents = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Documents')
    else:
        # On macOS and Linux, ~/Documents works correctly
        documents = os.path.expanduser("~/Documents")

    return os.path.join(documents, project_name)

# Utility to read JSON from a file and return it as a Python object
def read_json_from_path(path):
    """Read JSON from a file and return its contents as a Python object."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r") as f:
        return json.load(f)

# Utility to write a Python object to a file as JSON
def write_json_to_path(path, data):
    """Write the provided data to the given path as formatted JSON."""
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

# set the flask logger level
def set_logger_level(level_name: str):
    level_name = level_name.upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Invalid log level: {level_name}")
    # Set root logger level - Flask's logger will inherit this
    logging.getLogger().setLevel(level)

# if any of the config things need to do anything extra (ie set logging level) it happens here
# this is run after each time a config setting is changed via set-config-setting

def run_config_task(changed_key):

    match changed_key:
        case "LOGGER_LEVEL":
            set_logger_level(app_config.get("LOGGER_LEVEL", "INFO"))
        case _:
            None
            # could log something here

def run_all_config_tasks():

    for key in app_config.keys():
        run_config_task(key)




# Function to load the configuration from a JSON file
def load_config():
    if os.path.exists(CONFIG_PATH):
        loaded = read_json_from_path(CONFIG_PATH)
        app_config.clear()
        app_config.update(loaded)
    return app_config

# Function to save the configuration to a JSON file
def save_config():
    write_json_to_path(CONFIG_PATH, app_config)

# Function to reset configuration (clears file and memory)
def reset_config():
    write_json_to_path(CONFIG_PATH, {})
    app_config.clear()
    return app_config

# Get a config setting with an optional default
def get_config_setting(key, default=None):
    # Special case: return default working directory if not set
    if key == "WORKING_DIRECTORY":
        value = app_config.get(key)
        if not value:
            return get_default_working_directory(PROJECT_NAME)
        return value

    # Special case: return default selected device if not set
    if key == "SELECTED_DEVICE":
        value = app_config.get(key)
        if not value:
            return "opz"  # Default to OP-Z
        return value

    # Special case: DEVELOPER_MODE defaults to False
    if key == "DEVELOPER_MODE":
        value = app_config.get(key)
        if value is None:
            return False
        return value

    value = app_config.get(key, default)
    # If the value exists but is an empty string, use the default
    if value == "" and default is not None:
        return default
    return value


def get_device_mount_path(device):
    """
    Get the effective mount path for a device.

    In developer mode, returns the manually configured path.
    Otherwise, returns the auto-detected path.

    Args:
        device: "opz" or "op1"

    Returns:
        Mount path string or empty string if not set
    """
    if get_config_setting("DEVELOPER_MODE", False):
        # Use manual path in developer mode
        key = "OPZ_MOUNT_PATH" if device == "opz" else "OP1_MOUNT_PATH"
    else:
        # Use auto-detected path in normal mode
        key = "OPZ_DETECTED_PATH" if device == "opz" else "OP1_DETECTED_PATH"

    return get_config_setting(key, "")

# Set a config setting and with option to not save it
def set_config_setting(key, value, save=True):
    app_config.get(key)
    app_config[key] = value
    if save:
        save_config()

# Optional: delete a config key, with option to not save
def delete_config_setting(key, save=True):
    if key in app_config:
        app_config.pop(key)
        if save:
            save_config()
        return True
    return False

# Flask routes for config management
# needs the _route suffix because the function names above already exist

@config_bp.route('/set-config-setting', methods=['POST'])
def set_config_setting_route():
    try:
        data = request.json
        current_app.logger.debug("Incoming JSON data: " + str(data))

        config_option = data.get("config_option")
        config_value = data.get("config_value")

        if config_option is None or config_value is None:
            return jsonify({"error": "Missing 'config_option' or 'config_value'"}), 400

        set_config_setting(config_option, config_value)
        run_config_task(config_option)
        return jsonify({"success": True})

    except Exception:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

@config_bp.route('/get-config-setting')
def get_config_setting_route():
    config_option = request.args.get("config_option")

    if config_option is None:
        current_app.logger.warning("Tried to get config setting without any config option sent.")
        return jsonify({"error": "Missing 'config_option' parameter"}), 400

    config_value = get_config_setting(config_option, "")
    if config_value == "":
        current_app.logger.warning("Did not find a config entry for " + str(config_option) + " or it is an empty string.")
    current_app.logger.debug("Returning Config value of " + str(config_value) + " for " + str(config_option))
    return jsonify({"success": True, "config_value": config_value})

@config_bp.route('/remove-config-setting', methods=['POST'])
def remove_config_setting_route():
    data = request.json
    config_option = data.get("config_option")

    if config_option is None:
        return jsonify({"error": "Missing 'config_option'"}), 400

    if delete_config_setting(config_option):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Config option not found"}), 404

@config_bp.route('/reset-config', methods=['POST'])
def reset_config_flask():
    delete_config_setting("OPZ_MOUNT_PATH", save=False)
    reset_config()
    return jsonify({"success": True, "message": "Configuration reset successfully"})


@config_bp.route('/open-config-in-editor', methods=['POST'])
def open_config_in_editor():
    """Open the config file in the system's default text editor."""
    config_path = get_config_path()

    # Ensure the config file exists
    if not os.path.exists(config_path):
        # Create an empty config file if it doesn't exist
        write_json_to_path(config_path, {})

    try:
        if sys.platform.startswith("win"):
            os.startfile(config_path)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", config_path])
        else:  # Linux and others
            subprocess.Popen(["xdg-open", config_path])

        return jsonify({"status": "opened", "path": config_path}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Flask routes to edit config files on the OP-Z device
@config_bp.route('/get-config/general')
def get_general_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    general_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'general.json')
    return jsonify(read_json_from_path(general_json_path))

@config_bp.route('/get-config/midi')
def get_midi_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    midi_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'midi.json')
    return jsonify(read_json_from_path(midi_json_path))

@config_bp.route('/save-config/general', methods=['POST'])
def save_general_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    general_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'general.json')
    data = request.get_json()
    write_json_to_path(general_json_path, data)
    return '', 204

@config_bp.route('/save-config/midi', methods=['POST'])
def save_midi_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    midi_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'midi.json')
    data = request.get_json()
    write_json_to_path(midi_json_path, data)
    return '', 204

@config_bp.route('/get-config/dmx')
def get_dmx_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    dmx_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'dmx.json')
    if not os.path.exists(dmx_json_path):
        return jsonify({"error": "dmx.json not found"}), 404
    with open(dmx_json_path, 'r') as f:
        content = f.read()
    return jsonify({"content": content})

@config_bp.route('/save-config/dmx', methods=['POST'])
def save_dmx_config():
    OPZ_MOUNT_PATH = get_device_mount_path("opz")
    dmx_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'dmx.json')
    data = request.get_json()
    content = data.get('content', '')
    with open(dmx_json_path, 'w') as f:
        f.write(content)
    return '', 204
