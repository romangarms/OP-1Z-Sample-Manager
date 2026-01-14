"""
This is a migration script.

It updates the system from version v0.0.1 to v0.0.2.

"""
import logging
import os
import sys
import shutil
from ..migrator import backup_file

TARGET_VERSION = "v2.0.0"

def migrate(logger: logging.Logger):
    """
    Migration script to update from v1.x.x to v2.x.x
    """
    
    v1_config_file_path = v1_get_config_path()
    v2_config_file_path = v2_get_config_path()


    v2_proj_name = "OP-1Z-Sample-Manager"
    v1_proj_name = "OP1Z-Sample-Manager"
    v1_work_dir = get_default_working_directory(v1_proj_name)
    v2_work_dir = get_default_working_directory(v2_proj_name)


    if os.path.exists(v1_config_file_path):
        logger.info("v1 config file found, attempting migration to v2")
        # Ensure v2 config directory exists (v2_get_config_dir creates it)
        try:
            v2_get_config_dir()
        except Exception:
            logger.exception("Unable to create or access v2 config directory: %s", v2_config_file_path)
            return

        # If a v2 config already exists, move it aside as a backup
        try:
            if os.path.exists(v2_config_file_path):
                logger.warning("v2 config already exists; backing up existing file")
                if backup_file(logger, v2_config_file_path, "v2.0.0_existing", None):
                    if os.path.exists(v2_config_file_path):
                        os.remove(v2_config_file_path)
                else:
                    logger.error("Failed to back up existing v2 config; aborting migration")
                    return False
            # Attempt to move the v1 config to the v2 path
            try:
                backup_file(logger, v1_config_file_path, "v1_to_v2", None)
                try:
                    os.replace(v1_config_file_path, v2_config_file_path)
                except Exception:
                    shutil.move(v1_config_file_path, v2_config_file_path)
            except Exception:
                logger.exception("Failed to move v1 config to v2 location")
                return False

            logger.info("Successfully migrated config from %s to %s", v1_config_file_path, v2_config_file_path)

        except Exception:
            logger.exception("Unexpected error during migration")
            return False
    else:
        logger.info("No v1 config file found; skipping config migration")

    # Migrate files in working directory
    if os.path.exists(v1_work_dir):
        logger.info("v1 working directory found, attempting migration to v2")
        try:
            if not os.path.exists(v2_work_dir):
                os.makedirs(v2_work_dir, exist_ok=True)

            for item in os.listdir(v1_work_dir):
                source = os.path.join(v1_work_dir, item)
                destination = os.path.join(v2_work_dir, item)
                try:
                    if os.path.isdir(source):
                        shutil.copytree(source, destination, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, destination)
                except Exception:
                    logger.exception(f"Failed to copy {source} to {destination}")

            logger.info("Successfully migrated working directory from %s to %s", v1_work_dir, v2_work_dir)

        except Exception:
            logger.exception("Unexpected error during working directory migration")
            return False
    logger.info("Migration to v2.0.0 completed.")
    return True


def get_default_working_directory(project_name):
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


"""These are taken from the v1.0.0 config.py"""
def v1_get_config_dir():
    """Get the appropriate config directory for the current OS."""
    if sys.platform == 'darwin':
        config_dir = os.path.expanduser('~/Library/Application Support/OP-Z Sample Manager')
    elif sys.platform == 'win32':
        config_dir = os.path.join(os.environ.get('APPDATA', ''), 'OP-Z Sample Manager')
    else:
        config_dir = os.path.expanduser('~/.config/OP-Z Sample Manager')

    # Create directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def v1_get_config_path():
    """Get the full path to the config file."""
    return os.path.join(v1_get_config_dir(), 'opz_sm_config.json')

"""Taken from v2"""
def v2_get_config_dir():
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

def v2_get_config_path():
    """Get the full path to the config file."""
    return os.path.join(v2_get_config_dir(), 'op-1z_sm_config.json')