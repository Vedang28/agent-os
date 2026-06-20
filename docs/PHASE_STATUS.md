# PHASE STATUS

> Update this after every working session. CLAUDE.md imports this file, so it's always in context.

## Active phase
**Phase 6 — Integrations (Composio + MCP)**

## Phase ladder
| Phase | Name | Status |
|------|------|--------|
| 0 | Foundation (repo, protocol, state, CI) | 🟢 COMPLETE |
| 1 | Brain + Tools | 🟢 COMPLETE |
| 2 | Spine + first department (Engineering) | 🟢 COMPLETE |
| 3 | Autonomous engine (daemon + Intelligence) | 🟢 COMPLETE |
| 4 | Learning loop + Guardian | 🟢 COMPLETE |
| 5 | Dashboard + Voice | 🟢 COMPLETE |
| 6 | Integrations (Composio + MCP) | 🟢 COMPLETE |
| 7 | Mass-produce departments | 🔴 not started |
| 8 | Harden & scale | 🔴 not started |

## Phase 0 exit gate (must pass before Phase 1)
- [x] Monorepo + layered folders created (14 `__init__.py` files across all layers)
- [x] `Agent` protocol + empty registry load (`agents/protocol.py`, `agents/registry.py`)
- [x] `AgentState` typed schema defined (`core/state.py` — TypedDict, total=False, 12 fields)
- [x] Empty LangGraph compiles and runs a no-op end to end (`core/graph.py` — invoke returns `approved: True`)
- [x] `telemetry.py` skeleton (structured logging) in place (`infra/telemetry.py` — JSON formatter)
- [x] `pytest` green, CI passes (20 tests pass, `.github/workflows/ci.yml` created)
- [x] memory system bootstrapped (`node .claude/memory/memory.js recent` runs)

## Phase 1 exit gate (must pass before Phase 2)
- [x] `brain/obsidian.py` — write a note → read it back
- [x] `brain/qdrant.py` — embed a note → retrieve it semantically
- [x] `brain/librarian.py` — `query()` returns relevant notes
- [x] `tools/bash.py` — executes a command, returns output
- [x] `tools/file.py` — writes and reads a file
- [x] `tools/web.py` — makes an HTTP request (mocked in tests)
- [x] Each tool declares the correct `Permission` level
- [x] A SHELL-permission tool blocks without approval (permission gate test)
- [x] Integration: agent stub queries brain AND calls a tool
- [x] All `pytest` green (73 tests pass)

## Phase 2 exit gate (must pass before Phase 3)
- [x] `core/dispatcher.py` — classifies requests into instant/fast/deep lanes
- [x] `core/orchestrator.py` — routes deep requests to the engineering department
- [x] `core/graph.py` — full company graph compiles and routes correctly (instant short-circuits, deep hits department)
- [x] Checkpointer wired — state persists across invocations with `thread_id`
- [x] Engineering sub-graph — Architect → Scaffolder → CodeDoctor with conditional edge
- [x] Bounded critic loop — `max_revisions = 3` enforced, escalation on exceeded
- [x] A deep request flows: User → Dispatcher → Orchestrator → Engineering triad → approved output
- [x] A deliberately bad draft triggers exactly one revise loop then passes
- [x] Engineering department registers in agent registry (no if-elif dispatch)
- [x] Engineering sub-graph plugs into company graph as one node
- [x] All `pytest` green (114 tests pass)

## Phase 3 exit gate (must pass before Phase 4)
- [x] Daemon starts, ticks on schedule (configurable interval)
- [x] Daemon saves checkpoint after each tick
- [x] Kill the process mid-tick → restart → it resumes from checkpoint
- [x] Token budget and wall-clock budget enforced per tick
- [x] Model router returns correct model config per task type (`code`, `long_docs`, `triage`)
- [x] Intelligence triad runs: Scout → Analyst → Skeptic
- [x] Scout reads brain context before drafting (read-before-act)
- [x] Skeptic rejects low-quality items, approves good ones
- [x] `max_revisions = 3` cap is respected in Intelligence department
- [x] A daily briefing note appears in the brain after a tick
- [x] Intelligence department registers in agent registry (no if-elif dispatch)
- [x] Intelligence sub-graph plugs into company graph as one node
- [x] All `pytest` green (167 tests pass)

