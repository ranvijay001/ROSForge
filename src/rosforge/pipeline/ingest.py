"""Ingest stage — scan and parse the ROS1 package into a PackageIR."""

from __future__ import annotations

from rosforge.parsers.package_scanner import scan_package
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage


class IngestStage(PipelineStage):
    """Stage 1: walk the source directory and build the PackageIR."""

    @property
    def name(self) -> str:
        return "Ingest"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        package_ir = scan_package(ctx.source_path)

        # Validate that the scan found at least a package.xml
        has_package_xml = any(
            f.relative_path == "package.xml" or f.relative_path.endswith("/package.xml")
            for f in package_ir.source_files
        )
        if not has_package_xml:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message=(
                        f"No package.xml found in {ctx.source_path}. Is this a valid ROS1 package?"
                    ),
                    recoverable=False,
                )
            )
            return ctx

        ctx.package_ir = package_ir
        return ctx
