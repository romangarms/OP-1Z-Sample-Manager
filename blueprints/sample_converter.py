import os
import sys
import subprocess
import tempfile
import uuid
import shutil
from flask import Blueprint, request, jsonify, current_app
from .config import get_config_setting
from .utils import run_ffmpeg
from .pitch_detection import detect_pitch, find_nearest_a, calculate_pitch_shift_params

# Create Blueprint
sample_converter_bp = Blueprint('sample_converter', __name__)

# Constants
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), "op-1z_sample_manager_uploads")

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_converted_folder():
    """Return converted folder path: WORKING_DIRECTORY/converted/"""
    working_dir = get_config_setting("WORKING_DIRECTORY")
    return os.path.join(working_dir, "converted")


def get_converted_subfolder(sample_type):
    """Return converted subfolder path: WORKING_DIRECTORY/converted/{sample_type}/"""
    return os.path.join(get_converted_folder(), sample_type)

# Helper function to convert audio files to OP-Z / OP-1 compatible format
def convert_audio_file(input_path, output_path, sample_type, auto_pitch=True):
    """
    Convert an audio file to OP-Z / OP-1 compatible AIFF format.

    Args:
        input_path: Path to the input audio file
        output_path: Path where the converted file should be saved
        sample_type: Either "drum" (12s max) or "synth" (6s max)
        auto_pitch: If True, detect and correct pitch to nearest A (synth only)

    Returns:
        dict: Pitch correction info if applied, empty dict otherwise
            {
                "detected_hz": float,
                "target_hz": int,
                "semitones_shift": float
            }

    Raises:
        Exception if conversion fails
    """
    max_duration = 12 if sample_type == "drum" else 6

    # Build filter chain
    filters = []

    # Pitch correction for synth samples
    pitch_info = {}
    if auto_pitch and sample_type == "synth":
        try:
            detected_hz = detect_pitch(input_path)
            if detected_hz:
                target_hz, semitones = find_nearest_a(detected_hz)
                asetrate_ratio, atempo_ratio = calculate_pitch_shift_params(semitones)

                # Add pitch shift filters
                filters.append(f"asetrate=44100*{asetrate_ratio}")
                filters.append(f"atempo={atempo_ratio}")
                filters.append("aresample=44100")

                pitch_info = {
                    "detected_hz": round(detected_hz, 2),
                    "target_hz": target_hz,
                    "semitones_shift": round(semitones, 2)
                }

                current_app.logger.info(f"Pitch correction: {detected_hz:.2f}Hz -> {target_hz}Hz ({semitones:+.2f} semitones)")
            else:
                current_app.logger.warning("Pitch detection failed - skipping pitch correction")
        except Exception as e:
            current_app.logger.warning(f"Pitch detection error: {e} - skipping pitch correction")

    # Always apply normalization
    filters.append("loudnorm")

    # Build FFmpeg command
    filter_chain = ",".join(filters)

    run_ffmpeg([
        "-y",  # overwrite output file without asking
        "-i", input_path,
        "-af", filter_chain,
        "-t", str(max_duration),  # trim to correct duration
        "-ac", "1",  # force mono
        "-ar", "44100",  # sample rate 44.1k
        "-sample_fmt", "s16",  # 16-bit samples
        output_path,
    ], check=True)

    return pitch_info

@sample_converter_bp.route("/convert", methods=["POST"])
def convert_sample():
    file = request.files["file"]
    sample_type = request.form["type"]
    auto_pitch = request.form.get("auto_pitch", "true") == "true"

    if file.filename == "":
        return jsonify({"error": "No file uploaded"}), 400

    # Save uploaded file temporarily
    input_path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + "_" + file.filename)
    file.save(input_path)

    # Set output path using working directory
    output_filename = os.path.splitext(os.path.basename(file.filename))[0] + ".aiff"
    output_dir = get_converted_subfolder(sample_type)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_filename)

    conversion_failed = False
    try:
        # Use shared conversion function
        pitch_info = convert_audio_file(input_path, output_path, sample_type, auto_pitch)

        response = {
            "message": f"Converted to {output_filename} successfully.",
            "pitch_corrected": bool(pitch_info)
        }

        if pitch_info:
            response["pitch_info"] = pitch_info

        return jsonify(response)
    except subprocess.CalledProcessError as e:
        conversion_failed = True
        current_app.logger.error(f"Subprocess Error: {e}")
        return jsonify({"error": "Conversion failed"}), 500
    except Exception as e:
        conversion_failed = True
        current_app.logger.error("Unknown error while attempting to run the FFMPEG subprocess.")
        if os.name == "nt":
            current_app.logger.warning("Windows detected. This error is often due to a misconfigured FFMPEG path. Double check it.")
        current_app.logger.error(f"Error details: {e}")
        return jsonify({"error": "Conversion failed"}), 500
    finally:
        # Clean up input file
        if os.path.exists(input_path):
            os.remove(input_path)
            current_app.logger.info("Removed uploaded temp file")
        # Clean up failed output file
        if conversion_failed and os.path.exists(output_path):
            os.remove(output_path)
            current_app.logger.info("Removed failed output file")

# open the sample converter's converted folder in the file explorer
@sample_converter_bp.route("/open-explorer", methods=["POST"])
def open_explorer():
    folder_path = get_converted_folder()
    os.makedirs(folder_path, exist_ok=True)
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


@sample_converter_bp.route("/delete-all-converted", methods=["DELETE"])
def delete_all_converted():
    """Delete all converted samples from the converted folder."""
    folder_path = get_converted_folder()

    if not os.path.exists(folder_path):
        return jsonify({"status": "deleted", "count": 0}), 200

    try:
        # Count files before deletion
        file_count = 0
        for root, dirs, files in os.walk(folder_path):
            file_count += len(files)

        # Delete contents of folder but keep the folder itself
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

        return jsonify({"status": "deleted", "count": file_count}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting converted samples: {e}")
        return jsonify({"error": str(e)}), 500
