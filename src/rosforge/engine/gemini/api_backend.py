"""Gemini API backend — uses google-genai SDK."""

from __future__ import annotations

try:
    import google.genai as genai  # type: ignore[import]

    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    _GENAI_AVAILABLE = False

from rosforge.engine.base import EngineInterface
from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.engine.response_parser import (
    parse_analyze_response,
    parse_fix_response,
    parse_transform_response,
)
from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile

# Pricing as of 2024: Gemini 1.5 Pro input/output per 1M tokens
_GEMINI_INPUT_COST_PER_1M = 3.50
_GEMINI_OUTPUT_COST_PER_1M = 10.50
_DEFAULT_MODEL = "gemini-1.5-pro"


class GeminiAPIEngine(EngineInterface):
    """AI engine backend that uses the Gemini API via google-genai SDK."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._builder = PromptBuilder()
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai SDK is not installed. Install it with: pip install google-genai"
            )
        api_key = config.api_key or ""
        self._client = genai.Client(api_key=api_key or None)
        self._model_name = config.model or _DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Gemini API and return raw text response.

        Args:
            system_prompt: System-level instruction string.
            user_prompt: User-level content string.

        Returns:
            Raw text from the API response.

        Raises:
            RuntimeError: If the API call fails.
        """
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                    max_output_tokens=8192,
                ),
            )
            return response.text or ""
        except Exception as exc:
            raise RuntimeError(f"Gemini API error: {exc}") from exc

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

    def fix(
        self,
        source_file: SourceFile,
        transformed_content: str,
        error_message: str,
        plan: MigrationPlan,
    ) -> TransformedFile:
        system_prompt, user_prompt = self._builder.build_fix_prompt(
            source_file, transformed_content, error_message
        )
        raw = self._call_api(system_prompt, user_prompt)
        result = parse_fix_response(raw)
        result.original_content = source_file.content
        return result

    def estimate_cost(self, package_ir: PackageIR) -> CostEstimate:
        system_prompt, user_prompt = self._builder.build_analyze_prompt(package_ir)
        total_chars = sum(len(f.content) for f in package_ir.source_files)
        input_tokens = PromptBuilder.estimate_tokens(
            system_prompt + user_prompt + "X" * total_chars
        )
        output_tokens = int(input_tokens * 0.20)
        cost_usd = (
            (input_tokens / 1_000_000) * _GEMINI_INPUT_COST_PER_1M
            + (output_tokens / 1_000_000) * _GEMINI_OUTPUT_COST_PER_1M
        ) * max(1, package_ir.total_files)
        return CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, package_ir.total_files),
            estimated_cost_usd=round(cost_usd, 4),
            engine_name="gemini-api",
        )

    def health_check(self) -> bool:
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents="Reply with OK",
            )
            return bool(response.text)
        except Exception:
            return False
