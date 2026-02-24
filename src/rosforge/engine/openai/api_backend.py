"""OpenAI API backend — uses openai SDK."""

from __future__ import annotations

try:
    import openai as _openai_sdk  # type: ignore[import]
    _OPENAI_AVAILABLE = True
except ImportError:
    _openai_sdk = None  # type: ignore[assignment]
    _OPENAI_AVAILABLE = False

from rosforge.engine.base import EngineInterface
from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.engine.response_parser import parse_analyze_response, parse_transform_response
from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile

# Pricing as of 2024: gpt-4o per 1M tokens
_GPT4O_INPUT_COST_PER_1M = 5.00
_GPT4O_OUTPUT_COST_PER_1M = 15.00
_DEFAULT_MODEL = "gpt-4o"


class OpenAIAPIEngine(EngineInterface):
    """AI engine backend that uses the OpenAI API via openai SDK."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._builder = PromptBuilder()
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "openai is not installed. "
                "Install it with: pip install openai"
            )
        api_key = config.api_key or ""
        self._client = _openai_sdk.OpenAI(
            api_key=api_key or None,
            timeout=config.timeout_seconds,
        )
        self._model_name = config.model or _DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call the OpenAI Chat Completions API and return content text.

        Args:
            system_prompt: System-level instruction string.
            user_prompt: User-level content string.

        Returns:
            Assistant message content text.

        Raises:
            RuntimeError: If the API call fails.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""
            return content
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI API error: {exc}") from exc

    # ------------------------------------------------------------------
    # EngineInterface
    # ------------------------------------------------------------------

    def analyze(self, package_ir: PackageIR) -> MigrationPlan:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        raw = self._call_api(system_prompt, user_prompt)
        return parse_analyze_response(raw)

    def transform(self, source_file: SourceFile, plan: MigrationPlan) -> TransformedFile:
        system_prompt, user_prompt = self._builder.build_transform_prompt(source_file, plan)
        raw = self._call_api(system_prompt, user_prompt)
        result = parse_transform_response(raw)
        result.original_content = source_file.content
        return result

    def estimate_cost(self, package_ir: PackageIR) -> CostEstimate:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        total_chars = sum(len(f.content) for f in package_ir.source_files)
        input_tokens = PromptBuilder.estimate_tokens(system_prompt + user_prompt + "X" * total_chars)
        output_tokens = int(input_tokens * 0.20)
        cost_usd = (
            (input_tokens / 1_000_000) * _GPT4O_INPUT_COST_PER_1M
            + (output_tokens / 1_000_000) * _GPT4O_OUTPUT_COST_PER_1M
        ) * max(1, package_ir.total_files)
        return CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, package_ir.total_files),
            estimated_cost_usd=round(cost_usd, 4),
            engine_name="openai-api",
        )

    def health_check(self) -> bool:
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": "Reply with OK"}],
                max_tokens=5,
            )
            return bool(response.choices[0].message.content)
        except Exception:  # noqa: BLE001
            return False
