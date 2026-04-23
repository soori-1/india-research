"""
fetcher.py
----------
Fetches financial data from yfinance for all NSE tickers and saves
everything to data/companies.json in the repo.

GitHub Actions runs this on a schedule and commits the updated file
back to the repo. Streamlit reads the JSON directly — no database needed.
"""

import yfinance as yf
import json
import os
import time
import logging
from datetime import datetime, timezone
from tickers import TOP_INDIAN_TICKERS, get_sector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

DATA_DIR  = "data"
DATA_FILE = os.path.join(DATA_DIR, "companies.json")
NEWS_FILE = os.path.join(DATA_DIR, "news.json")
META_FILE = os.path.join(DATA_DIR, "meta.json")

MIN_MARKET_CAP_CR = 500
INR_CRORE = 1e7


def _safe(val, decimals=4):
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN
            return None
        return round(f, decimals)
    except Exception:
        return None


def _crore(val):
    if val is None:
        return None
    try:
        return round(float(val) / INR_CRORE, 2)
    except Exception:
        return None


def _pct(val):
    """Convert 0.15 → 15.0 for display."""
    v = _safe(val)
    return round(v * 100, 2) if v is not None else None


def fetch_one(ticker: str) -> dict | None:
    """
    Fetch all data for one ticker. Returns a dict or None if skipped/failed.
    Every field that comes from yfinance includes a source_url so the UI
    can always show where the number came from.
    """
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}

        # Market cap filter
        mkt_cap_cr = _crore(info.get("marketCap"))
        if mkt_cap_cr is not None and mkt_cap_cr < MIN_MARKET_CAP_CR:
            return None  # below threshold

        now      = datetime.now(timezone.utc).isoformat()
        src_url  = f"https://finance.yahoo.com/quote/{ticker}"
        src_name = "Yahoo Finance (yfinance)"

        record = {
            # Identity
            "ticker":       ticker,
            "ticker_short": ticker.replace(".NS", ""),
            "name":         info.get("longName") or info.get("shortName") or ticker,
            "sector":       get_sector(ticker) or info.get("sector", "Other"),
            "industry":     info.get("industry", ""),
            "exchange":     "NSE",

            # Source provenance — every record cites its source
            "source_name":  src_name,
            "source_url":   src_url,
            "fetched_at":   now,

            # Market data
            "current_price":    _safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            "market_cap_cr":    mkt_cap_cr,
            "week_52_high":     _safe(info.get("fiftyTwoWeekHigh")),
            "week_52_low":      _safe(info.get("fiftyTwoWeekLow")),
            "beta":             _safe(info.get("beta")),
            "avg_volume":       _safe(info.get("averageVolume"), 0),

            # Valuation ratios
            "pe_ratio":         _safe(info.get("trailingPE")),
            "pb_ratio":         _safe(info.get("priceToBook")),
            "ps_ratio":         _safe(info.get("priceToSalesTrailing12Months")),
            "peg_ratio":        _safe(info.get("pegRatio")),
            "ev_ebitda":        _safe(info.get("enterpriseToEbitda")),
            "enterprise_value_cr": _crore(info.get("enterpriseValue")),

            # Income statement
            "revenue_cr":       _crore(info.get("totalRevenue")),
            "revenue_growth_pct": _pct(info.get("revenueGrowth")),
            "gross_profit_cr":  _crore(info.get("grossProfits")),
            "ebitda_cr":        _crore(info.get("ebitda")),
            "net_income_cr":    _crore(info.get("netIncomeToCommon")),
            "eps":              _safe(info.get("trailingEps")),
            "eps_growth_pct":   _pct(info.get("earningsGrowth")),

            # Balance sheet
            "total_assets_cr":  _crore(info.get("totalAssets")),
            "total_debt_cr":    _crore(info.get("totalDebt")),
            "cash_cr":          _crore(info.get("totalCash")),
            "book_value":       _safe(info.get("bookValue")),

            # Profitability
            "roe_pct":          _pct(info.get("returnOnEquity")),
            "roa_pct":          _pct(info.get("returnOnAssets")),
            "gross_margin_pct": _pct(info.get("grossMargins")),
            "op_margin_pct":    _pct(info.get("operatingMargins")),
            "net_margin_pct":   _pct(info.get("profitMargins")),
            "debt_to_equity":   _safe(info.get("debtToEquity")),
            "current_ratio":    _safe(info.get("currentRatio")),
            "quick_ratio":      _safe(info.get("quickRatio")),

            # Dividends
            "dividend_yield_pct": _pct(info.get("dividendYield")),
            "dividend_rate":    _safe(info.get("dividendRate")),
            "payout_ratio_pct": _pct(info.get("payoutRatio")),

            # Analyst
            "target_price":     _safe(info.get("targetMeanPrice")),
            "analyst_count":    info.get("numberOfAnalystOpinions"),
            "recommendation":   (info.get("recommendationKey") or "").lower(),

            # News (latest 8)
            "news": [],
        }

        # Fetch news
        try:
            news_raw = t.news or []
            for n in news_raw[:8]:
                link = n.get("link") or n.get("url") or ""
                if not link:
                    continue
                pub = n.get("providerPublishTime")
                record["news"].append({
                    "title":     n.get("title", ""),
                    "publisher": n.get("publisher", "Yahoo Finance"),
                    "link":      link,
                    "published": datetime.fromtimestamp(pub, tz=timezone.utc).strftime("%d %b %Y") if pub else "",
                })
        except Exception:
            pass

        return record

    except Exception as e:
        log.warning(f"  ✗ {ticker}: {e}")
        return None


