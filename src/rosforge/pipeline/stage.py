"""Pipeline stage abstract base class and error model."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PipelineError(BaseModel):
    """Structured error emitted by a pipeline stage."""

    stage_name: str
    message: str
    recoverable: bool = False


class PipelineStage(ABC):
    """Abstract base class for all pipeline stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable stage identifier."""

    @abstractmethod
    def execute(self, ctx: "PipelineContext") -> "PipelineContext":  # noqa: F821
        """Run this stage against the provided context.

        Args:
            ctx: Mutable pipeline context carrying all stage I/O.

        Returns:
            Updated context (same object, mutated in place).
        """
