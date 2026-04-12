#!/usr/bin/env python3
"""
Quick test script to verify Slack bot can communicate with MCP server

Usage:
    python test_slack_bot.py
"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "dev-key-12345")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

def test_mcp_server_health():
    """Test if MCP server is running and healthy"""
    print("Testing MCP server health...")
    try:
        response = requests.get(f"{MCP_SERVER_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ MCP server is healthy: {response.json()}")
            return True
        else:
            print(f"❌ MCP server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to MCP server at {MCP_SERVER_URL}")
        print("   Make sure the server is running: python -m mcp.mcp_server")
        return False
    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")
        return False


def test_mcp_tool_call():
    """Test calling an MCP tool directly using JSON-RPC 2.0"""
    print("\nTesting MCP tool call (tools/list)...")
    try:
        # Test tools/list method first
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = requests.post(
            f"{MCP_SERVER_URL}/mcp",
            json=mcp_request,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": MCP_API_KEY
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if "result" in result and "tools" in result["result"]:
                tool_count = len(result["result"]["tools"])
                print("✅ MCP tool call successful")
                print(f"   Found {tool_count} available tools")
                return True
            else:
                print(f"❌ MCP tool call returned unexpected format: {result}")
                return False
        else:
            print(f"❌ MCP tool call failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error calling MCP tool: {e}")
        return False


def test_anthropic_api_key():
    """Test if Anthropic API key is set"""
    print("\nTesting Anthropic API key...")
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set in .env file")
        return False

    if not ANTHROPIC_API_KEY.startswith("sk-ant-"):
        print("❌ ANTHROPIC_API_KEY has invalid format (should start with 'sk-ant-')")
        return False

    print(f"✅ ANTHROPIC_API_KEY is set (ends with: ...{ANTHROPIC_API_KEY[-8:]})")
    return True


def test_slack_tokens():
    """Test if Slack tokens are set"""
    print("\nTesting Slack tokens...")

    slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
    slack_app_token = os.environ.get("SLACK_APP_TOKEN")

    issues = []

    if not slack_bot_token:
        issues.append("SLACK_BOT_TOKEN not set")
    elif not slack_bot_token.startswith("xoxb-"):
        issues.append("SLACK_BOT_TOKEN should start with 'xoxb-'")
    else:
        print(f"✅ SLACK_BOT_TOKEN is set (ends with: ...{slack_bot_token[-8:]})")

    if not slack_app_token:
        issues.append("SLACK_APP_TOKEN not set")
    elif not slack_app_token.startswith("xapp-"):
        issues.append("SLACK_APP_TOKEN should start with 'xapp-'")
    else:
        print(f"✅ SLACK_APP_TOKEN is set (ends with: ...{slack_app_token[-8:]})")

    if issues:
        print("❌ Slack token issues:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n   See SLACK_BOT_SETUP.md for instructions on getting tokens")
        return False

    return True


def test_slack_sdk():
    """Test if slack-bolt is installed"""
    print("\nTesting slack-bolt installation...")
    try:
        import slack_bolt
        try:
            version = slack_bolt.__version__
        except AttributeError:
            # slack-bolt might not expose __version__, check via pkg_resources
            try:
                import pkg_resources
                version = pkg_resources.get_distribution("slack-bolt").version
            except:
                version = "installed"
        print(f"✅ slack-bolt is installed (version: {version})")
        return True
    except ImportError:
        print("❌ slack-bolt not installed")
        print("   Install with: pip install -r requirements-slack.txt")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Slack Bot Configuration Test")
    print("=" * 60)

    results = {
        "MCP Server Health": test_mcp_server_health(),
        "MCP Tool Call": test_mcp_tool_call(),
        "Anthropic API Key": test_anthropic_api_key(),
        "Slack Tokens": test_slack_tokens(),
        "Slack SDK": test_slack_sdk()
    }

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("=" * 60)

    if all(results.values()):
        print("\n🎉 All tests passed! You're ready to run the Slack bot.")
        print("\nNext steps:")
        print("1. Start the MCP server: python -m mcp.mcp_server")
        print("2. Start the Slack bot: python slack_bot_local.py")
        print("3. Test in Slack: @Compliance Agent who am i")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before running the bot.")
        print("\nSee SLACK_BOT_SETUP.md for complete setup instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
