"""Validate stage — colcon build verification."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from rosforge.models.result import BuildError, ValidationResult
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineStage
from rosforge.utils.subprocess_utils import run_command

# Patterns for colcon/CMake/compiler error lines
_ERROR_PATTERNS = [
    # CMake error: "CMakeFiles/..." style
    re.compile(
        r"(?P<file>[^:\n]+\.(?:cpp|cxx|cc|c|hpp|h)):(?P<line>\d+):\d+:\s*(?P<severity>error|warning):\s*(?P<msg>.+)"
    ),
    # Python errors from ament_python builds
    re.compile(r"(?P<severity>ERROR|WARNING)\s+(?P<file>[^:\n]+):(?P<line>\d+):\s*(?P<msg>.+)"),
    # Generic colcon error lines
    re.compile(r"(?P<severity>[Ee]rror):\s*(?P<msg>.+)"),
]


def _parse_build_errors(log: str) -> tuple[list[BuildError], int, int]:
    """Parse compiler/build output and extract structured errors.

    Args:
        log: Raw build log (stdout + stderr combined).

    Returns:
        Tuple of (errors list, error_count, warning_count).
    """
    errors: list[BuildError] = []
    error_count = 0
    warning_count = 0

    for line in log.splitlines():
        matched = False
        for pattern in _ERROR_PATTERNS:
            m = pattern.search(line)
            if m:
                groups = m.groupdict()
                severity = groups.get("severity", "error").lower()
                if "warn" in severity:
                    warning_count += 1
                    sev = "warning"
                else:
                    error_count += 1
                    sev = "error"

                errors.append(
                    BuildError(
                        file_path=groups.get("file", ""),
                        line_number=int(groups.get("line", 0)),
                        message=groups.get("msg", line.strip()),
                        severity=sev,
                    )
                )
                matched = True
                break

        # Fallback: lines containing " error:" but not matched above
        if not matched and " error:" in line.lower() and len(line.strip()) > 0:
            error_count += 1
            errors.append(
                BuildError(
                    file_path="",
                    line_number=0,
                    message=line.strip(),
                    severity="error",
                )
            )

    return errors, error_count, warning_count


class ValidateStage(PipelineStage):
    """Stage 4: run colcon build to validate the migration output.

    Respects ``config.validation.auto_build`` and
    ``config.validation.rosdep_install`` flags.
    """

    @property
    def name(self) -> str:
        return "Validate"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        validation_cfg = ctx.config.validation

        if not validation_cfg.auto_build:
            ctx.validation_result = ValidationResult(
                success=True,
                build_log="[Validation skipped: auto_build=false]",
            )
            return ctx

        # Check colcon is available
        if not shutil.which("colcon"):
            ctx.validation_result = ValidationResult(
                success=False,
                build_log="colcon not found in PATH — install colcon to enable build validation.",
                error_count=1,
                build_errors=[
                    BuildError(
                        file_path="",
                        line_number=0,
                        message="colcon not found in PATH",
                        severity="error",
                    )
                ],
            )
            return ctx

        output_path: Path = ctx.output_path

        # Optional: run rosdep install first
        if validation_cfg.rosdep_install and shutil.which("rosdep"):
            self._run_rosdep(output_path)

        # Run colcon build
        start = time.monotonic()
        build_result = run_command(
            cmd=[
                "colcon",
                "build",
                "--base-paths",
                str(output_path),
                "--cmake-args",
                "-DCMAKE_BUILD_TYPE=Release",
            ],
            timeout=600,
            cwd=output_path,
        )
        duration = time.monotonic() - start

        raw_log = (build_result.raw_stdout or "") + "\n" + (build_result.raw_stderr or "")
        build_errors, error_count, warning_count = _parse_build_errors(raw_log)

        success = build_result.exit_code == 0 and error_count == 0

        ctx.validation_result = ValidationResult(
            success=success,
            build_errors=build_errors,
            warning_count=warning_count,
            error_count=error_count,
            build_log=raw_log,
            duration_seconds=round(duration, 2),
        )
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_rosdep(path: Path) -> None:
        """Run rosdep install in *path* (best-effort, errors ignored)."""
        run_command(
            cmd=["rosdep", "install", "--from-paths", str(path), "--ignore-src", "-y"],
            timeout=120,
            cwd=path,
        )
