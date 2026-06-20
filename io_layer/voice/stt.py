from __future__ import annotations

import os
from collections.abc import AsyncIterator

import httpx
from pydantic import BaseModel

from infra.telemetry import get_logger

logger = get_logger("io.voice.stt")


class STTConfig(BaseModel):
    backend: str = "api"
    model: str = "whisper-1"
    language: str = "en"
    api_base: str = "https://api.openai.com/v1"
    api_key: str | None = None

    def get_api_key(self) -> str:
        key = self.api_key or os.environ.get("OPENAI_API_KEY", "")
        return key


class STTEngine:
    def __init__(self, config: STTConfig | None = None) -> None:
        self._config = config or STTConfig()
        self._client = httpx.AsyncClient(timeout=30.0)

    async def transcribe(self, audio_stream: AsyncIterator[bytes]) -> str:
        chunks: list[bytes] = []
        async for chunk in audio_stream:
            chunks.append(chunk)

        audio_data = b"".join(chunks)
        if not audio_data or self._is_silence(audio_data):
            return ""

        return await self._call_api(audio_data)

    async def transcribe_file(self, path: str) -> str:
        with open(path, "rb") as f:
            audio_data = f.read()

        if not audio_data or self._is_silence(audio_data):
            return ""

        return await self._call_api(audio_data)

    async def _call_api(self, audio_data: bytes) -> str:
        url = f"{self._config.api_base}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self._config.get_api_key()}"}

        response = await self._client.post(
            url,
            headers=headers,
            files={"file": ("audio.wav", audio_data, "audio/wav")},
            data={"model": self._config.model, "language": self._config.language},
        )
        response.raise_for_status()
        result = response.json()
        return result.get("text", "")

    def _is_silence(self, audio: bytes) -> bool:
        if len(audio) < 44:
            return True
        non_zero = sum(1 for b in audio[44:] if b not in (0, 128))
        return non_zero < len(audio[44:]) * 0.01

    async def close(self) -> None:
        await self._client.aclose()
