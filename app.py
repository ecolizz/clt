import io
import datetime
import textwrap

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import streamlit_authenticator as stauth


# ----------------------------
# Theme colors (same vibe as your Tkinter palette)
# ----------------------------
COLORS = {
    "hot_pink": "#FF4FD8",
    "bubblegum": "#FF9BEF",
    "electric_purple": "#9B5CFF",
    "neon_teal": "#00F5FF",
    "sun_yellow": "#FFF44F",
    "mint": "#7CFFCB",
    "sky_blue": "#5CD3FF",
    "lavender": "#E6C8FF",

    "dark_bg": "#3A007A",
    "light_bg": "#FFF7FE",
    "text": "#3A007A",

    "report_bg": "#F7FFFF",
    "tax_bg": "#FFFBE6",
}
# After your new COLORS dict:
# --- legacy / compatibility keys used elsewhere (charts, etc.) ---
COLORS.update({
    "pink": COLORS.get("hot_pink", "#FF4FD8"),
    "purple": COLORS.get("electric_purple", "#9B5CFF"),
    "blue": COLORS.get("sky_blue", "#5CD3FF"),
    "yellow": COLORS.get("sun_yellow", "#FFF44F"),
    "green": COLORS.get("mint", "#7CFFCB"),
    "teal": COLORS.get("neon_teal", "#00F5FF"),

    # IMPORTANT: define red if anything still uses it
    "red": "#FF2D55",  # neon-ish red/pink

    # if older code expects these
    "report_bg": COLORS.get("report_bg", "#F7FFFF"),
    "tax_bg": COLORS.get("tax_bg", "#FFFBE6"),
    "text": COLORS.get("text", "#3A007A"),
})


# ----------------------------
# Helpers (ported from your Tkinter logic)
# ----------------------------
import html
import streamlit as st

def lisa_report_box(title: str, text: str, bg1: str, bg2: str, border: str):
    safe = html.escape(text or "")

    st.markdown(f"### {title}")

    st.markdown(
        f"""
<div style="
    background: linear-gradient(135deg, {bg1}, {bg2});
    border-radius: 22px;
    padding: 18px;
    border: 6px dashed {border};
    box-shadow:
        0 0 0 3px rgba(255,255,255,0.55),
        0 14px 30px rgba(0,0,0,0.25);
    overflow-x: auto;
">
<pre style="
    margin: 0;
    padding: 0;

    font-family: Consolas, 'Cascadia Mono', 'DejaVu Sans Mono',
                 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.25;
    color: {COLORS['text']};

    white-space: pre;
    overflow-x: auto;
">{safe}</pre>
</div>
        """,
        unsafe_allow_html=True
    )



def parse_sales_summary(s_df: pd.DataFrame) -> dict[str, float]:
    out = {}
    for _, row in s_df.iterrows():
        k = str(row.iloc[0]).strip()
        v = row.iloc[1] if len(row) > 1 else None
        if k and k != "nan" and pd.notna(v):
            try:
                out[k] = float(v)
            except Exception:
                pass
    return out


def parse_expenses(exp_df: pd.DataFrame) -> pd.DataFrame:
    expenses_list = []
    curr_cat = None

    for i, row in exp_df.iterrows():
        c0 = str(row.iloc[0]).strip()

        if c0 == "Total" or "Total Expenses" in c0:
            continue

        if c0 and c0 != "nan" and c0 != "Vendor" and "Report" not in c0:
            if i + 1 < len(exp_df) and str(exp_df.iloc[i + 1, 0]) == "Vendor":
                curr_cat = c0
            elif curr_cat:
                try:
                    date_val = pd.to_datetime(row.iloc[2], errors="coerce")
                    amount_val = float(str(row.iloc[3]).replace(",", "").replace("$", ""))
                    if pd.notna(date_val):
                        expenses_list.append(
                            {"Category": curr_cat, "Vendor": row.iloc[0], "Date": date_val, "Amount": amount_val}
                        )
                except Exception:
                    pass

    return pd.DataFrame(expenses_list)


