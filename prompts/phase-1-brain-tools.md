# Phase 1 — Brain + Tools (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 1 of agent-os.

## Context

Phase 0 is complete (commit `6099759`). The foundation is in place: AgentState, Agent protocol,
Tool base + Permission enum, registries, LangGraph E2E, telemetry, 20 passing tests, CI.

Phase 1 adds the Brain (knowledge layer) and Tools (capability layer) — two independent tracks.

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 0 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Brain) + Track B (Tools) — sequential or parallel
STEP 4: INSTALL — add any new deps (qdrant-client, httpx), verify imports
STEP 5: TEST — write all tests, run pytest, fix until green
STEP 6: VERIFY (5-step verification protocol):
6a. @test-runner → all tests green
6b. @architect + /code-review high → no layer violations
6c. @security-auditor + /security-review → no injection, path traversal, SSRF
6d. @gate-checker → all exit criteria pass with evidence
6e. Fix any failures → re-run from 6a
STEP 7: /log → commit → push

## What to build

### Track A — Brain (`/brain/`)

**`brain/schema.py`** — Note schema (Pydantic):

- `Note(BaseModel)`: title, content, tags, backlinks, created_at, embedding (optional)

**`brain/obsidian.py`** — Obsidian vault interface:

- `write_note(note: Note)` → writes markdown file to vault path
- `read_note(title: str) -> Note` → reads note by title
- `list_notes() -> list[str]` → lists all note titles
- `find_backlinks(title: str) -> list[Note]` → finds notes linking to this title
- Vault path configurable (default: `./brain_vault/`)
- Path validation — no traversal outside the vault

**`brain/qdrant.py`** — Qdrant vector store:

- `embed_note(note: Note)` → generates embedding, upserts into Qdrant
- `search(query: str, top_k: int = 5) -> list[Note]` → semantic search
- Configurable embedding function (start with a simple hash-based stub, swap later)
- Qdrant client connection configurable (default: localhost:6333)
- Must work with a mock/in-memory backend for tests (don't require a running Qdrant)

**`brain/librarian.py`** — Read-before-act query API:

- `query(question: str) -> list[Note]` — single entry point for agents
- Combines: Qdrant semantic search → enrich with Obsidian backlinks → return context
- This is the "read-before-act" implementation from the engineering principles

### Track B — Tools (`/tools/`)

**`tools/bash.py`** — BashTool:

- `permission = Permission.SHELL`
- Executes shell commands via `asyncio.create_subprocess_shell`
- Returns stdout/stderr, respects timeout (default 30s)
- NEVER use raw `subprocess` — this is the blessed path

**`tools/file.py`** — FileTool:

- `permission = Permission.WRITE`
- Operations: `read`, `write`, `list_dir`, `exists`
- Path validation: no escaping allowed paths (prevent path traversal)

**`tools/web.py`** — WebTool:

- `permission = Permission.READ`
- HTTP GET/POST via `httpx` (async)
- Returns response body, status code, headers
- Timeout (default 10s) and response size limits
- Block internal/private IPs (SSRF prevention)

**Update `tools/registry.py`** — register all three tools on import.

### Integration test

**`tests/test_integration/test_brain_tools.py`** — proves both tracks work together:

1. Agent stub queries the brain (`librarian.query()`) and gets context
2. Agent stub calls a permission-gated tool and it respects the permission

### Tests to write

- `tests/test_brain/test_obsidian.py` — write note → read it back, verify backlinks
- `tests/test_brain/test_qdrant.py` — embed note → search → find it (mock/in-memory)
- `tests/test_brain/test_librarian.py` — query returns relevant notes
- `tests/test_tools/test_bash.py` — execute `echo hello`, verify output, verify timeout
- `tests/test_tools/test_file.py` — write file → read it back, path traversal blocked
- `tests/test_tools/test_web.py` — mock HTTP call, verify response handling
- `tests/test_tools/test_permissions.py` — verify each tool declares correct Permission
- `tests/test_integration/test_brain_tools.py` — brain + tool integration

## Exit gate (ALL must pass)

- [ ] `brain/obsidian.py` — write a note → read it back
- [ ] `brain/qdrant.py` — embed a note → retrieve it semantically
- [ ] `brain/librarian.py` — `query()` returns relevant notes
- [ ] `tools/bash.py` — executes a command, returns output
- [ ] `tools/file.py` — writes and reads a file
- [ ] `tools/web.py` — makes an HTTP request (mocked in tests)
- [ ] Each tool declares the correct `Permission` level
- [ ] A SHELL-permission tool blocks without approval (permission gate test)
- [ ] Integration: agent stub queries brain AND calls a tool
- [ ] All `pytest` green

## Non-negotiable rules

- Layer rule: agents call Tools, never raw `subprocess`
- Tools use the `Tool` base class from `tools/base.py`
- Brain is queried through `librarian.py`, never directly through Qdrant
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`
- Typed state only — nothing outside `AgentState`
- Do NOT build Phase 2 work (orchestration, departments)

## Security checklist (enforced at VERIFY step)

- [ ] BashTool: no command injection (shell metacharacters handled)
- [ ] FileTool: no path traversal (validate paths, block `..`)
- [ ] WebTool: no SSRF (block private/internal IPs)
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization (no pickle, no yaml.load)
- [ ] No eval/exec outside sandboxed tools
- [ ] Permission gates enforced on all tools

## When stuck

Follow `docs/WHEN_STUCK.md`:

1. Read the actual error
2. One targeted fix, re-run
3. Consult docs/decisions
4. Search memory: `node .claude/memory/memory.js search "<error>"`
5. Max 2 retries on same fix, then log blocker and STOP

## End of session

- Run `/exit-gate` to verify all criteria pass
- Run `/log` to record the session
- Run `/save-session` to save full conversation
- Commit and push
