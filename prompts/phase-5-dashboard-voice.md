# Phase 5 — Dashboard + Voice (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 5 of agent-os.
> **This is when agent-os gets a UI and a voice.**

## Context

Phase 4 is complete. The learning loop is working — the Reflector reviews outcomes, writes playbook notes to the brain, and proposers read those playbooks before drafting (measurable improvement confirmed). The Guardian enforces permission gates on all tools, supports human-in-the-loop interrupt via LangGraph `interrupt()` for SHELL/DESTRUCTIVE actions, and has a kill switch. Two departments (Engineering, Intelligence) are active.

Phase 5 adds the **dashboard** (FastAPI + WebSocket backend and Next.js frontend for live monitoring) and **voice I/O** (speech-to-text input and streaming text-to-speech output with ACK-first pattern for deep tasks).

## What exists now

- `core/state.py` — `AgentState` TypedDict with 12 fields
- `core/graph.py` — full company StateGraph with lane routing, department dispatch, outcome recording
- `core/dispatcher.py` — lane classifier (instant/fast/deep)
- `core/orchestrator.py` — routes to departments via registry
- `core/checkpointer.py` — `get_checkpointer()` wrapping `MemorySaver`
- `agents/protocol.py` — `Agent` Protocol
- `agents/registry.py` — register/get/list_agents/clear
- `agents/guardian.py` — permission gates, human-in-the-loop interrupt, kill switch
- `agents/security_gate.py` — `SecurityGate` ABC
- `agents/departments/engineering/` — Architect → Scaffolder → CodeDoctor triad
- `agents/departments/intelligence/` — Scout → Analyst → Skeptic triad
- `tools/base.py` — `Tool` ABC with `Permission` enum, Guardian-gated execution
- `tools/permissions.py` — permission checker
- `tools/bash.py`, `tools/file.py`, `tools/web.py` — permission-gated tools
- `brain/schema.py` — `Note` Pydantic model
- `brain/obsidian.py` — Obsidian vault (write/read/list/backlinks)
- `brain/qdrant.py` — Qdrant vector store (embed/search)
- `brain/librarian.py` — `Librarian.query()`
- `brain/reflector.py` — reviews outcomes, writes playbook notes
- `brain/outcome.py` — `Outcome` model + `OutcomeStore`
- `brain/playbook.py` — playbook query helper
- `infra/telemetry.py` — `get_logger()` with JSON formatter
- `infra/daemon.py` — daemon heartbeat, job registry, checkpoint persistence
- `infra/model_router.py` — model routing by task type

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 4 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Dashboard backend + frontend) + Track B (Voice I/O) — sequential or parallel
STEP 4: INSTALL — add new deps (fastapi, uvicorn, websockets, next.js, whisper/TTS libs), verify imports
STEP 5: TEST — write all tests, run pytest + npm test, fix until green
STEP 6: VERIFY (5-step verification protocol):
6a. @test-runner → all tests green
6b. @architect + /code-review high → no layer violations
6c. @security-auditor + /security-review → no injection, no secrets, no SSRF, auth on all endpoints
6d. @gate-checker → all exit criteria pass with evidence
6e. Fix any failures → re-run from 6a
STEP 7: /log → commit → push

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
Dispatch:
1. `@spine-builder Build Phase 5 Track A: FastAPI + WebSocket backend for live agent streaming in /io/dashboard_api/`
2. `@edge-builder Build Phase 5 Track B: Voice I/O — STT input + streaming TTS output with ACK-first pattern in /io/voice/`
3. Then: `Build the Next.js dashboard frontend in /dashboard/`

Merge test:
4. `@gate-checker Verify Phase 5 exit gate`

---

## What to build

### Track A — Dashboard Backend (`/io/dashboard_api/`)

**`io/dashboard_api/__init__.py`** — package init

**`io/dashboard_api/app.py`** — FastAPI application:

