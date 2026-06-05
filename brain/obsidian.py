import json
import re
from pathlib import Path

from infra.telemetry import get_logger

from brain.schema import Note

logger = get_logger("brain.obsidian")

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_UNSAFE_CHARS_RE = re.compile(r"[^\w\s-]")


class ObsidianVault:
    def __init__(self, vault_path: str | Path = "./brain_vault/"):
        self._vault_path = Path(vault_path).resolve()

    def write_note(self, note: Note) -> Path:
        self._vault_path.mkdir(parents=True, exist_ok=True)
        path = self._title_to_path(note.title)
        path.write_text(self._note_to_markdown(note), encoding="utf-8")
        logger.info("wrote note: %s", note.title)
        return path

    def read_note(self, title: str) -> Note:
        path = self._title_to_path(title)
        if not path.exists():
            raise FileNotFoundError(f"Note not found: {title}")
        return self._markdown_to_note(path, title)

    def list_notes(self) -> list[str]:
        if not self._vault_path.exists():
            return []
        return [p.stem for p in sorted(self._vault_path.glob("*.md"))]

    def find_backlinks(self, title: str) -> list[Note]:
        if not self._vault_path.exists():
            return []
        results = []
        for path in self._vault_path.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            links = _WIKILINK_RE.findall(text)
            if title in links:
                results.append(self._markdown_to_note(path, path.stem))
        return results

    def _title_to_path(self, title: str) -> Path:
        if ".." in title:
            raise PermissionError(f"Path traversal blocked in title: {title}")
        safe = _UNSAFE_CHARS_RE.sub("_", title).strip().replace(" ", "_")
        if not safe:
            raise ValueError("Title cannot be empty")
        path = (self._vault_path / f"{safe}.md").resolve()
        self._validate_path(path)
        return path

    def _validate_path(self, path: Path) -> None:
        resolved = path.resolve()
        if not resolved.is_relative_to(self._vault_path):
            raise PermissionError(f"Path escapes vault: {path}")

    def _note_to_markdown(self, note: Note) -> str:
        lines = [
            "---",
            f"title: {json.dumps(note.title)}",
            f"tags: {json.dumps(note.tags)}",
            f"created_at: {json.dumps(note.created_at.isoformat())}",
            "---",
            "",
            note.content,
        ]
        return "\n".join(lines) + "\n"

    def _markdown_to_note(self, path: Path, title: str) -> Note:
        text = path.read_text(encoding="utf-8")
        tags: list[str] = []
        created_at = None
        content = text

        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1].strip()
                content = parts[2].strip()
                for line in frontmatter.splitlines():
                    if line.startswith("tags: "):
                        try:
                            tags = json.loads(line[6:])
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith("created_at: "):
                        raw = line[12:].strip()
                        try:
                            created_at = json.loads(raw)
                        except json.JSONDecodeError:
                            created_at = raw

        backlinks = _WIKILINK_RE.findall(content)

        kwargs: dict = {
            "title": title,
            "content": content,
            "tags": tags,
            "backlinks": backlinks,
        }
        if created_at:
            from datetime import datetime

            try:
                kwargs["created_at"] = datetime.fromisoformat(created_at)
            except ValueError:
                pass

        return Note(**kwargs)
