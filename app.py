import sys
import os
import webbrowser
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from blueprints.migration import migrator
from blueprints.config import load_config, run_all_config_tasks, get_config_setting, set_config_setting, config_bp
from blueprints.sample_converter import sample_converter_bp
from blueprints.sample_manager import sample_manager_bp
from blueprints.tape_export import tape_export_bp
from blueprints.dialogs import dialog_bp
from blueprints.backup import backup_bp
from blueprints.device_monitor import device_monitor_bp, initialize_device_monitor
from blueprints.update_checker import update_checker_bp


# Get base path for PyInstaller or normal execution
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# setup
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app)  # Enable CORS for all routes

# Register blueprints
app.register_blueprint(sample_converter_bp)
app.register_blueprint(sample_manager_bp)
app.register_blueprint(tape_export_bp)
app.register_blueprint(config_bp)
app.register_blueprint(dialog_bp)
app.register_blueprint(backup_bp)
app.register_blueprint(device_monitor_bp)
app.register_blueprint(update_checker_bp)

# run before server startup at the end of this file
def app_startup_tasks():
    # config
    load_config()

    # Run migrations - this relies on config being loaded, but will run before anything can use them.
    successfull_migration = migrator.run_migrations()
    if not successfull_migration:
        print("Migrations failed - exiting startup.")
        exit(1)
    
    run_all_config_tasks()  # Initialize config settings
    # fetch and set the os config
    set_config_setting("OS", get_os())
    # Note: Device monitoring is initialized lazily when the homepage loads
    # to avoid blocking app startup


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

@app.route("/tapeexport")
def tapeexport():
    return render_template("tapeexport.html")

@app.route("/configeditor")
def configeditor():
    return render_template("configeditor.html")

@app.route("/utilitysettings")
def utilitysettings():
    return render_template("utilitysettings.html")

@app.route("/backup")
def backup():
    return render_template("backup.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/licenses")
def licenses():
    """Serve the third-party licenses page."""
    licenses_path = os.path.join(BASE_DIR, 'THIRD_PARTY_LICENSES.md')
    try:
        with open(licenses_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template("licenses.html", content=content)
    except FileNotFoundError:
        return render_template("licenses.html", content="Licenses file not found.")

@app.route("/changelog")
def changelog():
    """Serve the latest changelog page."""
    changelog_path = os.path.join(BASE_DIR, 'LATEST_CHANGELOG.md')
    try:
        with open(changelog_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return render_template("changelog.html", content=content)
    except FileNotFoundError:
        return render_template("changelog.html", content="Latest changelog not found.")

@app.route("/open-external-link")
def open_external_link():
    url = request.args.get("url")

    # Validate URL
    if not url or not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL"}), 400

    try:
        webbrowser.open(url)
        return jsonify({"status": "opened"}), 200
    except Exception as e:
        app.logger.error(f"Error opening external link: {e}")
        return jsonify({"error": "Failed to open link"}), 500

if __name__ == "__main__":
    app_startup_tasks()
    app.run(debug=False)