def format_line(desc, amount, pct=""):
    return f"║ {desc:<40} ║ {amount:>15} ║ {pct:>10} ║\n"


def build_report_and_tables(sales_summary, expenses_df, include_tips: bool):
    net_sales = sales_summary.get("Net Sales", 0.0)
    gratuity = sales_summary.get("Gratuity", 0.0)
    tax_collected = sales_summary.get("Tax", 0.0)
    prepayments = sales_summary.get("Prepayments For Future Sales", 0.0)

    total_rev = net_sales + tax_collected + prepayments
    if include_tips:
        total_rev += gratuity

    cogs_cats = ["Back Bar", "Inventory"]
    cogs_df = expenses_df[expenses_df["Category"].isin(cogs_cats)] if not expenses_df.empty else expenses_df
    opex_df = expenses_df[~expenses_df["Category"].isin(cogs_cats)] if not expenses_df.empty else expenses_df

    processing_fees = abs(sales_summary.get("Payment Processing Fees Paid By Business", 0.0))
    sales_tax_expense = tax_collected

    total_cogs = float(cogs_df["Amount"].sum()) if not cogs_df.empty else 0.0
    gross_margin = float(total_rev - total_cogs)
    total_opex = float((opex_df["Amount"].sum() if not opex_df.empty else 0.0) + processing_fees + sales_tax_expense)
    net_profit = float(gross_margin - total_opex)

    last_pnl_data = [
        ["REVENUE", "", ""],
        ["  Net Sales", net_sales, (net_sales / total_rev) if total_rev else 0],
        ["  Tax Collected", tax_collected, (tax_collected / total_rev) if total_rev else 0],
        ["  Prepayments", prepayments, (prepayments / total_rev) if total_rev else 0],
    ]
    if include_tips:
        last_pnl_data.append(["  Tips/Gratuity", gratuity, (gratuity / total_rev) if total_rev else 0])

    last_pnl_data.append(["TOTAL REVENUE", total_rev, 1.0])
    last_pnl_data.append(["", "", ""])
    last_pnl_data.append(["COGS", "", ""])

    for cat in cogs_cats:
        amt = float(cogs_df[cogs_df["Category"] == cat]["Amount"].sum()) if not cogs_df.empty else 0.0
        if amt > 0:
            last_pnl_data.append([f"  {cat}", amt, (amt / total_rev) if total_rev else 0])

    last_pnl_data.extend(
        [
            ["TOTAL COGS", total_cogs, (total_cogs / total_rev) if total_rev else 0],
            ["GROSS MARGIN", gross_margin, (gross_margin / total_rev) if total_rev else 0],
            ["", "", ""],
            ["OPERATING EXPENSES", "", ""],
            ["  Sales Tax Paid Out", sales_tax_expense, (sales_tax_expense / total_rev) if total_rev else 0],
            ["  Processing Fees", processing_fees, (processing_fees / total_rev) if total_rev else 0],
        ]
    )

    if not opex_df.empty:
        cat_totals = opex_df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
        for cat, amt in cat_totals.items():
            amt = float(amt)
            last_pnl_data.append([f"  {cat}", amt, (amt / total_rev) if total_rev else 0])

    last_pnl_data.extend(
        [
            ["TOTAL OPEX", total_opex, (total_opex / total_rev) if total_rev else 0],
            ["NET PROFIT", net_profit, (net_profit / total_rev) if total_rev else 0],
        ]
    )

    rep = f"{' ' * 20}PROFIT & LOSS STATEMENT - All Year\n"
    rep += f"╔{'═'*42}╦{'═'*17}╦{'═'*12}╗\n"
    rep += format_line("DESCRIPTION", "AMOUNT ($)", "% OF REV")
    rep += f"╠{'═'*42}╬{'═'*17}╬{'═'*12}╣\n"

    for row in last_pnl_data:
        if row[0] and not row[1] and not row[2]:
            rep += f"║ {row[0]:<40} ║ {'':>15} ║ {'':>10} ║\n"
        elif not row[0]:
            rep += f"╠{'─'*42}╬{'─'*17}╬{'─'*12}╣\n"
        else:
            rep += format_line(row[0], f"{row[1]:,.2f}", f"{(row[2]*100):.1f}%")

    rep += f"╚{'═'*42}╩{'═'*17}╩{'═'*12}╝\n"
    return rep, last_pnl_data, net_profit


