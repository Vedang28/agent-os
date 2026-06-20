import json
import os

import pytest
from cryptography.fernet import Fernet

from integrations.token_store import TokenStore


@pytest.fixture()
def store(tmp_path):
    key = Fernet.generate_key().decode()
    return TokenStore(store_dir=tmp_path, key=key)


def test_store_and_retrieve(store):
    data = {"access_token": "abc123", "refresh_token": "xyz"}
    store.store_token("gmail", data)
    result = store.get_token("gmail")
    assert result == data


def test_get_nonexistent_returns_none(store):
    assert store.get_token("nonexistent") is None


def test_delete_token(store):
    store.store_token("slack", {"token": "x"})
    assert store.get_token("slack") is not None
    store.delete_token("slack")
    assert store.get_token("slack") is None


def test_delete_nonexistent_no_error(store):
    store.delete_token("nothing")


def test_encrypted_at_rest(tmp_path):
    key = Fernet.generate_key().decode()
    s = TokenStore(store_dir=tmp_path, key=key)
    data = {"access_token": "supersecret"}
    s.store_token("test", data)

    raw = (tmp_path / "test.enc").read_bytes()
    assert b"supersecret" not in raw
    assert raw != json.dumps(data).encode()


def test_list_apps(store):
    store.store_token("gmail", {"t": "1"})
    store.store_token("slack", {"t": "2"})
    apps = store.list_apps()
    assert sorted(apps) == ["gmail", "slack"]


def test_missing_key_raises(tmp_path):
    with pytest.raises(ValueError, match="Token encryption key required"):
        TokenStore(store_dir=tmp_path, key=None)


def test_key_from_env(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("AGENT_OS_TOKEN_KEY", key)
    s = TokenStore(store_dir=tmp_path)
    s.store_token("test", {"v": "1"})
    assert s.get_token("test") == {"v": "1"}


def test_path_traversal_blocked(store):
    with pytest.raises(ValueError, match="Invalid app_name"):
        store.store_token("../../etc/evil", {"t": "1"})


def test_path_traversal_slashes_blocked(store):
    with pytest.raises(ValueError, match="Invalid app_name"):
        store.store_token("foo/bar", {"t": "1"})


def test_valid_app_names(store):
    for name in ["gmail", "my-app", "app_v2", "Notion"]:
        store.store_token(name, {"t": "1"})
        assert store.get_token(name) == {"t": "1"}
