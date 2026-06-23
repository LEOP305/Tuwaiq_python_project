import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
from datetime import date

from data import (
    load_expenses, load_settings, save_settings,
    add_expense, search_expenses, aggregate_by,
    monthly_summary, aggregate_by_week, cumulative_spending,
    budget_status, savings_rate,
)

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Manager",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;700&display=swap');

html, body {
    font-family: 'Inter', sans-serif;
    background-color: #0f1117;
    color: #e8eaf0;
}
[data-testid="stSidebar"] {
    background-color: #161b27;
    border-right: 1px solid #1e2433;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.95rem;
    font-weight: 500;
    padding: 6px 0;
    color: #9aa3b8;
}
.card {
    background: #161b27;
    border: 1px solid #1e2433;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.card-accent { border-left: 3px solid #7c8cff; }
.card-warn   { border-left: 3px solid #ff6b6b; }
.card-ok     { border-left: 3px solid #4ecb94; }
.metric-label {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6b7694;
    margin-bottom: 4px;
}
.metric-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #e8eaf0;
    line-height: 1.1;
}
.metric-sub { font-size: 0.82rem; color: #6b7694; margin-top: 4px; }
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e8eaf0;
    margin-bottom: 16px;
}
.budget-row { margin-bottom: 14px; }
.budget-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.budget-cat { font-size: 0.88rem; font-weight: 500; color: #c4c9dc; }
.budget-amt { font-size: 0.82rem; color: #6b7694; }
.bar-bg { background: #1e2433; border-radius: 4px; height: 6px; }
.bar-fill { height: 6px; border-radius: 4px; }
.tag { display:inline-block; background:#1e2433; color:#9aa3b8; border-radius:6px; padding:2px 10px; font-size:0.78rem; font-weight:500; }
.tag-warn { background:#2d1f1f; color:#ff6b6b; }
.tag-ok   { background:#1a2d26; color:#4ecb94; }
.stButton > button {
    background: #7c8cff;
    color: #0f1117;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 10px 24px;
}
.stButton > button:hover { opacity: 0.85; }
.stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
    background: #1e2433 !important;
    color: #e8eaf0 !important;
    border: 1px solid #2a3044 !important;
    border-radius: 8px !important;
}
hr { border-color: #1e2433; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

CATEGORIES = ["Bills", "Food", "Transport", "Shopping", "Health", "Other"]

def sar(amount):
    return f"SAR {amount:,.2f}"

def pct_bar(spent, limit, over=False):
    pct = min(spent / limit * 100, 100) if limit else 0
    color = "#ff6b6b" if over else "#7c8cff"
    return f"""
    <div class="bar-bg">
      <div class="bar-fill" style="width:{pct:.1f}%;background:{color};"></div>
    </div>"""

def make_pie(labels, values, title):
    COLORS = ["#7c8cff","#4ecb94","#ff6b6b","#f7b731","#a29bfe","#fd79a8"]
    fig, ax = plt.subplots(figsize=(5, 4), facecolor="#161b27")
    wedges, _, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%",
        colors=COLORS[:len(values)], startangle=140,
        wedgeprops=dict(linewidth=1.5, edgecolor="#0f1117"),
        pctdistance=0.78,
    )
    for at in autotexts:
        at.set(color="#0f1117", fontsize=9, fontweight="bold")
    ax.set_title(title, color="#e8eaf0", fontsize=12, fontweight="bold", pad=12)
    legend = [mpatches.Patch(color=COLORS[i], label=f"{labels[i]}  {sar(values[i])}")
              for i in range(len(labels))]
    ax.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, -0.22),
              ncol=2, frameon=False, labelcolor="#9aa3b8", fontsize=8.5)
    fig.tight_layout()
    return fig

def make_bar(data, title):
    keys, vals = list(data.keys()), list(data.values())
    fig, ax = plt.subplots(figsize=(7, 3.5), facecolor="#161b27")
    ax.set_facecolor("#161b27")
    bars = ax.bar(keys, vals, color="#7c8cff", width=0.55, zorder=3)
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in vals],
                 padding=4, color="#9aa3b8", fontsize=8)
    ax.set_title(title, color="#e8eaf0", fontsize=12, fontweight="bold")
    ax.tick_params(colors="#6b7694", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e2433")
    ax.yaxis.grid(True, color="#1e2433", zorder=0)
    fig.tight_layout()
    return fig

def make_line(data, title, xlabel="Day", ylabel="SAR"):
    keys, vals = list(data.keys()), list(data.values())
    fig, ax = plt.subplots(figsize=(7, 3.5), facecolor="#161b27")
    ax.set_facecolor("#161b27")
    ax.plot(keys, vals, color="#7c8cff", linewidth=2, marker="o", markersize=5)
    ax.fill_between(keys, vals, alpha=0.1, color="#7c8cff")
    ax.set_title(title, color="#e8eaf0", fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel, color="#6b7694", fontsize=9)
    ax.set_ylabel(ylabel, color="#6b7694", fontsize=9)
    ax.tick_params(colors="#6b7694", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1e2433")
    ax.yaxis.grid(True, color="#1e2433", alpha=0.5)
    fig.tight_layout()
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding:8px 0 24px'>
      <div style='font-family:Space Grotesk;font-size:1.3rem;font-weight:700;color:#e8eaf0'>
        💳 Finance Manager
      </div>
      <div style='font-size:0.78rem;color:#6b7694;margin-top:2px'>Personal expense tracker</div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("", [
        "📊  Dashboard",
        "➕  Add Expense",
        "🔍  Search",
        "📈  Charts",
        "⚙️  Settings",
    ], label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"<div style='font-size:0.78rem;color:#6b7694'>{date.today().strftime('%A, %B %d %Y')}</div>",
                unsafe_allow_html=True)


# ── Dashboard ─────────────────────────────────────────────────────────────────

if page == "📊  Dashboard":
    today = date.today()
    year, month = today.year, today.month
    summary = monthly_summary(year, month)
    sr      = savings_rate(year, month)
    salary  = load_settings().get("salary", 0)

    st.markdown("<div class='section-title'>This Month</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("Total Spent",  sar(summary["total"]), f"{summary['count']} transactions", "card-accent"),
        ("Income",       sar(salary),            "Set in Settings",                  "card-accent"),
        ("Saved",        sar(sr["saved"]),        "After expenses",                   "card-ok" if sr["saved"] >= 0 else "card-warn"),
        ("Savings Rate", f"{sr['savings_rate']}%" if sr["savings_rate"] is not None else "—",
                         "this month's savings rate",
                         "card-ok" if sr["savings_rate"] and sr["savings_rate"] >= 20 else "card-warn"),
    ]
    for col, (label, value, sub, card_class) in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(f"""<div class='card {card_class}'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value'>{value}</div>
                <div class='metric-sub'>{sub}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    left, right = st.columns([1.6, 1])

    with left:
        st.markdown("<div class='section-title'>Budget vs. Actual</div>", unsafe_allow_html=True)
        status = budget_status(year, month)
        if not status:
            st.markdown("<div style='color:#6b7694;font-size:0.9rem'>No expenses this month yet.</div>",
                        unsafe_allow_html=True)
        for row in status:
            limit    = row["limit"]
            spent    = row["spent"]
            tag      = ("<span class='tag tag-warn'>Over budget</span>" if row["over_budget"]
                        else "<span class='tag tag-ok'>On track</span>" if limit
                        else "<span class='tag'>No limit</span>")
            limit_str = sar(limit) if limit else "No limit"
            st.markdown(f"""
            <div class='budget-row'>
              <div class='budget-header'>
                <span class='budget-cat'>{row['category']} {tag}</span>
                <span class='budget-amt'>{sar(spent)} / {limit_str}</span>
              </div>
              {pct_bar(spent, limit, row["over_budget"]) if limit else ""}
            </div>""", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-title'>Breakdown</div>", unsafe_allow_html=True)
        by_cat = summary["by_category"]
        if by_cat:
            fig = make_pie(list(by_cat.keys()), list(by_cat.values()), "")
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.markdown("<div style='color:#6b7694;font-size:0.9rem'>No data yet.</div>",
                        unsafe_allow_html=True)


# ── Add Expense ───────────────────────────────────────────────────────────────

elif page == "➕  Add Expense":
    st.markdown("<div class='section-title'>Add Expense</div>", unsafe_allow_html=True)
    col, _ = st.columns([1.2, 1])
    with col:
        with st.form("add_form", clear_on_submit=True):
            category     = st.selectbox("Category", CATEGORIES)
            amount       = st.number_input("Amount (SAR)", min_value=0.01, step=0.5, format="%.2f")
            expense_date = st.date_input("Date", value=date.today())
            submitted    = st.form_submit_button("Add Expense")

        if submitted:
            add_expense(category, amount, expense_date)
            st.success(f"Added {category} — {sar(amount)} on {expense_date}")

    st.markdown("---")
    st.markdown("<div class='section-title'>Recent Expenses</div>", unsafe_allow_html=True)
    expenses = load_expenses()
    if expenses:
        df = pd.DataFrame(expenses[-10:][::-1])[["date", "category", "amount"]]
        df.columns = ["Date", "Category", "Amount (SAR)"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("<div style='color:#6b7694'>No expenses yet.</div>", unsafe_allow_html=True)


# ── Search ────────────────────────────────────────────────────────────────────

elif page == "🔍  Search":
    st.markdown("<div class='section-title'>Search Expenses</div>", unsafe_allow_html=True)
    col, _ = st.columns([1.4, 1])
    with col:
        with st.form("search_form"):
            cat_filter = st.selectbox("Category", ["All"] + CATEGORIES)
            amt_filter = st.number_input("Exact amount (0 to skip)", min_value=0.0,
                                         step=0.5, format="%.2f")
            c1, c2 = st.columns(2)
            with c1:
                date_from = st.date_input("From", value=None)
            with c2:
                date_to = st.date_input("To", value=None)
            search_btn = st.form_submit_button("Search")

    if search_btn:
        results = search_expenses(
            category="" if cat_filter == "All" else cat_filter,
            amount=amt_filter if amt_filter > 0 else None,
            date_from=date_from,
            date_to=date_to,
        )
        st.markdown("---")
        if not results:
            st.warning("No matching expenses found.")
        else:
            total = sum(r["amount"] for r in results)
            st.markdown(f"""<div class='card card-accent' style='display:inline-block;margin-bottom:16px'>
                <span style='color:#6b7694;font-size:0.85rem'>{len(results)} result(s) · total </span>
                <span style='font-family:Space Grotesk;font-weight:700;color:#e8eaf0'>{sar(total)}</span>
            </div>""", unsafe_allow_html=True)
            df = pd.DataFrame(results)[["date", "category", "amount"]]
            df.columns = ["Date", "Category", "Amount (SAR)"]
            st.dataframe(df.sort_values("Date", ascending=False),
                         use_container_width=True, hide_index=True)


# ── Charts ────────────────────────────────────────────────────────────────────

elif page == "📈  Charts":
    st.markdown("<div class='section-title'>Charts</div>", unsafe_allow_html=True)
    expenses = load_expenses()

    if not expenses:
        st.markdown("<div style='color:#6b7694'>Add some expenses first.</div>",
                    unsafe_allow_html=True)
    else:
        tab1, tab2, tab3 = st.tabs([
            "📂 By Category",
            "📅 By Week",
            "📈 Cumulative Spending",
        ])

        # ── Tab 1: By Category ────────────────────────────────────────────────
        with tab1:
            chart_type = st.radio("Chart type", ["Pie", "Bar"], horizontal=True, key="cat_type")
            totals = aggregate_by("category")
            if totals:
                if chart_type == "Pie":
                    st.pyplot(make_pie(list(totals.keys()), list(totals.values()),
                                       "All Time by Category"), use_container_width=False)
                else:
                    st.pyplot(make_bar(totals, "All Time by Category"),
                              use_container_width=True)
            else:
                st.markdown("<div style='color:#6b7694'>No data yet.</div>", unsafe_allow_html=True)

        # ── Tab 2: By Week ────────────────────────────────────────────────────
        with tab2:
            today = date.today()
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                sel_year = st.number_input("Year", min_value=2000, max_value=today.year,
                                           value=today.year, step=1, key="week_year")
            with col2:
                sel_month = st.number_input("Month", min_value=1, max_value=12,
                                            value=today.month, step=1, key="week_month")
            with col3:
                chart_type2 = st.radio("Chart type", ["Pie", "Bar"], horizontal=True, key="week_type")

            totals = aggregate_by_week(int(sel_year), int(sel_month))
            if totals:
                month_label = date(int(sel_year), int(sel_month), 1).strftime("%B %Y")
                if chart_type2 == "Pie":
                    st.pyplot(make_pie(list(totals.keys()), list(totals.values()),
                                       f"Spending by Week — {month_label}"), use_container_width=False)
                else:
                    st.pyplot(make_bar(totals, f"Spending by Week — {month_label}"),
                              use_container_width=True)
            else:
                st.markdown("<div style='color:#6b7694'>No expenses found for this date.</div>",
                            unsafe_allow_html=True)

        # ── Tab 3: Cumulative Spending ────────────────────────────────────────
        with tab3:
            st.markdown("<div style='color:#6b7694;font-size:0.85rem;margin-bottom:12px'>Shows how your total spending builds up day by day through the month.</div>",
                        unsafe_allow_html=True)
            today = date.today()
            col1, col2 = st.columns([1, 1])
            with col1:
                cum_year = st.number_input("Year", min_value=2000, max_value=today.year,
                                           value=today.year, step=1, key="cum_year")
            with col2:
                cum_month = st.number_input("Month", min_value=1, max_value=12,
                                            value=today.month, step=1, key="cum_month")

            cum_data = cumulative_spending(int(cum_year), int(cum_month))
            if cum_data:
                month_label = date(int(cum_year), int(cum_month), 1).strftime("%B %Y")
                st.pyplot(make_line(cum_data, f"Cumulative Spending — {month_label}",
                                    xlabel="Day of Month", ylabel="SAR"),
                          use_container_width=True)
            else:
                st.markdown("<div style='color:#6b7694'>No expenses found for this date.</div>",
                            unsafe_allow_html=True)


# ── Settings ──────────────────────────────────────────────────────────────────

elif page == "⚙️  Settings":
    st.markdown("<div class='section-title'>Settings</div>", unsafe_allow_html=True)
    settings = load_settings()

    col, _ = st.columns([1.2, 1])
    with col:
        st.markdown("<div style='font-weight:600;color:#9aa3b8;margin-bottom:12px'>Monthly Income</div>",
                    unsafe_allow_html=True)
        new_salary = st.number_input("Income (SAR)", value=float(settings.get("salary", 0)),
                                     min_value=0.0, step=100.0, format="%.2f")
        if st.button("Save Income"):
            settings["salary"] = new_salary
            save_settings(settings)
            st.success("Income saved.")

    st.markdown("---")
    st.markdown("<div class='section-title'>Category Budget Limits</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#6b7694;font-size:0.85rem;margin-bottom:16px'>Monthly spending limit per category. Leave 0 for no limit.</div>",
                unsafe_allow_html=True)

    budgets = settings.get("budgets", {})
    updated = {}
    cols = st.columns(3)
    for i, cat in enumerate(CATEGORIES):
        with cols[i % 3]:
            updated[cat] = st.number_input(cat, value=float(budgets.get(cat, 0)),
                                           min_value=0.0, step=50.0, format="%.2f",
                                           key=f"budget_{cat}")
    if st.button("Save Budgets"):
        settings["budgets"] = {k: v for k, v in updated.items() if v > 0}
        save_settings(settings)
        st.success("Budgets saved.")