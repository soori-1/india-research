"""
streamlit_app.py — Right Horizons Research Screener
Brand: Maroon #8B1A1A · Gold #C8922A · Cream #F5ECD7
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="Right Horizons · Research Screener",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Page background */
.stApp { background-color: #120606; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E0A0A 0%, #2A1212 100%);
    border-right: 1px solid #5C2A0A;
}
[data-testid="stSidebar"] * { color: #F5ECD7 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stNumberInput label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stRadio label {
    color: #C8922A !important; font-size: 12px !important;
    font-weight: 600 !important; text-transform: uppercase; letter-spacing: .05em;
}
[data-testid="stSidebar"] hr { border-color: #5C2A0A !important; }
[data-testid="stSidebar"] h3 {
    color: #C8922A !important; font-size: 13px !important;
    text-transform: uppercase; letter-spacing: .08em;
}
[data-testid="stSidebar"] .stMarkdown strong {
    color: #C8922A !important; font-size: 12px; font-weight: 600;
    text-transform: uppercase; letter-spacing: .05em;
}

/* Header bar */
.rh-header {
    background: linear-gradient(90deg, #6B1010 0%, #8B1A1A 40%, #C8922A 100%);
    padding: 16px 28px; border-radius: 10px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
}
.rh-title  { font-size: 22px; font-weight: 700; color: #FFF; letter-spacing: .02em; }
.rh-sub    { font-size: 12px; color: #F5ECD7; opacity: .85; margin-top: 3px; }
.rh-badge  {
    background: rgba(255,255,255,.15); color: #F5ECD7; font-size: 11px;
    padding: 4px 12px; border-radius: 20px; border: 1px solid rgba(255,255,255,.25);
    display: inline-block; margin-left: 8px;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #1E0A0A; border: 1px solid #3D1A0A;
    border-radius: 10px; padding: 14px 16px !important;
}
[data-testid="stMetricLabel"] {
    color: #C8922A !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase; letter-spacing: .06em;
}
[data-testid="stMetricValue"] {
    color: #F5ECD7 !important; font-size: 22px !important; font-weight: 700 !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #8B1A1A, #C8922A) !important;
    color: #FFF !important; border: none !important; border-radius: 7px !important;
    font-weight: 600 !important; font-size: 13px !important; transition: opacity .15s !important;
}
.stButton > button:hover { opacity: .88 !important; }

/* Inputs */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background-color: #2A1010 !important; border: 1px solid #5C2A0A !important;
    color: #F5ECD7 !important; border-radius: 7px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent; border-bottom: 1px solid #3D1A0A; gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #8B6A4A !important;
    border: none !important; font-size: 13px !important; font-weight: 500 !important;
    padding: 8px 18px !important; border-radius: 6px 6px 0 0 !important;
}
.stTabs [aria-selected="true"] {
    background: #2A1010 !important; color: #C8922A !important;
    border-bottom: 2px solid #C8922A !important;
}

/* Dataframe */
[data-testid="stDataFrame"] { border: 1px solid #3D1A0A !important; border-radius: 10px !important; }

/* Info / warning */
[data-testid="stInfo"]    { background: #1E0A0A !important; border-left: 3px solid #C8922A !important; color: #F5ECD7 !important; }
[data-testid="stWarning"] { background: #2A1A04 !important; border-left: 3px solid #E8721C !important; color: #F5ECD7 !important; }

/* Dividers */
hr { border-color: #3D1A0A !important; margin: 16px 0 !important; }

/* Captions */
.stCaption, small { color: #8B6A4A !important; font-size: 11px !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg, #8B1A1A, #C8922A) !important; border-radius: 4px !important; }
.stProgress > div { background: #2A1010 !important; border-radius: 4px !important; }

/* Headings */
h1 { color: #F5ECD7 !important; }
h2 { color: #C8922A !important; }
h3 { color: #E8A84A !important; }

/* Filter pill */
.f-pill {
    display: inline-block; background: #2A1010; border: 1px solid #C8922A;
    color: #C8922A; font-size: 11px; padding: 3px 10px; border-radius: 20px; margin: 2px 0;
}

/* Download button */
.stDownloadButton > button {
    background: #2A1010 !important; color: #C8922A !important;
    border: 1px solid #C8922A !important; border-radius: 7px !important; font-weight: 600 !important;
}
.stDownloadButton > button:hover { background: #C8922A !important; color: #FFF !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1E0A0A; }
::-webkit-scrollbar-thumb { background: #5C2A0A; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #C8922A; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_FILE  = "data/companies.json"
META_FILE  = "data/meta.json"
SAVED_FILE = "data/saved_screeners.json"

# ── Data loading ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_companies():
    if not os.path.exists(DATA_FILE): return []
    with open(DATA_FILE) as f: return json.load(f)

@st.cache_data(ttl=3600)
def load_meta():
    if not os.path.exists(META_FILE): return {}
    with open(META_FILE) as f: return json.load(f)

def load_saved():
    if not os.path.exists(SAVED_FILE): return {}
    with open(SAVED_FILE) as f: return json.load(f)

def save_screener(name, filters, sector):
    s = load_saved()
    s[name] = {"filters": filters, "sector": sector, "saved_at": datetime.utcnow().isoformat()}
    os.makedirs("data", exist_ok=True)
    with open(SAVED_FILE, "w") as f: json.dump(s, f, indent=2)

def delete_screener(name):
    s = load_saved(); s.pop(name, None)
    with open(SAVED_FILE, "w") as f: json.dump(s, f, indent=2)

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_cr(v):
    if v is None: return "—"
    try:
        v = float(v)
        if v >= 100000: return f"₹{v/100000:.2f}L Cr"
        if v >= 1000:   return f"₹{v/1000:.1f}K Cr"
        return f"₹{v:,.0f} Cr"
    except: return "—"

def fmt(v, pre="", suf="", dec=2):
    if v is None: return "—"
    try: return f"{pre}{float(v):.{dec}f}{suf}"
    except: return "—"

def rec_icon(r):
    if not r: return ""
    r = r.lower()
    if "buy" in r: return "🟢"
    if "hold" in r or "neutral" in r: return "🟡"
    if "sell" in r or "under" in r: return "🔴"
    return ""

# ── Filter definitions ────────────────────────────────────────────────────────

FILTERS = {
    "Valuation":        {"P/E Ratio":("pe_ratio",0,200,.5),"P/B Ratio":("pb_ratio",0,50,.1),
                         "P/S Ratio":("ps_ratio",0,50,.1),"EV/EBITDA":("ev_ebitda",0,80,.5),"PEG Ratio":("peg_ratio",0,10,.1)},
    "Profitability":    {"ROE (%)":("roe_pct",-50,100,1),"ROA (%)":("roa_pct",-50,50,.5),
                         "Gross Margin (%)":("gross_margin_pct",0,100,1),"Op Margin (%)":("op_margin_pct",-50,100,1),
                         "Net Margin (%)":("net_margin_pct",-50,100,1)},
    "Growth":           {"Revenue Growth (%)":("revenue_growth_pct",-50,300,1),"EPS Growth (%)":("eps_growth_pct",-100,500,5)},
    "Size":             {"Market Cap (Cr)":("market_cap_cr",500,2000000,500),"Revenue (Cr)":("revenue_cr",0,500000,500),
                         "Cash (Cr)":("cash_cr",0,200000,500)},
    "Financial Health": {"Debt/Equity":("debt_to_equity",0,20,.1),"Current Ratio":("current_ratio",0,10,.1),
                         "Quick Ratio":("quick_ratio",0,10,.1)},
    "Dividends":        {"Div Yield (%)":("dividend_yield_pct",0,20,.25),"Payout Ratio (%)":("payout_ratio_pct",0,100,1)},
    "Market":           {"Beta":("beta",-2,5,.1),"52W High (₹)":("week_52_high",0,50000,50),
                         "52W Low (₹)":("week_52_low",0,50000,50)},
}

# ── Screener engine ───────────────────────────────────────────────────────────

def run_screener(companies, filters, sector, sort_col, sort_asc):
    rows = []
    for c in companies:
        if sector != "All sectors" and c.get("sector") != sector: continue
        mc = c.get("market_cap_cr")
        if mc is not None and mc < 500: continue
        ok = True
        for f in filters:
            v = c.get(f["column"])
            if v is None: ok = False; break
            try:
                fv = float(v)
                if f["op"] == "≤" and fv > f["val"]: ok = False; break
                if f["op"] == "≥" and fv < f["val"]: ok = False; break
            except: ok = False; break
        if not ok: continue
        rows.append({
            "Ticker": c.get("ticker_short",""), "Company": c.get("name",""),
            "Sector": c.get("sector","—"), "Mkt Cap": fmt_cr(c.get("market_cap_cr")),
            "Price (₹)": c.get("current_price"), "P/E": c.get("pe_ratio"),
            "P/B": c.get("pb_ratio"), "EV/EBITDA": c.get("ev_ebitda"),
            "ROE %": c.get("roe_pct"), "Net Margin %": c.get("net_margin_pct"),
            "Rev Growth %": c.get("revenue_growth_pct"), "D/E": c.get("debt_to_equity"),
            "Div Yield %": c.get("dividend_yield_pct"),
            "Rating": (rec_icon(c.get("recommendation")) + " " + (c.get("recommendation") or "—")).strip(),
            "Fetched": (c.get("fetched_at") or "")[:10],
            "_t": c.get("ticker",""), "_mc": c.get("market_cap_cr") or 0,
        })
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    sk = {"Market Cap":"_mc","P/E Ratio":"P/E","P/B Ratio":"P/B","ROE %":"ROE %",
          "Net Margin %":"Net Margin %","Revenue Growth %":"Rev Growth %","Dividend Yield %":"Div Yield %"}.get(sort_col,"_mc")
    if sk in df.columns: df = df.sort_values(sk, ascending=sort_asc, na_position="last")
    return df

# ── Company detail ─────────────────────────────────────────────────────────────

def company_detail(tf, companies):
    c = next((x for x in companies if x.get("ticker") == tf), None)
    if not c: st.warning("Not found."); return

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1E0A0A,#2A1212);border:1px solid #5C2A0A;
                border-radius:12px;padding:20px 24px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">
        <div>
          <div style="font-size:22px;font-weight:700;color:#F5ECD7">{c.get("name",tf)}</div>
          <div style="font-size:12px;color:#C8922A;margin-top:4px">
            <span style="background:#2A1010;border:1px solid #5C2A0A;padding:2px 8px;
                         border-radius:4px;margin-right:6px">{c.get("ticker_short","")}</span>
            {c.get("sector","—")} <span style="color:#8B6A4A">· {c.get("industry","—")}</span>
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:28px;font-weight:700;color:#F5ECD7">
            {"₹{:,.2f}".format(c["current_price"]) if c.get("current_price") else "—"}
          </div>
          <div style="font-size:13px;color:#C8922A">{fmt_cr(c.get("market_cap_cr"))}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.caption(f"📋 Source: [{c.get('source_name','Yahoo Finance')}]({c.get('source_url','#')}) · Fetched: {(c.get('fetched_at',''))[:10]}")

    rec = c.get("recommendation","")
    if rec:
        tp = c.get("target_price"); ac = c.get("analyst_count")
        tstr = f" · Target ₹{tp:,.2f} ({ac} analysts)" if tp else ""
        bg = {"buy":"#4A7C3F","strong_buy":"#4A7C3F","hold":"#C8922A","sell":"#8B1A1A"}.get(rec.lower(),"#2A1010")
        st.markdown(f'<div style="background:{bg}22;border:1px solid {bg};border-radius:8px;'
                    f'padding:10px 16px;font-size:13px;color:#F5ECD7;margin-bottom:8px">'
                    f'{rec_icon(rec)} Analyst: <strong>{rec.upper()}</strong>{tstr}</div>', unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["📊 Ratios", "📄 Financials", "📈 Earnings", "📰 News"])

    def mc(label, value):
        return (f'<div style="background:#1E0A0A;border:1px solid #3D1A0A;border-radius:8px;'
                f'padding:12px;text-align:center">'
                f'<div style="font-size:10px;color:#C8922A;font-weight:600;text-transform:uppercase;'
                f'letter-spacing:.05em;margin-bottom:6px">{label}</div>'
                f'<div style="font-size:18px;font-weight:700;color:#F5ECD7">{value}</div></div>')

    with t1:
        for section, items in [
            ("Valuation", [("P/E",fmt(c.get("pe_ratio"))),("P/B",fmt(c.get("pb_ratio"))),
                           ("EV/EBITDA",fmt(c.get("ev_ebitda"))),("PEG",fmt(c.get("peg_ratio"))),("P/S",fmt(c.get("ps_ratio")))]),
            ("Profitability", [("ROE",fmt(c.get("roe_pct"),suf="%")),("ROA",fmt(c.get("roa_pct"),suf="%")),
                               ("Gross Margin",fmt(c.get("gross_margin_pct"),suf="%")),
                               ("Op Margin",fmt(c.get("op_margin_pct"),suf="%")),("Net Margin",fmt(c.get("net_margin_pct"),suf="%"))]),
            ("Financial Health", [("D/E",fmt(c.get("debt_to_equity"))),("Current",fmt(c.get("current_ratio"))),
                                  ("Quick",fmt(c.get("quick_ratio"))),("Beta",fmt(c.get("beta"))),
                                  ("Div Yield",fmt(c.get("dividend_yield_pct"),suf="%"))]),
        ]:
            st.markdown(f"**{section}**")
            cols = st.columns(5)
            for col,(lbl,val) in zip(cols,items):
                col.markdown(mc(lbl,val), unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        hi,lo,cp = c.get("week_52_high"),c.get("week_52_low"),c.get("current_price")
        if hi and lo and cp and hi != lo:
            pct = max(0.0, min(1.0, (cp-lo)/(hi-lo)))
            st.markdown("**52-week range**")
            st.progress(pct, text=f"Low ₹{lo:,.0f}  ·  Current ₹{cp:,.0f}  ·  High ₹{hi:,.0f}  ({pct*100:.0f}%)")

    with t2:
        c1,c2 = st.columns(2)
        with c1:
            st.markdown("**Income statement**")
            st.table(pd.DataFrame([
                ("Revenue",         fmt_cr(c.get("revenue_cr"))),
                ("Revenue growth",  fmt(c.get("revenue_growth_pct"),suf="%")),
                ("Gross profit",    fmt_cr(c.get("gross_profit_cr"))),
                ("EBITDA",          fmt_cr(c.get("ebitda_cr"))),
                ("Net income",      fmt_cr(c.get("net_income_cr"))),
                ("EPS",             fmt(c.get("eps"),pre="₹")),
                ("EPS growth",      fmt(c.get("eps_growth_pct"),suf="%")),
            ], columns=["Metric","Value"]).set_index("Metric"))
        with c2:
            st.markdown("**Balance sheet**")
            st.table(pd.DataFrame([
                ("Total assets",     fmt_cr(c.get("total_assets_cr"))),
                ("Total debt",       fmt_cr(c.get("total_debt_cr"))),
                ("Cash",             fmt_cr(c.get("cash_cr"))),
                ("Book value/share", fmt(c.get("book_value"),pre="₹")),
                ("Enterprise value", fmt_cr(c.get("enterprise_value_cr"))),
                ("Dividend rate",    fmt(c.get("dividend_rate"),pre="₹")),
                ("Payout ratio",     fmt(c.get("payout_ratio_pct"),suf="%")),
            ], columns=["Metric","Value"]).set_index("Metric"))
        st.caption(f"Source: {c.get('source_name','Yahoo Finance')} · {c.get('source_url','')}")

    with t3:
        rows = [("Trailing EPS",fmt(c.get("eps"),pre="₹")),
                ("EPS growth",  fmt(c.get("eps_growth_pct"),suf="%")),
                ("Rev growth",  fmt(c.get("revenue_growth_pct"),suf="%"))]
        st.table(pd.DataFrame(rows, columns=["Metric","Value"]).set_index("Metric"))
        st.caption(f"Source: Yahoo Finance · {(c.get('fetched_at',''))[:10]}")

    with t4:
        news = c.get("news", [])
        if news:
            for n in news:
                st.markdown(
                    f'<div style="padding:12px 0;border-bottom:1px solid #3D1A0A">'
                    f'<a href="{n.get("link","#")}" target="_blank" '
                    f'style="color:#E8A84A;font-weight:500;font-size:14px;text-decoration:none">'
                    f'{n.get("title","")}</a>'
                    f'<div style="font-size:11px;color:#8B6A4A;margin-top:4px">'
                    f'{n.get("publisher","")} · {n.get("published","")}</div></div>',
                    unsafe_allow_html=True)
        else:
            st.info("No news yet. Refreshes every 3 days via GitHub Actions.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

companies = load_companies()
meta      = load_meta()

if "filters" not in st.session_state: st.session_state.filters = []
if "results" not in st.session_state: st.session_state.results = None

# Header
last_upd = (meta.get("last_financial_update") or "")[:10]
st.markdown(f"""
<div class="rh-header">
  <div>
    <div class="rh-title">Right Horizons · Research Screener</div>
    <div class="rh-sub">NSE companies · ₹500 Cr+ · Yahoo Finance · Updated monthly</div>
  </div>
  <div>
    <span class="rh-badge">📊 {len(companies):,} companies</span>
    <span class="rh-badge">🕐 {last_upd or 'pending first fetch'}</span>
  </div>
