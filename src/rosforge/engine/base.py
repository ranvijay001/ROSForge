"""Engine abstraction layer for ROSForge AI backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from rosforge.models.config import EngineConfig
from rosforge.models.ir import PackageIR, SourceFile
from rosforge.models.plan import CostEstimate, MigrationPlan
from rosforge.models.result import TransformedFile


class EngineInterface(ABC):
    """Abstract base class for all AI engine backends."""

    @abstractmethod
    def analyze(self, package_ir: PackageIR) -> MigrationPlan:
        """Analyse a ROS1 package and produce a migration plan.

        Args:
            package_ir: Parsed intermediate representation of the package.

        Returns:
            A MigrationPlan describing what transformations are needed.
        """

    @abstractmethod
    def transform(self, source_file: SourceFile, plan: MigrationPlan) -> TransformedFile:
        """Transform a single source file according to the migration plan.

        Args:
            source_file: The file to transform.
            plan: The migration plan produced by analyze().

        Returns:
            A TransformedFile with updated content and change metadata.
        """

    @abstractmethod
    def fix(
        self,
        source_file: SourceFile,
        transformed_content: str,
        error_message: str,
        plan: MigrationPlan,
    ) -> TransformedFile:
        """Fix a failed transformation using AI-driven error correction.

        Args:
            source_file: The original source file.
            transformed_content: The previously transformed (broken) content.
            error_message: The error or validation failure message.
            plan: The migration plan for context.

        Returns:
            A TransformedFile with corrected content.
        """

    @abstractmethod
    def estimate_cost(self, package_ir: PackageIR) -> CostEstimate:
        """Estimate the token/cost for processing this package.

        Args:
            package_ir: Parsed intermediate representation.

        Returns:
            A CostEstimate with token counts and USD estimate.
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the engine backend is available and functional.

        Returns:
            True if the backend is ready, False otherwise.
        """


class EngineRegistry:
    """Registry mapping engine names to their implementation classes."""

    _registry: ClassVar[dict[str, type[EngineInterface]]] = {}

    @classmethod
    def register(cls, name: str, engine_class: type[EngineInterface]) -> None:
        """Register an engine implementation under the given name.

        Args:
            name: Unique identifier string (e.g. "claude-cli").
            engine_class: Concrete subclass of EngineInterface.
        """
        cls._registry[name] = engine_class

    @classmethod
    def get(cls, name: str, config: EngineConfig) -> EngineInterface:
        """Instantiate a registered engine by name.

        Args:
            name: Engine identifier (e.g. "claude-cli").
            config: Engine configuration passed to the constructor.

        Returns:
            An initialised EngineInterface instance.

        Raises:
            KeyError: If no engine is registered under that name.
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry)) or "(none)"
            raise KeyError(
                f"Unknown engine {name!r}. Available engines: {available}"
            )
        return cls._registry[name](config)

    @classmethod
    def available(cls) -> list[str]:
        """Return sorted list of registered engine names."""
        return sorted(cls._registry)


def _try_register(name: str, module_path: str, class_name: str) -> None:
    """Attempt to register an engine; silently skip if not available."""
    try:
        import importlib

        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        EngineRegistry.register(name, cls)
    except (ImportError, AttributeError):
        pass  # Backend not installed or not yet implemented


def _register_defaults() -> None:
    """Pre-register all known engine backends (graceful on missing)."""
    backends = [
        ("claude-cli", "rosforge.engine.claude.cli_backend", "ClaudeCLIEngine"),
        ("claude-api", "rosforge.engine.claude.api_backend", "ClaudeAPIEngine"),
        ("gemini-cli", "rosforge.engine.gemini.cli_backend", "GeminiCLIEngine"),
        ("gemini-api", "rosforge.engine.gemini.api_backend", "GeminiAPIEngine"),
        ("openai-cli", "rosforge.engine.openai.cli_backend", "OpenAICLIEngine"),
        ("openai-api", "rosforge.engine.openai.api_backend", "OpenAIAPIEngine"),
    ]
    for name, module_path, class_name in backends:
        _try_register(name, module_path, class_name)


_register_defaults()
