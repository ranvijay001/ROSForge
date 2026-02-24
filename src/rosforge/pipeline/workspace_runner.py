"""WorkspaceRunner — migrate all packages in a catkin workspace sequentially."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rosforge.models.config import RosForgeConfig
from rosforge.parsers.workspace_scanner import discover_packages


@dataclass
class PackageResult:
    """Result record for a single package migration within a workspace run."""

    package_name: str
    source_path: Path
    output_path: Path
    success: bool
    error_message: str = ""
    duration_seconds: float = 0.0
    file_count: int = 0
    confidence_avg: float = 0.0


class WorkspaceRunner:
    """Migrate all packages found in a catkin workspace.

    Each package is run through the full ROSForge pipeline (Ingest, Analyze,
    Transform, Report).  A per-package failure is recorded but does not abort
    the remaining packages.

    Args:
        config: ROSForge configuration to pass to each PipelineRunner.
        custom_rules: Optional CustomRules instance (Any to avoid circular import).
    """

    def __init__(
        self,
        config: RosForgeConfig,
        custom_rules: Any = None,
    ) -> None:
        self._config = config
        self._custom_rules = custom_rules

    def run(self, workspace_path: Path, output_path: Path) -> list[PackageResult]:
        """Migrate all packages in *workspace_path* into subdirs of *output_path*.

        Args:
            workspace_path: Catkin workspace root (contains ``src/``).
            output_path: Directory under which per-package output dirs are created.

        Returns:
            Ordered list of :class:`PackageResult`, one per discovered package.
        """
        package_paths = discover_packages(workspace_path)
        results: list[PackageResult] = []

        for pkg_path in package_paths:
            pkg_name = pkg_path.name
            pkg_output = output_path / pkg_name
            result = self._migrate_package(pkg_name, pkg_path, pkg_output)
            results.append(result)

        return results

    def _migrate_package(
        self,
        pkg_name: str,
        source_path: Path,
        output_path: Path,
    ) -> PackageResult:
        """Run the full pipeline for a single package.

        Failures are caught and stored in the returned :class:`PackageResult`
        rather than propagating to the caller.
        """
        start = time.monotonic()

        try:
            from rosforge.pipeline.runner import PipelineContext, PipelineRunner  # noqa: PLC0415
            from rosforge.pipeline.ingest import IngestStage  # noqa: PLC0415
            from rosforge.pipeline.analyze import AnalyzeStage  # noqa: PLC0415
            from rosforge.pipeline.transform import TransformStage  # noqa: PLC0415
            from rosforge.pipeline.report import ReportStage  # noqa: PLC0415
        except ImportError as exc:
            duration = time.monotonic() - start
            return PackageResult(
                package_name=pkg_name,
                source_path=source_path,
                output_path=output_path,
                success=False,
                error_message=f"Pipeline import failed: {exc}",
                duration_seconds=duration,
            )

        ctx = PipelineContext(
            source_path=source_path,
            output_path=output_path,
            config=self._config,
            custom_rules=self._custom_rules,
        )

        stages = [IngestStage(), AnalyzeStage(), TransformStage(), ReportStage()]
        runner = PipelineRunner(stages=stages)

        try:
            ctx = runner.run(ctx)
        except Exception as exc:  # noqa: BLE001
            duration = time.monotonic() - start
            return PackageResult(
                package_name=pkg_name,
                source_path=source_path,
                output_path=output_path,
                success=False,
                error_message=str(exc),
                duration_seconds=duration,
            )

        duration = time.monotonic() - start
        fatal = ctx.fatal_errors

        if fatal:
            return PackageResult(
                package_name=pkg_name,
                source_path=source_path,
                output_path=output_path,
                success=False,
                error_message=fatal[-1].message,
                duration_seconds=duration,
                file_count=len(ctx.transformed_files),
            )

        file_count = len(ctx.transformed_files)
        confidence_avg = (
            sum(tf.confidence for tf in ctx.transformed_files) / file_count
            if file_count
            else 0.0
        )

        return PackageResult(
            package_name=pkg_name,
            source_path=source_path,
            output_path=output_path,
            success=True,
            duration_seconds=duration,
            file_count=file_count,
            confidence_avg=confidence_avg,
        )
