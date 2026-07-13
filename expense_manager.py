#!/usr/bin/env python3
"""
================================================================================
AI-Powered Personal Expense Manager
================================================================================
A production-grade command-line application that combines:
    - Machine Learning (scikit-learn)  -> automatic expense categorization
    - Data Engineering (pandas)        -> structured, queryable expense ledger
    - Data Visualization (matplotlib)  -> spending breakdown by category
    - Recurring bills, savings goals, and CSV import/export

Architecture
------------
The application is built around a single `ExpenseManager` class that owns:
    1. A trained text-classification pipeline (TF-IDF + Multinomial Naive
       Bayes) used to infer the spending `Category` from a free-text
       transaction `Description`.
    2. A pandas DataFrame acting as the in-memory ledger of expenses.
    3. A pandas DataFrame of recurring bills that can be "run" to generate
       expenses automatically (rent, subscriptions, utilities, etc.).
    4. A lightweight savings-goal tracker (target amount + contributions).
    5. Reporting / visualization utilities built on top of the ledger.
    6. CSV import/export so the ledger can round-trip to/from disk.

Author: Senior Python / Data Engineering Team
================================================================================
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# Silence noisy sklearn convergence/future warnings so the CLI output stays clean.
warnings.filterwarnings("ignore")


class ExpenseManager:
    """
    Encapsulates the full expense-tracking workflow: ML-based categorization,
    data storage (pandas), and visualization (matplotlib).

    Attributes
    ----------
    ledger : pd.DataFrame
        The live in-memory table of all recorded expenses. Columns:
        ['Date', 'Description', 'Amount', 'Category'].
    model : sklearn.pipeline.Pipeline
        Trained TF-IDF + Multinomial Naive Bayes text classifier used to
        predict a Category from a transaction Description.
    """

    # Columns enforced on the ledger DataFrame at all times.
    LEDGER_COLUMNS: List[str] = ["Date", "Description", "Amount", "Category"]

    # Columns enforced on the recurring-bills DataFrame at all times.
    RECURRING_COLUMNS: List[str] = [
        "Name",
        "Amount",
        "Category",
        "Frequency",   # "monthly" or "weekly"
        "NextDueDate",
        "Active",
    ]

    def __init__(self) -> None:
        """Initialize an empty ledger, recurring-bills table, savings goals,
        and train the categorization model."""
        self.ledger: pd.DataFrame = pd.DataFrame(columns=self.LEDGER_COLUMNS)
        self.recurring_bills: pd.DataFrame = pd.DataFrame(columns=self.RECURRING_COLUMNS)
        # Savings goals stored as {goal_name: {"target": float, "saved": float}}
        self.savings_goals: dict = {}
        self.model: Pipeline = self._build_and_train_model()

    # ------------------------------------------------------------------
    # 1. MACHINE LEARNING ENGINE
    # ------------------------------------------------------------------
    @staticmethod
    def _get_training_data() -> tuple[List[str], List[str]]:
        """
        Provide a seed training dataset for the classifier.

        Returns
        -------
        (texts, labels) : tuple[List[str], List[str]]
            Parallel lists of example transaction descriptions and their
            correct spending category. Real-world usage would grow this
            dataset over time (e.g., by persisting user corrections).
        """
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
        """
        Build and fit the TF-IDF + Multinomial Naive Bayes classification
        pipeline on the seed training dataset.

        Returns
        -------
        Pipeline
            A fitted scikit-learn Pipeline ready to call `.predict()` on
            new, unseen transaction descriptions.
        """
        texts, labels = self._get_training_data()

        pipeline = Pipeline(
            steps=[
                # Convert raw text into TF-IDF weighted feature vectors.
                # ngram_range=(1, 2) lets the model pick up on short phrases
                # (e.g. "gas station") in addition to single words.
                (
                    "tfidf",
                    TfidfVectorizer(
                        lowercase=True,
                        stop_words="english",
                        ngram_range=(1, 2),
                    ),
                ),
                # Multinomial Naive Bayes is a strong, fast baseline for
                # short-text classification tasks like this one.
                ("classifier", MultinomialNB()),
            ]
        )

        pipeline.fit(texts, labels)
        return pipeline

    def predict_category(self, description: str) -> str:
        """
        Predict the spending category for a given transaction description.

        Parameters
        ----------
        description : str
            Free-text description of the transaction (e.g. "Uber to work").

        Returns
        -------
        str
            The predicted category label.
        """
        if not description or not description.strip():
            return "Uncategorized"
        prediction = self.model.predict([description])
        return str(prediction[0])

    # ------------------------------------------------------------------
    # 2. DATA MANAGEMENT (pandas)
    # ------------------------------------------------------------------
    def add_expense(
        self,
        date: str,
        description: str,
        amount: float,
        category: Optional[str] = None,
    ) -> str:
        """
        Add a new expense record to the ledger. The user supplies only
        Date, Description, and Amount -- the Category is inferred
        automatically by the ML model unless explicitly overridden.

        Parameters
        ----------
        date : str
            Transaction date, expected format 'YYYY-MM-DD'.
        description : str
            Free-text description of the purchase.
        amount : float
            Transaction amount (positive number, in local currency).
        category : Optional[str]
            If provided, bypasses the ML prediction (useful for manual
            correction / override workflows).

        Returns
        -------
        str
            The category that was ultimately assigned to the expense.
        """
        # --- Basic validation / normalization -------------------------------
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: '{date}'. Expected YYYY-MM-DD.")

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid amount: '{amount}'. Must be numeric.")

        if amount <= 0:
            raise ValueError("Amount must be a positive number.")

        # --- AI-driven category inference ------------------------------------
        assigned_category = category or self.predict_category(description)

        # --- Append to ledger using pd.concat (append() is deprecated) -------
        new_row = pd.DataFrame(
            [
                {
                    "Date": parsed_date,
                    "Description": description,
                    "Amount": amount,
                    "Category": assigned_category,
                }
            ]
        )
        self.ledger = pd.concat([self.ledger, new_row], ignore_index=True)

        return assigned_category

    def get_summary_by_category(self) -> pd.Series:
        """
        Aggregate total spending per category.

        Returns
        -------
        pd.Series
            Index: category name, Values: total amount spent, sorted
            descending by amount.
        """
        if self.ledger.empty:
            return pd.Series(dtype=float)

        summary = (
            self.ledger.groupby("Category")["Amount"]
            .sum()
            .sort_values(ascending=False)
        )
        return summary

    def get_total_spent(self) -> float:
        """Return the total amount spent across all recorded expenses."""
        if self.ledger.empty:
            return 0.0
        return float(self.ledger["Amount"].sum())

    # ------------------------------------------------------------------
    # CSV IMPORT / EXPORT
    # ------------------------------------------------------------------
    def export_to_csv(self, filepath: str) -> None:
        """
        Export the current ledger to a CSV file on disk.

        Parameters
        ----------
        filepath : str
            Destination path, e.g. 'expenses.csv'.
        """
        self.ledger.to_csv(filepath, index=False)
        print(f"Exported {len(self.ledger)} expense(s) to: {filepath}")

    def import_from_csv(self, filepath: str, auto_categorize_missing: bool = True) -> int:
        """
        Import expenses from a CSV file, appending them to the ledger.

        The CSV must contain at least 'Date', 'Description', and 'Amount'
        columns. If a 'Category' column is missing (or a row's category is
        blank) and `auto_categorize_missing` is True, the ML model fills it
        in automatically -- so bank/credit-card exports (which never include
        a category) can be dropped straight in.

        Parameters
        ----------
        filepath : str
            Path to the CSV file to import.
        auto_categorize_missing : bool
            If True, use the ML model to categorize rows lacking a Category.

        Returns
        -------
        int
            Number of rows successfully imported.
        """
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
                    date=str(row["Date"]),
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
    # RECURRING BILLS
    # ------------------------------------------------------------------
    def add_recurring_bill(
        self,
        name: str,
        amount: float,
        category: Optional[str] = None,
        frequency: str = "monthly",
        start_date: Optional[str] = None,
    ) -> str:
        """
        Register a recurring bill (rent, subscriptions, utilities, etc.).
        Category is AI-predicted from the bill name if not supplied.

        Parameters
        ----------
        name : str
            Short label for the bill, e.g. "Netflix Subscription".
        amount : float
            Amount charged each cycle.
        category : Optional[str]
            Overrides ML prediction if provided.
        frequency : str
            Either "monthly" or "weekly".
        start_date : Optional[str]
            'YYYY-MM-DD' date of the first due date. Defaults to today.

        Returns
        -------
        str
            The category assigned to this recurring bill.
        """
        if frequency not in ("monthly", "weekly"):
            raise ValueError("Frequency must be 'monthly' or 'weekly'.")

        amount = float(amount)
        if amount <= 0:
            raise ValueError("Amount must be a positive number.")

        assigned_category = category or self.predict_category(name)
        next_due = start_date or datetime.today().strftime("%Y-%m-%d")

        # Validate the date format up front so bad input fails fast.
        datetime.strptime(next_due, "%Y-%m-%d")

        new_row = pd.DataFrame(
            [
                {
                    "Name": name,
                    "Amount": amount,
                    "Category": assigned_category,
                    "Frequency": frequency,
                    "NextDueDate": next_due,
                    "Active": True,
                }
            ]
        )
        self.recurring_bills = pd.concat([self.recurring_bills, new_row], ignore_index=True)
        return assigned_category

    def run_due_recurring_bills(self, as_of_date: Optional[str] = None) -> int:
        """
        Post any active recurring bills whose NextDueDate has arrived as
        real expenses into the ledger, then roll their NextDueDate forward
        by one billing cycle.

        Parameters
        ----------
        as_of_date : Optional[str]
            'YYYY-MM-DD' date to evaluate against. Defaults to today.

        Returns
        -------
        int
            Number of bills posted to the ledger.
        """
        if self.recurring_bills.empty:
            return 0

        today = datetime.strptime(as_of_date or datetime.today().strftime("%Y-%m-%d"), "%Y-%m-%d")
        posted_count = 0

        for idx, bill in self.recurring_bills.iterrows():
            if not bill["Active"]:
                continue

            due_date = datetime.strptime(bill["NextDueDate"], "%Y-%m-%d")

            # A bill may be overdue by more than one cycle (e.g. app wasn't
            # run for a while) -- post it repeatedly until it's caught up.
            while due_date <= today:
                self.add_expense(
                    date=due_date.strftime("%Y-%m-%d"),
                    description=f"{bill['Name']} (recurring)",
                    amount=bill["Amount"],
                    category=bill["Category"],
                )
                posted_count += 1

                if bill["Frequency"] == "monthly":
                    # Advance by one calendar month, safely handling month-end overflow.
                    month = due_date.month % 12 + 1
                    year = due_date.year + (1 if due_date.month == 12 else 0)
                    day = min(due_date.day, 28)  # keep it simple & always valid
                    due_date = due_date.replace(year=year, month=month, day=day)
                else:  # weekly
                    due_date = due_date + timedelta(weeks=1)

            self.recurring_bills.at[idx, "NextDueDate"] = due_date.strftime("%Y-%m-%d")

        if posted_count:
            print(f"Posted {posted_count} recurring bill(s) to the ledger.")
        return posted_count

    def display_recurring_bills(self) -> None:
        """Pretty-print all registered recurring bills."""
        if self.recurring_bills.empty:
            print("No recurring bills set up yet.")
            return

        display_df = self.recurring_bills.copy()
        display_df["Amount"] = display_df["Amount"].map(lambda x: f"${x:,.2f}")
        print(display_df.to_string(index=False))

    # ------------------------------------------------------------------
    # SAVINGS GOALS
    # ------------------------------------------------------------------
    def create_savings_goal(self, name: str, target_amount: float) -> None:
        """
        Create a new savings goal.

        Parameters
        ----------
        name : str
            Label for the goal, e.g. "Emergency Fund" or "Japan Trip".
        target_amount : float
            The amount to save toward.
        """
        target_amount = float(target_amount)
        if target_amount <= 0:
            raise ValueError("Target amount must be positive.")
        if name in self.savings_goals:
            raise ValueError(f"A savings goal named '{name}' already exists.")

        self.savings_goals[name] = {"target": target_amount, "saved": 0.0}

    def contribute_to_goal(self, name: str, amount: float) -> None:
        """
        Add a contribution toward an existing savings goal.

        Parameters
        ----------
        name : str
            The goal to contribute to.
        amount : float
            Amount to add (must be positive).
        """
        if name not in self.savings_goals:
            raise ValueError(f"No savings goal named '{name}' exists.")

        amount = float(amount)
        if amount <= 0:
            raise ValueError("Contribution amount must be positive.")

        self.savings_goals[name]["saved"] += amount

    def display_savings_goals(self) -> None:
        """Pretty-print progress toward each savings goal with a text-based
        progress bar for a bit of visual flair in the terminal."""
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
    # 3. DATA VISUALIZATION (matplotlib)
    # ------------------------------------------------------------------
    def plot_spending_by_category(self, save_path: Optional[str] = None) -> None:
        """
        Render a pie chart of total spending per category.

        Parameters
        ----------
        save_path : Optional[str]
            If provided, saves the chart to this file path instead of (or
            in addition to) displaying it interactively.
        """
        summary = self.get_summary_by_category()

        if summary.empty:
            print("No expense data available to plot yet.")
            return

        # A professional, muted color palette (avoids default matplotlib
        # primary colors which can look unpolished).
        palette = [
            "#4C72B0",  # muted blue
            "#DD8452",  # muted orange
            "#55A868",  # muted green
            "#C44E52",  # muted red
            "#8172B2",  # muted purple
            "#937860",  # muted brown
            "#DA8BC3",  # muted pink
            "#8C8C8C",  # muted gray
        ]

        fig, ax = plt.subplots(figsize=(8, 8))

        wedges, texts, autotexts = ax.pie(
            summary.values,
            labels=summary.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=palette[: len(summary)],
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
            textprops={"fontsize": 11},
            pctdistance=0.80,
        )

        # Style the percentage labels for readability against the wedges.
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
            autotext.set_fontsize(10)

        ax.set_title(
            f"Spending Breakdown by Category\nTotal: ${self.get_total_spent():,.2f}",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )

        # Equal aspect ratio ensures the pie is drawn as a circle.
        ax.axis("equal")
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Chart saved to: {save_path}")
        else:
            plt.show()

        plt.close(fig)

    # ------------------------------------------------------------------
    # UTILITY / DISPLAY HELPERS
    # ------------------------------------------------------------------
    def display_ledger(self) -> None:
        """Pretty-print the current expense ledger to the console."""
        if self.ledger.empty:
            print("Ledger is empty. No expenses recorded yet.")
            return

        display_df = self.ledger.copy()
        display_df["Amount"] = display_df["Amount"].map(lambda x: f"${x:,.2f}")
        print(display_df.to_string(index=False))

    def display_summary(self) -> None:
        """Pretty-print the per-category spending summary to the console."""
        summary = self.get_summary_by_category()
        if summary.empty:
            print("No spending summary available yet.")
            return

        print("\n--- Spending Summary by Category ---")
        for category, total in summary.items():
            print(f"  {category:<20} ${total:,.2f}")
        print(f"  {'TOTAL':<20} ${self.get_total_spent():,.2f}")


def run_interactive_cli(manager: ExpenseManager) -> None:
    """
    Run a simple interactive command-line loop for adding expenses,
    viewing the ledger/summary, and generating the pie chart on demand.

    Parameters
    ----------
    manager : ExpenseManager
        An initialized ExpenseManager instance to operate on.
    """
    menu = """
