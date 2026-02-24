"""Claude API backend — uses anthropic SDK."""

from __future__ import annotations

try:
    import anthropic as _anthropic_sdk  # type: ignore[import]
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _anthropic_sdk = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

from rosforge.engine.base import EngineInterface
from rosforge.engine.prompt_builder import PromptBuilder
from rosforge.engine.response_parser import parse_analyze_response, parse_transform_response
from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile

# Pricing as of 2024: Claude 3.5 Sonnet per 1M tokens
_CLAUDE_INPUT_COST_PER_1M = 3.00
_CLAUDE_OUTPUT_COST_PER_1M = 15.00
_DEFAULT_MODEL = "claude-3-5-sonnet-20241022"


class ClaudeAPIEngine(EngineInterface):
    """AI engine backend that uses the Claude API via anthropic SDK."""

    def __init__(self, config: EngineConfig) -> None:
        self._config = config
        self._builder = PromptBuilder()
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic is not installed. "
                "Install it with: pip install anthropic"
            )
        api_key = config.api_key or ""
        self._client = _anthropic_sdk.Anthropic(
            api_key=api_key or None,
            timeout=config.timeout_seconds,
        )
        self._model_name = config.model or _DEFAULT_MODEL

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Anthropic Messages API and return content text.

        Args:
            system_prompt: System-level instruction string.
            user_prompt: User-level content string.

        Returns:
            Assistant message content text.

        Raises:
            RuntimeError: If the API call fails.
        """
        try:
            message = self._client.messages.create(
                model=self._model_name,
                max_tokens=8192,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
            # Extract text from first content block
            content = message.content[0].text if message.content else ""
            return content
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Claude API error: {exc}") from exc

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
            (input_tokens / 1_000_000) * _CLAUDE_INPUT_COST_PER_1M
            + (output_tokens / 1_000_000) * _CLAUDE_OUTPUT_COST_PER_1M
        ) * max(1, package_ir.total_files)
        return CostEstimate(
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            estimated_api_calls=max(1, package_ir.total_files),
            estimated_cost_usd=round(cost_usd, 4),
            engine_name="claude-api",
        )

    def health_check(self) -> bool:
        try:
            message = self._client.messages.create(
                model=self._model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "Reply with OK"}],
            )
            return bool(message.content)
        except Exception:  # noqa: BLE001
            return False