def calc_hanover_tax_text(net: float, fed_income_rate: float, local_eit_rate: float):
    se_tax = (net * 0.9235) * 0.153
    fed_inc = max(0, net - (se_tax * 0.5)) * (fed_income_rate / 100)
    pa_state = net * 0.0307
    pa_local = net * (local_eit_rate / 100)
    lst = 52.0 if net > 12000 else 0
    total_tax = se_tax + fed_inc + pa_state + pa_local + lst

    txt = (
        "ESTIMATED TAX LIABILITY (HANOVER, PA)\n"
        + "=" * 50
        + "\n"
        + f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        + f"Business Profit:  ${net:,.2f}\n"
        + f"{'-' * 50}\n"
        + f"Fed SE Tax (15.3%):               ${se_tax:,.2f}\n"
        + f"Fed Income Tax ({fed_income_rate}%):           ${fed_inc:,.2f}\n"
        + f"PA State Tax (3.07%):             ${pa_state:,.2f}\n"
        + f"Hanover Local EIT ({local_eit_rate}%):          ${pa_local:,.2f}\n"
        + f"PA Local Services Tax (LST):      ${lst:,.2f}\n"
        + "=" * 50
        + "\n"
        + f"TOTAL ESTIMATED TAX DUE:          ${total_tax:,.2f}\n"
        + f"ESTIMATED TAKE-HOME:              ${net - total_tax:,.2f}\n"
    )
    return txt, total_tax


def draw_charts(expenses_df: pd.DataFrame):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    fig.patch.set_facecolor(COLORS["light_bg"])

    if expenses_df is not None and not expenses_df.empty:
        top_v = expenses_df.groupby("Vendor")["Amount"].sum().sort_values(ascending=False).head(5)
        wrapped_labels = [textwrap.fill(str(label), width=15) for label in top_v.index]
        top_v.plot(kind="bar", ax=ax1, color=[COLORS["pink"], COLORS["purple"], COLORS["blue"], COLORS["yellow"], COLORS["teal"]])
        ax1.set_xticklabels(wrapped_labels, rotation=30, ha="right")
        ax1.set_title("Top 5 Vendor Spend")
        ax1.set_facecolor(COLORS["report_bg"])

        expense_breakdown = expenses_df.groupby("Category")["Amount"].sum()
        pie_colors = [COLORS["pink"], COLORS["purple"], COLORS["blue"], COLORS["yellow"], COLORS["green"], COLORS["red"]]
        colors_for_pie = [pie_colors[i % len(pie_colors)] for i in range(len(expense_breakdown))]
        pie_labels = [textwrap.fill(str(label), width=20) for label in expense_breakdown.index]
        ax2.pie(expense_breakdown, labels=pie_labels, autopct="%1.1f%%", colors=colors_for_pie, textprops={"color": COLORS["text"]})
        ax2.set_title("Expense Breakdown by Category")
    else:
        ax1.text(0.5, 0.5, "No expense data available", ha="center", va="center", transform=ax1.transAxes)
        ax2.text(0.5, 0.5, "No expense data available", ha="center", va="center", transform=ax2.transAxes)

    plt.tight_layout()
    return fig


