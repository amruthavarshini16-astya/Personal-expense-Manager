# AI-Powered Personal Expense Manager — Streamlit Dashboard

An interactive web dashboard on top of the `ExpenseManager` backend
(TF-IDF + Naive Bayes categorization, pandas ledger, recurring bills,
savings goals, CSV import/export).

## Files

- `expense_manager.py` — backend logic only (ML pipeline, ledger, recurring
  bills, savings goals, CSV I/O). No UI code. Fully reusable/testable on its
  own, including as a plain CLI script (`python expense_manager.py`).
- `streamlit_app.py` — the web dashboard. Imports `ExpenseManager` and
  handles only layout, widgets, and charts.
- `requirements.txt` — dependencies.

## Run it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Pages

- **📊 Dashboard** — KPI cards, an interactive donut chart, a category bar
  chart, a daily/cumulative spending trend, and a recent-transactions table.
- **➕ Add Expense** — enter Date/Description/Amount; a live side panel shows
  the AI's predicted category as you type, before you even submit.
- **🔁 Recurring Bills** — register bills (rent, subscriptions, utilities)
  and post the ones that are due into the ledger with one click.
- **🎯 Savings Goals** — create goals, log contributions, watch progress
  bars fill up.
- **📁 Import / Export** — upload a CSV (even one with no Category column —
  the AI fills it in) or download the current ledger as a CSV.

Use the **"Load sample data"** button in the sidebar for an instant, fully
populated demo. **"Reset all data"** clears the session and starts fresh.

## Notes

- State lives in `st.session_state` for the duration of the browser session
  — refreshing the page keeps your data, closing the tab does not (there's
  no database in this version by design, to keep the example self-contained).
- The backend is completely UI-agnostic, so the same `ExpenseManager` class
  still works as a standalone CLI app if you run `expense_manager.py`
  directly.
