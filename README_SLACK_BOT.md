# Slack Bot Integration

Quick reference for the Compliance Agent Slack bot.

## 🚀 Quick Start (5 minutes)

### For Local Development

```bash
# 1. Install dependencies
pip install -r requirements-slack.txt

# 2. Test your configuration
python test_slack_bot.py

# 3. Follow setup guide
cat SLACK_BOT_SETUP.md

# 4. Start the bot
python slack_bot_local.py
```

## 📁 Files

| File | Purpose |
|------|---------|
| `slack_bot_local.py` | Socket Mode bot for local development |
| `SLACK_BOT_SETUP.md` | Complete 5-minute setup guide |
| `test_slack_bot.py` | Configuration test script |
| `requirements-slack.txt` | Additional Python dependencies |
| `.env.example` | Example environment variables |

## 🔧 Configuration

Add to your `.env` file:

```bash
# Slack Bot
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Anthropic API (for Claude integration)
ANTHROPIC_API_KEY=sk-ant-your-key

# MCP Server
MCP_SERVER_URL=http://localhost:8080
```

## 📖 Documentation

- **Local Setup**: See `SLACK_BOT_SETUP.md`
- **Production Deployment**: See `docs/SLACK_INTEGRATION.md`
- **AWS Deployment**: See `docs/AWS_PRODUCTION_DEPLOYMENT.md`

## ✅ Pre-Flight Checklist

Before starting the bot:

- [ ] MCP server is running (port 8080)
- [ ] Slack app created with Socket Mode enabled
- [ ] SLACK_BOT_TOKEN and SLACK_APP_TOKEN in `.env`
- [ ] ANTHROPIC_API_KEY in `.env`
- [ ] Dependencies installed: `pip install -r requirements-slack.txt`
- [ ] Configuration tested: `python test_slack_bot.py`

## 🎯 Usage Examples

### In Slack

```
@Compliance Agent who am i
@Compliance Agent show me active exceptions
@Compliance Agent what violations are critical?
@Compliance Agent find exceptions for john@fivetran.com

/compliance who am i
/compliance violations summary
/compliance my authority
```

## 🏗️ Architecture

### Local Development (Socket Mode)

```
┌─────────────┐
│ Slack User  │
└──────┬──────┘
       │ WebSocket
       ▼
┌──────────────────────┐
│ slack_bot_local.py   │
│ (Your Desktop)       │
└──────┬───────────────┘
       │ HTTP
       ▼
┌──────────────────────┐
│ Claude API           │
│ - Understands intent │
│ - Decides tools      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ MCP Server           │
│ localhost:8080       │
└──────────────────────┘
```

### Production (AWS Lambda)

See `docs/SLACK_INTEGRATION.md` for AWS deployment.

## 💰 Cost

### Local Development
- **Slack:** $0 (Socket Mode is free)
- **Anthropic API:** ~$0.015 per request
- **Total:** ~$9-45/month (depending on usage)

### Production
See `docs/AWS_PRODUCTION_DEPLOYMENT.md` for AWS cost breakdown.

## 🔍 Troubleshooting

### Bot doesn't respond

```bash
# Check MCP server
curl http://localhost:8080/health

# Check Slack tokens
python test_slack_bot.py

# Check logs
# Terminal running slack_bot_local.py will show errors
```

### Configuration issues

```bash
# Run test script
python test_slack_bot.py

# This will check:
# - MCP server health
# - MCP tool calls
# - Anthropic API key
# - Slack tokens
# - Python dependencies
```

### Bot can't see user emails

Make sure you added `users:read.email` scope in Slack App settings.

## 📚 Additional Resources

- **Slack API Docs**: https://api.slack.com/docs
- **Socket Mode Guide**: https://api.slack.com/apis/connections/socket
- **slack-bolt SDK**: https://slack.dev/bolt-python/
- **Anthropic API**: https://docs.anthropic.com

## 🎓 Next Steps

### After Local Testing

1. **Deploy to production**: See `docs/AWS_PRODUCTION_DEPLOYMENT.md`
2. **Add more commands**: Edit `slack_bot_local.py`
3. **Customize responses**: Modify system message in `process_with_claude()`
4. **Add Slack UI elements**: Use Block Kit for interactive messages

### Advanced Features

- **User authentication**: Validate against NetSuite users
- **Approval workflows**: Create Jira tickets from Slack
- **Scheduled reports**: Send daily compliance summaries
- **Interactive buttons**: Approve/reject exceptions in Slack

See `docs/SLACK_INTEGRATION.md` for examples.

---

**Version:** 1.0
**Last Updated:** 2026-02-13
**Maintained by:** Systems Engineering Team
