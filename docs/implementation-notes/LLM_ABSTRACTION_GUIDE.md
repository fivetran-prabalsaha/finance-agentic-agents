

# LLM Abstraction Layer - Complete Guide

**Version**: 1.0.0
**Date**: 2026-02-09
**Status**: Production Ready

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Supported Providers](#supported-providers)
6. [Usage Examples](#usage-examples)
7. [Security & Encryption](#security--encryption)
8. [Migration Guide](#migration-guide)
9. [Advanced Features](#advanced-features)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Overview

The LLM Abstraction Layer provides a **unified, provider-agnostic interface** for interacting with different Large Language Model providers. This allows you to:

✅ **Switch between providers** without changing code
✅ **Encrypt API keys** for security
✅ **Track costs** across all providers
✅ **Fallback** to alternative providers
✅ **Local development** with Ollama/vLLM
✅ **Consistent interface** regardless of provider

### Supported Providers

- **Anthropic** (Claude Opus, Sonnet, Haiku)
- **OpenAI** (GPT-4, GPT-4o, GPT-3.5)
- **Google** (Gemini Pro, Gemini 1.5)
- **Cohere** (Command R, Command R+)
- **Azure OpenAI** (All GPT models)
- **Local Models** (Ollama, vLLM, LM Studio)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               LLM Abstraction Layer                          │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Factory    │───▶│Config Manager│───▶│  Encryption  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌────────────────────────────────────────────────────┐    │
│  │         BaseLLMProvider (Abstract Interface)       │    │
│  └────────────────────────────────────────────────────┘    │
│         │          │         │         │         │          │
└─────────┼──────────┼─────────┼─────────┼─────────┼──────────┘
          │          │         │         │         │
          ▼          ▼         ▼         ▼         ▼
   ┌──────────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌───────┐
   │Anthropic │ │ OpenAI │ │Google│ │ Cohere │ │ Local │
   └──────────┘ └────────┘ └──────┘ └────────┘ └───────┘
```

### Key Components

1. **`BaseLLMProvider`** - Abstract base class defining unified interface
2. **`LLMProviderFactory`** - Creates provider instances
3. **`LLMConfigManager`** - Manages configuration and encryption
4. **Provider Implementations** - Concrete provider classes

---

## Quick Start

### Installation

Install required dependencies:

```bash
# Core dependencies
pip install anthropic openai google-generativeai cohere cryptography pyyaml

# For OpenAI token counting
pip install tiktoken

# For local models (optional)
# Ollama: https://ollama.ai/
```

### Basic Usage

```python
from services.llm import create_llm, LLMMessage

# Create LLM provider
llm = create_llm(
    provider="anthropic",
    model="claude-sonnet-4-5",
    api_key="sk-ant-api03-...",
    temperature=0.0,
    max_tokens=4096
)

# Generate completion
messages = [
    LLMMessage(role="system", content="You are a helpful assistant."),
    LLMMessage(role="user", content="Explain SOD violations in simple terms.")
]

response = llm.generate(messages)

print(response.content)
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.usage['total_tokens']}")
```

### Using Configuration File

```python
from services.llm import get_llm_from_config, LLMMessage

# Load from config file
llm = get_llm_from_config(
    config_path="config/llm_config.yaml",
    provider="anthropic"  # Optional: uses default if not specified
)

# Use the same interface
response = llm.generate(messages)
```

---

## Configuration

### Config File Setup

1. **Copy example config:**

```bash
cp config/llm_config.example.yaml config/llm_config.yaml
```

2. **Edit configuration:**

```yaml
default_provider: anthropic

providers:
  anthropic:
    model: claude-sonnet-4-5-20250929
    api_key_env: ANTHROPIC_API_KEY  # Or use encrypted: api_key + encrypted: true
    temperature: 0.0
    max_tokens: 4096
```

3. **Set environment variables:**

```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key | If using Anthropic |
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI |
| `GOOGLE_API_KEY` | Google API key | If using Google |
| `COHERE_API_KEY` | Cohere API key | If using Cohere |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key | If using Azure |
| `MASTER_ENCRYPTION_KEY` | Fernet encryption key | If encrypting keys |
| `LLM_CONFIG_PATH` | Path to config file | Optional |

---

## Supported Providers

### Anthropic Claude

```python
llm = create_llm(
    provider="anthropic",
    model="claude-sonnet-4-5-20250929",  # or claude-opus-4-6, claude-haiku-4-5
    api_key="sk-ant-...",
    temperature=0.0,
    max_tokens=4096
)
```

**Models:**
- `claude-opus-4-6` - Most capable, $15/$75 per 1M tokens
- `claude-sonnet-4-5-20250929` - Balanced, $3/$15 per 1M tokens
- `claude-haiku-4-5` - Fastest, $0.80/$4 per 1M tokens

### OpenAI GPT

```python
llm = create_llm(
    provider="openai",
    model="gpt-4o",  # or gpt-4-turbo, gpt-4o-mini
    api_key="sk-...",
    temperature=0.0
)
```

**Models:**
- `gpt-4o` - Best overall, $5/$15 per 1M tokens
- `gpt-4-turbo` - High performance, $10/$30 per 1M tokens
- `gpt-4o-mini` - Cost-effective, $0.15/$0.60 per 1M tokens

### Google Gemini

```python
llm = create_llm(
    provider="google",
    model="gemini-1.5-pro",  # or gemini-1.5-flash
    api_key="...",
    temperature=0.0
)
```

### Azure OpenAI

```python
llm = create_llm(
    provider="azure",
    model="gpt-4",  # Your deployment name
    api_key="...",
    api_base="https://your-resource.openai.azure.com/",
    extra_params={
        "api_version": "2024-02-01",
        "azure_deployment": "your-deployment-name"
    }
)
```

### Local Models (Ollama)

```bash
# First, start Ollama
ollama serve

# Pull a model
ollama pull llama2
```

```python
llm = create_llm(
    provider="ollama",
    model="llama2",  # or mistral, codellama, etc.
    api_key="local",
    api_base="http://localhost:11434",
    temperature=0.0,
    max_tokens=2048
)
```

---

## Usage Examples

### Basic Completion

```python
from services.llm import create_llm, LLMMessage

llm = create_llm(provider="anthropic", model="claude-sonnet-4-5", api_key="...")

messages = [
    LLMMessage(role="user", content="What is 2+2?")
]

response = llm.generate(messages)
print(response.content)  # "2+2 equals 4."
```

### With System Message

```python
messages = [
    LLMMessage(role="system", content="You are a compliance expert."),
    LLMMessage(role="user", content="Explain SOD violations.")
]

response = llm.generate(messages, temperature=0.7)
```

### Streaming Response

```python
for chunk in llm.generate_stream(messages):
    print(chunk, end="", flush=True)
```

### Multi-turn Conversation

```python
conversation = [
    LLMMessage(role="system", content="You are a helpful assistant."),
    LLMMessage(role="user", content="What is Python?"),
]

response1 = llm.generate(conversation)
conversation.append(LLMMessage(role="assistant", content=response1.content))
conversation.append(LLMMessage(role="user", content="What are its main features?"))

response2 = llm.generate(conversation)
```

### Cost Tracking

```python
total_cost = 0.0

for prompt in prompts:
    messages = [LLMMessage(role="user", content=prompt)]
    response = llm.generate(messages)

    total_cost += response.cost
    print(f"Tokens: {response.usage['total_tokens']}")
    print(f"Cost: ${response.cost:.4f}")

print(f"\nTotal cost: ${total_cost:.4f}")
```

### Provider Switching

```python
# Try primary provider, fallback to secondary
providers = ["anthropic", "openai", "google"]

for provider_name in providers:
    try:
        llm = get_llm_from_config(provider=provider_name)
        response = llm.generate(messages)
        break
    except Exception as e:
        print(f"{provider_name} failed: {e}")
        continue
```

---

## Security & Encryption

### Generating Encryption Key

```bash
# Generate a new Fernet key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Output: ZjlWvN5xG8xJ3qKzL9mR7wC...
```

### Setting Up Encryption

1. **Set master key:**

```bash
export MASTER_ENCRYPTION_KEY="ZjlWvN5xG8xJ3qKzL9mR7wC..."
```

2. **Encrypt API keys:**

```python
from services.llm import ConfigEncryption

encryption = ConfigEncryption()

# Encrypt API key
encrypted_key = encryption.encrypt("sk-ant-api03-...")
print(encrypted_key)  # gAAAAABk...
```

3. **Update config:**

```yaml
anthropic:
  model: claude-sonnet-4-5
  api_key: gAAAAABk...  # Encrypted key
  encrypted: true  # Important!
```

### Best Practices

✅ **Do:**
- Use environment variables for API keys
- Encrypt keys in config files
- Store master key in secure vault (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly
- Use different keys for dev/staging/prod

❌ **Don't:**
- Commit API keys to git
- Share master encryption key
- Use same key across environments

---

## Migration Guide

### Migrating Existing Agents

#### Before (Direct Anthropic)

```python
from langchain_anthropic import ChatAnthropic

class Analyzer:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=0
        )

    def analyze(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages)
        return response.content
```

#### After (LLM Abstraction)

```python
from services.llm import get_llm_from_config, LLMMessage

class Analyzer:
    def __init__(self):
        # Can switch providers without code changes!
        self.llm = get_llm_from_config()

    def analyze(self, prompt):
        messages = [LLMMessage(role="user", content=prompt)]
        response = self.llm.generate(messages)
        return response.content
```

### Migrating Agent Files

#### agents/analyzer.py

**Before:**
```python
from langchain_anthropic import ChatAnthropic

class SODAnalyzer:
    def __init__(self):
        self.llm = ChatAnthropic(
            model="claude-opus-4-6",
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
```

**After:**
```python
from services.llm import get_llm_from_config, LLMMessage

class SODAnalyzer:
    def __init__(self, llm_provider=None):
        # Use provided LLM or load from config
        self.llm = llm_provider or get_llm_from_config(provider="anthropic")
```

#### agents/notifier.py

**Before:**
```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

def _generate_ai_analysis(self, user, violations, role_names):
    if not self.ai_enabled:
        return None

    chain = prompt | self.llm
    response = chain.invoke({...})
    return response.content
```

**After:**
```python
from services.llm import LLMMessage

def _generate_ai_analysis(self, user, violations, role_names):
    if not self.llm:
        return None

    # Format prompt
    prompt_text = self._format_analysis_prompt(user, violations, role_names)

    messages = [
        LLMMessage(role="system", content="You are a compliance analyst."),
        LLMMessage(role="user", content=prompt_text)
    ]

    response = self.llm.generate(messages)
    return response.content
```

### Step-by-Step Migration

1. **Update imports:**

```python
# Remove
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Add
from services.llm import get_llm_from_config, LLMMessage
```

2. **Update initialization:**

```python
# Old
self.llm = ChatAnthropic(model="...", api_key="...")

# New
self.llm = get_llm_from_config()
```

3. **Update message format:**

```python
# Old (LangChain format)
messages = [{"role": "user", "content": "..."}]

# New (Unified format)
messages = [LLMMessage(role="user", content="...")]
```

4. **Update invocation:**

```python
# Old (LangChain)
response = self.llm.invoke(messages)
content = response.content

# New (Unified)
response = self.llm.generate(messages)
content = response.content  # Same!
```

5. **Add cost tracking:**

```python
response = self.llm.generate(messages)

# Now you get cost for free!
print(f"Cost: ${response.cost:.4f}")
print(f"Tokens: {response.usage['total_tokens']}")
```

---

## Advanced Features

### Custom Provider Registration

```python
from services.llm import LLMProviderFactory, BaseLLMProvider

class CustomProvider(BaseLLMProvider):
    def generate(self, messages, **kwargs):
        # Your implementation
        pass

    # Implement other required methods...

# Register custom provider
LLMProviderFactory.register_provider("custom", CustomProvider)

# Use it
llm = create_llm(provider="custom", model="...", api_key="...")
```

### Token Counting

```python
# Count tokens before sending
text = "Your long prompt here..."
token_count = llm.count_tokens(text)

if token_count > 100000:
    print("Warning: Prompt too long!")
```

### Model Information

```python
# Get model details
info = llm.get_model_info()

print(f"Provider: {info['provider']}")
print(f"Model: {info['model']}")
print(f"Context length: {info['context_length']}")
print(f"Input cost: ${info['pricing']['input_per_million']}/1M tokens")
print(f"Supports streaming: {info['supports_streaming']}")
```

### Connection Testing

```python
# Test provider connection
if llm.test_connection():
    print("✅ Connection successful!")
else:
    print("❌ Connection failed!")
```

---

## Best Practices

### 1. Use Configuration Files

✅ **Good:**
```python
llm = get_llm_from_config()  # Easy to switch providers
```

❌ **Avoid:**
```python
llm = create_llm(provider="anthropic", api_key="hardcoded-key")
```

### 2. Handle Errors Gracefully

```python
from services.llm import LLMRateLimitError, LLMTimeoutError

try:
    response = llm.generate(messages)
except LLMRateLimitError:
    print("Rate limited! Waiting...")
    time.sleep(60)
    response = llm.generate(messages)
except LLMTimeoutError:
    print("Request timed out. Retrying with smaller prompt...")
```

### 3. Use System Messages

```python
# Good: Clear system context
messages = [
    LLMMessage(role="system", content="You are a financial compliance expert."),
    LLMMessage(role="user", content="Analyze this transaction...")
]
```

### 4. Track Costs

```python
# Monitor costs in production
response = llm.generate(messages)

if response.cost > 0.10:  # $0.10 threshold
    logger.warning(f"High cost operation: ${response.cost:.4f}")
```

### 5. Use Appropriate Models

- **Reasoning tasks**: Claude Opus, GPT-4o
- **Analysis tasks**: Claude Sonnet, GPT-4-turbo
- **Simple tasks**: Claude Haiku, GPT-4o-mini
- **Development**: Ollama (free)

---

## Troubleshooting

### Issue: "Provider not found"

**Solution:**
```python
# Check available providers
from services.llm import LLMProviderFactory

print(LLMProviderFactory.list_providers())
```

### Issue: "Authentication failed"

**Solution:**
1. Check API key is set correctly
2. Verify environment variable name
3. Try decrypting manually:

```python
from services.llm import ConfigEncryption

encryption = ConfigEncryption()
decrypted = encryption.decrypt("your-encrypted-key")
print(decrypted)
```

### Issue: "Module not found: anthropic"

**Solution:**
```bash
pip install anthropic openai google-generativeai cohere
```

### Issue: "Connection to Ollama failed"

**Solution:**
1. Start Ollama: `ollama serve`
2. Check endpoint: `curl http://localhost:11434/api/tags`
3. Pull model: `ollama pull llama2`

### Issue: High costs

**Solution:**
1. Use cheaper models (Haiku, GPT-4o-mini)
2. Reduce max_tokens
3. Add cost monitoring:

```python
if response.cost > threshold:
    raise Exception("Cost exceeded budget!")
```

---

## FAQ

**Q: Can I use multiple providers simultaneously?**
A: Yes! Each provider instance is independent:

```python
anthropic_llm = get_llm_from_config(provider="anthropic")
openai_llm = get_llm_from_config(provider="openai")

response1 = anthropic_llm.generate(messages)
response2 = openai_llm.generate(messages)
```

**Q: How do I switch providers without changing code?**
A: Just update the config file:

```yaml
default_provider: openai  # Changed from anthropic
```

**Q: Are streaming responses supported?**
A: Yes, all providers support streaming:

```python
for chunk in llm.generate_stream(messages):
    print(chunk, end="")
```

**Q: Can I use this with LangChain?**
A: Yes, but you'll need to wrap it. However, the abstraction layer provides similar functionality without LangChain dependencies.

**Q: How do I test without API costs?**
A: Use Ollama for free local testing:

```yaml
default_provider: ollama
```

---

## Summary

The LLM Abstraction Layer provides:

✅ **Unified Interface** - One API for all providers
✅ **Easy Provider Switching** - Change config, not code
✅ **Secure Key Management** - Encryption built-in
✅ **Cost Tracking** - Automatic cost calculation
✅ **Production Ready** - Error handling, retries, timeouts
✅ **Local Development** - Free testing with Ollama

### Next Steps

1. ✅ Copy example config: `cp config/llm_config.example.yaml config/llm_config.yaml`
2. ✅ Set API keys as environment variables
3. ✅ Test connection: `python -c "from services.llm import get_llm_from_config; llm = get_llm_from_config(); print(llm.test_connection())"`
4. ✅ Migrate existing agents (see Migration Guide)
5. ✅ Deploy to production

---

**Questions? Issues?**
Open an issue in the repository or contact the development team.

**Version**: 1.0.0
**Last Updated**: 2026-02-09
