import logging
import pkgutil
import importlib
from packaging import version

from blueprints.github_version_file import VERSION as APP_VERSION
from blueprints.config import get_config_setting, set_config_setting, get_config_dir, get_config_path
from packaging import version

"""
This function runs any migration tasks needed to update
the application's data/configuration to the latest version.

It runs before the server starts up to ensure everything is up to date.

It will run any migration scripts between the "LAST_RAN_VERSION" and the current application version defined in the github_version_file.

ie. If the LAST_RAN_VERSION is "v0.0.1" and the current version is "v0.0.4", it will run the migration scripts for "v0.0.2", "v0.0.3", and "v0.0.4" in that order.

Not all of them need to exist - only the ones that have changes.
"""
def run_migrations():

    current_version = version.parse(APP_VERSION)
    last_ran_version = version.parse(get_config_setting("LAST_RAN_VERSION", "v0.0.0"))

    try:
        migrations_pkg = importlib.import_module("blueprints.migration.migration_scripts")
    except Exception:
        print("migration_scripts package not available, stopping before continuing migrations.")
        return False

    migrations = []
    for finder, name, ispkg in pkgutil.iter_modules(migrations_pkg.__path__):
        try:
            mod = importlib.import_module(f"{migrations_pkg.__name__}.{name}")
        except Exception:
            print(f"Failed importing migration module: {name}")
            return False

        mig_version_str = getattr(mod, "TARGET_VERSION", None)

        if mig_version_str is None:
            print(f"Found migration module without version: {name}")
            return False

        try:
            mig_version = version.parse(str(mig_version_str))
        except Exception:
            print(f"Invalid version in migration {name}: {mig_version_str}")
            return False

        if mig_version > last_ran_version and mig_version <= current_version:
            migrations.append((mig_version, mod, name))

    migrations.sort(key=lambda t: t[0])

    for mig_version, mod, name in migrations:
        migrate_fn = getattr(mod, "migrate", None)
        if not callable(migrate_fn):
            print(f"Migration {name} does not define migrate();")
            return False
        print(f"Running migration {mig_version} ({name})")
        try:
            migrate_fn()
        except Exception:
            print(f"Migration failed: {name}")
            return False

    set_config_setting("LAST_RAN_VERSION", APP_VERSION)
    return True