import pytest

from io_layer.dashboard_api.auth import verify_token, verify_ws_token


@pytest.fixture(autouse=True)
def _set_token(monkeypatch):
    monkeypatch.setenv("AGENT_OS_API_TOKEN", "test-secret-token")


def test_valid_token_passes():
    assert verify_token("test-secret-token") is True


def test_invalid_token_rejected():
    assert verify_token("wrong-token") is False


def test_empty_token_rejected():
    assert verify_token("") is False


def test_ws_token_valid():
    assert verify_ws_token("test-secret-token") is True


def test_ws_token_none():
    assert verify_ws_token(None) is False


def test_ws_token_invalid():
    assert verify_ws_token("bad") is False


def test_missing_env_var_rejects(monkeypatch):
    monkeypatch.delenv("AGENT_OS_API_TOKEN", raising=False)
    assert verify_token("anything") is False
