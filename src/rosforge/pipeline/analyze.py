"""Analyze stage — full dependency resolution, risk scoring, complexity classification."""

from __future__ import annotations

from rosforge.knowledge import ROS1_TO_ROS2_PACKAGES
from rosforge.models.ir import FileType, PackageIR, SourceFile
from rosforge.models.plan import Confidence, CostEstimate
from rosforge.models.report import AnalysisReport, DependencyReport, FileComplexity
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage

# Complexity thresholds
_COMPLEXITY_LOW = 50  # lines
_COMPLEXITY_MEDIUM = 200  # lines
_COMPLEXITY_HIGH = 500  # lines

# Risk weights
_WEIGHT_API_USAGE = 0.05
_WEIGHT_MISSING_DEP = 0.1
_WEIGHT_COMPLEX_FILE = 0.08


def _classify_complexity(file: SourceFile) -> int:
    """Return a complexity score 1–5 for a source file."""
    api_count = len(file.api_usages)
    lines = file.line_count

    if lines < _COMPLEXITY_LOW and api_count <= 2:
        return 1
    if lines < _COMPLEXITY_MEDIUM and api_count <= 5:
        return 2
    if lines < _COMPLEXITY_HIGH and api_count <= 10:
        return 3
    if lines < _COMPLEXITY_HIGH * 2 and api_count <= 20:
        return 4
    return 5


def _transform_strategy(file: SourceFile) -> str:
    """Decide rule_based vs ai_driven for a file."""
    if file.file_type in (FileType.CMAKE, FileType.PACKAGE_XML):
        return "rule_based"
    if file.file_type in (FileType.MSG, FileType.SRV, FileType.ACTION):
        return "rule_based"
    if file.file_type in (FileType.CPP, FileType.HPP, FileType.PYTHON):
        return "ai_driven" if file.api_usages else "rule_based"
    if file.file_type == FileType.LAUNCH_XML:
        return "ai_driven"
    return "rule_based"


def _resolve_dependency(dep_name: str) -> DependencyReport:
    """Check if a ROS1 dependency has a known ROS2 equivalent."""
    # Check direct name mapping
    if dep_name in ROS1_TO_ROS2_PACKAGES:
        ros2_name = ROS1_TO_ROS2_PACKAGES[dep_name]
        return DependencyReport(
            name=dep_name,
            available_in_ros2=True,
            ros2_equivalent=ros2_name,
            notes=f"Maps to {ros2_name}",
        )

    # Check if name already looks like ROS2 (common pattern)
    if dep_name.startswith("rclcpp") or dep_name.startswith("rclpy"):
        return DependencyReport(
            name=dep_name,
            available_in_ros2=True,
            ros2_equivalent=dep_name,
            notes="Already a ROS2 package",
        )

    # Known system/third-party packages that carry over unchanged
    passthrough = {
        "std_msgs",
        "geometry_msgs",
        "sensor_msgs",
        "nav_msgs",
        "actionlib_msgs",
        "diagnostic_msgs",
        "visualization_msgs",
        "tf2",
        "tf2_ros",
        "tf2_geometry_msgs",
        "eigen",
        "boost",
        "opencv",
        "pcl",
    }
    if dep_name in passthrough:
        return DependencyReport(
            name=dep_name,
            available_in_ros2=True,
            ros2_equivalent=dep_name,
            notes="Available in ROS2 with same name",
        )

    # Unknown — flag as needing review
    return DependencyReport(
        name=dep_name,
        available_in_ros2=False,
        ros2_equivalent="",
        notes="No known ROS2 equivalent — manual review required",
    )


