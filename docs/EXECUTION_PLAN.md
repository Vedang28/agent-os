# AGENT OS — EXECUTION PLAN

> Step-by-step build plan for the autonomous multi-agent company.
> Two parallel tracks so two people can work different branches.
> **Track A = Spine** (orchestration · agents · brain · daemon).
> **Track B = Edges** (tools · I/O · dashboard · integrations).
> Each phase has a **merge point** where the two tracks converge, plus an **exit gate** (a check that must pass before the next phase).

---

## LOCKED STACK DECISIONS

| Concern | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** | sub-graphs = departments, conditional edges = critic loop, checkpointing = resume-after-restart |
| Language | **Python 3.12** | LangGraph + ML ecosystem |
| Brain (graph) | **Obsidian vault** (markdown) | human-readable, backlinks |
| Brain (vectors) | **Qdrant** | semantic retrieval |
| Integrations | **Composio** | 100+ OAuth apps as typed tools |
| Models | **Claude (code) · Gemini (long docs) · local NIM/Ollama (triage)** | routed per task by cost/latency |
| Voice I/O | kept at the **edge** (STT/TTS) | outside the graph, swappable |
| Dashboard | **FastAPI + WebSocket** backend, **Next.js** frontend | live agent stream |
| Persistence | LangGraph **checkpointer** (SQLite → Postgres later) | daemon survives restarts |

---

## LAYERED ARCHITECTURE (dependency rule: a layer may only call the layer directly below it)

1. **I/O & edge** — voice, chat, dashboard
2. **Orchestration** — LangGraph StateGraph (company + department sub-graphs)
3. **Agents** — singleton classes, proposer/worker/critic triads, registry
4. **Tools** — permission-gated (bash, file, web, vision), one registry
5. **Memory / brain** — Obsidian + Qdrant, read-before-act
6. **Integrations** — Composio + MCP
7. **Infrastructure** — daemon, model router, checkpointer, telemetry

Never let an agent reach past its layer (e.g. an agent must call a Tool, never raw `subprocess`).

---

## REPO STRUCTURE (monorepo, one folder per layer)

```
/agent-os
  /core            # orchestration: graph.py, state.py, dispatcher.py, orchestrator.py
  /agents          # agent layer
    protocol.py    # Agent Protocol (interface every agent implements)
    registry.py    # one registry, no if-elif anywhere
    /departments
      /engineering # architect.py, scaffolder.py, code_doctor.py, graph.py
      /intelligence
      ...
  /tools           # base.py (permission enum), registry.py, bash.py, file.py, web.py, vision.py
  /brain           # librarian.py, obsidian.py, qdrant.py, reflector.py, schema.py
  /integrations    # composio.py, mcp.py
  /io              # /voice (stt.py, tts.py), /dashboard_api (ws.py)
  /infra           # daemon.py, model_router.py, checkpointer.py, telemetry.py
  /dashboard       # Next.js frontend
  /tests           # one test folder mirroring the layers
```

---

## THE STATE CONTRACT (typed — every node reads/writes this)

```python
class AgentState(TypedDict):
    request: str
    lane: Literal["instant", "fast", "deep"]
    plan: list[str]
    department: str
    task: Task
    draft: str | None          # proposer output
    result: str | None         # worker output
    critique: Critique | None  # critic output
    approved: bool
    revisions: int             # BOUNDED — see principle below
    brain_context: list[Note]  # read-before-act results
    history: list[Step]
```

Typed state is the contract between nodes. No node passes anything outside this shape.

---

## ENGINEERING PRINCIPLES (enforced in review)

