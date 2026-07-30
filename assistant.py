"""
Resilient Pocket - Intelligent AI Assistant Layer
Natural language financial copilot providing friendly, supportive, and explainable recommendations.
"""
import re
from typing import Dict, Any, List, Tuple
from telemetry import measure_latency

class AIAssistantEngine:
    """Intelligent AI Assistant engine providing friendly, encouraging, and data-driven recommendations."""

    @measure_latency("assistant_process_query")
    def process_query(self, query_text: str, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process natural language queries with friendly, supportive financial coaching.
        """
        query_lower = query_text.lower().strip()
        
        cushion = dashboard_data.get("current_cushion", 0.0)
        runway_days = dashboard_data.get("runway", {}).get("runway_days", 0)
        daily_burn = dashboard_data.get("runway", {}).get("effective_daily_burn", 1000.0)
        health_state = dashboard_data.get("health", {}).get("state", "Steady")
        health_score = dashboard_data.get("health", {}).get("score", 70.0)
        shocks = dashboard_data.get("active_shocks", [])

        # Intent 1: "Can I afford X?" / "Can I buy X?"
        afford_match = re.search(r"(?:can i afford|can i buy|should i buy|buy|afford)\s*(?:₹|\$)?\s*([0-9,]+(?:\.[0-9]+)?)", query_lower)
        if afford_match or any(w in query_lower for w in ["afford", "buy", "purchase"]):
            amount = float(afford_match.group(1).replace(",", "")) if afford_match else 5000.0
            return self._handle_affordability_query(amount, query_text, cushion, runway_days, daily_burn, shocks)

        # Intent 2: "Where can I cut expenses?" / "How to save?"
        if any(w in query_lower for w in ["cut", "save", "spending", "reduce", "budget", "tips"]):
            return self._handle_savings_query(dashboard_data)

        # Intent 3: "Why is my health score X?" / "Flower pot"
        if any(w in query_lower for w in ["health", "score", "drooping", "critical", "thriving", "steady", "flower", "pot"]):
            return self._handle_health_query(health_score, health_state, dashboard_data)

        # Intent 4: "How long will my cash last?" / "Runway"
        if any(w in query_lower for w in ["runway", "last", "days", "exhaustion", "burn"]):
            return self._handle_runway_query(runway_days, daily_burn, cushion, dashboard_data)

        # Intent 5: "Shock recovery"
        if any(w in query_lower for w in ["shock", "emergency", "repair", "brake", "recover"]):
            return self._handle_shock_query(shocks, dashboard_data)

        # Default friendly & encouraging financial summary
        return {
            "query": query_text,
            "intent": "GENERAL_SUMMARY",
            "answer": (
                f"Hey there! 👋 I'm your AI Cash Copilot. Here is your quick financial status check:\n\n"
                f"• **Available Cash Cushion**: ₹{cushion:,.2f}\n"
                f"• **Predictive Cash Horizon**: {runway_days} Days remaining at ₹{daily_burn:,.2f}/day burn\n"
                f"• **Financial Garden Mood**: {health_state} ({health_score}/100 🌸)\n\n"
                f"💡 *Ask me anything like:* 'Can I buy a ₹15,000 gadget today?' or 'Give me 3 quick tips to save money!'"
            ),
            "explanation": {
                "trigger": "Friendly status overview",
                "data_point": f"Cushion: ₹{cushion:,.2f} | Horizon: {runway_days} Days",
                "next_action": "Try asking 'Can I afford ₹5,000?' for personalized spending advice!"
            }
        }

    def _handle_affordability_query(self, amount: float, item_name: str, cushion: float, runway_days: int, daily_burn: float, shocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate affordability with friendly, empathetic, and encouraging advice."""
        cushion_after = cushion - amount
        new_runway = int(cushion_after / max(100.0, daily_burn)) if daily_burn > 0 else 99
        days_lost = max(0, runway_days - new_runway)

        is_affordable = (amount < cushion * 0.15) and (new_runway >= 45) and len(shocks) == 0

        if is_affordable:
            verdict = "YES, AFFORDABLE 🎉"
            answer = (
                f"🎉 **Great news! You can safely afford this purchase of ₹{amount:,.2f}!**\n\n"
                f"Here is what happens to your cash safety net:\n"
                f"• **Post-Purchase Cushion**: ₹{cushion_after:,.2f}\n"
                f"• **Impact on Runway**: Reduces horizon by only {days_lost} days (leaving a strong **{new_runway} days** reserve!)\n\n"
                f"✨ *Copilot Tip:* Your financial garden will stay in full bloom 🌸. Enjoy your purchase responsibly!"
            )
        else:
            verdict = "CAUTION / SMART WAIT RECOMMENDED 🛡️"
            answer = (
                f"🛡️ **Friendly Advice: It's best to wait before spending ₹{amount:,.2f}.**\n\n"
                f"Here is why your Copilot recommends waiting:\n"
                f"• It consumes **{round((amount/max(1.0, cushion))*100, 1)}%** of your cash cushion.\n"
                f"• Your cash runway would drop from **{runway_days} days down to {new_runway} days** ({days_lost} days lost).\n\n"
                f"💡 *Smart Alternative:* If you wait just **10-14 days** or trim ₹500/day from food delivery, your cushion will naturally recover so you can buy it without risking your runway!"
            )

        return {
            "query": item_name,
            "intent": "AFFORDABILITY_CHECK",
            "verdict": verdict,
            "answer": answer,
            "explanation": {
                "trigger": f"Purchase request of ₹{amount:,.2f}",
                "data_point": f"Cushion: ₹{cushion:,.2f} -> ₹{cushion_after:,.2f} (Runway: {new_runway} days)",
                "next_action": "Wait 10-14 days or amortize the expense over 15 days to keep your runway safe."
            }
        }

    def _handle_savings_query(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate friendly category-level budget optimization advice."""
        budget_intel = dashboard_data.get("budget_intel", {})
        cuts = budget_intel.get("category_cuts", [])
        
        if cuts:
            top_cut = cuts[0]
            answer = (
                f"💡 **Here are 3 Friendly Copilot Tips to Boost Your Cash Cushion!**\n\n"
                f"1. **Optimize {top_cut['category']} Spending**:\n"
                f"   Your highest discretionary spending is in **{top_cut['category']}** (₹{top_cut['spent']:,.2f}, {top_cut['spent_pct']}% of total).\n"
                f"   • *Small Change:* Trimming 25% saves **₹{top_cut['recommended_cut']:,.2f}/month**!\n"
                f"2. **Enable 15-Day Amortization**: Use the Shock Recovery tab when unplanned bills arrive to keep your daily budget steady.\n"
                f"3. **Track Daily Spending**: Confirm your zero-expense days using the daily reminder banner to keep predictions 100% accurate!"
            )
            trigger_text = f"High spending in {top_cut['category']} ({top_cut['spent_pct']}% of total)"
            data_point_text = f"Spent: ₹{top_cut['spent']:,.2f} | Potential Savings: ₹{top_cut['recommended_cut']:,.2f}/mo"
        else:
            answer = (
                f"🌟 **Awesome job! Your spending is super balanced across all categories.**\n\n"
                f"No single category exceeds discretionary limits. Keep up the great financial habits!"
            )
            trigger_text = "Balanced category distribution"
            data_point_text = "No category exceeds discretionary threshold"

        return {
            "query": "Where can I cut spending?",
            "intent": "BUDGET_OPTIMIZATION",
            "answer": answer,
            "explanation": {
                "trigger": trigger_text,
                "data_point": data_point_text,
                "next_action": "Apply recommended category spending cap to extend runway."
            }
        }

    def _handle_health_query(self, score: float, state: str, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Explain living flower pot health state with friendly coaching."""
        health = dashboard_data.get("health", {})
        breakdown = health.get("breakdown", {})
        
        answer = (
            f"🌸 **Your Living Flower Pot Health: {state} ({score}/100)**\n\n"
            f"Here is how your financial garden score is calculated:\n"
            f"• **Reserve Cushion Score**: {breakdown.get('cushion_score', 0)} / 35 pts\n"
            f"• **Runway Horizon Score**: {breakdown.get('runway_score', 0)} / 35 pts\n"
            f"• **Emergency Resilience Score**: {breakdown.get('shock_score', 0)} / 15 pts\n"
            f"• **Spending Stability Score**: {breakdown.get('stability_score', 0)} / 15 pts\n\n"
            f"🌱 *Garden Status:* {health.get('action_prompt', '')}"
        )

        return {
            "query": "Why is my health score at this state?",
            "intent": "HEALTH_FSM_EXPLANATION",
            "answer": answer,
            "explanation": {
                "trigger": f"Living Flower Pot in {state} state",
                "data_point": f"Composite Health Score: {score}/100",
                "next_action": health.get("action_prompt", "Maintain spending stability.")
            }
        }

    def _handle_runway_query(self, runway_days: int, daily_burn: float, cushion: float, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Explain cash runway calculations in friendly, encouraging terms."""
        runway = dashboard_data.get("runway", {})
        answer = (
            f"⏱️ **Your Cash Runway Forecast: {runway_days} Days Remaining**\n\n"
            f"At your current average daily burn rate of **₹{daily_burn:,.2f}/day**, your **₹{cushion:,.2f}** liquid cushion will safely last until **{runway.get('exhaustion_date', '--')}**.\n\n"
            f"💡 *Copilot Recommendation:* Trimming just ₹150/day adds **+18 extra days** of buffer to your runway!"
        )

        return {
            "query": "How long will my cash last?",
            "intent": "RUNWAY_EXPLANATION",
            "answer": answer,
            "explanation": {
                "trigger": "Predictive Linear Forecast",
                "data_point": f"Cushion: ₹{cushion:,.2f} / ₹{daily_burn:,.2f} burn/day = {runway_days} Days",
                "next_action": "Reduce daily spending pace by 10% to extend exhaustion by 18 days."
            }
        }

    def _handle_shock_query(self, shocks: List[Dict[str, Any]], dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """Explain shock recovery in friendly, reassuring terms."""
        if shocks:
            s = shocks[0]
            answer = (
                f"🛡️ **Active Emergency Expense Recovery: {s['description']}**\n\n"
                f"Don't worry! Your unplanned emergency bill of **₹{s['shock_amount']:,.2f}** is being safely amortized.\n"
                f"• **Daily Buffer Brake**: Adding **+₹{s['daily_brake_amount']:.2f}/day** over a {s['recovery_days']}-day window.\n"
                f"• *Copilot Advice:* If your daily budget feels tight, click **30 Days** on the Shock Recovery tab to relax your daily brake!"
            )
        else:
            answer = (
                f"✨ **All Clear! No emergency shock deficits active.**\n\n"
                f"Your cash cushion is running smoothly under normal baseline conditions."
            )

        return {
            "query": "How to recover from spending shock?",
            "intent": "SHOCK_RECOVERY",
            "answer": answer,
            "explanation": {
                "trigger": "Active Shock Event evaluation" if shocks else "Normal operations",
                "data_point": f"Active Brake: +₹{shocks[0]['daily_brake_amount']:.2f}/day" if shocks else "No active brake",
                "next_action": "Adjust amortization recovery window (7, 15, 30 days) on the Shock Recovery tab."
            }
        }

    @measure_latency("assistant_proactive_insights")
    def generate_proactive_insights(self, dashboard_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate structured explainable AI recommendations for the dashboard UI."""
        insights = []
        cushion = dashboard_data.get("current_cushion", 0.0)
        runway_days = dashboard_data.get("runway", {}).get("runway_days", 0)
        shocks = dashboard_data.get("active_shocks", [])
        budget_intel = dashboard_data.get("budget_intel", {})

        # Insight 1: Runway Horizon
        if runway_days < 60:
            insights.append({
                "id": "insight_runway_risk",
                "title": "⚠️ Cash Horizon Warning",
                "category": "RUNWAY_RISK",
                "badge": "Action Suggested",
                "suggestion": f"Your runway is down to {runway_days} days. Trimming ₹200/day extends your horizon by 20 days!",
                "explanation": {
                    "trigger": "Runway under 60-day target",
                    "data_point": f"{runway_days} Days remaining (Exhaustion: {dashboard_data.get('runway', {}).get('exhaustion_date')})",
                    "next_action": "Pause non-essential categories for 14 days."
                }
            })

        # Insight 2: Shock Recovery
        if shocks:
            latest = shocks[0]
            insights.append({
                "id": "insight_shock_recovery",
                "title": "🛡️ Emergency Buffer Active",
                "category": "SHOCK_RECOVERY",
                "badge": "Recovery Active",
                "suggestion": f"Spreading ₹{latest['shock_amount']:,.2f} ({latest['description']}) over {latest['recovery_days']} days to protect daily budget.",
                "explanation": {
                    "trigger": f"Emergency shock of ₹{latest['shock_amount']}",
                    "data_point": f"Daily Brake: +₹{latest['daily_brake_amount']:.2f}/day",
                    "next_action": "Switch to 30-day window on Shock Recovery tab to lower daily brake."
                }
            })

        # Insight 3: Category Optimization
        cuts = budget_intel.get("category_cuts", [])
        if cuts:
            top = cuts[0]
            insights.append({
                "id": "insight_category_cut",
                "title": f"💡 Easy Savings in {top['category']}",
                "category": "BUDGET_CUT",
                "badge": "Savings Tip",
                "suggestion": f"Save ₹{top['recommended_cut']:,.2f}/month by trimming {top['category']} expenses by 25%.",
                "explanation": {
                    "trigger": f"{top['category']} accounts for {top['spent_pct']}% of expenses",
                    "data_point": f"Current Spent: ₹{top['spent']:,.2f}",
                    "next_action": "Set daily spending target for dining/shopping."
                }
            })

        # Insight 4: Savings Progress Goal
        goal = budget_intel.get("savings_goal", {})
        if goal:
            insights.append({
                "id": "insight_savings_goal",
                "title": f"🎯 Savings Goal: {goal['progress_pct']}% Achieved",
                "category": "SAVINGS",
                "badge": "Goal Progress",
                "suggestion": f"You have saved ₹{goal['current']:,.2f} towards your ₹{goal['target']:,.2f} goal! Keep going!",
                "explanation": {
                    "trigger": "Savings goal tracker",
                    "data_point": f"Progress: {goal['progress_pct']}%",
                    "next_action": f"Auto-transfer ₹{budget_intel.get('recommended_monthly_savings', 5000):,.2f}/month to reach goal faster."
                }
            })

        return insights