</div>""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔍 Screener filters")
    sectors       = sorted(set(c.get("sector","") for c in companies if c.get("sector")))
    sector_filter = st.selectbox("Sector", ["All sectors"] + sectors)
    st.divider()

    st.markdown("**Add a filter**")
    cat    = st.selectbox("Category", list(FILTERS.keys()), key="cat")
    metric = st.selectbox("Metric",   list(FILTERS[cat].keys()), key="metric")
    col_key, mn, mx, step = FILTERS[cat][metric]
    op     = st.radio("Operator", ["≤","≥"], horizontal=True)
    val    = st.number_input("Value", min_value=float(mn), max_value=float(mx),
                             value=float(round(mn+(mx-mn)*0.25, 2)), step=float(step))

    if st.button("➕ Add filter", use_container_width=True):
        st.session_state.filters.append({"label":f"{metric} {op} {val}","column":col_key,"op":op,"val":float(val)})
        st.rerun()

    if st.session_state.filters:
        st.divider()
        st.markdown("**Active filters**")
        rm = []
        for i,f in enumerate(st.session_state.filters):
            ca,cb = st.columns([5,1])
            ca.markdown(f'<div class="f-pill">{f["label"]}</div>', unsafe_allow_html=True)
            if cb.button("✕", key=f"rm{i}"): rm.append(i)
        for i in reversed(rm): st.session_state.filters.pop(i)
        if rm: st.rerun()
        if st.button("🗑 Clear all", use_container_width=True):
            st.session_state.filters=[]; st.session_state.results=None; st.rerun()

    st.divider()
    st.markdown("**Sort by**")
    sort_col = st.selectbox("", ["Market Cap","P/E Ratio","P/B Ratio","ROE %","Net Margin %","Revenue Growth %","Dividend Yield %"], label_visibility="collapsed")
    sort_asc = st.checkbox("Ascending", value=False)
    st.divider()

    if st.button("▶  Run screener", use_container_width=True):
        if not companies:
            st.error("No data. Run GitHub Actions first.")
        else:
            with st.spinner(f"Screening {len(companies):,} companies..."):
                st.session_state.results = run_screener(companies, st.session_state.filters, sector_filter, sort_col, sort_asc)
            st.rerun()

    st.divider()
    st.markdown("**Save screener**")
    sname = st.text_input("Name", placeholder="e.g. Quality large caps")
    if st.button("💾 Save", use_container_width=True):
        if not sname.strip(): st.warning("Enter a name")
        elif not st.session_state.filters: st.warning("Add a filter first")
        else: save_screener(sname.strip(), st.session_state.filters, sector_filter); st.success(f"Saved!"); st.rerun()

    saved = load_saved()
    if saved:
        st.markdown("**Saved screeners**")
        for name in list(saved.keys()):
            ca,cb = st.columns([4,1])
            if ca.button(f"📂 {name}", key=f"ld_{name}", use_container_width=True):
                st.session_state.filters = saved[name]["filters"]; st.rerun()
            if cb.button("✕", key=f"dl_{name}"):
                delete_screener(name); st.rerun()

    st.divider()
    if meta:
        st.markdown(
            f'<div style="font-size:11px;color:#8B6A4A;line-height:1.9">'
            f'Companies: <span style="color:#C8922A">{meta.get("total_companies",0):,}</span><br>'
            f'Financials: <span style="color:#C8922A">{(meta.get("last_financial_update",""))[:10] or "pending"}</span><br>'
            f'News: <span style="color:#C8922A">{(meta.get("last_news_update",""))[:10] or "pending"}</span><br>'
            f'Source: <span style="color:#C8922A">Yahoo Finance</span></div>',
            unsafe_allow_html=True)

