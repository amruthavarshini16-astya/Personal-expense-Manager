#!/usr/bin/env python3
"""
================================================================================
AI-Powered Personal Expense Manager -- Oracle Edition
================================================================================
Same ML-driven categorization experience as the original prototype, now
backed by a persistent Oracle database instead of an in-memory pandas
DataFrame. Every read/write goes through `db.OracleDB`; pandas is used
only at the edges (the `ledger` property, CSV import/export, plotting)
so existing frontend / notebook code that expects a DataFrame keeps
working unchanged.

New in this version
--------------------
    - Amortized expenses: high-cost one-time purchases spread evenly
      across a "useful life" in months, dynamically folded into monthly
      totals alongside regular expenses.
    - All ledger data is durable across process restarts.

Architecture
------------
    ExpenseManager
        - owns a fitted TF-IDF + Multinomial Naive Bayes pipeline
        - owns an `OracleDB` handle (dependency-injected, never created
          implicitly, so tests can point at a different schema/pool)
        - exposes the same public method names as the original prototype
          wherever practical, so callers only need to change how the
          manager is constructed, not how it's used.
================================================================================
"""

from __future__ import annotations

import os
import warnings
from datetime import date, datetime, timedelta
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from db import OracleDB

warnings.filterwarnings("ignore")


