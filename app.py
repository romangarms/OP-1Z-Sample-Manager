import json
import sys
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from config import (
    load_config,
    save_config,
    reset_config,
    run_config_task,
    run_all_config_tasks,
    get_config_setting,
    set_config_setting,
    delete_config_setting,
    read_json_from_path,
    write_json_to_path
)
from dialog_runner import run_dialog
from sample_converter import sample_converter_bp
from sample_manager import sample_manager_bp

# setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Register blueprints
app.register_blueprint(sample_converter_bp)
app.register_blueprint(sample_manager_bp)

# run before server startup at the end of this file
def app_startup_tasks():
    # config
    load_config()
    run_all_config_tasks()  # Initialize config settings
    # fetch and set the os config
    set_config_setting("OS", get_os())



def get_os():
    if sys.platform.startswith("win"):
        app.logger.info("Detected OS: Windows")
        return "windows"
    elif sys.platform.startswith("darwin"):
        app.logger.info("Detected OS: macOS")
        return "macos"
    else:
        app.logger.info("Detected OS: Linux")
        return "linux"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sampleconverter")
def sampleconverter():
    return render_template("sampleconverter.html")

@app.route("/samplemanager")
def samplemanager():
    return render_template("samplemanager.html")

@app.route("/configeditor")
def configeditor():
    return render_template("configeditor.html")

@app.route("/utilitysettings")
def utilitysettings():
    return render_template("utilitysettings.html")

# Flask routes to run dialogs for file/folder selection

@app.route("/get-user-file-path")
def get_user_file():
    app.logger.info("Getting file path from user")
    return run_dialog("file")

@app.route("/get-user-folder-path")
def get_user_folder():
    app.logger.info("Getting Folder Path from user")
    return run_dialog("folder")

@app.route("/get-save-location-path")
def get_save_location():
    app.logger.info("Get save location path - redundant?")
    return run_dialog("save")

@app.route("/get-user-multiple-file-paths")
def get_user_multiple_files():
    app.logger.info("Getting multiple file paths from user")
    return run_dialog("multi")

# Flask routes to manage config for the sample manager app
# needs the _route because *something*_config_setting already exists in config.py

@app.route('/set-config-setting', methods=['POST'])
def set_config_setting_route():
    try:
        data = request.json
        app.logger.debug("Incoming JSON data: " + str(data))

        config_option = data.get("config_option")
        config_value = data.get("config_value")

        if config_option is None or config_value is None:
            return jsonify({"error": "Missing 'config_option' or 'config_value'"}), 400

        set_config_setting(config_option, config_value)
        run_config_task(config_option)
        return jsonify({"success": True})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500

@app.route('/get-config-setting')
def get_config_setting_route():
    config_option = request.args.get("config_option")

    if config_option is None:
        app.logger.warning("Tried to get config setting without any config option sent.")
        return jsonify({"error": "Missing 'config_option' parameter"}), 400

    config_value = get_config_setting(config_option, "")
    if config_value == "":
        app.logger.warning("Did not find a config entry for " + str(config_option) + " or it is an empty string.")
    app.logger.debug("Returning Config value of " + str(config_value) + " for " + str(config_option))
    return jsonify({"success": True, "config_value": config_value})


@app.route('/remove-config-setting', methods=['POST'])
def remove_config_setting_route():
    data = request.json
    config_option = data.get("config_option")

    if config_option is None:
        return jsonify({"error": "Missing 'config_option'"}), 400

    if delete_config_setting(config_option):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Config option not found"}), 404


# Flask routes to edit config files on the OP-Z
@app.route('/get-config/general')
def get_general_config():
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    general_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'general.json')
    return jsonify(read_json_from_path(general_json_path))

@app.route('/get-config/midi')
def get_midi_config():
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    midi_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'midi.json')
    return jsonify(read_json_from_path(midi_json_path))

@app.route('/save-config/general', methods=['POST'])
def save_general_config():
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    general_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'general.json')
    data = request.get_json()
    write_json_to_path(general_json_path, data)
    return '', 204

@app.route('/save-config/midi', methods=['POST'])
def save_midi_config():
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    midi_json_path = os.path.join(OPZ_MOUNT_PATH, 'config', 'midi.json')
    data = request.get_json()
    write_json_to_path(midi_json_path, data)
    return '', 204

@app.route('/reset-config', methods=['POST'])
def reset_config_flask():
    delete_config_setting("OPZ_MOUNT_PATH", save=False)
    reset_config()
    return jsonify({"success": True, "message": "Configuration reset successfully"})

if __name__ == "__main__":
    app_startup_tasks()
    app.run(debug=False)
