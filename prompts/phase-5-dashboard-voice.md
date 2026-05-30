# Phase 5 — Dashboard + Voice

> **Prerequisite:** Phase 4 exit gate must pass.
> **Parallel tracks.** Track A = Dashboard backend. Track B = Voice I/O.
> **This is when you get a UI.**

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
1. `@spine-builder Build Phase 5 Track A: FastAPI + WebSocket backend for dashboard in /io/dashboard_api/`
2. `@edge-builder Build Phase 5 Track B: Voice I/O — STT input, streaming TTS output in /io/voice/`
3. Then: `Build the Next.js dashboard frontend in /dashboard/`
4. `@gate-checker Verify Phase 5 exit gate`

---

## Track A — Dashboard Backend

### `/io/dashboard_api/`

**`ws.py`** — WebSocket streaming:
- FastAPI application with WebSocket endpoint
- Streams real-time agent activity:
  - Which department is active
  - Current triad stage (proposer/worker/critic)
  - Tool calls in progress
  - Approval requests pending
- REST endpoints:
  - `GET /agents` — list all registered agents and their status
  - `GET /brain/notes` — browse brain notes
  - `GET /brain/search?q=` — semantic search
  - `GET /status` — system health, daemon status
  - `GET /history` — recent task history
  - `POST /request` — submit a new request to the company

**`models.py`** — API response models (Pydantic)

### `/dashboard/` — Next.js Frontend

- Real-time agent activity stream (WebSocket)
- Agent status panel (who's doing what)
- Brain browser (notes, search, backlinks)
- Task history with triad replay
- Integrations tab (placeholder for Phase 6)
- Live tool stream (see tool calls as they happen)
- Permission approval UI (approve/reject from dashboard)

**Stack:** Next.js 14+, Tailwind CSS, shadcn/ui components, WebSocket client.

---

## Track B — Voice I/O

### `/io/voice/`

**`stt.py`** — Speech-to-text:
- Microphone input → text
- Use Whisper API or local Whisper model
- Streaming input support

**`tts.py`** — Text-to-speech:
- Text → audio output
- Streaming TTS with sentence-boundary chunking (don't wait for full response)
- **ACK-first for deep tasks:** immediately say "on it" or "working on that", then run the graph in the background, then speak the result when ready
- Never block the voice thread on a deep task

### ACK-first pattern
```
User speaks → STT → Dispatcher classifies as "deep"
  → Immediately: TTS says "On it, I'll work on that"
  → Background: Graph runs the full triad
  → When done: TTS speaks the result
```

---

## Merge point
Dashboard shows live activity while a voice request runs.

---

## Exit gate (ALL must pass)
- [ ] FastAPI backend starts and serves WebSocket connections
- [ ] WebSocket streams real-time agent activity
- [ ] REST endpoints return agent status, brain notes, search results
- [ ] Next.js dashboard renders and connects to WebSocket
- [ ] Dashboard shows live agent activity in real-time
- [ ] Brain browser works (search, view notes, backlinks)
- [ ] STT converts speech to text
- [ ] TTS converts text to speech with streaming
- [ ] ACK-first pattern: deep request gets immediate verbal acknowledgment
- [ ] **Speak a deep request → hear ACK → watch triad work in dashboard → hear result**
- [ ] All `pytest` green (backend), `npm test` green (frontend)
