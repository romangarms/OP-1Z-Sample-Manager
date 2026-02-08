import pytest

from blueprints.config import load_config, reset_config_state, set_config_setting
from blueprints.constants import Config, EnvVars


@pytest.fixture(autouse=True)
def _isolate_config_and_working_dirs(tmp_path, monkeypatch, request):
    config_dir = tmp_path / "config"
    working_dir = tmp_path / "work"
    config_dir.mkdir()
    working_dir.mkdir()

    monkeypatch.setenv(EnvVars.CONFIG_DIR, str(config_dir))
    monkeypatch.setenv(EnvVars.WORKING_DIR, str(working_dir))

    reset_config_state()
    load_config()
    set_config_setting(Config.WORKING_DIRECTORY, str(working_dir), save=True)
    if request.node.get_closest_marker("run_migrations") is None:
        set_config_setting("SKIP_MIGRATIONS_ON_STARTUP", True, save=True)

    yield


@pytest.fixture
def app():
    import app as app_module

    app_instance = app_module.app
    app_instance.config.update(TESTING=True)
    return app_instance


@pytest.fixture
def client(app):
    with app.test_client() as client_instance:
        yield client_instance
