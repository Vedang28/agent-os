# Phase 1 — Brain + Tools

> **Prerequisite:** Phase 0 exit gate must pass. Run `/exit-gate` first to confirm.
> **Parallel tracks begin here.** Track A (Brain) and Track B (Tools) are independent.

## How to run this phase

**Recommended — Parallel with agent view:**
Open `claude agents` and dispatch both tracks simultaneously:
1. `@spine-builder Build Phase 1 Track A: Brain layer — obsidian.py, qdrant.py, librarian.py in /brain`
2. `@edge-builder Build Phase 1 Track B: Tools layer — BashTool, FileTool, WebTool with permissions in /tools`

Then dispatch the merge verification:
3. `@gate-checker Verify Phase 1 exit gate — both tracks`

**Alternative — Workflow:**
Say: `Run a workflow to execute Phase 1 of agent-os — Brain + Tools in parallel tracks`

---

## Track A — Brain (Spine builder)

### Files to create in `/brain/`

**`brain/schema.py`** — Note schema:
```python
from pydantic import BaseModel, Field
from datetime import datetime

class Note(BaseModel):
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    backlinks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    embedding: list[float] | None = None
```

**`brain/obsidian.py`** — Obsidian vault interface:
- `write_note(note: Note)` → writes a markdown file to the vault path
- `read_note(title: str) -> Note` → reads a note by title
- `list_notes() -> list[str]` → lists all note titles
- `find_backlinks(title: str) -> list[Note]` → finds notes linking to this title
- Vault path configurable (default: `./brain_vault/`)

**`brain/qdrant.py`** — Qdrant vector store:
- `embed_note(note: Note)` → generates embedding and upserts into Qdrant
- `search(query: str, top_k: int = 5) -> list[Note]` → semantic search
- Use a configurable embedding function (start with a simple one, swap for real model later)
- Qdrant client connection configurable (default: localhost:6333)

**`brain/librarian.py`** — Read-before-act query API:
- `query(question: str) -> list[Note]` — the single entry point agents use
- Combines: search Qdrant for semantic matches → enrich with Obsidian backlinks → return context
- This is the "read-before-act" implementation

### Tests for Track A
- `tests/test_brain/test_obsidian.py` — write note → read it back, verify backlinks
- `tests/test_brain/test_qdrant.py` — embed note → search → find it (mock or local Qdrant)
- `tests/test_brain/test_librarian.py` — query returns relevant notes

---

## Track B — Tools (Edge builder)

### Files to create in `/tools/`

**`tools/bash.py`** — BashTool:
- `permission = Permission.SHELL`
- Executes shell commands via `asyncio.create_subprocess_shell`
- Returns stdout/stderr, respects timeout
- Never use raw `subprocess` — this is the blessed path

**`tools/file.py`** — FileTool:
- `permission = Permission.WRITE`
- Operations: `read`, `write`, `list_dir`, `exists`
- Path validation (no escaping allowed paths)

**`tools/web.py`** — WebTool:
- `permission = Permission.READ`
- HTTP GET/POST via `aiohttp` or `httpx`
- Returns response body, status code, headers
- Timeout and size limits

**Update `tools/registry.py`** — Register all three tools on import.

### Tests for Track B
- `tests/test_tools/test_bash.py` — execute `echo hello`, verify output, verify timeout
- `tests/test_tools/test_file.py` — write file → read it back
- `tests/test_tools/test_web.py` — mock HTTP call, verify response handling
- `tests/test_tools/test_permissions.py` — verify each tool declares correct Permission

---

## Merge point
An agent stub can:
1. Query the brain (call `librarian.query()`) and get context back
2. Call a permission-gated tool (e.g., `BashTool.execute()`) and have it respect the permission

Write a `tests/test_integration/test_brain_tools.py` that demonstrates both capabilities.

---

## Exit gate (ALL must pass)
- [ ] `brain/obsidian.py` — write a note → read it back
- [ ] `brain/qdrant.py` — embed a note → retrieve it semantically from Qdrant
- [ ] `brain/librarian.py` — `query()` returns relevant notes
- [ ] `tools/bash.py` — executes a command, returns output
- [ ] `tools/file.py` — writes and reads a file
- [ ] `tools/web.py` — makes an HTTP request (mocked in tests)
- [ ] Each tool declares the correct `Permission` level
- [ ] A SHELL-permission tool blocks without approval (permission gate test)
- [ ] Integration: agent stub queries brain AND calls a tool
- [ ] All `pytest` green

## Rules
- Agents call Tools, never raw `subprocess`.
- Tools use the `Tool` base class from `tools/base.py`.
- Brain is queried through `librarian.py`, never directly through Qdrant.
- Do NOT build Phase 2 work (orchestration, departments).