# Main content
if not companies:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px">
      <div style="font-size:48px;margin-bottom:16px">📊</div>
      <div style="font-size:20px;font-weight:600;color:#F5ECD7;margin-bottom:8px">No data loaded yet</div>
      <div style="font-size:14px;color:#8B6A4A;max-width:480px;margin:0 auto">
        GitHub repo → <strong style="color:#C8922A">Actions</strong> →
        <strong style="color:#C8922A">Data refresh</strong> →
        <strong style="color:#C8922A">Run workflow → both</strong>. Takes ~25 min.
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

if st.session_state.results is None:
    st.markdown("### Build your screener")
    st.markdown('<p style="color:#8B6A4A;font-size:13px">Add filters in the sidebar → click <strong style="color:#C8922A">Run screener</strong></p>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    def ecard(title, items, color):
        li = "".join(f'<div style="font-size:12px;color:#8B6A4A;padding:3px 0">• {i}</div>' for i in items)
        return (f'<div style="background:#1E0A0A;border:1px solid {color};border-radius:10px;padding:18px">'
                f'<div style="font-size:13px;font-weight:600;color:{color};margin-bottom:10px">{title}</div>{li}</div>')
    c1.markdown(ecard("Quality Screen",["ROE ≥ 15%","Net Margin ≥ 10%","D/E ≤ 0.5","Mkt Cap ≥ ₹5000 Cr"],"#4A7C3F"), unsafe_allow_html=True)
    c2.markdown(ecard("Value Screen",  ["P/E ≤ 15","P/B ≤ 2","Div Yield ≥ 2%","Mkt Cap ≥ ₹2000 Cr"],"#C8922A"),    unsafe_allow_html=True)
    c3.markdown(ecard("Growth Screen", ["Rev Growth ≥ 20%","EPS Growth ≥ 15%","ROE ≥ 12%","Mkt Cap ≥ ₹1000 Cr"],"#8B1A1A"), unsafe_allow_html=True)

elif len(st.session_state.results) == 0:
    st.warning("No companies match. Try relaxing your filters.")

else:
    df = st.session_state.results
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Results",    len(df))
    c2.metric("Median P/E", f"{df['P/E'].dropna().median():.1f}x"  if df['P/E'].notna().any()   else "—")
    c3.metric("Median ROE", f"{df['ROE %'].dropna().median():.1f}%" if df['ROE %'].notna().any() else "—")
    c4.metric("Sectors",    df["Sector"].nunique())
    st.divider()

    show = ["Ticker","Company","Sector","Mkt Cap","Price (₹)","P/E","P/B","ROE %","Net Margin %","Rev Growth %","D/E","Rating","Fetched"]
    show = [c for c in show if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True, column_config={
        "Price (₹)":    st.column_config.NumberColumn(format="₹%.2f"),
        "P/E":          st.column_config.NumberColumn(format="%.1f"),
        "P/B":          st.column_config.NumberColumn(format="%.2f"),
        "ROE %":        st.column_config.NumberColumn(format="%.1f"),
        "Net Margin %": st.column_config.NumberColumn(format="%.1f"),
        "Rev Growth %": st.column_config.NumberColumn(format="%.1f"),
        "D/E":          st.column_config.NumberColumn(format="%.2f"),
    })
    st.caption("📋 All data from **Yahoo Finance via yfinance** · [Verify on Yahoo Finance ↗](https://finance.yahoo.com)")
    st.download_button("⬇ Export CSV", df[show].to_csv(index=False).encode(),
                       f"RH_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")
    st.divider()

    st.markdown("### Company detail")
    tl = df["Ticker"].tolist()
    sel = st.selectbox("Select company", ["— select —"] + tl)
    if sel and sel != "— select —":
        company_detail(df[df["Ticker"]==sel]["_t"].values[0], companies)
    st.divider()

    st.markdown("### Compare two companies")
    ca_col,cb_col = st.columns(2)
    with ca_col: cmp_a = st.selectbox("Company A", ["— select —"]+tl, key="ca")
    with cb_col: cmp_b = st.selectbox("Company B", ["— select —"]+tl, key="cb")
    if cmp_a != "— select —" and cmp_b != "— select —" and cmp_a != cmp_b:
        ta = df[df["Ticker"]==cmp_a]["_t"].values[0]
        tb = df[df["Ticker"]==cmp_b]["_t"].values[0]
        ca = next((x for x in companies if x["ticker"]==ta), {})
        cb = next((x for x in companies if x["ticker"]==tb), {})
        if ca.get("sector") != cb.get("sector"):
            st.warning(f"⚠ Different sectors: **{ca.get('sector','?')}** vs **{cb.get('sector','?')}** — comparisons may be misleading.")
        rows = [
            ("Sector",        ca.get("sector","—"),              cb.get("sector","—")),
            ("Market Cap",    fmt_cr(ca.get("market_cap_cr")),   fmt_cr(cb.get("market_cap_cr"))),
            ("Price (₹)",     fmt(ca.get("current_price"),"₹"),  fmt(cb.get("current_price"),"₹")),
            ("P/E",           fmt(ca.get("pe_ratio")),            fmt(cb.get("pe_ratio"))),
            ("P/B",           fmt(ca.get("pb_ratio")),            fmt(cb.get("pb_ratio"))),
            ("EV/EBITDA",     fmt(ca.get("ev_ebitda")),           fmt(cb.get("ev_ebitda"))),
            ("ROE %",         fmt(ca.get("roe_pct"),suf="%"),     fmt(cb.get("roe_pct"),suf="%")),
            ("Net Margin %",  fmt(ca.get("net_margin_pct"),suf="%"), fmt(cb.get("net_margin_pct"),suf="%")),
            ("Revenue",       fmt_cr(ca.get("revenue_cr")),      fmt_cr(cb.get("revenue_cr"))),
            ("Net Income",    fmt_cr(ca.get("net_income_cr")),   fmt_cr(cb.get("net_income_cr"))),
            ("D/E",           fmt(ca.get("debt_to_equity")),      fmt(cb.get("debt_to_equity"))),
            ("Div Yield %",   fmt(ca.get("dividend_yield_pct"),suf="%"), fmt(cb.get("dividend_yield_pct"),suf="%")),
            ("Rating",        (ca.get("recommendation","—")).upper(), (cb.get("recommendation","—")).upper()),
            ("Target Price",  fmt(ca.get("target_price"),"₹"),   fmt(cb.get("target_price"),"₹")),
            ("Last fetched",  (ca.get("fetched_at",""))[:10],    (cb.get("fetched_at",""))[:10]),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["Metric",cmp_a,cmp_b]).set_index("Metric"), use_container_width=True)
        st.caption("Source: Yahoo Finance via yfinance")
