"""OpenAI CLI backend — calls `openai` via subprocess."""

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

_LARGE_PROMPT_BYTES = 8 * 1024  # 8 KB threshold for file-based piping


class OpenAICLIEngine(EngineInterface):
    """AI engine backend that uses the OpenAI CLI (`openai api chat.completions.create`)."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._builder = PromptBuilder()
        self._log_dir = Path.home() / ".rosforge" / "logs"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke the OpenAI CLI and return raw stdout.

        Uses `openai api chat.completions.create` with JSON input.

        Args:
            system_prompt: System-level instruction string.
            user_prompt: User-level content string.

        Returns:
            Raw stdout string from the CLI.

        Raises:
            RuntimeError: If the CLI call fails or times out.
        """
        import json  # noqa: PLC0415

        verbose = bool(getattr(self._config, "verbose", False))
        model = self._config.model or "gpt-4o"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
        }
        payload_str = json.dumps(payload)

        if len(payload_str.encode()) > _LARGE_PROMPT_BYTES:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(payload_str)
                tmp_path = tmp.name
            cmd = ["openai", "api", "chat.completions.create", "--file", tmp_path]
        else:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(payload_str)
                tmp_path = tmp.name
            cmd = ["openai", "api", "chat.completions.create", "--file", tmp_path]

        result = run_command(
            cmd,
            timeout=self._config.timeout_seconds,
            verbose=verbose,
        )

        if verbose:
            self._maybe_log(payload_str, result.raw_stdout)

        if result.status == "timeout":
            raise RuntimeError(
                f"OpenAI CLI timed out after {self._config.timeout_seconds}s"
            )
        if result.status == "error":
            raise RuntimeError(f"OpenAI CLI error: {result.error_message}")

        # Extract content from CLI JSON response
        return self._extract_content(result.raw_stdout)

    def _extract_content(self, raw: str) -> str:
        """Extract message content from OpenAI API JSON response.

        Args:
            raw: Raw CLI stdout (JSON response).

        Returns:
            The assistant message content string, or raw if extraction fails.
        """
        import json  # noqa: PLC0415

        try:
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            return raw

    def _maybe_log(self, prompt: str, response: str) -> None:
        """Write I/O to ~/.rosforge/logs/ when verbose mode is active."""
        import time  # noqa: PLC0415

        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        (self._log_dir / f"openai_prompt_{ts}.txt").write_text(prompt, encoding="utf-8")
        (self._log_dir / f"openai_response_{ts}.txt").write_text(response, encoding="utf-8")

    # ------------------------------------------------------------------
    # EngineInterface
    # ------------------------------------------------------------------

    def analyze(self, package_ir: PackageIR) -> MigrationPlan:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        raw = self._run_openai(system_prompt, user_prompt)
        return parse_analyze_response(raw)

    def transform(self, source_file: SourceFile, plan: MigrationPlan) -> TransformedFile:
        system_prompt, user_prompt = self._builder.build_transform_prompt(source_file, plan)
        raw = self._run_openai(system_prompt, user_prompt)
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
            engine_name="openai-cli",
        )

    def health_check(self) -> bool:
        result = run_command(["openai", "--version"], timeout=10)
        return result.exit_code == 0
