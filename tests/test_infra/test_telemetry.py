import json
import logging

from infra.telemetry import get_logger


def test_get_logger_returns_logger():
    logger = get_logger("test_returns")
    assert isinstance(logger, logging.Logger)


def test_logger_emits_json(capfd):
    logger = get_logger("test_json_emit")
    logger.info("hello world")
    captured = capfd.readouterr()
    entry = json.loads(captured.err)
    assert entry["level"] == "INFO"
    assert entry["logger"] == "test_json_emit"
    assert entry["message"] == "hello world"
    assert "timestamp" in entry


def test_get_logger_idempotent():
    a = get_logger("test_idempotent")
    b = get_logger("test_idempotent")
    assert a is b
    assert len(a.handlers) == 1
