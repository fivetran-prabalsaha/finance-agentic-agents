# Token Usage & Cost Tracking Guide

## 🎯 Overview

This guide explains how to track Claude API token usage and costs in your compliance system.

**Why Track Tokens?**
- 💰 Monitor and control API costs
- 📊 Understand which agents consume the most resources
- 🔍 Optimize prompt engineering
- 📈 Forecast future costs based on usage patterns
- ⚡ Identify performance bottlenecks

---

## 📦 Components

### 1. Token Tracker (`utils/token_tracker.py`)

Core tracking module that monitors:
- Token usage per API call
- Costs calculated using current Claude pricing
- Per-agent statistics
- Aggregate totals

### 2. Anthropic Wrapper (`utils/anthropic_wrapper.py`)

Transparent wrapper around the Anthropic client that:
- Automatically tracks all API calls
- Attributes usage to specific agents
- Passes through all Claude API features

### 3. Demo Scripts

- `demos/demo_token_tracking.py` - Standalone demonstration
- `demos/demo_end_to_end.py` - Full system with tracking

---

## 🚀 Quick Start

### Basic Usage

```python
from utils.token_tracker import get_global_tracker

# Get the global tracker
tracker = get_global_tracker()

# Your agent code here...
# (tokens are tracked automatically if using the wrapper)

# Print summary
tracker.print_summary()
```

### Using the Anthropic Wrapper

**Before (without tracking):**
```python
from anthropic import Anthropic

client = Anthropic()
response = client.messages.create(
    model="claude-opus-4.6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Analyze this..."}]
)
```

**After (with automatic tracking):**
```python
from utils.anthropic_wrapper import create_tracked_client

client = create_tracked_client(agent_name="analyzer")
response = client.messages.create(
    model="claude-opus-4.6",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Analyze this..."}],
    operation="sod_check"  # Optional: describe the operation
)
# Token usage automatically tracked! ✨
```

### Manual Tracking

If you can't use the wrapper, track manually:

```python
from utils.token_tracker import get_global_tracker

tracker = get_global_tracker()

# After API call, extract usage from response
response = client.messages.create(...)

tracker.track(
    model=response.model,
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
    cache_creation_tokens=response.usage.cache_creation_input_tokens or 0,
    cache_read_tokens=response.usage.cache_read_input_tokens or 0,
    agent_name="analyzer",
    operation="sod_check"
)
```

---

## 📊 Understanding the Output

### Summary Report

```
================================================================================
  TOKEN USAGE & COST SUMMARY
================================================================================

📊 Overall Statistics:
   Total API Calls:       5
   Total Tokens Used:     57,500
   Total Cost:            $0.8670
   Avg Tokens/Call:       11500
   Avg Cost/Call:         $0.1734

🤖 Per-Agent Breakdown:
   Agent                     Calls    Tokens       Cost
   ------------------------- -------- ------------ ------------
   analyzer                  2        42,000       $0.7995
   risk_assessor             1        9,200        $0.0420
   orchestrator              1        3,800        $0.0210
   knowledge_base            1        2,500        $0.0045

================================================================================
```

### What Each Metric Means

| Metric | Description |
|--------|-------------|
| **Total API Calls** | Number of times agents called Claude API |
| **Total Tokens Used** | Sum of all input + output + cache tokens |
| **Total Cost** | Calculated cost in USD based on Claude pricing |
| **Avg Tokens/Call** | Average token usage per API call |
| **Avg Cost/Call** | Average cost per API call |

### Per-Agent Breakdown

Shows which agents are consuming the most resources:
- **Calls:** Number of API requests
- **Tokens:** Total tokens used (input + output + cache)
- **Cost:** Total cost for this agent

---

## 💰 Claude API Pricing

### Current Pricing (2026-02)

| Model | Input | Output | Cache Write | Cache Read |
|-------|-------|--------|-------------|------------|
| **Claude Opus 4.6** | $15/M | $75/M | $18.75/M | $1.50/M |
| **Claude Sonnet 4.5** | $3/M | $15/M | $3.75/M | $0.30/M |
| **Claude Haiku 4.5** | $1/M | $5/M | $1.25/M | $0.10/M |

*M = Million tokens*

### Cost Calculation

```python
cost = (
    (input_tokens * $input_price) +
    (output_tokens * $output_price) +
    (cache_write_tokens * $cache_write_price) +
    (cache_read_tokens * $cache_read_price)
)
```

**Example:**
```
Opus 4.6 with:
- 15,000 input tokens
- 2,500 output tokens

Cost = (15,000 * $0.000015) + (2,500 * $0.000075)
     = $0.225 + $0.1875
     = $0.4125
```

---

## 📈 Cost Projections

### Demo Run Example

Based on a single compliance scan:

```python
Demo Cost: $0.8670

# Scaling estimates
10 users/day:   $8.67/day   = $260/month   = $3,165/year
100 users/day:  $86.70/day  = $2,601/month = $31,646/year
500 users/day:  $433.50/day = $13,005/month = $158,228/year
```

