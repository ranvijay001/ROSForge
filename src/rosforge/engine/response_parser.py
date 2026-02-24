"""Parse raw AI engine responses into typed result models."""

from __future__ import annotations

import re

from rosforge.models.plan import (
    CostEstimate,
    MigrationPlan,
    TransformAction,
    TransformStrategy,
)
from rosforge.models.result import ChangeEntry, TransformedFile
from rosforge.utils.subprocess_utils import extract_json_from_text


def _extract_dict(raw: str) -> dict | None:
    """Try all JSON extraction strategies on a raw string."""
    return extract_json_from_text(raw)


def parse_transform_response(raw: str) -> TransformedFile:
    """Parse an AI transform response into a TransformedFile.

    Parsing priority:
    1. Full JSON parse of raw text.
    2. Extract from ```json fence.
    3. Extract from generic ``` fence.
    4. parse_failure — return minimal stub with raw text as content.

    Args:
        raw: Raw string output from the AI backend.

    Returns:
        A TransformedFile instance (may have empty fields on parse failure).
    """
    data = _extract_dict(raw)

    if data is None:
        # Strategy 4: parse_failure — preserve raw as transformed content
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
