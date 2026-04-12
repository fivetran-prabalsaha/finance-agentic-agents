# AI-Powered SOD Compliance System
**Celigo SysEng | February 2026**

---

## The Problem

SOX compliance requires continuous monitoring of who has access to what — and flagging any single user who can both initiate and approve a financial transaction (Segregation of Duties violation). Today this is manual, slow, and only happens at audit time. By then it's too late.

---

## What We Built

An autonomous AI compliance officer that monitors all 1,928 active NetSuite users 24/7 against 18 SOD rules — detecting violations, assessing risk, and answering access questions in real time.

---

## How It Works

```
NetSuite ERP  →  Data Sync Agent  →  SOD Rule Engine  →  AI Analysis (Claude Opus)
                 (hourly + daily)     (18 rules)          Risk scoring + recommendations
                                              ↓
                                     Slack Bot  ←→  Compliance team
                                     MCP Server ←→  Claude Code
```

**Three layers:**
- **Data**: Syncs user roles and permissions from NetSuite hourly (1,928 users, 99.7% coverage)
- **Analysis**: 18 SOD rules checked against every role combination; AI reasoning on CRITICAL/HIGH violations
- **Interface**: Slack bot for natural language queries; MCP server for programmatic access (35 tools)

---

## Key Capabilities

| Capability | Detail |
|---|---|
| Continuous monitoring | Full sync daily, incremental hourly |
| Access review | "Can we give John the Controller role?" → risk verdict in seconds |
| Violation dashboard | Filter by severity, department, user |
| Exception management | Request, route, and track SOD exceptions with audit trail |
| Compliance reports | Executive summary, audit-ready, department-level |
| Knowledge base | Semantic search across SOX policies and compensating controls |

---

## Current Status

- **1,928 users** monitored across NetSuite
- **18 SOD rules** active (Financial, Security, Compliance categories)
- **35 MCP tools** operational
- **Slack bot** live — multi-turn agentic reasoning, animated UX
- **Token-optimized** — prefix caching, intent-based tool routing, rolling summaries

---

## What's Next

- Jira integration for approval workflow routing
- Okta, Salesforce, Coupa connectors (NetSuite live today)
- Judge agent for CRITICAL violation escalation
- Tiered approval chain (manager → department head → CFO)

---

## Business Value

> One SOD violation missed in a SOX audit can trigger a material weakness finding — restatement risk, increased auditor scrutiny, and remediation costs. This system eliminates that exposure continuously, not just at audit time.
