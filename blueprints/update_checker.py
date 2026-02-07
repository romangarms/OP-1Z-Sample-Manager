from flask import Blueprint, jsonify, current_app
from urllib.error import URLError, HTTPError
import requests
from datetime import datetime, timedelta
from .config import get_config_setting, set_config_setting
from packaging import version

# Create Blueprint
update_checker_bp = Blueprint('update_checker', __name__)

# Constants:
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/romangarms/OP1Z-Sample-Manager/releases/latest"
from .github_version_file import VERSION as APP_VERSION

@update_checker_bp.route('/get_app_version', methods=['GET'])
def get_app_version():
    """Return the current application version."""
    return jsonify({"app_version": APP_VERSION})

@update_checker_bp.route('/get_github_latest_version', methods=['GET'])
def get_github_latest_version():
    """Fetch and return the latest version from GitHub."""
    latest_tag = get_latest_tag()
    return jsonify({"github_version": latest_tag})

@update_checker_bp.route('/display_update_notice', methods=['GET'])
def display_update_notice():
    """
    Check for updates by fetching the latest version from GitHub and comparing it to the current version.
    Handles all logic for deciding whether to display an update notice.
    
    Will only show update notice once per hour (configurable via update_notice_cooldown_hours).

    Returns JSON with:
    - display_update_notice (bool): Whether to show the update notice.
    - current_version (str): The current app version.
    - github_version (str): The latest version from GitHub.
    """

    response_data = {
        "display_update_notice": False,
        "current_version": APP_VERSION,
        "github_version": "unknown"
    }

    if get_config_setting('UPDATE_CHECKER_DISABLED', False):
        response_data["github_version"] = "checking_disabled"
        return jsonify(response_data)
    
    # Check if enough time has passed since last notification
    last_shown = get_config_setting('UPDATE_NOTICE_LAST_SHOWN')
    cooldown_seconds = get_config_setting('UPDATE_NOTICE_COOLDOWN_SECONDS', 3600)  # Default 1 hour
    
    if last_shown:
        try:
            last_shown_time = datetime.fromisoformat(last_shown)
            time_since_last = datetime.now() - last_shown_time
            if time_since_last < timedelta(seconds=cooldown_seconds):
                # Too soon - don't show notice
                return jsonify(response_data)
        except (ValueError, TypeError):
            # Invalid timestamp - proceed with check
            pass
    
    latest_tag = get_latest_tag()
    response_data["github_version"] = latest_tag

    ignored_version = get_config_setting('UPDATE_CHECKER_IGNORED_VERSION')
    if (ignored_version is not None) and (ignored_version == response_data["github_version"]):
        return jsonify(response_data)
    
    if response_data["github_version"] != 'unknown':
        try:
            response_data["display_update_notice"] = version.parse(APP_VERSION) < version.parse(response_data["github_version"])
        except version.InvalidVersion:
            response_data["display_update_notice"] = False
        # Store the current time as the last shown time
        set_config_setting('UPDATE_NOTICE_LAST_SHOWN', datetime.now().isoformat())

    return jsonify(response_data)

def get_latest_tag(timeout=5):
    """
    Fetch the latest release tag from GitHub.
    returns the tag name as a string, or
    returns 'unknown' on failure.
    """
    url = GITHUB_LATEST_RELEASE_URL
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get('tag_name', 'unknown')
    except requests.exceptions.Timeout:
        current_app.logger.error("GitHub request timed out while fetching latest tag.")
    except requests.exceptions.HTTPError as e:
        current_app.logger.error("HTTP error fetching latest tag: %s", e)
    except requests.exceptions.RequestException as e:
        current_app.logger.error("Error fetching latest tag: %s", e)
    except ValueError as e:
        current_app.logger.error("Invalid JSON received for latest tag: %s", e)
    
    return 'unknown'
    