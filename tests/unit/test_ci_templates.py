"""Verify CI/CD integration templates are valid YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "ci-templates"


class TestGitHubAction:
    def test_action_yml_exists(self):
        assert (TEMPLATES_DIR / "github" / "action.yml").is_file()

    def test_action_yml_valid_yaml(self):
        data = yaml.safe_load((TEMPLATES_DIR / "github" / "action.yml").read_text())
        assert "name" in data
        assert "inputs" in data
        assert "runs" in data

    def test_action_has_required_inputs(self):
        data = yaml.safe_load((TEMPLATES_DIR / "github" / "action.yml").read_text())
        inputs = data["inputs"]
        assert "source" in inputs
        assert "mode" in inputs
        assert "engine" in inputs
        assert inputs["source"]["required"] is True

    def test_action_has_outputs(self):
        data = yaml.safe_load((TEMPLATES_DIR / "github" / "action.yml").read_text())
        assert "exit-code" in data["outputs"]
        assert "report" in data["outputs"]

    def test_example_workflow_valid_yaml(self):
        data = yaml.safe_load((TEMPLATES_DIR / "github" / "example-workflow.yml").read_text())
        assert "jobs" in data
        assert "analyze" in data["jobs"]


class TestGitLabTemplate:
    def test_gitlab_template_exists(self):
        assert (TEMPLATES_DIR / "gitlab" / ".gitlab-ci-rosforge.yml").is_file()

    def test_gitlab_template_valid_yaml(self):
        data = yaml.safe_load((TEMPLATES_DIR / "gitlab" / ".gitlab-ci-rosforge.yml").read_text())
        assert "variables" in data
        assert ".rosforge-analyze" in data
        assert ".rosforge-migrate" in data

    def test_gitlab_template_has_variables(self):
        data = yaml.safe_load((TEMPLATES_DIR / "gitlab" / ".gitlab-ci-rosforge.yml").read_text())
        variables = data["variables"]
        assert "ROSFORGE_SOURCE" in variables
        assert "ROSFORGE_ENGINE" in variables
        assert "ROSFORGE_TARGET_DISTRO" in variables
