import sys
import subprocess
from flask import Blueprint, jsonify, current_app

# Create Blueprint for dialog routes
dialog_bp = Blueprint('dialog', __name__)


def run_dialog_macos(mode):
    """Use native macOS dialogs via osascript."""
    if mode == "folder":
        script = 'POSIX path of (choose folder with prompt "Select a folder")'
    elif mode == "file":
        script = 'POSIX path of (choose file with prompt "Select a file")'
    elif mode == "multi":
        script = '''
set selectedFiles to choose file with prompt "Select files" with multiple selections allowed
set output to ""
repeat with f in selectedFiles
    set output to output & POSIX path of f & linefeed
end repeat
return output
'''
    elif mode == "save":
        script = 'POSIX path of (choose file name with prompt "Save as")'
    else:
        return jsonify({"error": f"Unknown mode: {mode}"}), 400

    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            # User cancelled the dialog
            return jsonify({"error": "No selection made"}), 400

        output = result.stdout.strip()

        if mode == "multi":
            paths = [line.strip() for line in output.splitlines() if line.strip()]
            current_app.logger.debug("Got multiple paths: %s", paths)
            if paths:
                return jsonify({"paths": paths})
            else:
                return jsonify({"error": "No files selected"}), 400

        # Single path case (file, folder, save)
        if output:
            current_app.logger.debug("Got path of: %s from user.", output)
            return jsonify({"path": output})
        else:
            return jsonify({"error": "No selection made"}), 400

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Dialog timed out"}), 408
    except Exception as e:
        current_app.logger.error("Exception in run_dialog_macos: %s", e, exc_info=True)
        return jsonify({"error": "An internal error has occurred."}), 500


def run_dialog(mode):
    """Run a file/folder selection dialog."""
    try:
        if sys.platform == 'darwin':
            return run_dialog_macos(mode)
        else:
            # Fallback for non-macOS (would need different implementation)
            return jsonify({"error": "File dialogs not supported on this platform in bundled app"}), 501
    except Exception as e:
        current_app.logger.error("Exception in run_dialog: %s", e, exc_info=True)
        return jsonify({"error": "An internal error has occurred."}), 500

# Flask routes to run dialogs for file/folder selection

@dialog_bp.route("/get-user-file-path")
def get_user_file():
    current_app.logger.info("Getting file path from user")
    return run_dialog("file")

@dialog_bp.route("/get-user-folder-path")
def get_user_folder():
    current_app.logger.info("Getting Folder Path from user")
    return run_dialog("folder")

@dialog_bp.route("/get-save-location-path")
def get_save_location():
    current_app.logger.info("Get save location path - redundant?")
    return run_dialog("save")

@dialog_bp.route("/get-user-multiple-file-paths")
def get_user_multiple_files():
    current_app.logger.info("Getting multiple file paths from user")
    return run_dialog("multi")
