"""Unit tests for WorkspaceRunner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rosforge.models.config import RosForgeConfig
from rosforge.pipeline.workspace_runner import PackageResult, WorkspaceRunner

FIXTURE_WS = Path(__file__).parent.parent / "fixtures" / "catkin_ws"


def _make_success_result(name: str, source: Path, output: Path) -> PackageResult:
    return PackageResult(
        package_name=name,
        source_path=source,
        output_path=output,
        success=True,
        duration_seconds=0.5,
        file_count=3,
        confidence_avg=0.85,
    )


def _make_failure_result(name: str, source: Path, output: Path) -> PackageResult:
    return PackageResult(
        package_name=name,
        source_path=source,
        output_path=output,
        success=False,
        error_message="Ingest failed: no package.xml",
        duration_seconds=0.1,
    )


class TestPackageResult:
    def test_defaults(self, tmp_path: Path) -> None:
        r = PackageResult(
            package_name="foo",
            source_path=tmp_path,
            output_path=tmp_path,
            success=True,
        )
        assert r.error_message == ""
        assert r.duration_seconds == 0.0
        assert r.file_count == 0
        assert r.confidence_avg == 0.0


class TestWorkspaceRunnerAllSucceed:
    def test_all_succeed(self, tmp_path: Path) -> None:
        """WorkspaceRunner returns one PackageResult per discovered package."""
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)

        # Patch _migrate_package to avoid real pipeline execution
        pkg_a = FIXTURE_WS / "src" / "pkg_a"
        pkg_b = FIXTURE_WS / "src" / "pkg_b"

        def _fake_migrate(pkg_name: str, source_path: Path, output_path: Path) -> PackageResult:
            return _make_success_result(pkg_name, source_path, output_path)

        with patch.object(runner, "_migrate_package", side_effect=_fake_migrate):
            results = runner.run(FIXTURE_WS, tmp_path / "out")

        assert len(results) == 2
        assert all(r.success for r in results)
        names = {r.package_name for r in results}
        assert names == {"pkg_a", "pkg_b"}

    def test_output_dirs_are_per_package(self, tmp_path: Path) -> None:
        """Output path for each package is output_path / package_name."""
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)
        out_root = tmp_path / "ws_out"

        captured: list[tuple[str, Path, Path]] = []

        def _fake_migrate(pkg_name: str, source_path: Path, output_path: Path) -> PackageResult:
            captured.append((pkg_name, source_path, output_path))
            return _make_success_result(pkg_name, source_path, output_path)

        with patch.object(runner, "_migrate_package", side_effect=_fake_migrate):
            runner.run(FIXTURE_WS, out_root)

        for pkg_name, _, output_path in captured:
            assert output_path == out_root / pkg_name


class TestWorkspaceRunnerPartialFailure:
    def test_partial_failure_does_not_abort(self, tmp_path: Path) -> None:
        """A failure in one package does not prevent the remaining packages from running."""
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)

        call_count = 0

        def _fake_migrate(pkg_name: str, source_path: Path, output_path: Path) -> PackageResult:
            nonlocal call_count
            call_count += 1
            if pkg_name == "pkg_a":
                return _make_failure_result(pkg_name, source_path, output_path)
            return _make_success_result(pkg_name, source_path, output_path)

        with patch.object(runner, "_migrate_package", side_effect=_fake_migrate):
            results = runner.run(FIXTURE_WS, tmp_path / "out")

        # Both packages were attempted
        assert call_count == 2
        assert len(results) == 2

        failed = [r for r in results if not r.success]
        succeeded = [r for r in results if r.success]
        assert len(failed) == 1
        assert len(succeeded) == 1
        assert failed[0].package_name == "pkg_a"

    def test_failure_records_error_message(self, tmp_path: Path) -> None:
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)

        def _fake_migrate(pkg_name: str, source_path: Path, output_path: Path) -> PackageResult:
            return _make_failure_result(pkg_name, source_path, output_path)

        with patch.object(runner, "_migrate_package", side_effect=_fake_migrate):
            results = runner.run(FIXTURE_WS, tmp_path / "out")

        for r in results:
            assert not r.success
            assert r.error_message != ""


class TestWorkspaceRunnerEmpty:
    def test_empty_workspace(self, tmp_path: Path) -> None:
        """A workspace with no packages returns an empty result list."""
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)

        # Create a workspace with an empty src/
        ws = tmp_path / "empty_ws"
        (ws / "src").mkdir(parents=True)

        results = runner.run(ws, tmp_path / "out")
        assert results == []

    def test_migrate_package_fatal_pipeline_error(self, tmp_path: Path) -> None:
        """If the pipeline context has fatal errors, _migrate_package returns failure."""
        config = RosForgeConfig()
        runner = WorkspaceRunner(config=config)

        pkg_path = tmp_path / "pkg"
        pkg_path.mkdir()
        out_path = tmp_path / "out"

        from rosforge.pipeline.runner import PipelineContext
        from rosforge.pipeline.stage import PipelineError

        mock_ctx = MagicMock(spec=PipelineContext)
        mock_ctx.fatal_errors = [
            PipelineError(stage_name="Ingest", message="no package.xml", recoverable=False)
        ]
        mock_ctx.transformed_files = []

        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = mock_ctx

        # Patch PipelineRunner inside the rosforge.pipeline.runner module
        # (that is where workspace_runner imports it from inside _migrate_package)
        with patch("rosforge.pipeline.runner.PipelineRunner", return_value=mock_runner_instance):
            # Also patch the local import inside _migrate_package
            import rosforge.pipeline.runner as _runner_mod  # noqa: PLC0415
            original = _runner_mod.PipelineRunner
            _runner_mod.PipelineRunner = lambda stages: mock_runner_instance  # type: ignore[assignment]
            try:
                result = runner._migrate_package("pkg", pkg_path, out_path)  # noqa: SLF001
            finally:
                _runner_mod.PipelineRunner = original

        assert not result.success
        assert "no package.xml" in result.error_message
