# Local Slack Bot Setup Guide

This guide will help you set up the Compliance Agent Slack bot running locally on your desktop using Socket Mode.

## ⏱️ Setup Time: ~5 minutes

## Prerequisites

- Python 3.11+
- MCP server running locally (port 8080)
- Slack workspace admin access
- Anthropic API key

## Step 1: Install Python Dependencies (1 minute)

```bash
cd compliance-agent
pip install slack-bolt anthropic requests python-dotenv
```

## Step 2: Create Slack App (2 minutes)

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `Compliance Agent`
4. Choose your workspace
5. Click **"Create App"**

### Enable Socket Mode

1. In your app settings, go to **"Socket Mode"** (left sidebar)
2. Toggle **"Enable Socket Mode"** ON
3. Generate an app-level token:
   - Token Name: `socket-token`
   - Scope: `connections:write`
   - Click **"Generate"**
   - **Copy the token** (starts with `xapp-`) → Save for `.env` file

### Configure Bot Token Scopes

1. Go to **"OAuth & Permissions"** (left sidebar)
2. Scroll to **"Scopes"** → **"Bot Token Scopes"**
3. Add these scopes:
   - `app_mentions:read` - Read messages that mention the bot
   - `channels:history` - Read messages in channels
   - `channels:read` - View basic channel info
   - `chat:write` - Send messages
   - `commands` - Add slash commands
   - `im:history` - Read DMs
   - `im:read` - View DMs
   - `im:write` - Send DMs
   - `users:read` - View user info (for email lookup)
   - `users:read.email` - View user emails

4. Scroll up and click **"Install to Workspace"**
5. Click **"Allow"**
6. **Copy the "Bot User OAuth Token"** (starts with `xoxb-`) → Save for `.env` file

### Enable Event Subscriptions

1. Go to **"Event Subscriptions"** (left sidebar)
2. Toggle **"Enable Events"** ON
3. Under **"Subscribe to bot events"**, add:
   - `app_mention` - When users @mention the bot
   - `message.im` - Direct messages to the bot

4. Click **"Save Changes"**

### Add Slash Command (Optional)

1. Go to **"Slash Commands"** (left sidebar)
2. Click **"Create New Command"**
3. Configure:
   - Command: `/compliance`
   - Request URL: Leave blank (Socket Mode doesn't need this)
   - Short Description: `Interact with Compliance Agent`
   - Usage Hint: `who am i | my authority | violations summary`
4. Click **"Save"**

## Step 3: Configure Environment Variables (1 minute)

Create or update your `.env` file:

```bash
cd compliance-agent
nano .env
```

Add these three new lines:

```bash
# Slack Bot Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-level-token-here

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# MCP Server URL (default: http://localhost:8080)
MCP_SERVER_URL=http://localhost:8080
```

Replace with your actual tokens:
- `SLACK_BOT_TOKEN` - The `xoxb-...` token from Step 2
- `SLACK_APP_TOKEN` - The `xapp-...` token from Step 2
- `ANTHROPIC_API_KEY` - Your Claude API key

## Step 4: Start the Bot (30 seconds)

### Terminal 1: Start MCP Server

```bash
cd compliance-agent
python -m mcp.mcp_server
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Terminal 2: Start Slack Bot

```bash
cd compliance-agent
python slack_bot_local.py
```

You should see:
```
2026-02-13 10:30:00 - __main__ - INFO - Starting Compliance Agent Slack Bot...
2026-02-13 10:30:00 - __main__ - INFO - MCP Server: http://localhost:8080
2026-02-13 10:30:00 - __main__ - INFO - Socket Mode: Enabled
2026-02-13 10:30:00 - __main__ - INFO - Listening for messages...
```

## Step 5: Test the Bot (30 seconds)

### In Slack:

1. **Invite the bot to a channel:**
   ```
   /invite @Compliance Agent
   ```

2. **Test with @mention:**
   ```
   @Compliance Agent who am i
   ```

   You should get a response showing your email and approval authority.

3. **Test with DM:**
   - Send a direct message to the bot
   ```
   Show me active exceptions
   ```

4. **Test slash command:**
   ```
   /compliance violations summary
   ```

## Usage Examples

### Natural Language Commands

The bot uses Claude to understand natural language. Try:

```
@Compliance Agent who am i
@Compliance Agent what exceptions are active?
@Compliance Agent show me critical violations
@Compliance Agent what can I approve?
@Compliance Agent find exceptions for john@fivetran.com
@Compliance Agent analyze violation for user 12345
```

### Slash Commands

```bash
/compliance who am i
/compliance my authority
/compliance violations summary
/compliance violations critical
/compliance active exceptions
/compliance help
```

### Direct Messages

You can DM the bot without @mentioning:
```
Show me violations above risk score 80
Find exceptions that need review this month
What are my approval permissions?
```

## Architecture

```
┌─────────────┐
│ Slack User  │
└──────┬──────┘
       │ WebSocket (Socket Mode)
       ▼
┌──────────────────────┐
│ slack_bot_local.py   │
│ - Receives messages  │
│ - Gets user email    │
│ - Calls Claude API   │
└──────┬───────────────┘
       │ HTTP
       ▼
┌──────────────────────┐
│ Claude API           │
│ - Understands intent │
│ - Decides tool calls │
└──────┬───────────────┘
       │ Returns tool to call
       ▼
┌──────────────────────┐
│ slack_bot_local.py   │
│ - Executes tool call │
└──────┬───────────────┘
       │ HTTP POST
       ▼
┌──────────────────────┐
│ MCP Server           │
│ localhost:8080       │
│ - Executes tool      │
│ - Returns result     │
└──────────────────────┘
```

## Troubleshooting

### Bot doesn't respond

1. Check both terminals are running:
   - MCP server on port 8080
   - Slack bot with Socket Mode

2. Check `.env` file has correct tokens

3. Check bot is invited to the channel:
   ```
   /invite @Compliance Agent
   ```

### "Missing required environment variables"

Make sure your `.env` file has:
```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
ANTHROPIC_API_KEY=sk-ant-...
```

### "Error calling MCP tool"

1. Check MCP server is running on port 8080
2. Test manually:
   ```bash
   curl http://localhost:8080/health
   ```

### Bot can't see user email

Make sure you added the `users:read.email` scope in Step 2.

## Cost Estimate

- **Slack:** $0/month (Socket Mode is free)
- **Anthropic API:** ~$0.015 per request (Claude Opus 4.6)
  - 100 requests/day ≈ $45/month
  - 20 requests/day ≈ $9/month

## Benefits of Socket Mode

✅ **No webhooks** - No public URL needed
✅ **No deployment** - Runs on your desktop
✅ **Instant updates** - Just restart the script
✅ **Free** - No AWS/hosting costs
✅ **Secure** - All data stays local
✅ **Development friendly** - See logs in real-time

## Next Steps

### For Production

When you're ready to deploy to production:

1. See `docs/SLACK_INTEGRATION.md` for AWS Lambda deployment
2. See `docs/AWS_PRODUCTION_DEPLOYMENT.md` for full production setup

### For Development

- Edit `slack_bot_local.py` to customize responses
- Add new MCP tools to the `MCP_TOOLS` list
- Restart the bot to pick up changes

## Need Help?

- Slack API docs: https://api.slack.com/docs
- Socket Mode guide: https://api.slack.com/apis/connections/socket
- slack-bolt SDK: https://slack.dev/bolt-python/
