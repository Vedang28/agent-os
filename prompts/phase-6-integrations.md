# Phase 6 — Integrations: Composio + MCP (Complete Build Prompt)

> Paste this into a new Claude Code session to build Phase 6 of agent-os.

## Context

Phase 5 is complete. The dashboard (FastAPI + WebSocket backend, Next.js frontend) streams live agent activity, supports brain browsing, task history, and approval queue. Voice I/O (STT + TTS) works with ACK-first pattern for deep tasks. The event bus decouples I/O from the company graph. All mutating endpoints require authentication. Security headers are in place.

Phase 6 adds **external integrations** — Composio for OAuth-based app connections (Gmail, Notion, Slack, GitHub, Calendar) and MCP (Model Context Protocol) for tool discovery. This is where agent-os reaches beyond its own sandbox and interacts with the real world.

## What exists now

- `core/state.py` — `AgentState` TypedDict with 12 fields
- `core/graph.py` — full company StateGraph with lane routing, department dispatch, outcome recording, event publishing
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
- `tools/registry.py` — tool registry
- `brain/` — schema, obsidian, qdrant, librarian, reflector, outcome, playbook
- `infra/daemon.py` — daemon heartbeat, job registry, checkpoint persistence
- `infra/model_router.py` — model routing by task type
- `infra/telemetry.py` — structured logging
- `io/dashboard_api/` — FastAPI + WebSocket backend with auth
- `io/voice/` — STT + TTS + VoiceController with ACK-first
- `io/event_bus.py` — async pub/sub event bus
- `dashboard/` — Next.js frontend

## Workflow to follow

STEP 1: /start-phase (load context, verify Phase 5 gate still passes)
STEP 2: PLAN — enter plan mode, design both tracks, get approval
STEP 3: BUILD Track A (Composio bridge + MCP) + Track B (Wire tools into departments) — sequential or parallel
STEP 4: INSTALL — add new deps (composio-core, composio-langchain or composio SDK), verify imports
STEP 5: TEST — write all tests, run pytest, fix until green
STEP 6: VERIFY (5-step verification protocol):
6a. @test-runner → all tests green
6b. @architect + /code-review high → no layer violations
6c. @security-auditor + /security-review → no injection, no secrets, no SSRF, OAuth scopes minimal
6d. @gate-checker → all exit criteria pass with evidence
6e. Fix any failures → re-run from 6a
STEP 7: /log → commit → push

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
Dispatch:
1. `@spine-builder Build Phase 6 Track A: Composio bridge with OAuth flow + MCP integration in /integrations/`
2. `@edge-builder Build Phase 6 Track B: Wire Composio tools into Engineering and Intelligence departments, update tool registry`

Merge test:
3. `@gate-checker Verify Phase 6 exit gate`

---

## What to build

### Track A — Composio Bridge (`/integrations/`)

**`integrations/__init__.py`** — package init

**`integrations/composio.py`** — Composio integration:

- `ComposioConfig(BaseModel)`:
  - `api_key: str` — loaded from env var `COMPOSIO_API_KEY`
  - `connected_apps: list[str]` — which apps are connected (e.g. ["gmail", "notion", "github"])
  - `base_url: str` — Composio API base (default: official endpoint)

- `ComposioBridge` class:
  - `async def connect_app(app_name: str) -> OAuthResult` — initiates OAuth flow for an app
    - Returns `OAuthResult(BaseModel)`: success, auth_url (for user redirect), app_name, scopes
    - Stores tokens securely (NOT in brain, NOT in git — encrypted file or env-based)
  - `async def disconnect_app(app_name: str) -> bool` — revokes OAuth connection
  - `async def list_connected_apps() -> list[str]` — returns connected app names
  - `async def get_tools(app_name: str) -> list[Tool]` — returns Tool subclasses for an app
    - Each Composio tool wraps as a proper `Tool` subclass with correct `Permission`:

