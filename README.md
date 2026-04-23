# 🇮🇳 India Research — Custom Screener

No database. No connection strings. No servers.

**How it works:**
- GitHub Actions fetches data from yfinance → saves to `data/companies.json` → commits it back to this repo
- Streamlit reads `companies.json` directly — that's it

---

## Setup (3 steps, ~10 minutes + 25 min first fetch)

### Step 1 — Push this code to your GitHub repo

```bash
git clone https://github.com/YOUR-USERNAME/india-research.git
cd india-research
# copy all these files in
git add .
git commit -m "initial"
git push
```

Make sure the folder structure looks like this:
```
india-research/
├── streamlit_app.py
├── fetcher.py
├── tickers.py
├── requirements.txt
├── .gitignore
├── data/               ← created automatically by Actions
└── .github/
    └── workflows/
        └── data_refresh.yml
```

**Important:** `data_refresh.yml` must be inside `.github/workflows/` — not in the root.

---

### Step 2 — Run first data fetch

1. Go to your GitHub repo → **Actions** tab
2. Click **Data refresh** in the left panel
3. Click **Run workflow** (top right)
4. Select job: **both**
5. Click the green **Run workflow** button
6. Watch it run — takes ~25 minutes for all companies

When it finishes you'll see a new commit: *"Auto: data refresh 2024-xx-xx"*
That means `data/companies.json` is now in your repo with data for all companies.

---

### Step 3 — Deploy on Streamlit Cloud

1. Go to **share.streamlit.io** → Sign in with GitHub
2. Click **New app**
3. Repository: `india-research`
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. Click **Deploy**

**No secrets needed** — the app reads from `companies.json` in the repo.

Your app will be live at `https://YOUR-APP.streamlit.app`

---

## Automatic refresh schedule

| Job | When | What |
|-----|------|------|
| Financial data | 1st of every month | Re-fetches all ratios, prices, balance sheet |
| News | Every 3 days | Updates news for all companies |

Each run commits the updated `companies.json` back to the repo.
Streamlit Cloud auto-refreshes when it detects a new commit.

### Manual refresh
GitHub → Actions → Data refresh → Run workflow → choose financials / news / both

---

## File structure

| File | Purpose |
|------|---------|
| `streamlit_app.py` | The screener UI |
| `fetcher.py` | yfinance fetcher, saves to `data/companies.json` |
| `tickers.py` | 700+ NSE tickers + sector mapping |
| `requirements.txt` | Python dependencies |
| `.github/workflows/data_refresh.yml` | Automated scheduler |
| `data/companies.json` | Auto-generated, committed by Actions |
| `data/meta.json` | Auto-generated, last update timestamps |
| `data/saved_screeners.json` | Your saved screener definitions |

---

## Adding your existing 3 screeners

To combine all screeners into one multi-page app:

1. Create a `pages/` folder in the repo
2. Rename `streamlit_app.py` → `pages/1_Custom_Screener.py`
3. Add your existing screeners as `pages/2_Your_Screener.py`, etc.
4. Create a `Home.py` as the landing page

Streamlit Cloud detects `pages/` automatically and adds navigation in the sidebar.

---

## No database, no secrets — how is this secure?

`companies.json` contains only publicly available market data (same data you'd see on Yahoo Finance).
There is nothing sensitive in the repo. Your saved screener filters are also just JSON — no personal data.

If you later want to add private notes, watchlists, or client-specific data, that's when you'd add a database. For now this is clean and simple.
