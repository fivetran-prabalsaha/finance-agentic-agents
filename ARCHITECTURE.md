# System Architecture — Managed Agent Slack Events Server

## Overview

A FastAPI server that bridges Slack Events API with Anthropic Managed Agent sessions.
Inbound Slack messages trigger background jobs that create or resume sessions, poll
for completion, and post results back to Slack. A `Trace` object is created per job
and carried through every function to produce correlated, timed log lines.

---

## Components

| Component | Role |
|-----------|------|
| `slack_events()` | FastAPI route — verifies signature, classifies trigger, enqueues background task |
| `_process_trigger()` | Background task entry point — creates `Trace`, dispatches to handler |
| `_handle_weekly_update()` | Creates session, sends message, drives poll loop |
| `_handle_approve()` | Resumes a paused session, drives poll loop |
| `_poll_until_idle()` | Polls `sessions.events.list` until `session.status_idle` |
| `_post_slack_message()` | Async HTTP post to `chat.postMessage` via shared `httpx.AsyncClient` |
| `Trace` | Dataclass — carries `user_id`, `trigger`, `session_id`, `perf_counter` start |
| `Settings` | Pydantic-settings — validates all env config once at startup |
| `app.state.anthropic` | Singleton `anthropic.Anthropic` client (created in `lifespan`) |
| `app.state.http` | Shared `httpx.AsyncClient` for Slack HTTP (created in `lifespan`) |
| `active_sessions` | `dict[user_id → session_id]`, protected by `asyncio.Lock` |

---

## Component Diagram

```mermaid
graph TD
    subgraph external [External Systems]
        SL[Slack Workspace]
        AN[Anthropic API\nbeta.sessions.*]
    end

    subgraph server [FastAPI Server :8010]
        R[POST /slack/events]
        H[GET /health]
        D[GET /debug/sessions/user_id]
    end

    subgraph singletons [app.state — created once at lifespan]
        AC[anthropic.Anthropic]
        HC[httpx.AsyncClient]
    end

    subgraph state [In-Memory State]
        AS[active_sessions\nuser_id → session_id]
        SS[session_status\nuser_id → debug fields]
        LK[asyncio.Lock]
    end

    subgraph bg [Background Worker]
        PT[_process_trigger\nTrace created here]
        WU[_handle_weekly_update]
        AP[_handle_approve]
        PL[_poll_until_idle]
        PS[_post_slack_message]
    end

    SL -->|POST event| R
    R -->|enqueue| PT
    PT --> WU
    PT --> AP
    WU --> PL
    AP --> PL
    WU --> PS
    AP --> PS
    PS -->|chat.postMessage| SL
    WU -->|create + send| AC
    AP -->|send| AC
    PL -->|list events| AC
    AC --> AN
    PS --> HC
    HC --> SL
    PT <-->|read/write + Lock| AS
    PT <-->|read/write + Lock| SS
    LK -. guards .-> AS
    LK -. guards .-> SS
```

---

## Trace Instrumentation — Function Boundaries

Every `trace.log/warn/error()` call emits:
```
stage=<label>  user=<id>  trigger=<name>  session=<id>  elapsed_ms=<n>  [extra fields]
```

The diagram below shows exactly where `Trace` is called at each function boundary.
`▶` = entry point of hand-off, `◀` = return / completion. `⚠` = warn, `✖` = error.