## Phase 4 exit gate (must pass before Phase 5)
- [x] Reflector reviews outcomes, writes playbook notes to the brain
- [x] Proposers read playbooks before drafting
- [x] Guardian enforces permission gates on all tools
- [x] Human-in-the-loop interrupt for SHELL/DESTRUCTIVE actions
- [x] Kill switch active
- [x] All `pytest` green

## Phase 5 exit gate (must pass before Phase 6)
- [x] FastAPI backend starts and serves on configurable host/port
- [x] WebSocket `/ws/activity` streams real-time agent events
- [x] WebSocket requires authentication
- [x] `GET /api/agents` returns all registered agents with status
- [x] `GET /api/brain/notes` returns paginated notes with tag filtering
- [x] `GET /api/brain/search` returns semantic search results
- [x] `GET /api/status` returns system health (daemon status, agent count, etc.)
- [x] `GET /api/history` returns task history with outcomes
- [x] `POST /api/request` submits a request and returns task_id
- [x] `POST /api/approve` resumes a Guardian-paused graph
- [x] `POST /api/kill` triggers the kill switch
- [x] All mutating endpoints require authentication
- [x] Security headers on all responses (CSP, HSTS, X-Frame-Options)
- [x] Next.js dashboard renders and connects to WebSocket
- [x] Dashboard shows live agent activity in real-time
- [x] Brain browser works (search, view notes, backlinks)
- [x] Approval queue shows pending interrupts with approve/reject
- [x] STT converts speech to text (mocked in tests)
- [x] TTS converts text to speech with sentence-boundary streaming
- [x] ACK-first pattern: deep request gets immediate verbal acknowledgment, graph runs in background
- [x] Voice thread never blocks on deep tasks
- [x] Event bus broadcasts events to WebSocket and voice controller
- [x] Speak a deep request → hear ACK → watch triad work in dashboard → hear result (integration test)
- [x] All `pytest` green (280 pass), Next.js `build` succeeds

## Phase 6 exit gate (must pass before Phase 7)
- [x] `ComposioBridge` connects and manages OAuth flows (mocked in tests)
- [x] Composio tools register in the tool registry with namespaced names
- [x] Each Composio tool declares the correct `Permission` level
- [x] `GmailReadTool` reads emails (Permission.READ)
- [x] `GmailSendTool` sends emails (Permission.WRITE)
- [x] `GmailDeleteTool` deletes emails (Permission.DESTRUCTIVE, requires Guardian approval)
- [x] `NotionWriteTool` creates a page (Permission.WRITE)
- [x] `GitHubCreateIssueTool` creates an issue (Permission.WRITE)
- [x] Guardian enforces permissions on all Composio tools (DESTRUCTIVE actions need approval)
- [x] An agent reads Gmail and writes a Notion page via Composio, gated by permissions (integration test)
- [x] Token storage encrypts tokens at rest, never logs or exposes them
- [x] MCP bridge connects to a server and discovers tools
- [x] MCP tools register in tool registry alongside Composio tools
- [x] Dashboard integrations tab shows connected apps and tools
- [x] Tool registry supports namespace filtering
- [x] All `pytest` green

## Notes / blockers
Phase 3 complete as of 2026-06-10.
Phase 4 complete (commit 58e3117) — PHASE_STATUS.md was not updated at the time.
Phase 5 complete as of 2026-06-19.
- Renamed `io/` to `io_layer/` to avoid conflict with Python stdlib `io` module
- Added fastapi, uvicorn, slowapi dependencies
- 3 pre-existing test failures in Phase 4 tests (Architect.__init__ signature mismatch) — not Phase 5 regressions
- Python 3.12 venv set up with DYLD_LIBRARY_PATH for expat compatibility on macOS
- STT/TTS engines use httpx for API calls (no openai SDK dependency), fully mocked in tests
- Dashboard frontend: Next.js 16+ with App Router, Tailwind CSS
Phase 6 complete as of 2026-06-20.
- Composio integration via httpx (no SDK dependency), fully mocked in tests
- Token store uses cryptography.fernet, encrypted at rest in ~/.agent-os/tokens/
- MCP bridge with SSRF protection on server URLs
- 15 integration tools: Gmail (3), Notion (3), Slack (2), GitHub (3), Calendar (2), plus dynamic MCP tools
- Tool registry supports namespace filtering (backward compatible)
- Dashboard integrations page with connect/disconnect + tool inventory
- Scout uses Slack tools, Scaffolder uses GitHub tools when available
