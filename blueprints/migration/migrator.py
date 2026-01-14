"""
Functions in this file should not be modified unless absolutely necessary.
They are intended as being stable utilities for migration scripts to use.
If a change is needed in a future version, create a new migration assistance script instead.

run_migrations may be a sole exception to this, as long as existing migration scripts are not affected by any changes.

"""

import datetime
import logging
import os
import pkgutil
import importlib
import shutil
from packaging import version

from blueprints.github_version_file import VERSION as APP_VERSION
from blueprints.config import get_config_setting, set_config_setting

def run_migrations(logger: logging.Logger) -> bool:
    """
    This function runs any migration tasks needed to update
    the application's data/configuration to the latest version.

    It runs before the server starts up to ensure everything is up to date.

    It will run any migration scripts between the "LAST_RAN_VERSION" and the current application version defined in the github_version_file.

    ie. If the LAST_RAN_VERSION is "v1.2.5" and the current version is "v7.3.4", it will run the migration scripts for "v2.0.0", "v3.0.0", and "v4.0.0" in that order.

    Not all of them need to exist - only the ones that have changes that need to be migrated.

    Migration scripts are located in the blueprints/migration/migration_scripts/ folder.
    They must define a TARGET_VERSION string and a migrate() function.
    They should be named based on their target version for clarity, but this is not strictly required.

    The majority of the migration logic should be encapsulated within each migration script's migrate() function.
    This is because if the behaviour of the application changes in future versions, we want the migration scripts to remain valid.

    If they rely on any config settings, those should be read at runtime from within the migrate() function.

    Args:
        logger (logging.Logger): Logger instance to log migration progress.
    Returns:
        bool: True if all migrations succeeded or none were needed, False if any migration failed.
    """
    # We have not run the bit where we use the configured logging setting yet, so we set it to DEBUG for now.
    # It will be updated later once config is loaded.
    logger.setLevel(logging.DEBUG)

    logger.info("Starting migration process...")
    
    # 1. Resolve Versions
    try:
        current_version_str = APP_VERSION
        current_version = version.parse(current_version_str)
        
        # the default of v0.0.0 will cause all migrations to run on first launch.
        # The default should either be this or the current app version / dev version to skip all migrations on first launch.

        #TODO: if making a new migrator for a future version, consider changing the default to current_version_str to skip all migrations on first launch.

        last_ran_version_str = get_config_setting("LAST_RAN_VERSION", "v0.0.0")
        last_ran_version = version.parse(last_ran_version_str)
    except version.InvalidVersion as e:
        logger.error(f"Critical: Could not parse version strings. App: {APP_VERSION}, Config: {last_ran_version_str}. Error: {e}")
        return False
    
    if current_version.is_devrelease or last_ran_version.is_devrelease:
        logger.warning("Development version detected. Migration will not be performed.")

    logger.info(f"Migration Check: Current App Version {current_version} | Last Ran Migration {last_ran_version}")

    # Optimization: Skip import logic if versions match
    if current_version <= last_ran_version:
        logger.debug("System is up to date. No migrations required.")
        return True

    # 2. Load Migration Package
    try:
        migrations_pkg = importlib.import_module("blueprints.migration.migration_scripts")
    except ImportError:
        logger.error("Critical: 'blueprints.migration.migration_scripts' package missing. Cannot run migrations.")
        return False

    # 3. Discover Scripts
    pending_migrations = []
    
    # Handle PyInstaller/Frozen environments where __path__ might behave differently
    pkg_path = getattr(migrations_pkg, "__path__", [])
    
    for _, name, _ in pkgutil.iter_modules(pkg_path):
        logger.info(f"Found migration module: {name}")
        try:
            full_name = f"{migrations_pkg.__name__}.{name}"
            mod = importlib.import_module(full_name)
            
            # Extract version from module
            mig_version_str = getattr(mod, "TARGET_VERSION", None)
            if not mig_version_str:
                logger.warning(f"Skipping migration '{name}': No TARGET_VERSION defined.")
                continue

            mig_version = version.parse(str(mig_version_str))

            # Filter: Run only if newer than last run AND older/equal to current app version
            if last_ran_version < mig_version <= current_version:
                pending_migrations.append((mig_version, mod, name))
                
        except Exception as e:
            # Catch import errors (syntax errors in scripts, etc)
            logger.exception(f"Failed to import migration module '{name}'")
            return False

    # 4. Sort and Execute
    pending_migrations.sort(key=lambda t: t[0])
    
    if not pending_migrations:
        logger.info(f"No migration scripts found between {last_ran_version} and {current_version}. Fast-forwarding config.")
        set_config_setting("LAST_RAN_VERSION", current_version_str)
        return True

    logger.info(f"Found {len(pending_migrations)} pending migrations.")

    for mig_version, mod, name in pending_migrations:
        migrate_fn = getattr(mod, "migrate", None)
        
        if not callable(migrate_fn):
            logger.error(f"Migration '{name}' ({mig_version}) has no 'migrate()' function.")
            return False
            
        logger.info(f"Executing migration: {name} (Target: {mig_version})")
        
        try:
            # Run the migration
            successful_migration = migrate_fn(logger=logger)
            if successful_migration is False or successful_migration is None:
                logger.error(f"Migration '{name}' ({mig_version}) reported failure.")
                return False

            # IMPORTANT: Update state immediately after success.
            # If the next migration fails, we don't want to re-run this one.
            set_config_setting("LAST_RAN_VERSION", str(mig_version))
            logger.info(f"Successfully finished {name}. Config updated.")
            
        except Exception:
            logger.exception(f"CRITICAL FAILURE in migration {name}")
            return False

    # 5. Final Sync
    # Ensure we are tagged at the exact current version (handles gaps where no script existed)
    set_config_setting("LAST_RAN_VERSION", current_version_str)
    logger.info("All migrations completed successfully.")
    
    return True

def backup_file(logger: logging.Logger, source_path: str, vFrom: str, backup_dir: str) -> bool:
    """
    Utility function to back up a file from source_path to backup_dir with a versioned and dated filename.
    Will put the file in the same directory as source_path if backup_dir is None.
    This function should not be changed. If a change is needed in a future version, create a new migration script instead.
    Args:
        logger (logging.Logger): Logger instance for logging.
        source_path (str): Path to the source file to back up.
        vFrom (str): Version string to include in the backup filename.
        backup_dir (str): Optional directory where the backup file will be stored.

    Returns:
        bool: True if backup succeeded, False otherwise.
    """
    backup_path = ""
    if (backup_dir is None) or (not os.path.isdir(backup_dir)):
        backup_path = f"{source_path}.{datetime.datetime.now().isoformat()}.{vFrom}.bak"
    else:
        base_name = os.path.basename(source_path)
        backup_path = os.path.join(backup_dir, f"{base_name}.{datetime.datetime.now().isoformat()}.{vFrom}.bak")

    try:
        if os.path.exists(source_path):
            logger.info(f"Backing up file from {source_path} to {backup_path}")
            try:
                os.replace(source_path, backup_path)
            except Exception:
                shutil.move(source_path, backup_path)
        else:
            logger.warning(f"Source file {source_path} does not exist. No backup made.")
        return True
    except Exception:
        logger.exception(f"Failed to back up file from {source_path} to {backup_path}")
        return False
