from __future__ import annotations

import os
import re
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("io.voice.tts")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


class TTSConfig(BaseModel):
    backend: str = "api"
    voice: str = "alloy"
    speed: float = 1.0
    model: str = "tts-1"
    api_base: str = "https://api.openai.com/v1"
    api_key: str | None = None

    def get_api_key(self) -> str:
        return self.api_key or os.environ.get("OPENAI_API_KEY", "")


class TTSEngine:
    def __init__(self, config: TTSConfig | None = None) -> None:
        self._config = config or TTSConfig()
        self._client = httpx.AsyncClient(timeout=30.0)

    async def speak(self, text: str) -> AsyncIterator[bytes]:
        sentences = self._split_sentences(text)
        for sentence in sentences:
            audio = await self.speak_sentence(sentence)
            yield audio

    async def speak_sentence(self, sentence: str) -> bytes:
        sentence = sentence.strip()
        if not sentence:
            return b""

        url = f"{self._config.api_base}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._config.get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._config.model,
            "input": sentence,
            "voice": self._config.voice,
            "speed": self._config.speed,
        }

        response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.content

    def _split_sentences(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        parts = _SENTENCE_SPLIT.split(text.strip())
        return [p for p in parts if p.strip()]

    async def close(self) -> None:
        await self._client.aclose()
