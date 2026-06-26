"""LLM integration layer for agents.

Provides ``call_llm()`` — a unified async function that routes through the
model router and calls the appropriate provider (Anthropic, Google, or local
Ollama) via httpx.  Every agent calls this instead of producing hardcoded text.

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

import json
import os

import httpx

from infra.model_router import route
from infra.telemetry import get_logger

logger = get_logger("agents.llm")

_TIMEOUT = 120.0


async def call_llm(
    *,
    task_type: str = "code",
    system: str,
    user: str,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Call an LLM through the model router.

    Returns the assistant's text response.  Raises on HTTP/provider errors
    so callers can handle or let LangGraph retry.
    """
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
    """Fallback when no API key is configured.

    Returns a structured placeholder that downstream agents can still parse,
    so the pipeline doesn't crash in development/testing.  The placeholder
    clearly marks itself as AI-generated-pending so critics catch it.
    """
    return (
        f"[LLM_PLACEHOLDER — no API key configured]\n"
        f"System role: {system[:200]}\n"
        f"Request: {user[:500]}\n"
        f"--- This output needs a real LLM call to be useful. ---"
    )
