# Phase 3 — Autonomous Engine (Daemon + Intelligence)

> **Prerequisite:** Phase 2 exit gate must pass.
> **Parallel tracks.** Track A = Daemon. Track B = Intelligence department.

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
1. `@spine-builder Build Phase 3 Track A: Daemon with heartbeat, checkpoint persistence, resume-after-restart in /infra/daemon.py`
2. `@edge-builder Build Phase 3 Track B: Intelligence department — Scout/Analyst/Skeptic triad in /agents/departments/intelligence/`
3. `@gate-checker Verify Phase 3 exit gate`

---

## Track A — Daemon (Infra)

### `/infra/daemon.py`
- Heartbeat loop: tick every 15–20 minutes (configurable)
- Each tick can trigger registered jobs (department sub-graphs)
- Checkpoint persistence: save state after every tick via LangGraph checkpointer
- **Resume-after-restart:** on startup, load last checkpoint and continue
- Graceful shutdown: handle SIGTERM/SIGINT, save state, exit cleanly
- Token budget + wall-clock budget per tick (cost/latency ceiling)

### `/infra/model_router.py`
- Route model calls by task type:
  - `code` → Claude
  - `long_docs` → Gemini
  - `triage` → local NIM/Ollama
- Interface: `route(task_type: str) -> ModelConfig`
- Start with a simple config dict, swap for real routing later

---

## Track B — Intelligence Department

### `/agents/departments/intelligence/`

**`scout.py`** — Proposer:
- Scans sources: HN, X/Twitter, GitHub trending, RSS feeds
- Read-before-act: checks brain for what's already been reported
- Produces draft: list of interesting items with summaries

**`analyst.py`** — Worker:
- Takes Scout's draft, does deeper analysis
- Cross-references with brain knowledge
- Produces a briefing note (structured report)

**`skeptic.py`** — Critic:
- Reviews the briefing for accuracy, relevance, novelty
- Rejects items that are already known or low-signal
- Bounded: `max_revisions = 3`

**`graph.py`** — Department sub-graph:
- Same triad pattern as Engineering
- Register in agent registry

### Output
The Intelligence department writes briefing notes to the brain (via `brain/obsidian.py`).

---

## Merge point
The daemon tick triggers the Intelligence sub-graph. A daily briefing note appears in the brain.

---

## Exit gate (ALL must pass)
- [ ] Daemon starts, ticks on schedule
- [ ] Daemon saves checkpoint after each tick
- [ ] **Kill the process mid-tick → restart → it resumes and completes** (critical test)
- [ ] Model router returns correct model config per task type
- [ ] Intelligence triad runs: Scout → Analyst → Skeptic
- [ ] Skeptic rejects low-quality items, approves good ones
- [ ] A daily briefing note appears in the brain after a tick
- [ ] `max_revisions` cap is respected in Intelligence department
- [ ] All `pytest` green