- `create_app() -> FastAPI` — factory function
- CORS middleware configured (restrict origins, no wildcard in production)
- Security headers middleware (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- Lifespan: on startup, connect to agent registry and daemon; on shutdown, cleanup
- Mount all routers

**`io/dashboard_api/ws.py`** — WebSocket streaming:

- `WebSocket /ws/activity` — real-time agent activity stream:
  - Broadcasts events as agents progress through triads:
    - `{"type": "department_active", "department": "engineering", "timestamp": "..."}`
    - `{"type": "stage_change", "department": "engineering", "stage": "proposer", "agent": "engineering.architect"}`
    - `{"type": "tool_call", "tool": "bash", "permission": "SHELL", "status": "pending_approval"}`
    - `{"type": "approval_request", "action": "...", "details": {...}}`
    - `{"type": "task_complete", "department": "engineering", "success": true, "revisions": 1}`
  - Connection authentication (token-based, verify before accepting)
  - Heartbeat ping/pong to detect stale connections
  - Connection manager: tracks active connections, handles disconnect cleanly

**`io/dashboard_api/routes.py`** — REST endpoints:

- `GET /api/agents` — list all registered agents with status (idle/active/error)
  - Response: `[{"name": "engineering.architect", "role": "proposer", "department": "engineering", "status": "idle"}]`
- `GET /api/brain/notes` — paginated list of brain notes
  - Query params: `?tag=briefing&limit=20&offset=0`
  - Response: `{"notes": [...], "total": 42}`
- `GET /api/brain/search` — semantic search via librarian
  - Query params: `?q=authentication patterns&top_k=5`
  - Response: `{"results": [...], "query": "..."}`
- `GET /api/status` — system health
  - Response: `{"daemon": "running", "tick_count": 12, "last_tick": "...", "agents_registered": 6, "tools_registered": 3, "checkpointer": "active"}`
- `GET /api/history` — recent task history with outcomes
  - Query params: `?department=engineering&limit=20`
  - Response: `{"tasks": [...], "total": 55}`
- `POST /api/request` — submit a new request to the company graph
  - Body: `{"request": "Build a REST API for user management"}`
  - Response: `{"task_id": "...", "lane": "deep", "status": "accepted"}`
  - Runs graph invocation in the background, streams progress via WebSocket
- `POST /api/approve` — approve a pending Guardian interrupt
  - Body: `{"task_id": "...", "approved": true}`
  - Resumes the paused graph via `Command(resume=...)`
- `POST /api/kill` — trigger kill switch
  - Body: `{"reason": "manual"}`
  - Invokes `Guardian.kill()`

**`io/dashboard_api/models.py`** — API response models (Pydantic):

- `AgentResponse`, `NoteResponse`, `SearchResponse`, `StatusResponse`, `HistoryResponse`, `RequestResponse`, `ApprovalRequest`
- All responses use Pydantic v2 models for validation and serialization

**`io/dashboard_api/auth.py`** — API authentication:

- Token-based auth (Bearer token in header)
- `verify_token(token: str) -> bool` — validates the token
- Token configured via environment variable `AGENT_OS_API_TOKEN`
- All mutating endpoints (`POST`) require auth
- Read endpoints optionally require auth (configurable)

---

### Dashboard Frontend (`/dashboard/`)

**Stack:** Next.js 14+ (App Router), Tailwind CSS, shadcn/ui, WebSocket client

**`dashboard/package.json`** — dependencies

**Pages/components:**

- **`app/page.tsx`** — Main dashboard:
  - Real-time activity stream (WebSocket connection)
  - Agent status grid (who's doing what, live updates)
  - Quick stats: daemon status, active tasks, pending approvals

- **`app/brain/page.tsx`** — Brain browser:
  - Note list with tag filtering
  - Semantic search bar
  - Note detail view with backlinks
  - Playbook notes highlighted

- **`app/history/page.tsx`** — Task history:
  - Filterable table of past tasks
  - Per-task detail: department, revisions, outcome, cost
  - Triad replay: step-by-step view of how a task was processed

- **`app/approvals/page.tsx`** — Approval queue:
  - List of pending Guardian interrupts
  - Approve/Reject buttons per item
  - Details: what tool, what action, which agent requested it

- **`components/ActivityFeed.tsx`** — real-time event list (WebSocket)
- **`components/AgentCard.tsx`** — individual agent status card
- **`components/NoteViewer.tsx`** — brain note renderer (markdown)
- **`components/SearchBar.tsx`** — semantic search input
- **`components/ApprovalCard.tsx`** — approval request with action buttons

- **`lib/api.ts`** — API client (fetch wrapper for REST endpoints)
- **`lib/ws.ts`** — WebSocket client (connect, reconnect, event parsing)

---

### Track B — Voice I/O (`/io/voice/`)

**`io/voice/__init__.py`** — package init

**`io/voice/stt.py`** — Speech-to-text:

- `STTEngine` class:
  - `async def transcribe(audio_stream: AsyncIterator[bytes]) -> str` — streaming transcription
  - `async def transcribe_file(path: str) -> str` — transcribe an audio file
  - Backend configurable: Whisper API (default) or local Whisper model
  - `STTConfig(BaseModel)`: backend ("api" | "local"), model ("whisper-1"), language ("en")
  - Returns plain text transcription
  - Handles silence detection (don't send empty audio)

**`io/voice/tts.py`** — Text-to-speech:

- `TTSEngine` class:
  - `async def speak(text: str) -> AsyncIterator[bytes]` — streaming TTS output
  - `async def speak_sentence(sentence: str) -> bytes` — single sentence to audio
  - **Sentence-boundary chunking**: splits text at sentence boundaries, generates audio per sentence, streams as each chunk is ready (don't wait for full response)
  - Backend configurable: OpenAI TTS API (default) or local TTS model
  - `TTSConfig(BaseModel)`: backend ("api" | "local"), voice ("alloy"), speed (1.0)

**`io/voice/controller.py`** — Voice controller (orchestrates STT + TTS + company graph):

- `VoiceController` class:
  - `async def handle_voice_input(audio_stream: AsyncIterator[bytes])`:
    1. STT transcribes the audio → text
    2. Dispatcher classifies the request
    3. **ACK-first for deep tasks**:
       - If `lane == "deep"`: immediately speak "On it, I'll work on that" via TTS
       - Run the company graph in the background (asyncio.create_task)
       - When graph completes, speak the result via TTS
    4. If `lane == "instant"`: respond immediately via TTS
    5. If `lane == "fast"`: respond after quick processing via TTS
  - Never blocks the voice thread on a deep task
  - Emits WebSocket events so the dashboard shows activity during voice requests

---

### Integration: Dashboard ↔ Voice ↔ Company Graph

**Event bus** (new: `io/event_bus.py`):

- Simple async pub/sub for internal events
- `publish(event: dict)` — broadcast an event
- `subscribe(callback: Callable)` — register a listener
- WebSocket endpoint subscribes to all events and forwards to connected clients
- Voice controller publishes events (request received, ACK sent, result ready)
- Company graph nodes publish events (stage changes, tool calls, approvals)

---

## Tests to write

### `tests/test_io/test_dashboard_api/test_app.py`
- App creates successfully with `create_app()`
- CORS headers present in responses
- Security headers present (CSP, HSTS, X-Frame-Options)

### `tests/test_io/test_dashboard_api/test_ws.py`
- WebSocket connects and receives events
- WebSocket requires authentication
- WebSocket sends heartbeat pings
- Multiple clients receive the same events (broadcast)
- Disconnected client is cleaned up

### `tests/test_io/test_dashboard_api/test_routes.py`
- `GET /api/agents` returns registered agents
- `GET /api/brain/notes` returns paginated notes
- `GET /api/brain/search?q=test` returns search results
- `GET /api/status` returns system health
- `GET /api/history` returns task history with outcomes
- `POST /api/request` accepts a request and returns task_id
- `POST /api/request` requires authentication
- `POST /api/approve` resumes a paused graph
- `POST /api/kill` triggers kill switch
- Invalid auth token returns 401

### `tests/test_io/test_dashboard_api/test_auth.py`
- Valid token passes authentication
- Invalid token is rejected
- Missing token is rejected for protected endpoints
- Token loaded from environment variable

### `tests/test_io/test_voice/test_stt.py`
- STT transcribes audio file to text (mock Whisper API)
- STT handles streaming audio input
- STT returns empty string for silence
- STT config selects correct backend

### `tests/test_io/test_voice/test_tts.py`
- TTS converts text to audio bytes (mock TTS API)
- TTS streams audio in sentence-boundary chunks
- TTS handles empty text (no crash)
- TTS config selects correct backend and voice

### `tests/test_io/test_voice/test_controller.py`
- Deep request: STT → ACK spoken immediately → graph runs in background → result spoken
- Instant request: STT → response spoken immediately (no ACK delay)
- Fast request: STT → response spoken after quick processing
- Voice controller publishes events to event bus
- Voice thread is never blocked on deep tasks (verify async)

### `tests/test_io/test_event_bus.py`
- Publish event → subscriber receives it
- Multiple subscribers receive the same event
- Unsubscribed callback does not receive events

### `tests/test_dashboard/` (frontend — npm test)
- ActivityFeed component renders events
- AgentCard component shows correct status
- SearchBar triggers API call on submit
- ApprovalCard sends approve/reject API call
- WebSocket client reconnects on disconnect

### `tests/test_integration/test_dashboard_voice.py`
- **Speak a deep request → hear ACK → watch triad work in dashboard → hear result**
  - Mock STT/TTS, verify: ACK sent before graph starts, result sent after graph completes
  - Verify WebSocket events emitted for each triad stage
- Dashboard REST API returns live data while graph is running
- Approval flow: tool call pauses → dashboard shows approval request → approve via API → graph resumes

---

## Exit gate (ALL must pass)

- [ ] FastAPI backend starts and serves on configurable host/port
- [ ] WebSocket `/ws/activity` streams real-time agent events
- [ ] WebSocket requires authentication
- [ ] `GET /api/agents` returns all registered agents with status
- [ ] `GET /api/brain/notes` returns paginated notes with tag filtering
- [ ] `GET /api/brain/search` returns semantic search results
- [ ] `GET /api/status` returns system health (daemon status, agent count, etc.)
- [ ] `GET /api/history` returns task history with outcomes
- [ ] `POST /api/request` submits a request and returns task_id
- [ ] `POST /api/approve` resumes a Guardian-paused graph
- [ ] `POST /api/kill` triggers the kill switch
- [ ] All mutating endpoints require authentication
- [ ] Security headers on all responses (CSP, HSTS, X-Frame-Options)
- [ ] Next.js dashboard renders and connects to WebSocket
- [ ] Dashboard shows live agent activity in real-time
- [ ] Brain browser works (search, view notes, backlinks)
- [ ] Approval queue shows pending interrupts with approve/reject
- [ ] STT converts speech to text (mocked in tests)
- [ ] TTS converts text to speech with sentence-boundary streaming
- [ ] **ACK-first pattern: deep request gets immediate verbal acknowledgment, graph runs in background**
- [ ] Voice thread never blocks on deep tasks
- [ ] Event bus broadcasts events to WebSocket and voice controller
- [ ] **Speak a deep request → hear ACK → watch triad work in dashboard → hear result** (integration test)
- [ ] All `pytest` green (backend), `npm test` green (frontend)

---

## Non-negotiable rules

- Layer rule: I/O layer calls Orchestration, never agents directly
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Auth on all mutating endpoints — no open write APIs
- WebSocket requires authentication before accepting messages
- Voice thread NEVER blocks on deep tasks — ACK first, background run
- Dashboard is read-heavy, write-light — optimize for streaming reads
- Do NOT build Phase 6 work (Composio integrations)

## Security checklist (enforced at VERIFY step)

- [ ] API authentication: all `POST` endpoints require valid Bearer token
- [ ] WebSocket authentication: token verified before connection accepted
- [ ] CORS: restricted origins, no wildcard `*` in production config
- [ ] Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options on all responses
- [ ] No SQL/command injection in search queries (parameterized)
- [ ] Request body validation: all `POST` bodies validated via Pydantic models
- [ ] Rate limiting on `POST /api/request` (prevent abuse)
- [ ] WebSocket: no arbitrary message execution (validate event types)
- [ ] API token stored in environment variable, never in code
- [ ] No PII in WebSocket broadcast events (filter sensitive data)
- [ ] TTS/STT: audio data not persisted unless explicitly configured
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization
- [ ] No eval/exec

## Architecture diagram

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                          I/O & EDGE LAYER                             │
  │                                                                        │
  │  ┌────────────────────┐         ┌────────────────────────────────┐    │
  │  │    VOICE I/O        │         │      DASHBOARD                 │    │
  │  │                    │         │                                │    │
  │  │  ┌──────┐  ┌─────┐│         │  ┌──────────────────────────┐  │    │
  │  │  │ STT  │  │ TTS ││         │  │   Next.js Frontend       │  │    │
  │  │  │      │  │     ││         │  │                          │  │    │
  │  │  │ mic→ │  │ →spk ││         │  │  Activity │ Brain  │ Hist│  │    │
  │  │  │ text │  │audio││         │  │  Feed    │Browser │ory  │  │    │
  │  │  └──┬───┘  └──▲──┘│         │  │          │        │     │  │    │
  │  │     │         │    │         │  │  Approvals queue        │  │    │
  │  │     ▼         │    │         │  └──────────┬─────────────┘  │    │
  │  │  ┌────────────┤    │         │             │ WebSocket       │    │
  │  │  │ Controller │    │         │             ▼                 │    │
  │  │  │            │    │         │  ┌────────────────────────┐   │    │
  │  │  │ ACK-first  │    │         │  │  FastAPI Backend       │   │    │
  │  │  │ for deep   │    │         │  │                        │   │    │
  │  │  └─────┬──────┘    │         │  │  /ws/activity (stream) │   │    │
  │  │        │           │         │  │  /api/agents           │   │    │
  │  └────────┼───────────┘         │  │  /api/brain/*          │   │    │
  │           │                     │  │  /api/status           │   │    │
  │           │    ┌──────────────┐ │  │  /api/request (submit) │   │    │
  │           └───►│  Event Bus   │◄┘  │  /api/approve          │   │    │
  │                │  (pub/sub)   │    │  /api/kill             │   │    │
  │                └──────┬───────┘    └────────────────────────┘   │    │
  │                       │                                         │    │
  └───────────────────────┼─────────────────────────────────────────┘    │
                          │                                              │
                          ▼                                              │
                ┌──────────────────────┐                                 │
                │   COMPANY GRAPH       │                                 │
                │   (orchestration)     │                                 │
                │                      │                                 │
                │   Events emitted at: │                                 │
                │   - lane assignment   │                                 │
                │   - department entry  │                                 │
                │   - triad stages      │                                 │
                │   - tool calls        │                                 │
                │   - approval requests │                                 │
                │   - task completion   │                                 │
                └──────────────────────┘                                 │
```

## Key design decisions

1. **Event bus, not direct coupling** — the dashboard doesn't poll the company graph. An async pub/sub event bus decouples the graph from the I/O layer. The graph publishes events; the WebSocket and voice controller subscribe. This follows the layer rule (I/O doesn't reach into agents).

2. **FastAPI + Next.js, not a single framework** — the backend is Python (same process as the company graph), the frontend is a separate Next.js app. This keeps the backend thin (API + WebSocket) and the frontend independently deployable.

3. **ACK-first is architectural** — the voice controller has a hard rule: if the dispatcher classifies a request as "deep," speak an acknowledgment BEFORE starting the graph. The graph runs as a background task. This is not a UX choice — it's a concurrency requirement.

4. **Auth on mutating endpoints only (by default)** — read endpoints are open by default for dashboard convenience. Mutating endpoints (request, approve, kill) always require auth. This can be tightened to auth-on-everything via config.

5. **Sentence-boundary TTS** — the TTS engine splits text at sentence boundaries and streams audio per sentence. This means the user hears the first sentence while later sentences are still being generated. Smooth, low-latency voice output.

6. **WebSocket authentication at connection time** — the token is verified when the WebSocket connection is established, not per-message. This prevents unauthenticated clients from even connecting to the event stream.

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
