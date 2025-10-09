import os
import sys
import subprocess
import uuid
from flask import Blueprint, request, jsonify, current_app
from config import get_config_setting

# Create Blueprint
sample_converter_bp = Blueprint('sample_converter', __name__)

# Constants
UPLOAD_FOLDER = "uploads"
CONVERTED_FOLDER = "converted"
SYN_CONVERTED_FOLDER = "converted/synth"
DRUM_CONVERTED_FOLDER = "converted/drum"

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)
os.makedirs(SYN_CONVERTED_FOLDER, exist_ok=True)
os.makedirs(DRUM_CONVERTED_FOLDER, exist_ok=True)

# Helper function to convert audio files to OP-Z compatible format
def convert_audio_file(input_path, output_path, sample_type):
    """
    Convert an audio file to OP-Z compatible AIFF format.

    Args:
        input_path: Path to the input audio file
        output_path: Path where the converted file should be saved
        sample_type: Either "drum" (12s max) or "synth" (6s max)

    Returns:
        True if conversion succeeds

    Raises:
        Exception if conversion fails
    """
    max_duration = 12 if sample_type == "drum" else 6
    ffmpeg_path = get_config_setting("FFMPEG_PATH", "ffmpeg")

    ffmpeg_cmd = [
        ffmpeg_path,
        "-i",
        input_path,
        "-af",
        "loudnorm",  # normalize audio
        "-t",
        str(max_duration),  # trim to correct duration
        "-ac",
        "1",  # force mono
        "-ar",
        "44100",  # sample rate 44.1k
        "-sample_fmt",
        "s16",  # 16-bit samples
        output_path,
    ]

    subprocess.run(ffmpeg_cmd, check=True)
    return True

@sample_converter_bp.route("/convert", methods=["POST"])
def convert_sample():
    file = request.files["file"]
    sample_type = request.form["type"]

    if file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    # Save uploaded file temporarily
    input_path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + "_" + file.filename)
    file.save(input_path)

    # Set output filename (for sample converter page, saves to converted/ folder)
    output_filename = os.path.splitext(os.path.basename(file.filename))[0] + ".aiff"
    output_path = os.path.join(CONVERTED_FOLDER, sample_type, output_filename)

    try:
        # Use shared conversion function
        convert_audio_file(input_path, output_path, sample_type)
        return jsonify({"message": f"Converted to {output_filename} successfully."})
    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"Subprocess Error: {e}")
        return jsonify({"error": "Conversion failed"}), 500
    except Exception as e:
        current_app.logger.error("Unknown error while attempting to run the FFMPEG subprocess.")
        if os.name == "nt":
            current_app.logger.warning("Windows detected. This error is often due to a misconfigured FFMPEG path. Double check it.")
        current_app.logger.error(f"Error details: {e}")
        return jsonify({"error": "Conversion failed"}), 500
    finally:
        # Clean up input file
        if os.path.exists(input_path):
            os.remove(input_path)
            current_app.logger.info("Removed unconverted uploaded file")
        else:
            current_app.logger.warning("Did not find uploaded file and it was not removed")

# open the sample converter's converted folder in the file explorer
@sample_converter_bp.route("/open-explorer", methods=["POST"])
def open_explorer():
    folder_path = os.path.join(os.path.abspath("."), CONVERTED_FOLDER)
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", folder_path])
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", folder_path])
        else:  # Linux and others
            subprocess.Popen(["xdg-open", folder_path])

        return jsonify({"status": "opened", "path": folder_path}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
