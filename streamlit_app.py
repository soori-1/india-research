"""
India Research — Custom Screener
Streamlit app that reads from Supabase (or local SQLite in dev).
Every result shows its data source so nothing is presented without citation.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

from database import (
    SessionLocal, Financials, Company, SavedScreener,
    EarningsHistory, NewsItem, UpdateLog, init_db
)
from tickers import SECTOR_MAP

st.set_page_config(
    page_title="India Research · Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise DB on first run ────────────────────────────────────────────────

@st.cache_resource
def setup_db():
    init_db()
    return True

setup_db()

# ── Session state ─────────────────────────────────────────────────────────────

if "filters" not in st.session_state:
    st.session_state.filters = []
if "results" not in st.session_state:
    st.session_state.results = None
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_session() -> Session:
    return SessionLocal()

def latest_fin(ticker: str, db: Session):
    return (
        db.query(Financials)
        .filter(Financials.ticker == ticker)
        .order_by(desc(Financials.fetched_at))
        .first()
    )

def fmt_cr(val):
    if val is None:
        return "—"
    if val >= 100000:
        return f"₹{val/100000:.2f}L Cr"
    if val >= 1000:
        return f"₹{val/1000:.1f}K Cr"
    return f"₹{val:.0f} Cr"

def fmt_pct(val):
    if val is None:
        return "—"
    return f"{val*100:.1f}%"

def fmt_num(val, decimals=2, prefix="", suffix=""):
    if val is None:
        return "—"
    return f"{prefix}{val:.{decimals}f}{suffix}"

# ── Filter definitions ────────────────────────────────────────────────────────

FILTER_OPTIONS = {
    "Valuation": {
        "P/E Ratio":            ("pe_ratio",        0.0,   200.0, 0.1),
        "P/B Ratio":            ("pb_ratio",        0.0,    50.0, 0.1),
        "P/S Ratio":            ("ps_ratio",        0.0,    50.0, 0.1),
        "EV/EBITDA":            ("ev_ebitda",       0.0,    80.0, 0.1),
        "PEG Ratio":            ("peg_ratio",       0.0,    10.0, 0.1),
    },
    "Profitability": {
        "ROE (%)":              ("roe",            -50.0,  100.0, 0.5),
        "ROA (%)":              ("roa",            -50.0,   50.0, 0.5),
        "Gross Margin (%)":     ("gross_margin",     0.0,  100.0, 0.5),
        "Operating Margin (%)": ("operating_margin",-50.0, 100.0, 0.5),
        "Net Margin (%)":       ("profit_margin",  -50.0,  100.0, 0.5),
    },
    "Growth": {
        "Revenue Growth (%)":   ("revenue_growth", -50.0,  200.0, 1.0),
        "EPS Growth (%)":       ("eps_growth",     -100.0, 500.0, 1.0),
    },
    "Size": {
        "Market Cap (Cr)":      ("market_cap_cr",  500.0, 1000000.0, 500.0),
        "Revenue (Cr)":         ("revenue_cr",       0.0,  500000.0, 500.0),
        "Enterprise Value (Cr)":("enterprise_value", 0.0, 2000000.0, 500.0),
    },
    "Financial Health": {
        "Debt/Equity":          ("debt_to_equity",   0.0,   20.0, 0.1),
        "Current Ratio":        ("current_ratio",    0.0,   10.0, 0.1),
        "Quick Ratio":          ("quick_ratio",      0.0,   10.0, 0.1),
        "Cash (Cr)":            ("cash_cr",          0.0, 500000.0, 500.0),
    },
    "Dividends": {
        "Dividend Yield (%)":   ("dividend_yield",   0.0,   20.0, 0.1),
        "Payout Ratio (%)":     ("payout_ratio",     0.0,  100.0, 1.0),
    },
    "Market": {
        "Beta":                 ("beta",            -2.0,    5.0, 0.1),
        "52W High (₹)":         ("week_52_high",     0.0, 100000.0, 10.0),
        "52W Low (₹)":          ("week_52_low",      0.0, 100000.0, 10.0),
    },
}

IS_PERCENT = {
    "roe", "roa", "gross_margin", "operating_margin",
    "profit_margin", "revenue_growth", "eps_growth",
    "dividend_yield", "payout_ratio",
}

# ── Screener engine ───────────────────────────────────────────────────────────

def run_screener(filters: list, sector_filter: str, sort_col: str, sort_asc: bool) -> pd.DataFrame:
    """
    Execute screener filters against the latest financials for every company.
    Returns a DataFrame with source citation on every row.
    """
    db = get_session()
    try:
        # Subquery: latest fetched_at per ticker
        from sqlalchemy import func
        subq = (
            db.query(
                Financials.ticker,
                func.max(Financials.fetched_at).label("max_date")
            )
            .group_by(Financials.ticker)
            .subquery()
        )

        q = (
            db.query(Financials, Company)
            .join(subq, and_(
                Financials.ticker == subq.c.ticker,
                Financials.fetched_at == subq.c.max_date
            ))
            .join(Company, Financials.ticker == Company.ticker, isouter=True)
        )

        # Sector filter
        if sector_filter and sector_filter != "All sectors":
            q = q.filter(Company.sector == sector_filter)

        # Dynamic filters
        for f in filters:
            col = f["column"]
            op  = f["operator"]
            val = f["value"]
            is_pct = col in IS_PERCENT

            db_val = val / 100.0 if is_pct else val
            col_attr = getattr(Financials, col)

            if op == "≤":
                q = q.filter(col_attr <= db_val)
            elif op == "≥":
                q = q.filter(col_attr >= db_val)
            elif op == "=":
                q = q.filter(col_attr == db_val)

            # Always exclude nulls for filtered columns
            q = q.filter(col_attr.isnot(None))

        rows = q.all()

        records = []
        for fin, company in rows:
            if fin.market_cap_cr and fin.market_cap_cr < 500:
                continue
            records.append({
                "Ticker":           fin.ticker.replace(".NS", ""),
                "Company":          company.name if company else fin.ticker,
                "Sector":           company.sector if company else "—",
                "Mkt Cap":          fmt_cr(fin.market_cap_cr),
                "Mkt Cap (Cr)":     fin.market_cap_cr or 0,
                "Price (₹)":        fin.current_price,
                "P/E":              fin.pe_ratio,
                "P/B":              fin.pb_ratio,
                "EV/EBITDA":        fin.ev_ebitda,
                "ROE %":            round(fin.roe * 100, 1) if fin.roe else None,
                "Net Margin %":     round(fin.profit_margin * 100, 1) if fin.profit_margin else None,
                "Rev Growth %":     round(fin.revenue_growth * 100, 1) if fin.revenue_growth else None,
                "D/E":              fin.debt_to_equity,
                "Div Yield %":      round(fin.dividend_yield * 100, 2) if fin.dividend_yield else None,
                "Rating":           (fin.recommendation or "").upper(),
                "Source":           fin.source_name or "Yahoo Finance",
                "Source URL":       fin.source_url or f"https://finance.yahoo.com/quote/{fin.ticker}",
                "Fetched":          fin.fetched_at.strftime("%d %b %Y") if fin.fetched_at else "—",
                "_ticker_full":     fin.ticker,
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Sort
        sort_map = {
            "Market Cap": "Mkt Cap (Cr)",
            "P/E Ratio": "P/E",
            "P/B Ratio": "P/B",
            "ROE %": "ROE %",
            "Net Margin %": "Net Margin %",
            "Revenue Growth %": "Rev Growth %",
        }
        sort_key = sort_map.get(sort_col, "Mkt Cap (Cr)")
        if sort_key in df.columns:
            df = df.sort_values(sort_key, ascending=sort_asc, na_position="last")

        return df

    finally:
        db.close()

# ── Saved screeners ───────────────────────────────────────────────────────────

def load_saved_screeners():
    db = get_session()
    try:
        return db.query(SavedScreener).order_by(desc(SavedScreener.created_at)).all()
    finally:
        db.close()

def save_screener(name: str, filters: list):
    db = get_session()
    try:
        s = SavedScreener(
            name=name,
            filters=json.dumps(filters),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Could not save: {e}")
        return False
    finally:
        db.close()

def delete_screener(screener_id: int):
    db = get_session()
    try:
        s = db.query(SavedScreener).filter_by(id=screener_id).first()
        if s:
            db.delete(s)
            db.commit()
    finally:
        db.close()

def load_screener(screener_id: int):
    db = get_session()
    try:
        s = db.query(SavedScreener).filter_by(id=screener_id).first()
        if s and s.filters:
            return json.loads(s.filters)
        return []
    finally:
        db.close()

# ── Company detail panel ──────────────────────────────────────────────────────

def show_company_detail(ticker_full: str):
    db = get_session()
    try:
        company = db.query(Company).filter_by(ticker=ticker_full).first()
        fin     = latest_fin(ticker_full, db)

        if not fin:
            st.warning("No data found for this company. Try refreshing.")
            return

        name = company.name if company else ticker_full

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### {name}")
            if company:
                st.caption(f"{ticker_full}  ·  {company.sector}  ·  {company.industry}")
        with col2:
            if fin.current_price:
                st.metric("Price", f"₹{fin.current_price:,.2f}")
        with col3:
            st.metric("Market Cap", fmt_cr(fin.market_cap_cr))

        # Source citation — always shown
        st.caption(
            f"📋 Source: [{fin.source_name}]({fin.source_url}) "
            f"· Last fetched: {fin.fetched_at.strftime('%d %b %Y %H:%M UTC') if fin.fetched_at else '—'}"
        )

        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs(["Valuation & Ratios", "Financials", "Earnings", "News"])

        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("P/E Ratio",      fmt_num(fin.pe_ratio))
            c2.metric("P/B Ratio",      fmt_num(fin.pb_ratio))
            c3.metric("EV/EBITDA",      fmt_num(fin.ev_ebitda))
            c4.metric("PEG Ratio",      fmt_num(fin.peg_ratio))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("ROE",            fmt_pct(fin.roe))
            c2.metric("ROA",            fmt_pct(fin.roa))
            c3.metric("Net Margin",     fmt_pct(fin.profit_margin))
            c4.metric("Op. Margin",     fmt_pct(fin.operating_margin))

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("D/E Ratio",      fmt_num(fin.debt_to_equity))
            c2.metric("Current Ratio",  fmt_num(fin.current_ratio))
            c3.metric("Beta",           fmt_num(fin.beta))
            c4.metric("Div Yield",      fmt_pct(fin.dividend_yield))

            # 52-week range
            if fin.week_52_high and fin.week_52_low and fin.current_price:
                st.markdown("**52-week range**")
                lo, hi, cp = fin.week_52_low, fin.week_52_high, fin.current_price
                pct = (cp - lo) / (hi - lo) if hi != lo else 0
                st.progress(pct, text=f"₹{lo:,.0f} ——— ₹{cp:,.0f} ——— ₹{hi:,.0f}  ({pct*100:.0f}% of range)")

            if fin.recommendation:
                rec = fin.recommendation.upper()
                col = "🟢" if "BUY" in rec else ("🔴" if "SELL" in rec else "🟡")
                target = f"  ·  Target ₹{fin.target_mean_price:,.2f} ({fin.analyst_count} analysts)" if fin.target_mean_price else ""
                st.info(f"{col} Analyst consensus: **{rec}**{target}")

        with tab2:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Income statement**")
                data = {
                    "Revenue":      fmt_cr(fin.revenue_cr),
                    "Revenue growth": fmt_pct(fin.revenue_growth),
                    "Gross profit": fmt_cr(fin.gross_profit_cr),
                    "EBITDA":       fmt_cr(fin.ebitda_cr),
                    "Net income":   fmt_cr(fin.net_income_cr),
                    "EPS":          fmt_num(fin.eps, prefix="₹"),
                    "EPS growth":   fmt_pct(fin.eps_growth),
                }
                st.table(pd.DataFrame(data.items(), columns=["Metric", "Value"]).set_index("Metric"))
            with c2:
                st.markdown("**Balance sheet**")
                data = {
                    "Total assets":  fmt_cr(fin.total_assets_cr),
                    "Total debt":    fmt_cr(fin.total_debt_cr),
                    "Cash":          fmt_cr(fin.cash_cr),
                    "Book value/share": fmt_num(fin.book_value, prefix="₹"),
                    "Enterprise value": fmt_cr(fin.enterprise_value),
                }
                st.table(pd.DataFrame(data.items(), columns=["Metric", "Value"]).set_index("Metric"))
            st.caption(f"Source: {fin.source_name} · {fin.source_url}")

        with tab3:
            earnings = (
                db.query(EarningsHistory)
                .filter_by(ticker=ticker_full)
                .order_by(desc(EarningsHistory.fetched_at))
                .limit(8)
                .all()
            )
            if earnings:
                rows = []
                for e in earnings:
                    beat = None
                    if e.reported_eps is not None and e.estimated_eps is not None:
                        beat = "✅ Beat" if e.reported_eps >= e.estimated_eps else "❌ Miss"
                    rows.append({
                        "Period":        e.period,
                        "Reported EPS":  fmt_num(e.reported_eps, prefix="₹"),
                        "Estimated EPS": fmt_num(e.estimated_eps, prefix="₹"),
                        "Surprise":      fmt_num(e.surprise_pct, suffix="%") if e.surprise_pct else "—",
                        "Result":        beat or "—",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.caption(f"Source: Yahoo Finance / yfinance · {fin.source_url}")
            else:
                st.info("No earnings history available yet. Run a data refresh to populate.")

        with tab4:
            news = (
                db.query(NewsItem)
                .filter_by(ticker=ticker_full)
                .order_by(desc(NewsItem.published_at))
                .limit(15)
                .all()
            )
            if news:
                for n in news:
                    pub = n.published_at.strftime("%d %b %Y") if n.published_at else "—"
                    st.markdown(f"**[{n.title}]({n.link})**")
                    st.caption(f"{n.publisher or 'Yahoo Finance'}  ·  {pub}  ·  [Read article]({n.link})")
                    if n.summary:
                        st.markdown(f"<small>{n.summary[:200]}{'...' if len(n.summary or '')>200 else ''}</small>", unsafe_allow_html=True)
                    st.divider()
            else:
                st.info("No news yet. Run a news refresh from the sidebar.")

    finally:
        db.close()

# ── DB status ─────────────────────────────────────────────────────────────────

def get_db_status():
    db = get_session()
    try:
        from sqlalchemy import func
        company_count = db.query(Company).count()
        fin_count     = db.query(Financials).count()
        news_count    = db.query(NewsItem).count()
        last_log      = db.query(UpdateLog).order_by(desc(UpdateLog.started_at)).first()
        return company_count, fin_count, news_count, last_log
    except Exception:
        return 0, 0, 0, None
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

st.title("📊 India Research — Custom Screener")
st.caption("Fundamental screener for NSE-listed companies above ₹500 Cr market cap · Data: Yahoo Finance via yfinance")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🔍 Screener filters")

    # Sector filter
    all_sectors = ["All sectors"] + sorted(SECTOR_MAP.keys())
    sector_filter = st.selectbox("Sector", all_sectors)

    st.divider()

    # Add filter
    st.markdown("**Add a filter**")
    cat = st.selectbox("Category", list(FILTER_OPTIONS.keys()), key="cat_select")
    metric = st.selectbox("Metric", list(FILTER_OPTIONS[cat].keys()), key="metric_select")
    col_key, min_v, max_v, step = FILTER_OPTIONS[cat][metric]
    operator = st.radio("Operator", ["≤", "≥"], horizontal=True, key="op_select")

    is_pct = col_key in IS_PERCENT
    display_min = min_v * 100 if is_pct else min_v
    display_max = max_v * 100 if is_pct else max_v
    display_step = step * 100 if is_pct else step
    default_val  = display_min + (display_max - display_min) * 0.3

    value = st.number_input(
        f"Value {'(%)' if is_pct else ''}",
        min_value=float(display_min),
        max_value=float(display_max),
        value=float(round(default_val / display_step) * display_step),
        step=float(display_step),
        key="val_input",
    )

    if st.button("➕ Add filter", use_container_width=True):
        st.session_state.filters.append({
            "label":    f"{metric} {operator} {value}{'%' if is_pct else ''}",
            "column":   col_key,
            "operator": operator,
            "value":    float(value),
        })

    # Active filters
    if st.session_state.filters:
        st.divider()
        st.markdown("**Active filters**")
        to_remove = []
        for i, f in enumerate(st.session_state.filters):
            col_a, col_b = st.columns([4, 1])
            col_a.markdown(f"<small>{f['label']}</small>", unsafe_allow_html=True)
            if col_b.button("✕", key=f"rm_{i}"):
                to_remove.append(i)
        for i in reversed(to_remove):
            st.session_state.filters.pop(i)
        if st.button("🗑 Clear all filters", use_container_width=True):
            st.session_state.filters = []
            st.session_state.results = None

    st.divider()

    # Sort
    st.markdown("**Sort results by**")
    sort_col = st.selectbox("", ["Market Cap", "P/E Ratio", "P/B Ratio", "ROE %", "Net Margin %", "Revenue Growth %"], label_visibility="collapsed")
    sort_asc = st.checkbox("Ascending", value=False)

    st.divider()

    # Run button
    if st.button("▶ Run screener", type="primary", use_container_width=True):
        with st.spinner("Running screener across 1000 companies..."):
            st.session_state.results = run_screener(
                st.session_state.filters, sector_filter, sort_col, sort_asc
            )
            st.session_state.selected_ticker = None

    st.divider()

    # Save / load screeners
    st.markdown("**Save this screener**")
    screener_name = st.text_input("Name", placeholder="e.g. Quality large caps", key="screener_name")
    if st.button("💾 Save", use_container_width=True):
        if not screener_name.strip():
            st.warning("Give it a name first")
        elif not st.session_state.filters:
            st.warning("Add at least one filter")
        else:
            if save_screener(screener_name.strip(), st.session_state.filters):
                st.success("Saved!")

    saved = load_saved_screeners()
    if saved:
        st.markdown("**Saved screeners**")
        for s in saved:
            col_a, col_b = st.columns([3, 1])
            if col_a.button(f"📂 {s.name}", key=f"load_{s.id}", use_container_width=True):
                st.session_state.filters = load_screener(s.id)
                st.rerun()
            if col_b.button("✕", key=f"del_{s.id}"):
                delete_screener(s.id)
                st.rerun()

    st.divider()

    # DB status
    company_count, fin_count, news_count, last_log = get_db_status()
    st.markdown("**Database status**")
    st.caption(f"Companies: {company_count:,} · Records: {fin_count:,} · News: {news_count:,}")
    if last_log:
        status_icon = "✅" if last_log.status == "done" else "⏳"
        st.caption(f"{status_icon} Last update: {last_log.job_name} · {last_log.started_at.strftime('%d %b %Y') if last_log.started_at else '—'}")
    else:
        st.caption("⚠ No data yet — run first fetch via GitHub Actions")

# ── Main area ─────────────────────────────────────────────────────────────────

if st.session_state.results is None:
    # Welcome state
    st.markdown("### Build a custom screener")
    st.markdown(
        "Use the filters in the sidebar to define your criteria. "
        "You can combine any number of conditions across valuation, profitability, growth, "
        "size, and financial health metrics."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Quality screen example**\n\nROE ≥ 15%\n\nNet Margin ≥ 10%\n\nD/E ≤ 0.5\n\nMarket Cap ≥ 5000 Cr")
    with col2:
        st.info("**Value screen example**\n\nP/E ≤ 15\n\nP/B ≤ 2\n\nDividend Yield ≥ 2%\n\nMarket Cap ≥ 2000 Cr")
    with col3:
        st.info("**Growth screen example**\n\nRevenue Growth ≥ 20%\n\nEPS Growth ≥ 15%\n\nROE ≥ 12%\n\nMarket Cap ≥ 1000 Cr")

    if company_count == 0:
        st.warning(
            "⚠ **No data in database yet.** "
            "Go to your GitHub repo → Actions tab → 'Data refresh' workflow → click 'Run workflow' → select 'both'. "
            "It takes ~25 minutes to fetch all 1000 companies."
        )

elif len(st.session_state.results) == 0:
    st.warning("No companies match your filters. Try relaxing one or more criteria.")

else:
    df = st.session_state.results
    n = len(df)

    st.markdown(f"### {n} companies match your screener")

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    valid_pe = df["P/E"].dropna()
    valid_roe = df["ROE %"].dropna()
    c1.metric("Median P/E",    f"{valid_pe.median():.1f}x" if len(valid_pe) else "—")
    c2.metric("Median ROE",    f"{valid_roe.median():.1f}%" if len(valid_roe) else "—")
    c3.metric("Sectors",       df["Sector"].nunique())
    c4.metric("Total results", n)

    st.divider()

    # Results table — hide internal columns
    display_cols = [
        "Ticker", "Company", "Sector", "Mkt Cap",
        "Price (₹)", "P/E", "P/B", "ROE %",
        "Net Margin %", "Rev Growth %", "D/E", "Rating",
    ]
    available = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df[available],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "P/E":        st.column_config.NumberColumn(format="%.1f"),
            "P/B":        st.column_config.NumberColumn(format="%.2f"),
            "ROE %":      st.column_config.NumberColumn(format="%.1f%%"),
            "Net Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            "Rev Growth %": st.column_config.NumberColumn(format="%.1f%%"),
            "D/E":        st.column_config.NumberColumn(format="%.2f"),
        }
    )

    # Source line — always shown
    st.caption(
        f"📋 All data sourced from Yahoo Finance via yfinance · "
        f"Fetched dates shown in detail view · "
        f"[Verify any ticker on Yahoo Finance](https://finance.yahoo.com)"
    )

    # Export
    csv = df[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Export to CSV",
        csv,
        file_name=f"screener_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    st.divider()

    # Company drill-down
    st.markdown("### Company detail")
    ticker_options = df["Ticker"].tolist()
    selected = st.selectbox(
        "Select a company to view full detail",
        ["— select —"] + ticker_options,
        key="detail_select"
    )

    if selected and selected != "— select —":
        ticker_full = df[df["Ticker"] == selected]["_ticker_full"].values[0]
        show_company_detail(ticker_full)

    # Compare two companies
    st.divider()
    st.markdown("### Compare two companies")
    col_a, col_b = st.columns(2)
    with col_a:
        cmp_a = st.selectbox("Company A", ["— select —"] + ticker_options, key="cmp_a")
    with col_b:
        cmp_b = st.selectbox("Company B", ["— select —"] + ticker_options, key="cmp_b")

    if cmp_a != "— select —" and cmp_b != "— select —" and cmp_a != cmp_b:
        db = get_session()
        try:
            ta = df[df["Ticker"] == cmp_a]["_ticker_full"].values[0]
            tb = df[df["Ticker"] == cmp_b]["_ticker_full"].values[0]
            fa = latest_fin(ta, db)
            fb = latest_fin(tb, db)
            ca = db.query(Company).filter_by(ticker=ta).first()
            cb = db.query(Company).filter_by(ticker=tb).first()

            if fa and fb:
                diff_sector = ca and cb and ca.sector != cb.sector
                if diff_sector:
                    st.warning(f"⚠ Different sectors: {ca.sector} vs {cb.sector} — direct ratio comparisons may be misleading")

                compare_rows = [
                    ("Sector",          ca.sector if ca else "—",         cb.sector if cb else "—"),
                    ("Market Cap",       fmt_cr(fa.market_cap_cr),          fmt_cr(fb.market_cap_cr)),
                    ("Price (₹)",        fmt_num(fa.current_price,"₹"),     fmt_num(fb.current_price,"₹")),
                    ("P/E Ratio",        fmt_num(fa.pe_ratio),              fmt_num(fb.pe_ratio)),
                    ("P/B Ratio",        fmt_num(fa.pb_ratio),              fmt_num(fb.pb_ratio)),
                    ("EV/EBITDA",        fmt_num(fa.ev_ebitda),             fmt_num(fb.ev_ebitda)),
                    ("ROE",              fmt_pct(fa.roe),                   fmt_pct(fb.roe)),
                    ("Net Margin",       fmt_pct(fa.profit_margin),         fmt_pct(fb.profit_margin)),
                    ("Revenue",          fmt_cr(fa.revenue_cr),             fmt_cr(fb.revenue_cr)),
                    ("Net Income",       fmt_cr(fa.net_income_cr),          fmt_cr(fb.net_income_cr)),
                    ("D/E Ratio",        fmt_num(fa.debt_to_equity),        fmt_num(fb.debt_to_equity)),
                    ("Div Yield",        fmt_pct(fa.dividend_yield),        fmt_pct(fb.dividend_yield)),
                    ("Analyst Rating",   (fa.recommendation or "—").upper(),(fb.recommendation or "—").upper()),
                    ("Target Price",     fmt_num(fa.target_mean_price,prefix="₹"), fmt_num(fb.target_mean_price,prefix="₹")),
                    ("Data source",      fa.source_name,                    fb.source_name),
                    ("Last fetched",     fa.fetched_at.strftime("%d %b %Y") if fa.fetched_at else "—",
                                         fb.fetched_at.strftime("%d %b %Y") if fb.fetched_at else "—"),
                ]
                cmp_df = pd.DataFrame(compare_rows, columns=["Metric", cmp_a, cmp_b])
                st.dataframe(cmp_df.set_index("Metric"), use_container_width=True)
                st.caption("Source: Yahoo Finance via yfinance · All figures from latest available data")
        finally:
            db.close()