- **Single Responsibility** — one class, one agent, one job. If it does two things, split it.
- **Open/Closed** — add a department without editing the orchestrator. New department = new sub-graph + registry line.
- **Dependency Inversion** — agents depend on the `Agent` protocol and `Tool` interface, never concrete implementations.
- **DRY** — shared tools live in `/tools`. No agent re-implements bash, file, or web access.
- **Separation of concerns** — the 7-layer rule above.
- **Contract-first** — typed state + typed Task/Critique. Design the contract before the node.
- **Fail-safe defaults** — Guardian + permission gates. Destructive actions require approval.
- **Security Gate on all code output** — every code-producing department's sub-graph includes a SecurityGate node after the Critic. Checks injection, secrets, auth, input validation, dependency CVEs. Failures count toward `max_revisions`. See `docs/SECURITY_ARCHITECTURE.md`.
- **Idempotent + checkpointed** — every node can be re-run safely; the daemon resumes from the last checkpoint.
- **Bounded loops** — the critic revise loop has a `max_revisions` cap (e.g. 3). After the cap, escalate to Guardian/human. **Never an unbounded loop.**
- **Cost & latency ceilings** — every deep task has a token budget and a wall-clock budget. Exceed it → stop and report.
- **Lane discipline** — 90% of requests must never enter the company. Cheap path for cheap requests.
- **Observability from day 1** — telemetry wired in Phase 0, not bolted on later.

---

## THE PHASES

### Phase 0 — Foundation (both together, no split yet)
- Monorepo + layered folders, Python env, pre-commit, ruff/black, pytest harness, CI.
- `Agent` protocol + empty registry. `Tool` base with `Permission` enum.
- `AgentState` typed schema. Empty LangGraph that compiles and runs a no-op.
- `telemetry.py` skeleton (structured logging from the start).
- **Exit gate:** empty graph runs end-to-end, registry loads, `pytest` green, CI passes.

### Phase 1 — Brain + Tools (PARALLEL)
- **Track A — Brain:** `obsidian.py` (note schema, write/read), `qdrant.py` (embed + search), `librarian.py` (read-before-act query API).
- **Track B — Tools:** permission-gated `BashTool`, `FileTool`, `WebTool`; tool `registry`; each tool declares its `Permission`.
- **Merge point:** an agent stub can (a) query the brain and (b) call a permission-gated tool.
- **Exit gate:** write a note → retrieve it semantically from Qdrant; a SHELL-permission tool blocks without approval.

### Phase 2 — Spine + first department (PARALLEL)
- **Track A — Orchestration:** company `StateGraph`, `Orchestrator` node (decompose + route), `Dispatcher` (lane assignment), checkpointer wired.
- **Track B — First department:** Engineering sub-graph — `Architect` (proposer) → `Scaffolder` (worker) → `CodeDoctor` (critic), with the **conditional edge** (approve → up / revise → back to worker, bounded by `max_revisions`).
- **Merge point:** Engineering sub-graph registers and plugs into the company graph as one node.
- **Exit gate:** a deep request flows User → Dispatcher → Orchestrator → Engineering triad → approved output, and a deliberately bad draft triggers exactly one revise loop then passes.

### Phase 3 — Autonomous engine (PARALLEL)
- **Track A — Daemon:** `daemon.py` heartbeat (tick every 15–20 min), checkpoint persistence, resume-after-restart.
- **Track B — Intelligence department:** `Scout` (HN/X/GitHub/RSS) → `Analyst` → `Skeptic`, writing briefings to the brain.
- **Merge point:** the daemon tick triggers the Intelligence sub-graph.
- **Exit gate:** kill the process mid-tick → it resumes and completes; a daily briefing note appears in the brain.

### Phase 4 — Learning loop + Guardian (PARALLEL)
- **Track A — Reflector:** reviews outcomes in the brain, updates playbook notes; proposers read playbooks before drafting.
- **Track B — Guardian:** permission gates enforced, human-in-the-loop **interrupt** (LangGraph pause/resume) on destructive actions, kill switch.
- **Merge point:** a low-scoring outcome produces an improved playbook on the next run; a destructive tool call pauses for approval.
- **Exit gate:** measurable improvement on a repeated task after reflection; no destructive action executes without an approval step.

### Phase 5 — Dashboard + Voice (PARALLEL)
- **Track A — Dashboard backend:** FastAPI + WebSocket streaming agent status, live tool stream, brain browser, integrations tab.
- **Track B — Voice I/O:** STT in, streaming TTS out (sentence-boundary), ACK-first for deep tasks.
- **Merge point:** dashboard shows live activity while a voice request runs.
- **Exit gate:** speak a deep request → hear an immediate ACK → watch the triad work live in the dashboard → hear the result.

