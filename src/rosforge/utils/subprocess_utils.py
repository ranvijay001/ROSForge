"""Subprocess execution helpers with JSON parsing and timeout handling."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from rosforge.models.result import SubprocessResult


def extract_json_from_text(text: str) -> dict | None:
    """Attempt to extract a JSON object from arbitrary text.

    Tries four strategies in order:
    1. Full text is valid JSON.
    2. Text contains a ```json ... ``` fenced block.
    3. Text contains a generic ``` ... ``` fenced block.
    4. Returns None (caller records parse_failure).

    Args:
        text: Raw text that may contain embedded JSON.

    Returns:
        Parsed dict on success, None otherwise.
    """
    # Strategy 1: entire text is JSON
    stripped = text.strip()
    try:
        result = json.loads(stripped)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: ```json fence
    json_fence = re.search(r"```json\s*([\s\S]*?)```", text, re.IGNORECASE)
    if json_fence:
        try:
            result = json.loads(json_fence.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: generic ``` fence
    generic_fence = re.search(r"```\s*([\s\S]*?)```", text)
    if generic_fence:
        try:
            result = json.loads(generic_fence.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


def run_command(
    cmd: list[str] | str,
    timeout: int = 300,
    cwd: Path | str | None = None,
    verbose: bool = False,
) -> SubprocessResult:
    """Run a shell command and return a structured result.

    Args:
        cmd: Command and arguments as a list, or a shell string.
        timeout: Maximum seconds to wait before marking as timeout.
        cwd: Working directory for the subprocess.
        verbose: If True, print the command before running.

    Returns:
        SubprocessResult with status, raw output, exit code, and parsed JSON.
    """
    if verbose:
        display_cmd = cmd if isinstance(cmd, str) else " ".join(cmd)
        print(f"[rosforge] running: {display_cmd}")

    use_shell = isinstance(cmd, str)

    try:
        proc = subprocess.run(
            cmd,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        return SubprocessResult(
            status="timeout",
            raw_stdout=exc.stdout or "",
            raw_stderr=exc.stderr or "",
            exit_code=-1,
            error_message=f"Command timed out after {timeout}s",
        )
    except Exception as exc:  # noqa: BLE001
        return SubprocessResult(
            status="error",
            error_message=str(exc),
        )

    raw_stdout = proc.stdout or ""
    raw_stderr = proc.stderr or ""
    exit_code = proc.returncode

    if exit_code != 0:
        return SubprocessResult(
            status="error",
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            exit_code=exit_code,
            error_message=f"Command exited with code {exit_code}",
        )

    parsed = extract_json_from_text(raw_stdout)
    if parsed is None:
        return SubprocessResult(
            status="parse_failure",
            raw_stdout=raw_stdout,
            raw_stderr=raw_stderr,
            exit_code=exit_code,
            error_message="Could not parse JSON from stdout",
        )

    return SubprocessResult(
        status="success",
        raw_stdout=raw_stdout,
        raw_stderr=raw_stderr,
        exit_code=exit_code,
        parsed_json=parsed,
    )
