"""
Resilient Pocket - Web Dashboard & REST API Server
Serves static HTML/CSS/JS interface and exposes REST API endpoints for real-time finance monitoring.
"""
import os
import sys
import json
import urllib.parse
import http.server
import socketserver
from typing import Dict, Any

# Ensure UTF-8 encoding for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from config import BASE_DIR
from core import ResilientPocket
from telemetry import telemetry, measure_latency

STATIC_DIR = os.path.join(BASE_DIR, "static")
PORT = 8080

copilot = ResilientPocket()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

class ResilientPocketHandler(http.server.SimpleHTTPRequestHandler):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        """Route GET requests to static assets or API endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == "/api/dashboard":
            self.handle_get_dashboard()
        elif path == "/api/chart":
            self.handle_get_chart()
        elif path == "/api/telemetry":
            self.handle_get_telemetry()
        elif path == "/api/assistant/insights":
            self.handle_get_assistant_insights()
        else:
            super().do_GET()

    def do_POST(self):
        """Route POST requests to API endpoints."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/transactions":
            self.handle_add_transaction(payload)
        elif path == "/api/shocks/recover":
            self.handle_shock_recover(payload)
        elif path == "/api/tagger/predict":
            self.handle_tagger_predict(payload)
        elif path == "/api/ledger/clear":
            self.handle_clear_ledger(payload)
        elif path == "/api/ledger/seed":
            self.handle_seed_ledger(payload)
        elif path == "/api/profile/update":
            self.handle_update_profile(payload)
        elif path == "/api/assistant/ask":
            self.handle_assistant_ask(payload)
        elif path == "/api/savings/goals":
            self.handle_update_savings_goal(payload)
        elif path == "/api/reminder/dismiss":
            self.handle_dismiss_reminder(payload)
        else:
            self.send_error(404, "Endpoint Not Found")

    def _send_json(self, data: Dict[str, Any], status: int = 200):
        """Helper to send JSON response with standard headers."""
        body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    @measure_latency("api_get_dashboard")
    def handle_get_dashboard(self):
        """GET /api/dashboard - Complete real-time dashboard summary."""
        dashboard_data = copilot.get_dashboard_summary()
        self._send_json(dashboard_data)

    @measure_latency("api_get_assistant_insights")
    def handle_get_assistant_insights(self):
        """GET /api/assistant/insights - Proactive AI recommendations."""
        dashboard_data = copilot.get_dashboard_summary()
        insights = copilot.assistant_engine.generate_proactive_insights(dashboard_data)
        self._send_json({"insights": insights})

    @measure_latency("api_assistant_ask")
    def handle_assistant_ask(self, payload: Dict[str, Any]):
        """POST /api/assistant/ask - Chat interaction with AI Copilot."""
        query = payload.get("query", "").strip()
        if not query:
            self._send_json({"error": "Empty query"}, 400)
            return

        res = copilot.ask_assistant(query)
        self._send_json(res)

    @measure_latency("api_update_savings_goal")
    def handle_update_savings_goal(self, payload: Dict[str, Any]):
        """POST /api/savings/goals - Update savings goal target & current amounts."""
        target = float(payload.get("target_amount", 50000.0))
        current = float(payload.get("current_amount", 10000.0))
        dashboard = copilot.update_savings_goal(target_amount=target, current_amount=current)
        self._send_json({"status": "UPDATED", "dashboard": dashboard})

    @measure_latency("api_dismiss_reminder")
    def handle_dismiss_reminder(self, payload: Dict[str, Any]):
        """POST /api/reminder/dismiss - Dismiss daily logging reminder."""
        copilot.db.dismiss_reminder()
        dashboard = copilot.get_dashboard_summary()
        self._send_json({"status": "DISMISSED", "dashboard": dashboard})

    @measure_latency("api_get_chart")
    def handle_get_chart(self):
        """GET /api/chart - Returns generated Matplotlib PNG image binary."""
        from app import generate_visual_chart
        chart_file = os.path.join(BASE_DIR, "runway_forecast.png")
        generate_visual_chart(copilot, chart_file)

        if os.path.exists(chart_file):
            with open(chart_file, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "Chart Image Not Available")

    @measure_latency("api_get_telemetry")
    def handle_get_telemetry(self):
        """GET /api/telemetry - Microsecond timing metrics."""
        summary = telemetry.get_summary()
        self._send_json(summary)

    @measure_latency("api_add_transaction")
    def handle_add_transaction(self, payload: Dict[str, Any]):
        """POST /api/transactions - Add transaction with NLP tagging & shock evaluation."""
        description = payload.get("description", "").strip()
        amount = float(payload.get("amount", 0.0))
        tx_type = payload.get("tx_type", "EXPENSE").upper()
        recovery_days = int(payload.get("recovery_window_days", 15))
        date_str = payload.get("date_str", None)

        if not description or amount <= 0:
            self._send_json({"error": "Invalid description or amount"}, 400)
            return

        res = copilot.record_transaction(
            description=description,
            amount=amount,
            tx_type=tx_type,
            recovery_window_days=recovery_days,
            date_str=date_str
        )
        self._send_json(res, 201)

    @measure_latency("api_clear_ledger")
    def handle_clear_ledger(self, payload: Dict[str, Any]):
        """POST /api/ledger/clear - Delete all transactions to enter real transactions."""
        reset_cushion = payload.get("reset_cushion", 0.0)
        if reset_cushion is not None:
            reset_cushion = float(reset_cushion)
        dashboard = copilot.clear_ledger(reset_cushion=reset_cushion)
        self._send_json({"status": "CLEARED", "dashboard": dashboard})

    @measure_latency("api_seed_ledger")
    def handle_seed_ledger(self, payload: Dict[str, Any]):
        """POST /api/ledger/seed - Re-seed demo dataset."""
        dashboard = copilot.seed_demo_ledger()
        self._send_json({"status": "SEEDED", "dashboard": dashboard})

    @measure_latency("api_update_profile")
    def handle_update_profile(self, payload: Dict[str, Any]):
        """POST /api/profile/update - Update initial liquid cushion, monthly income, & daily target budget."""
        cushion = float(payload.get("current_cushion", 100000.0))
        income = float(payload.get("monthly_income", 60000.0))
        budget = float(payload.get("target_daily_budget", 1500.0))

        dashboard = copilot.update_user_profile(cushion=cushion, monthly_income=income, target_daily_budget=budget)
        self._send_json({"status": "UPDATED", "dashboard": dashboard})

    @measure_latency("api_shock_recover")
    def handle_shock_recover(self, payload: Dict[str, Any]):
        """POST /api/shocks/recover - Re-amortize shock window (7, 15, 30 days)."""
        shock_id = int(payload.get("shock_id", 0))
        recovery_days = int(payload.get("recovery_days", 15))

        res = copilot.apply_shock_recovery(shock_id, recovery_days)
        self._send_json(res)

    @measure_latency("api_tagger_predict")
    def handle_tagger_predict(self, payload: Dict[str, Any]):
        """POST /api/tagger/predict - Real-time NLP tag prediction."""
        text = payload.get("text", "")
        category, confidence = copilot.tagger.predict_category(text)
        self._send_json({"text": text, "category": category, "confidence": confidence})

def run_server(port: int = PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    
    server_address = ("", port)
    try:
        httpd = ReusableTCPServer(server_address, ResilientPocketHandler)
    except OSError:
        port = 8081
        server_address = ("", port)
        httpd = ReusableTCPServer(server_address, ResilientPocketHandler)

    print(f"\n==================================================================")
    print(f"  [SERVER] RESILIENT POCKET WEB DASHBOARD SERVER RUNNING AT:")
    print(f"  http://localhost:{port}")
    print(f"==================================================================\n")
    sys.stdout.flush()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()