# ----------------------------
# Page + style
# ----------------------------
st.set_page_config(page_title="Custom Lash Therapy Suite", layout="wide")
st.markdown(
    f"""
    <style>

    /* 🌈 App background */
    .stApp {{
        background: radial-gradient(circle at top left,
            {COLORS["hot_pink"]},
            {COLORS["electric_purple"]},
            {COLORS["dark_bg"]});
    }}

    /* 🧁 Main content card */
    .block-container {{
        background: linear-gradient(135deg,
            {COLORS["light_bg"]},
            {COLORS["lavender"]});
        border-radius: 22px;
        padding: 1.6rem 1.6rem 2.4rem 1.6rem;
        box-shadow:
            0 0 0 4px {COLORS["bubblegum"]},
            0 20px 40px rgba(0,0,0,.35);
    }}

    /* ✨ Fonts */
    h1, h2, h3, label, p, div {{
        color: {COLORS["text"]} !important;
        font-family: "Comic Sans MS", "Trebuchet MS", sans-serif;
    }}

    h1 {{
        text-shadow: 2px 2px 0 {COLORS["sun_yellow"]};
    }}

    /* 🌈 Tabs */
    button[data-baseweb="tab"] {{
        background: linear-gradient(135deg,
            {COLORS["bubblegum"]},
            {COLORS["electric_purple"]});
        color: white !important;
        border-radius: 16px;
        margin-right: 6px;
        font-weight: 800;
        box-shadow: 0 4px 10px rgba(0,0,0,.25);
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg,
            {COLORS["sun_yellow"]},
            {COLORS["neon_teal"]});
        color: {COLORS["dark_bg"]} !important;
        box-shadow: 0 0 12px {COLORS["neon_teal"]};
    }}

    /* 💎 Buttons */
    .stButton>button {{
        background: linear-gradient(135deg,
            {COLORS["hot_pink"]},
            {COLORS["neon_teal"]});
        color: white;
        border-radius: 18px;
        font-weight: 900;
        border: none;
        box-shadow:
            0 6px 14px rgba(0,0,0,.35),
            inset 0 0 8px rgba(255,255,255,.6);
        transition: transform .15s ease, box-shadow .15s ease;
    }}

    .stButton>button:hover {{
        transform: scale(1.05);
        box-shadow: 0 0 18px {COLORS["sun_yellow"]};
    }}

    </style>
    """,
    unsafe_allow_html=True
)



# ----------------------------
# Login (2 users) from st.secrets
# ----------------------------
# Secrets come from Streamlit Cloud Secrets UI (recommended) or local .streamlit/secrets.toml
# creds = st.secrets["auth"]["credentials"]
# cookie_name = st.secrets["auth"]["cookie"]["name"]
# cookie_key = st.secrets["auth"]["cookie"]["key"]
# cookie_expiry_days = int(st.secrets["auth"]["cookie"]["expiry_days"])

# authenticator = stauth.Authenticate(
#     creds,
#     cookie_name=cookie_name,
#     cookie_key=cookie_key,
#     cookie_expiry_days=cookie_expiry_days,
# )

# name, authentication_status, username = authenticator.login("Login", "main")

# if authentication_status is False:
#     st.error("Username/password is incorrect.")
#     st.stop()
# elif authentication_status is None:
#     st.warning("Please enter your username and password.")
#     st.stop()

# authenticator.logout("Logout", "sidebar")
# st.sidebar.success(f"Signed in as: {name}")


# ----------------------------
# Session state (keeps you and her separate)
# ----------------------------
if "sales_df" not in st.session_state:
    st.session_state.sales_df = None
if "exp_df_raw" not in st.session_state:
    st.session_state.exp_df_raw = None
if "report_text" not in st.session_state:
    st.session_state.report_text = ""
if "last_pnl_data" not in st.session_state:
    st.session_state.last_pnl_data = []
if "net_profit" not in st.session_state:
    st.session_state.net_profit = 0.0
if "tax_text" not in st.session_state:
    st.session_state.tax_text = ""


# ----------------------------
# UI Tabs (like your Notebook)
# ----------------------------
st.title("Custom Lash Therapy: Financials & Tax Suite")
#tab1, tab2, tab3 = st.tabs(["P&L & Reports", "Charts & Analytics", "Tax Estimator"])
tab1, tab2, tab3 = st.tabs([
    "💖 P&L & Reports",
    "📊 Charts & Analytics",
    "🧾 Tax Estimator"
])


