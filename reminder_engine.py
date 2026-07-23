#!/usr/bin/env python3
"""
================================================================================
reminder_engine.py -- Smart Grace-Period & "Too Tired" Reminders (Feature C)
================================================================================
Humane, non-spammy nudges built on two tables:
    - user_preferences : per-user `preferred_time` + `reminder_buffer_hours`
    - sent_reminders    : de-duplication log so a nudge fires at most once
                          per (user, date, reminder_type)

Two scenarios, both driven by the same idea -- "did the user log anything
today/yesterday?" -- checked against their own stated preferences rather
than a hard-coded time:

    Scenario 1 (SAME_DAY_GRACE)
        It's now past `preferred_time + reminder_buffer_hours` today, and
        the user hasn't logged a single expense today yet. Nudge them
        gently before the day is out.

    Scenario 2 (NEXT_DAY_CATCHUP)
        The user logged literally nothing yesterday (they were "too
        tired" and skipped the whole day). Catch it the next morning with
        a friendly makeup reminder instead of silently losing the data.

This module is transport-agnostic: `run_reminder_checks` returns the
message text(s) that should be sent. Wiring them to email / push /
SMS is left to the caller (e.g. a scheduled job that calls this once
an hour and forwards any returned messages to a notification service).
================================================================================
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import List, Optional

from db import OracleDB

DEFAULT_PREFERRED_TIME = "21:00"
DEFAULT_REMINDER_BUFFER_HOURS = 1.5
DEFAULT_CATCHUP_HOUR = 9  # "the next morning" -- overridable per call

SAME_DAY_GRACE = "SAME_DAY_GRACE"
NEXT_DAY_CATCHUP = "NEXT_DAY_CATCHUP"


class ReminderEngine:
    """Owns preference lookups, expense-logged checks, and de-duplicated
    reminder dispatch for the "too tired to log it" UX."""

    def __init__(self, db: OracleDB) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------
    def get_preferences(self, user_id: str) -> dict:
        """Fetch a user's reminder preferences, falling back to sane
        defaults (21:00, 1.5h buffer) if they haven't set any yet."""
        row = self.db.query_dicts(
            "SELECT preferred_time, reminder_buffer_hours FROM user_preferences WHERE user_id = :user_id",
            {"user_id": user_id},
        )
        if not row:
            return {
                "preferred_time": DEFAULT_PREFERRED_TIME,
                "reminder_buffer_hours": DEFAULT_REMINDER_BUFFER_HOURS,
            }
        return row[0]

    def set_preferences(
        self, user_id: str, preferred_time: str = DEFAULT_PREFERRED_TIME,
        reminder_buffer_hours: float = DEFAULT_REMINDER_BUFFER_HOURS,
    ) -> None:
        """Upsert a user's reminder preferences via MERGE."""
        # Validate the time format up front so bad input fails fast.
        datetime.strptime(preferred_time, "%H:%M")
        if reminder_buffer_hours < 0:
            raise ValueError("reminder_buffer_hours must be non-negative.")

        self.db.execute(
            """
            MERGE INTO user_preferences up
            USING (SELECT :user_id AS user_id FROM dual) src
            ON (up.user_id = src.user_id)
            WHEN MATCHED THEN
                UPDATE SET preferred_time = :preferred_time,
                           reminder_buffer_hours = :reminder_buffer_hours
            WHEN NOT MATCHED THEN
                INSERT (user_id, preferred_time, reminder_buffer_hours)
                VALUES (:user_id, :preferred_time, :reminder_buffer_hours)
            """,
            {
                "user_id": user_id,
                "preferred_time": preferred_time,
                "reminder_buffer_hours": reminder_buffer_hours,
            },
        )

    # ------------------------------------------------------------------
    # Ledger-activity checks
    # ------------------------------------------------------------------
    def _has_expense_on(self, day: date) -> bool:
        """Whether at least one expense was logged on the given date."""
        count = self.db.query_scalar(
            "SELECT COUNT(*) FROM expenses WHERE expense_date = :d", {"d": day}
        )
        return bool(count)

    # ------------------------------------------------------------------
    # Reminder de-duplication
    # ------------------------------------------------------------------
    def _already_sent(self, log_date: date, reminder_type: str, user_id: str) -> bool:
        count = self.db.query_scalar(
            "SELECT COUNT(*) FROM sent_reminders "
            "WHERE log_date = :d AND reminder_type = :t AND user_id = :u",
            {"d": log_date, "t": reminder_type, "u": user_id},
        )
        return bool(count)

    def _mark_sent(self, log_date: date, reminder_type: str, user_id: str) -> None:
        # Guard against a race between the check and the insert re-firing
        # the same reminder; the UNIQUE constraint on sent_reminders is the
        # ultimate backstop, so a duplicate insert is simply ignored.
        if self._already_sent(log_date, reminder_type, user_id):
            return
        self.db.execute(
            "INSERT INTO sent_reminders (log_date, reminder_type, user_id) "
            "VALUES (:d, :t, :u)",
            {"d": log_date, "t": reminder_type, "u": user_id},
        )

    # ------------------------------------------------------------------
    # Scenario checks
    # ------------------------------------------------------------------
    def check_same_day_grace(self, user_id: str, now: Optional[datetime] = None) -> Optional[str]:
        """
        Scenario 1: if it's now past the user's preferred_time +
        reminder_buffer_hours, and they haven't logged anything today,
        fire (at most once) a same-day nudge.
        """
        now = now or datetime.now()
        prefs = self.get_preferences(user_id)
        preferred = datetime.strptime(prefs["preferred_time"], "%H:%M").time()
        buffer_hours = float(prefs["reminder_buffer_hours"])

        trigger_dt = datetime.combine(now.date(), preferred) + timedelta(hours=buffer_hours)
        if now < trigger_dt:
            return None  # too early -- still within the grace period

        if self._has_expense_on(now.date()):
            return None  # they already logged something today

        if self._already_sent(now.date(), SAME_DAY_GRACE, user_id):
            return None  # don't spam -- already nudged once today

        self._mark_sent(now.date(), SAME_DAY_GRACE, user_id)
        return (
            "Hey! Looks like today's expenses haven't been logged yet. "
            "No pressure -- just a gentle nudge before the day wraps up. 🌙"
        )

    def check_next_day_catchup(
        self, user_id: str, now: Optional[datetime] = None, catchup_hour: int = DEFAULT_CATCHUP_HOUR,
    ) -> Optional[str]:
        """
        Scenario 2: if it's the morning (>= `catchup_hour`) and *yesterday*
        has zero logged expenses, fire (at most once) a friendly
        makeup reminder instead of silently letting the day go untracked.
        """
        now = now or datetime.now()
        if now.time() < time(hour=catchup_hour):
            return None  # not "morning" yet -- wait for the next check

        yesterday = now.date() - timedelta(days=1)
        if self._has_expense_on(yesterday):
            return None  # they didn't actually skip anything

        if self._already_sent(yesterday, NEXT_DAY_CATCHUP, user_id):
            return None  # already sent this catch-up

        self._mark_sent(yesterday, NEXT_DAY_CATCHUP, user_id)
        return (
            "Looks like yesterday slipped by without any logged expenses -- "
            "totally okay, life happens! Got a minute to catch it up now? ☕"
        )

    def run_reminder_checks(self, user_id: str, now: Optional[datetime] = None) -> List[str]:
        """
        Convenience entry point for a scheduler: run both scenario checks
        and return whichever reminder message(s) actually fired. Safe to
        call as often as you like (e.g. hourly) -- de-duplication makes
        repeated calls a no-op once a reminder has already gone out.
        """
        messages = []
        for check in (self.check_same_day_grace, self.check_next_day_catchup):
            message = check(user_id, now=now)
            if message:
                messages.append(message)
        return messages
