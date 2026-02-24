"""Transform stage — plan and convert all files to ROS2."""

from __future__ import annotations

from pathlib import Path

from rosforge.engine.base import EngineRegistry
from rosforge.knowledge.cmake_rules import transform_cmake
from rosforge.knowledge.package_xml_rules import transform_package_xml
from rosforge.models.ir import FileType, SourceFile
from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy
from rosforge.models.result import ChangeEntry, TransformedFile
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage


def _choose_strategy(source_file: SourceFile) -> TransformStrategy:
    """Assign a transform strategy to a file based on its type."""
    if source_file.file_type == FileType.PACKAGE_XML:
        return TransformStrategy.RULE_BASED
    if source_file.file_type == FileType.CMAKE:
        return TransformStrategy.RULE_BASED
    if source_file.file_type in (FileType.CPP, FileType.HPP, FileType.PYTHON):
        return TransformStrategy.AI_DRIVEN
    if source_file.file_type == FileType.LAUNCH_XML:
        return TransformStrategy.AI_DRIVEN
    if source_file.file_type in (FileType.MSG, FileType.SRV, FileType.ACTION):
        return TransformStrategy.RULE_BASED
    return TransformStrategy.SKIP


def _target_path(source_path: str, file_type: FileType) -> str:
    """Derive the ROS2 output relative path from the ROS1 source path."""
    # launch XML files move to launch/ directory with .py extension in ROS2
    if file_type == FileType.LAUNCH_XML:
        p = Path(source_path)
        return str(p.with_suffix(".py"))
    return source_path


def _build_plan(ir) -> MigrationPlan:
    """Construct a MigrationPlan from PackageIR using rule-based classification."""
    actions = []
    for sf in ir.source_files:
        strategy = _choose_strategy(sf)
        if strategy == TransformStrategy.SKIP:
            continue
        actions.append(
            TransformAction(
                source_path=sf.relative_path,
                target_path=_target_path(sf.relative_path, sf.file_type),
                strategy=strategy,
                description=f"{strategy.value} transform for {sf.file_type.value} file",
                estimated_complexity=3 if strategy == TransformStrategy.AI_DRIVEN else 1,
                confidence=0.9 if strategy == TransformStrategy.RULE_BASED else 0.6,
            )
        )

    ai_count = sum(1 for a in actions if a.strategy == TransformStrategy.AI_DRIVEN)
    overall_conf = 0.9 if ai_count == 0 else 0.7

    return MigrationPlan(
        package_name=ir.metadata.name,
        target_ros2_distro="humble",
        actions=actions,
        overall_confidence=overall_conf,
        summary=(
            f"{len(actions)} files to transform "
            f"({ai_count} AI-driven, {len(actions) - ai_count} rule-based)"
        ),
    )


def _rule_based_transform(
    source_file: SourceFile,
    action: TransformAction,
    ctx: PipelineContext,
) -> TransformedFile:
    """Apply deterministic knowledge-base rules to a file."""

    content = source_file.content
    changes: list[ChangeEntry] = []
    ir = ctx.package_ir

    if source_file.file_type == FileType.PACKAGE_XML and ir is not None:
        new_content = transform_package_xml(ir.metadata, ir.dependencies)
        if new_content != content:
            changes.append(
                ChangeEntry(
                    description="Converted package.xml from format=2 (catkin) to format=3 (ament_cmake)",
                    reason="ROS2 requires package.xml format 3 with ament_cmake build type",
                )
            )
    elif source_file.file_type == FileType.CMAKE:
        from rosforge.parsers.cmake import parse_cmake

        cmake_path = ctx.source_path / source_file.relative_path
        cmake_info = parse_cmake(cmake_path) if cmake_path.exists() else {}
        catkin_deps = cmake_info.get("catkin_packages", [])
        new_content = transform_cmake(content, catkin_deps)
        if new_content != content:
            changes.append(
                ChangeEntry(
                    description="Converted CMakeLists.txt from catkin to ament_cmake",
                    reason="ROS2 uses ament_cmake build system instead of catkin",
                )
            )
    else:
        new_content = content  # MSG/SRV: pass through for now

    return TransformedFile(
        source_path=source_file.relative_path,
        target_path=action.target_path,
        original_content=content,
        transformed_content=new_content,
        changes=changes,
        confidence=action.confidence,
        strategy_used="rule_based",
    )


class TransformStage(PipelineStage):
    """Stage 3: plan and execute file-by-file transformation."""

    @property
    def name(self) -> str:
        return "Transform"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.package_ir is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="PackageIR missing — Ingest must run first.",
                    recoverable=False,
                )
            )
            return ctx

        ir = ctx.package_ir
        plan = _build_plan(ir)
        ctx.migration_plan = plan

        # Build a lookup from source_path -> action
        action_map = {a.source_path: a for a in plan.actions}

        # Prepare engine (lazy — only instantiated if AI_DRIVEN files exist)
        engine = None
        ai_actions = [a for a in plan.actions if a.strategy == TransformStrategy.AI_DRIVEN]

        if ai_actions:
            engine_name = f"{ctx.config.engine.name}-{ctx.config.engine.mode}"
            try:
                engine = EngineRegistry.get(engine_name, ctx.config.engine)
            except KeyError:
                ctx.errors.append(
                    PipelineError(
                        stage_name=self.name,
                        message=f"Engine {engine_name!r} not available.",
                        recoverable=False,
                    )
                )
                return ctx

        transformed: list[TransformedFile] = []

        for sf in ir.source_files:
            action = action_map.get(sf.relative_path)
            if action is None:
                continue

            if action.strategy == TransformStrategy.RULE_BASED:
                result = _rule_based_transform(sf, action, ctx)
            elif action.strategy == TransformStrategy.AI_DRIVEN and engine is not None:
                try:
                    result = engine.transform(sf, plan)
                    result.original_content = sf.content
                except Exception as exc:
                    ctx.errors.append(
                        PipelineError(
                            stage_name=self.name,
                            message=f"AI transform failed for {sf.relative_path}: {exc}",
                            recoverable=True,
                        )
                    )
                    # Fall back to passing through the original
                    result = TransformedFile(
                        source_path=sf.relative_path,
                        target_path=action.target_path,
                        original_content=sf.content,
                        transformed_content=sf.content,
                        confidence=0.0,
                        strategy_used="ai_driven_fallback",
                        warnings=[f"AI transform failed: {exc}"],
                    )
            else:
                continue

            transformed.append(result)

        # Write output files
        ctx.output_path.mkdir(parents=True, exist_ok=True)
        for tf in transformed:
            out_file = ctx.output_path / tf.target_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(tf.transformed_content, encoding="utf-8")

        ctx.transformed_files = transformed
        return ctx
