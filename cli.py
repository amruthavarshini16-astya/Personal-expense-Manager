#!/usr/bin/env python3
"""
================================================================================
cli.py -- Interactive CLI / Demo Entrypoint
================================================================================
Wires OracleDB + ExpenseManager + ReminderEngine together. Requires these
environment variables to be set before running:

    ORACLE_USER
    ORACLE_PASSWORD
    ORACLE_DSN        e.g. "myhost:1521/ORCLPDB1" or a full Easy Connect string

Provision the schema once via `schema.sql` before first run:
    sqlplus your_user/your_password@your_dsn @schema.sql
================================================================================
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from db import OracleDB
from expense_manager import ExpenseManager
from reminder_engine import ReminderEngine

DEFAULT_USER_ID = "default_user"


def run_interactive_cli(manager: ExpenseManager, reminders: ReminderEngine, user_id: str = DEFAULT_USER_ID) -> None:
    """Interactive command-line loop covering every feature, including
    amortized expenses and reminder preferences."""
    menu = """
========================================
   AI-Powered Personal Expense Manager
========================================
1.  Add a new expense
2.  View ledger
3.  View all-time category summary
4.  Show spending pie chart
5.  Import expenses from CSV
6.  Export ledger to CSV
7.  Add a recurring bill
8.  Run due recurring bills
9.  View recurring bills
10. Create a savings goal
11. Contribute to a savings goal
12. View savings goals
13. Add an amortized expense
14. View this month's summary (amortization-aware)
15. Set reminder preferences
16. Check reminders now
17. Exit
----------------------------------------
"""
    while True:
        print(menu)
        choice = input("Select an option (1-17): ").strip()

        if choice == "1":
            d = input("  Date (YYYY-MM-DD): ").strip()
            description = input("  Description: ").strip()
            amount_raw = input("  Amount: ").strip()
            try:
                category = manager.add_expense(d, description, amount_raw)
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
            description = input("  Description (e.g. 'Annual gym membership'): ").strip()
            total_raw = input("  Total amount: ").strip()
            months_raw = input("  Spread across how many months? ").strip() or "12"
            purchase_date = input("  Purchase date (YYYY-MM-DD, blank = today): ").strip() or None
            try:
                category = manager.add_amortized_expense(
                    description, total_raw, purchase_date=purchase_date, duration_months=int(months_raw)
                )
                print(f"  -> Amortized expense added! AI categorized this as: '{category}'")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "14":
            manager.display_monthly_summary()

        elif choice == "15":
            preferred_time = input("  Preferred logging time (HH:MM, e.g. 21:00): ").strip() or "21:00"
            buffer_raw = input("  Grace buffer in hours (e.g. 1.5): ").strip() or "1.5"
            try:
                reminders.set_preferences(user_id, preferred_time, float(buffer_raw))
                print("  -> Preferences saved!")
            except ValueError as exc:
                print(f"  [Error] {exc}")

        elif choice == "16":
            messages = reminders.run_reminder_checks(user_id)
            if not messages:
                print("  No reminders to send right now.")
            for msg in messages:
                print(f"  🔔 {msg}")

        elif choice == "17":
            print("Goodbye!")
            break

        else:
            print("  Invalid option. Please choose 1-17.")


if __name__ == "__main__":
    print("Connecting to Oracle and training the ML categorization model...\n")
    db = OracleDB()  # reads ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN from env
    manager = ExpenseManager(db)
    reminders = ReminderEngine(db)

    print("\n--- Full Ledger ---")
    manager.display_ledger()
    manager.display_summary()

    print("\n--- Reminder Check ---")
    reminders.set_preferences(DEFAULT_USER_ID, preferred_time="21:00", reminder_buffer_hours=1.5)
    for msg in reminders.run_reminder_checks(DEFAULT_USER_ID):
        print(f"  🔔 {msg}")

    # --- LAUNCH INTERACTIVE CLI MENU ---
    run_interactive_cli(manager, reminders)

    # Close connection cleanly after exiting menu loop
    db.close()   