with tab1:
    st.subheader("Import Data")

    c1, c2 = st.columns([1, 1])
    with c1:
        sales_file = st.file_uploader("Load Sales File (.csv/.xlsx)", type=["csv", "xlsx", "xls"], key="sales_upload")
    with c2:
        exp_file = st.file_uploader("Load Expenses File (.csv/.xlsx)", type=["csv", "xlsx", "xls"], key="exp_upload")

    include_tips = st.checkbox("Include Tips", value=True)

    cA, cB = st.columns([1, 1])
    with cA:
        if st.button("GENERATE REPORT", type="primary", use_container_width=True):
            if sales_file is None or exp_file is None:
                st.error("Load both files first!")
            else:
                # read
                if sales_file.name.lower().endswith(".csv"):
                    s_df = pd.read_csv(sales_file, header=None)
                else:
                    s_df = pd.read_excel(sales_file, header=None)

                if exp_file.name.lower().endswith(".csv"):
                    e_df_raw = pd.read_csv(exp_file, header=None)
                else:
                    e_df_raw = pd.read_excel(exp_file, header=None)

                st.session_state.sales_df = s_df
                st.session_state.exp_df_raw = e_df_raw

                sales_summary = parse_sales_summary(s_df)
                expenses_df = parse_expenses(e_df_raw)

                report_text, last_pnl_data, net_profit = build_report_and_tables(sales_summary, expenses_df, include_tips)
                st.session_state.report_text = report_text
                st.session_state.last_pnl_data = last_pnl_data
                st.session_state.net_profit = net_profit

                # update tax too (default rates)
                fed_rate = float(st.session_state.get("fed_income_rate", 12.0))
                local_rate = float(st.session_state.get("local_eit_rate", 1.0))
                tax_txt, _ = calc_hanover_tax_text(net_profit, fed_rate, local_rate)
                st.session_state.tax_text = tax_txt

                st.success("Report generated!")

    with cB:
        if st.session_state.last_pnl_data:
            df_export = pd.DataFrame(st.session_state.last_pnl_data, columns=["Description", "Amount ($)", "% of Total"])
            excel_bytes = io.BytesIO()
            with pd.ExcelWriter(excel_bytes, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False, sheet_name="P&L Report")
            excel_bytes.seek(0)

            st.download_button(
                "DOWNLOAD TO EXCEL",
                data=excel_bytes.getvalue(),
                file_name=f"Pnl_Report_{datetime.date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.button("DOWNLOAD TO EXCEL", disabled=True, use_container_width=True)

    st.subheader("Report")
    st.code(st.session_state.report_text or "Load files and click GENERATE REPORT...", language="text")

with tab2:
    st.subheader("Charts & Analytics")
    if st.session_state.exp_df_raw is None:
        st.info("Generate a report first to load expense data.")
    else:
        expenses_df = parse_expenses(st.session_state.exp_df_raw)
        fig = draw_charts(expenses_df)
        st.pyplot(fig, clear_figure=True)

with tab3:
    st.subheader("Tax Estimator")

    c1, c2 = st.columns(2)
    with c1:
        fed_income_rate = st.number_input("Fed Income Tax Est (%)", min_value=0.0, max_value=60.0, value=float(st.session_state.get("fed_income_rate", 12.0)), step=0.5)
        st.session_state.fed_income_rate = fed_income_rate

    with c2:
        local_eit_rate = st.number_input("Hanover EIT Local (%)", min_value=0.0, max_value=10.0, value=float(st.session_state.get("local_eit_rate", 1.0)), step=0.1)
        st.session_state.local_eit_rate = local_eit_rate

    if st.button("RECALCULATE", use_container_width=True):
        tax_txt, _ = calc_hanover_tax_text(st.session_state.net_profit, fed_income_rate, local_eit_rate)
        st.session_state.tax_text = tax_txt
        st.success("Tax recalculated!")

    st.code(st.session_state.tax_text or "Generate a P&L report to populate net profit, then recalculate taxes.", language="text")

    # Download button (unchanged)
    if st.session_state.get("tax_text"):
        st.download_button(
            "SAVE TAX REPORT",
            data=st.session_state.tax_text.encode("utf-8"),
            file_name=f"Tax_Report_{datetime.date.today().isoformat()}.txt",
            mime="text/plain",
            use_container_width=True,
        )








