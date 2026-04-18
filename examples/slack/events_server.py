"""
Slack Events API example backed by a managed agent session.

This server accepts Slack Events API payloads at `/slack/events`, creates a new
managed-agent session per inbound user message, forwards the Slack message into
that session, and waits until the session reaches an idle state.

Environment variables:
    ANTHROPIC_API_KEY=sk-ant-...
    ANTHROPIC_AGENT_ID=agent_011Ca8aSumLi1szcRYV1isWt
    ANTHROPIC_ENVIRONMENT_ID=env_...
    ANTHROPIC_VAULT_IDS=vlt_123,vlt_456

Run:
    python examples/slack/events_server.py
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

logger = logging.getLogger(__name__)

BETAS: list[str] = ["managed-agents-2026-04-01"]
DEFAULT_POLL_INTERVAL_SECONDS = float(os.getenv("SLACK_AGENT_POLL_INTERVAL_SECONDS", "2"))
DEFAULT_POLL_TIMEOUT_SECONDS = float(os.getenv("SLACK_AGENT_POLL_TIMEOUT_SECONDS", "120"))

app = FastAPI(title="focalpoint Slack Events example", version="0.1.0")
active_sessions: dict[str, str] = {}
session_status: dict[str, dict[str, str]] = {}


def _get_agent_id() -> str:
    agent_id = os.getenv("ANTHROPIC_AGENT_ID", "agent_011Ca8aSumLi1szcRYV1isWt")
    if not agent_id:
        raise RuntimeError("ANTHROPIC_AGENT_ID is not set.")
    return agent_id


def _get_environment_id() -> str:
    environment_id = os.getenv(
        "ANTHROPIC_ENVIRONMENT_ID",
        "env_01X5N6iGzqU8mbqNuoWmmUye",
    )
    if not environment_id:
        raise RuntimeError("ANTHROPIC_ENVIRONMENT_ID is not set.")
    return environment_id


def _get_vault_ids() -> list[str]:
    raw = os.getenv("ANTHROPIC_VAULT_IDS", "vlt_011CZtQCniKgM1WZVczFdwTf")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")

    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def _get_slack_signing_secret() -> str:
    return os.getenv("SLACK_SIGNING_SECRET", "").strip()


def _get_slack_bot_token() -> str:
    return os.getenv("SLACK_BOT_TOKEN", "").strip()


def _post_slack_message(channel: str, text: str, thread_ts: str | None = None) -> bool:
    token = _get_slack_bot_token()
    if not token:
        logger.warning("SLACK_BOT_TOKEN is not set; cannot post status message to Slack.")
        return False

    payload: dict[str, Any] = {"channel": channel, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Slack API error: {result.get('error', 'unknown_error')}")
    return True


def _verify_slack_signature(request: Request, body: bytes) -> bool:
    secret = _get_slack_signing_secret()
    if not secret:
        return True

    timestamp = request.headers.get("x-slack-request-timestamp", "")
    signature = request.headers.get("x-slack-signature", "")
    if not timestamp or not signature:
        return False

    try:
        request_ts = int(timestamp)
    except ValueError:
        return False

    if abs(time.time() - request_ts) > 60 * 5:
        return False

    basestring = f"v0:{timestamp}:".encode("utf-8") + body
    computed = "v0=" + hmac.new(secret.encode("utf-8"), basestring, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def _extract_user_id(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    user_id = event.get("user")
    if isinstance(user_id, str):
        return user_id
    return ""


def _extract_user_text(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    text = event.get("text")
    if isinstance(text, str):
        return text.strip().lower()
    return ""


def _extract_channel(payload: dict[str, Any]) -> str:
    event = payload.get("event") or {}
    channel = event.get("channel")
    if isinstance(channel, str):
        return channel
    return ""


def _extract_thread_ts(payload: dict[str, Any]) -> str | None:
    event = payload.get("event") or {}
    thread_ts = event.get("thread_ts") or event.get("ts")
    if isinstance(thread_ts, str):
        return thread_ts
    return None


def _should_ignore_event(payload: dict[str, Any]) -> bool:
    event = payload.get("event") or {}
    if payload.get("type") != "event_callback":
        return False
    if event.get("type") != "message":
        return True
    if event.get("subtype") in {"bot_message", "message_changed", "message_deleted"}:
        return True
    if event.get("bot_id") or event.get("app_id"):
        return True
    return False


def _create_session(client: Any):
    create_kwargs: dict[str, Any] = {
        "agent": _get_agent_id(),
        "environment_id": _get_environment_id(),
        "betas": BETAS,
    }
    vault_ids = _get_vault_ids()
    if vault_ids:
        create_kwargs["vault_ids"] = vault_ids
    return client.beta.sessions.create(**create_kwargs)


def _send_user_message(client: Any, session_id: str, text: str) -> None:
    client.beta.sessions.events.send(
        session_id=session_id,
        events=[
            {
                "type": "user.message",
                "content": [{"type": "text", "text": text}],
            }
        ],
        betas=BETAS,
    )


def _list_session_events(client: Any, session_id: str):
    return client.beta.sessions.events.list(session_id=session_id, betas=BETAS)


def _extract_agent_message_text(event: Any) -> str:
    parts: list[str] = []
    for block in getattr(event, "content", []) or []:
        text = getattr(block, "text", "")
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _record_session_debug(user_id: str, **fields: str) -> None:
    current = session_status.get(user_id, {}).copy()
    current.update(fields)
    session_status[user_id] = current


def _emit_terminal_agent_output(user_id: str, session_id: str, text: str) -> None:
    if not text:
        return
    logger.info(
        "Managed-agent terminal output\nuser_id=%s\nsession_id=%s\n---\n%s\n---",
        user_id,
        session_id,
        text,
    )


async def _wait_for_session_idle(client: Any, session_id: str) -> tuple[str, str]:
    deadline = asyncio.get_running_loop().time() + DEFAULT_POLL_TIMEOUT_SECONDS
    latest_agent_text = ""
    while True:
        events = await asyncio.to_thread(_list_session_events, client, session_id)
        for event in events.data:
            if event.type == "agent.message":
                latest_agent_text = _extract_agent_message_text(event) or latest_agent_text
            if event.type == "session.status_idle":
                return session_id, latest_agent_text
            if event.type == "session.error":
                error = getattr(event, "error", None)
                message = getattr(error, "message", "Managed agent session error.")
                raise RuntimeError(message)
            if event.type == "session.status_terminated":
                raise RuntimeError("Managed agent session terminated before becoming idle.")

        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("Timed out waiting for the managed agent session to become idle.")
        await asyncio.sleep(DEFAULT_POLL_INTERVAL_SECONDS)


async def _start_user_session(text: str) -> str:
    client = await asyncio.to_thread(_build_client)
    session = await asyncio.to_thread(_create_session, client)
    session_id = session.id

    await asyncio.to_thread(_send_user_message, client, session_id, text)
    return await _wait_for_session_idle(client, session_id)


async def _create_and_send_user_session(text: str) -> str:
    client = await asyncio.to_thread(_build_client)
    session = await asyncio.to_thread(_create_session, client)
    session_id = session.id
    await asyncio.to_thread(_send_user_message, client, session_id, text)
    return session_id


async def _send_followup_to_session(session_id: str, text: str) -> str:
    client = await asyncio.to_thread(_build_client)
    await asyncio.to_thread(_send_user_message, client, session_id, text)
    completed_session_id, _ = await _wait_for_session_idle(client, session_id)
    return completed_session_id


async def _notify_slack(channel: str, text: str, thread_ts: str | None = None) -> None:
    if not channel:
        return
    try:
        await asyncio.to_thread(_post_slack_message, channel, text, thread_ts)
    except Exception:
        logger.exception("Failed to post status message to Slack channel %s", channel)


async def _process_trigger(user_id: str, text: str, channel: str, thread_ts: str | None) -> None:
    try:
        if "weekly update" in text:
            session_id = await _create_and_send_user_session(text)
            active_sessions[user_id] = session_id
            _record_session_debug(
                user_id,
                session_id=session_id,
                status="started",
                last_trigger="weekly update",
            )
            logger.info("Started managed-agent session for Slack user %s: %s", user_id, session_id)
            await _notify_slack(
                channel,
                f"Your weekly update job has started. Managed agent session: `{session_id}`",
                thread_ts,
            )
            client = await asyncio.to_thread(_build_client)
            deadline = asyncio.get_running_loop().time() + DEFAULT_POLL_TIMEOUT_SECONDS
            latest_agent_text = ""
            while True:
                events = await asyncio.to_thread(_list_session_events, client, session_id)
                event_types: list[str] = []
                for event in events.data:
                    event_types.append(event.type)
                    if event.type == "agent.message":
                        latest_agent_text = _extract_agent_message_text(event) or latest_agent_text
                        logger.info(
                            "Managed-agent message observed for %s (%s chars)",
                            session_id,
                            len(latest_agent_text),
                        )
                        _emit_terminal_agent_output(user_id, session_id, latest_agent_text)
                        _record_session_debug(
                            user_id,
                            session_id=session_id,
                            status="agent_message",
                            last_event_type=event.type,
                            final_output=latest_agent_text,
                            final_output_preview=latest_agent_text[:200],
                            observed_event_types=",".join(event_types),
                        )
                    elif event.type == "session.status_idle":
                        logger.info("Managed-agent session %s reached idle", session_id)
                        _emit_terminal_agent_output(user_id, session_id, latest_agent_text)
                        _record_session_debug(
                            user_id,
                            session_id=session_id,
                            status="idle",
                            last_event_type=event.type,
                            final_output=latest_agent_text,
                            final_output_preview=latest_agent_text[:200],
                            observed_event_types=",".join(event_types),
                        )
                        return
                    elif event.type == "session.error":
                        error = getattr(event, "error", None)
                        message = getattr(error, "message", "Managed agent session error.")
                        _record_session_debug(
                            user_id,
                            session_id=session_id,
                            status="failed",
                            last_event_type=event.type,
                            error_message=message,
                            observed_event_types=",".join(event_types),
                        )
                        raise RuntimeError(message)
                    elif event.type == "session.status_terminated":
                        _record_session_debug(
                            user_id,
                            session_id=session_id,
                            status="terminated",
                            last_event_type=event.type,
                            observed_event_types=",".join(event_types),
                        )
                        raise RuntimeError("Managed agent session terminated before becoming idle.")

                _record_session_debug(
                    user_id,
                    session_id=session_id,
                    status="polling",
                    final_output=latest_agent_text,
                    final_output_preview=latest_agent_text[:200],
                    observed_event_types=",".join(event_types),
                )

                if asyncio.get_running_loop().time() >= deadline:
                    _record_session_debug(
                        user_id,
                        session_id=session_id,
                        status="timeout",
                        final_output=latest_agent_text,
                        final_output_preview=latest_agent_text[:200],
                        observed_event_types=",".join(event_types),
                    )
                    raise TimeoutError("Timed out waiting for the managed agent session to become idle.")
                await asyncio.sleep(DEFAULT_POLL_INTERVAL_SECONDS)
            return

        if "approve" in text and user_id in active_sessions:
            _record_session_debug(
                user_id,
                session_id=active_sessions[user_id],
                status="approving",
                last_trigger="approve",
            )
            await _notify_slack(
                channel,
                "Approval received. I’m continuing the workflow now.",
                thread_ts,
            )
            session_id = await _send_followup_to_session(active_sessions[user_id], "approve")
            _record_session_debug(user_id, session_id=session_id, status="approved")
            logger.info("Sent approval to managed-agent session for Slack user %s: %s", user_id, session_id)
            await _notify_slack(
                channel,
                f"Approval sent to managed agent session: `{session_id}`",
                thread_ts,
            )
            return

        logger.info("Ignoring Slack message for user %s: no matching trigger", user_id)
    except TimeoutError:
        logger.warning("Slack background processing timed out for user %s", user_id)
        if user_id in active_sessions:
            _record_session_debug(user_id, session_id=active_sessions[user_id], status="timeout")
        await _notify_slack(
            channel,
            "The backend job is still running longer than expected. Please check back shortly.",
            thread_ts,
        )
    except RuntimeError:
        logger.exception("Slack background processing failed for user %s", user_id)
        if user_id in active_sessions:
            _record_session_debug(user_id, session_id=active_sessions[user_id], status="failed")
        await _notify_slack(
            channel,
            "The backend job failed before it could complete. Please try again.",
            thread_ts,
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/debug/sessions/{user_id}")
async def get_session_status(user_id: str) -> dict[str, str]:
    if user_id in session_status:
        return session_status[user_id]
    raise HTTPException(status_code=404, detail="No session found for that Slack user.")


@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    if not _verify_slack_signature(request, body):
        raise HTTPException(status_code=401, detail="Invalid Slack signature.")

    payload = await request.json()
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    if _should_ignore_event(payload):
        return {"ok": True, "ignored": True}

    user_id = _extract_user_id(payload)
    text = _extract_user_text(payload)
    channel = _extract_channel(payload)
    thread_ts = _extract_thread_ts(payload)
    if not text or not user_id:
        return {"ok": True, "ignored": True, "reason": "no_text"}

    if "weekly update" in text or ("approve" in text and user_id in active_sessions):
        background_tasks.add_task(_process_trigger, user_id, text, channel, thread_ts)
        return {"ok": True, "queued": True}

    return {"ok": True, "ignored": True, "reason": "no_trigger"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
