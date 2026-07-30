"""
Resilient Pocket - Predictive Financial Runway Engine
Implements Ordinary Least Squares (OLS) Linear Regression from scratch using pure NumPy math.
No heavy machine learning packages used.
"""
import datetime
import numpy as np
from typing import Dict, Any, List
from telemetry import measure_latency

class PredictiveRunwayEngine:
    """Predictive Financial Runway Engine powered by raw NumPy OLS Linear Regression."""

    @measure_latency("ols_runway_forecast")
    def fit_and_predict(self, daily_expenditures: List[float], current_cushion: float, active_daily_brake: float = 0.0) -> Dict[str, Any]:
        """
        Fit OLS regression on historical daily spending and project runway remaining.
        
        Math Explanation:
        - X matrix: [1, t] where t is time step index (0..N-1)
        - Y vector: Daily expense values
        - Beta = (X^T * X)^(-1) * X^T * Y
        - Slope (m) = daily burn rate trend
        - Intercept (c) = baseline spending level
        - R^2 = 1 - (SS_res / SS_tot)
        """
        n = len(daily_expenditures)
        if n == 0:
            # Fallback for empty history
            avg_burn = 1500.0
            total_burn = avg_burn + active_daily_brake
            runway_days = int(current_cushion / total_burn) if total_burn > 0 else 999
            exhaustion = (datetime.date.today() + datetime.timedelta(days=runway_days)).isoformat()
            return {
                "daily_burn_rate": avg_burn,
                "active_daily_brake": active_daily_brake,
                "effective_daily_burn": total_burn,
                "runway_days": runway_days,
                "exhaustion_date": exhaustion,
                "slope": 0.0,
                "intercept": avg_burn,
                "r_squared": 0.0,
                "explanation": "No transaction history available. Default baseline burn rate applied."
            }

        if n == 1:
            avg_burn = max(100.0, daily_expenditures[0])
            total_burn = avg_burn + active_daily_brake
            runway_days = int(current_cushion / total_burn)
            exhaustion = (datetime.date.today() + datetime.timedelta(days=runway_days)).isoformat()
            return {
                "daily_burn_rate": avg_burn,
                "active_daily_brake": active_daily_brake,
                "effective_daily_burn": total_burn,
                "runway_days": runway_days,
                "exhaustion_date": exhaustion,
                "slope": 0.0,
                "intercept": avg_burn,
                "r_squared": 1.0,
                "explanation": "Single data point baseline projection."
            }

        # Construct Design Matrix X and Target Y
        X = np.column_stack((np.ones(n), np.arange(n, dtype=float)))
        Y = np.array(daily_expenditures, dtype=float)

        # OLS Formula: Beta = (X^T * X)^(-1) * X^T * Y
        try:
            XtX = np.dot(X.T, X)
            XtY = np.dot(X.T, Y)
            Beta = np.linalg.solve(XtX, XtY)
            intercept, slope = Beta[0], Beta[1]
        except np.linalg.LinAlgError:
            # Singular matrix fallback to simple mean
            intercept = float(np.mean(Y))
            slope = 0.0

        # Fitted values & Model Quality Metrics
        Y_pred = np.dot(X, Beta) if 'Beta' in locals() else np.full(n, intercept)
        ss_res = np.sum((Y - Y_pred) ** 2)
        ss_tot = np.sum((Y - np.mean(Y)) ** 2)
        r_squared = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 1.0
        r_squared = max(0.0, min(1.0, r_squared))

        # Mean historical burn rate & OLS projected burn rate
        avg_historical_burn = float(np.mean(Y))
        # Projected burn for upcoming period (using baseline + slope offset)
        ols_projected_burn = max(100.0, intercept + slope * (n - 1))

        # Blended resilient daily burn rate (weighted 70% average, 30% slope trend)
        blended_burn_rate = round(0.70 * avg_historical_burn + 0.30 * ols_projected_burn, 2)
        effective_daily_burn = round(blended_burn_rate + active_daily_brake, 2)

        # Calculate Runway Remaining
        if effective_daily_burn <= 0:
            runway_days = 9999
            exhaustion_date = "Indefinite (Surplus Net Flow)"
        else:
            runway_days = int(current_cushion / effective_daily_burn)
            runway_days = max(0, runway_days)
            exhaustion_date = (datetime.date.today() + datetime.timedelta(days=runway_days)).isoformat()

        explanation = (
            f"OLS Fit: y = {round(slope, 4)}*t + {round(intercept, 2)} (R²={round(r_squared, 4)}). "
            f"Historical Avg Burn: ${round(avg_historical_burn, 2)}/day. "
            f"Active Shock Brake: +${round(active_daily_brake, 2)}/day. "
            f"Effective Daily Burn: ${effective_daily_burn}/day."
        )

        return {
            "daily_burn_rate": blended_burn_rate,
            "active_daily_brake": round(active_daily_brake, 2),
            "effective_daily_burn": effective_daily_burn,
            "runway_days": runway_days,
            "exhaustion_date": exhaustion_date,
            "slope": round(float(slope), 4),
            "intercept": round(float(intercept), 2),
            "r_squared": round(float(r_squared), 4),
            "avg_historical_burn": round(avg_historical_burn, 2),
            "explanation": explanation
        }
