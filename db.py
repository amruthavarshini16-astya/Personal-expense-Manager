"""
Resilient Pocket - Database Persistence Layer Module
Manages SQLite database initialization, transactions, shocks, snapshots, user profiles, and clearing for Real Money mode.
"""
import sqlite3
import datetime
import os
from typing import Dict, List, Any, Optional
from config import DB_PATH, DEFAULT_PROFILE
from telemetry import measure_latency

class DatabaseManager:
    """Manages SQLite database connections and operations for Resilient Pocket."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT DEFAULT 'Alex Vance',
                    initial_balance REAL DEFAULT 150000.0,
                    current_cushion REAL DEFAULT 150000.0,
                    monthly_income REAL DEFAULT 85000.0,
                    target_daily_budget REAL DEFAULT 1800.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    tx_type TEXT CHECK(tx_type IN ('EXPENSE', 'INCOME')) NOT NULL,
                    category TEXT NOT NULL,
                    raw_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shock_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id INTEGER,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    shock_amount REAL NOT NULL,
                    impact_pct REAL NOT NULL,
                    recovery_days INTEGER DEFAULT 15,
                    daily_brake_amount REAL DEFAULT 0.0,
                    status TEXT CHECK(status IN ('ACTIVE', 'RESOLVED')) DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(transaction_id) REFERENCES transactions(id)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runway_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_date TEXT DEFAULT '',
                    current_cushion REAL NOT NULL,
                    daily_burn_rate REAL NOT NULL,
                    runway_days INTEGER NOT NULL,
                    exhaustion_date TEXT,
                    health_score REAL,
                    health_state TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_dismissed_date TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT 'Emergency Rainy-Day Reserve',
                    target_amount REAL DEFAULT 50000.0,
                    current_amount REAL DEFAULT 18500.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assistant_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    trigger_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()
            self.ensure_user_profile()
            self.ensure_default_savings_goal()
            self.ensure_user_preferences()

    def ensure_user_profile(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_profile LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO user_profile (name, initial_balance, current_cushion, monthly_income, target_daily_budget)
                    VALUES (?, ?, ?, ?, ?);
                """, (
                    DEFAULT_PROFILE["name"],
                    DEFAULT_PROFILE["initial_balance"],
                    DEFAULT_PROFILE["current_cushion"],
                    DEFAULT_PROFILE["monthly_income"],
                    DEFAULT_PROFILE["target_daily_budget"]
                ))
                conn.commit()
                cursor.execute("SELECT * FROM user_profile LIMIT 1;")
                row = cursor.fetchone()
            return dict(row)

    def ensure_default_savings_goal(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM savings_goals LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                    INSERT INTO savings_goals (title, target_amount, current_amount)
                    VALUES ('Emergency Rainy-Day Reserve', 50000.0, 18500.0);
                """)
                conn.commit()
                cursor.execute("SELECT * FROM savings_goals LIMIT 1;")
                row = cursor.fetchone()
            return dict(row)

    def ensure_user_preferences(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_preferences LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                cursor.execute("INSERT INTO user_preferences (last_dismissed_date) VALUES ('');")
                conn.commit()
                cursor.execute("SELECT * FROM user_preferences LIMIT 1;")
                row = cursor.fetchone()
            return dict(row)

    def check_daily_logging_status(self) -> Dict[str, Any]:
        today = datetime.date.today()
        today_str = today.isoformat()
        yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM transactions WHERE date = ?;", (today_str,))
            logged_today = cursor.fetchone()["cnt"] > 0

            cursor.execute("SELECT COUNT(*) as cnt FROM transactions WHERE date = ?;", (yesterday_str,))
            logged_yesterday = cursor.fetchone()["cnt"] > 0

            cursor.execute("SELECT date FROM transactions ORDER BY date DESC LIMIT 1;")
            last_row = cursor.fetchone()
            
            if last_row:
                last_date = datetime.date.fromisoformat(last_row["date"])
                days_since = (today - last_date).days
            else:
                days_since = 0

            prefs = self.ensure_user_preferences()

        needs_reminder = False
        reminder_prompt = ""

        if not logged_today and days_since >= 1:
            needs_reminder = True
            if days_since == 1:
                reminder_prompt = "🌅 Good Morning! You haven't logged yesterday's spending yet. Did you make any purchases yesterday?"
            else:
                reminder_prompt = f"⏰ Daily Reminder: You haven't logged expenses for {days_since} days! Keep your runway prediction accurate by logging today."

        return {
            "logged_today": logged_today,
            "logged_yesterday": logged_yesterday,
            "days_since_last_tx": days_since,
            "needs_reminder": needs_reminder,
            "reminder_prompt": reminder_prompt,
            "last_dismissed_date": prefs.get("last_dismissed_date", "")
        }

    @measure_latency("db_dismiss_reminder")
    def dismiss_reminder(self) -> None:
        today_str = datetime.date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE user_preferences SET last_dismissed_date = ? WHERE id = 1;", (today_str,))
            conn.commit()

    @measure_latency("db_update_profile")
    def update_profile(self, current_cushion: float, monthly_income: float, target_daily_budget: float) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_profile
                SET current_cushion = ?, monthly_income = ?, target_daily_budget = ?
                WHERE id = 1;
            """, (current_cushion, monthly_income, target_daily_budget))
            conn.commit()
        return self.ensure_user_profile()

    @measure_latency("db_update_savings_goal")
    def update_savings_goal(self, target_amount: float, current_amount: float) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE savings_goals
                SET target_amount = ?, current_amount = ?
                WHERE id = 1;
            """, (target_amount, current_amount))
            conn.commit()
        return self.ensure_default_savings_goal()

    @measure_latency("db_save_assistant_message")
    def save_assistant_message(self, query: str, answer: str, intent: str, trigger_info: str = "") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO assistant_messages (query, answer, intent, trigger_info)
                VALUES (?, ?, ?, ?);
            """, (query, answer, intent, trigger_info))
            conn.commit()
            return cursor.lastrowid

    @measure_latency("db_get_assistant_history")
    def get_assistant_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assistant_messages ORDER BY id DESC LIMIT ?;", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    @measure_latency("db_add_transaction")
    def add_transaction(self, date_str: str, description: str, amount: float, tx_type: str, category: str, raw_text: str = "") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions (date, description, amount, tx_type, category, raw_text)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (date_str, description, amount, tx_type, category, raw_text or description))
            tx_id = cursor.lastrowid
            
            delta = amount if tx_type == "INCOME" else -amount
            cursor.execute("UPDATE user_profile SET current_cushion = current_cushion + ? WHERE id = 1;", (delta,))
            conn.commit()
            return tx_id

    @measure_latency("db_get_transactions")
    def get_all_transactions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transactions ORDER BY date ASC, id ASC;")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @measure_latency("db_clear_all_transactions")
    def clear_all_transactions(self, reset_cushion: Optional[float] = 0.0) -> None:
        cushion_val = reset_cushion if reset_cushion is not None else 0.0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions;")
            cursor.execute("DELETE FROM shock_events;")
            cursor.execute("DELETE FROM runway_snapshots;")
            cursor.execute("DELETE FROM assistant_messages;")
            cursor.execute("UPDATE user_profile SET current_cushion = ?, monthly_income = 0.0, target_daily_budget = 0.0 WHERE id = 1;", (cushion_val,))
            conn.commit()

    @measure_latency("db_add_shock_event")
    def add_shock_event(self, transaction_id: Optional[int], date_str: str, description: str, shock_amount: float, impact_pct: float, recovery_days: int, daily_brake_amount: float) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO shock_events (transaction_id, date, description, shock_amount, impact_pct, recovery_days, daily_brake_amount, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE');
            """, (transaction_id, date_str, description, shock_amount, impact_pct, recovery_days, daily_brake_amount))
            conn.commit()
            return cursor.lastrowid

    @measure_latency("db_get_active_shocks")
    def get_active_shocks(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM shock_events WHERE status = 'ACTIVE' ORDER BY date DESC;")
            return [dict(r) for r in cursor.fetchall()]

    @measure_latency("db_resolve_shock")
    def resolve_shock(self, shock_id: int) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE shock_events SET status = 'RESOLVED' WHERE id = ?;", (shock_id,))
            conn.commit()

    @measure_latency("db_save_runway_snapshot")
    def save_runway_snapshot(self, cushion: float, daily_burn: float, runway_days: int, exhaustion_date: str, health_score: float, health_state: str) -> int:
        today_str = datetime.date.today().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO runway_snapshots (snapshot_date, current_cushion, daily_burn_rate, runway_days, exhaustion_date, health_score, health_state)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (today_str, cushion, daily_burn, runway_days, exhaustion_date, health_score, health_state))
            conn.commit()
            return cursor.lastrowid

    @measure_latency("db_seed_demo_data")
    def seed_demo_data(self, force: bool = False) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM transactions;")
            cnt = cursor.fetchone()["cnt"]
            
            if cnt > 0 and not force:
                return

            cursor.execute("DELETE FROM transactions;")
            cursor.execute("DELETE FROM shock_events;")
            cursor.execute("DELETE FROM runway_snapshots;")

            base_cushion = 150000.0
            cursor.execute("""
                UPDATE user_profile
                SET current_cushion = ?, monthly_income = 85000.0, target_daily_budget = 1800.0
                WHERE id = 1;
            """, (base_cushion,))

            today = datetime.date.today()
            demo_txs = [
                ( (today - datetime.timedelta(days=42)).isoformat(), "Monthly Salary Direct Deposit", 85000.0, "INCOME", "Income", "salary" ),
                ( (today - datetime.timedelta(days=40)).isoformat(), "House Rent Payment", 25000.0, "EXPENSE", "Bills", "rent" ),
                ( (today - datetime.timedelta(days=38)).isoformat(), "Supermarket Groceries & Curd", 4200.0, "EXPENSE", "Food", "groceries curd" ),
                ( (today - datetime.timedelta(days=35)).isoformat(), "Swiggy Biryani Order", 850.0, "EXPENSE", "Food", "swiggy biryani" ),
                ( (today - datetime.timedelta(days=32)).isoformat(), "Uber Taxi Ride", 450.0, "EXPENSE", "Travel", "uber taxi" ),
                ( (today - datetime.timedelta(days=28)).isoformat(), "Electricity & Utility Bill", 2400.0, "EXPENSE", "Bills", "electricity bill" ),
                ( (today - datetime.timedelta(days=25)).isoformat(), "Curd Rice & Snacks", 320.0, "EXPENSE", "Food", "curd rice lays" ),
                ( (today - datetime.timedelta(days=20)).isoformat(), "Emergency Hardware Laptop Repair", 15000.0, "EXPENSE", "Shopping", "laptop repair" ),
                ( (today - datetime.timedelta(days=15)).isoformat(), "Amazon Electronics Purchase", 5600.0, "EXPENSE", "Shopping", "amazon electronics" ),
                ( (today - datetime.timedelta(days=12)).isoformat(), "Lays Chips & Munchies", 120.0, "EXPENSE", "Food", "lays chips" ),
                ( (today - datetime.timedelta(days=8)).isoformat(), "Apollo Pharmacy Medicine", 680.0, "EXPENSE", "Health", "pharmacy" ),
                ( (today - datetime.timedelta(days=4)).isoformat(), "Swiggy Dinner Order", 920.0, "EXPENSE", "Food", "swiggy dinner" ),
                ( (today - datetime.timedelta(days=1)).isoformat(), "Curd & Dairy Grocery", 180.0, "EXPENSE", "Food", "curd dairy" )
            ]

            cushion_acc = base_cushion
            for date_s, desc, amt, t_type, cat, raw_t in demo_txs:
                cursor.execute("""
                    INSERT INTO transactions (date, description, amount, tx_type, category, raw_text)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (date_s, desc, amt, t_type, cat, raw_t))
                if t_type == "INCOME":
                    cushion_acc += amt
                else:
                    cushion_acc -= amt

            cursor.execute("UPDATE user_profile SET current_cushion = ? WHERE id = 1;", (cushion_acc,))

            shock_tx_id = 8
            shock_amt = 15000.0
            impact = round((shock_amt / base_cushion) * 100, 1)
            brake = round(shock_amt / 15.0, 2)
            cursor.execute("""
                INSERT INTO shock_events (transaction_id, date, description, shock_amount, impact_pct, recovery_days, daily_brake_amount, status)
                VALUES (?, ?, 'Emergency Hardware Laptop Repair', ?, ?, 15, ?, 'ACTIVE');
            """, (shock_tx_id, (today - datetime.timedelta(days=20)).isoformat(), shock_amt, impact, brake))

            conn.commit()
