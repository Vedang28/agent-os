from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable

from infra.telemetry import get_logger
from io_layer.event_bus import (
    VOICE_ACK,
    VOICE_REQUEST,
    VOICE_RESULT,
    publish_event,
)
from io_layer.voice.stt import STTEngine
from io_layer.voice.tts import TTSEngine

logger = get_logger("io.voice.controller")

ACK_MESSAGE = "On it, I'll work on that."


class VoiceController:
    def __init__(
        self,
        stt: STTEngine,
        tts: TTSEngine,
        graph_factory: Callable,
    ) -> None:
        self._stt = stt
        self._tts = tts
        self._graph_factory = graph_factory
        self._background_tasks: dict[str, asyncio.Task] = {}
        self._results: dict[str, str] = {}

    async def handle_voice_input(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[bytes]:
        text = await self._stt.transcribe(audio_stream)
        if not text:
            return

        task_id = str(uuid.uuid4())

        from core.dispatcher import assign_lane

        lane_result = assign_lane({"request": text})
        lane = lane_result.get("lane", "fast")

        await publish_event(VOICE_REQUEST, task_id=task_id, request=text, lane=lane)

        if lane == "instant":
            result = await self._run_graph(text, task_id)
            result_text = result.get("result", "") or ""
            async for chunk in self._tts.speak(result_text):
                yield chunk
            await publish_event(
                VOICE_RESULT, task_id=task_id, result=result_text
            )

        elif lane == "deep":
            ack_audio = await self._tts.speak_sentence(ACK_MESSAGE)
            yield ack_audio
            await publish_event(VOICE_ACK, task_id=task_id)

            bg_task = asyncio.create_task(self._run_graph_background(text, task_id))
            self._background_tasks[task_id] = bg_task

        else:
            result = await self._run_graph(text, task_id)
            result_text = result.get("result", "") or ""
            async for chunk in self._tts.speak(result_text):
                yield chunk
            await publish_event(
                VOICE_RESULT, task_id=task_id, result=result_text
            )

    async def _run_graph(self, request: str, task_id: str) -> dict:
        graph = self._graph_factory()
        result = await asyncio.to_thread(
            graph.invoke,
            {"request": request},
            {"configurable": {"thread_id": task_id}},
        )
        return result

    async def _run_graph_background(self, request: str, task_id: str) -> None:
        try:
            result = await self._run_graph(request, task_id)
            result_text = result.get("result", "") or ""
            self._results[task_id] = result_text
            await publish_event(
                VOICE_RESULT, task_id=task_id, result=result_text
            )
        except Exception:
            logger.exception("background voice task %s failed", task_id)
        finally:
            self._background_tasks.pop(task_id, None)

    async def get_background_result(self, task_id: str) -> str | None:
        return self._results.pop(task_id, None)
