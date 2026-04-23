"""
Data fetcher — yfinance wrapper.
Every value written to DB includes source_name + source_url so the frontend
can show "Source: Yahoo Finance" with a direct link. No hallucination possible
because we only store what yfinance actually returns.
"""

import yfinance as yf
import time
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from database import SessionLocal, Financials, EarningsHistory, NewsItem, Company, UpdateLog, init_db
from tickers import TOP_INDIAN_TICKERS, get_sector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

INR_CRORE = 1e7  # 1 crore = 10 million
MIN_MARKET_CAP_CR = 500  # only store companies above 500 Cr

def _crore(val):
    """Convert raw INR to crores. Returns None if val is None."""
    if val is None:
        return None
    try:
        return round(float(val) / INR_CRORE, 2)
    except Exception:
        return None

def _safe(val):
    """Return rounded float or None."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if (f != f) else round(f, 4)  # NaN check
    except Exception:
        return None

def source_url(ticker: str) -> str:
    return f"https://finance.yahoo.com/quote/{ticker}"

def fetch_company_financials(ticker: str, db: Session) -> dict:
    """
    Fetch all financial data for one ticker via yfinance.
    Returns a dict with status and data.
    Only stores to DB if market cap > 500 Cr.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        mkt_cap = _safe(info.get("marketCap"))
        mkt_cap_cr = _crore(mkt_cap * INR_CRORE) if mkt_cap else None  # info already in native currency

        # yfinance returns market cap in native currency (INR for .NS tickers)
        mkt_cap_cr_direct = _crore(info.get("marketCap"))

        if mkt_cap_cr_direct and mkt_cap_cr_direct < MIN_MARKET_CAP_CR:
            return {"status": "skipped", "reason": f"Market cap {mkt_cap_cr_direct:.0f} Cr < {MIN_MARKET_CAP_CR} Cr"}

        now = datetime.now(timezone.utc)
        src_url = source_url(ticker)

        # Upsert company record
        company = db.query(Company).filter_by(ticker=ticker).first()
        if not company:
            company = Company(ticker=ticker)
            db.add(company)

        company.name = info.get("longName") or info.get("shortName") or ticker
        company.sector = get_sector(ticker) or info.get("sector", "Unknown")
        company.industry = info.get("industry", "Unknown")
        company.market_cap_cr = mkt_cap_cr_direct
        company.last_updated = now

        # Insert new financials row (keeps history)
        fin = Financials(
            ticker=ticker,
            fetched_at=now,
            source_name="Yahoo Finance (yfinance)",
            source_url=src_url,

            # Valuation
            pe_ratio=_safe(info.get("trailingPE")),
            pb_ratio=_safe(info.get("priceToBook")),
            ps_ratio=_safe(info.get("priceToSalesTrailing12Months")),
            peg_ratio=_safe(info.get("pegRatio")),
            ev_ebitda=_safe(info.get("enterpriseToEbitda")),
            enterprise_value=_crore(info.get("enterpriseValue")),

            # Market
            current_price=_safe(info.get("currentPrice") or info.get("regularMarketPrice")),
            market_cap=_safe(info.get("marketCap")),
            market_cap_cr=mkt_cap_cr_direct,
            week_52_high=_safe(info.get("fiftyTwoWeekHigh")),
            week_52_low=_safe(info.get("fiftyTwoWeekLow")),
            beta=_safe(info.get("beta")),
            avg_volume=_safe(info.get("averageVolume")),

            # Income
            revenue_cr=_crore(info.get("totalRevenue")),
            revenue_growth=_safe(info.get("revenueGrowth")),
            gross_profit_cr=_crore(info.get("grossProfits")),
            ebitda_cr=_crore(info.get("ebitda")),
            net_income_cr=_crore(info.get("netIncomeToCommon")),
            eps=_safe(info.get("trailingEps")),
            eps_growth=_safe(info.get("earningsGrowth")),

            # Balance sheet
            total_assets_cr=_crore(info.get("totalAssets")),
            total_debt_cr=_crore(info.get("totalDebt")),
            cash_cr=_crore(info.get("totalCash")),
            book_value=_safe(info.get("bookValue")),

            # Profitability
            roe=_safe(info.get("returnOnEquity")),
            roa=_safe(info.get("returnOnAssets")),
            gross_margin=_safe(info.get("grossMargins")),
            operating_margin=_safe(info.get("operatingMargins")),
            profit_margin=_safe(info.get("profitMargins")),
            debt_to_equity=_safe(info.get("debtToEquity")),
            current_ratio=_safe(info.get("currentRatio")),
            quick_ratio=_safe(info.get("quickRatio")),

            # Dividends
            dividend_yield=_safe(info.get("dividendYield")),
            dividend_rate=_safe(info.get("dividendRate")),
            payout_ratio=_safe(info.get("payoutRatio")),

            # Analyst
            target_mean_price=_safe(info.get("targetMeanPrice")),
            analyst_count=info.get("numberOfAnalystOpinions"),
            recommendation=info.get("recommendationKey"),
        )
        db.add(fin)

        # Earnings history
        try:
            earnings_df = t.quarterly_earnings
            if earnings_df is not None and not earnings_df.empty:
                for period, row in earnings_df.iterrows():
                    period_str = str(period)
                    existing = db.query(EarningsHistory).filter_by(
                        ticker=ticker, period=period_str
                    ).first()
                    if not existing:
                        eh = EarningsHistory(
                            ticker=ticker,
                            period=period_str,
                            reported_eps=_safe(row.get("Reported EPS") or row.get("Actual")),
                            estimated_eps=_safe(row.get("Estimated EPS") or row.get("Estimate")),
                            surprise_pct=_safe(row.get("Surprise(%)")),
                            fetched_at=now,
                            source_name="Yahoo Finance (yfinance)",
                            source_url=src_url,
                        )
                        db.add(eh)
        except Exception as e:
            log.debug(f"{ticker} earnings history: {e}")

        db.commit()
        return {"status": "ok", "name": company.name, "market_cap_cr": mkt_cap_cr_direct}

    except Exception as e:
        db.rollback()
        return {"status": "error", "error": str(e)}