def run_financial_update(tickers=None, batch_size=50, delay=1.2):
    """
    Main fetch loop. Saves all results to data/companies.json.
    Called by GitHub Actions monthly.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    tickers = tickers or TOP_INDIAN_TICKERS

    # Load existing data so we can preserve records that fail this run
    existing = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                for rec in json.load(f):
                    existing[rec["ticker"]] = rec
            log.info(f"Loaded {len(existing)} existing records")
        except Exception:
            pass

    results  = dict(existing)  # start with existing, overwrite on success
    ok = fail = skip = 0

    for i, ticker in enumerate(tickers):
        log.info(f"[{i+1}/{len(tickers)}] {ticker}")
        rec = fetch_one(ticker)

        if rec is None:
            # Could be below 500 Cr or a fetch error — keep existing if we have it
            if ticker not in existing:
                skip += 1
            else:
                fail += 1
                log.info(f"  → keeping existing data for {ticker}")
        else:
            results[ticker] = rec
            ok += 1
            log.info(f"  ✓ {rec['name']} | ₹{rec['market_cap_cr']} Cr")

        # Batch pause to avoid rate limiting
        if (i + 1) % batch_size == 0:
            log.info(f"  Batch pause ({delay}s)...")
            time.sleep(delay)

    # Save
    output = sorted(results.values(), key=lambda x: x.get("market_cap_cr") or 0, reverse=True)
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Save metadata
    meta = {
        "last_financial_update": datetime.now(timezone.utc).isoformat(),
        "total_companies":       len(output),
        "fetch_ok":              ok,
        "fetch_failed":          fail,
        "fetch_skipped":         skip,
        "source":                "Yahoo Finance via yfinance",
    }
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    log.info(f"\n✓ Done — {ok} updated, {fail} kept existing, {skip} skipped")
    log.info(f"✓ Saved {len(output)} companies to {DATA_FILE}")
    return meta


def run_news_update(tickers=None):
    """
    Lightweight news-only update. Runs every 3 days.
    Updates the news field in each company record.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        log.warning("No companies.json found — run financial update first")
        return

    with open(DATA_FILE) as f:
        companies = json.load(f)

    company_map = {c["ticker"]: c for c in companies}
    tickers     = tickers or list(company_map.keys())
    updated     = 0

    for i, ticker in enumerate(tickers):
        try:
            t    = yf.Ticker(ticker)
            news = t.news or []
            items = []
            for n in news[:8]:
                link = n.get("link") or n.get("url") or ""
                if not link:
                    continue
                pub = n.get("providerPublishTime")
                items.append({
                    "title":     n.get("title", ""),
                    "publisher": n.get("publisher", "Yahoo Finance"),
                    "link":      link,
                    "published": datetime.fromtimestamp(pub, tz=timezone.utc).strftime("%d %b %Y") if pub else "",
                })
            if ticker in company_map:
                company_map[ticker]["news"] = items
                company_map[ticker]["news_updated_at"] = datetime.now(timezone.utc).isoformat()
                updated += 1
        except Exception as e:
            log.debug(f"{ticker} news: {e}")

        if (i + 1) % 100 == 0:
            time.sleep(1)

    # Save updated file
    output = sorted(company_map.values(), key=lambda x: x.get("market_cap_cr") or 0, reverse=True)
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2)

    # Update meta
    meta = {}
    if os.path.exists(META_FILE):
        with open(META_FILE) as f:
            meta = json.load(f)
    meta["last_news_update"] = datetime.now(timezone.utc).isoformat()
    meta["news_updated_count"] = updated
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    log.info(f"✓ News updated for {updated} companies")


if __name__ == "__main__":
    import sys
    job = sys.argv[1] if len(sys.argv) > 1 else "both"
    if job == "financials":
        run_financial_update()
    elif job == "news":
        run_news_update()
    else:
        run_financial_update()
        run_news_update()
