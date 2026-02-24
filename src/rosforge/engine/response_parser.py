"""Parse raw AI engine responses into typed result models."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from rosforge.models.plan import (
    CostEstimate,
    MigrationPlan,
    TransformAction,
    TransformStrategy,
)
from rosforge.models.result import ChangeEntry, TransformedFile
from rosforge.utils.subprocess_utils import extract_json_from_text

# ---------------------------------------------------------------------------
# Cost tables (USD per 1 000 tokens — approximate public pricing)
# ---------------------------------------------------------------------------

_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    # engine_name -> (input_cost_per_1k, output_cost_per_1k)
    "claude-3-5-sonnet": (0.003, 0.015),
    "claude-3-5-haiku": (0.001, 0.005),
    "claude-3-opus": (0.015, 0.075),
    "claude-opus-4": (0.015, 0.075),
    "claude-sonnet-4": (0.003, 0.015),
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.010, 0.030),
    "gemini-1.5-pro": (0.00125, 0.005),
    "gemini-1.5-flash": (0.000075, 0.0003),
    "gemini-2.0-flash": (0.0001, 0.0004),
}

# Fallback cost when engine is unknown
_DEFAULT_COST_PER_1K = (0.003, 0.015)


def _lookup_cost(engine_name: str) -> tuple[float, float]:
    """Return (input_cost, output_cost) per 1k tokens for the given engine.

    Performs prefix matching so ``"claude-3-5-sonnet-20241022"`` matches
    ``"claude-3-5-sonnet"``.
    """
    name_lower = engine_name.lower()
    # Sort by key length descending so more-specific keys (e.g. "gpt-4o-mini")
    # are checked before shorter prefixes (e.g. "gpt-4o").
    for key in sorted(_COST_PER_1K_TOKENS, key=len, reverse=True):
        if name_lower.startswith(key):
            return _COST_PER_1K_TOKENS[key]
    return _DEFAULT_COST_PER_1K


# ---------------------------------------------------------------------------
# Enhanced JSON extraction
# ---------------------------------------------------------------------------

def _try_parse_json(text: str) -> dict | None:
    """Try to parse text as JSON, returning None on failure."""
    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    return None


def _extract_nested_fences(text: str) -> dict | None:
    """Extract JSON from nested or multiple fenced blocks.

    Handles cases like:
    - ```json\\n{...}\\n``` (standard)
    - ```\\n{...}\\n``` (no language tag)
    - Nested fences where outer is not JSON
    - Multiple fences — tries each one
    """
    # Find all ```json ... ``` blocks (greedy inner content)
    json_fences = re.findall(r"```json\s*([\s\S]*?)```", text, re.IGNORECASE)
    for candidate in json_fences:
        result = _try_parse_json(candidate.strip())
        if result is not None:
            return result

    # Find all generic ``` ... ``` blocks
    generic_fences = re.findall(r"```(?:\w+)?\s*([\s\S]*?)```", text)
    for candidate in generic_fences:
        result = _try_parse_json(candidate.strip())
        if result is not None:
            return result

    return None


def _recover_partial_json(text: str) -> dict | None:
    """Attempt partial JSON recovery by finding the outermost { ... } block.

    Useful when the AI response has trailing text after a valid JSON object,
    or when the response is cut off mid-array.
    """
    # Find the first '{' and attempt to parse from there
    start = text.find("{")
    if start == -1:
        return None

    # Walk forward, tracking brace depth to find matching '}'
    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                result = _try_parse_json(candidate)
                if result is not None:
                    return result
                break

    return None


def _extract_dict(raw: str) -> dict | None:
    """Try all JSON extraction strategies on a raw string.

    Order:
    1. Full text is valid JSON.
    2. ```json fenced block(s) — including nested/multiple.
    3. Generic fenced block(s).
    4. Partial JSON recovery (outermost { ... }).
    5. Returns None.
    """
    # Strategy 1: entire text
    result = _try_parse_json(raw)
    if result is not None:
        return result

    # Strategies 2 + 3: fenced blocks (handles nested and multiple)
    result = _extract_nested_fences(raw)
    if result is not None:
        return result

    # Strategy 4: partial recovery
    result = _recover_partial_json(raw)
    if result is not None:
        return result

    return None


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def compute_confidence(transformed_content: str, original_content: str) -> float:
    """Compute a confidence score for a transformed file.

    Uses a combination of heuristics:
    - Similarity ratio between original and transformed (penalises unchanged files
      and over-changed files).
    - Presence of known ROS2 identifiers in the transformed output.
    - Absence of known ROS1 identifiers (roscpp, rospy patterns) in output.

    Args:
        transformed_content: The AI-transformed file content.
        original_content: The original ROS1 file content.

    Returns:
        A float in [0.0, 1.0]. Higher is more confident.
    """
    if not transformed_content or not original_content:
        return 0.0

    # Similarity ratio (0=completely different, 1=identical)
    ratio = SequenceMatcher(None, original_content, transformed_content).ratio()

    # Penalise if unchanged (ratio == 1.0 likely means no migration happened)
    if ratio >= 0.99:
        similarity_score = 0.1
    elif ratio >= 0.80:
        # Small changes — good for CMake/package.xml, mediocre for C++/Python
        similarity_score = 0.5
    elif ratio >= 0.30:
        # Substantial changes — typical for C++/Python migrations
        similarity_score = 0.85
    else:
        # Very different — might be hallucination or complete rewrite
        similarity_score = 0.4

    # Bonus: ROS2 markers present in transformed output
    ros2_markers = [
        "rclcpp", "rclpy", "ament", "rclcpp::Node",
        "create_publisher", "create_subscription", "get_logger",
    ]
    transformed_lower = transformed_content.lower()
    ros2_bonus = sum(0.05 for m in ros2_markers if m.lower() in transformed_lower)
    ros2_bonus = min(ros2_bonus, 0.20)

    # Penalty: ROS1 markers still present (incomplete migration)
    ros1_markers = [
        "ros::NodeHandle", "rospy.init_node", "nh.advertise",
        "nh.subscribe", "ros::Publisher", "catkin_package(",
    ]
    ros1_penalty = sum(0.05 for m in ros1_markers if m in transformed_content)
    ros1_penalty = min(ros1_penalty, 0.30)

    score = similarity_score + ros2_bonus - ros1_penalty
    return max(0.0, min(score, 1.0))


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_cost_usd(
    engine_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate the USD cost of an AI API call.

    Args:
        engine_name: The model/engine identifier (e.g. ``"claude-3-5-sonnet"``).
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.

    Returns:
        Estimated cost in USD.
    """
    input_cost_per_1k, output_cost_per_1k = _lookup_cost(engine_name)
    cost = (input_tokens / 1000.0) * input_cost_per_1k
    cost += (output_tokens / 1000.0) * output_cost_per_1k
    return round(cost, 6)


# ---------------------------------------------------------------------------
# Response parsers
# ---------------------------------------------------------------------------

def parse_transform_response(raw: str) -> TransformedFile:
    """Parse an AI transform response into a TransformedFile.

    Parsing priority:
    1. Full JSON parse of raw text.
    2. Extract from ```json fence (handles nested/multiple).
    3. Extract from generic ``` fence.
    4. Partial JSON recovery.
    5. parse_failure — return minimal stub with raw text as content.

    Args:
        raw: Raw string output from the AI backend.

    Returns:
        A TransformedFile instance (may have empty fields on parse failure).
    """
    data = _extract_dict(raw)

    if data is None:
        return TransformedFile(
            source_path="",
            target_path="",
            transformed_content=raw,
            confidence=0.0,
            strategy_used="ai_driven",
            warnings=["parse_failure: could not extract JSON from AI response"],
        )

    changes = [
        ChangeEntry(
            description=c.get("description", ""),
            line_range=c.get("line_range", ""),
            reason=c.get("reason", ""),
        )
        for c in data.get("changes", [])
    ]

    return TransformedFile(
        source_path=data.get("source_path", ""),
        target_path=data.get("target_path", ""),
        transformed_content=data.get("transformed_content", ""),
        confidence=float(data.get("confidence", 0.0)),
        strategy_used=data.get("strategy_used", "ai_driven"),
        warnings=data.get("warnings", []),
        changes=changes,
    )


def parse_analyze_response(raw: str) -> MigrationPlan:
    """Parse an AI analyze response into a MigrationPlan.

    Args:
        raw: Raw string output from the AI backend.

    Returns:
        A MigrationPlan (may have empty fields on parse failure).
    """
    data = _extract_dict(raw)

    if data is None:
        return MigrationPlan(
            warnings=["parse_failure: could not extract JSON from AI analyze response"],
        )

    actions = []
    for a in data.get("actions", []):
        try:
            strategy = TransformStrategy(a.get("strategy", "ai_driven"))
        except ValueError:
            strategy = TransformStrategy.AI_DRIVEN

        actions.append(
            TransformAction(
                source_path=a.get("source_path", ""),
                target_path=a.get("target_path", ""),
                strategy=strategy,
                description=a.get("description", ""),
                estimated_complexity=int(a.get("estimated_complexity", 1)),
                confidence=float(a.get("confidence", 0.0)),
            )
        )

    return MigrationPlan(
        package_name=data.get("package_name", ""),
        target_ros2_distro=data.get("target_ros2_distro", "humble"),
        actions=actions,
        overall_confidence=float(data.get("overall_confidence", 0.0)),
        warnings=data.get("warnings", []),
        summary=data.get("summary", ""),
    )


def parse_structured_output(raw: str, schema_keys: list[str]) -> dict:
    """Parse structured output from API backends, validating expected keys.

    Args:
        raw: Raw string from API backend.
        schema_keys: Expected top-level keys in the JSON object.

    Returns:
        Parsed dict. Missing keys are filled with ``None``.
        On parse failure returns a dict with all keys set to ``None``
        and a ``"_parse_error"`` key.
    """
    data = _extract_dict(raw)
    if data is None:
        result: dict = {k: None for k in schema_keys}
        result["_parse_error"] = "could not extract JSON from response"
        return result

    return {k: data.get(k) for k in schema_keys}
