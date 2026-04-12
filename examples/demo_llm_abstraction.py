#!/usr/bin/env python3
"""
LLM Abstraction Layer Demo

Demonstrates how to use the unified LLM interface with different providers
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.llm import (
    ConfigEncryption,
    LLMConfigManager,
    LLMMessage,
    create_llm,
    get_llm_from_config,
)


def demo_basic_usage():
    """Demo 1: Basic LLM usage"""
    print("="*80)
    print("DEMO 1: Basic LLM Usage")
    print("="*80)

    # Create LLM provider directly
    llm = create_llm(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
        max_tokens=500
    )

    print(f"\n✅ Created {llm.get_provider_name()} provider")
    print(f"   Model: {llm.get_model_name()}")

    # Test connection
    print("\n🔍 Testing connection...")
    if llm.test_connection():
        print("   ✅ Connection successful!")
    else:
        print("   ❌ Connection failed!")
        return

    # Generate completion
    print("\n💬 Generating completion...")
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content="What is a segregation of duties violation? Explain in one sentence.")
    ]

    response = llm.generate(messages)

    print("\n📝 Response:")
    print(f"   {response.content}")
    print("\n📊 Metrics:")
    print(f"   Input tokens: {response.usage['input_tokens']}")
    print(f"   Output tokens: {response.usage['output_tokens']}")
    print(f"   Total tokens: {response.usage['total_tokens']}")
    print(f"   Cost: ${response.cost:.4f}")
    print(f"   Latency: {response.latency_ms:.2f}ms")


def demo_config_file():
    """Demo 2: Using configuration file"""
    print("\n\n" + "="*80)
    print("DEMO 2: Using Configuration File")
    print("="*80)

    config_path = "config/llm_config.yaml"

    if not os.path.exists(config_path):
        print(f"\n⚠️  Config file not found: {config_path}")
        print("   Create one by copying config/llm_config.example.yaml")
        return

    try:
        # Load from config
        llm = get_llm_from_config(config_path=config_path)

        print("\n✅ Loaded provider from config")
        print(f"   Provider: {llm.get_provider_name()}")
        print(f"   Model: {llm.get_model_name()}")

        # Get model info
        info = llm.get_model_info()
        print("\n📋 Model Information:")
        print(f"   Context length: {info['context_length']:,} tokens")
        print(f"   Input cost: ${info['pricing']['input_per_million']}/1M tokens")
        print(f"   Output cost: ${info['pricing']['output_per_million']}/1M tokens")
        print(f"   Supports streaming: {info['supports_streaming']}")

    except Exception as e:
        print(f"\n❌ Error loading config: {str(e)}")


def demo_streaming():
    """Demo 3: Streaming responses"""
    print("\n\n" + "="*80)
    print("DEMO 3: Streaming Responses")
    print("="*80)

    llm = create_llm(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0
    )

    messages = [
        LLMMessage(role="user", content="List 3 benefits of SOD compliance. Be brief.")
    ]

    print("\n💬 Streaming response:\n")
    print("   ", end="", flush=True)

    for chunk in llm.generate_stream(messages):
        print(chunk, end="", flush=True)

    print("\n")


def demo_multi_provider():
    """Demo 4: Testing multiple providers"""
    print("\n\n" + "="*80)
    print("DEMO 4: Multiple Provider Comparison")
    print("="*80)

    providers_to_test = [
        ("anthropic", "claude-sonnet-4-5-20250929", "ANTHROPIC_API_KEY"),
        ("openai", "gpt-4o-mini", "OPENAI_API_KEY"),
    ]

    messages = [
        LLMMessage(role="user", content="What is 2+2? Answer in one word.")
    ]

    print("\n🔬 Testing providers with same prompt...\n")

    results = []

    for provider, model, env_var in providers_to_test:
        api_key = os.getenv(env_var)

        if not api_key:
            print(f"   ⚠️  {provider}: API key not found (${env_var})")
            continue

        try:
            llm = create_llm(
                provider=provider,
                model=model,
                api_key=api_key,
                temperature=0.0,
                max_tokens=10
            )

            response = llm.generate(messages)

            results.append({
                'provider': provider,
                'model': model,
                'response': response.content,
                'cost': response.cost,
                'tokens': response.usage['total_tokens'],
                'latency': response.latency_ms
            })

            print(f"   ✅ {provider}:")
            print(f"      Response: {response.content}")
            print(f"      Cost: ${response.cost:.6f}")
            print(f"      Tokens: {response.usage['total_tokens']}")
            print(f"      Latency: {response.latency_ms:.2f}ms\n")

        except Exception as e:
            print(f"   ❌ {provider}: {str(e)}\n")

    # Summary
    if results:
        print("\n📊 Summary:")
        cheapest = min(results, key=lambda x: x['cost'])
        fastest = min(results, key=lambda x: x['latency'])

        print(f"   💰 Cheapest: {cheapest['provider']} (${cheapest['cost']:.6f})")
        print(f"   ⚡ Fastest: {fastest['provider']} ({fastest['latency']:.2f}ms)")


def demo_encryption():
    """Demo 5: API key encryption"""
    print("\n\n" + "="*80)
    print("DEMO 5: API Key Encryption")
    print("="*80)

    # Generate encryption key
    print("\n🔐 Generating encryption key...")
    encryption_key = ConfigEncryption.generate_key()
    print(f"   Key: {encryption_key[:20]}...")
    print("   (Store this in MASTER_ENCRYPTION_KEY environment variable)")

    # Encrypt API key
    print("\n🔒 Encrypting API key...")
    encryption = ConfigEncryption(master_key=encryption_key)

    sample_key = "sk-ant-api03-abc123xyz789"
    encrypted = encryption.encrypt(sample_key)

    print(f"   Original: {sample_key}")
    print(f"   Encrypted: {encrypted[:50]}...")

    # Decrypt API key
    print("\n🔓 Decrypting API key...")
    decrypted = encryption.decrypt(encrypted)
    print(f"   Decrypted: {decrypted}")

    if decrypted == sample_key:
        print("   ✅ Encryption/decryption successful!")
    else:
        print("   ❌ Encryption/decryption failed!")


def demo_cost_tracking():
    """Demo 6: Cost tracking across multiple calls"""
    print("\n\n" + "="*80)
    print("DEMO 6: Cost Tracking")
    print("="*80)

    llm = create_llm(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        temperature=0.0,
        max_tokens=100
    )

    prompts = [
        "What is SOD?",
        "Why is SOD important?",
        "Give one example of SOD violation."
    ]

    print("\n💰 Running multiple prompts and tracking costs...\n")

    total_cost = 0.0
    total_tokens = 0

    for i, prompt in enumerate(prompts, 1):
        messages = [LLMMessage(role="user", content=prompt)]
        response = llm.generate(messages)

        total_cost += response.cost
        total_tokens += response.usage['total_tokens']

        print(f"   {i}. Prompt: {prompt}")
        print(f"      Cost: ${response.cost:.4f}")
        print(f"      Tokens: {response.usage['total_tokens']}\n")

    print("📊 Total:")
    print(f"   Total cost: ${total_cost:.4f}")
    print(f"   Total tokens: {total_tokens:,}")
    print(f"   Avg cost per call: ${total_cost / len(prompts):.4f}")


def demo_config_manager():
    """Demo 7: Using Config Manager"""
    print("\n\n" + "="*80)
    print("DEMO 7: Configuration Manager")
    print("="*80)

    # Create config manager
    config_manager = LLMConfigManager()

    # Add provider configuration
    print("\n➕ Adding provider configuration...")
    config_manager.set_provider_config(
        provider_name="test_anthropic",
        model="claude-sonnet-4-5",
        api_key="sk-ant-test-123",
        encrypt_key=False,  # For demo purposes
        temperature=0.7,
        max_tokens=2048
    )

    # List providers
    print("\n📋 Configured providers:")
    for provider in config_manager.list_providers():
        print(f"   - {provider}")

    # Set default
    if config_manager.list_providers():
        first_provider = config_manager.list_providers()[0]
        config_manager.set_default_provider(first_provider)
        print(f"\n✅ Set default provider: {first_provider}")

    # Save config
    output_path = "config/llm_config_demo.yaml"
    config_manager.save_config(output_path)
    print(f"\n💾 Saved config to: {output_path}")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("  LLM ABSTRACTION LAYER - DEMO")
    print("="*80)

    # Check for API keys
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))

    print("\n🔑 API Keys Status:")
    print(f"   Anthropic: {'✅ Found' if has_anthropic else '❌ Not found (set ANTHROPIC_API_KEY)'}")
    print(f"   OpenAI: {'✅ Found' if has_openai else '❌ Not found (set OPENAI_API_KEY)'}")

    if not has_anthropic and not has_openai:
        print("\n⚠️  No API keys found. Set at least one to run the demo.")
        print("\n   export ANTHROPIC_API_KEY='sk-ant-...'")
        print("   export OPENAI_API_KEY='sk-...'")
        return

    print("\n" + "-"*80)

    try:
        # Run demos
        if has_anthropic:
            demo_basic_usage()
            demo_config_file()
            demo_streaming()
            demo_cost_tracking()

        if has_anthropic and has_openai:
            demo_multi_provider()

        demo_encryption()
        demo_config_manager()

        print("\n\n" + "="*80)
        print("  ✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\n📚 For more information, see: LLM_ABSTRACTION_GUIDE.md\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