- **Composio Tool wrappers** — each external action becomes a `Tool` subclass:

  **`integrations/tools/gmail.py`** — Gmail tools:
  - `GmailReadTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, query: str, max_results: int = 10) -> list[dict]`
    - Returns: `[{"id": str, "subject": str, "from": str, "snippet": str, "date": str}]`
  - `GmailSendTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, to: str, subject: str, body: str) -> dict`
    - Returns: `{"id": str, "status": "sent"}`
  - `GmailDeleteTool(Tool)` — `permission = Permission.DESTRUCTIVE`
    - `async def _execute(self, message_id: str) -> dict`

  **`integrations/tools/notion.py`** — Notion tools:
  - `NotionReadTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, page_id: str) -> dict`
    - Returns page content as structured dict
  - `NotionWriteTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, title: str, content: str, parent_id: str | None = None) -> dict`
    - Returns: `{"id": str, "url": str}`
  - `NotionSearchTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, query: str) -> list[dict]`

  **`integrations/tools/slack.py`** — Slack tools:
  - `SlackReadTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, channel: str, limit: int = 20) -> list[dict]`
  - `SlackSendTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, channel: str, message: str) -> dict`

  **`integrations/tools/github.py`** — GitHub tools:
  - `GitHubReadRepoTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, owner: str, repo: str) -> dict`
  - `GitHubCreateIssueTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, owner: str, repo: str, title: str, body: str) -> dict`
  - `GitHubCreatePRTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, owner: str, repo: str, title: str, body: str, head: str, base: str) -> dict`

  **`integrations/tools/calendar.py`** — Calendar tools:
  - `CalendarReadTool(Tool)` — `permission = Permission.READ`
    - `async def _execute(self, start: str, end: str) -> list[dict]`
  - `CalendarCreateTool(Tool)` — `permission = Permission.WRITE`
    - `async def _execute(self, title: str, start: str, end: str, attendees: list[str] | None = None) -> dict`

- **Token storage** (`integrations/token_store.py`):
  - `TokenStore` class:
    - `store_token(app_name: str, token_data: dict)` — encrypt and save
    - `get_token(app_name: str) -> dict | None` — decrypt and return
    - `delete_token(app_name: str)` — securely delete
  - Storage: encrypted file in a configurable directory (NOT the brain vault, NOT git-tracked)
  - Encryption: use `cryptography.fernet` with key from env var `AGENT_OS_TOKEN_KEY`
  - Tokens NEVER appear in logs, brain notes, or git history

**`integrations/mcp.py`** — MCP integration:

- `MCPConfig(BaseModel)`:
  - `servers: list[MCPServerConfig]` — list of MCP servers to connect to
  - `MCPServerConfig(BaseModel)`: name, url, auth_token (optional)

- `MCPBridge` class:
  - `async def connect(server: MCPServerConfig)` — connect to an MCP server
  - `async def discover_tools(server_name: str) -> list[Tool]` — discover available tools from the server
    - Each MCP tool wraps as a `Tool` subclass with inferred `Permission`
  - `async def call_tool(server_name: str, tool_name: str, args: dict) -> dict` — invoke a tool
  - `async def list_servers() -> list[str]` — connected servers
  - MCP tools auto-register in the tool registry alongside Composio tools

---

### Track B — Wire into Departments

**Update department tool access**:

- **Engineering department** gets:
  - `GitHubReadRepoTool` — read repository info for context
  - `GitHubCreateIssueTool` — create issues for tracked work
  - `GitHubCreatePRTool` — create pull requests
  - Update `agents/departments/engineering/scaffolder.py` to have access to GitHub tools via tool registry

- **Intelligence department** gets:
  - `SlackReadTool` — read relevant channels for signal
  - (Already has WebTool for web scraping)
  - Update `agents/departments/intelligence/scout.py` to use Slack as an additional source

**Update tool registry** (`tools/registry.py`):

- Composio tools register on bridge initialization
- MCP tools register on server connection
- Registry supports namespaced names: `composio.gmail.read`, `composio.github.create_issue`, `mcp.{server}.{tool}`
- `list_tools(namespace: str | None = None)` — filter tools by namespace

**Update dashboard**:

- **`io/dashboard_api/routes.py`** — add integration endpoints:
  - `GET /api/integrations` — list connected apps and MCP servers
  - `POST /api/integrations/connect` — initiate OAuth flow for an app
  - `POST /api/integrations/disconnect` — revoke an app connection
  - `GET /api/integrations/tools` — list all integration tools with permissions
- **Dashboard frontend**: integrations tab (was placeholder, now functional)
  - Connected apps list with connect/disconnect buttons
  - Tool inventory per integration
  - OAuth redirect handling

---

## Tests to write

### `tests/test_integrations/test_composio.py`
- `ComposioBridge` initializes with config from env
- `connect_app("gmail")` initiates OAuth flow (mock Composio API)
- `connect_app` returns OAuth URL for user redirect
- `disconnect_app` revokes connection (mock API)
- `list_connected_apps()` returns connected app names
- `get_tools("gmail")` returns Gmail tool subclasses
- Each tool declares correct `Permission` level
- Config rejects missing API key

### `tests/test_integrations/test_token_store.py`
- `store_token` encrypts and saves token data
- `get_token` decrypts and returns token data
- `get_token` for nonexistent app returns None
- `delete_token` removes token securely
- Tokens are encrypted at rest (verify ciphertext != plaintext)
- Token key loaded from environment variable
- Missing token key raises clear error

### `tests/test_integrations/test_gmail.py`
- `GmailReadTool` reads emails (mock Composio API), returns structured list
- `GmailSendTool` sends email (mock), returns status
- `GmailDeleteTool` declares `Permission.DESTRUCTIVE`
- `GmailDeleteTool` is gated by Guardian (requires approval)

