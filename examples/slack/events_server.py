"""
Slack Events API server backed by Anthropic Managed Agent sessions.

Listens at /slack/events. Two triggers are supported:
  - "weekly update" → starts a new managed-agent session, polls until idle
  - "approve"       → resumes a paused session for the same Slack user

Required env vars:
    ANTHROPIC_API_KEY
    ANTHROPIC_AGENT_ID
    ANTHROPIC_ENVIRONMENT_ID

Optional env vars:
    ANTHROPIC_VAULT_IDS                    (comma-separated)
    SLACK_SIGNING_SECRET                   (omit to skip signature verification in dev)
    SLACK_BOT_TOKEN
    SLACK_AGENT_POLL_INTERVAL_SECONDS      (default: 2)
    SLACK_AGENT_POLL_TIMEOUT_SECONDS       (default: 120)

Run:
    python examples/slack/events_server.py

Dependencies (additions over original):
    pydantic-settings, httpx
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import anthropic
import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

logger = logging.getLogger(__name__)

BETAS: list[str] = ["managed-agents-2026-04-01"]


# ---------------------------------------------------------------------------
# Settings — validated once at startup; no credential defaults in source
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")

    anthropic_api_key: str
    anthropic_agent_id: str
    anthropic_environment_id: str
    anthropic_vault_ids: str = ""
    slack_signing_secret: str = ""
    slack_bot_token: str = ""
    slack_agent_poll_interval_seconds: float = 2.0
    slack_agent_poll_timeout_seconds: float = 120.0

    @property
    def vault_ids(self) -> list[str]:
        return [v.strip() for v in self.anthropic_vault_ids.split(",") if v.strip()]


settings = Settings()


# ---------------------------------------------------------------------------
# Trace — correlation context + elapsed timing carried across every hand-off
# ---------------------------------------------------------------------------

@dataclass
class Trace:
    """
    Created once per background job. Carried through every function so every
    log line shares the same user/trigger/session/elapsed_ms fields — making
    it trivial to grep a full request lifecycle from a single session_id.
    """
    user_id: str
    trigger: str
    session_id: str = ""
    _t0: float = field(default_factory=time.perf_counter, repr=False)

    def elapsed_ms(self) -> int:
        return round((time.perf_counter() - self._t0) * 1000)

    def log(self, stage: str, **extra) -> None:
        self._emit(logger.info, stage, **extra)

    def warn(self, stage: str, **extra) -> None:
        self._emit(logger.warning, stage, **extra)

    def error(self, stage: str, **extra) -> None:
        self._emit(logger.error, stage, **extra)

    def _emit(self, fn: Any, stage: str, **extra) -> None:
        fields = {
            "stage": stage,
            "user": self.user_id,
            "trigger": self.trigger,
            "session": self.session_id or "—",
            "elapsed_ms": self.elapsed_ms(),
            **extra,
        }
        fn(" ".join(f"{k}={v}" for k, v in fields.items()))


# ---------------------------------------------------------------------------
# App lifecycle — singleton Anthropic client + shared HTTP session
# ---------------------------------------------------------------------------

_sessions_lock = asyncio.Lock()
active_sessions: dict[str, str] = {}           # user_id → session_id
session_status: dict[str, dict[str, str]] = {} # user_id → debug fields


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    app.state.http = httpx.AsyncClient(timeout=15)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Managed Agent Slack Events", version="0.2.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Anthropic session helpers
# ---------------------------------------------------------------------------

def _create_session(client: anthropic.Anthropic) -> Any:
    kwargs: dict[str, Any] = {
        "agent": settings.anthropic_agent_id,
        "environment_id": settings.anthropic_environment_id,
        "betas": BETAS,
    }
    if settings.vault_ids:
        kwargs["vault_ids"] = settings.vault_ids
    return client.beta.sessions.create(**kwargs)


def _send_message(client: anthropic.Anthropic, session_id: str, text: str) -> None:
    client.beta.sessions.events.send(
        session_id=session_id,
        events=[{"type": "user.message", "content": [{"type": "text", "text": text}]}],
        betas=BETAS,
    )


def _list_events(client: anthropic.Anthropic, session_id: str) -> Any:
    return client.beta.sessions.events.list(session_id=session_id, betas=BETAS)


def _extract_agent_text(event: Any) -> str:
    return "\n".join(
        getattr(block, "text", "")
        for block in (getattr(event, "content", []) or [])
        if getattr(block, "text", "")
    ).strip()


async def _poll_until_idle(
    client: anthropic.Anthropic,
    session_id: str,
    trace: Trace,
    on_agent_message: Callable[[str], None] | None = None,
) -> str:
    """Poll session events until idle. Returns final agent text."""
    deadline = asyncio.get_running_loop().time() + settings.slack_agent_poll_timeout_seconds
    latest_text = ""
    poll_n = 0

    while True:
        poll_n += 1
        # ── hand-off 9: BackgroundTask → Anthropic (poll fetch) ──────────────
        trace.log("poll.fetch", poll_n=poll_n)
        events = await asyncio.to_thread(_list_events, client, session_id)

        # ── hand-off 10: Anthropic → PollLoop (events returned) ──────────────
        observed_types = [e.type for e in events.data]
        trace.log(
            "poll.events_received",
            poll_n=poll_n,
            count=len(observed_types),
            types=",".join(observed_types) or "none",
        )

        for event in events.data:
            if event.type == "agent.message":
                # ── hand-off 11: agent output observed ───────────────────────
                latest_text = _extract_agent_text(event) or latest_text
                trace.log("poll.agent_message", chars=len(latest_text), preview=repr(latest_text[:80]))
                if on_agent_message:
                    on_agent_message(latest_text)

            elif event.type == "session.status_idle":
                # ── hand-off 12: session reached idle ────────────────────────
                trace.log("poll.idle", poll_n=poll_n, output_chars=len(latest_text))
                return latest_text

            elif event.type == "session.error":
                # ── hand-off 13a: session error ──────────────────────────────
                msg = getattr(getattr(event, "error", None), "message", "Managed agent session error.")
                trace.error("poll.session_error", reason=msg)
                raise RuntimeError(msg)

            elif event.type == "session.status_terminated":
                # ── hand-off 13b: session terminated ─────────────────────────
                trace.error("poll.terminated", poll_n=poll_n)
                raise RuntimeError("Managed agent session terminated before becoming idle.")

        # ── hand-off 14: still running — log deadline and sleep ──────────────
        remaining_s = round(deadline - asyncio.get_running_loop().time())
        if remaining_s <= 0:
            trace.warn("poll.timeout", poll_n=poll_n)
            raise TimeoutError("Timed out waiting for managed agent session to become idle.")
        trace.log("poll.waiting", poll_n=poll_n, remaining_s=remaining_s)
        await asyncio.sleep(settings.slack_agent_poll_interval_seconds)


# ---------------------------------------------------------------------------
# Slack helpers
# ---------------------------------------------------------------------------

async def _post_slack_message(
    http: httpx.AsyncClient,
    channel: str,
    text: str,
    trace: Trace,
    thread_ts: str | None = None,
) -> None:
    if not settings.slack_bot_token:
        trace.warn("slack.skip", reason="SLACK_BOT_TOKEN_not_set")
        return
    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    # ── hand-off 15: BackgroundTask → Slack ──────────────────────────────────
    trace.log("slack.posting", channel=channel, chars=len(text))
    resp = await http.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
        json=payload,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"Slack API error: {result.get('error', 'unknown_error')}")
    # ── hand-off 16: Slack confirmed delivery ─────────────────────────────────
    trace.log("slack.posted", channel=channel, status="ok")


def _verify_slack_signature(request: Request, body: bytes) -> bool:
    if not settings.slack_signing_secret:
        return True  # dev mode — no secret configured
    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")
    if not timestamp or not signature:
        return False
    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False
    basestring = f"v0:{timestamp}:".encode() + body
    computed = "v0=" + hmac.new(
        settings.slack_signing_secret.encode(), basestring, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def _should_ignore_event(payload: dict[str, Any]) -> bool:
    if payload.get("type") != "event_callback":
        return True  # url_verification handled upstream; ignore everything else
    event = payload.get("event") or {}
    if event.get("type") != "message":
        return True
    if event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
        return True
    if event.get("bot_id") or event.get("app_id"):
        return True
    return False


def _extract_event_fields(payload: dict[str, Any]) -> tuple[str, str, str, str | None]:
    """Return (user_id, text, channel, thread_ts)."""
    event = payload.get("event") or {}
    user_id = event.get("user", "") if isinstance(event.get("user"), str) else ""
    text = (event.get("text") or "").strip().lower()
    channel = event.get("channel", "") if isinstance(event.get("channel"), str) else ""
    raw_ts = event.get("thread_ts") or event.get("ts")
    thread_ts = raw_ts if isinstance(raw_ts, str) else None
    return user_id, text, channel, thread_ts


# ---------------------------------------------------------------------------
# Trigger handlers
# ---------------------------------------------------------------------------

async def _handle_weekly_update(
    client: anthropic.Anthropic,
    http: httpx.AsyncClient,
    trace: Trace,
    text: str,
    channel: str,
    thread_ts: str | None,
) -> None:
    # ── hand-off 4: BackgroundTask → Anthropic (create session) ──────────────
    trace.log("session.creating", agent=settings.anthropic_agent_id)
    session = await asyncio.to_thread(_create_session, client)
    # ── hand-off 5: Anthropic → BackgroundTask (session_id returned) ─────────
    trace.session_id = session.id
    trace.log("session.created")

    # ── hand-off 6: BackgroundTask → Anthropic (send user message) ───────────
    trace.log("message.sending", chars=len(text))
    await asyncio.to_thread(_send_message, client, trace.session_id, text)
    # ── hand-off 7: Anthropic → BackgroundTask (message accepted) ────────────
    trace.log("message.sent")

    async with _sessions_lock:
        active_sessions[trace.user_id] = trace.session_id
        session_status[trace.user_id] = {"session_id": trace.session_id, "status": "started"}
    trace.log("state.recorded")

    await _post_slack_message(http, channel, f"Weekly update started. Session: `{trace.session_id}`", trace, thread_ts)

    def _on_message(agent_text: str) -> None:
        trace.log("agent.message_observed", chars=len(agent_text))
        session_status[trace.user_id].update({"status": "agent_message", "output_preview": agent_text[:200]})

    # ── hand-off 8: BackgroundTask → PollLoop ────────────────────────────────
    trace.log("poll.entering")
    final_text = await _poll_until_idle(client, trace.session_id, trace, on_agent_message=_on_message)
    # ── hand-off 8 return: PollLoop → BackgroundTask ──────────────────────────
    trace.log("poll.complete", output_chars=len(final_text))

    async with _sessions_lock:
        session_status[trace.user_id].update({"status": "idle", "final_output": final_text})
    trace.log("state.idle")


async def _handle_approve(
    client: anthropic.Anthropic,
    http: httpx.AsyncClient,
    trace: Trace,
    channel: str,
    thread_ts: str | None,
) -> None:
    async with _sessions_lock:
        session_id = active_sessions.get(trace.user_id)
    if not session_id:
        trace.warn("approval.no_active_session")
        return

    trace.session_id = session_id
    # ── hand-off 17a: approval trigger received, ack Slack ───────────────────
    trace.log("approval.received")
    await _post_slack_message(http, channel, "Approval received. Continuing the workflow.", trace, thread_ts)

    # ── hand-off 17b: BackgroundTask → Anthropic (send approval) ─────────────
    trace.log("approval.sending")
    await asyncio.to_thread(_send_message, client, session_id, "approve")
    # ── hand-off 17c: Anthropic → BackgroundTask (approval accepted) ──────────
    trace.log("approval.sent")

    # ── hand-off 17d: entering poll after approval ────────────────────────────
    trace.log("poll.entering")
    await _poll_until_idle(client, session_id, trace)
    trace.log("poll.complete")

    async with _sessions_lock:
        session_status[trace.user_id]["status"] = "approved"
    trace.log("state.approved")
    await _post_slack_message(http, channel, f"Workflow approved and complete. Session: `{session_id}`", trace, thread_ts)


async def _process_trigger(
    client: anthropic.Anthropic,
    http: httpx.AsyncClient,
    user_id: str,
    trigger: str,
    text: str,
    channel: str,
    thread_ts: str | None,
) -> None:
    trace = Trace(user_id=user_id, trigger=trigger)
    trace.log("trigger.started")
    try:
        if trigger == "weekly_update":
            await _handle_weekly_update(client, http, trace, text, channel, thread_ts)
        elif trigger == "approve":
            await _handle_approve(client, http, trace, channel, thread_ts)
        trace.log("trigger.complete")
    except TimeoutError:
        trace.warn("trigger.timeout")
        async with _sessions_lock:
            if user_id in session_status:
                session_status[user_id]["status"] = "timeout"
        await _post_slack_message(
            http, channel, "The job is still running. Please check back shortly.", trace, thread_ts
        )
    except RuntimeError:
        trace.error("trigger.failed")
        logger.exception("trigger.failed user=%s session=%s", user_id, trace.session_id)
        async with _sessions_lock:
            if user_id in session_status:
                session_status[user_id]["status"] = "failed"
        await _post_slack_message(
            http, channel, "The job failed. Please try again.", trace, thread_ts
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/sessions/{user_id}")
async def get_session_status(user_id: str) -> dict[str, str]:
    async with _sessions_lock:
        status = session_status.get(user_id)
    if status is None:
        raise HTTPException(status_code=404, detail="No session found for that Slack user.")
    return status


@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    body = await request.body()

    # ── hand-off 1: Slack → Server ────────────────────────────────────────────
    logger.info("stage=event.received bytes=%d", len(body))

    # ── hand-off 2: signature check ───────────────────────────────────────────
    if not _verify_slack_signature(request, body):
        logger.warning("stage=event.sig_rejected")
        raise HTTPException(status_code=401, detail="Invalid Slack signature.")
    logger.info("stage=event.sig_ok")

    payload: dict[str, Any] = await request.json()

    if payload.get("type") == "url_verification":
        logger.info("stage=event.url_verification")
        return {"challenge": payload.get("challenge")}

    if _should_ignore_event(payload):
        logger.info("stage=event.ignored type=%s", payload.get("type"))
        return {"ok": True, "ignored": True}

    user_id, text, channel, thread_ts = _extract_event_fields(payload)
    if not user_id or not text:
        logger.info("stage=event.ignored reason=no_text")
        return {"ok": True, "ignored": True, "reason": "no_text"}

    # ── hand-off 3: classify trigger ──────────────────────────────────────────
    trigger: str | None = None
    if "weekly update" in text:
        trigger = "weekly_update"
    elif "approve" in text and user_id in active_sessions:
        trigger = "approve"

    if trigger is None:
        logger.info("stage=event.ignored reason=no_trigger user=%s", user_id)
        return {"ok": True, "ignored": True, "reason": "no_trigger"}

    logger.info("stage=event.queuing user=%s trigger=%s channel=%s", user_id, trigger, channel)
    background_tasks.add_task(
        _process_trigger,
        request.app.state.anthropic,
        request.app.state.http,
        user_id, trigger, text, channel, thread_ts,
    )
    # ── hand-off 3 complete: queued to BackgroundTask, HTTP response returned ─
    logger.info("stage=event.queued user=%s trigger=%s", user_id, trigger)
    return {"ok": True, "queued": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
