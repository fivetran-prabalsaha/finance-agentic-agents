#!/usr/bin/env python3
"""
Token Tracking Demo

Demonstrates token usage tracking and cost calculation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.token_tracker import TokenTracker, format_cost, format_tokens


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_token_tracking():
    """Demonstrate token tracking features"""

    print_header("TOKEN USAGE & COST TRACKING DEMO")

    # Create a tracker
    tracker = TokenTracker()

    print("📊 Simulating Agent API Calls...\n")

    # Simulate various agent calls
    print("1. Analysis Agent - SOD Rule Check")
    tracker.track(
        model='claude-opus-4.6',
        input_tokens=15000,
        output_tokens=2500,
        agent_name='analyzer',
        operation='sod_rule_check'
    )
    print("   ✓ Tracked: 15,000 input + 2,500 output tokens")

    print("\n2. Risk Assessor - Organization Risk")
    tracker.track(
        model='claude-sonnet-4.5',
        input_tokens=8000,
        output_tokens=1200,
        agent_name='risk_assessor',
        operation='org_risk_assessment'
    )
    print("   ✓ Tracked: 8,000 input + 1,200 output tokens")

    print("\n3. Knowledge Base - Semantic Search")
    tracker.track(
        model='claude-haiku-4.5',
        input_tokens=2000,
        output_tokens=500,
        agent_name='knowledge_base',
        operation='semantic_search'
    )
    print("   ✓ Tracked: 2,000 input + 500 output tokens")

    print("\n4. Analysis Agent - User Violation Check (with caching)")
    tracker.track(
        model='claude-opus-4.6',
        input_tokens=5000,
        output_tokens=1500,
        cache_creation_tokens=10000,  # Write to cache
        cache_read_tokens=8000,       # Read from cache
        agent_name='analyzer',
        operation='user_violation_check'
    )
    print("   ✓ Tracked: 5,000 input + 1,500 output + 10,000 cache write + 8,000 cache read")

    print("\n5. Orchestrator - Workflow Coordination")
    tracker.track(
        model='claude-sonnet-4.5',
        input_tokens=3000,
        output_tokens=800,
        agent_name='orchestrator',
        operation='workflow_coordination'
    )
    print("   ✓ Tracked: 3,000 input + 800 output tokens")

    # Print summary
    tracker.print_summary()

    # Detailed per-agent breakdown
    print("\n" + "="*80)
    print("  DETAILED PER-AGENT ANALYSIS")
    print("="*80 + "\n")

    for agent_name in ['analyzer', 'risk_assessor', 'knowledge_base', 'orchestrator']:
        stats = tracker.get_agent_stats(agent_name)
        if stats:
            print(f"🤖 {agent_name.upper()}")
            print(f"   API Calls:         {stats['calls']}")
            print(f"   Input Tokens:      {format_tokens(stats['input_tokens'])}")
            print(f"   Output Tokens:     {format_tokens(stats['output_tokens'])}")

            if stats['cache_creation_tokens'] > 0:
                print(f"   Cache Write:       {format_tokens(stats['cache_creation_tokens'])}")
            if stats['cache_read_tokens'] > 0:
                print(f"   Cache Read:        {format_tokens(stats['cache_read_tokens'])}")

            print(f"   Total Tokens:      {format_tokens(stats['total_tokens'])}")
            print(f"   Cost:              {format_cost(stats['cost'])}")
            print()

    # Cost projections
    print("="*80)
    print("  COST PROJECTIONS")
    print("="*80 + "\n")

    summary = tracker.get_summary()
    total_cost = summary['total_cost']

    print("💰 Based on this demo run:")
    print(f"   Demo Cost:              {format_cost(total_cost)}")
    print("\n📊 Scaling Estimates:")
    print(f"   10 users/day:           {format_cost(total_cost * 10)} per day")
    print(f"   100 users/day:          {format_cost(total_cost * 100)} per day")
    print(f"   500 users/day:          {format_cost(total_cost * 500)} per day")
    print("\n📅 Monthly Estimates (30 days):")
    print(f"   10 users/day:           {format_cost(total_cost * 10 * 30)} per month")
    print(f"   100 users/day:          {format_cost(total_cost * 100 * 30)} per month")
    print(f"   500 users/day:          {format_cost(total_cost * 500 * 30)} per month")
    print("\n📆 Annual Estimates (365 days):")
    print(f"   10 users/day:           {format_cost(total_cost * 10 * 365)} per year")
    print(f"   100 users/day:          {format_cost(total_cost * 100 * 365)} per year")
    print(f"   500 users/day:          {format_cost(total_cost * 500 * 365)} per year")

    # Model pricing comparison
    print("\n" + "="*80)
    print("  MODEL PRICING COMPARISON")
    print("="*80 + "\n")

    print("💵 Claude API Pricing (per million tokens):")
    print("\n   Claude Opus 4.6 (Most Capable):")
    print("      Input:       $15.00")
    print("      Output:      $75.00")
    print("      Cache Write: $18.75")
    print("      Cache Read:  $1.50")
    print("\n   Claude Sonnet 4.5 (Balanced):")
    print("      Input:       $3.00")
    print("      Output:      $15.00")
    print("      Cache Write: $3.75")
    print("      Cache Read:  $0.30")
    print("\n   Claude Haiku 4.5 (Fast & Affordable):")
    print("      Input:       $1.00")
    print("      Output:      $5.00")
    print("      Cache Write: $1.25")
    print("      Cache Read:  $0.10")

    # Optimization recommendations
    print("\n" + "="*80)
    print("  COST OPTIMIZATION RECOMMENDATIONS")
    print("="*80 + "\n")

    print("💡 Tips to Reduce Costs:")
    print("\n   1. Use Prompt Caching:")
    print("      • Cache SOD rules and system prompts")
    print("      • Can reduce costs by 90% for repeated content")
    print("      • Especially effective for batch processing")

    print("\n   2. Choose the Right Model:")
    print("      • Opus: Complex analysis requiring deep reasoning")
    print("      • Sonnet: Standard SOD checks and risk assessment")
    print("      • Haiku: Simple lookups and semantic search")

    print("\n   3. Optimize Token Usage:")
    print("      • Use concise prompts")
    print("      • Limit context to relevant information")
    print("      • Batch similar operations together")

    print("\n   4. Monitor and Alert:")
    print("      • Set up cost alerts")
    print("      • Track token usage trends")
    print("      • Optimize high-cost operations")

    print("\n" + "="*80)


if __name__ == '__main__':
    demo_token_tracking()
