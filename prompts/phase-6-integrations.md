# Phase 6 — Integrations (Composio + MCP)

> **Prerequisite:** Phase 5 exit gate must pass.
> **Parallel tracks.** Track A = Composio bridge. Track B = Wire tools into departments.

## How to run this phase

**Recommended — Parallel:**
```
claude agents
```
1. `@spine-builder Build Phase 6 Track A: Composio bridge — OAuth flow, register tools in /integrations/composio.py`
2. `@edge-builder Build Phase 6 Track B: Wire Composio tools into departments — Gmail/Notion for Growth, GitHub for Engineering`
3. `@gate-checker Verify Phase 6 exit gate`

---

## Track A — Composio Bridge

### `/integrations/composio.py`
- OAuth flow management for Composio apps
- Register Composio tools into the tool registry:
  - Gmail (read, send, search)
  - Notion (read, write pages)
  - Slack (send messages, read channels)
  - GitHub (create issues, PRs, read repos)
  - Calendar (read, create events)
- Each Composio tool wraps as a `Tool` subclass with correct `Permission`:
  - Reading emails → `Permission.READ`
  - Sending emails → `Permission.WRITE`
  - Deleting anything → `Permission.DESTRUCTIVE`
- OAuth tokens stored securely (not in brain, not in git)

### `/integrations/mcp.py`
- MCP (Model Context Protocol) server integration
- Register MCP tools alongside Composio tools
- Same permission model applies

---

## Track B — Wire into Departments

Give departments their new tools:

| Department | New tools |
|-----------|-----------|
| Engineering | GitHub (issues, PRs, code review) |
| Intelligence | Web (already has), RSS feeds via Composio |
| Growth (Phase 7) | Gmail, Notion, Slack, Calendar |
| Sales (Phase 7) | Gmail, Slack, CRM |

For now, wire Engineering + Intelligence. Growth and Sales get theirs in Phase 7 when those departments are built.

---

## Merge point
A department agent completes a real task through Composio.

---

## Exit gate (ALL must pass)
- [ ] Composio OAuth flow works for at least one app (Gmail)
- [ ] Composio tools register in the tool registry
- [ ] Each Composio tool declares correct Permission level
- [ ] Guardian enforces permissions on Composio tools (destructive actions need approval)
- [ ] **An agent reads Gmail and writes a Notion page via Composio, gated by permissions**
- [ ] Engineering department can create a GitHub issue via Composio
- [ ] MCP integration loads external tools
- [ ] All `pytest` green


## Verification
After building, run the full **Verification Protocol** from `prompts/VERIFICATION_PROTOCOL.md`:
1. `@test-runner` — all tests green
2. `@architect` + `/code-review high` — no layer violations, no bugs
3. `@security-auditor` + `/security-review` — no injection, no secrets, no SSRF
4. `@gate-checker` — all exit criteria pass with evidence
