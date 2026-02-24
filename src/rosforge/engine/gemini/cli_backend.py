"""Gemini CLI backend — calls `gemini` via subprocess."""

from __future__ import annotations

import tempfile
from pathlib import Path

from rosforge.engine.base import EngineInterface
from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.engine.response_parser import parse_analyze_response, parse_transform_response
from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile
from rosforge.utils.subprocess_utils import run_command

_LARGE_PROMPT_BYTES = 8 * 1024  # 8 KB threshold for stdin piping


class GeminiCLIEngine(EngineInterface):
    """AI engine backend that uses the Gemini CLI (`gemini ...`)."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._builder = PromptBuilder()
        self._log_dir = Path.home() / ".rosforge" / "logs"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke the Gemini CLI and return raw stdout.

        Args:
            system_prompt: System-level instruction string.
            user_prompt: User-level content string.

        Returns:
            Raw stdout string from the CLI.

        Raises:
            RuntimeError: If the CLI call fails or times out.
        """
        combined = f"{system_prompt}\n\n{user_prompt}"
        verbose = bool(getattr(self._config, "verbose", False))

        model_args: list[str] = []
        if self._config.model:
            model_args = ["--model", self._config.model]

        if len(combined.encode()) > _LARGE_PROMPT_BYTES:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(combined)
                tmp_path = tmp.name

            cmd = ["gemini"] + model_args + ["-p", f"@{tmp_path}"]
            result = run_command(
                cmd,
                timeout=self._config.timeout_seconds,
                verbose=verbose,
            )
            if not result.ok:
                short = combined[:_LARGE_PROMPT_BYTES]
                result = run_command(
                    ["gemini"] + model_args + ["-p", short],
                    timeout=self._config.timeout_seconds,
                    verbose=verbose,
                )
        else:
            cmd = ["gemini"] + model_args + ["-p", combined]
            result = run_command(
                cmd,
                timeout=self._config.timeout_seconds,
                verbose=verbose,
            )

        if getattr(self._config, "verbose", False):
            self._maybe_log(combined, result.raw_stdout)

        if result.status == "timeout":
            raise RuntimeError(
                f"Gemini CLI timed out after {self._config.timeout_seconds}s"
            )
        if result.status == "error":
            raise RuntimeError(f"Gemini CLI error: {result.error_message}")

        return result.raw_stdout

    def _maybe_log(self, prompt: str, response: str) -> None:
        """Write I/O to ~/.rosforge/logs/ when verbose mode is active."""
        import time  # noqa: PLC0415

        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        (self._log_dir / f"gemini_prompt_{ts}.txt").write_text(prompt, encoding="utf-8")
        (self._log_dir / f"gemini_response_{ts}.txt").write_text(response, encoding="utf-8")

    # ------------------------------------------------------------------
    # EngineInterface
    # ------------------------------------------------------------------

    def analyze(self, package_ir: PackageIR) -> MigrationPlan:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        raw = self._run_gemini(system_prompt, user_prompt)
        return parse_analyze_response(raw)

    def transform(self, source_file: SourceFile, plan: MigrationPlan) -> TransformedFile:
        system_prompt, user_prompt = self._builder.build_transform_prompt(source_file, plan)
        raw = self._run_gemini(system_prompt, user_prompt)
        result = parse_transform_response(raw)
        result.original_content = source_file.content
        return result

    def estimate_cost(self, package_ir: PackageIR) -> CostEstimate:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        total_chars = sum(len(f.content) for f in package_ir.source_files)
        input_tokens = PromptBuilder.estimate_tokens(system_prompt + user_prompt + "X" * total_chars)
        output_tokens = int(input_tokens * 0.20)
        return CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, package_ir.total_files),
            estimated_cost_usd=0.0,  # CLI has no per-token cost
            engine_name="gemini-cli",
        )

    def health_check(self) -> bool:
        result = run_command(["gemini", "--version"], timeout=10)
        return result.exit_code == 0
