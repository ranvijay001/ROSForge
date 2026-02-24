"""Unit tests for rosforge.config.manager.ConfigManager."""

from __future__ import annotations

import pytest

from rosforge.config.manager import ConfigManager
from rosforge.models.config import RosForgeConfig


def _write_toml(path, **overrides):
    """Write a minimal valid TOML config file (telemetry.enabled as bool, not None)."""
    import tomli_w
    data = {
        "engine": {"name": "claude", "mode": "cli",
                   "timeout_seconds": 300, "api_key": "", "model": ""},
        "migration": {"target_ros2_distro": "humble", "backup_original": True,
                      "init_git": True, "output_dir": ""},
        "validation": {"auto_build": True, "rosdep_install": True, "max_fix_attempts": 0},
        "telemetry": {"enabled": False, "local_log": True},
        "verbose": False,
    }
    data.update(overrides)
    with path.open("wb") as fh:
        tomli_w.dump(data, fh)


class TestConfigManagerLoad:
    def test_default_config_values(self):
        # tomli_w cannot serialise None (telemetry.enabled default).
        # Test in-memory defaults directly without touching the filesystem.
        config = RosForgeConfig()
        assert isinstance(config, RosForgeConfig)
        assert config.engine.name == "claude"

    def test_load_from_existing_file(self, tmp_path):
        cfg_path = tmp_path / "config.toml"
        _write_toml(cfg_path)
        mgr = ConfigManager()
        loaded = mgr.load(cfg_path)
        assert loaded.engine.name == "claude"

    def test_load_roundtrip(self, tmp_path):
        cfg_path = tmp_path / "config.toml"
        _write_toml(cfg_path)
        mgr = ConfigManager()
        loaded = mgr.load(cfg_path)
        assert loaded.engine.name == "claude"
        assert loaded.migration.target_ros2_distro == "humble"


class TestConfigManagerGet:
    def setup_method(self):
        self.mgr = ConfigManager()
        self.config = RosForgeConfig()

    def test_get_top_level_key(self):
        assert self.mgr.get(self.config, "verbose") is False

    def test_get_nested_key(self):
        assert self.mgr.get(self.config, "engine.name") == "claude"

    def test_get_deeply_nested_key(self):
        assert self.mgr.get(self.config, "migration.target_ros2_distro") == "humble"

    def test_get_missing_key_raises(self):
        with pytest.raises(KeyError):
            self.mgr.get(self.config, "nonexistent")

    def test_get_partial_path_raises(self):
        with pytest.raises(KeyError):
            self.mgr.get(self.config, "engine.nonexistent")


class TestConfigManagerSet:
    def setup_method(self):
        self.mgr = ConfigManager()
        self.config = RosForgeConfig()

    def test_set_top_level_key(self):
        new_cfg = self.mgr.set(self.config, "verbose", True)
        assert new_cfg.verbose is True

    def test_set_nested_key(self):
        new_cfg = self.mgr.set(self.config, "engine.name", "gemini")
        assert new_cfg.engine.name == "gemini"

    def test_set_does_not_mutate_original(self):
        self.mgr.set(self.config, "engine.name", "gemini")
        assert self.config.engine.name == "claude"

    def test_set_migration_distro(self):
        new_cfg = self.mgr.set(self.config, "migration.target_ros2_distro", "iron")
        assert new_cfg.migration.target_ros2_distro == "iron"

    def test_set_missing_key_raises(self):
        with pytest.raises(KeyError):
            self.mgr.set(self.config, "engine.nonexistent", "value")
