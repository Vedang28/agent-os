# AGENT OS — PROJECT MEMORY

> This file loads automatically every session. Keep it lean — it's a behavioral contract, not documentation.

## Identity
Autonomous multi-agent company. Society-of-mind: CEO orchestrator → divisions → departments → proposer/worker/critic triads. Runs continuously via a daemon, learns via a reflector + Obsidian/Qdrant brain.

## Locked stack (do not change without approval)
- Orchestration: **LangGraph** — sub-graphs = departments, conditional edges = critic loop, checkpointer = resume-after-restart
- Python 3.12 · Qdrant (vectors) · Obsidian markdown (knowledge graph) · Composio (OAuth) · FastAPI+WebSocket / Next.js (dashboard)
- Models routed per task: Claude (code) · Gemini (long docs) · local NIM/Ollama (triage)
- Voice (STT/TTS) lives at the I/O edge, outside the graph

## Read before working
- `docs/EXECUTION_PLAN.md` — the build plan. Read the **active phase section** before writing any code.
- `docs/AGENT_ROSTER.md` — the full 89-agent catalog. Read on demand, not every session.
- Current phase: see @docs/PHASE_STATUS.md

## Non-negotiable rules
1. **Layer rule** — a layer may only call the layer directly below it. Agents call Tools, never raw `subprocess`.
2. **One class = one agent** (single responsibility). No god objects.
3. **No if-elif dispatch.** Use the registry.
4. **Bounded critic loop** — `max_revisions = 3`, then escalate. NEVER an unbounded loop.
5. **Permission-gated tools** — every tool declares a `Permission`. Destructive actions require Guardian approval.
6. **Lane discipline** — cheap requests (greetings, time) skip the company entirely.
7. **Read-before-act** — every proposer queries the brain first.
8. **Typed state only** — nodes pass nothing outside `AgentState`.
9. **Every department ships one eval test** that runs in CI.

## Conventions
- One folder per layer: `/core /agents /tools /brain /integrations /io /infra /dashboard`
- New department = ~4 class files + a sub-graph + ONE registry line. Copy the Engineering pattern.
- Tests mirror the layer folders.
- Phase gates are mandatory: do NOT start the next phase until the current phase's exit gate passes.

## How to work
- Work ONLY the active phase in `PHASE_STATUS.md`.
- Two tracks run in parallel: Track A (spine: orchestration/agents/brain/daemon), Track B (edges: tools/io/dashboard/integrations).
- **Start every session** with `/start-phase` (loads recent context).
- **End every session** with `/log` (writes a session summary).
- Verify completion with `/exit-gate` — never advance a phase whose gate hasn't actually passed.

## Session memory & continuity (so sessions don't start cold)
- `.claude/memory/SESSION_LOG.md` — append-only log of what each session did. Read recent via `node .claude/memory/memory.js recent 5`.
- `.claude/memory/DECISIONS.md` — architectural decisions (ADR). Check here before changing architecture; never re-litigate a recorded decision.
- `.claude/memory/memory.js` — CLI: `log` · `decide` · `recent [n]` · `search <kw>`.
- This is the dev-workflow memory, separate from the runtime brain (Obsidian/Qdrant) built in Phase 1.

## When stuck or erroring
Follow `docs/WHEN_STUCK.md`. Summary: read the real error → one targeted fix → consult docs/decisions → search memory → log a blocker and STOP. Bounded retries (max 2). Never fake success, never swallow errors, never widen scope to escape a blocker.

## Learning loop
Follow `docs/LEARNING_LOOP.md`. Use `/reflect` to turn repeated outcomes into recorded decisions and playbook improvements.

## Verification protocol (mandatory per phase)
After every phase build, run the 5-step verification from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` → all tests green
2. `@architect` + `/code-review high` → no layer violations, no bugs
3. `@security-auditor` + `/security-review` → no injection, no secrets, no SSRF, no path traversal
4. `@gate-checker` → all exit criteria pass with evidence
5. Fix any failures → re-run from step 1
Never advance a phase until all 5 steps pass.

## Subagents (.claude/agents/)
- **`@spine-builder`** — Track A builder (core, agents, brain, infra). Uses worktree isolation.
- **`@edge-builder`** — Track B builder (tools, io, dashboard, integrations). Uses worktree isolation.
- **`@test-runner`** — Runs pytest, reports failures with root causes. Read-only.
- **`@gate-checker`** — Verifies phase exit gates with real checks. Read-only.
- **`@architect`** — Reviews designs against architectural constraints. Read-only.
- **`@security-auditor`** — OWASP top 10, injection, secrets, path traversal, SSRF. Read-only.

## Phase prompts (prompts/)
One prompt per phase (0–8). Each includes:
- What to build (Track A + Track B)
- How to run it (single session, workflow, or parallel agent view)
- Exit gate checklist
- Rules reminder

To run a phase: copy the prompt from `prompts/phase-N-*.md` into a new session.

## Parallel work patterns
- **Agent view** (`claude agents`): dispatch `@spine-builder` and `@edge-builder` as parallel sessions with worktree isolation
- **Workflows**: say "run a workflow to..." for fan-out orchestration
- **Worktrees**: each builder agent gets its own worktree so Track A and Track B don't conflict

## Custom commands (.claude/commands/)
`/start-phase` · `/exit-gate` · `/log` · `/reflect` · `/new-department <name>`
