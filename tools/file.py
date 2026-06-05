from pathlib import Path

from infra.telemetry import get_logger

from tools.base import Permission, Tool

logger = get_logger("tools.file")


class FileTool(Tool):
    name = "file"
    permission = Permission.WRITE

    def __init__(self, allowed_root: str | Path = "."):
        self._allowed_root = Path(allowed_root).resolve()
        self._ops: dict[str, callable] = {
            "read": self._read,
            "write": self._write,
            "list_dir": self._list_dir,
            "exists": self._exists,
        }

    async def _run(
        self, *, operation: str, path: str, content: str | None = None
    ) -> str:
        resolved = self._validate_path(path)
        handler = self._ops.get(operation)
        if handler is None:
            raise ValueError(f"unknown operation: {operation}")
        return handler(resolved, content)

    def _read(self, resolved: Path, _content: str | None) -> str:
        return resolved.read_text(encoding="utf-8")

    def _write(self, resolved: Path, content: str | None) -> str:
        if content is None:
            raise ValueError("content is required for write")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        logger.info("wrote file: %s", resolved)
        return f"written: {resolved}"

    def _list_dir(self, resolved: Path, _content: str | None) -> str:
        if not resolved.is_dir():
            raise NotADirectoryError(str(resolved))
        return "\n".join(p.name for p in sorted(resolved.iterdir()))

    def _exists(self, resolved: Path, _content: str | None) -> str:
        return str(resolved.exists()).lower()

    def _validate_path(self, path: str) -> Path:
        p = Path(path)
        if ".." in p.parts:
            raise PermissionError(f"Path traversal blocked: {path}")
        resolved = (self._allowed_root / p).resolve()
        if not resolved.is_relative_to(self._allowed_root):
            raise PermissionError(f"Path escapes allowed root: {path}")
        return resolved