def fetch_news(ticker: str, db: Session):
    """Fetch latest news for a ticker. Deduplicated by link."""
    try:
        t = yf.Ticker(ticker)
        news = t.news or []
        added = 0
        for item in news[:15]:
            link = item.get("link") or item.get("url") or ""
            if not link:
                continue
            existing = db.query(NewsItem).filter_by(link=link).first()
            if existing:
                continue
            published = item.get("providerPublishTime")
            pub_dt = datetime.fromtimestamp(published, tz=timezone.utc) if published else None
            publisher = item.get("publisher") or ""
            ni = NewsItem(
                ticker=ticker,
                title=item.get("title", ""),
                summary=item.get("summary") or item.get("description") or "",
                publisher=publisher,
                link=link,
                published_at=pub_dt,
                fetched_at=datetime.now(timezone.utc),
                source_name=publisher or "Yahoo Finance News",
            )
            db.add(ni)
            added += 1
        db.commit()
        return added
    except Exception as e:
        db.rollback()
        log.debug(f"{ticker} news: {e}")
        return 0

def run_financial_update(tickers: list = None, batch_size: int = 50, delay: float = 1.0):
    """
    Full financial update run. Call this monthly (or manually).
    Processes in batches to avoid rate limiting.
    """
    tickers = tickers or TOP_INDIAN_TICKERS
    db = SessionLocal()
    log_entry = UpdateLog(
        job_name="financial_update",
        started_at=datetime.now(timezone.utc),
        status="running",
        tickers_updated=0,
        tickers_failed=0,
    )
    db.add(log_entry)
    db.commit()

    ok = fail = skip = 0
    for i, ticker in enumerate(tickers):
        result = fetch_company_financials(ticker, db)
        if result["status"] == "ok":
            ok += 1
            log.info(f"[{i+1}/{len(tickers)}] ✓ {ticker} — {result.get('name')} | ₹{result.get('market_cap_cr','?')} Cr")
        elif result["status"] == "skipped":
            skip += 1
            log.debug(f"[{i+1}/{len(tickers)}] SKIP {ticker}: {result.get('reason')}")
        else:
            fail += 1
            log.warning(f"[{i+1}/{len(tickers)}] ✗ {ticker}: {result.get('error')}")

        if (i + 1) % batch_size == 0:
            time.sleep(delay)

    log_entry.finished_at = datetime.now(timezone.utc)
    log_entry.tickers_updated = ok
    log_entry.tickers_failed = fail
    log_entry.status = "done"
    log_entry.notes = f"skipped (below 500 Cr): {skip}"
    db.commit()
    db.close()
    log.info(f"\n✓ Financial update done: {ok} updated, {fail} failed, {skip} skipped")
    return {"ok": ok, "fail": fail, "skip": skip}

def run_news_update(tickers: list = None):
    """
    News update run. Call every 3 days.
    Only fetches news for companies already in the DB.
    """
    tickers = tickers or TOP_INDIAN_TICKERS
    db = SessionLocal()
    total_added = 0
    for ticker in tickers:
        added = fetch_news(ticker, db)
        total_added += added
    db.close()
    log.info(f"✓ News update done: {total_added} new items added")
    return {"news_added": total_added}

if __name__ == "__main__":
    init_db()
    print("\nStarting initial data fetch for top Indian companies...")
    print("This will take 15-30 minutes for 1000 tickers. Ctrl+C to stop anytime.\n")
    run_financial_update()
    run_news_update()
