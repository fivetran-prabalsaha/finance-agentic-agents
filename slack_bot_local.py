#!/usr/bin/env python3
"""
Local Slack Bot for Compliance Agent MCP Server
Uses Socket Mode for WebSocket-based connection (no webhooks needed)

Setup:
1. pip install slack-bolt anthropic requests python-dotenv
2. Create .env file with tokens
3. Run: python slack_bot_local.py
"""

import os
import re
import sys
import logging
import threading
import itertools
import hashlib
from typing import Dict, Any, Optional, List
import json
import requests
import redis as redis_lib
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# MCP Server configuration
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Token / context control
MAX_TOKENS_SLACK = int(os.environ.get("SLACK_MAX_TOKENS", "1024"))
MAX_HISTORY_TURNS = int(os.environ.get("SLACK_MAX_HISTORY_TURNS", "4"))
TOOL_OUTPUT_MAX_CHARS = int(os.environ.get("SLACK_TOOL_OUTPUT_MAX_CHARS", "2000"))
# Rolling summary: compress tool results larger than this with Haiku before storing in history
ROLLING_SUMMARY_MIN_CHARS = int(os.environ.get("SLACK_ROLLING_SUMMARY_MIN_CHARS", "800"))
# Responses longer than this get uploaded as a Slack file and the message shows a trimmed summary + link
MAX_SLACK_RESPONSE_CHARS = int(os.environ.get("SLACK_MAX_RESPONSE_CHARS", "2000"))

# Global variable to store MCP tools (fetched at startup)
MCP_TOOLS: List[Dict[str, Any]] = []

# ---------------------------------------------------------------------------
# Phase A — Redis TTL Cache for MCP tool calls
# Feature flag: set USE_MCP_CACHE=false in .env to disable
# ---------------------------------------------------------------------------
USE_MCP_CACHE = os.getenv("USE_MCP_CACHE", "true").lower() == "true"

_redis_client = None

