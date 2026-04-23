"""
Database — reads SUPABASE_DB_URL from environment.
Locally: set it in .env or export it in your shell.
Streamlit Cloud: add it in App Settings → Secrets.
GitHub Actions: stored as a repository secret.
"""

import os
from sqlalchemy import (
    create_engine, Column, String, Float, Integer,
    DateTime, Text, Boolean, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from datetime import datetime

def get_database_url():
    # Streamlit secrets format
    try:
        import streamlit as st
        url = st.secrets.get("database", {}).get("SUPABASE_DB_URL")
        if url:
            return url
    except Exception:
        pass
    # Environment variable (GitHub Actions, local .env)
    url = os.environ.get("SUPABASE_DB_URL")
    if url:
        return url
    # Fallback to local SQLite for development only
    os.makedirs("data", exist_ok=True)
    return "sqlite:///./data/india_research.db"

DATABASE_URL = get_database_url()

# PostgreSQL needs pool_pre_ping to handle connection drops
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class Company(Base):
    __tablename__ = "companies"
    ticker          = Column(String, primary_key=True)
    name            = Column(String)
    sector          = Column(String)
    industry        = Column(String)
    exchange        = Column(String, default="NSE")
    market_cap_cr   = Column(Float)
    is_active       = Column(Boolean, default=True)
    last_updated    = Column(DateTime, default=datetime.utcnow)

class Financials(Base):
    __tablename__ = "financials"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticker          = Column(String, index=True)
    fetched_at      = Column(DateTime, default=datetime.utcnow)
    source_name     = Column(String, default="Yahoo Finance / yfinance")
    source_url      = Column(String)

    pe_ratio        = Column(Float)
    pb_ratio        = Column(Float)
    ps_ratio        = Column(Float)
    peg_ratio       = Column(Float)
    ev_ebitda       = Column(Float)
    enterprise_value= Column(Float)

    current_price   = Column(Float)
    market_cap      = Column(Float)
    market_cap_cr   = Column(Float)
    week_52_high    = Column(Float)
    week_52_low     = Column(Float)
    beta            = Column(Float)
    avg_volume      = Column(Float)

    revenue_cr          = Column(Float)
    revenue_growth      = Column(Float)
    gross_profit_cr     = Column(Float)
    ebitda_cr           = Column(Float)
    net_income_cr       = Column(Float)
    eps                 = Column(Float)
    eps_growth          = Column(Float)

    total_assets_cr     = Column(Float)
    total_debt_cr       = Column(Float)
    cash_cr             = Column(Float)
    book_value          = Column(Float)

    roe                 = Column(Float)
    roa                 = Column(Float)
    gross_margin        = Column(Float)
    operating_margin    = Column(Float)
    profit_margin       = Column(Float)
    debt_to_equity      = Column(Float)
    current_ratio       = Column(Float)
    quick_ratio         = Column(Float)

    dividend_yield      = Column(Float)
    dividend_rate       = Column(Float)
    payout_ratio        = Column(Float)

    target_mean_price   = Column(Float)
    analyst_count       = Column(Integer)
    recommendation      = Column(String)

class SavedScreener(Base):
    __tablename__ = "saved_screeners"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String, nullable=False)
    filters     = Column(Text)   # JSON string
    created_at  = Column(DateTime, default=datetime.utcnow)
    last_run    = Column(DateTime)
    result_count= Column(Integer)

class EarningsHistory(Base):
    __tablename__ = "earnings_history"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticker          = Column(String, index=True)
    period          = Column(String)
    reported_eps    = Column(Float)
    estimated_eps   = Column(Float)
    surprise_pct    = Column(Float)
    revenue_actual  = Column(Float)
    revenue_estimate= Column(Float)
    fetched_at      = Column(DateTime, default=datetime.utcnow)
    source_name     = Column(String, default="Yahoo Finance / yfinance")
    source_url      = Column(String)

class NewsItem(Base):
    __tablename__ = "news_items"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    ticker          = Column(String, index=True)
    title           = Column(String)
    summary         = Column(Text)
    publisher       = Column(String)
    link            = Column(String)
    published_at    = Column(DateTime)
    fetched_at      = Column(DateTime, default=datetime.utcnow)
    source_name     = Column(String)

class UpdateLog(Base):
    __tablename__ = "update_log"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    job_name        = Column(String)
    started_at      = Column(DateTime)
    finished_at     = Column(DateTime)
    tickers_updated = Column(Integer)
    tickers_failed  = Column(Integer)
    status          = Column(String)
    notes           = Column(Text)

Index("ix_fin_ticker_date", Financials.ticker, Financials.fetched_at)
Index("ix_news_ticker_date", NewsItem.ticker, NewsItem.published_at)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created/verified")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