### `tests/test_integrations/test_notion.py`
- `NotionReadTool` reads a page (mock API)
- `NotionWriteTool` creates a page (mock API)
- `NotionSearchTool` searches pages (mock API)
- Write tool declares `Permission.WRITE`

### `tests/test_integrations/test_slack.py`
- `SlackReadTool` reads channel messages (mock API)
- `SlackSendTool` sends a message (mock API)
- Send tool declares `Permission.WRITE`

### `tests/test_integrations/test_github.py`
- `GitHubReadRepoTool` reads repo info (mock API)
- `GitHubCreateIssueTool` creates an issue (mock API)
- `GitHubCreatePRTool` creates a PR (mock API)
- Issue/PR tools declare `Permission.WRITE`

### `tests/test_integrations/test_calendar.py`
- `CalendarReadTool` reads events (mock API)
- `CalendarCreateTool` creates an event (mock API)
- Create tool declares `Permission.WRITE`

### `tests/test_integrations/test_mcp.py`
- `MCPBridge` connects to a mock MCP server
- `discover_tools` returns tool list from server
- Discovered tools register in the tool registry
- `call_tool` invokes a tool on the server (mock)
- MCP tools have correct permission inference

### `tests/test_integrations/test_registry_integration.py`
- Composio tools register with namespaced names
- MCP tools register with namespaced names
- `list_tools("composio")` filters to Composio tools only
- `list_tools("mcp")` filters to MCP tools only
- `list_tools()` returns all tools (built-in + Composio + MCP)

### `tests/test_integration/test_composio_flow.py`
- **End-to-end: an agent reads Gmail and writes a Notion page via Composio, gated by permissions**
  - Mock Composio APIs
  - Verify: GmailReadTool (READ) executes without approval
  - Verify: NotionWriteTool (WRITE) executes with logging
  - Verify: GmailDeleteTool (DESTRUCTIVE) pauses for approval via Guardian
- Engineering department creates a GitHub issue via Composio tool
- Intelligence department reads Slack channel via Composio tool
- Dashboard `/api/integrations` returns connected apps
- Integration tools appear in dashboard tool inventory

---

## Exit gate (ALL must pass)

- [ ] `ComposioBridge` connects and manages OAuth flows (mocked in tests)
- [ ] Composio tools register in the tool registry with namespaced names
- [ ] Each Composio tool declares the correct `Permission` level
- [ ] `GmailReadTool` reads emails (Permission.READ)
- [ ] `GmailSendTool` sends emails (Permission.WRITE)
- [ ] `GmailDeleteTool` deletes emails (Permission.DESTRUCTIVE, requires Guardian approval)
- [ ] `NotionWriteTool` creates a page (Permission.WRITE)
- [ ] `GitHubCreateIssueTool` creates an issue (Permission.WRITE)
- [ ] Guardian enforces permissions on all Composio tools (DESTRUCTIVE actions need approval)
- [ ] **An agent reads Gmail and writes a Notion page via Composio, gated by permissions** (integration test)
- [ ] **Engineering department creates a GitHub issue via Composio**
- [ ] Token storage encrypts tokens at rest, never logs or exposes them
- [ ] MCP bridge connects to a server and discovers tools
- [ ] MCP tools register in tool registry alongside Composio tools
- [ ] Dashboard integrations tab shows connected apps and tools
- [ ] Tool registry supports namespace filtering
- [ ] All `pytest` green

---

## Non-negotiable rules

- Layer rule: agents call Tools, never raw Composio/MCP APIs directly
- No if-elif dispatch — use the registry
- Bounded critic loop: `max_revisions = 3`, then escalate. NEVER unbounded.
- Typed state only — nothing outside `AgentState`
- One class = one agent (single responsibility)
- Every Composio action = one Tool subclass with explicit Permission
- OAuth tokens NEVER in code, git, brain, or logs
- Tool registry is the single source of truth for all tools (built-in, Composio, MCP)
- Guardian gates ALL tools equally — Composio tools get the same permission enforcement as built-in tools
- Minimum OAuth scopes — request only what the tool needs
- Do NOT build Phase 7 work (mass-producing departments)

## Security checklist (enforced at VERIFY step)

