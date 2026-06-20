import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from io_layer.event_bus import VOICE_ACK, VOICE_REQUEST, VOICE_RESULT, get_event_bus, reset_event_bus, AgentEvent
from io_layer.voice.controller import VoiceController
from io_layer.voice.stt import STTConfig, STTEngine
from io_layer.voice.tts import TTSConfig, TTSEngine


async def _audio_stream(data: bytes = b"fake-audio"):
    yield data


@pytest.fixture(autouse=True)
def _clean_bus():
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture()
def mock_stt():
    engine = MagicMock(spec=STTEngine)
    engine.transcribe = AsyncMock(return_value="hello")
    return engine


@pytest.fixture()
def mock_tts():
    engine = MagicMock(spec=TTSEngine)
    engine.speak_sentence = AsyncMock(return_value=b"ack-audio")

    async def mock_speak(text):
        yield b"result-audio"

    engine.speak = mock_speak
    return engine


@pytest.fixture()
def mock_graph_factory():
    graph = MagicMock()
    graph.invoke.return_value = {
        "result": "here is the result",
        "approved": True,
        "lane": "instant",
    }
    return lambda: graph


@pytest.fixture()
def controller(mock_stt, mock_tts, mock_graph_factory):
    return VoiceController(
        stt=mock_stt, tts=mock_tts, graph_factory=mock_graph_factory
    )


@pytest.mark.asyncio
async def test_instant_request_responds_immediately(controller, mock_stt):
    mock_stt.transcribe = AsyncMock(return_value="hello")

    chunks = []
    async for chunk in controller.handle_voice_input(_audio_stream()):
        chunks.append(chunk)

    assert len(chunks) >= 1
    assert b"result-audio" in chunks


@pytest.mark.asyncio
async def test_deep_request_ack_first(controller, mock_stt, mock_tts):
    mock_stt.transcribe = AsyncMock(
        return_value="build a REST API for user management"
    )

    chunks = []
    async for chunk in controller.handle_voice_input(_audio_stream()):
        chunks.append(chunk)

    assert len(chunks) >= 1
    assert chunks[0] == b"ack-audio"
    mock_tts.speak_sentence.assert_awaited()


@pytest.mark.asyncio
async def test_voice_publishes_events(controller, mock_stt):
    mock_stt.transcribe = AsyncMock(return_value="hello")

    events = []
    bus = get_event_bus()

    async def capture(event: AgentEvent):
        events.append(event)

    bus.subscribe(capture)

    async for _ in controller.handle_voice_input(_audio_stream()):
        pass

    event_types = [e.type for e in events]
    assert VOICE_REQUEST in event_types
    assert VOICE_RESULT in event_types


@pytest.mark.asyncio
async def test_empty_transcription_produces_no_output(controller, mock_stt):
    mock_stt.transcribe = AsyncMock(return_value="")

    chunks = []
    async for chunk in controller.handle_voice_input(_audio_stream()):
        chunks.append(chunk)

    assert len(chunks) == 0
