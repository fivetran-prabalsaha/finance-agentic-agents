#!/usr/bin/env python3
"""
Test script for MCP Server

Tests all MCP endpoints and tool calls
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

# Configuration
BASE_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:8080')
API_KEY = os.getenv('MCP_API_KEY', 'dev-key-12345')

HEADERS = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
}


def print_section(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(success: bool, message: str):
    """Print test result"""
    status = "✅" if success else "❌"
    print(f"{status} {message}")


def test_health_check():
    """Test health check endpoint"""
    print_section("TEST 1: Health Check")

    try:
        response = requests.get(f"{BASE_URL}/health")
        success = response.status_code == 200

        print_result(success, f"Health check: {response.status_code}")

        if success:
            print(f"   Response: {response.json()}")

        return success

    except Exception as e:
        print_result(False, f"Health check failed: {str(e)}")
        return False


def test_root_endpoint():
    """Test root endpoint"""
    print_section("TEST 2: Root Endpoint")

    try:
        response = requests.get(f"{BASE_URL}/")
        success = response.status_code == 200

        print_result(success, f"Root endpoint: {response.status_code}")

        if success:
            data = response.json()
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")

        return success

    except Exception as e:
        print_result(False, f"Root endpoint failed: {str(e)}")
        return False


def test_tools_list_endpoint():
    """Test /tools endpoint"""
    print_section("TEST 3: Tools List Endpoint")

    try:
        response = requests.get(
            f"{BASE_URL}/tools",
            headers=HEADERS
        )
        success = response.status_code == 200

        print_result(success, f"Tools list endpoint: {response.status_code}")

        if success:
            data = response.json()
            print(f"   Available tools: {data.get('count')}")
            for tool in data.get('tools', []):
                print(f"      • {tool['name']}")

        return success

    except Exception as e:
        print_result(False, f"Tools list endpoint failed: {str(e)}")
        return False


def test_mcp_initialize():
    """Test MCP initialize"""
    print_section("TEST 4: MCP Initialize")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1
        }

        response = requests.post(
            f"{BASE_URL}/mcp",
            headers=HEADERS,
            json=payload
        )

        success = response.status_code == 200

        print_result(success, f"MCP initialize: {response.status_code}")

        if success:
            data = response.json()
            print(f"   Protocol version: {data.get('result', {}).get('protocolVersion')}")
            print(f"   Server: {data.get('result', {}).get('serverInfo', {}).get('name')}")

        return success

    except Exception as e:
        print_result(False, f"MCP initialize failed: {str(e)}")
        return False


def test_mcp_tools_list():
    """Test MCP tools/list"""
    print_section("TEST 5: MCP Tools List")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }

        response = requests.post(
            f"{BASE_URL}/mcp",
            headers=HEADERS,
            json=payload
        )

        success = response.status_code == 200

        print_result(success, f"MCP tools/list: {response.status_code}")

        if success:
            data = response.json()
            tools = data.get('result', {}).get('tools', [])
            print(f"   Tools available: {len(tools)}")
            for tool in tools:
                print(f"      • {tool['name']}: {tool['description'][:60]}...")

        return success

    except Exception as e:
        print_result(False, f"MCP tools/list failed: {str(e)}")
        return False


def test_mcp_ping():
    """Test MCP ping"""
    print_section("TEST 6: MCP Ping")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "ping",
            "params": {},
            "id": 3
        }

        response = requests.post(
            f"{BASE_URL}/mcp",
            headers=HEADERS,
            json=payload
        )

        success = response.status_code == 200

        print_result(success, f"MCP ping: {response.status_code}")

        if success:
            data = response.json()
            print(f"   Response: {data.get('result')}")

        return success

    except Exception as e:
        print_result(False, f"MCP ping failed: {str(e)}")
        return False


def test_list_systems_tool():
    """Test list_systems tool"""
    print_section("TEST 7: Tool - list_systems")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_systems",
                "arguments": {}
            },
            "id": 4
        }

        response = requests.post(
            f"{BASE_URL}/mcp",
            headers=HEADERS,
            json=payload
        )

        success = response.status_code == 200

        print_result(success, f"list_systems tool: {response.status_code}")

        if success:
            data = response.json()
            content = data.get('result', {}).get('content', [])
            if content:
                print(f"\n{content[0].get('text', '')}\n")

        return success

    except Exception as e:
        print_result(False, f"list_systems tool failed: {str(e)}")
        return False


def test_violation_stats_tool():
    """Test get_violation_stats tool"""
    print_section("TEST 8: Tool - get_violation_stats")

    try:
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_violation_stats",
                "arguments": {
                    "time_range": "month"
                }
            },
            "id": 5
        }

        response = requests.post(
            f"{BASE_URL}/mcp",
            headers=HEADERS,
            json=payload
        )

        success = response.status_code == 200

        print_result(success, f"get_violation_stats tool: {response.status_code}")

        if success:
            data = response.json()
            content = data.get('result', {}).get('content', [])
            if content:
                print(f"\n{content[0].get('text', '')}\n")

        return success

    except Exception as e:
        print_result(False, f"get_violation_stats tool failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("  MCP SERVER TEST SUITE")
    print("=" * 80)
    print(f"\nTesting: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}...\n")

    tests = [
        ("Health Check", test_health_check),
        ("Root Endpoint", test_root_endpoint),
        ("Tools List Endpoint", test_tools_list_endpoint),
        ("MCP Initialize", test_mcp_initialize),
        ("MCP Tools List", test_mcp_tools_list),
        ("MCP Ping", test_mcp_ping),
        ("Tool: list_systems", test_list_systems_tool),
        ("Tool: get_violation_stats", test_violation_stats_tool),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {str(e)}")
            results.append((name, False))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Passed: {passed}/{total}\n")

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {name}")

    print("\n" + "=" * 80)

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
