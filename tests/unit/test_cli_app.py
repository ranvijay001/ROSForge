"""Unit tests for the ROSForge CLI (Typer app)."""

from __future__ import annotations

from typer.testing import CliRunner

from rosforge.cli.app import app

runner = CliRunner()


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "rosforge" in result.output
        assert "0.2.0" in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output


class TestHelp:
    def test_root_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "migrate" in result.output

    def test_migrate_help(self):
        result = runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "SOURCE" in result.output
        assert "--engine" in result.output
        assert "--distro" in result.output

    def test_config_help(self):
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_analyze_help(self):
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0


class TestMigrateValidation:
    def test_migrate_missing_source_exits_nonzero(self):
        result = runner.invoke(app, ["migrate", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_migrate_source_file_not_dir_exits_nonzero(self, tmp_path):
        f = tmp_path / "notadir.txt"
        f.write_text("hello")
        result = runner.invoke(app, ["migrate", str(f)])
        assert result.exit_code != 0


class TestConfigCommand:
    def _write_config(self, tmp_path):
        """Write a TOML-serialisable config so ConfigManager.load() succeeds."""
        import tomli_w
        cfg_dir = tmp_path / ".rosforge"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "config.toml"
        data = {
            "engine": {"name": "claude", "mode": "cli",
                       "timeout_seconds": 300, "api_key": "", "model": ""},
            "migration": {"target_ros2_distro": "humble", "backup_original": True,
                          "init_git": True, "output_dir": ""},
            "validation": {"auto_build": True, "rosdep_install": True, "max_fix_attempts": 0},
            "telemetry": {"enabled": False, "local_log": True},
            "verbose": False,
        }
        with cfg_path.open("wb") as fh:
            tomli_w.dump(data, fh)

    def test_config_list_runs(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "engine" in result.output

    def test_config_set_known_key(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        # Patch save() to avoid tomli_w None-serialisation issues with
        # the module-level _cfg singleton which may have cached the old HOME.
        monkeypatch.setattr(
            "rosforge.cli.config_cmd._cfg.save",
            lambda config, path=None: None,
        )
        monkeypatch.setattr(
            "rosforge.cli.config_cmd._cfg.load",
            lambda path=None: __import__(
                "rosforge.models.config", fromlist=["RosForgeConfig"]
            ).RosForgeConfig(),
        )
        result = runner.invoke(app, ["config", "set", "engine.name", "gemini"])
        assert result.exit_code == 0
        assert "gemini" in result.output

    def test_config_set_unknown_key_exits_nonzero(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "set", "engine.nonexistent", "value"])
        assert result.exit_code != 0


class TestStubCommands:
    def test_status_exits_nonzero_no_logs(self, tmp_path, monkeypatch):
        """Status should exit non-zero when no migration logs exist."""
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["status"])
        assert result.exit_code != 0

    def test_analyze_exits_nonzero_empty_dir(self, tmp_path):
        result = runner.invoke(app, ["analyze", str(tmp_path)])
        assert result.exit_code != 0


class TestConfigGetCommand:
    def _write_config(self, tmp_path):
        import tomli_w
        cfg_dir = tmp_path / ".rosforge"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = cfg_dir / "config.toml"
        data = {
            "engine": {"name": "claude", "mode": "cli",
                       "timeout_seconds": 300, "api_key": "", "model": ""},
            "migration": {"target_ros2_distro": "humble", "backup_original": True,
                          "init_git": True, "output_dir": ""},
            "validation": {"auto_build": True, "rosdep_install": True, "max_fix_attempts": 0},
            "telemetry": {"enabled": False, "local_log": True},
            "verbose": False,
        }
        with cfg_path.open("wb") as fh:
            tomli_w.dump(data, fh)

    def test_config_get_known_key(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "get", "engine.name"])
        assert result.exit_code == 0
        assert "claude" in result.output

    def test_config_get_unknown_key_exits_nonzero(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "get", "engine.nonexistent"])
        assert result.exit_code != 0

    def test_config_reset_with_yes_flag(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "reset", "--yes"])
        assert result.exit_code == 0
        assert "defaults" in result.output.lower()

    def test_config_path_shows_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0
        assert "config.toml" in result.output


class TestUIFunctions:
    """Tests for rosforge.cli.ui helper functions."""

    def test_print_diff_no_changes(self) -> None:
        from io import StringIO
        from rich.console import Console
        from rosforge.cli.ui import print_diff

        buf = StringIO()
        con = Console(file=buf, no_color=True)
        print_diff("same content", "same content", "file.cpp", console_obj=con)
        output = buf.getvalue()
        assert "No changes" in output

    def test_print_diff_with_changes(self) -> None:
        from io import StringIO
        from rich.console import Console
        from rosforge.cli.ui import print_diff

        buf = StringIO()
        con = Console(file=buf, no_color=True)
        print_diff("line1\nline2\n", "line1\nchanged\n", "test.cpp", console_obj=con)
        output = buf.getvalue()
        assert "test.cpp" in output

    def test_create_pipeline_progress_context(self) -> None:
        from rosforge.cli.ui import create_pipeline_progress
        with create_pipeline_progress() as prog:
            task = prog.add_task("Testing...", total=None)
            assert task is not None
