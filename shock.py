"""
Resilient Pocket - Capital Shock Recovery & Amortization Brake Engine
Detects capital shocks, computes deficit impact, and applies multi-window amortization brakes (7, 15, 30 days).
"""
import datetime
from typing import Dict, Any, List, Optional
from config import SHOCK_THRESHOLD_RATIO, SHOCK_BUDGET_MULTIPLIER
from telemetry import measure_latency

class CapitalShockEngine:
    """Detects liquidity shocks and recalculates daily spending brakes using deficit amortization."""

    def __init__(self, shock_threshold_ratio: float = SHOCK_THRESHOLD_RATIO, budget_multiplier: float = SHOCK_BUDGET_MULTIPLIER) -> None:
        self.shock_threshold_ratio = shock_threshold_ratio
        self.budget_multiplier = budget_multiplier

    @measure_latency("shock_evaluate_tx")
    def evaluate_transaction(self, amount: float, description: str, current_cushion: float, target_daily_budget: float) -> Optional[Dict[str, Any]]:
        """
        Evaluate if an expense transaction qualifies as a Capital Shock.
        Returns shock assessment dictionary if detected, otherwise None.
        """
        if amount <= 0 or current_cushion <= 0:
            return None

        cushion_impact = (amount / current_cushion)
        budget_ratio = (amount / target_daily_budget) if target_daily_budget > 0 else 0.0

        is_cushion_shock = cushion_impact >= self.shock_threshold_ratio
        is_budget_shock = budget_ratio >= self.budget_multiplier

        if is_cushion_shock or is_budget_shock:
            impact_pct = round(cushion_impact * 100.0, 2)
            severity = "HIGH" if impact_pct >= 15.0 else ("MEDIUM" if impact_pct >= 8.0 else "MODERATE")
            
            return {
                "is_shock": True,
                "amount": amount,
                "description": description,
                "impact_pct": impact_pct,
                "budget_ratio": round(budget_ratio, 2),
                "severity": severity,
                "suggested_windows": [7, 15, 30],
                "message": f"Capital Shock Detected! {description} of ${amount:.2f} consumes {impact_pct}% of liquid cushion."
            }

        return None

    @measure_latency("shock_create_amortization_brake")
    def create_amortization_brake(self, shock_amount: float, recovery_days: int = 15) -> Dict[str, Any]:
        """
        Calculate daily amortization brake distribution across the chosen recovery window (7, 15, or 30 days).
        
        Amortization Formula:
          Daily Deficit Distribution = Shock Deficit Amount / Recovery Days
        """
        valid_windows = [7, 15, 30]
        days = recovery_days if recovery_days in valid_windows else 15

        daily_brake_amount = round(shock_amount / days, 2)
        end_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()

        return {
            "shock_amount": shock_amount,
            "recovery_days": days,
            "daily_brake_amount": daily_brake_amount,
            "end_date": end_date,
            "explanation": (
                f"Amortizing ${shock_amount:.2f} deficit over {days} days. "
                f"Daily spending allowance reduced by ${daily_brake_amount:.2f}/day until {end_date}."
            )
        }

    @measure_latency("shock_recalculate_spending_limit")
    def recalculate_spending_limit(self, base_daily_budget: float, active_shocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recalculate current daily spending limit considering all active amortization brakes.
        """
        total_daily_brake = sum(s.get("daily_brake_amount", 0.0) for s in active_shocks)
        adjusted_daily_limit = max(100.0, base_daily_budget - total_daily_brake)

        return {
            "base_daily_budget": base_daily_budget,
            "total_daily_brake": round(total_daily_brake, 2),
            "adjusted_daily_limit": round(adjusted_daily_limit, 2),
            "active_shock_count": len(active_shocks),
            "status": "RECOVERY_ACTIVE" if total_daily_brake > 0 else "NORMAL"
        }
