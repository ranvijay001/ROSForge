"""Interactive review stage — lets users accept or skip each transformed file."""

from __future__ import annotations

import difflib
import sys

from rosforge.models.result import TransformedFile
from rosforge.pipeline.runner import PipelineContext
from rosforge.pipeline.stage import PipelineStage


class InteractiveReviewStage(PipelineStage):
    """Stage: present each transformed file to the user for review.

    For each TransformedFile the user is shown a unified diff and prompted
    to accept, skip, or quit (accepting all remaining).  If stdin is not a
    TTY the stage is a no-op (all files accepted automatically).
    """

    @property
    def name(self) -> str:
        return "Interactive Review"

    def execute(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.transformed_files:
            return ctx

        if not sys.stdin.isatty():
            import warnings  # noqa: PLC0415

            warnings.warn(
                "Interactive review skipped: stdin is not a TTY. "
                "All transformed files accepted automatically.",
                stacklevel=2,
            )
            return ctx

        accepted = 0
        skipped = 0
        quit_early = False

        # Build a lookup from relative_path -> original content for skip reverting
        original_lookup: dict[str, str] = {}
        if ctx.package_ir is not None:
            for sf in ctx.package_ir.source_files:
                original_lookup[sf.relative_path] = sf.content

        updated: list[TransformedFile] = []

        for tf in ctx.transformed_files:
            if quit_early:
                # Accept all remaining without prompting
                updated.append(
                    tf.model_copy(update={"user_reviewed": True, "user_action": "accept"})
                )
                accepted += 1
                continue

            # Display diff
            self._print_diff(tf)

            # Prompt
            while True:
                try:
                    answer = input("[A]ccept / [S]kip / [Q]uit (accept remaining)? ").strip().lower()
                except EOFError:
                    answer = "a"

                if answer in ("a", "accept", ""):
                    updated.append(
                        tf.model_copy(update={"user_reviewed": True, "user_action": "accept"})
                    )
                    accepted += 1
                    break
                elif answer in ("s", "skip"):
                    # Revert to original content
                    original = original_lookup.get(tf.source_path, tf.original_content)
                    updated.append(
                        tf.model_copy(
                            update={
                                "transformed_content": original,
                                "user_reviewed": True,
                                "user_action": "skip",
                            }
                        )
                    )
                    skipped += 1
                    break
                elif answer in ("q", "quit"):
                    # Accept current file, then accept all remaining without prompting
                    updated.append(
                        tf.model_copy(update={"user_reviewed": True, "user_action": "accept"})
                    )
                    accepted += 1
                    quit_early = True
                    break
                else:
                    print("Please enter A (accept), S (skip), or Q (quit).")

        ctx.transformed_files = updated

        # Print summary to stdout so migrate.py can read counts if needed; also
        # expose counts as attributes for the CLI to consume.
        self._accepted = accepted
        self._skipped = skipped

        print(f"Interactive review: {accepted} accepted, {skipped} skipped")
        return ctx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _print_diff(tf: TransformedFile) -> None:
        """Print a unified diff for *tf* to stdout."""
        diff_lines = list(
            difflib.unified_diff(
                tf.original_content.splitlines(keepends=True),
                tf.transformed_content.splitlines(keepends=True),
                fromfile=f"a/{tf.source_path}",
                tofile=f"b/{tf.target_path}",
                lineterm="",
            )
        )

        print()
        print(f"--- File: {tf.source_path} ---")
        if not diff_lines:
            print("(no changes)")
        else:
            print("".join(diff_lines))
        print()
