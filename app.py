from datetime import date, datetime, timedelta
import io
import pandas as pd
import plotly.express as px
import streamlit as st

# Import ReportLab for PDF Generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Import the database layer
from db import OracleDB

# 1. Initialize DB connector instance
if "db_instance" not in st.session_state:
    st.session_state.db_instance = OracleDB()

# Initialize active interactive dashboard tab focus tracking
if "active_view" not in st.session_state:
    st.session_state.active_view = "Breakdown"

# Initialize dismissible pill badge state
if "hide_daily_pill" not in st.session_state:
    st.session_state.hide_daily_pill = False

# 2. Configure screen properties
st.set_page_config(
    page_title="Personal Expense Manager",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ========================================================
# CURRENCY CONFIGURATION
# ========================================================
currency_options = {
    "INR (₹)": {"symbol": "₹", "rate": 1.0},
    "USD ($)": {"symbol": "$", "rate": 0.012},
    "EUR (€)": {"symbol": "€", "rate": 0.011}
}

# Default display currency parameters
selected_currency_key = "INR (₹)"
currency_symbol = currency_options[selected_currency_key]["symbol"]
conversion_rate = currency_options[selected_currency_key]["rate"]

db_conn = st.session_state.db_instance

# 3. Modern SaaS Glassmorphism CSS styling
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Sidebar Navigation completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* Dark Slate Background */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 50%, #020617 100%);
        color: #f8fafc;
    }

    /* Top padding */
    .block-container {
        padding-top: 2.5rem !important;
    }

    /* Unique Title Styling */
    .custom-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.3 !important;
        margin-bottom: 0.2rem;
        letter-spacing: -0.03em;
    }

    .custom-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 1.2rem;
    }

    /* Compact Header Pill Badge */
    .status-pill {
        background: rgba(245, 158, 11, 0.1) !important;
        border: 1px solid rgba(245, 158, 11, 0.25) !important;
        border-radius: 20px !important;
        padding: 6px 14px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 8px !important;
        margin-bottom: 1.2rem !important;
    }

    /* Elevated Frosted Glass Cards */
    div[data-testid="stMetric"], div[data-testid="stForm"] {
        background: rgba(15, 23, 42, 0.65) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 22px !important;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5) !important;
    }

    /* Dynamic Button Styling */
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        padding: 10px 16px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        border-color: #818cf8 !important;
        background: linear-gradient(135deg, #312e81 0%, #1e1b4b 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px -5px rgba(99, 102, 241, 0.4) !important;
    }

    /* Custom Input Fields */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox > div > div {
        background: rgba(15, 23, 42, 0.8) !important;
        color: #f8fafc !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 10px !important;
    }

    /* Health Badge */
    .status-badge {
        background: rgba(15, 23, 42, 0.8);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #10b981;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        line-height: 1.8;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# ========================================================
# HELPER: PDF GENERATION ENGINE
# ========================================================
def generate_pdf_report(df, total_spent, primary_cat, limit, period_label, symbol):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e1b4b'), spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#64748b'), spaceAfter=15
    )

    story.append(Paragraph("Personal Expense Manager - Financial Report", title_style))
    story.append(Paragraph(f"Report Period: {period_label} | Generated on: {date.today().strftime('%Y-%m-%d')}", subtitle_style))
    story.append(Spacer(1, 10))

    amt_col_name = f"Amount ({symbol})"
    avg_spend = df[amt_col_name].mean() if not df.empty else 0.0
    summary_data = [
        [Paragraph("<b>Total Spending</b>", styles['Normal']), f"{symbol}{total_spent:,.2f}"],
        [Paragraph("<b>Spending Limit</b>", styles['Normal']), f"{symbol}{limit:,.2f}"],
        [Paragraph("<b>Top Spending Category</b>", styles['Normal']), str(primary_cat)],
        [Paragraph("<b>Average Ticket Size</b>", styles['Normal']), f"{symbol}{avg_spend:,.2f}"],
        [Paragraph("<b>Total Transactions</b>", styles['Normal']), str(len(df))]
    ]
    
    t_summary = Table(summary_data, colWidths=[200, 300])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 20))

    story.append(Paragraph("Detailed Ledger Transactions", styles['Heading2']))
    story.append(Spacer(1, 8))

    if not df.empty:
        table_data = [["Date", "Description", "Category", f"Amount ({symbol})"]]
        for _, row in df.iterrows():
            table_data.append([
                str(row["Date"]),
                str(row["Description"])[:30],
                str(row["Category"]),
                f"{symbol}{row[amt_col_name]:,.2f}"
            ])
            
        t_ledger = Table(table_data, colWidths=[80, 220, 110, 90])
        t_ledger.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#312e81')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f1f5f9')]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('FONTSIZE', (0,0), (-1,-1), 9),
        ]))
        story.append(t_ledger)
    else:
        story.append(Paragraph("No records found for this period.", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ========================================================
# BUDGET MODAL DIALOG
# ========================================================
@st.dialog("🎯 Budget & Savings Planner")
def show_budget_modal(symbol, rate):
    st.markdown(
        "<p style='color: #94a3b8; font-size: 0.9rem;'>Configure your monthly earnings to automatically calculate your recommended spending ceiling and savings target.</p>",
        unsafe_allow_html=True,
    )

    monthly_income = st.number_input(
        f"Monthly Income ({symbol})",
        min_value=0.0,
        value=st.session_state.get("popover_income", 30000.0 * rate),
        step=1000.0 * rate,
        format="%.2f",
        key="popover_income",
    )

    savings_pct = st.slider(
        "Target Savings Goal (%)",
        min_value=5,
        max_value=70,
        value=st.session_state.get("popover_savings", 20),
        step=5,
        key="popover_savings",
    )

    target_savings = monthly_income * (savings_pct / 100.0)
    spending_limit = monthly_income - target_savings

    st.markdown(
        f"""
        <div style="background: rgba(30, 41, 59, 0.7); padding: 16px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.1);">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #94a3b8; font-size: 0.9rem;">Target Savings Goal ({savings_pct}%):</span>
                <strong style="color: #a5b4fc; font-size: 0.95rem;">{symbol}{target_savings:,.2f}</strong>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #94a3b8; font-size: 0.9rem;">Max Expense Ceiling:</span>
                <strong style="color: #38bdf8; font-size: 0.95rem;">{symbol}{spending_limit:,.2f}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("Save & Apply Target", use_container_width=True, type="primary"):
        st.rerun()

# ========================================================
# HEADER SECTION
# ========================================================
st.markdown('<div class="custom-header">Personal Expense Manager</div>', unsafe_allow_html=True)
st.markdown('<div class="custom-subtitle">An intelligent, NLP-driven financial ledger</div>', unsafe_allow_html=True)

# Re-calculate budget variables for session state
if "popover_income" in st.session_state and "popover_savings" in st.session_state:
    monthly_income = st.session_state.popover_income
    savings_pct = st.session_state.popover_savings
else:
    monthly_income = 30000.0 * conversion_rate
    savings_pct = 20

target_savings = monthly_income * (savings_pct / 100.0)
spending_limit = monthly_income - target_savings

# ========================================================
# DATA EXTRACTION LAYER
# ========================================================
try:
    raw_rows = db_conn.query_dicts(
        "SELECT expense_date, description, amount, category FROM expenses ORDER BY expense_date DESC"
    )

    if raw_rows:
        ledger_df = pd.DataFrame(raw_rows)
        ledger_df.columns = ["Date", "Description", f"Amount ({currency_symbol})", "Category"]
        ledger_df[f"Amount ({currency_symbol})"] = pd.to_numeric(ledger_df[f"Amount ({currency_symbol})"]) * conversion_rate
        ledger_df["Date"] = ledger_df["Date"].astype(str)
    else:
        ledger_df = pd.DataFrame(
            columns=["Date", "Description", f"Amount ({currency_symbol})", "Category"]
        )
except Exception as e:
    st.error(f"Failed to fetch data: {e}")
    ledger_df = pd.DataFrame(
        columns=["Date", "Description", f"Amount ({currency_symbol})", "Category"]
    )

# Check daily logging status & show dismissible pill badge
today_str = date.today().strftime("%Y-%m-%d")
logged_today = not ledger_df[ledger_df["Date"] == today_str].empty if not ledger_df.empty else False

if not logged_today and not st.session_state.hide_daily_pill:
    p_col1, p_col2 = st.columns([20, 1])
    with p_col1:
        st.markdown(
            """
            <div class="status-pill">
                <span style="color: #fbbf24; font-size: 0.82rem; font-weight: 600;">
                    ⏳ Daily Status: No expenses logged for today yet
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p_col2:
        if st.button("✕", key="dismiss_pill_btn", help="Hide notification"):
            st.session_state.hide_daily_pill = True
            st.rerun()

# ========================================================
# RESPONSIVE MASTER GRID
# ========================================================
col1, col2 = st.columns([1, 2], gap="large")

# --------------------------------------------------------
# COLUMN 1: Live Inputs & AI Interaction
# --------------------------------------------------------
with col1:
    st.markdown("### Log Transaction")

    input_date = st.date_input("Transaction Date", value=datetime.today())
    input_desc = st.text_input("Description", placeholder="e.g., curd packet")

    preview_cat = "Miscellaneous"

    # Quick Rule/Pattern Based Auto-Categorization
    if input_desc:
        desc_lower = input_desc.lower()
        food_terms = ["food", "snack", "dinner", "lunch", "coffee", "curd", "biryani", "swiggy", "zomato"]
        bill_terms = ["bill", "electricity", "rent", "recharge", "wifi"]
        tech_terms = ["laptop", "charger", "mouse", "lenovo", "keyboard"]

        if any(w in desc_lower for w in food_terms):
            preview_cat = "Food & Dining"
            color = "#f59e0b"
        elif any(w in desc_lower for w in bill_terms):
            preview_cat = "Bills & Utilities"
            color = "#10b981"
        elif any(w in desc_lower for w in tech_terms):
            preview_cat = "Electronics"
            color = "#38bdf8"
        else:
            preview_cat = "Miscellaneous"
            color = "#64748b"

        st.markdown(
            f'<div style="background-color:rgba(15, 23, 42, 0.8); padding:10px;'
            f' border-radius:8px; border-left:3px solid {color}; margin: 8px 0 16px 0;">'
            f'<span style="color:#94a3b8; font-size:0.75rem; text-transform:uppercase; display:block;">Categorized As</span>'
            f'<strong style="color:{color}; font-size:0.95rem;">{preview_cat}</strong></div>',
            unsafe_allow_html=True,
        )

    # --- MULTI-CURRENCY LOGGING INPUT ---
    amt_col1, amt_col2 = st.columns([2, 1])
    with amt_col1:
        input_amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=1.0,
            format="%.2f"
        )
    with amt_col2:
        log_currency = st.selectbox(
            "Currency",
            options=list(currency_options.keys()),
            index=0,
            key="log_transaction_currency"
        )

    # Get rate for selected transaction currency
    input_currency_rate = currency_options[log_currency]["rate"]

    if st.button("Add Expense to Ledger", use_container_width=True, key="main_submit_btn"):
        if not input_desc or input_amount <= 0:
            st.error("Please provide a valid description and amount.")
        else:
            try:
                # Convert entered amount to base currency (INR) before storing
                base_inr_amount = input_amount / input_currency_rate
                
                insert_query = (
                    "INSERT INTO expenses (expense_date, description, amount, category) "
                    "VALUES (:1, :2, :3, :4)"
                )
                db_conn.execute(
                    insert_query,
                    {
                        "1": input_date.strftime("%Y-%m-%d"),
                        "2": input_desc.strip(),
                        "3": base_inr_amount,
                        "4": preview_cat,
                    },
                )
                st.success(f"Recorded {currency_options[log_currency]['symbol']}{input_amount:,.2f} under {preview_cat}!")
                st.rerun()
            except Exception as ex:
                st.error(f"Database write error: {ex}")

# --------------------------------------------------------
# COLUMN 2: Visual Dashboard & Analytics
# --------------------------------------------------------
with col2:
    ana_col1, ana_col2, ana_col3 = st.columns([2, 1, 1])
    with ana_col1:
        st.markdown("### Analytics Overview")
    
    with ana_col2:
        date_filter = st.selectbox(
            "Filter Period",
            options=["Current Month", "Last 30 Days", "All Time"],
            index=0,
            label_visibility="collapsed"
        )

    with ana_col3:
        if st.button("💰 Budget Targets", use_container_width=True, key="open_budget_btn"):
            show_budget_modal(currency_symbol, conversion_rate)

    filtered_analytics_df = ledger_df.copy()
    if not filtered_analytics_df.empty:
        filtered_analytics_df["Date_DT"] = pd.to_datetime(filtered_analytics_df["Date"])
        
        if date_filter == "Current Month":
            current_month = datetime.today().month
            current_year = datetime.today().year
            filtered_analytics_df = filtered_analytics_df[
                (filtered_analytics_df["Date_DT"].dt.month == current_month) &
                (filtered_analytics_df["Date_DT"].dt.year == current_year)
            ]
        elif date_filter == "Last 30 Days":
            thirty_days_ago = datetime.today() - timedelta(days=30)
            filtered_analytics_df = filtered_analytics_df[filtered_analytics_df["Date_DT"] >= thirty_days_ago]

    amt_col = f"Amount ({currency_symbol})"
    total_spent = filtered_analytics_df[amt_col].sum() if not filtered_analytics_df.empty else 0.0
    primary_cat = (
        filtered_analytics_df["Category"].mode()[0]
        if not filtered_analytics_df.empty and not filtered_analytics_df["Category"].dropna().empty
        else "None Logged"
    )

    if spending_limit > 0:
        budget_pct = min(total_spent / spending_limit, 1.0)
        st.markdown(f"**Spending vs. Expense Limit ({date_filter}):** {currency_symbol}{total_spent:,.2f} / {currency_symbol}{spending_limit:,.2f}")
        st.progress(budget_pct)

        if total_spent > spending_limit:
            st.warning(f"⚠️ Limit exceeded by {currency_symbol}{total_spent - spending_limit:,.2f}!")

    st.markdown("<br>", unsafe_allow_html=True)
    kpi1, kpi2, kpi3 = st.columns(3)

    avg_spend = filtered_analytics_df[amt_col].mean() if not filtered_analytics_df.empty else 0.0
    max_spend = filtered_analytics_df[amt_col].max() if not filtered_analytics_df.empty else 0.0

    with kpi1:
        st.metric(label="Total Spent", value=f"{currency_symbol}{total_spent:,.2f}")
    with kpi2:
        st.metric(label="Avg Ticket Size", value=f"{currency_symbol}{avg_spend:,.2f}")
    with kpi3:
        st.metric(label="Largest Expense", value=f"{currency_symbol}{max_spend:,.2f}")

    st.markdown("---")

    if filtered_analytics_df.empty:
        st.info("No records found for this period.")
    else:
        st.markdown("#### Category Distribution")
        fig_donut = px.pie(
            filtered_analytics_df,
            values=amt_col,
            names="Category",
            hole=0.6,
            color_discrete_sequence=px.colors.sequential.Darkmint_r,
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            margin=dict(t=10, b=10, l=10, r=10),
            height=250,
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    st.markdown("---")

    # Table Controls
    tbl_col1, tbl_col2, tbl_col3 = st.columns([2, 1, 1])

    with tbl_col1:
        st.markdown("#### Transactions Ledger")

    display_df = filtered_analytics_df.drop(columns=["Date_DT"], errors="ignore") if not filtered_analytics_df.empty else filtered_analytics_df

    with tbl_col2:
        excel_buffer = io.BytesIO()
        if not display_df.empty:
            display_df.to_excel(excel_buffer, index=False)
        st.download_button(
            label="📊 Excel",
            data=excel_buffer.getvalue(),
            file_name=f"expense_ledger_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with tbl_col3:
        pdf_data = generate_pdf_report(
            display_df, total_spent, primary_cat, spending_limit, date_filter, currency_symbol
        )
        st.download_button(
            label="📄 PDF Report",
            data=pdf_data,
            file_name=f"monthly_expense_report_{date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True)