========================================
   AI-Powered Personal Expense Manager
========================================
1.  Add a new expense
2.  View ledger
3.  View category summary
4.  Show spending pie chart
5.  Import expenses from CSV
6.  Export ledger to CSV
7.  Add a recurring bill
8.  Run due recurring bills
9.  View recurring bills
10. Create a savings goal
11. Contribute to a savings goal
12. View savings goals
13. Exit
----------------------------------------
"""
    while True:
        print(menu)
        choice = input("Select an option (1-13): ").strip()

        if choice == "1":
            date = input("  Date (YYYY-MM-DD): ").strip()
            description = input("  Description: ").strip()
            amount_raw = input("  Amount: ").strip()
            try:
                category = manager.add_expense(date, description, amount_raw)
                print(f"  -> Added! AI categorized this as: '{category}'")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "2":
            manager.display_ledger()

        elif choice == "3":
            manager.display_summary()

        elif choice == "4":
            manager.plot_spending_by_category()

        elif choice == "5":
            path = input("  CSV file path to import: ").strip()
            try:
                manager.import_from_csv(path)
            except (FileNotFoundError, ValueError) as exc:
                print(f"  [Error] {exc}")

        elif choice == "6":
            path = input("  CSV file path to export to: ").strip()
            manager.export_to_csv(path)

        elif choice == "7":
            name = input("  Bill name: ").strip()
            amount_raw = input("  Amount: ").strip()
            frequency = input("  Frequency (monthly/weekly): ").strip().lower() or "monthly"
            try:
                category = manager.add_recurring_bill(name, amount_raw, frequency=frequency)
                print(f"  -> Recurring bill added! AI categorized this as: '{category}'")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "8":
            manager.run_due_recurring_bills()

        elif choice == "9":
            manager.display_recurring_bills()

        elif choice == "10":
            name = input("  Goal name: ").strip()
            target_raw = input("  Target amount: ").strip()
            try:
                manager.create_savings_goal(name, target_raw)
                print(f"  -> Goal '{name}' created!")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "11":
            name = input("  Goal name: ").strip()
            amount_raw = input("  Contribution amount: ").strip()
            try:
                manager.contribute_to_goal(name, amount_raw)
                print(f"  -> Contribution added to '{name}'!")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "12":
            manager.display_savings_goals()

        elif choice == "13":
            print("Goodbye!")
            break

        else:
            print("  Invalid option. Please choose 1-13.")


if __name__ == "__main__":
    # ------------------------------------------------------------------
    # DEMONSTRATION BLOCK
    # Showcases the full pipeline end-to-end: ML categorization -> ledger
    # management -> visualization, using realistic sample transactions.
    # ------------------------------------------------------------------
    print("Initializing Expense Manager and training the ML categorization model...\n")
    manager = ExpenseManager()

    demo_transactions = [
        ("2025-01-03", "Uber ride to downtown office", 18.50),
        ("2025-01-04", "Whole Foods weekly grocery shopping", 87.32),
        ("2025-01-05", "Netflix subscription renewal", 15.99),
        ("2025-01-06", "Electricity bill payment", 120.00),
        ("2025-01-07", "Dinner at the Italian restaurant", 54.75),
        ("2025-01-08", "Gas station fuel fill up", 42.10),
        ("2025-01-09", "Movie tickets for the weekend", 28.00),
        ("2025-01-10", "Costco bulk shopping trip", 152.44),
        ("2025-01-11", "Internet and wifi monthly bill", 65.00),
        ("2025-01-12", "Starbucks coffee run", 6.75),
    ]

    print("Adding sample transactions (AI predicts each category automatically):\n")
    for date, description, amount in demo_transactions:
        predicted_category = manager.add_expense(date, description, amount)
        print(f"  [{date}] '{description}' -> ${amount:.2f}  =>  Category: {predicted_category}")

    print("\n--- Full Ledger ---")
    manager.display_ledger()

    manager.display_summary()

    # ------------------------------------------------------------------
    # RECURRING BILLS DEMO
    # ------------------------------------------------------------------
    print("\n--- Setting Up Recurring Bills ---")
    manager.add_recurring_bill("Netflix Subscription", 15.99, frequency="monthly", start_date="2025-01-01")
    manager.add_recurring_bill("Apartment Rent", 1400.00, frequency="monthly", start_date="2025-01-01")
    manager.add_recurring_bill("Gym Membership", 40.00, frequency="monthly", start_date="2025-01-01")
    manager.display_recurring_bills()

    print("\nRunning due recurring bills as of 2025-01-31...")
    manager.run_due_recurring_bills(as_of_date="2025-01-31")
    manager.display_recurring_bills()

    # ------------------------------------------------------------------
    # SAVINGS GOALS DEMO
    # ------------------------------------------------------------------
    print("\n--- Setting Up Savings Goals ---")
    manager.create_savings_goal("Emergency Fund", 5000)
    manager.create_savings_goal("Japan Trip", 3000)
    manager.contribute_to_goal("Emergency Fund", 1250)
    manager.contribute_to_goal("Japan Trip", 3000)
    manager.display_savings_goals()

    # ------------------------------------------------------------------
    # CSV EXPORT / IMPORT DEMO
    # ------------------------------------------------------------------
    print("\n--- CSV Export / Import Round-Trip ---")
    manager.export_to_csv("expenses_export.csv")

    # Simulate importing a fresh batch of transactions (e.g. a bank export)
    # that has NO Category column -- the AI fills it in automatically.
    bank_export = pd.DataFrame(
        [
            {"Date": "2025-01-15", "Description": "Trader Joe's grocery run", "Amount": 63.20},
            {"Date": "2025-01-16", "Description": "Lyft ride home", "Amount": 22.40},
            {"Date": "2025-01-17", "Description": "Concert tickets", "Amount": 89.00},
        ]
    )
    bank_export.to_csv("bank_export_sample.csv", index=False)
    manager.import_from_csv("bank_export_sample.csv")

    print("\n--- Final Ledger After Recurring Bills + CSV Import ---")
    manager.display_ledger()
    manager.display_summary()

    print("\nGenerating final spending breakdown pie chart...")
    manager.plot_spending_by_category(save_path="expense_breakdown.png")

    # Uncomment the line below to launch the interactive CLI after the demo:
    # run_interactive_cli(manager)