### Phase 6 — Integrations (PARALLEL)
- **Track A — Composio bridge:** OAuth flow, register Composio tools (Gmail, Notion, Slack, GitHub) into the tool registry.
- **Track B — Wire into departments:** give the relevant departments their new tools (e.g. Growth gets Gmail/Notion).
- **Merge point:** a department agent completes a real task through Composio.
- **Exit gate:** an agent reads Gmail and writes a Notion page via Composio, gated by permissions.

### Phase 7 — Mass-produce departments (PARALLEL, split the catalog)
- Copy the proven pattern across the remaining departments. Each = ~4 class files + a sub-graph + a registry line.
- **Split the work:** Person A takes Backend + DevOps + AI/ML + Developer Experience divisions. Person B takes Frontend + Growth + Sales/Ops. Perception (the eyes) is shared since Quality depends on it.
- **Developer Experience division** (24 agents): Code Review, Testing, Security, Bug Triage, Dependency Mgmt, Documentation, Performance, DevOps/CI. These are high-priority — dogfood them while building the rest.
- **Exit gate:** every department has a passing end-to-end test through its triad and critic loop.

### Phase 8 — Harden & scale
- Eval harness per department, cost dashboards, lane tuning, security audit (secrets, tool permissions, OAuth scopes), load test the daemon, swap checkpointer SQLite → Postgres.
- **Exit gate:** runs unattended for 48h with no crash, briefings generated, costs within ceiling.

---

## ROSTER BY PHASE (which agents get built when, and on which track)

| Phase | Track A (Spine) | Track B (Edges) |
|---|---|---|
| 0 | Agent protocol, registry, state | Tool base + Permission enum |
| 1 | Brain Librarian | Bash/File/Web tools |
| 2 | Orchestrator, Dispatcher | Engineering: Architect · Scaffolder · CodeDoctor |
| 3 | (Daemon — infra) | Intelligence: Scout · Analyst · Skeptic |
| 4 | Reflector | Guardian |
| 5 | (Dashboard backend) | (Voice I/O) + Vision-reader stub |
| 6 | Composio bridge | (wire tools to departments) |
| 7 | Backend, DevOps, AI/ML, Dev Experience divisions | Frontend, Growth, Sales/Ops divisions |
| — | Shared: Perception (Screen-watcher · Vision-reader · Frame-critic), Quality (UI testing) |

The full 89-agent catalog in `AGENT_ROSTER.md` still stands — this table is the **build order**, not a replacement.

---

## CODE PIPELINE (every code-producing department)

Every department that produces code runs a 9-stage pipeline. See `docs/CODE_PIPELINE.md` for full details.

```
PLAN → SCAFFOLD → BUILD → TEST → DEBUG → REVIEW → AUDIT → PROD-READY → PUSH
```

Non-code departments (Intelligence, Marketing, Sales) use: `PLAN → DRAFT → REVIEW → FACT-CHECK → DELIVER`.

Failures at TEST, REVIEW, or AUDIT send code back to DEBUG. Max 3 loops total, then escalate. No unbounded loops. No stage skipping.

---

## WHAT WORKS WELL (battle-tested patterns to use)

- **Sub-graph per department** — isolates each team; a department becomes one node in the company graph.
- **Conditional edge for the critic** — `approve → end / revise → worker`, bounded by `max_revisions`.
- **Read-before-act** — every proposer queries the brain first; never start cold.
- **Permission-gated tools** — high-risk tools (bash, destructive) treated differently from read-only at the architecture level.
- **ACK-first for deep tasks** — speak "on it" immediately, run the graph in the background; never block the voice thread.
- **Checkpointer everywhere** — free resume-after-crash and human-in-the-loop pauses.
- **One eval per department** — a fixed test case the triad must pass; run it in CI so a department can't regress.

## ANTI-PATTERNS (do not do)

- Unbounded critic loops (always cap revisions).
- Routing cheap requests through the company (lane discipline).
- Duplicating tools across agents (DRY — one tool registry).
- Skipping the brain (agents go amnesiac).
- One god-node that does everything (defeats the whole structure).
- Building all 89 at once (prove one department, then replicate).
