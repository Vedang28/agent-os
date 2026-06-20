import json
import os
from pathlib import Path

from cryptography.fernet import Fernet

from infra.telemetry import get_logger

logger = get_logger("integrations.token_store")

DEFAULT_STORE_DIR = Path.home() / ".agent-os" / "tokens"


class TokenStore:
    def __init__(self, store_dir: str | Path | None = None, key: str | None = None):
        self._store_dir = Path(store_dir) if store_dir else DEFAULT_STORE_DIR
        self._store_dir.mkdir(parents=True, exist_ok=True)

        raw_key = key or os.environ.get("AGENT_OS_TOKEN_KEY")
        if not raw_key:
            raise ValueError(
                "Token encryption key required: pass key= or set AGENT_OS_TOKEN_KEY env var"
            )
        self._fernet = Fernet(raw_key.encode() if isinstance(raw_key, str) else raw_key)

    def store_token(self, app_name: str, token_data: dict) -> None:
        payload = json.dumps(token_data).encode()
        encrypted = self._fernet.encrypt(payload)
        path = self._store_dir / f"{app_name}.enc"
        path.write_bytes(encrypted)
        logger.info("stored token for app=%s", app_name)

    def get_token(self, app_name: str) -> dict | None:
        path = self._store_dir / f"{app_name}.enc"
        if not path.exists():
            return None
        encrypted = path.read_bytes()
        decrypted = self._fernet.decrypt(encrypted)
        return json.loads(decrypted)

    def delete_token(self, app_name: str) -> None:
        path = self._store_dir / f"{app_name}.enc"
        if path.exists():
            path.unlink()
            logger.info("deleted token for app=%s", app_name)

    def list_apps(self) -> list[str]:
        return [p.stem for p in self._store_dir.glob("*.enc")]