```mermaid
sequenceDiagram
    participant SL as Slack
    participant R  as slack_events()
    participant PT as _process_trigger()
    participant WU as _handle_weekly_update()
    participant AP as _handle_approve()
    participant PL as _poll_until_idle()
    participant PS as _post_slack_message()
    participant AN as Anthropic API

    SL ->> R: POST /slack/events

    Note over R: logger event.received
    Note over R: logger event.sig_ok
    Note over R: logger event.queuing
    R -->> PT: background_tasks.add_task()
    Note over R: logger event.queued

    Note over PT: ▶ trace.log trigger.started
    PT ->> WU: weekly_update trigger

    rect rgb(220, 240, 255)
        Note over WU: ▶ trace.log session.creating
        WU ->> AN: sessions.create()
        AN -->> WU: session_id
        Note over WU: ◀ trace.log session.created

        Note over WU: ▶ trace.log message.sending
        WU ->> AN: sessions.events.send()
        AN -->> WU: ack
        Note over WU: ◀ trace.log message.sent

        Note over WU: trace.log state.recorded

        WU ->> PS: _post_slack_message()
        rect rgb(255, 240, 220)
            Note over PS: ▶ trace.log slack.posting
            PS ->> SL: chat.postMessage
            SL -->> PS: ok
            Note over PS: ◀ trace.log slack.posted
        end

        Note over WU: ▶ trace.log poll.entering
        WU ->> PL: _poll_until_idle()

        rect rgb(220, 255, 220)
            loop until session.status_idle
                Note over PL: ▶ trace.log poll.fetch
                PL ->> AN: sessions.events.list()
                AN -->> PL: events[]
                Note over PL: ◀ trace.log poll.events_received

                alt agent.message
                    Note over PL: trace.log poll.agent_message
                else session.status_idle
                    Note over PL: ◀ trace.log poll.idle
                else session.error
                    Note over PL: ✖ trace.error poll.session_error
                else session.status_terminated
                    Note over PL: ✖ trace.error poll.terminated
                else still running
                    Note over PL: trace.log poll.waiting
                else deadline exceeded
                    Note over PL: ⚠ trace.warn poll.timeout
                end
            end
        end

        PL -->> WU: final_text
        Note over WU: ◀ trace.log poll.complete
        Note over WU: trace.log state.idle
    end

    PT ->> AP: approve trigger

    rect rgb(255, 225, 255)
        Note over AP: ▶ trace.log approval.received
        AP ->> PS: _post_slack_message()
        rect rgb(255, 240, 220)
            Note over PS: ▶ trace.log slack.posting
            PS ->> SL: chat.postMessage
            SL -->> PS: ok
            Note over PS: ◀ trace.log slack.posted
        end

        Note over AP: ▶ trace.log approval.sending
        AP ->> AN: sessions.events.send(approve)
        AN -->> AP: ack
        Note over AP: ◀ trace.log approval.sent

        Note over AP: ▶ trace.log poll.entering
        AP ->> PL: _poll_until_idle()
        Note over PL: (same poll loop as above)
        PL -->> AP: done
        Note over AP: ◀ trace.log poll.complete

        Note over AP: trace.log state.approved

        AP ->> PS: _post_slack_message()
        rect rgb(255, 240, 220)
            Note over PS: ▶ trace.log slack.posting
            PS ->> SL: chat.postMessage
            SL -->> PS: ok
            Note over PS: ◀ trace.log slack.posted
        end
    end

    Note over PT: ◀ trace.log trigger.complete
```

---

## Trace Stage Reference

| Stage | Level | Function | Description |
|-------|-------|----------|-------------|
| `trigger.started` | info | `_process_trigger` | Background job begins |
| `trigger.complete` | info | `_process_trigger` | Job finished cleanly |
| `trigger.timeout` | warn | `_process_trigger` | Deadline exceeded |
| `trigger.failed` | error | `_process_trigger` | Unhandled RuntimeError |
| `session.creating` | info | `_handle_weekly_update` | About to call `sessions.create` |
| `session.created` | info | `_handle_weekly_update` | `session_id` returned |
| `message.sending` | info | `_handle_weekly_update` | About to call `sessions.events.send` |
| `message.sent` | info | `_handle_weekly_update` | Message accepted by Anthropic |
| `state.recorded` | info | `_handle_weekly_update` | `active_sessions` / `session_status` updated |
| `poll.entering` | info | `_handle_weekly_update`, `_handle_approve` | Hand-off to poll loop |
| `poll.complete` | info | `_handle_weekly_update`, `_handle_approve` | Poll loop returned |
| `state.idle` | info | `_handle_weekly_update` | Session marked idle in state |
| `approval.no_active_session` | warn | `_handle_approve` | Approve with no known session |
| `approval.received` | info | `_handle_approve` | Approve trigger accepted |
| `approval.sending` | info | `_handle_approve` | About to send approval message |
| `approval.sent` | info | `_handle_approve` | Approval accepted by Anthropic |
| `state.approved` | info | `_handle_approve` | Session marked approved in state |
| `poll.fetch` | info | `_poll_until_idle` | About to call `sessions.events.list` |
| `poll.events_received` | info | `_poll_until_idle` | Event list returned (with types) |
| `poll.agent_message` | info | `_poll_until_idle` | `agent.message` event observed |
| `poll.idle` | info | `_poll_until_idle` | `session.status_idle` received |
| `poll.waiting` | info | `_poll_until_idle` | Sleeping until next poll |
| `poll.timeout` | warn | `_poll_until_idle` | Deadline exceeded inside loop |
| `poll.session_error` | error | `_poll_until_idle` | `session.error` event received |
| `poll.terminated` | error | `_poll_until_idle` | `session.status_terminated` received |
| `slack.posting` | info | `_post_slack_message` | About to call `chat.postMessage` |
| `slack.posted` | info | `_post_slack_message` | Slack confirmed delivery |
| `slack.skip` | warn | `_post_slack_message` | `SLACK_BOT_TOKEN` not set |
