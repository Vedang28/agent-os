"""LLM integration layer for agents.

Routes through the user's AI coding tool (Claude Code, Codex, Cursor, etc.)
when available, falls back to direct API calls only when no host tool is
detected.

Priority:
  1. Host coding tool (claude, codex, cursor, etc.) — uses the user's
     existing auth, billing, and model selection
  2. Direct API (Anthropic, Google, Ollama) — requires API keys in env vars
  3. Placeholder — structured text so the pipeline doesn't crash

Usage inside an agent::

    from agents.llm import call_llm

    class MyAgent:
        SYSTEM_PROMPT = "You are a database architect..."

        async def run(self, state):
            response = await call_llm(
                task_type="code",
                system=self.SYSTEM_PROMPT,
                user=f"Design a schema for: {state['request']}",
            )
            return {"draft": response}
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx

from agents.host_detector import HostTool, detect_host
from infra.model_router import route
from infra.telemetry import get_logger

logger = get_logger("agents.llm")

_TIMEOUT = 120.0

# Cache the detected host so we don't re-detect every call
_host: HostTool | None = None


def _get_host() -> HostTool:
    global _host
    if _host is None:
        _host = detect_host()
    return _host


def reset_host():
    """Reset cached host detection (for testing)."""
    global _host
    _host = None


async def call_llm(
    *,
    task_type: str = "code",
    system: str,
    user: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Call an LLM — through the host tool if available, else direct API.

    Returns the assistant's text response. Raises on errors so callers can
    handle or let LangGraph retry.
    """
    host = _get_host()

    # Priority 1: Use the host coding tool
    if host.available and host.cli:
        result = await _call_host_tool(host, system, user)
        if result is not None:
            return result
        logger.warning("host tool %s failed, falling back to direct API", host.name)

    # Priority 2: Direct API calls
    config = route(task_type)
    _max = max_tokens or config.max_tokens
    _temp = temperature if temperature is not None else config.temperature

    if config.provider == "anthropic":
        return await _call_anthropic(config, system, user, _max, _temp)
    elif config.provider == "google":
        return await _call_google(config, system, user, _max, _temp)
    elif config.provider == "local":
        return await _call_ollama(config, system, user, _max, _temp)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")


# -------------------------------------------------------------------
# Host tool execution
# -------------------------------------------------------------------

async def _call_host_tool(host: HostTool, system: str, user: str) -> str | None:
    """Delegate to the user's coding tool CLI."""
    prompt = f"{system}\n\n{user}"

    try:
        if host.name == "claude_code":
            return await _call_claude_code(host.cli, prompt)
        elif host.name == "codex":
            return await _call_codex(host.cli, prompt)
        elif host.name == "aider":
            return await _call_aider(host.cli, prompt)
        else:
            return await _call_generic_cli(host.cli, prompt)
    except Exception as e:
        logger.warning("host tool %s error: %s", host.name, e)
        return None


async def _call_claude_code(cli: str, prompt: str) -> str:
    """Call Claude Code CLI: claude -p 'prompt' --output-format text"""
    proc = await asyncio.create_subprocess_exec(
        cli, "-p", prompt, "--output-format", "text",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")[:500]
        logger.warning("claude code exit %d: %s", proc.returncode, err)
        return None

    return stdout.decode(errors="replace").strip()


async def _call_codex(cli: str, prompt: str) -> str:
    """Call Codex CLI: codex -q 'prompt'"""
    proc = await asyncio.create_subprocess_exec(
        cli, "-q", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)

    if proc.returncode != 0:
        return None

    return stdout.decode(errors="replace").strip()


async def _call_aider(cli: str, prompt: str) -> str:
    """Call Aider: aider --message 'prompt' --yes --no-auto-commits"""
    proc = await asyncio.create_subprocess_exec(
        cli, "--message", prompt, "--yes", "--no-auto-commits",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)

    if proc.returncode != 0:
        return None

    return stdout.decode(errors="replace").strip()


async def _call_generic_cli(cli: str, prompt: str) -> str:
    """Generic fallback: cli 'prompt'"""
    proc = await asyncio.create_subprocess_exec(
        cli, prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300.0)

    if proc.returncode != 0:
        return None

    return stdout.decode(errors="replace").strip()


# -------------------------------------------------------------------
# Direct API calls (fallback when no host tool)
# -------------------------------------------------------------------

async def _call_anthropic(config, system: str, user: str, max_tokens: int, temperature: float) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, returning placeholder")
        return _placeholder(system, user)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.api_base}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.model_name,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        logger.info(
            "anthropic response model=%s tokens_in=%s tokens_out=%s",
            config.model_name,
            data.get("usage", {}).get("input_tokens"),
            data.get("usage", {}).get("output_tokens"),
        )
        return text


async def _call_google(config, system: str, user: str, max_tokens: int, temperature: float) -> str:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set, returning placeholder")
        return _placeholder(system, user)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.api_base}/v1beta/models/{config.model_name}:generateContent",
            params={"key": api_key},
            headers={"content-type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return text
        return ""


async def _call_ollama(config, system: str, user: str, max_tokens: int, temperature: float) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{config.api_base}/api/chat",
                json={
                    "model": config.model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
    except httpx.ConnectError:
        logger.warning("Ollama not running at %s, returning placeholder", config.api_base)
        return _placeholder(system, user)


def _placeholder(system: str, user: str) -> str:
    """Fallback when no host tool and no API key configured."""
    return (
        f"[LLM_PLACEHOLDER — no AI coding tool or API key detected]\n"
        f"System role: {system[:200]}\n"
        f"Request: {user[:500]}\n"
        f"--- This output needs a real LLM call to be useful. ---"
    )
