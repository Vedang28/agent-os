import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from io_layer.voice.tts import TTSConfig, TTSEngine


@pytest.fixture()
def engine():
    config = TTSConfig(api_key="test-key")
    return TTSEngine(config=config)


def test_config_defaults():
    config = TTSConfig()
    assert config.backend == "api"
    assert config.voice == "alloy"
    assert config.speed == 1.0
    assert config.model == "tts-1"


def test_sentence_splitting(engine):
    text = "Hello world. How are you? I am fine!"
    sentences = engine._split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Hello world."
    assert sentences[1] == "How are you?"
    assert sentences[2] == "I am fine!"


def test_sentence_splitting_single_sentence(engine):
    sentences = engine._split_sentences("Just one sentence.")
    assert len(sentences) == 1


def test_sentence_splitting_empty(engine):
    assert engine._split_sentences("") == []
    assert engine._split_sentences("   ") == []


@pytest.mark.asyncio
async def test_speak_sentence(engine):
    mock_response = MagicMock()
    mock_response.content = b"audio-bytes-here"
    mock_response.raise_for_status = MagicMock()

    with patch.object(engine._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await engine.speak_sentence("Hello world.")

    assert result == b"audio-bytes-here"
    mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_speak_empty_sentence(engine):
    result = await engine.speak_sentence("")
    assert result == b""


@pytest.mark.asyncio
async def test_speak_streams_sentences(engine):
    mock_response = MagicMock()
    mock_response.content = b"chunk"
    mock_response.raise_for_status = MagicMock()

    with patch.object(engine._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        chunks = []
        async for chunk in engine.speak("First sentence. Second sentence."):
            chunks.append(chunk)

    assert len(chunks) == 2
    assert all(c == b"chunk" for c in chunks)


@pytest.mark.asyncio
async def test_speak_empty_text(engine):
    chunks = []
    async for chunk in engine.speak(""):
        chunks.append(chunk)
    assert len(chunks) == 0
