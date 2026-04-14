# AR Collection Agent — CLAUDE.md
**Version:** 0.1.0 | **Updated:** 2026-04-14

Advanced AR Collection Agent — monitors accounts receivable ageing, identifies overdue invoices, prioritises collection actions, and surfaces a daily digest to Slack.

---

## Commands

```bash
# ── Development ───────────────────────────────────────────────
source .venv/bin/activate
python bot.py                        # Slack bot (Socket Mode, foreground)
python scheduler.py                  # daily cron job (foreground)

# ── MCP server ────────────────────────────────────────────────
python -m mcp.mcp_server             # starts on :8084

# ── Tests ─────────────────────────────────────────────────────
pytest tests/ -v
```

---

## Stack

| Layer | Tech |
|-------|------|
| Language | Python 3.11+ |
| LLM dispatch | Claude Haiku 4.5 — `tool_choice: {"type":"any"}` |
| LLM synthesis | Claude Opus 4.6 — `thinking: {"type":"adaptive"}`, streaming |
| Scheduler | APScheduler — `BlockingScheduler`, cron trigger |
| Database | PostgreSQL via SQLAlchemy |
| Notifications | Slack SDK (WebClient) |
| MCP | JSON-RPC 2.0, POST /mcp — port 8084 |

---

## Key Files

```
ar-collection-agent/
├── CLAUDE.md
├── .env.example
├── requirements.txt
├── bot.py                  ← Slack Socket Mode entry point (not yet implemented)
├── scheduler.py            ← APScheduler daily job (not yet implemented)
├── src/
│   ├── agents/             ← collection agent logic
│   ├── db/                 ← DatabaseConfig, get_session()
│   └── services/           ← AR data fetching, prioritisation
├── mcp/
│   └── mcp_server.py       ← NOT YET IMPLEMENTED
├── tests/
└── scripts/
    └── setup_db.sql        ← idempotent schema creation (not yet created)
```

---

## Port Map

| Port | Service |
|------|---------|
| **8084** | AR Collection MCP server |
| **8090** | Shared MCP Gateway |

---

## Verified State

| Component | Status |
|-----------|--------|
| Project structure | ✅ Created |
| Dependencies | ❌ Run `pip install -r requirements.txt` |
| DB schema | ❌ Not yet designed |
| MCP server | ❌ Not yet implemented |
| Slack bot | ❌ Not yet configured |