- [ ] OAuth tokens encrypted at rest via `cryptography.fernet`
- [ ] Token encryption key loaded from env var, never hardcoded
- [ ] OAuth tokens never logged (check telemetry output)
- [ ] OAuth tokens never stored in brain notes
- [ ] OAuth tokens never committed to git (verify `.gitignore`)
- [ ] Composio API key loaded from env var, never hardcoded
- [ ] OAuth scopes: each app requests minimum necessary scopes
- [ ] DESTRUCTIVE Composio actions (delete email, delete page) require Guardian approval
- [ ] MCP server connections authenticated (token in config, not code)
- [ ] MCP tool calls validated before execution (no arbitrary code execution)
- [ ] No injection via Composio tool parameters (validate all inputs)
- [ ] No SSRF via MCP server URLs (validate against blocklist)
- [ ] Integration endpoints require auth (POST /api/integrations/*)
- [ ] No secrets in code or git history
- [ ] No unsafe deserialization

## Architecture diagram

```
  ┌────────────────────────────────────────────────────────────────────┐
  │                      INTEGRATIONS LAYER                           │
  │                                                                    │
  │  ┌──────────────────────────────────────┐  ┌──────────────────┐  │
  │  │         COMPOSIO BRIDGE              │  │   MCP BRIDGE     │  │
  │  │                                      │  │                  │  │
  │  │  OAuth Flow Manager                  │  │  Server Connector│  │
  │  │  Token Store (encrypted)             │  │  Tool Discovery  │  │
  │  │                                      │  │  Tool Invocation │  │
  │  │  ┌─────────┬─────────┬──────────┐   │  │                  │  │
  │  │  │  Gmail  │ Notion  │  Slack   │   │  │  ┌────────────┐  │  │
  │  │  │ Read(R) │ Read(R) │ Read(R)  │   │  │  │ MCP Server │  │  │
  │  │  │ Send(W) │Write(W) │ Send(W)  │   │  │  │ tools auto │  │  │
  │  │  │ Del(D)  │Search(R)│          │   │  │  │ register   │  │  │
  │  │  ├─────────┼─────────┼──────────┤   │  │  └────────────┘  │  │
  │  │  │ GitHub  │Calendar │          │   │  │                  │  │
  │  │  │ Read(R) │ Read(R) │          │   │  └──────────────────┘  │
  │  │  │Issue(W) │Create(W)│          │   │                        │
  │  │  │  PR(W)  │         │          │   │                        │
  │  │  └─────────┴─────────┴──────────┘   │                        │
  │  └────────────────┬─────────────────────┘                        │
  │                   │                                               │
  │                   ▼                                               │
  │  ┌─────────────────────────────────────────────────────────────┐ │
  │  │                    TOOL REGISTRY                             │ │
  │  │                                                             │ │
  │  │  Built-in:    bash, file, web                               │ │
  │  │  Composio:    composio.gmail.read, composio.notion.write... │ │
  │  │  MCP:         mcp.{server}.{tool}                           │ │
  │  │                                                             │ │
  │  │  All gated by Guardian → Permission check → execute         │ │
  │  └─────────────────────────────────────────────────────────────┘ │
  │                   │                                               │
  │                   ▼                                               │
  │  ┌────────────────────────────────────┐                          │
  │  │  DEPARTMENTS (tool consumers)      │                          │
  │  │                                    │                          │
  │  │  Engineering → GitHub tools        │                          │
  │  │  Intelligence → Slack + Web tools  │                          │
  │  │  (Phase 7: Growth → Gmail/Notion)  │                          │
  │  │  (Phase 7: Sales → Gmail/Slack)    │                          │
  │  └────────────────────────────────────┘                          │
  └────────────────────────────────────────────────────────────────────┘

  Token security:
    ┌──────────────┐    ┌──────────────┐
    │ Env var:     │    │ Encrypted    │
    │ COMPOSIO_KEY │    │ token store  │
    │ TOKEN_KEY    │    │ (Fernet)     │
    │              │    │ NOT in brain │
    │ Never in git │    │ NOT in git   │
    └──────────────┘    └──────────────┘
```

## Key design decisions

1. **One Tool subclass per Composio action** — `GmailReadTool`, `GmailSendTool`, etc. are separate classes, not one `GmailTool` with mode switches. This respects the single-responsibility rule and makes Permission assignment explicit per action.

2. **Composio tools are regular Tools** — they extend the same `Tool` base class as BashTool and FileTool. The Guardian doesn't know or care whether a tool is built-in, Composio, or MCP. Same permission enforcement for all.

3. **Token store is separate from the brain** — OAuth tokens are secrets. They live in an encrypted file store, never in Obsidian notes, never in Qdrant vectors, never in git. The `cryptography.fernet` encryption is keyed by an env var.

4. **Namespaced tool registry** — tools are registered as `composio.gmail.read`, `mcp.server1.tool_name`, etc. This prevents name collisions and allows filtering by namespace. Built-in tools have no namespace prefix.

5. **MCP is additive** — MCP tools are discovered at runtime from connected servers and auto-registered. This means agent-os can gain new capabilities without code changes — just connect a new MCP server.

6. **Minimum scopes** — each Composio app connection requests only the scopes the tools need. Gmail read doesn't request send scope. This is enforced in the tool wrapper definitions.

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
