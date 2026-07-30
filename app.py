"""
Resilient Pocket - Main CLI Demo & AI Copilot Test Suite
Run with: python app.py
"""
import sys
import os
import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from core import ResilientPocket
from telemetry import telemetry

def print_banner():
    print("=" * 80)
    print("                     RESILIENT POCKET (v2.0.0)")
    print("       Predictive AI Financial Copilot & Budget Intelligence Engine")
    print("=" * 80)

def generate_visual_chart(copilot: ResilientPocket, output_path: str = "runway_forecast.png"):
    """Generate high-contrast visual forecast chart."""
    dashboard = copilot.get_dashboard_summary()
    runway = dashboard["runway"]
    health = dashboard["health"]
    cushion = dashboard["current_cushion"]

    state_clean = health["state"].split()[0]

    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0f172a')
    ax1.set_facecolor('#1e293b')
    ax2.set_facecolor('#1e293b')

    days = np.arange(0, min(120, max(30, runway["runway_days"] + 10)))
    daily_burn = runway["effective_daily_burn"]
    cushion_projection = np.maximum(0, cushion - daily_burn * days)

    ax1.plot(days, cushion_projection, color='#38bdf8', linewidth=2.5, label=f'Projected Cushion (${daily_burn}/day burn)')
    ax1.axhline(0, color='#ef4444', linestyle='--', alpha=0.7, label='Depletion Horizon')
    ax1.scatter([runway["runway_days"]], [0], color='#f59e0b', s=100, zorder=5, label=f'Exhaustion (Day {runway["runway_days"]})')
    
    ax1.set_title('OLS Financial Runway Forecast Trajectory', fontsize=12, fontweight='bold', color='#f8fafc', pad=12)
    ax1.set_xlabel('Days Ahead', color='#94a3b8')
    ax1.set_ylabel('Liquid Cushion ($)', color='#94a3b8')
    ax1.grid(True, linestyle=':', alpha=0.3, color='#475569')
    ax1.legend(loc='upper right', facecolor='#0f172a', edgecolor='#334155')

    breakdown = health["breakdown"]
    pillars = ['Cushion Ratio', 'Runway Days', 'Shock Penalty', 'Stability Index']
    scores = [breakdown["cushion_score"], breakdown["runway_score"], breakdown["shock_score"], breakdown["stability_score"]]
    colors = ['#10b981', '#38bdf8', '#f59e0b', '#8b5cf6']

    bars = ax2.bar(pillars, scores, color=colors, width=0.5, edgecolor='#334155', linewidth=1.5)
    ax2.set_ylim(0, 110)
    ax2.set_title(f'Health FSM Matrix: {health["score"]}/100 [{state_clean}]', fontsize=12, fontweight='bold', color='#f8fafc', pad=12)
    ax2.set_ylabel('Score Pillar (0-100)', color='#94a3b8')
    ax2.grid(axis='y', linestyle=':', alpha=0.3, color='#475569')

    for bar, score in zip(bars, scores):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{score}', ha='center', va='bottom', color='#f8fafc', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

def run_demo():
    print_banner()

    # 1. Initialize Co-Pilot & Seed Data
    print("\n[1] INITIALIZING AI COPILOT & SQLITE MEMORY LAYER...")
    copilot = ResilientPocket()
    copilot.db.seed_demo_data(force=True)
    print("   [OK] SQLite database initialized and seeded with 45 days of transaction history.")

    # 2. Test AI Assistant Query Scenarios
    print("\n[2] TESTING INTELLIGENT AI ASSISTANT QUERY ENGINE...")
    test_queries = [
        "Can I afford a $450 smartwatch?",
        "Where can I cut spending?",
        "Why is my health score at this state?",
        "How long will my cash last?"
    ]
    for q in test_queries:
        ans = copilot.ask_assistant(q)
        print(f"\n   💬 User Query: '{q}'")
        print(f"   🤖 AI Verdict: {ans.get('verdict', 'INFORMATIONAL')}")
        print(f"   💡 Explanation:")
        print(f"      - Trigger   : {ans['explanation']['trigger']}")
        print(f"      - Data Point: {ans['explanation']['data_point']}")
        print(f"      - Next Step : {ans['explanation']['next_action']}")

    # 3. Simulate Overspending & Shock Recovery Scenario
    print("\n[3] TESTING SHOCK RECOVERY & OVERSPENDING ASSISTANT RESPONSE...")
    shock_result = copilot.record_transaction("Emergency Laptop Repair", 18500.0, "EXPENSE", recovery_window_days=15)
    shock_ans = copilot.ask_assistant("How to recover from my emergency laptop shock?")
    print(f"   💥 Shock Triggered: $18,500 Laptop Repair")
    print(f"   🤖 AI Guidance: {shock_ans['explanation']['next_action']}")

    # 4. Proactive Explainable AI Insights
    print("\n[4] GENERATING PROACTIVE EXPLAINABLE AI INSIGHTS...")
    dashboard = copilot.get_dashboard_summary()
    insights = dashboard.get("ai_insights", [])
    for idx, ins in enumerate(insights, 1):
        print(f"   • Insight #{idx}: {ins['title']} [{ins['badge']}]")
        print(f"     - Suggestion : {ins['suggestion']}")
        print(f"     - Trigger    : {ins['explanation']['trigger']}")
        print(f"     - Next Action: {ins['explanation']['next_action']}")

    # 5. Print Microsecond Telemetry Summary
    print("\n[5] MICROSECOND SYSTEM TELEMETRY AUDIT...")
    telemetry_summary = telemetry.get_summary()
    print(f"   * Total Monitored Calls   : {telemetry_summary['total_calls']}")
    print(f"   * Average Function Latency: {telemetry_summary['avg_latency_us']} us ({telemetry_summary['avg_latency_ms']} ms)")
    print(f"   * Recent Latency Benchmarks:")
    for metric in telemetry_summary['latest_metrics']:
        print(f"     - [{metric['operation']}] -> {metric['latency_us']} us ({metric['latency_ms']} ms)")

    # 6. Generate Chart
    generate_visual_chart(copilot, "runway_forecast.png")

    print("\n" + "=" * 80)
    print("   SUCCESS! Resilient Pocket v2.0 AI Copilot execution completed cleanly.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_demo()
