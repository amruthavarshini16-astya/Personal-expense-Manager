#!/usr/bin/env python3
"""
================================================================================
db.py -- PostgreSQL / Supabase Cloud Data-Access Layer
================================================================================
A direct connection wrapper for PostgreSQL / Supabase deployment on Streamlit.
Maintains full backward compatibility with the Oracle interface.
================================================================================
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

import psycopg2
import psycopg2.extras
import streamlit as st


class OracleDB:
    """
    Supabase (PostgreSQL) adapter maintaining the original OracleDB class 
    interface so existing app.py/cli.py code functions without changes.
    """

    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        dsn: Optional[str] = None,
        min_connections: int = 1,
        max_connections: int = 4,
    ) -> None:
        # Retrieve PostgreSQL connection URI from Streamlit Secrets or Environment
        self.db_url = st.secrets.get("DATABASE_URL", os.environ.get("DATABASE_URL"))
        
        if not self.db_url:
            raise ValueError(
                "DATABASE_URL is missing. Please add your Supabase connection string "
                "to Streamlit Secrets or environment variables."
            )

        # Auto-initialize expenses table in Supabase
        self._init_db()

    def _init_db(self) -> None:
        """Creates the expenses table if it does not exist."""
        init_sql = """
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            expense_date DATE DEFAULT CURRENT_DATE,
            description VARCHAR(255),
            amount NUMERIC(10, 2),
            category VARCHAR(100)
        );
        """
        try:
            self.execute(init_sql)
            print("Expenses table verified / synchronized in Supabase successfully!")
        except Exception as e:
            print(f"Table check note: {e}")

    @contextmanager
    def connection(self) -> Iterator[psycopg2.extensions.connection]:
        """Establish direct connection to Supabase PostgreSQL."""
        conn = psycopg2.connect(self.db_url)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def cursor(self) -> Iterator[psycopg2.extensions.cursor]:
        """Acquire a cursor with automatic commit/rollback handling."""
        with self.connection() as conn:
            cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    # ------------------------------------------------------------------
    # High-level query helpers (Preserved Oracle interface)
    # ------------------------------------------------------------------
    def _convert_params(self, sql: str, params: Optional[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        """Converts Oracle named params (:param) to PyFormat (%(param)s) if needed."""
        if params:
            for key in params.keys():
                sql = sql.replace(f":{key}", f"%({key})s")
        return sql, params or {}

    def execute(self, sql: str, params: Optional[dict[str, Any]] = None) -> None:
        """Run an INSERT / UPDATE / DELETE statement."""
        pg_sql, pg_params = self._convert_params(sql, params)
        with self.cursor() as cur:
            cur.execute(pg_sql, pg_params)

    def execute_returning_id(self, sql: str, params: Optional[dict[str, Any]] = None) -> int:
        """Run an INSERT ... RETURNING id statement."""
        # Convert Oracle RETURNING INTO syntax to PostgreSQL RETURNING id
        cleaned_sql = sql.split("RETURNING")[0].rstrip() + " RETURNING id"
        pg_sql, pg_params = self._convert_params(cleaned_sql, params)
        
        with self.cursor() as cur:
            cur.execute(pg_sql, pg_params)
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def query(self, sql: str, params: Optional[dict[str, Any]] = None) -> list[tuple]:
        """Run a SELECT and return raw row tuples."""
        pg_sql, pg_params = self._convert_params(sql, params)
        with self.cursor() as cur:
            cur.execute(pg_sql, pg_params)
            return cur.fetchall()

    def query_dicts(self, sql: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Run a SELECT and return rows as lowercase-keyed dicts."""
        pg_sql, pg_params = self._convert_params(sql, params)
        with self.connection() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            try:
                cur.execute(pg_sql, pg_params)
                results = cur.fetchall()
                # Ensure all dictionary keys are lowercase
                return [{k.lower(): v for k, v in row.items()} for row in results]
            finally:
                cur.close()

    def query_scalar(self, sql: str, params: Optional[dict[str, Any]] = None) -> Any:
        """Run a SELECT expected to return exactly one column/row."""
        rows = self.query(sql, params)
        if not rows or not rows[0]:
            return None
        return rows[0][0]

    def close(self) -> None:
        """No-op wrapper to prevent crashing if caller attempts to close."""
        pass