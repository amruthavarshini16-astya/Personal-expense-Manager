"""
Resilient Pocket - Financial Health & Flower Pot Mood State Machine Module
Evaluates liquid cushion, burn rate, shock deficit, and spending volatility into a 0-100 score.
"""

class HealthStateMachine:
    """
    Evaluates financial health score (0-100) across 4 core pillars:
    1. Reserve Ratio (35%): Available cushion vs 3-month target
    2. Runway Days (35%): Days cash will last (>90 days target)
    3. Shock Deficit Impact (15%): Active shock deficit deduction
    4. Spending Volatility (15%): Volatility index of daily spend
    """

    STATES = {
        "THRIVING": {
            "name": "Blooming Blossom Flower 🌸",
            "emoji": "🌸",
            "svg": "flower-blooming.svg",
            "min_score": 80.0,
            "badge_color": "#10b981",
            "action_prompt": "Blooming Health: Cash reserves are thriving! Your financial garden is in full bloom."
        },
        "STEADY": {
            "name": "Healthy Sunflower 🌻",
            "emoji": "🌻",
            "svg": "flower-healthy.svg",
            "min_score": 60.0,
            "badge_color": "#38bdf8",
            "action_prompt": "Sunny & Stable: Spending velocity is balanced like a sunny garden. Keep nurturing your cushion!"
        },
        "DROOPING": {
            "name": "Drooping Petals 🥀",
            "emoji": "🥀",
            "svg": "flower-drooping.svg",
            "min_score": 40.0,
            "badge_color": "#f59e0b",
            "action_prompt": "Needs Care: Spending is drying up your cushion reserves. Trim extra expenses to perk up!"
        },
        "CRITICAL": {
            "name": "Withered Rescue Alert! 🏜️",
            "emoji": "🏜️",
            "svg": "flower-withered.svg",
            "min_score": 0.0,
            "badge_color": "#ef4444",
            "action_prompt": "Emergency Hydration Required: Cash reserves below 30 days. Emergency spending brake engaged!"
        }
    }

    @classmethod
    def compute_health_score(cls, current_cushion: float = 0.0, effective_daily_burn: float = 0.0,
                             target_daily_budget: float = 0.0, active_shocks: list = None,
                             spending_volatility: float = 0.0, **kwargs) -> dict:
        
        # Support both positional & keyword arguments seamlessly
        cushion = kwargs.get("cushion", current_cushion)
        daily_burn = kwargs.get("daily_burn", effective_daily_burn)
        target_budget = kwargs.get("target_budget", target_daily_budget)
        shocks = active_shocks if active_shocks is not None else kwargs.get("shocks", [])
        std_dev = kwargs.get("std_dev_burn", spending_volatility)

        daily_burn_safe = max(1.0, daily_burn)
        runway_days = cushion / daily_burn_safe

        # Pillar 1: Cushion Ratio (35 pts)
        target_3mo = daily_burn_safe * 90.0
        cushion_ratio = min(1.0, cushion / max(1.0, target_3mo))
        pillar_cushion = cushion_ratio * 35.0

        # Pillar 2: Runway Days (35 pts)
        runway_ratio = min(1.0, runway_days / 90.0)
        pillar_runway = runway_ratio * 35.0

        # Pillar 3: Shock Impact (15 pts)
        total_shock = sum(s.get("shock_amount", 0) for s in shocks)
        shock_ratio = max(0.0, 1.0 - (total_shock / max(1.0, cushion)))
        pillar_shock = shock_ratio * 15.0

        # Pillar 4: Stability (15 pts)
        volatility_ratio = max(0.0, 1.0 - (std_dev / max(1.0, target_budget)))
        pillar_stability = volatility_ratio * 15.0

        total_score = round(pillar_cushion + pillar_runway + pillar_shock + pillar_stability, 1)
        total_score = max(0.0, min(100.0, total_score))

        # Determine State
        if total_score >= 80.0:
            state_key = "THRIVING"
            state_name = "Thriving"
        elif total_score >= 60.0:
            state_key = "STEADY"
            state_name = "Steady"
        elif total_score >= 40.0:
            state_key = "DROOPING"
            state_name = "Drooping"
        else:
            state_key = "CRITICAL"
            state_name = "Critical"

        config = cls.STATES[state_key]

        return {
            "score": total_score,
            "state": state_name,
            "character_name": config["name"],
            "emoji": config["emoji"],
            "svg": config["svg"],
            "badge_color": config["badge_color"],
            "action_prompt": config["action_prompt"],
            "breakdown": {
                "cushion_score": round(pillar_cushion, 1),
                "runway_score": round(pillar_runway, 1),
                "shock_score": round(pillar_shock, 1),
                "stability_score": round(pillar_stability, 1)
            }
        }

    # Alias compute_score
    @classmethod
    def compute_score(cls, *args, **kwargs):
        return cls.compute_health_score(*args, **kwargs)
