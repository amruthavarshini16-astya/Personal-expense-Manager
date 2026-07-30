"""
Resilient Pocket - Central Co-Pilot Orchestrator
Binds persistence, NLP tagging, OLS runway prediction, capital shock brakes, FSM health state, Budget Intelligence, AI Assistant Layer, and microsecond telemetry.
"""
import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from db import DatabaseManager
from tagger import ZeroDepNLPTagger
from runway import PredictiveRunwayEngine
from shock import CapitalShockEngine
from health import HealthStateMachine
from budget_intelligence import BudgetIntelligenceEngine
from assistant import AIAssistantEngine
from telemetry import telemetry, measure_latency

class ResilientPocket:
    """Production-grade predictive micro-fintech co-pilot orchestrator with AI Assistant layer."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db = DatabaseManager(db_path) if db_path else DatabaseManager()
        self.tagger = ZeroDepNLPTagger()
        self.runway_engine = PredictiveRunwayEngine()
        self.shock_engine = CapitalShockEngine()
        self.health_fsm = HealthStateMachine()
        self.budget_intel_engine = BudgetIntelligenceEngine()
        self.assistant_engine = AIAssistantEngine()

    @measure_latency("core_add_transaction")
    def record_transaction(self, description: str, amount: float, tx_type: str = "EXPENSE", category: Optional[str] = None, recovery_window_days: int = 15, date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Record a transaction with auto NLP tagging, shock assessment, and immediate state update.
        """
        raw_text = description
        predicted_cat, confidence = self.tagger.predict_category(raw_text)
        final_category = category or predicted_cat

        today_str = date_str or datetime.date.today().isoformat()
        
        tx_id = self.db.add_transaction(
            date_str=today_str,
            description=description,
            amount=amount,
            tx_type=tx_type,
            category=final_category,
            raw_text=raw_text
        )

        user_profile = self.db.ensure_user_profile()
        cushion = user_profile["current_cushion"]
        budget = user_profile["target_daily_budget"]

        shock_info = None
        if tx_type == "EXPENSE":
            shock_eval = self.shock_engine.evaluate_transaction(amount, description, cushion, budget)
            if shock_eval:
                brake_info = self.shock_engine.create_amortization_brake(amount, recovery_window_days)
                shock_id = self.db.add_shock_event(
                    transaction_id=tx_id,
                    date_str=today_str,
                    description=description,
                    shock_amount=amount,
                    impact_pct=shock_eval["impact_pct"],
                    recovery_days=brake_info["recovery_days"],
                    daily_brake_amount=brake_info["daily_brake_amount"]
                )
                shock_info = {**shock_eval, **brake_info, "shock_id": shock_id}

        dashboard_summary = self.get_dashboard_summary()

        return {
            "transaction_id": tx_id,
            "category": final_category,
            "confidence": confidence,
            "cushion_after": cushion,
            "shock_detected": shock_info is not None,
            "shock_info": shock_info,
            "dashboard_summary": dashboard_summary
        }

    @measure_latency("core_ask_assistant")
    def ask_assistant(self, query_text: str) -> Dict[str, Any]:
        """Ask natural language financial question to AI Assistant engine."""
        dashboard = self.get_dashboard_summary()
        response = self.assistant_engine.process_query(query_text, dashboard)
        
        self.db.save_assistant_message(
            query=query_text,
            answer=response["answer"],
            intent=response.get("intent", "GENERAL_SUMMARY"),
            trigger_info=response.get("explanation", {}).get("trigger", "")
        )
        return response

    @measure_latency("core_clear_ledger")
    def clear_ledger(self, reset_cushion: Optional[float] = None) -> Dict[str, Any]:
        """Clear all transactions and reset SQLite ledger for real transaction entry."""
        self.db.clear_all_transactions(reset_cushion=reset_cushion)
        return self.get_dashboard_summary()

    @measure_latency("core_seed_demo_ledger")
    def seed_demo_ledger(self) -> Dict[str, Any]:
        """Re-seed 45 days of demo transaction history."""
        self.db.seed_demo_data(force=True)
        return self.get_dashboard_summary()

    @measure_latency("core_update_profile")
    def update_user_profile(self, cushion: float, monthly_income: float, target_daily_budget: float) -> Dict[str, Any]:
        """Update initial liquid cushion balance, monthly income, and daily target budget."""
        self.db.update_profile(current_cushion=cushion, monthly_income=monthly_income, target_daily_budget=target_daily_budget)
        return self.get_dashboard_summary()

    @measure_latency("core_update_savings_goal")
    def update_savings_goal(self, target_amount: float, current_amount: float) -> Dict[str, Any]:
        """Update savings goal targets."""
        self.db.update_savings_goal(target_amount=target_amount, current_amount=current_amount)
        return self.get_dashboard_summary()

    @measure_latency("core_recover_shock")
    def apply_shock_recovery(self, shock_id: int, recovery_days: int) -> Dict[str, Any]:
        """Recalculate shock amortization brake for a specific recovery period (7, 15, 30 days)."""
        active_shocks = self.db.get_active_shocks()
        target_shock = next((s for s in active_shocks if s["id"] == shock_id), None)
        
        if not target_shock:
            return {"error": f"Active shock ID {shock_id} not found."}

        new_brake = self.shock_engine.create_amortization_brake(target_shock["shock_amount"], recovery_days)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE shock_events
                SET recovery_days = ?, daily_brake_amount = ?
                WHERE id = ?;
            """, (new_brake["recovery_days"], new_brake["daily_brake_amount"], shock_id))
            conn.commit()

        return {
            "status": "SUCCESS",
            "shock_id": shock_id,
            "new_recovery_days": recovery_days,
            "new_daily_brake": new_brake["daily_brake_amount"],
            "explanation": new_brake["explanation"]
        }

    @measure_latency("core_get_dashboard")
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        Get complete real-time dashboard data including OLS forecast, health state, active shocks, budget intelligence, AI insights, daily logging status, and telemetry.
        """
        profile = self.db.ensure_user_profile()
        savings_goal = self.db.ensure_default_savings_goal()
        daily_status = self.db.check_daily_logging_status()

        cushion = profile["current_cushion"]
        monthly_income = profile["monthly_income"]
        target_daily_budget = profile["target_daily_budget"]

        transactions = self.db.get_all_transactions()
        active_shocks = self.db.get_active_shocks()

        total_daily_brake = sum(s["daily_brake_amount"] for s in active_shocks)
        spending_limit_data = self.shock_engine.recalculate_spending_limit(target_daily_budget, active_shocks)

        if transactions:
            df = pd.DataFrame(transactions)
            df_expenses = df[df["tx_type"] == "EXPENSE"].copy()
            if not df_expenses.empty:
                daily_totals = df_expenses.groupby("date")["amount"].sum().tolist()
                daily_arr = np.array(daily_totals)
                spending_volatility = float(np.std(daily_arr) / np.mean(daily_arr)) if np.mean(daily_arr) > 0 else 0.1
            else:
                daily_totals = [1200.0]
                spending_volatility = 0.1
        else:
            daily_totals = []
            spending_volatility = 0.1

        # 1. Run OLS Runway Engine
        runway_forecast = self.runway_engine.fit_and_predict(daily_totals, cushion, total_daily_brake)

        # 2. Financial Health FSM State
        health_summary = self.health_fsm.compute_health_score(
            current_cushion=cushion,
            monthly_income=monthly_income,
            runway_days=runway_forecast["runway_days"],
            active_shocks=active_shocks,
            spending_volatility=spending_volatility
        )

        # 3. Budget Intelligence Engine
        budget_intel = self.budget_intel_engine.analyze_budget_intelligence(
            current_cushion=cushion,
            monthly_income=monthly_income,
            target_daily_budget=target_daily_budget,
            runway_days=runway_forecast["runway_days"],
            daily_burn_rate=runway_forecast["effective_daily_burn"],
            active_brake=total_daily_brake,
            transactions=transactions,
            savings_goal_target=savings_goal["target_amount"],
            savings_goal_current=savings_goal["current_amount"]
        )

        temp_data = {
            "current_cushion": cushion,
            "runway": runway_forecast,
            "health": health_summary,
            "active_shocks": active_shocks,
            "budget_intel": budget_intel
        }

        # 4. Generate Proactive AI Insights
        ai_insights = self.assistant_engine.generate_proactive_insights(temp_data)

        # 5. Save Runway Snapshot
        self.db.save_runway_snapshot(
            cushion=cushion,
            daily_burn=runway_forecast["effective_daily_burn"],
            runway_days=runway_forecast["runway_days"],
            exhaustion_date=runway_forecast["exhaustion_date"],
            health_score=health_summary["score"],
            health_state=health_summary["state"]
        )

        telemetry_summary = telemetry.get_summary()

        return {
            "profile": profile,
            "savings_goal": savings_goal,
            "daily_status": daily_status,
            "current_cushion": round(cushion, 2),
            "spending_limits": spending_limit_data,
            "runway": runway_forecast,
            "health": health_summary,
            "budget_intel": budget_intel,
            "ai_insights": ai_insights,
            "assistant_history": self.db.get_assistant_history(5),
            "active_shocks": active_shocks,
            "recent_transactions": transactions[-15:] if transactions else [],
            "total_transaction_count": len(transactions),
            "telemetry": telemetry_summary
        }
