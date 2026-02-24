"""Fix stage — apply engine-driven fixes to build errors."""

from __future__ import annotations

from pathlib import Path

from rosforge.models.result import TransformedFile
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineError, PipelineStage


class FixStage(PipelineStage):
    """Apply engine fixes to files that produced build errors.

    For each BuildError that references a file path, locates the matching
    TransformedFile in ctx.transformed_files and calls ctx.engine.fix() to
    produce updated content.  The fixed file is written back to ctx.output_path
    and ctx.transformed_files is updated in place.  ctx.fix_attempts is
    incremented once per call regardless of how many files were fixed.
    """

    @property
    def name(self) -> str:
        return "Fix"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.engine is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="No engine available for fix — set ctx.engine before running FixStage.",
                    recoverable=False,
                )
            )
            return ctx

        if ctx.validation_result is None:
            ctx.errors.append(
                PipelineError(
                    stage_name=self.name,
                    message="No validation result — ValidateStage must run before FixStage.",
                    recoverable=False,
                )
            )
            return ctx

        plan = ctx.migration_plan
        build_errors = ctx.validation_result.build_errors

        # Build lookup maps for fast access
        transformed_by_target: dict[str, int] = {
            tf.target_path: i for i, tf in enumerate(ctx.transformed_files)
        }
        # Also index by source_path basename for fuzzy file-path matching
        transformed_by_source: dict[str, int] = {
            tf.source_path: i for i, tf in enumerate(ctx.transformed_files)
        }

        # Source files lookup (relative_path -> SourceFile)
        source_files_map = {}
        if ctx.package_ir is not None:
            source_files_map = {sf.relative_path: sf for sf in ctx.package_ir.source_files}

        # Track which transformed-file indices have already been fixed this
        # round so we coalesce multiple errors on the same file into a single
        # fix call (the last error message wins — engine sees full context).
        pending_fixes: dict[int, str] = {}

        for build_error in build_errors:
            if build_error.severity != "error":
                continue

            tf_index = self._find_transformed_index(
                build_error.file_path,
                transformed_by_target,
                transformed_by_source,
            )

            if tf_index is None:
                # Error does not reference a specific file — pick first available
                if ctx.transformed_files:
                    tf_index = 0
                else:
                    continue

            pending_fixes[tf_index] = build_error.message

        for tf_index, error_message in pending_fixes.items():
            tf = ctx.transformed_files[tf_index]

            # Locate original SourceFile (best-effort)
            source_file = source_files_map.get(tf.source_path)

            # engine.fix() requires a SourceFile; fall back to a minimal stub
            # when the original file is not in the IR (should not happen in
            # normal usage, but guards against incomplete context).
            if source_file is None:
                from rosforge.models.ir import FileType, SourceFile as SF  # noqa: PLC0415

                source_file = SF(
                    relative_path=tf.source_path,
                    file_type=FileType.CPP,
                    content=tf.original_content,
                )

            try:
                fixed = ctx.engine.fix(
                    source_file=source_file,
                    transformed_content=tf.transformed_content,
                    error_message=error_message,
                    plan=plan,
                )
            except Exception as exc:  # noqa: BLE001
                ctx.errors.append(
                    PipelineError(
                        stage_name=self.name,
                        message=f"Engine fix failed for {tf.target_path}: {exc}",
                        recoverable=True,
                    )
                )
                continue

            # Update in-memory record
            updated_tf = tf.model_copy(
                update={"transformed_content": fixed.transformed_content}
            )
            ctx.transformed_files[tf_index] = updated_tf

            # Write updated file back to output_path
            out_file: Path = ctx.output_path / updated_tf.target_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text(updated_tf.transformed_content, encoding="utf-8")

        ctx.fix_attempts += 1
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_transformed_index(
        error_file_path: str,
        by_target: dict[str, int],
        by_source: dict[str, int],
    ) -> int | None:
        """Return the index in ctx.transformed_files that matches *error_file_path*.

        Tries exact target-path match, then exact source-path match, then
        suffix (basename) match against both maps.
        """
        if not error_file_path:
            return None

        # Exact matches first
        if error_file_path in by_target:
            return by_target[error_file_path]
        if error_file_path in by_source:
            return by_source[error_file_path]

        # Suffix match — error paths from the compiler often include the full
        # build-tree path, but we only store relative paths.
        error_basename = Path(error_file_path).name
        for path_str, idx in by_target.items():
            if Path(path_str).name == error_basename:
                return idx
        for path_str, idx in by_source.items():
            if Path(path_str).name == error_basename:
                return idx

        return None