def _get_redis():
    """Lazy Redis client — returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis_lib.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
                socket_connect_timeout=1,
            )
            _redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable — MCP cache disabled: {e}")
            _redis_client = None
    return _redis_client

# TTL in seconds per read-only tool
_MCP_CACHE_TTL = {
    "get_user_violations":      3600,   # 1 hour
    "get_violation_stats":      1800,   # 30 min
    "get_role_conflicts":       86400,  # 24 hours
    "get_role_risk_matrix":     86400,  # 24 hours (matrix only changes after a sync + rebuild)
    "analyze_access_request":   3600,   # 1 hour
    "initialize_session":       300,    # 5 min
    "list_systems":             3600,
    "list_all_users":           1800,
    "get_compliance_report":    1800,
    "search_permissions":       3600,
    "check_my_approval_authority": 3600,
    "validate_job_role":        3600,
}

# Tools that mutate state — never cached
_MUTATING_TOOLS = {
    "trigger_manual_sync",
    "approve_exception",
    "request_exception_approval",
    "remediate_violation",
    "update_exception_status",
}

# Thread-local flag so cache hits inside call_mcp_tool() can be reported
# on the root slack_compliance_query LangSmith run (not just the child span)
_cache_hit_tls = threading.local()

# ---------------------------------------------------------------------------
# Human feedback loop — Block Kit buttons on every response
# Feature flag: set USE_ANSWER_FEEDBACK=false in .env to disable
# ---------------------------------------------------------------------------
USE_ANSWER_FEEDBACK = os.getenv("USE_ANSWER_FEEDBACK", "true").lower() == "true"

_langsmith_client = None

def _get_langsmith_client():
    """Lazy LangSmith client for create_feedback() calls."""
    global _langsmith_client
    if _langsmith_client is None:
        try:
            from langsmith import Client
            _langsmith_client = Client()
        except Exception as e:
            logger.warning(f"LangSmith client unavailable: {e}")
    return _langsmith_client

# ---------------------------------------------------------------------------
# Phase B — Conversation Summarization
# Feature flag: set USE_CONV_SUMMARIES=false in .env to disable
# ---------------------------------------------------------------------------
USE_CONV_SUMMARIES = os.getenv("USE_CONV_SUMMARIES", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Phase C — Correction Embeddings (few-shot context from past corrections)
# Feature flag: set USE_CORRECTION_CONTEXT=false in .env to disable
# ---------------------------------------------------------------------------
USE_CORRECTION_CONTEXT = os.getenv("USE_CORRECTION_CONTEXT", "true").lower() == "true"

_db_session_factory = None


def _get_db_session():
    """Lazy SQLAlchemy session — returns None if DB is unavailable."""
    global _db_session_factory
    if _db_session_factory is None:
        try:
            from models.database_config import get_db_config
            _db_session_factory = get_db_config().SessionLocal
        except Exception as e:
            logger.warning(f"DB unavailable — conversation summaries disabled: {e}")
            _db_session_factory = False  # sentinel: stop retrying
    if _db_session_factory is False:
        return None
    return _db_session_factory()


def _get_prior_summaries(user_email: str, limit: int = 3) -> str:
    """
    Retrieve the N most recent non-expired conversation summaries for a user.

    Returns a formatted string to inject into the system message, or '' if none.
    Injects ~150 tokens instead of ~2K raw prior messages.
    """
    if not USE_CONV_SUMMARIES:
        return ""
    try:
        session = _get_db_session()
        if not session:
            return ""
        try:
            from models.conversation_summary import ConversationSummary
            from datetime import datetime as _dt
            rows = (
                session.query(ConversationSummary)
                .filter(ConversationSummary.user_email == user_email)
                .filter(
                    (ConversationSummary.expires_at == None) |  # noqa: E711
                    (ConversationSummary.expires_at > _dt.utcnow())
                )
                .order_by(ConversationSummary.created_at.desc())
                .limit(limit)
                .all()
            )
            if not rows:
                return ""
            summaries = [row.summary for row in reversed(rows)]
            logger.info(f"Injecting {len(summaries)} prior summaries for {user_email}")
            return (
                "## Prior conversation context (auto-generated summaries)\n"
                + "\n".join(f"- {s}" for s in summaries)
            )
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Could not fetch summaries for {user_email}: {e}")
        return ""


def _write_conversation_summary(
    user_email: str, channel_id: str, exchange: list, final_answer: str
):
    """
    Generate a 2-3 sentence Haiku summary of the exchange and persist to Postgres.

    Called in a non-blocking background thread after each DM response.
    Uses Haiku (not Opus) — cheap and fast enough for summarization.
    """
    if not USE_CONV_SUMMARIES:
        return
    try:
        from langchain_anthropic import ChatAnthropic
        from datetime import datetime as _dt, timedelta
        haiku_sum = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            anthropic_api_key=ANTHROPIC_API_KEY,
        )
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content'][:300]}"
            for m in (exchange or [])[-6:]
        )
        prompt = (
            "Summarise this compliance conversation in 2-3 sentences.\n"
            "Extract: users/emails mentioned, roles discussed, decision made "
            "(APPROVED/DENIED/ESCALATED/INFO — or omit if purely informational).\n"
            "Be concise — aim for under 100 words.\n\n"
            f"History:\n{history_text}\n\n"
            f"Final answer: {final_answer[:500]}"
        )
        summary_text = haiku_sum.invoke(prompt).content.strip()

        session = _get_db_session()
        if not session:
            return
        try:
            from models.conversation_summary import ConversationSummary
            row = ConversationSummary(
                user_email=user_email,
                channel_id=channel_id,
                summary=summary_text,
                expires_at=_dt.utcnow() + timedelta(days=90),
            )
            session.add(row)
            session.commit()
            logger.info(f"Saved summary for {user_email}: {summary_text[:80]}...")
        except Exception as e:
            session.rollback()
            logger.warning(f"Could not save conversation summary: {e}")
        finally:
            session.close()
    except Exception as e:
        logger.warning(f"Summary write-back failed: {e}")


def fetch_mcp_tools():
    """
    Fetch available tools from the MCP server at startup

    Returns:
        List of tool definitions in Claude API format
    """
    try:
        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            },
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tools = result["result"]["tools"]
                # Convert MCP tool format to Claude API format
                claude_tools = []
                for tool in tools:
                    claude_tools.append({
                        "name": tool["name"],
                        "description": tool["description"],
                        "input_schema": tool["inputSchema"]
                    })
                logger.info(f"Fetched {len(claude_tools)} tools from MCP server")
                return claude_tools
            else:
                logger.error(f"Unexpected response format: {result}")
                return []
        else:
            logger.error(f"Failed to fetch tools: HTTP {response.status_code}")
            return []

    except Exception as e:
        logger.error(f"Error fetching MCP tools: {e}")
        return []


# Old hardcoded tools removed - now fetched dynamically from MCP server


@traceable(run_type="tool")
def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Call an MCP tool on the local server using JSON-RPC 2.0 protocol

    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments

    Returns:
        Tool result as string
    """
    # -----------------------------------------------------------------------
    # Phase A — Redis cache read (before HTTP call)
    # -----------------------------------------------------------------------
    ttl = _MCP_CACHE_TTL.get(tool_name) if USE_MCP_CACHE else None
    cache_key: Optional[str] = None
    if ttl and tool_name not in _MUTATING_TOOLS:
        cache_key = (
            f"mcp:{tool_name}:"
            f"{hashlib.md5(json.dumps(arguments, sort_keys=True).encode()).hexdigest()}"
        )
        try:
            r = _get_redis()
            if r:
                cached = r.get(cache_key)
                if cached:
                    logger.info(f"Cache HIT: {tool_name}")
                    _cache_hit_tls.hit = True
                    _cache_hit_tls.tool = tool_name
                    return cached
        except Exception as e:
            logger.warning(f"Redis read failed for {tool_name}: {e}")

    try:
        # Build JSON-RPC 2.0 request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            # Extract result from JSON-RPC response
            if "result" in result:
                content = result["result"].get("content", [])
                if content and len(content) > 0:
                    tool_result = content[0].get("text", str(result))
                else:
                    tool_result = str(result.get("result"))
            elif "error" in result:
                logger.error(f"MCP tool error: {result['error']}")
                return f"❌ Error calling {tool_name}: {result['error'].get('message', 'Unknown error')}"
            else:
                tool_result = str(result)

            # -------------------------------------------------------------------
            # Phase A — Redis cache write (after successful HTTP call)
            # -------------------------------------------------------------------
            if cache_key and ttl and tool_result and not tool_result.startswith("❌"):
                try:
                    r = _get_redis()
                    if r:
                        r.setex(cache_key, ttl, tool_result)
                        logger.info(f"Cache SET: {tool_name} (TTL={ttl}s)")
                except Exception as e:
                    logger.warning(f"Redis write failed for {tool_name}: {e}")

            # -------------------------------------------------------------------
            # Phase A — Cache bust after sync (user/role data is now stale)
            # Preserve static keys: SOD rules and system list don't change on sync
            # -------------------------------------------------------------------
            if tool_name == "trigger_manual_sync" and not tool_result.startswith("❌"):
                _SYNC_SAFE_PREFIXES = ("mcp:get_role_conflicts:", "mcp:list_systems:")
                try:
                    r = _get_redis()
                    if r:
                        all_keys = r.keys("mcp:*")
                        bust_keys = [
                            k for k in all_keys
                            if not any(k.startswith(p) for p in _SYNC_SAFE_PREFIXES)
                        ]
                        if bust_keys:
                            r.delete(*bust_keys)
                            logger.info(
                                f"Cache BUST: {len(bust_keys)} keys cleared after trigger_manual_sync"
                            )
                except Exception as e:
                    logger.warning(f"Cache bust failed after trigger_manual_sync: {e}")

            return tool_result
        else:
            logger.error(f"MCP tool call failed: {response.status_code} - {response.text}")
            return f"❌ Error calling {tool_name}: HTTP {response.status_code}"

    except Exception as e:
        logger.error(f"Exception calling MCP tool {tool_name}: {e}")
        return f"❌ Exception calling {tool_name}: {str(e)}"


def extract_user_mentions(message_text: str, slack_client) -> Dict[str, str]:
    """
    Extract Slack user mentions from message and get their email addresses

    Args:
        message_text: Raw message text with Slack mentions like <@U12345>
        slack_client: Slack client for API calls

    Returns:
        Dict mapping user IDs to email addresses
    """
    import re

    user_map = {}
    # Find all user mentions in format <@U12345>
    user_ids = re.findall(r'<@([A-Z0-9]+)>', message_text)

    for user_id in user_ids:
        try:
            user_info = slack_client.users_info(user=user_id)
            email = user_info["user"]["profile"].get("email")
            name = user_info["user"]["real_name"]
            if email:
                user_map[user_id] = {
                    "email": email,
                    "name": name
                }
                logger.info(f"Resolved @{name} to {email}")
        except Exception as e:
            logger.warning(f"Could not resolve user {user_id}: {e}")

    return user_map


def _sanitize_tool_output(tool_name: str, raw_output: str) -> str:
    """
    Trim tool output to TOOL_OUTPUT_MAX_CHARS characters before feeding back to Claude.
    Large tool outputs (e.g., list_all_users) would otherwise blow up the context.
    """
    if len(raw_output) <= TOOL_OUTPUT_MAX_CHARS:
        return raw_output
    trimmed = raw_output[:TOOL_OUTPUT_MAX_CHARS]
    logger.info(f"Tool output for '{tool_name}' trimmed from {len(raw_output)} to {TOOL_OUTPUT_MAX_CHARS} chars")
    return trimmed + f"\n\n[Output truncated — {len(raw_output) - TOOL_OUTPUT_MAX_CHARS} chars omitted]"


