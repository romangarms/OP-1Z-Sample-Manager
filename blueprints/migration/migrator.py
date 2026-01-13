import logging
import pkgutil
import importlib
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

    Not all of them need to exist - only the ones that have changes.

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
        
        last_ran_version_str = get_config_setting("LAST_RAN_VERSION", "v0.0.0")
        last_ran_version = version.parse(last_ran_version_str)
    except version.InvalidVersion as e:
        logger.error(f"Critical: Could not parse version strings. App: {APP_VERSION}, Config: {last_ran_version_str}. Error: {e}")
        return False

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
            migrate_fn()
            
            # IMPORTANT: Update state immediately after success.
            # If the next migration fails, we don't want to re-run this one.
            set_config_setting("LAST_RAN_VERSION", str(mig_version))
            logger.info(f"Successfully finished {name}. Config updated.")
            
        except Exception:
            # Log the full traceback so you can actually debug it
            logger.exception(f"CRITICAL FAILURE in migration {name}")
            return False

    # 5. Final Sync
    # Ensure we are tagged at the exact current version (handles gaps where no script existed)
    set_config_setting("LAST_RAN_VERSION", current_version_str)
    logger.info("All migrations completed successfully.")
    
    return True