def _compute_risk_score(
    ir: PackageIR,
    dependency_reports: list[DependencyReport],
    file_complexities: list[FileComplexity],
) -> float:
    """Compute a 0.0–1.0 risk score for the package."""
    score = 0.0

    # Contribution from API usages
    total_apis = len(ir.api_usages)
    score += min(total_apis * _WEIGHT_API_USAGE, 0.30)

    # Contribution from missing dependencies
    missing = sum(1 for d in dependency_reports if not d.available_in_ros2)
    score += min(missing * _WEIGHT_MISSING_DEP, 0.25)

    # Contribution from high-complexity files
    high_complexity = sum(1 for f in file_complexities if f.estimated_complexity >= 4)
    score += min(high_complexity * _WEIGHT_COMPLEX_FILE, 0.25)

    # Contribution from ai_driven file count relative to total
    ai_driven = sum(1 for f in file_complexities if f.transform_strategy == "ai_driven")
    if ir.total_files > 0:
        score += min((ai_driven / ir.total_files) * 0.20, 0.20)

    return min(score, 1.0)


def _risk_to_confidence(risk: float) -> Confidence:
    if risk < 0.3:
        return Confidence.HIGH
    if risk < 0.6:
        return Confidence.MEDIUM
    return Confidence.LOW


class AnalyzeStage(PipelineStage):
    """Stage 2: full dependency resolution, risk scoring, and complexity classification."""

    @property
    def name(self) -> str:
        return "Analyze"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.package_ir is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="PackageIR is not available — Ingest stage must run first.",
                    recoverable=False,
                )
            )
            return ctx

        ir = ctx.package_ir

        # 1. Resolve dependencies
        dependency_reports = [_resolve_dependency(dep.name) for dep in ir.dependencies]

        # 2. Classify each source file
        file_complexities = [
            FileComplexity(
                relative_path=f.relative_path,
                file_type=f.file_type.value,
                line_count=f.line_count,
                api_usage_count=len(f.api_usages),
                estimated_complexity=_classify_complexity(f),
                transform_strategy=_transform_strategy(f),
            )
            for f in ir.source_files
        ]

        # 3. Risk score
        risk_score = _compute_risk_score(ir, dependency_reports, file_complexities)
        confidence = _risk_to_confidence(risk_score)

        # 4. Warnings
        warnings: list[str] = []
        missing_deps = [d for d in dependency_reports if not d.available_in_ros2]
        if missing_deps:
            names = ", ".join(d.name for d in missing_deps[:5])
            suffix = f" (and {len(missing_deps) - 5} more)" if len(missing_deps) > 5 else ""
            warnings.append(f"Dependencies with no known ROS2 equivalent: {names}{suffix}")

        high_complexity_files = [f for f in file_complexities if f.estimated_complexity >= 4]
        if high_complexity_files:
            paths = ", ".join(f.relative_path for f in high_complexity_files[:3])
            warnings.append(f"High-complexity files requiring careful review: {paths}")

        if ir.launch_files > 0:
            warnings.append(
                "Launch files detected — roslaunch XML must be converted to Python launch files."
            )

        # 5. Summary
        ai_driven_count = sum(1 for f in file_complexities if f.transform_strategy == "ai_driven")
        summary = (
            f"Package '{ir.metadata.name}' has {ir.total_files} files "
            f"({ir.cpp_files} C++, {ir.python_files} Python, "
            f"{ir.launch_files} launch, {ir.msg_srv_files} msg/srv). "
            f"Risk score: {risk_score:.2f} ({confidence.value}). "
            f"{ai_driven_count} files require AI-driven transformation."
        )

        # 6. Build structured AnalysisReport
        analysis_report = AnalysisReport(
            package_name=ir.metadata.name,
            total_files=ir.total_files,
            total_lines=ir.total_lines,
            risk_score=risk_score,
            confidence=confidence,
            dependencies=dependency_reports,
            file_complexities=file_complexities,
            warnings=warnings,
            summary=summary,
        )

        # 7. Cost estimate
        input_tokens = ir.total_lines * 2 + ai_driven_count * 500
        output_tokens = int(input_tokens * 0.20)
        ctx.cost_estimate = CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, ai_driven_count),
            estimated_cost_usd=0.0,
            engine_name=ctx.config.engine.name + "-" + ctx.config.engine.mode,
        )

        # Store both structured report on context and text summary
        ctx.analysis_report = analysis_report.model_dump_json(indent=2)

        return ctx
