--------------------------------------------------------------------------
-- AI-Powered Personal Expense Manager -- Oracle Schema
--------------------------------------------------------------------------
-- Run once, as the application's schema owner, to provision every table
-- the application depends on. Compatible with Oracle 12c+ (IDENTITY
-- columns require 12c or later; adjust to a sequence + trigger for older
-- databases).
--------------------------------------------------------------------------

-- 1. Core expense ledger ------------------------------------------------
-- Every individual transaction the user has logged (manual entries,
-- posted recurring bills, and CSV imports all land here).
CREATE TABLE expenses (
    id              NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expense_date    DATE            NOT NULL,
    description     VARCHAR2(500)   NOT NULL,
    amount          NUMBER(12,2)    NOT NULL CHECK (amount > 0),
    category        VARCHAR2(100)   NOT NULL
);

CREATE INDEX idx_expenses_date ON expenses (expense_date);

-- 2. Recurring bills -------------------------------------------------------
-- Subscriptions, rent, utilities -- anything that repeats on a schedule
-- and gets "run" to post a new row into `expenses` when due.
CREATE TABLE recurring_bills (
    id              NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            VARCHAR2(200)   NOT NULL,
    amount          NUMBER(12,2)    NOT NULL CHECK (amount > 0),
    category        VARCHAR2(100)   NOT NULL,
    frequency       VARCHAR2(10)    NOT NULL CHECK (frequency IN ('monthly', 'weekly')),
    next_due_date   DATE            NOT NULL,
    active          NUMBER(1)       DEFAULT 1 NOT NULL CHECK (active IN (0, 1))
);

-- 3. Amortized expenses -----------------------------------------------------
-- High-cost, one-time purchases (e.g. a gym membership paid upfront) that
-- should be *spread* across a "useful life" for reporting purposes, rather
-- than blowing up a single month's total.
CREATE TABLE amortized_expenses (
    id                      NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    description             VARCHAR2(500)   NOT NULL,
    total_amount            NUMBER(12,2)    NOT NULL CHECK (total_amount > 0),
    category                VARCHAR2(100)   NOT NULL,
    purchase_date           DATE            NOT NULL,
    duration_months         NUMBER(4)       NOT NULL CHECK (duration_months > 0),
    monthly_installment     NUMBER(12,2)    NOT NULL
);

-- 4. Per-user reminder preferences ------------------------------------------
CREATE TABLE user_preferences (
    user_id                 VARCHAR2(100)   PRIMARY KEY,
    preferred_time          VARCHAR2(5)     DEFAULT '21:00' NOT NULL,   -- 'HH24:MI', e.g. '21:00'
    reminder_buffer_hours   NUMBER(4,2)     DEFAULT 1.5     NOT NULL
);

-- 5. Reminder de-duplication log ---------------------------------------------
-- Guarantees the "too tired" nudges fire at most once per user, per day,
-- per reminder type -- no matter how many times the checker function runs.
CREATE TABLE sent_reminders (
    id              NUMBER          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    log_date        DATE            NOT NULL,
    reminder_type   VARCHAR2(30)    NOT NULL,   -- 'SAME_DAY_GRACE' | 'NEXT_DAY_CATCHUP'
    user_id         VARCHAR2(100)   NOT NULL,
    CONSTRAINT uq_reminder_per_day UNIQUE (log_date, reminder_type, user_id)
);
