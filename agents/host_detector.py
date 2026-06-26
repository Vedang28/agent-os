"""Detect which AI coding tool AgentOS is running inside.

Checks environment variables, running processes, and config files to figure
out whether we're inside Claude Code, Codex, Cursor, Windsurf, Aider, etc.
Then exposes the right CLI command to delegate work to that tool.

Usage::

    from agents.host_detector import detect_host, HostTool

    host = detect_host()
    # host.name = "claude_code"
    # host.cli  = "claude"
    # host.available = True
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from infra.telemetry import get_logger

logger = get_logger("agents.host_detector")


@dataclass
class HostTool:
    name: str
    cli: str | None
    available: bool
    version: str | None = None

    # How to invoke: each tool has a different CLI interface
    # "prompt" = pass a prompt string as argument
    # "stdin"  = pipe the prompt via stdin
    # "flag"   = use --prompt or -p flag
    invocation: str = "prompt"


# Detection order matters — first match wins
_DETECTORS: list[tuple[str, callable]] = []


def _register(name: str):
    def decorator(fn):
        _DETECTORS.append((name, fn))
        return fn
    return decorator


def detect_host() -> HostTool:
    """Detect the AI coding tool this process is running inside."""
    # Check explicit override first
    override = os.environ.get("AGENT_OS_HOST")
    if override:
        for name, detector in _DETECTORS:
            if name == override:
                result = detector()
                if result:
                    logger.info("host override: %s (available=%s)", name, result.available)
                    return result

        logger.info("host override=%s (forced, no detector)", override)
        return HostTool(name=override, cli=override, available=True)

    # Auto-detect
    for name, detector in _DETECTORS:
        result = detector()
        if result and result.available:
            logger.info("detected host: %s", name)
            return result

    logger.info("no AI coding tool detected, falling back to direct API")
    return HostTool(name="none", cli=None, available=False)


# -------------------------------------------------------------------
# Individual detectors
# -------------------------------------------------------------------

@_register("claude_code")
def _detect_claude_code() -> HostTool | None:
    # Claude Code sets CLAUDE_CODE=1 or similar env vars
    indicators = [
        os.environ.get("CLAUDE_CODE"),
        os.environ.get("CLAUDE_SESSION_ID"),
        os.environ.get("CLAUDE_PROJECT_DIR"),
    ]
    cli = shutil.which("claude")

    if any(indicators) or cli:
        return HostTool(
            name="claude_code",
            cli=cli or "claude",
            available=cli is not None,
            invocation="prompt",
        )
    return None


@_register("codex")
def _detect_codex() -> HostTool | None:
    indicators = [
        os.environ.get("CODEX_HOME"),
        os.environ.get("CODEX_SESSION"),
    ]
    cli = shutil.which("codex")

    if any(indicators) or cli:
        return HostTool(
            name="codex",
            cli=cli or "codex",
            available=cli is not None,
            invocation="prompt",
        )
    return None


@_register("cursor")
def _detect_cursor() -> HostTool | None:
    indicators = [
        os.environ.get("CURSOR_SESSION"),
        os.environ.get("CURSOR_WORKSPACE"),
    ]
    # Cursor runs as an IDE, check if its CLI extension exists
    cli = shutil.which("cursor")

    if any(indicators) or cli:
        return HostTool(
            name="cursor",
            cli=cli or "cursor",
            available=cli is not None,
            invocation="prompt",
        )
    return None


@_register("windsurf")
def _detect_windsurf() -> HostTool | None:
    indicators = [
        os.environ.get("WINDSURF_SESSION"),
    ]
    cli = shutil.which("windsurf")

    if any(indicators) or cli:
        return HostTool(
            name="windsurf",
            cli=cli or "windsurf",
            available=cli is not None,
            invocation="prompt",
        )
    return None


@_register("aider")
def _detect_aider() -> HostTool | None:
    cli = shutil.which("aider")
    if cli:
        return HostTool(
            name="aider",
            cli=cli,
            available=True,
            invocation="prompt",
        )
    return None


@_register("kimi")
def _detect_kimi() -> HostTool | None:
    indicators = [
        os.environ.get("KIMI_SESSION"),
        os.environ.get("KIMI_API_KEY"),
    ]
    cli = shutil.which("kimi")

    if any(indicators) or cli:
        return HostTool(
            name="kimi",
            cli=cli or "kimi",
            available=cli is not None,
            invocation="prompt",
        )
    return None
