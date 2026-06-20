import json
import os
import re
from pathlib import Path

from cryptography.fernet import Fernet

from infra.telemetry import get_logger

logger = get_logger("integrations.token_store")

DEFAULT_STORE_DIR = Path.home() / ".agent-os" / "tokens"

_SAFE_APP_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,98}$")


class TokenStore:
    def __init__(self, store_dir: str | Path | None = None, key: str | None = None):
        self._store_dir = Path(store_dir) if store_dir else DEFAULT_STORE_DIR
        self._store_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

        raw_key = key or os.environ.get("AGENT_OS_TOKEN_KEY")
        if not raw_key:
            raise ValueError(
                "Token encryption key required: pass key= or set AGENT_OS_TOKEN_KEY env var"
            )
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)

    def _safe_path(self, app_name: str) -> Path:
        if not _SAFE_APP_NAME.match(app_name):
            raise ValueError(f"Invalid app_name: must be alphanumeric/hyphens/underscores")
        path = (self._store_dir / f"{app_name}.enc").resolve()
        if not path.is_relative_to(self._store_dir.resolve()):
            raise ValueError("Path traversal blocked")
        return path

    def store_token(self, app_name: str, token_data: dict) -> None:
        payload = json.dumps(token_data).encode()
        encrypted = self._fernet.encrypt(payload)
        path = self._safe_path(app_name)
        path.write_bytes(encrypted)
        path.chmod(0o600)
        logger.info("stored token for app=%s", app_name)

    def get_token(self, app_name: str) -> dict | None:
        path = self._safe_path(app_name)
        if not path.exists():
            return None
        encrypted = path.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        return json.loads(decrypted)

    def delete_token(self, app_name: str) -> None:
        path = self._safe_path(app_name)
        if path.exists():
            path.unlink()
            logger.info("deleted token for app=%s", app_name)

    def list_apps(self) -> list[str]:
        return [p.stem for p in self._store_dir.glob("*.enc")]
