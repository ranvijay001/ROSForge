"""PipelineRunner and PipelineContext — the core execution harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from rosforge.models.config import RosForgeConfig
from rosforge.models.ir import PackageIR
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile, ValidationResult
from rosforge.pipeline.stage import PipelineError, PipelineStage

if TYPE_CHECKING:
    from rosforge.engine.base import EngineInterface


@dataclass
class PipelineContext:
    """Shared state threaded through every pipeline stage."""

    # --- Fixed inputs (set before run) ---
    source_path: Path
    output_path: Path
    config: RosForgeConfig

    # --- Optional custom rules (set before run, if provided) ---
    # Type is Any to avoid a circular import; callers should pass CustomRules.
    custom_rules: Any = None

    # --- Stage outputs (populated progressively) ---
    package_ir: PackageIR | None = None
    analysis_report: str = ""
    cost_estimate: CostEstimate | None = None
    migration_plan: MigrationPlan | None = None
    transformed_files: list[TransformedFile] = field(default_factory=list)
    validation_result: ValidationResult | None = None
    migration_report: str = ""

    # --- Engine (set by TransformStage or caller for fix loop) ---
    engine: "EngineInterface | None" = None

    # --- Fix loop tracking ---
    fix_attempts: int = 0
    max_fix_attempts: int = 0

    # --- Tracking ---
    errors: list[PipelineError] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def fatal_errors(self) -> list[PipelineError]:
        return [e for e in self.errors if not e.recoverable]


class PipelineRunner:
    """Execute a sequence of PipelineStages, tracking progress with Rich."""

    def __init__(
        self,
        stages: list[PipelineStage],
        after_stage_callback: Callable[[str, "PipelineContext"], None] | None = None,
    ) -> None:
        self._stages = stages
        self.after_stage_callback = after_stage_callback

    def run(self, ctx: PipelineContext) -> PipelineContext:
        """Execute all stages sequentially.

        Stops immediately on any non-recoverable error. Emits Rich progress
        output when available, falls back to plain print otherwise.

        Args:
            ctx: Populated PipelineContext (source_path, output_path, config).

        Returns:
            The same context with all stage outputs populated.
        """
        ctx.started_at = datetime.now(timezone.utc)

        try:
            from rich.console import Console  # noqa: PLC0415
            from rich.progress import Progress, SpinnerColumn, TextColumn  # noqa: PLC0415

            console = Console()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                for stage in self._stages:
                    task = progress.add_task(f"[cyan]{stage.name}...", total=None)
                    ctx = self._run_stage(stage, ctx)
                    progress.remove_task(task)
                    if self.after_stage_callback is not None:
                        self.after_stage_callback(stage.name, ctx)
                    if ctx.fatal_errors:
                        console.print(
                            f"[red]Pipeline stopped at stage '{stage.name}': "
                            f"{ctx.fatal_errors[-1].message}[/red]"
                        )
                        break
                    console.print(f"[green]✓[/green] {stage.name}")
        except ImportError:
            # Rich not available — plain output
            for stage in self._stages:
                print(f"[rosforge] running stage: {stage.name}")
                ctx = self._run_stage(stage, ctx)
                if self.after_stage_callback is not None:
                    self.after_stage_callback(stage.name, ctx)
                if ctx.fatal_errors:
                    print(
                        f"[rosforge] pipeline stopped at '{stage.name}': "
                        f"{ctx.fatal_errors[-1].message}"
                    )
                    break
                print(f"[rosforge] done: {stage.name}")

        ctx.completed_at = datetime.now(timezone.utc)
        return ctx

    @staticmethod
    def _run_stage(stage: PipelineStage, ctx: PipelineContext) -> PipelineContext:
        """Run a single stage, catching and recording any exceptions."""
        try:
            return stage.execute(ctx)
        except Exception as exc:  # noqa: BLE001
            ctx.errors.append(
                PipelineError(
                    stage_name=stage.name,
                    message=str(exc),
                    recoverable=False,
                )
            )
            return ctx