def _trim_history(messages: List) -> List:
    """
    Keep at most MAX_HISTORY_TURNS turn-pairs (user + assistant) to cap context growth.

    CRITICAL: Never start the trimmed slice on a ToolMessage or an AIMessage whose
    tool_calls have been cut off. The Anthropic API requires every tool_result block
    to have a matching tool_use in the immediately preceding assistant message.

    Strategy: take the last MAX_HISTORY_TURNS*2 messages as a candidate slice, then
    advance forward to the first HumanMessage — that is always a safe starting point.
    If no HumanMessage is found (edge case: pure tool-exchange history), fall back to
    the full list rather than risking an orphaned tool_result.
    """
    if len(messages) <= MAX_HISTORY_TURNS * 2:
        return messages
    candidate = messages[-(MAX_HISTORY_TURNS * 2):]
    # Advance to the first HumanMessage to avoid orphaned tool_result blocks
    from langchain_core.messages import HumanMessage as _HumanMessage
    for i, m in enumerate(candidate):
        if isinstance(m, _HumanMessage):
            return candidate[i:]
    # Fallback: can't find a clean HumanMessage boundary — return full list
    return messages


def _compress_tool_result(tool_name: str, content: str, llm) -> str:
    """
    Rolling summary: use Haiku to compress a large tool result down to key facts
    before it is stored in the conversation history that Claude re-reads every turn.

    Only fires when content exceeds ROLLING_SUMMARY_MIN_CHARS (default 800 chars).
    Falls back to the original content on any error.
    """
    if len(content) <= ROLLING_SUMMARY_MIN_CHARS:
        return content

    try:
        from langchain_core.messages import HumanMessage as _HM
        prompt = (
            f"Compliance tool '{tool_name}' returned the following result. "
            f"Extract ONLY the key facts in ≤150 tokens: "
            f"emails, role names, violation counts, risk scores, conflict names, "
            f"approval status, and any action items.\n\n{content}"
        )
        resp = llm.invoke([_HM(content=prompt)])
        if isinstance(resp.content, str):
            summary = resp.content
        else:
            summary = "".join(
                b.get("text", "") for b in resp.content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        logger.info(
            f"Rolling summary: '{tool_name}' compressed {len(content)} → {len(summary)} chars"
        )
        return summary if summary else content
    except Exception as e:
        logger.warning(f"Rolling summary failed for '{tool_name}': {e}")
        return content


_THINKING_STAGES = itertools.cycle([
    "⏳ _Analyzing your request..._",
    "🔍 _Querying compliance data..._",
    "🧠 _Reasoning about SOD rules..._",
    "📊 _Processing results..._",
    "✍️ _Drafting response..._",
])


def _animate_thinking(client, channel: str, thinking_ts: str, stop_event: threading.Event):
    """Cycle through thinking stage labels every 2.5 s until stop_event is set."""
    for stage in _THINKING_STAGES:
        if stop_event.wait(timeout=2.5):
            break
        try:
            client.chat_update(channel=channel, ts=thinking_ts, text=stage)
        except Exception:
            break


def format_as_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Convert Claude's mrkdwn response into Slack Block Kit blocks.
    Splits on '---' dividers and respects Slack's 3000-char block limit.
    """
    blocks = []
    sections = re.split(r'\n---+\n', text.strip())

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        # Slack section block text limit is 3000 chars
        if len(section) > 3000:
            section = section[:2997] + "…"

        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": section}
        })

        if i < len(sections) - 1:
            blocks.append({"type": "divider"})

    return blocks or [{"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}]


def _feedback_blocks(run_id: str, user_email: str,
                     query: str, answer: str, tool_called: str) -> Dict[str, Any]:
    """
    Build a Slack actions block with 3 feedback buttons appended to bot responses.

    All context is encoded into button value (pipe-separated) so the action handler
    has everything it needs without a Redis lookup.
    Max value length is 2000 chars — previews are capped at 100 chars each.
    """
    payload = "|".join([
        run_id or "",
        user_email or "",
        (query or "")[:100],
        (answer or "")[:100],
        tool_called or "",
    ])
    return {
        "type": "actions",
        "block_id": f"feedback_{(run_id or 'noid')[:36]}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👎", "emoji": True},
                "value": f"NEGATIVE|{payload}",
                "action_id": "feedback_negative",
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "👍", "emoji": True},
                "value": f"POSITIVE|{payload}",
                "action_id": "feedback_positive",
            },
        ],
    }


def _upload_full_response(client, channel: str, title: str, content: str) -> Optional[str]:
    """
    Upload a long response as a Slack file so the in-channel message stays concise.
    Returns the file permalink on success, None on failure.
    Callers should treat None as a soft failure and degrade gracefully.
    """
    try:
        result = client.files_upload_v2(
            channel=channel,
            content=content.encode("utf-8"),
            filename="compliance_analysis.md",
            title=title,
        )
        files = result.get("files", [])
        if files:
            return files[0].get("permalink")
        logger.warning("files_upload_v2 returned ok but no files list")
    except Exception as e:
        logger.warning(f"Slack file upload failed: {e}")
    return None


def _trim_response_for_slack(response: str, client, channel: str) -> str:
    """
    If response exceeds MAX_SLACK_RESPONSE_CHARS, upload the full text as a Slack file
    and return a trimmed version with a link to the full analysis.
    """
    if len(response) <= MAX_SLACK_RESPONSE_CHARS:
        return response

    # Find a clean paragraph or line boundary near the limit
    cutoff = response.rfind('\n\n', 0, MAX_SLACK_RESPONSE_CHARS)
    if cutoff < MAX_SLACK_RESPONSE_CHARS // 2:
        cutoff = response.rfind('\n', 0, MAX_SLACK_RESPONSE_CHARS)
    if cutoff < MAX_SLACK_RESPONSE_CHARS // 2:
        cutoff = MAX_SLACK_RESPONSE_CHARS

    trimmed = response[:cutoff].rstrip()
    permalink = _upload_full_response(client, channel, "Full Compliance Analysis", response)
    if permalink:
        return trimmed + f"\n\n_Full analysis →_ {permalink}"
    return trimmed + "\n\n_Ask me about a specific role for the complete breakdown (e.g. 'tell me more about the Controller role')._"


def _save_feedback(signal: str, run_id: str, user_email: str, channel_id: str,
                   message_ts: str, query: str, answer: str, tool_called: str,
                   correction: str = None) -> None:
    """
    Persist human feedback non-blocking (called via threading.Thread).

    1. Writes to Postgres answer_feedback table.
       If correction is provided (Phase B modal), UPDATEs the existing row by
       run_id rather than inserting a duplicate.
    2. Posts score to LangSmith create_feedback().
       If correction is provided, also posts a 'human_correction' entry with
       the correction text as the comment.
    3. On NEGATIVE (no correction path): busts get_user_violations Redis cache.
    """
    _SIGNAL_SCORES = {"POSITIVE": 1.0, "NEGATIVE": 0.0, "PARTIAL": 0.5, "UNCLEAR": 0.3}

    # 1. Postgres write
    try:
        session = _get_db_session()
        if session:
            try:
                from models.answer_feedback import AnswerFeedback
                from sqlalchemy import text as sqla_text
                if correction and run_id:
                    # UPDATE existing row written when the button was clicked
                    session.execute(
                        sqla_text(
                            "UPDATE answer_feedback SET correction = :c "
                            "WHERE run_id = :r AND signal = 'NEGATIVE'"
                        ),
                        {"c": correction[:1000], "r": run_id},
                    )
                    session.commit()
                    logger.info(f"Updated correction for run={run_id}")
                else:
                    row = AnswerFeedback(
                        run_id=run_id or None,
                        user_email=user_email,
                        channel_id=channel_id,
                        message_ts=message_ts,
                        query_preview=(query or "")[:200],
                        answer_preview=(answer or "")[:200],
                        signal=signal,
                        tool_called=tool_called or None,
                    )
                    session.add(row)
                    session.commit()
                    logger.info(f"Saved feedback {signal} for {user_email} run={run_id}")
            except Exception as e:
                session.rollback()
                logger.warning(f"Could not save answer feedback: {e}")
            finally:
                session.close()
    except Exception as e:
        logger.warning(f"Feedback DB write failed: {e}")

    # 2. LangSmith score write-back
    if run_id:
        try:
            ls = _get_langsmith_client()
            if ls:
                if correction:
                    # Write correction as a separate human_correction entry
                    ls.create_feedback(
                        run_id=run_id,
                        key="human_correction",
                        score=0.0,
                        comment=correction[:1000],
                    )
                    logger.info(f"LangSmith correction posted for run={run_id}")
                else:
                    ls.create_feedback(
                        run_id=run_id,
                        key="human_rating",
                        score=_SIGNAL_SCORES.get(signal, 0.3),
                        comment=f"Slack feedback: {signal}",
                    )
                    logger.info(f"LangSmith feedback posted: {signal} → {_SIGNAL_SCORES.get(signal)}")
        except Exception as e:
            logger.warning(f"LangSmith feedback write failed: {e}")

    # 3. Redis cache bust on NEGATIVE (only on initial signal, not correction update)
    if signal == "NEGATIVE" and not correction:
        try:
            r = _get_redis()
            if r:
                keys = r.keys("mcp:get_user_violations:*")
                if keys:
                    r.delete(*keys)
                    logger.info(f"Busted {len(keys)} violation cache key(s) after NEGATIVE feedback")
        except Exception as e:
            logger.warning(f"Redis cache bust failed: {e}")

    # 4. Phase C — embed and store correction for future few-shot injection
    if correction and USE_CORRECTION_CONTEXT:
        try:
            from services.correction_service import store_correction as _store_correction
            _store_correction(
                run_id=run_id or "",
                user_email=user_email,
                query_preview=query[:300] if query else "",
                correction=correction,
                tool_called=tool_called,
            )
        except Exception as e:
            logger.warning(f"Phase C correction embedding failed: {e}")


def _replace_feedback_block_with_confirmation(client, body: dict, signal: str) -> None:
    """
    Replace the feedback actions block with a one-line confirmation so users
    cannot double-submit and the message looks clean after voting.
    """
    _CONFIRMATIONS = {
        "POSITIVE": "✅  Got it — marked as correct. Thanks!",
        "NEGATIVE": "❌  Marked as incorrect. A correction form has opened — please describe the right answer.",
        "PARTIAL":  "🔧  Got it — marked as partial. Thanks for the signal.",
        "UNCLEAR":  "❓  Got it — marked as unclear.",
    }
    try:
        channel = body["container"]["channel_id"]
        msg_ts  = body["container"]["message_ts"]
        existing_blocks = body.get("message", {}).get("blocks", [])

        # Replace the feedback actions block; keep all other blocks
        new_blocks = [
            b for b in existing_blocks
            if not (b.get("type") == "actions" and
                    b.get("block_id", "").startswith("feedback_"))
        ]
        new_blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn",
                          "text": _CONFIRMATIONS.get(signal, "✅  Feedback recorded.")}],
        })
        client.chat_update(channel=channel, ts=msg_ts, blocks=new_blocks)
    except Exception as e:
        logger.warning(f"Could not replace feedback block: {e}")


def fetch_dm_history(client, channel: str, bot_user_id: str, current_ts: str, limit: int = 10) -> list:
    """
    Fetch recent messages from a DM channel as conversation history.
    Used when thread_ts is absent (DMs have no threads — every message is top-level).
    """
    try:
        result = client.conversations_history(channel=channel, limit=limit + 1)
        # conversations_history returns newest-first; reverse for chronological order
        messages = list(reversed(result.get("messages", [])))
        history = []
        for msg in messages:
            if msg.get("ts") == current_ts:
                continue
            text = msg.get("text", "").strip()
            if not text or text.startswith("⏳"):
                continue
            if msg.get("user") == bot_user_id or msg.get("bot_id"):
                role = "assistant"
            else:
                role = "user"
                text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
            if text:
                history.append({"role": role, "content": text})
        logger.info(f"Fetched {len(history)} DM history messages")
        return history
    except Exception as e:
        logger.warning(f"Could not fetch DM history: {e}")
        return []


def fetch_thread_history(client, channel: str, thread_ts: str, bot_user_id: str, current_ts: str) -> list:
    """
    Fetch prior messages from a Slack thread as alternating user/assistant history.
    Caps at the 20 most recent messages to avoid token explosion.
    """
    try:
        result = client.conversations_replies(channel=channel, ts=thread_ts, limit=20)
        history = []
        for msg in result.get("messages", []):
            if msg["ts"] == current_ts:
                continue
            text = msg.get("text", "").strip()
            if not text or text.startswith("⏳"):
                continue
            if msg.get("user") == bot_user_id or msg.get("bot_id"):
                role = "assistant"
            else:
                role = "user"
                text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
            if text:
                history.append({"role": role, "content": text})
        logger.info(f"Fetched {len(history)} messages of thread history")
        return history
    except Exception as e:
        logger.warning(f"Could not fetch thread history: {e}")
        return []


@traceable(name="slack_compliance_query", run_type="chain", tags=["slack", "compliance"])
def process_with_claude(user_message: str, user_email: str, mentioned_users: Optional[Dict[str, Dict]] = None,
                        thread_history: Optional[list] = None,
                        prior_context: Optional[str] = None) -> str:
    """
    Process user message with Claude and execute any tool calls.
    Uses ChatAnthropic so LangChain's callback system populates LangSmith
    prompt_tokens / completion_tokens / total_cost automatically.

    Args:
        prior_context: Phase B — formatted string of prior conversation summaries
                       injected into the system message (~150 tokens vs ~2K raw history)
    """
    try:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
        from utils.langchain_callback import TokenTrackingCallback
        from utils.tool_router import select_tools_for_intent

        token_cb = TokenTrackingCallback(agent_name="slack_bot")

        # Main model — Opus for reasoning + tool use
        llm = ChatAnthropic(
            model="claude-opus-4-6",
            max_tokens=MAX_TOKENS_SLACK,
            anthropic_api_key=ANTHROPIC_API_KEY,
            callbacks=[token_cb],
        )

        # Haiku for rolling summaries (cheap compression)
        haiku = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            anthropic_api_key=ANTHROPIC_API_KEY,
            callbacks=[token_cb],
        )

        # ── Static system content (cache-eligible — identical across all users/turns) ──
        _STATIC_SYSTEM = (
            "You are Fivetran's compliance agent — you help with access review, role conflict detection, violation tracking, and compliance reporting across critical business systems. "
            "Never refer to yourself as a 'SOD agent' or 'SOD compliance agent' — you are a 'compliance agent'. "
            "Role conflict detection (also known as Segregation of Duties analysis) is one of your capabilities, not your identity. "
            "For access requests: (1) get current roles, (2) check job appropriateness, "
            "(3) call analyze_access_request with ALL roles combined — never analyze a single role in isolation. "
            "Flag Finance roles for non-Finance users and vice versa. "
            "Be concise.\n\n"
            "DATA GROUNDING — always query MCP tools before answering any compliance question. "
            "Never generate SOD rules, control recommendations, violation counts, role lists, or risk scores from general knowledge. "
            "If asked what rules are active, call list_sod_rules. "
            "TOOL SELECTION — follow this rule strictly:\n"
            "  • Question is about ROLES or ROLE COMBINATIONS (e.g. 'which Fivetran roles have conflicts?', 'are there any high-risk roles?', "
            "    'what role pairs present control risk?', 'can roles X and Y be combined safely?', 'roles that have intra-role issues', "
            "    'are there other roles in isolation or combination that introduce conflicts?') — "
            "    ALWAYS call get_role_risk_matrix. NEVER call list_violations for these questions. "
            "    Call it with NO arguments to get the full overview of all 17 Fivetran roles — you do NOT need to know role names first. "
            "    get_role_risk_matrix() returns a complete precomputed matrix of all 153 role pairs and intra-role conflicts. "
            "    Only add role_name if the question is about one specific role. "
            "    list_violations only reflects current user assignments and will miss most roles. "
            "    RESPONSE FORMAT — HARD LIMIT for get_role_risk_matrix: "
            "    (1) One sentence verdict. "
            "    (2) Top 3 bullet points ONLY — worst intra-role role, worst cross-role pair, root cause. "
            "    (3) One direct recommendation sentence. "
            "    MAXIMUM 1,200 characters total. Do NOT list every role or every conflict. Do NOT reproduce permission names or levels. "
            "    If the user wants more detail on a specific role, they can ask a follow-up.\n"
            "GLOBAL RESPONSE LENGTH: Every Slack response must be under 1,800 characters. "
            "If a complete answer requires more, give the most critical 3 points and end with "
            "'Ask me about [specific topic] for the complete breakdown.' "
            "Never write a response that would be truncated mid-sentence.\n\n"
            "  • Question is about a SPECIFIC PERSON's violations or 'who currently has violations' — call get_user_violations or list_violations(roles_only=False).\n"
            "  • Question is about violation COUNTS or STATS — call get_violation_stats.\n"
            "  • Never substitute list_violations for get_role_risk_matrix for role-risk questions.\n"
            "If asked about violation statistics or counts only, call get_violation_stats. "
            "If asked what controls are in place, call list_sod_rules then identify gaps. "
            "To get users in a department, call list_all_users(system_name='netsuite', filter_by_department='Finance') — the parameter is filter_by_department, NOT department. "
            "Every compliance answer must cite a tool result, not training data.\n\n"
            "LANGUAGE — people who hold conflicting roles are not at fault; the access pattern is the problem. "
            "Never use the word 'violator'. Refer to people as 'affected users' or 'users with this access pattern'. "
            "Never use the word 'dangerous'. Use 'high-risk', 'elevated risk', or 'presents material control risk' instead. "
            "Keep the focus on the role combination, not the individual.\n\n"
            "VOICE — communicate as a senior McKinsey partner advising a CFO or Chief Compliance Officer. "
            "This means: lead with the business or control implication, not the technical finding. "
            "Frame issues in terms of organisational risk exposure, control gaps, and remediation priority — not IT permissions. "
            "Be direct and confident. State conclusions first, evidence second. "
            "Use precise, executive-level language: 'material control weakness', 'structural remediation', 'risk-ranked', 'immediate remediation warranted'. "
            "Avoid hedging phrases like 'it seems', 'you might want to', 'perhaps'. "
            "Where there is a clear recommendation, make it — do not present a menu of options without a preferred path.\n\n"
            "CAPABILITIES QUERY — when someone asks 'what can you do', 'how can you help', 'what are your capabilities', "
            "'what do you support', or any similar question about your role: "
            "ALWAYS call list_systems first before answering. "
            "After seeing the result, respond ONLY using this template:\n"
            "  'Hey there — I'm Fivetran's compliance agent. I can help with a few specific tasks across your critical systems.\n"
            "  Based on active connections, I currently support: [list only the system names that appear with ✅ (connected) in the list_systems result].\n"
            "  Then list these capabilities — adjust wording based on how many systems are active:\n"
            "    • Access requests — I check whether a proposed role assignment creates SOD conflicts before it is granted.\n"
            "    • User violations — I pull SOD violations for any person, show conflicting roles, and explain the control risk.\n"
            "    • Role analysis — I assess whether roles are safe in isolation or in combination, and flag maker-checker violations.\n"
            "    • Compliance reporting — I give you aggregate violation stats and help prioritise remediation. "
            "      If multiple systems are connected, I report cross-system: e.g. a user with admin rights in NetSuite and Okta simultaneously. "
            "      If only one system is connected, say: As of now this covers [system name] only — additional systems will be included automatically once connected.'\n"
            "NEVER use the phrase 'SOD compliance agent' or 'SOD agent' — always say 'compliance agent' or 'Fivetran's compliance agent'. "
            "NEVER hardcode system names (NetSuite, Okta, Salesforce, etc.) in this response — always derive them from what list_systems returns. "
            "If a system shows ❌ or is missing, do not mention it. "
            "If new integrations are added later, they will automatically appear. "
            "MAXIMUM 800 characters for the entire capabilities response. Keep each bullet to one short sentence.\n\n"
            "FORMATTING — write like a senior adviser sending a concise Slack message, not a dashboard report:\n"
            "• Be concise. Lead with the answer, then supporting detail.\n"
            "• Use flowing prose where possible. Avoid turning every answer into a bullet list.\n"
            "• Use *bold* only for the single most important fact (e.g. a verdict or a name).\n"
            "• Bullet lists are fine for genuinely enumerable items (roles, violations, steps) — keep them short.\n"
            "• Use Slack mrkdwn syntax: *bold*, _italic_, `code`, ```code block```\n"
            "• DO NOT use ### or ## headings.\n"
            "• DO NOT use Markdown tables (| col | col |) — use short bullet lists instead.\n"
            "• DO NOT use **double asterisks** — Slack ignores them.\n"
            "• Do not use emojis. Write in plain professional text. The only exception is ⚠️ when flagging a critical SOD violation — use it once, at the start of that specific sentence."
        )

        # ── Dynamic context (not cached — contains per-user data) ──
        dynamic_parts = [f"Current user: {user_email}"]
        if mentioned_users:
            dynamic_parts.append("Mentioned users:")
            for _uid, info in mentioned_users.items():
                dynamic_parts.append(f"  @{info['name']}: {info['email']}")
            dynamic_parts.append(
                "Use these emails with get_user_violations / analyze_access_request automatically."
            )
        dynamic_context = "\n".join(dynamic_parts)

        # Phase B — inject prior conversation summaries into system message
        if prior_context:
            dynamic_context += f"\n\n{prior_context}"
            try:
                run = get_current_run_tree()
                if run:
                    run.metadata["context_summaries_injected"] = prior_context.count("\n- ")
            except Exception:
                pass

        # Phase C — inject semantically similar past corrections as few-shot context
        if USE_CORRECTION_CONTEXT:
            try:
                from services.correction_service import (
                    find_similar_corrections as _find_corrections,
                    format_corrections_for_context as _fmt_corrections,
                )
                past_corrections = _find_corrections(user_message)
                if past_corrections:
                    correction_block = _fmt_corrections(past_corrections)
                    dynamic_context += f"\n\n{correction_block}"
                    logger.info(
                        f"Phase C: injected {len(past_corrections)} correction(s) "
                        f"into context for {user_email}"
                    )
                    try:
                        run = get_current_run_tree()
                        if run:
                            run.metadata["corrections_injected"] = len(past_corrections)
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Phase C correction context injection failed: {e}")

        # SystemMessage with cache_control on the static portion
        system_msg = SystemMessage(content=[
            {"type": "text", "text": _STATIC_SYSTEM, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": dynamic_context},
        ])

        # Select only the tools relevant to this message (saves ~8K tokens per request)
        relevant_tools = select_tools_for_intent(user_message, MCP_TOOLS) if MCP_TOOLS else []
        tools = relevant_tools if relevant_tools else MCP_TOOLS
        # Haiku dispatches tools (fast, cheap); Opus synthesizes the final answer (quality)
        haiku_with_tools = haiku.bind_tools(tools)
        llm_with_tools = llm.bind_tools(tools)

        # Build message list: thread history (if any) + current user message
        messages: List = []
        for h in (thread_history or []):
            if h["role"] == "user":
                messages.append(HumanMessage(content=h["content"]))
            elif h["role"] == "assistant":
                messages.append(AIMessage(content=h["content"]))
        messages.append(HumanMessage(content=user_message))

        final_text = ""
        max_turns = 5  # Prevent infinite loops

        for turn in range(max_turns):
            trimmed = _trim_history(messages)
            # Use Haiku for tool-selection turns (no tool results in history yet).
            # Switch to Opus once tool results are present — that's the synthesis turn
            # where reasoning quality matters most.
            has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
            active_model = llm_with_tools if has_tool_results else haiku_with_tools
            response = active_model.invoke([system_msg] + trimmed)

            # No tool calls → extract final text and stop
            if not response.tool_calls:
                if isinstance(response.content, str):
                    final_text = response.content
                else:
                    for block in response.content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            final_text += block.get("text", "")
                break

            # Append AIMessage with tool_calls to history
            messages.append(response)

            # Execute each tool call and append ToolMessage results
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_input = dict(tool_call["args"])
                tool_use_id = tool_call["id"]

                logger.info(f"Turn {turn+1}: Executing tool: {tool_name} with input: {tool_input}")

                # Inject user email where required by specific tools
                if "my_email" in str(MCP_TOOLS) and tool_name in ["initialize_session", "check_my_approval_authority"]:
                    if "my_email" not in tool_input:
                        tool_input["my_email"] = user_email
                if "requester_email" in str(MCP_TOOLS) and tool_name == "request_exception_approval":
                    if "requester_email" not in tool_input:
                        tool_input["requester_email"] = user_email

                raw_result = call_mcp_tool(tool_name, tool_input)
                result = _sanitize_tool_output(tool_name, raw_result)
                result = _compress_tool_result(tool_name, result, haiku)

                messages.append(ToolMessage(content=result, tool_call_id=tool_use_id))

        # Tag root LangSmith run — must happen here (not inside call_mcp_tool)
        # because get_current_run_tree() inside a child @traceable span returns
        # the child span, not the root slack_compliance_query run.
        try:
            root_run = get_current_run_tree()
            if root_run:
                cache_hit = getattr(_cache_hit_tls, "hit", False)
                root_run.metadata["context_cache_hit"] = cache_hit
                if cache_hit:
                    root_run.metadata["cache_tool"] = getattr(_cache_hit_tls, "tool", "")
                _cache_hit_tls.hit = False  # reset for next call
                _cache_hit_tls.run_id = str(root_run.id)  # expose to handle_dm/mention
        except Exception:
            pass

        return final_text.strip() if final_text else "I processed your request, but have nothing to report."

    except Exception as e:
        logger.error(f"Error processing with Claude: {e}")
        return f"❌ Error processing your request: {str(e)}"


@app.event("app_home_opened")
def handle_home_tab(event, client, logger):
    """Publish a static info page to the App Home tab"""
    logger.info(f"app_home_opened fired for user: {event.get('user')}")
    try:
        client.views_publish(
            user_id=event["user"],
        view={
            "type": "home",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🤖  Compliance Agent — Fivetran",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "I perform *compliance reviews across your critical business systems* — ask me anything about access controls, role conflicts, violations, exceptions, or approvals.\n\n*What I can help with:*\n• Access request analysis — does assigning this role create a conflict?\n• User violations — who has conflicting roles and what's the risk?\n• Role risk analysis — which roles or combinations are high-risk?\n• Compliance reporting — aggregate stats, remediation priorities, audit readiness"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*💬  How to use me*\n\nMessage me directly or *@mention* me in any channel. I understand natural language — no commands needed."
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📋  What you can ask*"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "• `Show me all CRITICAL violations`\n• `Can we assign AP-Approver to @austin?`\n• `What roles does sarah.chen@fivetran.com have?`\n• `Run an access review for the Finance team`\n• `Is there an SOD conflict between GL and AP roles?`\n• `What exceptions are currently approved?`"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*⚙️  System*"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Connected systems*\nNetSuite · extensible to any"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Compliance rules*\n18 SOD rules active"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Users monitored*\n1,928 across NetSuite"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Data refresh*\nHourly · full sync at 2 AM"
                        }
                    ]
                },
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Powered by Claude Opus 4.6 + MCP · Cross-system compliance monitoring · Extensible to any critical system · Questions? Ask me directly"
                        }
                    ]
                }
            ]
        }
        )
        logger.info(f"Home tab published successfully for user: {event.get('user')}")
    except Exception as e:
        logger.error(f"Failed to publish home tab: {e}")


@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle @mention of the bot"""
    try:
        # Get user email
        user_id = event["user"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        # Get message text (remove bot mention)
        message_text = event["text"]
        bot_user_id = event.get("bot_user_id") or client.auth_test()["user_id"]
        message_text_clean = message_text.replace(f"<@{bot_user_id}>", "").strip()

        # Extract mentioned users
        mentioned_users = extract_user_mentions(message_text, client)

        # Fetch conversation history so Claude has full context
        thread_ts = event.get("thread_ts")
        thread_history = []
        if channel.startswith("D"):
            # DM channel: no threads — fetch recent channel history
            thread_history = fetch_dm_history(client, channel, bot_user_id, event["ts"])
        elif thread_ts and thread_ts != event["ts"]:
            # Public/private channel thread reply
            thread_history = fetch_thread_history(
                client, channel, thread_ts, bot_user_id, event["ts"]
            )

        logger.info(f"Processing message from {user_email}: {message_text_clean}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Post initial thinking message and animate it while Claude processes
        channel = event["channel"]
        # LangSmith Threads: stable ID groups all turns of a conversation
        _ts = thread_ts or event["ts"]
        thread_id = channel if channel.startswith("D") else f"{channel}-{_ts}"
        thinking_result = client.chat_postMessage(
            channel=channel,
            thread_ts=event["ts"],
            text="⏳ _Analyzing your request..._"
        )
        thinking_ts = thinking_result["ts"]

        stop_event = threading.Event()
        anim_thread = threading.Thread(
            target=_animate_thinking,
            args=(client, channel, thinking_ts, stop_event),
            daemon=True
        )
        anim_thread.start()

        try:
            response = process_with_claude(
                message_text_clean, user_email, mentioned_users, thread_history,
                langsmith_extra={"metadata": {"thread_id": thread_id, "conversation_id": thread_id}}
            )
        finally:
            stop_event.set()
            anim_thread.join(timeout=3)

        # Trim long responses — upload full text as Slack file, show concise summary inline
        display_response = _trim_response_for_slack(response, client, channel)

        # Build blocks: response content + optional feedback buttons
        run_id = getattr(_cache_hit_tls, "run_id", None)
        tool_called = getattr(_cache_hit_tls, "tool", "")
        blocks = format_as_blocks(display_response)
        if USE_ANSWER_FEEDBACK and run_id:
            blocks.append(_feedback_blocks(run_id, user_email, message_text_clean, response, tool_called))

        # Update the thinking message in-place with the real response
        client.chat_update(
            channel=channel,
            ts=thinking_ts,
            text=display_response,
            blocks=blocks,
        )

    except Exception as e:
        logger.error(f"Error handling mention: {e}")
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ Sorry, I encountered an error: {str(e)}"}}],
            thread_ts=event.get("ts")
        )


@app.event("message")
def handle_dm(event, say, client):
    """Handle direct messages to the bot"""
    # Ignore bot messages and threaded messages
    if event.get("bot_id") or event.get("thread_ts"):
        return

    try:
        # Get user email
        user_id = event["user"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        message_text = event["text"]

        # Extract mentioned users
        mentioned_users = extract_user_mentions(message_text, client)

        logger.info(f"Processing DM from {user_email}: {message_text}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Fetch prior DM history so Claude has multi-turn context
        channel = event["channel"]
        bot_user_id = client.auth_test()["user_id"]
        thread_history = fetch_dm_history(client, channel, bot_user_id, event["ts"])

        # Phase B — retrieve prior conversation summaries for this user
        prior_context = _get_prior_summaries(user_email)

        # Post initial thinking message and animate it while Claude processes
        thinking_result = client.chat_postMessage(
            channel=channel,
            text="⏳ _Analyzing your request..._"
        )
        thinking_ts = thinking_result["ts"]

        stop_event = threading.Event()
        anim_thread = threading.Thread(
            target=_animate_thinking,
            args=(client, channel, thinking_ts, stop_event),
            daemon=True
        )
        anim_thread.start()

        thread_id = channel  # DM channel ID is stable per user-pair
        try:
            response = process_with_claude(
                message_text, user_email, mentioned_users, thread_history,
                prior_context=prior_context,
                langsmith_extra={"metadata": {"thread_id": thread_id, "conversation_id": thread_id}}
            )
        finally:
            stop_event.set()
            anim_thread.join(timeout=3)

        # Phase B — write conversation summary asynchronously (non-blocking)
        exchange = (thread_history or []) + [{"role": "user", "content": message_text}]
        threading.Thread(
            target=_write_conversation_summary,
            args=(user_email, channel, exchange, response),
            daemon=True,
        ).start()

        # Trim long responses — upload full text as Slack file, show concise summary inline
        display_response = _trim_response_for_slack(response, client, channel)

        # Build blocks: response content + optional feedback buttons
        run_id = getattr(_cache_hit_tls, "run_id", None)
        tool_called = getattr(_cache_hit_tls, "tool", "")
        blocks = format_as_blocks(display_response)
        if USE_ANSWER_FEEDBACK and run_id:
            blocks.append(_feedback_blocks(run_id, user_email, message_text, response, tool_called))

        # Update the thinking message in-place with the real response
        client.chat_update(
            channel=channel,
            ts=thinking_ts,
            text=display_response,
            blocks=blocks,
        )

    except Exception as e:
        logger.error(f"Error handling DM: {e}")
        say(
            text=f"❌ Sorry, I encountered an error: {str(e)}",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ Sorry, I encountered an error: {str(e)}"}}]
        )


@app.action(re.compile("^feedback_(positive|negative)$"))
def handle_feedback(ack, body, client):
    """
    Handle 👍 / 👎 button clicks appended to every bot response.

    👍 (POSITIVE): saves immediately + replaces buttons with confirmation.
    👎 (NEGATIVE): saves the signal immediately (so it's recorded even if the
        user skips the modal), then opens a correction modal asking "What went
        wrong?" — trigger_id is only valid for 3s so views_open is called
        synchronously before any async work.
    """
    ack()
    try:
        raw_value = body["actions"][0]["value"]     # "SIGNAL|run_id|email|query|answer|tool"
        parts = raw_value.split("|", 5)
        if len(parts) < 6:
            parts += [""] * (6 - len(parts))
        signal, run_id, user_email, query, answer, tool_called = parts

        channel  = body["container"]["channel_id"]
        msg_ts   = body["container"]["message_ts"]

        # Always persist the signal immediately (correction added later if modal submitted)
        threading.Thread(
            target=_save_feedback,
            args=(signal, run_id, user_email, channel, msg_ts, query, answer, tool_called),
            daemon=True,
        ).start()

        if signal == "NEGATIVE":
            # Open correction modal — private_metadata carries all context needed
            # by the view submission handler (channel + msg_ts to update the message)
            private_metadata = "|".join([
                raw_value,          # "NEGATIVE|run_id|email|query|answer|tool"
                channel,
                msg_ts,
            ])
            try:
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        "callback_id": "feedback_correction_modal",
                        "private_metadata": private_metadata,
                        "title": {"type": "plain_text", "text": "What went wrong?"},
                        "submit": {"type": "plain_text", "text": "Submit"},
                        "close":  {"type": "plain_text", "text": "Skip"},
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": (
                                        f"*Your question:* _{query[:120]}_\n\n"
                                        "Help improve future answers by describing "
                                        "what the correct response should have been."
                                    ),
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "correction_block",
                                "label": {"type": "plain_text", "text": "What was the correct answer?"},
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "correction_input",
                                    "multiline": True,
                                    "placeholder": {
                                        "type": "plain_text",
                                        "text": "Describe what the correct answer should have been...",
                                    },
                                },
                            },
                        ],
                    },
                )
            except Exception as e:
                logger.warning(f"Could not open correction modal: {e}")

        _replace_feedback_block_with_confirmation(client, body, signal)

    except Exception as e:
        logger.error(f"Feedback action handler error: {e}")


