import os
import subprocess
import uuid
import html
import werkzeug.utils
from flask import Blueprint, request, jsonify, current_app
from config import get_config_setting
from sample_converter import convert_audio_file, UPLOAD_FOLDER

# Create Blueprint
sample_manager_bp = Blueprint('sample_manager', __name__)

# Constants
NUMBER_OF_SAMPLE_TYPES = 8
NUMBER_OF_SAMPLES_PER_SLOT = 10  # Number of samples to read
SAMPLE_CATEGORIES = [
    "1-kick",
    "2-snare",
    "3-perc",
    "4-fx",
    "5-bass",
    "6-lead",
    "7-arpeggio",
    "8-chord",
]

# Helper function to determine sample type from category
def get_sample_type_from_category(category):
    """
    Determine if a category is a drum or synth sample.

    Categories 1-4 (kick, snare, perc, fx) are drum samples (12s max).
    Categories 5-8 (bass, lead, arpeggio, chord) are synth samples (6s max).

    Args:
        category: Category string like "1-kick" or "8-chord"

    Returns:
        "drum" or "synth"
    """
    drum_categories = ["1-kick", "2-snare", "3-perc", "4-fx"]
    return "drum" if category in drum_categories else "synth"

@sample_manager_bp.route("/read-samples")
def read_opz():
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    sample_data = []
    current_app.logger.info(f"Reading samples from: {OPZ_MOUNT_PATH}")

    for category in SAMPLE_CATEGORIES:
        category_data = []
        for slot in range(NUMBER_OF_SAMPLES_PER_SLOT):
            slot_name = f"{slot + 1:02d}"  # "01", "02", ..., "10"
            slot_path = os.path.join(OPZ_MOUNT_PATH, "samplepacks", category, slot_name)

            sample_info = {"path": None}

            if os.path.isdir(slot_path):
                files = [f for f in os.listdir(slot_path) if os.path.isfile(os.path.join(slot_path, f))]
                if files:
                    sample_info["path"] = os.path.join(slot_path, files[0])
                    sample_info["filename"] = files[0]
                    sample_info["filesize"] = os.path.getsize(os.path.join(slot_path, files[0]))

            category_data.append(sample_info)
        sample_data.append(category_data)

    return jsonify({"sampleData": sample_data, "categories": SAMPLE_CATEGORIES})

@sample_manager_bp.route("/upload-sample", methods=["POST"])
def upload_sample():
    category = request.form.get("category")
    slot = request.form.get("slot")
    file = request.files.get("file")

    if not category or not slot or not file:
        return {"error": "Missing category, slot, or file"}, 400

    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    # Make sure the directory exists
    target_dir = os.path.join(OPZ_MOUNT_PATH, "samplepacks", category, f"{int(slot)+1:02d}")
    os.makedirs(target_dir, exist_ok=True)

    # Clean the filename and determine if conversion is needed
    original_filename = werkzeug.utils.secure_filename(file.filename)
    file_ext = os.path.splitext(original_filename)[1].lower()
    needs_conversion = file_ext != ".aiff"

    # Final filename will always be .aiff
    base_name = os.path.splitext(original_filename)[0]
    final_filename = base_name + ".aiff"
    final_path = os.path.join(target_dir, final_filename)

    temp_path = None

    try:
        # Delete any existing sample(s) in this slot
        for existing_file in os.listdir(target_dir):
            existing_path = os.path.join(target_dir, existing_file)
            if os.path.isfile(existing_path):
                os.remove(existing_path)

        if needs_conversion:
            # Save to temp location, convert, then delete temp
            temp_path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + "_" + original_filename)
            file.save(temp_path)

            # Determine sample type from category
            sample_type = get_sample_type_from_category(category)

            # Convert to final location
            convert_audio_file(temp_path, final_path, sample_type)
        else:
            # Already .aiff, save directly
            file.save(final_path)

        return {
            "status": "uploaded",
            "path": html.escape(final_path),
            "filename": html.escape(final_filename),
            "filesize": os.path.getsize(final_path),
        }, 200

    except subprocess.CalledProcessError as e:
        current_app.logger.error(f"Conversion error: {e}")
        return {"error": "Audio conversion failed"}, 500
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}")
        return {"error": "File save failed"}, 500
    finally:
        # Clean up temp file if it exists
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@sample_manager_bp.route("/delete-sample", methods=["DELETE"])
def delete_sample():
    data = request.get_json()
    sample_path = data.get("path")

    if not sample_path or not os.path.isfile(sample_path):
        return {"error": "Invalid path"}, 400

    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    # prevent deleting files outside the samplepacks directory, probably not needed but just in case
    if not sample_path.startswith(os.path.join(OPZ_MOUNT_PATH, "samplepacks")):
        return {"error": "Unauthorized path"}, 403

    try:
        os.remove(sample_path)
        return {"status": "deleted"}, 200
    except Exception as e:
        current_app.logger.error(f"Error deleting file: {e}")
        return {"error": "Failed to delete file"}, 500

@sample_manager_bp.route("/move-sample", methods=["POST"])
def move_sample():
    source_path = request.form.get("source_path")
    target_category = request.form.get("target_category")
    target_slot = request.form.get("target_slot")

    if not source_path or not target_category or target_slot is None:
        return {"error": "Missing required fields"}, 400

    if not os.path.isfile(source_path):
        return {"error": "Source file doesn't exist"}, 404

    # Resolve destination path
    OPZ_MOUNT_PATH = get_config_setting("OPZ_MOUNT_PATH")
    filename = os.path.basename(source_path)
    target_dir = os.path.join(OPZ_MOUNT_PATH, "samplepacks", target_category, f"{int(target_slot)+1:02d}")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, filename)

    try:
        # Check if there's an existing file in the target slot
        existing_files = [f for f in os.listdir(target_dir) if os.path.isfile(os.path.join(target_dir, f))]
        if existing_files:
            # Assume one sample per folder — just grab the first one
            existing_target = os.path.join(target_dir, existing_files[0])

            # Swap paths if moving between different slots
            if os.path.abspath(source_path) != os.path.abspath(existing_target):
                # Move target sample to source's original folder
                source_dir = os.path.dirname(source_path)
                swapped_target = os.path.join(source_dir, os.path.basename(existing_target))
                os.rename(existing_target, swapped_target)

        # Move new file into target slot (overwriting any remaining copy of itself)
        os.rename(source_path, target_path)

        return {"status": "moved", "path": html.escape(target_path)}, 200

    except Exception as e:
        current_app.logger.error(f"Move error: {e}")
        return {"error": "Move failed"}, 500
