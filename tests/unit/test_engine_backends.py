"""Unit tests for Gemini CLI/API, OpenAI CLI/API, and Claude API engine backends."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rosforge.models.config import EngineConfig
from rosforge.models.ir import FileType, PackageIR, PackageMetadata, SourceFile
from rosforge.models.plan import MigrationPlan, TransformAction, TransformStrategy
from rosforge.models.result import SubprocessResult

# ── Shared fixtures ────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_ir() -> PackageIR:
    sf = SourceFile(
        relative_path="src/talker.cpp",
        file_type=FileType.CPP,
        content="#include <ros/ros.h>\nint main() { ros::init(); }",
        line_count=2,
    )
    return PackageIR(
        source_path=Path("/tmp/pkg"),
        metadata=PackageMetadata(name="test_pkg", version="0.1.0"),
        source_files=[sf],
        total_files=1,
        total_lines=2,
        cpp_files=1,
    )


@pytest.fixture()
def sample_plan() -> MigrationPlan:
    return MigrationPlan(
        package_name="test_pkg",
        actions=[
            TransformAction(
                source_path="src/talker.cpp",
                target_path="src/talker.cpp",
                strategy=TransformStrategy.AI_DRIVEN,
                confidence=0.8,
            )
        ],
    )


@pytest.fixture()
def cli_config() -> EngineConfig:
    return EngineConfig(name="gemini", mode="cli", timeout_seconds=10)


@pytest.fixture()
def api_config() -> EngineConfig:
    return EngineConfig(name="gemini", mode="api", timeout_seconds=10, api_key="test-key")


VALID_ANALYZE_JSON = '{"package_name":"test_pkg","target_ros2_distro":"humble","overall_confidence":0.8,"summary":"ok","warnings":[],"actions":[]}'
VALID_TRANSFORM_JSON = '{"source_path":"src/talker.cpp","target_path":"src/talker.cpp","transformed_content":"// ros2","confidence":0.9,"strategy_used":"ai_driven","warnings":[],"changes":[]}'


# ── GeminiCLIEngine tests ──────────────────────────────────────────────────────


class TestGeminiCLIEngine:
    def _make_engine(self, config: EngineConfig):
        from rosforge.engine.gemini.cli_backend import GeminiCLIEngine

        return GeminiCLIEngine(config)

    def test_health_check_success(self, cli_config):
        mock_result = SubprocessResult(status="success", exit_code=0, parsed_json={})
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            assert engine.health_check() is True

    def test_health_check_failure(self, cli_config):
        mock_result = SubprocessResult(status="error", exit_code=1, error_message="not found")
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            assert engine.health_check() is False

    def test_analyze_calls_subprocess(self, cli_config, sample_ir):
        mock_result = SubprocessResult(
            status="success",
            exit_code=0,
            raw_stdout=VALID_ANALYZE_JSON,
            parsed_json={"package_name": "test_pkg"},
        )
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            plan = engine.analyze(sample_ir)
            assert plan.package_name == "test_pkg"

    def test_transform_calls_subprocess(self, cli_config, sample_ir, sample_plan):
        mock_result = SubprocessResult(
            status="success",
            exit_code=0,
            raw_stdout=VALID_TRANSFORM_JSON,
            parsed_json={"source_path": "src/talker.cpp"},
        )
        sf = sample_ir.source_files[0]
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            result = engine.transform(sf, sample_plan)
            assert result.source_path == "src/talker.cpp"
            assert result.original_content == sf.content

    def test_analyze_timeout_raises(self, cli_config, sample_ir):
        mock_result = SubprocessResult(
            status="timeout",
            exit_code=-1,
            error_message="Command timed out after 10s",
        )
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            with pytest.raises(RuntimeError, match="timed out"):
                engine.analyze(sample_ir)

    def test_analyze_error_raises(self, cli_config, sample_ir):
        mock_result = SubprocessResult(
            status="error",
            exit_code=1,
            error_message="gemini not found",
        )
        with patch("rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(cli_config)
            with pytest.raises(RuntimeError, match="error"):
                engine.analyze(sample_ir)

    def test_estimate_cost_returns_estimate(self, cli_config, sample_ir):
        engine = self._make_engine(cli_config)
        estimate = engine.estimate_cost(sample_ir)
        assert estimate.engine_name == "gemini-cli"
        assert estimate.estimated_cost_usd == 0.0
        assert estimate.estimated_api_calls == 1
        assert estimate.total_input_tokens > 0

    def test_model_arg_included(self, sample_ir):
        config = EngineConfig(name="gemini", mode="cli", timeout_seconds=10, model="gemini-1.5-pro")
        mock_result = SubprocessResult(
            status="success",
            exit_code=0,
            raw_stdout=VALID_ANALYZE_JSON,
            parsed_json={},
        )
        with patch(
            "rosforge.engine.gemini.cli_backend.run_command", return_value=mock_result
        ) as mock_cmd:
            from rosforge.engine.gemini.cli_backend import GeminiCLIEngine

            engine = GeminiCLIEngine(config)
            engine.analyze(sample_ir)
            call_args = mock_cmd.call_args[0][0]
            assert "--model" in call_args
            assert "gemini-1.5-pro" in call_args


# ── GeminiAPIEngine tests ──────────────────────────────────────────────────────


class TestGeminiAPIEngine:
    def _make_engine_with_mock_genai(self, config: EngineConfig):
        mock_genai = MagicMock()
        mock_genai.GenerationConfig = MagicMock(return_value={})
        with patch.dict("sys.modules", {"google.generativeai": mock_genai}):
            # Re-import with mock
            import importlib

            import rosforge.engine.gemini.api_backend as mod

            # Patch the module-level flag
            with (
                patch.object(mod, "_GENAI_AVAILABLE", True),
                patch.object(mod, "genai", mock_genai),
            ):
                from rosforge.engine.gemini.api_backend import GeminiAPIEngine

                engine = GeminiAPIEngine.__new__(GeminiAPIEngine)
                engine._config = config
                engine._builder = __import__(
                    "rosforge.engine.prompt_builder", fromlist=["PromptBuilder"]
                ).PromptBuilder()
                engine._model_name = config.model or "gemini-1.5-pro"
                engine._genai = mock_genai
                return engine, mock_genai

    def test_import_error_without_sdk(self, api_config):
        import rosforge.engine.gemini.api_backend as mod

        with patch.object(mod, "_GENAI_AVAILABLE", False):
            from rosforge.engine.gemini.api_backend import GeminiAPIEngine

            with pytest.raises(ImportError, match="google-genai"):
                GeminiAPIEngine(api_config)

    def test_estimate_cost_returns_estimate(self, api_config):
        import rosforge.engine.gemini.api_backend as mod

        mock_genai = MagicMock()
        with patch.object(mod, "_GENAI_AVAILABLE", True), patch.object(mod, "genai", mock_genai):
            from rosforge.engine.gemini.api_backend import GeminiAPIEngine

            engine = GeminiAPIEngine.__new__(GeminiAPIEngine)
            engine._config = api_config
            engine._builder = __import__(
                "rosforge.engine.prompt_builder", fromlist=["PromptBuilder"]
            ).PromptBuilder()
            engine._model_name = "gemini-1.5-pro"
            sample_ir_local = PackageIR(
                source_path=Path("/tmp/pkg"),
                metadata=PackageMetadata(name="test_pkg", version="0.1.0"),
                source_files=[
                    SourceFile(
                        relative_path="src/talker.cpp",
                        file_type=FileType.CPP,
                        content="int main() {}",
                        line_count=1,
                    )
                ],
                total_files=1,
                total_lines=1,
                cpp_files=1,
            )
            estimate = engine.estimate_cost(sample_ir_local)
            assert estimate.engine_name == "gemini-api"
            assert estimate.estimated_api_calls == 1

    def test_analyze_calls_api(self, api_config):
        import rosforge.engine.gemini.api_backend as mod

        mock_genai = MagicMock()
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = VALID_ANALYZE_JSON
        mock_model_instance.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model_instance
        mock_genai.GenerationConfig.return_value = {}

        sample_ir_local = PackageIR(
            source_path=Path("/tmp/pkg"),
            metadata=PackageMetadata(name="test_pkg", version="0.1.0"),
            source_files=[
                SourceFile(
                    relative_path="src/talker.cpp",
                    file_type=FileType.CPP,
                    content="int main() {}",
                    line_count=1,
                )
            ],
            total_files=1,
            total_lines=1,
            cpp_files=1,
        )

        with patch.object(mod, "_GENAI_AVAILABLE", True), patch.object(mod, "genai", mock_genai):
            from rosforge.engine.gemini.api_backend import GeminiAPIEngine

            engine = GeminiAPIEngine.__new__(GeminiAPIEngine)
            engine._config = api_config
            engine._builder = __import__(
                "rosforge.engine.prompt_builder", fromlist=["PromptBuilder"]
            ).PromptBuilder()
            engine._model_name = "gemini-1.5-pro"
            plan = engine.analyze(sample_ir_local)
            assert plan.package_name == "test_pkg"

    def test_health_check_success(self, api_config):
        import rosforge.engine.gemini.api_backend as mod

        mock_genai = MagicMock()
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "OK"
        mock_model_instance.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model_instance

        with patch.object(mod, "_GENAI_AVAILABLE", True), patch.object(mod, "genai", mock_genai):
            from rosforge.engine.gemini.api_backend import GeminiAPIEngine

            engine = GeminiAPIEngine.__new__(GeminiAPIEngine)
            engine._config = api_config
            engine._builder = MagicMock()
            engine._model_name = "gemini-1.5-pro"
            assert engine.health_check() is True

    def test_health_check_failure(self, api_config):
        import rosforge.engine.gemini.api_backend as mod

        mock_genai = MagicMock()
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.side_effect = Exception("API error")
        mock_genai.GenerativeModel.return_value = mock_model_instance

        with patch.object(mod, "_GENAI_AVAILABLE", True), patch.object(mod, "genai", mock_genai):
            from rosforge.engine.gemini.api_backend import GeminiAPIEngine

            engine = GeminiAPIEngine.__new__(GeminiAPIEngine)
            engine._config = api_config
            engine._builder = MagicMock()
            engine._model_name = "gemini-1.5-pro"
            assert engine.health_check() is False


# ── OpenAICLIEngine tests ──────────────────────────────────────────────────────


class TestOpenAICLIEngine:
    def _make_engine(self, config: EngineConfig):
        from rosforge.engine.openai.cli_backend import OpenAICLIEngine

        return OpenAICLIEngine(config)

    def test_health_check_success(self, cli_config):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        mock_result = SubprocessResult(status="success", exit_code=0, parsed_json={})
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            assert engine.health_check() is True

    def test_health_check_failure(self, cli_config):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        mock_result = SubprocessResult(status="error", exit_code=1, error_message="not found")
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            assert engine.health_check() is False

    def test_analyze_parses_wrapped_response(self, sample_ir):
        import json

        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        # OpenAI CLI returns JSON with choices[0].message.content
        cli_response = json.dumps({"choices": [{"message": {"content": VALID_ANALYZE_JSON}}]})
        mock_result = SubprocessResult(
            status="success",
            exit_code=0,
            raw_stdout=cli_response,
            parsed_json={},
        )
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            plan = engine.analyze(sample_ir)
            assert plan.package_name == "test_pkg"

    def test_transform_parses_wrapped_response(self, sample_ir, sample_plan):
        import json

        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        cli_response = json.dumps({"choices": [{"message": {"content": VALID_TRANSFORM_JSON}}]})
        mock_result = SubprocessResult(
            status="success",
            exit_code=0,
            raw_stdout=cli_response,
            parsed_json={},
        )
        sf = sample_ir.source_files[0]
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            result = engine.transform(sf, sample_plan)
            assert result.source_path == "src/talker.cpp"
            assert result.original_content == sf.content

    def test_timeout_raises(self, sample_ir):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        mock_result = SubprocessResult(
            status="timeout",
            exit_code=-1,
            error_message="Command timed out after 10s",
        )
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            with pytest.raises(RuntimeError, match="timed out"):
                engine.analyze(sample_ir)

    def test_error_raises(self, sample_ir):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        mock_result = SubprocessResult(
            status="error",
            exit_code=1,
            error_message="openai not found",
        )
        with patch("rosforge.engine.openai.cli_backend.run_command", return_value=mock_result):
            engine = self._make_engine(config)
            with pytest.raises(RuntimeError, match="error"):
                engine.analyze(sample_ir)

    def test_estimate_cost_returns_estimate(self, sample_ir):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        engine = self._make_engine(config)
        estimate = engine.estimate_cost(sample_ir)
        assert estimate.engine_name == "openai-cli"
        assert estimate.estimated_cost_usd == 0.0
        assert estimate.estimated_api_calls == 1

    def test_extract_content_malformed_returns_raw(self):
        config = EngineConfig(name="openai", mode="cli", timeout_seconds=10)
        engine = self._make_engine(config)
        raw = "not valid json"
        assert engine._extract_content(raw) == raw


# ── OpenAIAPIEngine tests ──────────────────────────────────────────────────────


class TestOpenAIAPIEngine:
    def test_import_error_without_sdk(self):
        import rosforge.engine.openai.api_backend as mod

        with patch.object(mod, "_OPENAI_AVAILABLE", False):
            from rosforge.engine.openai.api_backend import OpenAIAPIEngine

            config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
            with pytest.raises(ImportError, match="openai"):
                OpenAIAPIEngine(config)

    def _make_engine_with_mock(self, config: EngineConfig):
        import rosforge.engine.openai.api_backend as mod

        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        with (
            patch.object(mod, "_OPENAI_AVAILABLE", True),
            patch.object(mod, "_openai_sdk", mock_openai),
        ):
            from rosforge.engine.openai.api_backend import OpenAIAPIEngine

            engine = OpenAIAPIEngine.__new__(OpenAIAPIEngine)
            engine._config = config
            engine._builder = __import__(
                "rosforge.engine.prompt_builder", fromlist=["PromptBuilder"]
            ).PromptBuilder()
            engine._model_name = config.model or "gpt-4o"
            engine._client = mock_client
            return engine, mock_client

    def test_analyze_calls_api(self, sample_ir):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)

        mock_response = MagicMock()
        mock_response.choices[0].message.content = VALID_ANALYZE_JSON
        mock_client.chat.completions.create.return_value = mock_response

        plan = engine.analyze(sample_ir)
        assert plan.package_name == "test_pkg"
        mock_client.chat.completions.create.assert_called_once()

    def test_transform_calls_api(self, sample_ir, sample_plan):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)

        mock_response = MagicMock()
        mock_response.choices[0].message.content = VALID_TRANSFORM_JSON
        mock_client.chat.completions.create.return_value = mock_response

        sf = sample_ir.source_files[0]
        result = engine.transform(sf, sample_plan)
        assert result.source_path == "src/talker.cpp"
        assert result.original_content == sf.content

    def test_api_error_raises_runtime_error(self, sample_ir):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_client.chat.completions.create.side_effect = Exception("API failed")

        with pytest.raises(RuntimeError, match="OpenAI API error"):
            engine.analyze(sample_ir)

    def test_health_check_success(self):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "OK"
        mock_client.chat.completions.create.return_value = mock_response
        assert engine.health_check() is True

    def test_health_check_failure(self):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_client.chat.completions.create.side_effect = Exception("Network error")
        assert engine.health_check() is False

    def test_estimate_cost_returns_estimate(self, sample_ir):
        config = EngineConfig(name="openai", mode="api", timeout_seconds=10, api_key="key")
        engine, _ = self._make_engine_with_mock(config)
        estimate = engine.estimate_cost(sample_ir)
        assert estimate.engine_name == "openai-api"
        assert estimate.estimated_api_calls == 1
        assert estimate.estimated_cost_usd >= 0.0


# ── ClaudeAPIEngine tests ──────────────────────────────────────────────────────


class TestClaudeAPIEngine:
    def test_import_error_without_sdk(self):
        import rosforge.engine.claude.api_backend as mod

        with patch.object(mod, "_ANTHROPIC_AVAILABLE", False):
            from rosforge.engine.claude.api_backend import ClaudeAPIEngine

            config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
            with pytest.raises(ImportError, match="anthropic"):
                ClaudeAPIEngine(config)

    def _make_engine_with_mock(self, config: EngineConfig):
        import rosforge.engine.claude.api_backend as mod

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        with (
            patch.object(mod, "_ANTHROPIC_AVAILABLE", True),
            patch.object(mod, "_anthropic_sdk", mock_anthropic),
        ):
            from rosforge.engine.claude.api_backend import ClaudeAPIEngine

            engine = ClaudeAPIEngine.__new__(ClaudeAPIEngine)
            engine._config = config
            engine._builder = __import__(
                "rosforge.engine.prompt_builder", fromlist=["PromptBuilder"]
            ).PromptBuilder()
            engine._model_name = config.model or "claude-3-5-sonnet-20241022"
            engine._client = mock_client
            return engine, mock_client

    def test_analyze_calls_api(self, sample_ir):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=VALID_ANALYZE_JSON)]
        mock_client.messages.create.return_value = mock_message

        plan = engine.analyze(sample_ir)
        assert plan.package_name == "test_pkg"
        mock_client.messages.create.assert_called_once()

    def test_analyze_uses_system_and_user(self, sample_ir):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=VALID_ANALYZE_JSON)]
        mock_client.messages.create.return_value = mock_message

        engine.analyze(sample_ir)
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert "messages" in call_kwargs
        assert call_kwargs["messages"][0]["role"] == "user"

    def test_transform_calls_api(self, sample_ir, sample_plan):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=VALID_TRANSFORM_JSON)]
        mock_client.messages.create.return_value = mock_message

        sf = sample_ir.source_files[0]
        result = engine.transform(sf, sample_plan)
        assert result.source_path == "src/talker.cpp"
        assert result.original_content == sf.content

    def test_api_error_raises_runtime_error(self, sample_ir):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_client.messages.create.side_effect = Exception("API failed")

        with pytest.raises(RuntimeError, match="Claude API error"):
            engine.analyze(sample_ir)

    def test_health_check_success(self):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="OK")]
        mock_client.messages.create.return_value = mock_message
        assert engine.health_check() is True

    def test_health_check_failure(self):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_client.messages.create.side_effect = Exception("Network error")
        assert engine.health_check() is False

    def test_health_check_empty_content(self):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_message = MagicMock()
        mock_message.content = []
        mock_client.messages.create.return_value = mock_message
        assert engine.health_check() is False

    def test_estimate_cost_returns_estimate(self, sample_ir):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, _ = self._make_engine_with_mock(config)
        estimate = engine.estimate_cost(sample_ir)
        assert estimate.engine_name == "claude-api"
        assert estimate.estimated_api_calls == 1
        assert estimate.estimated_cost_usd >= 0.0

    def test_empty_content_returns_empty_string(self, sample_ir):
        config = EngineConfig(name="claude", mode="api", timeout_seconds=10, api_key="key")
        engine, mock_client = self._make_engine_with_mock(config)
        mock_message = MagicMock()
        mock_message.content = []
        mock_client.messages.create.return_value = mock_message
        # analyze with empty response should return parse_failure plan
        plan = engine.analyze(sample_ir)
        assert any("parse_failure" in w for w in plan.warnings)