### Real-World Estimates

**Typical Enterprise Scenario:**
- 500 active users
- Daily compliance scan
- 18 SOD rules checked per user
- 3 agents per scan (analyzer, risk assessor, orchestrator)

**Monthly Cost:** ~$2,600 - $3,000

**Cost Breakdown:**
- Analysis Agent: 70% ($1,820)
- Risk Assessor: 20% ($520)
- Orchestrator: 10% ($260)

---

## 🎯 Cost Optimization Strategies

### 1. Use Prompt Caching (90% cost reduction!)

**Without Caching:**
```python
# Every call sends full SOD rules (15,000 tokens)
Cost per call = $0.225 (input) + $0.1875 (output) = $0.4125
```

**With Caching:**
```python
# First call: Write to cache
Cache write: 15,000 tokens * $0.00001875 = $0.28125
Input: 1,000 tokens * $0.000015 = $0.015
Output: 2,500 tokens * $0.000075 = $0.1875
First call cost = $0.48375

# Subsequent calls: Read from cache
Cache read: 15,000 tokens * $0.0000015 = $0.0225 (90% savings!)
Input: 1,000 tokens * $0.000015 = $0.015
Output: 2,500 tokens * $0.000075 = $0.1875
Subsequent cost = $0.225 (53% savings overall)
```

**Implementation:**
```python
response = client.messages.create(
    model="claude-opus-4.6",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": sod_rules_text,
                "cache_control": {"type": "ephemeral"}  # Cache this!
            },
            {
                "type": "text",
                "text": f"Analyze user: {user_data}"
            }
        ]
    }]
)
```

### 2. Choose the Right Model

**Use Opus (most expensive) for:**
- Complex SOD analysis requiring deep reasoning
- New violation types requiring nuanced understanding
- Critical financial compliance decisions

**Use Sonnet (balanced) for:**
- Standard SOD rule checks ← **Recommended for most use cases**
- Risk assessment
- Report generation
- Most compliance operations

**Use Haiku (cheapest) for:**
- Simple semantic search
- Knowledge base lookups
- Basic classification tasks
- High-volume, simple operations

**Example Savings:**
```
100 users/day with standard SOD checks:

Opus:   $86.70/day  = $2,601/month
Sonnet: $17.34/day  = $520/month    ← 80% savings!
Haiku:  $5.78/day   = $173/month    ← 93% savings!
```

### 3. Optimize Prompts

**Bad (wasteful):**
```python
prompt = f"""
Here are all the SOD rules: {all_18_rules_full_text}
And here is the user data: {user_full_profile}
And here are all violations ever: {all_violations}
Please analyze this user...
"""
# 20,000+ tokens!
```

**Good (efficient):**
```python
# Use caching + concise context
prompt = f"""
[CACHED: SOD rules definitions]

User: {user_id}
Roles: {role_names_only}
Check violations: {relevant_rules_only}
"""
# 3,000 tokens!
```

### 4. Batch Operations

**Bad (individual calls):**
```python
for user in users:
    result = analyzer.analyze_user(user)
    # 100 calls * $0.42 = $42
```

**Good (batch processing):**
```python
# Analyze 10 users per call
for batch in chunk(users, 10):
    result = analyzer.analyze_batch(batch)
    # 10 calls * $0.85 = $8.50 (80% savings!)
```

### 5. Implement Caching at Application Level

```python
import redis

cache = redis.Redis()

def analyze_user_with_cache(user_id):
    # Check cache first
    cached = cache.get(f"sod_analysis:{user_id}")
    if cached:
        return json.loads(cached)

    # Only call API if not cached
    result = analyzer.analyze_user(user_id)

    # Cache for 24 hours
    cache.setex(
        f"sod_analysis:{user_id}",
        86400,  # 24 hours
        json.dumps(result)
    )

    return result
```

---

## 📊 Monitoring & Alerts

### Set Up Cost Monitoring

```python
from utils.token_tracker import get_global_tracker

tracker = get_global_tracker()

# After operations
summary = tracker.get_summary()

# Alert if costs exceed threshold
if summary['total_cost'] > 10.0:  # $10 threshold
    send_alert(f"High API costs: ${summary['total_cost']:.2f}")

# Alert if tokens/call are high
if summary['average_tokens_per_call'] > 20000:
    send_alert("Token usage per call is high - optimize prompts")
```

### Daily Cost Reports

```python
from utils.token_tracker import get_global_tracker
import schedule

def daily_report():
    tracker = get_global_tracker()
    summary = tracker.get_summary()

    report = f"""
    Daily Compliance Scan Report
    ----------------------------
    Date: {datetime.now().date()}
    Users Analyzed: {users_count}
    API Calls: {summary['total_calls']}
    Tokens Used: {summary['total_tokens']:,}
    Cost: ${summary['total_cost']:.2f}

    Top Consuming Agents:
    {format_agent_stats(summary['agents'])}
    """

    send_email(to='ops@company.com', subject='Daily Cost Report', body=report)

# Schedule daily
schedule.every().day.at("09:00").do(daily_report)
```