@app.view("feedback_correction_modal")
def handle_correction_modal(ack, body, view):
    """
    Handle submission of the Phase B correction modal.

    Recovers the original button payload from private_metadata, extracts the
    correction text, and calls _save_feedback with correction= so the DB row
    is updated and LangSmith receives a human_correction entry.
    """
    ack()
    try:
        correction = (
            view["state"]["values"]
            .get("correction_block", {})
            .get("correction_input", {})
            .get("value") or ""
        ).strip()

        if not correction:
            return  # User submitted empty — nothing to record

        # private_metadata = "SIGNAL|run_id|email|query|answer|tool|channel|msg_ts"
        metadata = view.get("private_metadata", "")
        parts = metadata.split("|", 7)
        if len(parts) < 8:
            parts += [""] * (8 - len(parts))
        signal, run_id, user_email, query, answer, tool_called, channel, msg_ts = parts

        threading.Thread(
            target=_save_feedback,
            args=(signal, run_id, user_email, channel, msg_ts, query, answer, tool_called),
            kwargs={"correction": correction},
            daemon=True,
        ).start()

        logger.info(f"Correction submitted by {user_email} for run={run_id}: {correction[:60]}")

    except Exception as e:
        logger.error(f"Correction modal handler error: {e}")


@app.command("/compliance")
def handle_compliance_command(ack, command, say, client):
    """Handle /compliance slash command"""
    ack()

    try:
        # Get user email
        user_id = command["user_id"]
        user_info = client.users_info(user=user_id)
        user_email = user_info["user"]["profile"].get("email", "unknown@fivetran.com")

        command_text = command.get("text", "").strip()

        if not command_text:
            help_text = (
                "*Compliance Agent Commands:*\n"
                "• `/compliance who am i` — Initialize session and check your permissions\n"
                "• `/compliance my authority` — Check your approval authority\n"
                "• `/compliance violations summary` — Get violations summary\n"
                "• `/compliance violations critical` — Get critical violations\n"
                "• `/compliance active exceptions` — List active exceptions\n"
                "• `/compliance help` — Show this help message\n\n"
                "You can also @mention me with natural language requests!"
            )
            say(text=help_text, blocks=format_as_blocks(help_text))
            return

        # Extract mentioned users
        mentioned_users = extract_user_mentions(command_text, client)

        logger.info(f"Processing command from {user_email}: {command_text}")
        if mentioned_users:
            logger.info(f"Mentioned users: {list(mentioned_users.values())}")

        # Process with Claude
        thread_id = f"{command.get('channel_id', 'cmd')}-slash"
        response = process_with_claude(
            command_text, user_email, mentioned_users,
            langsmith_extra={"metadata": {"thread_id": thread_id, "conversation_id": thread_id}}
        )

        # Send response using Block Kit for proper Slack rendering
        say(text=response, blocks=format_as_blocks(response))

    except Exception as e:
        logger.error(f"Error handling command: {e}")
        say(text=f"❌ Sorry, I encountered an error: {str(e)}")


def main():
    """Start the Socket Mode handler"""
    # Validate environment variables
    required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please create a .env file with:")
        logger.error("SLACK_BOT_TOKEN=xoxb-your-bot-token")
        logger.error("SLACK_APP_TOKEN=xapp-your-app-token")
        logger.error("ANTHROPIC_API_KEY=sk-ant-your-key")
        logger.error("MCP_SERVER_URL=http://localhost:8080 (optional)")
        sys.exit(1)

    logger.info("Starting Compliance Agent Slack Bot...")
    logger.info(f"MCP Server: {MCP_SERVER_URL}")

    # Fetch available tools from MCP server
    global MCP_TOOLS
    MCP_TOOLS = fetch_mcp_tools()

    if not MCP_TOOLS:
        logger.error("Failed to fetch tools from MCP server. Bot may not function correctly.")
        logger.error("Please ensure the MCP server is running at: " + MCP_SERVER_URL)
        sys.exit(1)

    logger.info("Socket Mode: Enabled")
    logger.info("Listening for messages...")

    # Start Socket Mode handler
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()


if __name__ == "__main__":
    main()
