"""
streamlit_app.py
----------------
India Research — Custom Screener
Reads from data/companies.json — no database, no connection strings.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="India Research · Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_FILE    = "data/companies.json"
META_FILE    = "data/meta.json"
SAVED_FILE   = "data/saved_screeners.json"

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_companies() -> list[dict]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

@st.cache_data(ttl=3600)
def load_meta() -> dict:
    if not os.path.exists(META_FILE):
        return {}
    with open(META_FILE) as f:
        return json.load(f)

def load_saved_screeners() -> dict:
    if not os.path.exists(SAVED_FILE):
        return {}
    with open(SAVED_FILE) as f:
        return json.load(f)

def save_screener_to_file(name: str, filters: list, sector: str):
    screeners = load_saved_screeners()
    screeners[name] = {
        "filters": filters,
        "sector":  sector,
        "saved_at": datetime.utcnow().isoformat(),
    }
    os.makedirs("data", exist_ok=True)
    with open(SAVED_FILE, "w") as f:
        json.dump(screeners, f, indent=2)

def delete_screener_from_file(name: str):
    screeners = load_saved_screeners()
    screeners.pop(name, None)
    with open(SAVED_FILE, "w") as f:
        json.dump(screeners, f, indent=2)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_cr(val):
    if val is None or val == "":
        return "—"
    try:
        v = float(val)
        if v >= 100000: return f"₹{v/100000:.2f}L Cr"
        if v >= 1000:   return f"₹{v/1000:.1f}K Cr"
        return f"₹{v:,.0f} Cr"
    except Exception:
        return "—"

def fmt_num(val, prefix="", suffix="", dec=2):
    if val is None:
        return "—"
    try:
        return f"{prefix}{float(val):.{dec}f}{suffix}"
    except Exception:
        return "—"

def rec_color(rec):
    if not rec:
        return ""
    r = rec.lower()
    if "strong_buy" in r or "buy" in r:
        return "🟢"
    if "hold" in r or "neutral" in r:
        return "🟡"
    if "sell" in r or "under" in r:
        return "🔴"
    return ""

# ── Filter definitions ────────────────────────────────────────────────────────

FILTERS = {
    "Valuation": {
        "P/E Ratio":             ("pe_ratio",          0.0,  200.0,  0.5),
        "P/B Ratio":             ("pb_ratio",          0.0,   50.0,  0.1),
        "P/S Ratio":             ("ps_ratio",          0.0,   50.0,  0.1),
        "EV/EBITDA":             ("ev_ebitda",         0.0,   80.0,  0.5),
        "PEG Ratio":             ("peg_ratio",         0.0,   10.0,  0.1),
    },
    "Profitability": {
        "ROE (%)":               ("roe_pct",         -50.0,  100.0,  1.0),
        "ROA (%)":               ("roa_pct",         -50.0,   50.0,  0.5),
        "Gross Margin (%)":      ("gross_margin_pct",  0.0,  100.0,  1.0),
        "Operating Margin (%)":  ("op_margin_pct",   -50.0,  100.0,  1.0),
        "Net Margin (%)":        ("net_margin_pct",  -50.0,  100.0,  1.0),
    },
    "Growth": {
        "Revenue Growth (%)":    ("revenue_growth_pct", -50.0, 300.0, 1.0),
        "EPS Growth (%)":        ("eps_growth_pct",   -100.0, 500.0, 5.0),
    },
    "Size": {
        "Market Cap (Cr)":       ("market_cap_cr",    500.0, 2000000.0, 500.0),
        "Revenue (Cr)":          ("revenue_cr",         0.0,  500000.0, 500.0),
        "Cash (Cr)":             ("cash_cr",            0.0,  200000.0, 500.0),
    },
    "Financial Health": {
        "Debt/Equity":           ("debt_to_equity",    0.0,   20.0,  0.1),
        "Current Ratio":         ("current_ratio",     0.0,   10.0,  0.1),
        "Quick Ratio":           ("quick_ratio",       0.0,   10.0,  0.1),
    },
    "Dividends": {
        "Dividend Yield (%)":    ("dividend_yield_pct", 0.0,  20.0,  0.25),
        "Payout Ratio (%)":      ("payout_ratio_pct",   0.0, 100.0,  1.0),
    },
    "Market": {
        "Beta":                  ("beta",             -2.0,    5.0,  0.1),
        "52W High (₹)":          ("week_52_high",      0.0, 50000.0, 50.0),
        "52W Low (₹)":           ("week_52_low",       0.0, 50000.0, 50.0),
    },
}

# ── Screener engine ───────────────────────────────────────────────────────────

def run_screener(companies, filters, sector_filter, sort_col, sort_asc) -> pd.DataFrame:
    results = []

    for c in companies:
        # Sector filter
        if sector_filter and sector_filter != "All sectors":
            if c.get("sector") != sector_filter:
                continue

        # Skip below 500 Cr
        mc = c.get("market_cap_cr")
        if mc is not None and mc < 500:
            continue

        # Apply all filters
        passed = True
        for f in filters:
            val = c.get(f["column"])
            if val is None:
                passed = False
                break
            try:
                fval = float(val)
                if f["operator"] == "≤" and not (fval <= f["value"]):
                    passed = False; break
                if f["operator"] == "≥" and not (fval >= f["value"]):
                    passed = False; break
            except Exception:
                passed = False; break

        if not passed:
            continue

        results.append({
            "Ticker":         c.get("ticker_short", ""),
            "Company":        c.get("name", ""),
            "Sector":         c.get("sector", "—"),
            "Mkt Cap":        fmt_cr(c.get("market_cap_cr")),
            "Price (₹)":      c.get("current_price"),
            "P/E":            c.get("pe_ratio"),
            "P/B":            c.get("pb_ratio"),
            "EV/EBITDA":      c.get("ev_ebitda"),
            "ROE %":          c.get("roe_pct"),
            "Net Margin %":   c.get("net_margin_pct"),
            "Rev Growth %":   c.get("revenue_growth_pct"),
            "D/E":            c.get("debt_to_equity"),
            "Div Yield %":    c.get("dividend_yield_pct"),
            "Rating":         (rec_color(c.get("recommendation")) + " " + (c.get("recommendation") or "—")).strip(),
            "Fetched":        (c.get("fetched_at") or "")[:10],
            "_ticker_full":   c.get("ticker", ""),
            "_mkt_cap_num":   c.get("market_cap_cr") or 0,
        })

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    sort_map = {
        "Market Cap":      "_mkt_cap_num",
        "P/E Ratio":       "P/E",
        "P/B Ratio":       "P/B",
        "ROE %":           "ROE %",
        "Net Margin %":    "Net Margin %",
        "Revenue Growth %":"Rev Growth %",
        "Dividend Yield %":"Div Yield %",
    }
    sk = sort_map.get(sort_col, "_mkt_cap_num")
    if sk in df.columns:
        df = df.sort_values(sk, ascending=sort_asc, na_position="last")

    return df

# ── Company detail ─────────────────────────────────────────────────────────────

def show_company_detail(ticker_full: str, companies: list):
    c = next((x for x in companies if x.get("ticker") == ticker_full), None)
    if not c:
        st.warning("Company data not found.")
        return

    # Header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"### {c.get('name', ticker_full)}")
        st.caption(
            f"`{c.get('ticker_short')}` · {c.get('sector','—')} · {c.get('industry','—')}"
        )
    with col2:
        price = c.get("current_price")
        st.metric("Price", f"₹{price:,.2f}" if price else "—")
    with col3:
        st.metric("Market Cap", fmt_cr(c.get("market_cap_cr")))

    # Source citation — always visible
    fetched = (c.get("fetched_at") or "")[:10]
    st.caption(
        f"📋 **Source:** [{c.get('source_name','Yahoo Finance')}]({c.get('source_url','#')}) "
        f"· Fetched: {fetched} · "
        f"[Open on Yahoo Finance]({c.get('source_url','#')})"
    )

    # Recommendation badge
    rec = c.get("recommendation", "")
    if rec:
        target = c.get("target_price")
        analysts = c.get("analyst_count")
        target_str = f" · Target ₹{target:,.2f} ({analysts} analysts)" if target else ""
        st.info(f"{rec_color(rec)} Analyst consensus: **{rec.upper()}**{target_str}")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Ratios", "📄 Financials", "📈 Earnings", "📰 News"])

    with tab1:
        st.markdown("**Valuation**")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("P/E",      fmt_num(c.get("pe_ratio")))
        c2.metric("P/B",      fmt_num(c.get("pb_ratio")))
        c3.metric("EV/EBITDA",fmt_num(c.get("ev_ebitda")))
        c4.metric("PEG",      fmt_num(c.get("peg_ratio")))
        c5.metric("P/S",      fmt_num(c.get("ps_ratio")))

        st.markdown("**Profitability**")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("ROE",          fmt_num(c.get("roe_pct"),    suffix="%"))
        c2.metric("ROA",          fmt_num(c.get("roa_pct"),    suffix="%"))
        c3.metric("Gross Margin", fmt_num(c.get("gross_margin_pct"), suffix="%"))
        c4.metric("Op. Margin",   fmt_num(c.get("op_margin_pct"),   suffix="%"))
        c5.metric("Net Margin",   fmt_num(c.get("net_margin_pct"),  suffix="%"))

        st.markdown("**Financial health**")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("D/E Ratio",     fmt_num(c.get("debt_to_equity")))
        c2.metric("Current Ratio", fmt_num(c.get("current_ratio")))
        c3.metric("Quick Ratio",   fmt_num(c.get("quick_ratio")))
        c4.metric("Beta",          fmt_num(c.get("beta")))
        c5.metric("Div Yield",     fmt_num(c.get("dividend_yield_pct"), suffix="%"))

        # 52-week range bar
        hi  = c.get("week_52_high")
        lo  = c.get("week_52_low")
        cp  = c.get("current_price")
        if hi and lo and cp and hi != lo:
            pct = max(0.0, min(1.0, (cp - lo) / (hi - lo)))
            st.markdown("**52-week range**")
            st.progress(pct, text=f"Low ₹{lo:,.0f}  ·  Current ₹{cp:,.0f}  ·  High ₹{hi:,.0f}  ({pct*100:.0f}% of range)")

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Income statement**")
            rows = [
                ("Revenue",          fmt_cr(c.get("revenue_cr"))),
                ("Revenue growth",   fmt_num(c.get("revenue_growth_pct"), suffix="%")),
                ("Gross profit",     fmt_cr(c.get("gross_profit_cr"))),
                ("EBITDA",           fmt_cr(c.get("ebitda_cr"))),
                ("Net income",       fmt_cr(c.get("net_income_cr"))),
                ("EPS",              fmt_num(c.get("eps"), prefix="₹")),
                ("EPS growth",       fmt_num(c.get("eps_growth_pct"), suffix="%")),
            ]
            st.table(pd.DataFrame(rows, columns=["Metric","Value"]).set_index("Metric"))
        with c2:
            st.markdown("**Balance sheet**")
            rows = [
                ("Total assets",     fmt_cr(c.get("total_assets_cr"))),
                ("Total debt",       fmt_cr(c.get("total_debt_cr"))),
                ("Cash",             fmt_cr(c.get("cash_cr"))),
                ("Book value/share", fmt_num(c.get("book_value"), prefix="₹")),
                ("Enterprise value", fmt_cr(c.get("enterprise_value_cr"))),
                ("Dividend rate",    fmt_num(c.get("dividend_rate"), prefix="₹")),
                ("Payout ratio",     fmt_num(c.get("payout_ratio_pct"), suffix="%")),
            ]
            st.table(pd.DataFrame(rows, columns=["Metric","Value"]).set_index("Metric"))

        st.caption(
            f"Source: {c.get('source_name','Yahoo Finance')} · "
            f"[{c.get('source_url','')}]({c.get('source_url','#')})"
        )

    with tab3:
        st.info(
            "Earnings history is fetched from Yahoo Finance. "
            "If empty, run a manual financial refresh from the GitHub Actions tab."
        )
        # yfinance quarterly earnings aren't stored in the JSON yet
        # Show what we have from the info dict
        eps     = c.get("eps")
        eps_g   = c.get("eps_growth_pct")
        rev_g   = c.get("revenue_growth_pct")
        if eps or eps_g or rev_g:
            rows = [
                ("Trailing EPS",    fmt_num(eps, prefix="₹")),
                ("EPS growth (YoY)",fmt_num(eps_g, suffix="%")),
                ("Revenue growth",  fmt_num(rev_g, suffix="%")),
            ]
            st.table(pd.DataFrame(rows, columns=["Metric","Value"]).set_index("Metric"))
        st.caption(f"Source: {c.get('source_name','Yahoo Finance')} · {c.get('fetched_at','')[:10]}")

    with tab4:
        news = c.get("news", [])
        if news:
            for n in news:
                st.markdown(f"**[{n.get('title','')}]({n.get('link','#')})**")
                st.caption(
                    f"{n.get('publisher','Yahoo Finance')} · {n.get('published','')} · "
                    f"[Read →]({n.get('link','#')})"
                )
                st.divider()
        else:
            st.info("No news available. News refreshes every 3 days via GitHub Actions.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("📊 India Research — Custom Screener")
st.caption("NSE companies · ₹500 Cr+ market cap · Data: Yahoo Finance via yfinance · Updated monthly")

# Load data
companies = load_companies()
meta      = load_meta()

# Session state
if "filters" not in st.session_state:
    st.session_state.filters = []
if "results" not in st.session_state:
    st.session_state.results = None

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Screener filters")

    # Sector filter
    sectors = sorted(set(c.get("sector","") for c in companies if c.get("sector")))
    sector_filter = st.selectbox("Sector", ["All sectors"] + sectors)

    st.divider()

    # Add filter row
    st.markdown("**Add a filter**")
    cat    = st.selectbox("Category", list(FILTERS.keys()), key="cat")
    metric = st.selectbox("Metric",   list(FILTERS[cat].keys()), key="metric")
    col_key, min_v, max_v, step = FILTERS[cat][metric]

    operator = st.radio("Operator", ["≤", "≥"], horizontal=True)
    default  = round(min_v + (max_v - min_v) * 0.25, 2)
    value    = st.number_input(
        "Value", min_value=float(min_v), max_value=float(max_v),
        value=float(default), step=float(step)
    )

    if st.button("➕ Add filter", use_container_width=True, type="primary"):
        st.session_state.filters.append({
            "label":    f"{metric} {operator} {value}",
            "column":   col_key,
            "operator": operator,
            "value":    float(value),
        })
        st.rerun()

    # Active filters
    if st.session_state.filters:
        st.divider()
        st.markdown("**Active filters**")
        to_remove = []
        for i, f in enumerate(st.session_state.filters):
            ca, cb = st.columns([5, 1])
            ca.markdown(f"<small>{'🔵'} {f['label']}</small>", unsafe_allow_html=True)
            if cb.button("✕", key=f"rm_{i}"):
                to_remove.append(i)
        for i in reversed(to_remove):
            st.session_state.filters.pop(i)
        if st.button("🗑 Clear all", use_container_width=True):
            st.session_state.filters = []
            st.session_state.results = None
            st.rerun()

    st.divider()

    # Sort options
    st.markdown("**Sort by**")
    sort_col = st.selectbox(
        "", ["Market Cap","P/E Ratio","P/B Ratio","ROE %",
             "Net Margin %","Revenue Growth %","Dividend Yield %"],
        label_visibility="collapsed"
    )
    sort_asc = st.checkbox("Ascending", value=False)

    st.divider()

    # Run screener
    if st.button("▶  Run screener", use_container_width=True, type="primary"):
        if not companies:
            st.error("No data loaded. Trigger a fetch from GitHub Actions first.")
        else:
            with st.spinner(f"Screening {len(companies)} companies..."):
                st.session_state.results = run_screener(
                    companies, st.session_state.filters,
                    sector_filter, sort_col, sort_asc
                )
            st.rerun()

    st.divider()

    # Save / load screeners
    st.markdown("**Save screener**")
    s_name = st.text_input("Name", placeholder="e.g. Quality large caps")
    if st.button("💾 Save", use_container_width=True):
        if not s_name.strip():
            st.warning("Enter a name first")
        elif not st.session_state.filters:
            st.warning("Add at least one filter")
        else:
            save_screener_to_file(s_name.strip(), st.session_state.filters, sector_filter)
            st.success(f"Saved '{s_name}'")
            st.rerun()

    saved = load_saved_screeners()
    if saved:
        st.markdown("**Saved screeners**")
        for name, data in saved.items():
            ca, cb = st.columns([4, 1])
            if ca.button(f"📂 {name}", key=f"load_{name}", use_container_width=True):
                st.session_state.filters = data["filters"]
                st.rerun()
            if cb.button("✕", key=f"del_{name}"):
                delete_screener_from_file(name)
                st.rerun()

    st.divider()

    # Status
    st.markdown("**Status**")
    if meta:
        last_fin  = (meta.get("last_financial_update") or "")[:10]
        last_news = (meta.get("last_news_update") or "")[:10]
        total     = meta.get("total_companies", 0)
        st.caption(f"Companies: **{total:,}**")
        st.caption(f"Financials: {last_fin or 'never'}")
        st.caption(f"News: {last_news or 'never'}")
        st.caption(f"Source: {meta.get('source','Yahoo Finance')}")
    elif not companies:
        st.warning("No data yet. Go to GitHub → Actions → Run workflow.")
    else:
        st.caption(f"{len(companies)} companies loaded")

# ── Main area ─────────────────────────────────────────────────────────────────

if not companies:
    st.warning(
        "**No data loaded yet.** \n\n"
        "Go to your GitHub repo → **Actions** tab → **Data refresh** → "
        "**Run workflow** → select **both** → click **Run workflow**. "
        "It takes ~25 minutes to fetch all companies."
    )
    st.stop()

if st.session_state.results is None:
    # Welcome
    st.markdown("### Build your screener")
    st.markdown("Add filters in the sidebar, then click **Run screener**.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**Quality screen**\n\nROE ≥ 15%\n\nNet Margin ≥ 10%\n\nD/E ≤ 0.5\n\nMarket Cap ≥ 5000 Cr")
    with c2:
        st.info("**Value screen**\n\nP/E ≤ 15\n\nP/B ≤ 2\n\nDiv Yield ≥ 2%\n\nMarket Cap ≥ 2000 Cr")
    with c3:
        st.info("**Growth screen**\n\nRev Growth ≥ 20%\n\nEPS Growth ≥ 15%\n\nROE ≥ 12%\n\nMarket Cap ≥ 1000 Cr")

elif len(st.session_state.results) == 0:
    st.warning("No companies match your filters. Try relaxing one or more criteria.")

else:
    df = st.session_state.results
    n  = len(df)

    # Summary bar
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Results",     n)
    c2.metric("Median P/E",  f"{df['P/E'].dropna().median():.1f}x" if df['P/E'].notna().any() else "—")
    c3.metric("Median ROE",  f"{df['ROE %'].dropna().median():.1f}%" if df['ROE %'].notna().any() else "—")
    c4.metric("Sectors",     df["Sector"].nunique())

    st.divider()

    # Results table
    display_cols = ["Ticker","Company","Sector","Mkt Cap","Price (₹)",
                    "P/E","P/B","ROE %","Net Margin %","Rev Growth %","D/E","Rating","Fetched"]
    show_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[show_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price (₹)":     st.column_config.NumberColumn(format="₹%.2f"),
            "P/E":           st.column_config.NumberColumn(format="%.1f"),
            "P/B":           st.column_config.NumberColumn(format="%.2f"),
            "ROE %":         st.column_config.NumberColumn(format="%.1f"),
            "Net Margin %":  st.column_config.NumberColumn(format="%.1f"),
            "Rev Growth %":  st.column_config.NumberColumn(format="%.1f"),
            "D/E":           st.column_config.NumberColumn(format="%.2f"),
        }
    )

    # Source line — always shown
    st.caption(
        "📋 All data from **Yahoo Finance via yfinance**. "
        "Click any company below to see its source URL and fetch date. "
        "[Verify on Yahoo Finance →](https://finance.yahoo.com)"
    )

    # Export
    csv = df[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Export CSV",
        csv,
        file_name=f"screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    st.divider()

    # Company detail drill-down
    st.markdown("### Company detail")
    tickers_list = df["Ticker"].tolist()
    selected = st.selectbox("Select company", ["— select —"] + tickers_list)
    if selected and selected != "— select —":
        ticker_full = df[df["Ticker"] == selected]["_ticker_full"].values[0]
        show_company_detail(ticker_full, companies)

    st.divider()

    # Compare two
    st.markdown("### Compare two companies")
    ca_col, cb_col = st.columns(2)
    with ca_col:
        cmp_a = st.selectbox("Company A", ["— select —"] + tickers_list, key="cmp_a")
    with cb_col:
        cmp_b = st.selectbox("Company B", ["— select —"] + tickers_list, key="cmp_b")

    if cmp_a != "— select —" and cmp_b != "— select —" and cmp_a != cmp_b:
        ta = df[df["Ticker"] == cmp_a]["_ticker_full"].values[0]
        tb = df[df["Ticker"] == cmp_b]["_ticker_full"].values[0]
        ca = next((x for x in companies if x["ticker"] == ta), {})
        cb = next((x for x in companies if x["ticker"] == tb), {})

        if ca.get("sector") != cb.get("sector"):
            st.warning(
                f"⚠ Different sectors: **{ca.get('sector','?')}** vs **{cb.get('sector','?')}** "
                "— direct ratio comparisons may be misleading."
            )

        rows = [
            ("Sector",           ca.get("sector","—"),                cb.get("sector","—")),
            ("Market Cap",       fmt_cr(ca.get("market_cap_cr")),     fmt_cr(cb.get("market_cap_cr"))),
            ("Price (₹)",        fmt_num(ca.get("current_price"),"₹"),fmt_num(cb.get("current_price"),"₹")),
            ("P/E Ratio",        fmt_num(ca.get("pe_ratio")),         fmt_num(cb.get("pe_ratio"))),
            ("P/B Ratio",        fmt_num(ca.get("pb_ratio")),         fmt_num(cb.get("pb_ratio"))),
            ("EV/EBITDA",        fmt_num(ca.get("ev_ebitda")),        fmt_num(cb.get("ev_ebitda"))),
            ("ROE %",            fmt_num(ca.get("roe_pct"),suffix="%"),fmt_num(cb.get("roe_pct"),suffix="%")),
            ("Net Margin %",     fmt_num(ca.get("net_margin_pct"),suffix="%"),fmt_num(cb.get("net_margin_pct"),suffix="%")),
            ("Revenue",          fmt_cr(ca.get("revenue_cr")),        fmt_cr(cb.get("revenue_cr"))),
            ("Net Income",       fmt_cr(ca.get("net_income_cr")),     fmt_cr(cb.get("net_income_cr"))),
            ("D/E Ratio",        fmt_num(ca.get("debt_to_equity")),   fmt_num(cb.get("debt_to_equity"))),
            ("Div Yield %",      fmt_num(ca.get("dividend_yield_pct"),suffix="%"),fmt_num(cb.get("dividend_yield_pct"),suffix="%")),
            ("Analyst Rating",   (ca.get("recommendation","—")).upper(),(cb.get("recommendation","—")).upper()),
            ("Target Price",     fmt_num(ca.get("target_price"),"₹"), fmt_num(cb.get("target_price"),"₹")),
            ("Data source",      ca.get("source_name","Yahoo Finance"),cb.get("source_name","Yahoo Finance")),
            ("Last fetched",     (ca.get("fetched_at",""))[:10],      (cb.get("fetched_at",""))[:10]),
        ]
        cmp_df = pd.DataFrame(rows, columns=["Metric", cmp_a, cmp_b])
        st.dataframe(cmp_df.set_index("Metric"), use_container_width=True)
        st.caption("Source: Yahoo Finance via yfinance")