class ExpenseManager:
    """
    Encapsulates the full expense-tracking workflow: ML-based
    categorization, persistent storage (Oracle), amortization-aware
    reporting, and visualization (matplotlib).

    Parameters
    ----------
    db : OracleDB
        An already-configured database handle. Injected rather than
        constructed here so the same class can point at prod, staging,
        or a test schema without code changes.
    """

    LEDGER_COLUMNS: List[str] = ["Date", "Description", "Amount", "Category"]
    RECURRING_COLUMNS: List[str] = [
        "Name", "Amount", "Category", "Frequency", "NextDueDate", "Active",
    ]

    def __init__(self, db: OracleDB) -> None:
        self.db = db
        # Savings goals are lightweight, session-scoped, and not part of
        # the required schema -- kept in memory as in the original
        # prototype. (Promote to a `savings_goals` table if persistence
        # across restarts becomes a requirement.)
        self.savings_goals: dict = {}
        self.model: Pipeline = self._build_and_train_model()

    # ------------------------------------------------------------------
    # 1. MACHINE LEARNING ENGINE (unchanged from the original prototype)
    # ------------------------------------------------------------------
    @staticmethod
    def _get_training_data() -> tuple[List[str], List[str]]:
        """Seed training dataset for the classifier."""
        training_samples = {
            "Food & Dining": [
                "Dinner at the Italian restaurant downtown",
                "Starbucks coffee and croissant",
                "Lunch with colleagues at Thai place",
                "McDonald's drive-thru order",
                "Sushi takeout for date night",
                "Brunch at the local cafe",
            ],
            "Groceries": [
                "Walmart grocery run for the week",
                "Whole Foods organic vegetables and fruit",
                "Costco bulk shopping trip",
                "Local supermarket milk eggs and bread",
                "Trader Joe's weekly grocery shopping",
                "Butcher shop meat purchase",
            ],
            "Transport": [
                "Uber ride to the airport",
                "Monthly metro train pass",
                "Gas station fuel fill up",
                "Lyft ride home from downtown",
                "Parking garage fee",
                "Car maintenance and oil change",
            ],
            "Entertainment": [
                "Movie tickets at the cinema",
                "Netflix monthly subscription",
                "Concert tickets for the weekend show",
                "Video game purchase on Steam",
                "Bowling night with friends",
                "Spotify premium subscription renewal",
            ],
            "Bills & Utilities": [
                "Electricity bill payment",
                "Monthly internet and wifi bill",
                "Water utility bill payment",
                "Cell phone bill for the month",
                "Rent payment for apartment",
                "Gas utility heating bill",
            ],
        }
        texts: List[str] = []
        labels: List[str] = []
        for category, phrases in training_samples.items():
            texts.extend(phrases)
            labels.extend([category] * len(phrases))
        return texts, labels

    def _build_and_train_model(self) -> Pipeline:
        """Build and fit the TF-IDF + Multinomial Naive Bayes pipeline."""
        texts, labels = self._get_training_data()
        pipeline = Pipeline(
            steps=[
                ("tfidf", TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2))),
                ("classifier", MultinomialNB()),
            ]
        )
        pipeline.fit(texts, labels)
        return pipeline

    def predict_category(self, description: str) -> str:
        """Predict the spending category for a free-text description."""
        if not description or not description.strip():
            return "Uncategorized"
        return str(self.model.predict([description])[0])

    # ------------------------------------------------------------------
    # 2. EXPENSE LEDGER (Oracle-backed)
    # ------------------------------------------------------------------
    def add_expense(
        self,
        date_str: str,
        description: str,
        amount: float,
        category: Optional[str] = None,
    ) -> str:
        """
        Insert a new expense row into the `expenses` table. Category is
        ML-predicted unless explicitly supplied.

        Returns
        -------
        str : the category ultimately assigned.
        """
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid amount: '{amount}'. Must be numeric.")
        if amount <= 0:
            raise ValueError("Amount must be a positive number.")

        assigned_category = category or self.predict_category(description)

        self.db.execute(
            """
            INSERT INTO expenses (expense_date, description, amount, category)
            VALUES (:expense_date, :description, :amount, :category)
            """,
            {
                "expense_date": parsed_date,
                "description": description,
                "amount": amount,
                "category": assigned_category,
            },
        )
        return assigned_category

    @property
    def ledger(self) -> pd.DataFrame:
        """
        Dynamically query the `expenses` table and return it as a pandas
        DataFrame with the same column names the original in-memory
        prototype used, so existing frontend / visualization code that
        expects `manager.ledger` keeps working unmodified.
        """
        rows = self.db.query_dicts(
            "SELECT expense_date, description, amount, category "
            "FROM expenses ORDER BY expense_date, id"
        )
        if not rows:
            return pd.DataFrame(columns=self.LEDGER_COLUMNS)

        df = pd.DataFrame(rows)
        df = df.rename(
            columns={
                "expense_date": "Date",
                "description": "Description",
                "amount": "Amount",
                "category": "Category",
            }
        )
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        return df[self.LEDGER_COLUMNS]

    def get_total_spent(self) -> float:
        """All-time total across every logged expense (amortized purchases
        are NOT included here -- use `get_monthly_spending` for
        amortization-aware totals)."""
        total = self.db.query_scalar("SELECT NVL(SUM(amount), 0) FROM expenses")
        return float(total or 0.0)

    def get_summary_by_category(self) -> pd.Series:
        """All-time spending total per category, descending."""
        rows = self.db.query(
            "SELECT category, SUM(amount) FROM expenses GROUP BY category ORDER BY SUM(amount) DESC"
        )
        if not rows:
            return pd.Series(dtype=float)
        categories, totals = zip(*rows)
        return pd.Series(data=[float(t) for t in totals], index=list(categories))

    # ------------------------------------------------------------------
    # 3. AMORTIZATION (Feature B)
    # ------------------------------------------------------------------
    def add_amortized_expense(
        self,
        description: str,
        total_amount: float,
        category: Optional[str] = None,
        purchase_date: Optional[str] = None,
        duration_months: int = 12,
    ) -> str:
        """
        Record a high-cost, one-time purchase (e.g. a ₹12,000 annual gym
        membership) that should be spread evenly across `duration_months`
        for reporting purposes -- ₹1,000/month for 12 months, in that
        example -- rather than distorting a single month's total.

        This does NOT insert anything into `expenses`; amortized rows are
        folded into monthly totals dynamically by `get_monthly_spending`
        and `get_monthly_summary_by_category`, so the raw ledger stays an
        accurate record of what was actually paid, and when.

        Returns
        -------
        str : the category ultimately assigned.
        """
        total_amount = float(total_amount)
        if total_amount <= 0:
            raise ValueError("Total amount must be a positive number.")
        if duration_months <= 0:
            raise ValueError("Duration must be a positive number of months.")

        try:
            parsed_date = datetime.strptime(
                purchase_date or date.today().strftime("%Y-%m-%d"), "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError(f"Invalid date format: '{purchase_date}'. Expected YYYY-MM-DD.")

        assigned_category = category or self.predict_category(description)
        monthly_installment = round(total_amount / duration_months, 2)

        self.db.execute(
            """
            INSERT INTO amortized_expenses
                (description, total_amount, category, purchase_date,
                 duration_months, monthly_installment)
            VALUES
                (:description, :total_amount, :category, :purchase_date,
                 :duration_months, :monthly_installment)
            """,
            {
                "description": description,
                "total_amount": total_amount,
                "category": assigned_category,
                "purchase_date": parsed_date,
                "duration_months": duration_months,
                "monthly_installment": monthly_installment,
            },
        )
        return assigned_category

    def _amortized_installments_for_month(self, year: int, month: int) -> pd.DataFrame:
        """
        Return every amortized expense whose payment window covers the
        given (year, month) -- i.e. `purchase_date` has arrived, and the
        `duration_months`-month window hasn't yet elapsed -- along with
        that row's per-month installment.

        The window check is expressed directly in SQL using Oracle's
        `ADD_MONTHS`, so the "which installments apply this month" logic
        lives in one place and is trivially reusable by any future report.
        """
        month_start = date(year, month, 1)
        rows = self.db.query_dicts(
            """
            SELECT description, category, monthly_installment
            FROM amortized_expenses
            WHERE purchase_date <= :month_start
              AND ADD_MONTHS(TRUNC(purchase_date, 'MM'), duration_months) > :month_start
            """,
            {"month_start": month_start},
        )
        if not rows:
            return pd.DataFrame(columns=["description", "category", "monthly_installment"])
        return pd.DataFrame(rows)

    def get_monthly_spending(self, year: Optional[int] = None, month: Optional[int] = None) -> float:
        """
        Total spending for a given calendar month, dynamically combining:
            1. Regular expenses actually logged that month, plus
            2. The pro-rated monthly installment of any amortized
               purchase whose payment window covers that month.

        Defaults to the current month if `year`/`month` are omitted.
        """
        today = date.today()
        year = year or today.year
        month = month or today.month

        month_total = self.db.query_scalar(
            """
            SELECT NVL(SUM(amount), 0) FROM expenses
            WHERE EXTRACT(YEAR FROM expense_date) = :y
              AND EXTRACT(MONTH FROM expense_date) = :m
            """,
            {"y": year, "m": month},
        )
        amortized_df = self._amortized_installments_for_month(year, month)
        amortized_total = float(amortized_df["monthly_installment"].sum()) if not amortized_df.empty else 0.0

        return float(month_total or 0.0) + amortized_total

    def get_monthly_summary_by_category(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> pd.Series:
        """
        Per-category spending for a given month, including the pro-rated
        share of any applicable amortized purchases -- e.g. a gym
        membership bought in January still shows up under "Entertainment"
        (or whatever category it was assigned) every month it's active.
        """
        today = date.today()
        year = year or today.year
        month = month or today.month

        expense_rows = self.db.query(
            """
            SELECT category, SUM(amount) FROM expenses
            WHERE EXTRACT(YEAR FROM expense_date) = :y
              AND EXTRACT(MONTH FROM expense_date) = :m
            GROUP BY category
            """,
            {"y": year, "m": month},
        )
        combined: dict[str, float] = {cat: float(total) for cat, total in expense_rows}

        amortized_df = self._amortized_installments_for_month(year, month)
        for _, row in amortized_df.iterrows():
            combined[row["category"]] = combined.get(row["category"], 0.0) + float(row["monthly_installment"])

        if not combined:
            return pd.Series(dtype=float)
        return pd.Series(combined).sort_values(ascending=False)

    # ------------------------------------------------------------------
    # 4. CSV IMPORT / EXPORT
    # ------------------------------------------------------------------
    def export_to_csv(self, filepath: str) -> None:
        """Export the current (DB-backed) ledger to a CSV file."""
        ledger = self.ledger
        ledger.to_csv(filepath, index=False)
        print(f"Exported {len(ledger)} expense(s) to: {filepath}")

    def import_from_csv(self, filepath: str, auto_categorize_missing: bool = True) -> int:
        """Import expenses from a CSV file, inserting each row via `add_expense`."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV file not found: '{filepath}'")

        incoming = pd.read_csv(filepath)
        required = {"Date", "Description", "Amount"}
        missing_cols = required - set(incoming.columns)
        if missing_cols:
            raise ValueError(f"CSV is missing required column(s): {missing_cols}")

        if "Category" not in incoming.columns:
            incoming["Category"] = None

        imported_count = 0
        for _, row in incoming.iterrows():
            category = row.get("Category")
            category = None if pd.isna(category) or str(category).strip() == "" else str(category)
            if category is None and not auto_categorize_missing:
                category = "Uncategorized"

            try:
                self.add_expense(
                    date_str=str(row["Date"]),
                    description=str(row["Description"]),
                    amount=row["Amount"],
                    category=category,
                )
                imported_count += 1
            except ValueError as exc:
                print(f"  [Skipped row] {row.to_dict()} -> {exc}")

        print(f"Imported {imported_count}/{len(incoming)} row(s) from: {filepath}")
        return imported_count

    # ------------------------------------------------------------------
    # 5. RECURRING BILLS
    # ------------------------------------------------------------------
    def add_recurring_bill(
        self,
        name: str,
        amount: float,
        category: Optional[str] = None,
        frequency: str = "monthly",
        start_date: Optional[str] = None,
    ) -> str:
        """Register a recurring bill; category is ML-predicted if omitted."""
        if frequency not in ("monthly", "weekly"):
            raise ValueError("Frequency must be 'monthly' or 'weekly'.")

        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be a positive number.")

        assigned_category = category or self.predict_category(name)
        next_due = datetime.strptime(
            start_date or date.today().strftime("%Y-%m-%d"), "%Y-%m-%d"
        ).date()

        self.db.execute(
            """
            INSERT INTO recurring_bills (name, amount, category, frequency, next_due_date, active)
            VALUES (:name, :amount, :category, :frequency, :next_due_date, 1)
            """,
            {
                "name": name,
                "amount": amount,
                "category": assigned_category,
                "frequency": frequency,
                "next_due_date": next_due,
            },
        )
        return assigned_category

    @property
    def recurring_bills(self) -> pd.DataFrame:
        """Dynamically query active + inactive recurring bills as a DataFrame."""
        rows = self.db.query_dicts(
            "SELECT id, name, amount, category, frequency, next_due_date, active "
            "FROM recurring_bills ORDER BY next_due_date"
        )
        if not rows:
            return pd.DataFrame(columns=["id"] + self.RECURRING_COLUMNS)
        df = pd.DataFrame(rows)
        df = df.rename(
            columns={
                "name": "Name", "amount": "Amount", "category": "Category",
                "frequency": "Frequency", "next_due_date": "NextDueDate", "active": "Active",
            }
        )
        df["NextDueDate"] = pd.to_datetime(df["NextDueDate"]).dt.strftime("%Y-%m-%d")
        df["Active"] = df["Active"].astype(bool)
        return df

    def run_due_recurring_bills(self, as_of_date: Optional[str] = None) -> int:
        """
        Post any active recurring bill whose `next_due_date` has arrived
        into `expenses`, rolling `next_due_date` forward one cycle at a
        time until it's caught up with `as_of_date` (handles bills that
        went unposted for a while, e.g. the app wasn't run for weeks).
        """
        today = datetime.strptime(
            as_of_date or date.today().strftime("%Y-%m-%d"), "%Y-%m-%d"
        ).date()

        due_bills = self.db.query_dicts(
            "SELECT id, name, amount, category, frequency, next_due_date "
            "FROM recurring_bills WHERE active = 1 AND next_due_date <= :today",
            {"today": today},
        )

        posted_count = 0
        for bill in due_bills:
            due_date = bill["next_due_date"]
            if isinstance(due_date, datetime):
                due_date = due_date.date()

            while due_date <= today:
                self.add_expense(
                    date_str=due_date.strftime("%Y-%m-%d"),
                    description=f"{bill['name']} (recurring)",
                    amount=float(bill["amount"]),
                    category=bill["category"],
                )
                posted_count += 1

                if bill["frequency"] == "monthly":
                    month = due_date.month % 12 + 1
                    year = due_date.year + (1 if due_date.month == 12 else 0)
                    day = min(due_date.day, 28)  # keep it simple & always valid
                    due_date = due_date.replace(year=year, month=month, day=day)
                else:  # weekly
                    due_date = due_date + timedelta(weeks=1)

            self.db.execute(
                "UPDATE recurring_bills SET next_due_date = :next_due WHERE id = :id",
                {"next_due": due_date, "id": bill["id"]},
            )

        if posted_count:
            print(f"Posted {posted_count} recurring bill(s) to the ledger.")
        return posted_count

    def display_recurring_bills(self) -> None:
        df = self.recurring_bills
        if df.empty:
            print("No recurring bills set up yet.")
            return
        display_df = df.drop(columns=["id"]).copy()
        display_df["Amount"] = display_df["Amount"].map(lambda x: f"${x:,.2f}")
        print(display_df.to_string(index=False))

    # ------------------------------------------------------------------
    # 6. SAVINGS GOALS (in-memory -- see class docstring)
    # ------------------------------------------------------------------
    def create_savings_goal(self, name: str, target_amount: float) -> None:
        target_amount = float(target_amount)
        if target_amount <= 0:
            raise ValueError("Target amount must be positive.")
        if name in self.savings_goals:
            raise ValueError(f"A savings goal named '{name}' already exists.")
        self.savings_goals[name] = {"target": target_amount, "saved": 0.0}

    def contribute_to_goal(self, name: str, amount: float) -> None:
        if name not in self.savings_goals:
            raise ValueError(f"No savings goal named '{name}' exists.")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Contribution amount must be positive.")
        self.savings_goals[name]["saved"] += amount

    def display_savings_goals(self) -> None:
        if not self.savings_goals:
            print("No savings goals created yet.")
            return
        print("\n--- Savings Goals ---")
        for name, info in self.savings_goals.items():
            target, saved = info["target"], info["saved"]
            pct = min(saved / target, 1.0) if target else 0.0
            bar_length = 20
            filled = int(bar_length * pct)
            bar = "#" * filled + "-" * (bar_length - filled)
            status = " (COMPLETE!)" if pct >= 1.0 else ""
            print(f"  {name:<18} [{bar}] {pct * 100:5.1f}%  ${saved:,.2f} / ${target:,.2f}{status}")

    # ------------------------------------------------------------------
    # 7. VISUALIZATION
    # ------------------------------------------------------------------
    def plot_spending_by_category(self, save_path: Optional[str] = None) -> None:
        summary = self.get_summary_by_category()
        if summary.empty:
            print("No expense data available to plot yet.")
            return

        palette = [
            "#4C72B0", "#DD8452", "#55A868", "#C44E52",
            "#8172B2", "#937860", "#DA8BC3", "#8C8C8C",
        ]
        fig, ax = plt.subplots(figsize=(8, 8))
        wedges, texts, autotexts = ax.pie(
            summary.values, labels=summary.index, autopct="%1.1f%%", startangle=140,
            colors=palette[: len(summary)], wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            textprops={"fontsize": 11}, pctdistance=0.80,
        )
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
            autotext.set_fontsize(10)

        ax.set_title(
            f"Spending Breakdown by Category\nTotal: ${self.get_total_spent():,.2f}",
            fontsize=14, fontweight="bold", pad=20,
        )
        ax.axis("equal")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Chart saved to: {save_path}")
        else:
            plt.show()
        plt.close(fig)

    # ------------------------------------------------------------------
    # 8. DISPLAY HELPERS
    # ------------------------------------------------------------------
    def display_ledger(self) -> None:
        ledger = self.ledger
        if ledger.empty:
            print("Ledger is empty. No expenses recorded yet.")
            return
        display_df = ledger.copy()
        display_df["Amount"] = display_df["Amount"].map(lambda x: f"${x:,.2f}")
        print(display_df.to_string(index=False))

    def display_summary(self) -> None:
        summary = self.get_summary_by_category()
        if summary.empty:
            print("No spending summary available yet.")
            return
        print("\n--- All-Time Spending Summary by Category ---")
        for category, total in summary.items():
            print(f"  {category:<20} ${total:,.2f}")
        print(f"  {'TOTAL':<20} ${self.get_total_spent():,.2f}")

    def display_monthly_summary(self, year: Optional[int] = None, month: Optional[int] = None) -> None:
        """Print the amortization-aware summary for a given month (defaults to current)."""
        today = date.today()
        year, month = year or today.year, month or today.month
        summary = self.get_monthly_summary_by_category(year, month)
        label = date(year, month, 1).strftime("%B %Y")

        if summary.empty:
            print(f"No spending recorded for {label} (including amortized installments).")
            return
        print(f"\n--- Spending Summary for {label} (includes amortized installments) ---")
        for category, total in summary.items():
            print(f"  {category:<20} ${total:,.2f}")
        print(f"  {'TOTAL':<20} ${self.get_monthly_spending(year, month):,.2f}")