---

## 🔍 Troubleshooting

### Issue: No token usage tracked

**Check:**
1. Using the wrapper? `from utils.anthropic_wrapper import create_tracked_client`
2. Calling `track()` manually if not using wrapper?
3. API responses include usage data?

**Debug:**
```python
from utils.token_tracker import get_global_tracker

tracker = get_global_tracker()
print(f"Total calls tracked: {tracker.total_calls}")
print(f"Usages: {len(tracker.usages)}")

# Check individual usage
for usage in tracker.usages:
    print(f"{usage.agent_name}: {usage.total_tokens} tokens, ${usage.cost:.4f}")
```

### Issue: Costs seem wrong

**Verify model name:**
```python
# Wrong model name uses fallback pricing
tracker.track(model="claude-3-opus", ...)  # ❌ Old model name

# Use current model names
tracker.track(model="claude-opus-4.6", ...)  # ✅
tracker.track(model="claude-sonnet-4.5", ...)  # ✅
tracker.track(model="claude-haiku-4.5", ...)  # ✅
```

**Check pricing:**
```python
from utils.token_tracker import PRICING

print(PRICING['claude-opus-4.6'])
# Update if Anthropic changes pricing
```

---

## 📚 API Reference

### TokenTracker

```python
class TokenTracker:
    def track(
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None
    ) -> TokenUsage

    def track_from_response(
        response: Dict,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None
    ) -> Optional[TokenUsage]

    @property
    def total_tokens(self) -> int
    @property
    def total_cost(self) -> float
    @property
    def total_calls(self) -> int

    def get_agent_stats(self, agent_name: str) -> Optional[Dict]
    def get_all_agent_stats(self) -> Dict[str, Dict]
    def get_summary(self) -> Dict
    def print_summary(self)
    def reset(self)
```

### AnthropicClientWrapper

```python
class AnthropicClientWrapper:
    def __init__(
        agent_name: Optional[str] = None,
        api_key: Optional[str] = None,
        track_tokens: bool = True
    )

    def messages.create(
        model: str,
        max_tokens: int,
        messages: list,
        operation: Optional[str] = None,
        **kwargs
    ) -> Message
```

---

## 🎓 Best Practices

### 1. Always Name Your Agents

```python
# Good
client = create_tracked_client(agent_name="analyzer")

# Bad
client = create_tracked_client()  # Shows as "unknown"
```

### 2. Describe Operations

```python
# Good
response = client.messages.create(
    ...,
    operation="sod_rule_check"  # Know what each call does
)

# OK
response = client.messages.create(...)  # Generic "message_create"
```

### 3. Check Costs Regularly

```python
# At key points in your workflow
tracker = get_global_tracker()
summary = tracker.get_summary()

logger.info(f"Cost so far: ${summary['total_cost']:.4f}")

# Reset between runs
tracker.reset()
```

### 4. Use Cost Budgets

```python
MAX_COST_PER_RUN = 5.0  # $5 budget

tracker = get_global_tracker()

# Before expensive operation
if tracker.total_cost > MAX_COST_PER_RUN:
    raise CostLimitExceeded(
        f"Budget exceeded: ${tracker.total_cost:.2f} > ${MAX_COST_PER_RUN}"
    )
```

---

## 🚀 Next Steps

1. **Run the demo:**
   ```bash
   python3 demos/demo_token_tracking.py
   ```

2. **Integrate into your agents:**
   - Replace `Anthropic()` with `create_tracked_client(agent_name="...")`
   - Add `tracker.print_summary()` at end of workflows

3. **Monitor and optimize:**
   - Check which agents cost the most
   - Implement prompt caching
   - Use appropriate models for each task

4. **Set up alerts:**
   - Daily cost reports
   - Threshold alerts
   - Usage trend monitoring

---

## 📊 Example Output

Running the end-to-end demo with token tracking:

```bash
python3 demos/demo_end_to_end.py
```

**Output includes:**
```
================================================================================
  TOKEN USAGE & COST SUMMARY
================================================================================

📊 Overall Statistics:
   Total API Calls:       12
   Total Tokens Used:     145,000
   Total Cost:            $2.1750
   Avg Tokens/Call:       12083
   Avg Cost/Call:         $0.1813

🤖 Per-Agent Breakdown:
   Agent                     Calls    Tokens       Cost
   ------------------------- -------- ------------ ------------
   analyzer                  5        95,000       $1.4250
   risk_assessor             3        28,000       $0.4200
   orchestrator              2        15,000       $0.2250
   knowledge_base            2        7,000        $0.1050

💰 Cost Analysis:
   Cost per User Analyzed:     $0.0725
   Cost per Violation Found:   $0.2175
   Estimated Monthly Cost*:    $65.25
   Estimated Annual Cost*:     $793.88

   * Based on daily scan with similar data volume
```

---

**Questions or issues?** Check the troubleshooting section or create an issue in the repository.
