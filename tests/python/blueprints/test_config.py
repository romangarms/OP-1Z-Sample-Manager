import os

from blueprints.config import (
    app_config,
    get_config_dir,
    get_default_working_directory,
    load_config,
    reset_config_state,
    set_config_setting,
)
from blueprints.constants import EnvVars


def _norm(path):
    return os.path.normcase(os.path.normpath(path))


def _is_within(base, path):
    base_norm = _norm(base)
    path_norm = _norm(path)
    return os.path.commonpath([base_norm, path_norm]) == base_norm


def test_env_overrides_config_dir(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_config"
    monkeypatch.setenv(EnvVars.CONFIG_DIR, str(custom_dir))

    resolved = get_config_dir()

    assert _norm(resolved) == _norm(str(custom_dir))
    assert os.path.isdir(resolved)


def test_env_overrides_working_dir(tmp_path, monkeypatch):
    custom_dir = tmp_path / "custom_work"
    monkeypatch.setenv(EnvVars.WORKING_DIR, str(custom_dir))

    resolved = get_default_working_directory("Ignored-Project-Name")

    assert _norm(resolved) == _norm(str(custom_dir))


def test_load_config_clears_when_missing(tmp_path, monkeypatch):
    config_dir = tmp_path / "isolated_config"
    monkeypatch.setenv(EnvVars.CONFIG_DIR, str(config_dir))

    reset_config_state()
    set_config_setting("SOME_KEY", "value", save=False)
    assert "SOME_KEY" in app_config

    load_config()

    assert "SOME_KEY" not in app_config


def test_conftest_isolation_paths(tmp_path):
    config_dir = os.environ.get(EnvVars.CONFIG_DIR)
    working_dir = os.environ.get(EnvVars.WORKING_DIR)

    assert config_dir
    assert working_dir
    assert _is_within(str(tmp_path), config_dir)
    assert _is_within(str(tmp_path), working_dir)
