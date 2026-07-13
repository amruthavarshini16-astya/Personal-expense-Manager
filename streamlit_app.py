#!/usr/bin/env python3
"""
================================================================================
AI-Powered Personal Expense Manager -- Streamlit Dashboard
================================================================================
An interactive web front-end for the `ExpenseManager` backend (see
`expense_manager.py`). This file contains ONLY presentation logic: routing,
layout, widgets, and charts. All business logic (ML categorization, ledger
math, recurring bills, savings goals, CSV I/O) stays in the backend class, so
the two can evolve independently and the backend remains fully unit-testable
without a browser.

Run locally with:
    streamlit run streamlit_app.py

Author: Senior Python / Data Engineering Team
================================================================================
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from expense_manager import ExpenseManager

# ==============================================================================
# PAGE CONFIGURATION & GLOBAL STYLE
# ==============================================================================
st.set_page_config(
    page_title="AI Expense Manager",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# A single, consistent color palette shared across every chart on the page so
# "Groceries" is always the same color whether it's in a pie, bar, or line.
CATEGORY_COLORS = {
    "Food & Dining": "#DD8452",
    "Groceries": "#55A868",
    "Transport": "#4C72B0",
    "Entertainment": "#8172B2",
    "Bills & Utilities": "#C44E52",
    "Uncategorized": "#8C8C8C",
}
FALLBACK_PALETTE = px.colors.qualitative.Set2

CUSTOM_CSS = """
<style>
    /* Tighten the default Streamlit top padding so the dashboard feels denser */
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }

    /* KPI metric cards */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #EAECEF;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetricLabel"] { font-weight: 600; color: #6B7280; }

    /* Section headers */
    h2, h3 { font-weight: 700; }

    /* Sidebar branding */
    section[data-testid="stSidebar"] { background-color: #111827; }
    section[data-testid="stSidebar"] * { color: #F3F4F6 !important; }
    section[data-testid="stSidebar"] .stRadio label { font-size: 0.95rem; }

    /* Progress bar rounding for savings goals */
    div[data-testid="stProgress"] > div > div { border-radius: 8px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ==============================================================================
# SESSION STATE / BACKEND WIRING
# ==============================================================================
def get_manager() -> ExpenseManager:
    """
    Return the single ExpenseManager instance for this browser session,
    creating (and training the ML model) exactly once per session.
    """
    if "manager" not in st.session_state:
        st.session_state.manager = ExpenseManager()
        st.session_state.demo_loaded = False
    return st.session_state.manager


def load_demo_data(manager: ExpenseManager) -> None:
    """Seed the session with realistic sample data so the dashboard never
    greets a first-time visitor with an empty, unconvincing screen."""
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
        ("2025-01-15", "Trader Joe's grocery run", 63.20),
        ("2025-01-16", "Lyft ride home", 22.40),
        ("2025-01-17", "Concert tickets", 89.00),
        ("2025-01-20", "Sushi takeout for date night", 47.60),
        ("2025-01-22", "Parking garage fee", 12.00),
    ]
    for tx_date, description, amount in demo_transactions:
        manager.add_expense(tx_date, description, amount)

    manager.add_recurring_bill("Apartment Rent", 1400.00, frequency="monthly", start_date="2025-01-01")
    manager.add_recurring_bill("Gym Membership", 40.00, frequency="monthly", start_date="2025-01-01")
    manager.run_due_recurring_bills(as_of_date="2025-01-31")

    manager.create_savings_goal("Emergency Fund", 5000)
    manager.contribute_to_goal("Emergency Fund", 1250)
    manager.create_savings_goal("Japan Trip", 3000)
    manager.contribute_to_goal("Japan Trip", 900)

    st.session_state.demo_loaded = True


def category_color_sequence(categories: list[str]) -> list[str]:
    """Map a list of category names to consistent colors, falling back to
    the qualitative palette for any category not in CATEGORY_COLORS."""
    colors = []
    fallback_idx = 0
    for cat in categories:
        if cat in CATEGORY_COLORS:
            colors.append(CATEGORY_COLORS[cat])
        else:
            colors.append(FALLBACK_PALETTE[fallback_idx % len(FALLBACK_PALETTE)])
            fallback_idx += 1
    return colors


manager = get_manager()

# ==============================================================================
# SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.markdown("## 💸 Expense AI")
    st.caption("TF-IDF + Naive Bayes categorization, live.")
    st.divider()

    page = st.radio(
        "Navigate",
        [
            "📊 Dashboard",
            "➕ Add Expense",
            "🔁 Recurring Bills",
            "🎯 Savings Goals",
            "📁 Import / Export",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if not st.session_state.get("demo_loaded", False):
        if st.button("✨ Load sample data", use_container_width=True):
            load_demo_data(manager)
            st.rerun()
    if st.button("🗑️ Reset all data", use_container_width=True):
        for key in ("manager", "demo_loaded"):
            st.session_state.pop(key, None)
        st.rerun()

    st.divider()
    st.caption("Built with Python · pandas · scikit-learn · Plotly · Streamlit")


# ==============================================================================
# PAGE: DASHBOARD
# ==============================================================================
if page == "📊 Dashboard":
    st.title("📊 Spending Dashboard")

    ledger = manager.ledger

    if ledger.empty:
        st.info("No expenses recorded yet. Use **➕ Add Expense** or click **Load sample data** in the sidebar to get started.")
    else:
        ledger = ledger.copy()
        ledger["Date"] = pd.to_datetime(ledger["Date"])

        total_spent = manager.get_total_spent()
        this_month = ledger[ledger["Date"].dt.to_period("M") == pd.Timestamp.today().to_period("M")]["Amount"].sum()
        # Fall back to the most recent month present in the data if "this month"
        # (real-world today) has no demo transactions in it.
        if this_month == 0 and not ledger.empty:
            latest_period = ledger["Date"].dt.to_period("M").max()
            this_month = ledger[ledger["Date"].dt.to_period("M") == latest_period]["Amount"].sum()

        summary = manager.get_summary_by_category()
        top_category = summary.index[0] if not summary.empty else "N/A"
        avg_transaction = ledger["Amount"].mean()

        # --- KPI row ------------------------------------------------------
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Spent", f"${total_spent:,.2f}")
        c2.metric("This Period", f"${this_month:,.2f}")
        c3.metric("Top Category", top_category)
        c4.metric("Avg Transaction", f"${avg_transaction:,.2f}")

        st.markdown("")

        # --- Charts row -----------------------------------------------------
        col_pie, col_bar = st.columns([1, 1.2])

        with col_pie:
            st.subheader("Breakdown by Category")
            pie_fig = go.Figure(
                data=[
                    go.Pie(
                        labels=summary.index,
                        values=summary.values,
                        hole=0.45,
                        marker=dict(colors=category_color_sequence(list(summary.index))),
                        textinfo="percent+label",
                        textfont=dict(size=13),
                        pull=[0.03] * len(summary),
                    )
                ]
            )
            pie_fig.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=380,
                annotations=[dict(text=f"${total_spent:,.0f}", x=0.5, y=0.5, font_size=20, showarrow=False)],
            )
            st.plotly_chart(pie_fig, use_container_width=True)

        with col_bar:
            st.subheader("Total by Category")
            bar_fig = px.bar(
                x=summary.values,
                y=summary.index,
                orientation="h",
                color=summary.index,
                color_discrete_map=CATEGORY_COLORS,
                text=[f"${v:,.0f}" for v in summary.values],
            )
            bar_fig.update_traces(textposition="outside")
            bar_fig.update_layout(
                showlegend=False,
                xaxis_title="Amount ($)",
                yaxis_title="",
                yaxis=dict(categoryorder="total ascending"),
                margin=dict(t=10, b=10, l=10, r=10),
                height=380,
            )
            st.plotly_chart(bar_fig, use_container_width=True)

        # --- Spending trend over time ----------------------------------------
        st.subheader("Spending Over Time")
        daily = ledger.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
        daily["Cumulative"] = daily["Amount"].cumsum()

        trend_fig = go.Figure()
        trend_fig.add_trace(
            go.Bar(x=daily["Date"], y=daily["Amount"], name="Daily Spend", marker_color="#4C72B0", opacity=0.55)
        )
        trend_fig.add_trace(
            go.Scatter(
                x=daily["Date"],
                y=daily["Cumulative"],
                name="Cumulative Spend",
                mode="lines",
                line=dict(color="#C44E52", width=3),
                yaxis="y2",
            )
        )
        trend_fig.update_layout(
            height=340,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis_title="Date",
            yaxis=dict(title="Daily Amount ($)"),
            yaxis2=dict(title="Cumulative ($)", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
        )
        st.plotly_chart(trend_fig, use_container_width=True)

        # --- Recent transactions ----------------------------------------------
        st.subheader("Recent Transactions")
        recent = ledger.sort_values("Date", ascending=False).head(10).copy()
        recent["Date"] = recent["Date"].dt.strftime("%Y-%m-%d")
        recent["Amount"] = recent["Amount"].map(lambda x: f"${x:,.2f}")
        st.dataframe(recent, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE: ADD EXPENSE
# ==============================================================================
elif page == "➕ Add Expense":
    st.title("➕ Add a New Expense")
    st.caption("Type a description below and watch the AI categorize it live -- before you even submit.")

    col_form, col_preview = st.columns([1.3, 1])

    with col_form:
        with st.form("add_expense_form", clear_on_submit=True):
            tx_date = st.date_input("Date", value=date.today())
            description = st.text_input("Description", placeholder="e.g. Uber ride to the airport")
            amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f")
            submitted = st.form_submit_button("Add Expense", use_container_width=True, type="primary")

            if submitted:
                if not description.strip():
                    st.error("Please enter a description.")
                else:
                    category = manager.add_expense(tx_date.strftime("%Y-%m-%d"), description, amount)
                    st.success(f"Added! The AI categorized this as **{category}**.")
                    st.balloons()

    with col_preview:
        st.markdown("#### Live AI Prediction")
        live_description = st.text_input("Try a description (preview only)", key="live_preview_input")
        if live_description.strip():
            predicted = manager.predict_category(live_description)
            color = CATEGORY_COLORS.get(predicted, "#4C72B0")
            st.markdown(
                f"""
                <div style="background:{color}20; border-left:5px solid {color};
                            padding:0.9rem 1rem; border-radius:8px; margin-top:0.5rem;">
                    <div style="font-size:0.85rem; color:#6B7280;">Predicted Category</div>
                    <div style="font-size:1.3rem; font-weight:700; color:{color};">{predicted}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Start typing above to see the model's prediction in real time.")


# ==============================================================================
# PAGE: RECURRING BILLS
# ==============================================================================
elif page == "🔁 Recurring Bills":
    st.title("🔁 Recurring Bills")
    st.caption("Register rent, subscriptions, and utilities once -- run them each period to post automatically.")

    col_form, col_table = st.columns([1, 1.4])

    with col_form:
        with st.form("add_bill_form", clear_on_submit=True):
            name = st.text_input("Bill Name", placeholder="e.g. Netflix Subscription")
            bill_amount = st.number_input("Amount ($)", min_value=0.01, step=1.0, format="%.2f")
            frequency = st.selectbox("Frequency", ["monthly", "weekly"])
            start = st.date_input("Start Date", value=date.today())
            add_bill = st.form_submit_button("Add Recurring Bill", use_container_width=True, type="primary")

            if add_bill:
                if not name.strip():
                    st.error("Please enter a bill name.")
                else:
                    category = manager.add_recurring_bill(
                        name, bill_amount, frequency=frequency, start_date=start.strftime("%Y-%m-%d")
                    )
                    st.success(f"'{name}' added, categorized as **{category}**.")

        st.markdown("")
        if st.button("▶️ Run Due Bills Now", use_container_width=True):
            posted = manager.run_due_recurring_bills()
            if posted:
                st.success(f"Posted {posted} bill(s) to the ledger.")
            else:
                st.info("No bills are due yet.")

    with col_table:
        st.subheader("Registered Bills")
        if manager.recurring_bills.empty:
            st.info("No recurring bills yet. Add one on the left.")
        else:
            display_bills = manager.recurring_bills.copy()
            display_bills["Amount"] = display_bills["Amount"].map(lambda x: f"${x:,.2f}")
            st.dataframe(display_bills, use_container_width=True, hide_index=True)


# ==============================================================================
# PAGE: SAVINGS GOALS
# ==============================================================================
elif page == "🎯 Savings Goals":
    st.title("🎯 Savings Goals")
    st.caption("Set targets and track contributions with a live progress bar.")

    col_create, col_contribute = st.columns(2)

    with col_create:
        with st.form("create_goal_form", clear_on_submit=True):
            st.markdown("**Create a Goal**")
            goal_name = st.text_input("Goal Name", placeholder="e.g. Japan Trip")
            target = st.number_input("Target Amount ($)", min_value=1.0, step=50.0, format="%.2f")
            create = st.form_submit_button("Create Goal", use_container_width=True)
            if create:
                if not goal_name.strip():
                    st.error("Please enter a goal name.")
                elif goal_name in manager.savings_goals:
                    st.error(f"A goal named '{goal_name}' already exists.")
                else:
                    manager.create_savings_goal(goal_name, target)
                    st.success(f"Goal '{goal_name}' created!")

    with col_contribute:
        with st.form("contribute_form", clear_on_submit=True):
            st.markdown("**Add a Contribution**")
            if manager.savings_goals:
                target_goal = st.selectbox("Goal", list(manager.savings_goals.keys()))
                contribution = st.number_input("Contribution ($)", min_value=0.01, step=10.0, format="%.2f")
                contribute = st.form_submit_button("Contribute", use_container_width=True)
                if contribute:
                    manager.contribute_to_goal(target_goal, contribution)
                    st.success(f"Added ${contribution:,.2f} to '{target_goal}'!")
            else:
                st.info("Create a goal first.")
                st.form_submit_button("Contribute", use_container_width=True, disabled=True)

    st.divider()
    st.subheader("Progress")
    if not manager.savings_goals:
        st.info("No savings goals yet.")
    else:
        for goal_name, info in manager.savings_goals.items():
            target, saved = info["target"], info["saved"]
            pct = min(saved / target, 1.0) if target else 0.0
            label = f"**{goal_name}** — ${saved:,.2f} / ${target:,.2f} ({pct * 100:.1f}%)"
            if pct >= 1.0:
                label += "  🎉 Complete!"
            st.markdown(label)
            st.progress(pct)


# ==============================================================================
# PAGE: IMPORT / EXPORT
# ==============================================================================
elif page == "📁 Import / Export":
    st.title("📁 Import / Export")

    col_import, col_export = st.columns(2)

    with col_import:
        st.subheader("Import from CSV")
        st.caption("Needs 'Date', 'Description', 'Amount' columns. A missing 'Category' column is filled in by the AI.")
        uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
        if uploaded is not None:
            temp_path = f"/tmp/{uploaded.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded.getbuffer())
            if st.button("Import Now", type="primary"):
                try:
                    before = len(manager.ledger)
                    manager.import_from_csv(temp_path)
                    after = len(manager.ledger)
                    st.success(f"Imported {after - before} new expense(s).")
                except (FileNotFoundError, ValueError) as exc:
                    st.error(str(exc))

    with col_export:
        st.subheader("Export Ledger")
        st.caption("Download the current in-session ledger as a CSV file.")
        if manager.ledger.empty:
            st.info("No expenses to export yet.")
        else:
            csv_bytes = manager.ledger.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download expenses.csv",
                data=csv_bytes,
                file_name="expenses.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
            )
            st.dataframe(manager.ledger, use_container_width=True, hide_index=True)
