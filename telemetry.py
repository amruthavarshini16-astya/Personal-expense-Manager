"""
Resilient Pocket - Microsecond System Telemetry Layer
Measures function, database, and prediction latency with time.perf_counter().
"""
import time
import functools
from typing import Callable, Any, Dict, List

class TelemetryTracker:
    """High-precision telemetry tracker for monitoring operational latency in microseconds."""

    def __init__(self) -> None:
        self.metrics_history: List[Dict[str, Any]] = []

    def record(self, operation: str, latency_us: float, details: str = "") -> Dict[str, Any]:
        """Record a telemetry metric entry."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "operation": operation,
            "latency_us": round(latency_us, 2),
            "latency_ms": round(latency_us / 1000.0, 4),
            "details": details
        }
        self.metrics_history.append(entry)
        return entry

    def get_summary(self) -> Dict[str, Any]:
        """Compute aggregated statistics for recorded telemetry operations."""
        if not self.metrics_history:
            return {"total_calls": 0, "avg_latency_us": 0.0, "max_latency_us": 0.0}

        latencies = [m["latency_us"] for m in self.metrics_history]
        return {
            "total_calls": len(latencies),
            "avg_latency_us": round(sum(latencies) / len(latencies), 2),
            "avg_latency_ms": round((sum(latencies) / len(latencies)) / 1000.0, 4),
            "max_latency_us": round(max(latencies), 2),
            "min_latency_us": round(min(latencies), 2),
            "latest_metrics": self.metrics_history[-5:]
        }

# Global singleton telemetry instance
telemetry = TelemetryTracker()

def measure_latency(operation_name: str = None):
    """Decorator to measure function latency in microseconds."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_us = (time.perf_counter() - start_time) * 1_000_000
            op_name = operation_name or func.__name__
            telemetry.record(op_name, elapsed_us)
            return result
        return wrapper
    return decorator
