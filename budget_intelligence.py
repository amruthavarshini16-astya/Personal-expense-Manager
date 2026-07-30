"""
Resilient Pocket - Budget Intelligence Engine
Generates personalized, data-driven financial guidance, safe-to-spend limits, and category budget optimization cuts.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from telemetry import measure_latency

class BudgetIntelligenceEngine:
    """Computes safe-to-spend allowances, savings goals, overspending alerts, and budget cuts."""

    @measure_latency("budget_intel_analyze")
    def analyze_budget_intelligence(
        self,
        current_cushion: float,
        monthly_income: float,
        target_daily_budget: float,
        runway_days: int,
        daily_burn_rate: float,
        active_brake: float,
        transactions: List[Dict[str, Any]],
        savings_goal_target: float = 50000.0,
        savings_goal_current: float = 12000.0
    ) -> Dict[str, Any]:
        """
        Analyze current financial telemetry and generate actionable, explainable budget advice.
        """
        # 1. Emergency Reserve Target (3 months income target)
        emergency_reserve_target = max(5000.0, monthly_income * 3.0)
        cushion_surplus = current_cushion - emergency_reserve_target

        # 2. Safe-to-Spend Daily Amount Calculation
        if runway_days > 0 and current_cushion > 0:
            raw_safe_daily = (current_cushion / max(30, runway_days)) - active_brake
            safe_to_spend_daily = max(150.0, round(raw_safe_daily, 2))
        else:
            safe_to_spend_daily = 100.0

        # 3. Monthly Savings Target (Recommended 20% of income + cushion buffer)
        recommended_monthly_savings = round(monthly_income * 0.20, 2)
        savings_progress_pct = round(min(100.0, (savings_goal_current / max(1.0, savings_goal_target)) * 100.0), 1)

        # 4. Category Spending Breakdown & Budget Cut Optimization
        category_spending: Dict[str, float] = {}
        if transactions:
            df = pd.DataFrame(transactions)
            df_expenses = df[df["tx_type"] == "EXPENSE"]
            if not df_expenses.empty:
                category_spending = df_expenses.groupby("category")["amount"].sum().to_dict()

        total_expense = sum(category_spending.values()) if category_spending else 1.0
        
        # Identify high discretionary categories (Food, Shopping, Entertainment)
        category_cuts: List[Dict[str, Any]] = []
        overspending_alerts: List[Dict[str, Any]] = []

        discretionary_cats = ["Food", "Shopping", "Entertainment", "Travel"]
        for cat, amt in category_spending.items():
            pct = (amt / total_expense) * 100.0
            if cat in discretionary_cats and pct > 20.0:
                potential_savings = round(amt * 0.25, 2)
                category_cuts.append({
                    "category": cat,
                    "spent": round(amt, 2),
                    "spent_pct": round(pct, 1),
                    "recommended_cut": potential_savings,
                    "new_limit": round(amt - potential_savings, 2),
                    "reason": f"{cat} represents {round(pct, 1)}% of total expenses. Cutting 25% saves ${potential_savings:.2f}/mo."
                })
                overspending_alerts.append({
                    "category": cat,
                    "severity": "HIGH" if pct > 35.0 else "MODERATE",
                    "message": f"High expenditure in {cat} (${amt:.2f}, {round(pct, 1)}% of total spent)."
                })

        # 5. Risk-Aware Guidance Integration based on Runway Days
        risk_level = "LOW"
        forecast_guidance = []
        if runway_days < 30:
            risk_level = "CRITICAL"
            forecast_guidance.append({
                "action": "Pause Discretionary Spending",
                "impact": "Extends runway immediately by 12–18 days.",
                "reason": f"Runway is critical at {runway_days} days."
            })
            forecast_guidance.append({
                "action": "Activate 30-Day Recovery Path",
                "impact": "Spreads shock deficit over a wider window.",
                "reason": "Lowers daily spending limit to preserve remaining cash."
            })
        elif runway_days < 60:
            risk_level = "MODERATE"
            forecast_guidance.append({
                "action": "Trim Non-Essential Categories by 20%",
                "impact": "Adds 8–12 days to cash runway.",
                "reason": f"Runway is under 60 days ({runway_days} days remaining)."
            })

        return {
            "safe_to_spend_daily": safe_to_spend_daily,
            "emergency_reserve_target": emergency_reserve_target,
            "cushion_surplus": round(cushion_surplus, 2),
            "recommended_monthly_savings": recommended_monthly_savings,
            "savings_goal": {
                "target": savings_goal_target,
                "current": savings_goal_current,
                "progress_pct": savings_progress_pct,
                "remaining": round(max(0.0, savings_goal_target - savings_goal_current), 2)
            },
            "category_spending": {k: round(v, 2) for k, v in category_spending.items()},
            "category_cuts": category_cuts,
            "overspending_alerts": overspending_alerts,
            "risk_level": risk_level,
            "forecast_guidance": forecast_guidance
        }
