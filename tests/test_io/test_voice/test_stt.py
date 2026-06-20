import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from io_layer.voice.stt import STTConfig, STTEngine


async def _audio_stream(data: bytes):
    yield data


@pytest.fixture()
def engine():
    config = STTConfig(api_key="test-key")
    return STTEngine(config=config)


def test_config_defaults():
    config = STTConfig()
    assert config.backend == "api"
    assert config.model == "whisper-1"
    assert config.language == "en"


def test_silence_detection(engine):
    silence = bytes(100)
    assert engine._is_silence(silence) is True


def test_non_silence_detection(engine):
    audio = bytes(44) + bytes(range(256)) * 4
    assert engine._is_silence(audio) is False


def test_short_audio_is_silence(engine):
    assert engine._is_silence(b"\x00" * 10) is True


@pytest.mark.asyncio
async def test_transcribe_silence_returns_empty(engine):
    result = await engine.transcribe(_audio_stream(bytes(100)))
    assert result == ""


@pytest.mark.asyncio
async def test_transcribe_calls_api(engine):
    audio_data = bytes(44) + bytes(range(256)) * 4

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "hello world"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(engine._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await engine.transcribe(_audio_stream(audio_data))

    assert result == "hello world"
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args
    assert "audio/transcriptions" in call_kwargs.args[0]


@pytest.mark.asyncio
async def test_transcribe_file(engine, tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_data = bytes(44) + bytes(range(256)) * 4
    audio_file.write_bytes(audio_data)

    mock_response = MagicMock()
    mock_response.json.return_value = {"text": "from file"}
    mock_response.raise_for_status = MagicMock()

    with patch.object(engine._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await engine.transcribe_file(str(audio_file))

    assert result == "from file"
