# 🇮🇳 India Research — Custom Screener

Fundamental screener for NSE companies (₹500 Cr+) built on:
- **Streamlit Cloud** — UI, free hosting
- **Supabase** — persistent PostgreSQL database
- **GitHub Actions** — automated data refresh (no server needed)
- **yfinance** — market data source

---

## Setup guide (55 minutes total)

### Step 1 — Supabase (10 min)

1. Go to [supabase.com](https://supabase.com) → **Sign up with GitHub**
2. Click **New project** → name it `india-research`
3. Choose a strong DB password — **save it somewhere safe**
4. Region: **Southeast Asia (Singapore)** — closest to India
5. Wait ~2 minutes for provisioning
6. Go to **Project Settings → Database → Connection string**
7. Select **URI** tab → copy the full string:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[REF].supabase.co:5432/postgres
   ```
8. Save this — you'll use it in Steps 2 and 4

---

### Step 2 — GitHub repo (15 min)

1. Go to [github.com](https://github.com) → **New repository**
2. Name: `india-research` → **Private** → Create
3. Clone locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/india-research.git
   cd india-research
   ```
4. Copy all files from this folder into the cloned repo
5. Add Supabase URL as a secret:
   - Repo → **Settings → Secrets and variables → Actions**
   - Click **New repository secret**
   - Name: `SUPABASE_DB_URL`
   - Value: your Supabase connection string from Step 1
   - Click **Add secret**
6. Push the code:
   ```bash
   git add .
   git commit -m "initial commit"
   git push
   ```

---

### Step 3 — Run first data fetch (25 min, automated)

1. Go to your GitHub repo → **Actions** tab
2. Click **Data refresh** workflow
3. Click **Run workflow** → select job: **both** → **Run workflow**
4. Watch the logs — it fetches ~1000 tickers from yfinance
5. Takes ~25 minutes. You can close the browser — it runs in the cloud.

After this finishes, your Supabase database will have data for all companies.

---

### Step 4 — Streamlit Cloud (10 min)

1. Go to [share.streamlit.io](https://share.streamlit.io) → **Sign in with GitHub**
2. Click **New app**
3. Repository: `india-research` → Branch: `main` → Main file: `streamlit_app.py`
4. Click **Advanced settings** → **Secrets** → paste this:
   ```toml
   [database]
   SUPABASE_DB_URL = "postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres"
   ```
   (Replace with your actual connection string)
5. Click **Deploy**
6. Your app will be live at `https://YOUR-APP.streamlit.app`

---

### Step 5 — Verify (5 min)

1. **Supabase**: Dashboard → Table Editor → `companies` table → should show rows
2. **Streamlit app**: Build a test screener (P/E ≤ 20, ROE ≥ 15%) → should return results
3. **GitHub Actions**: Actions tab → Data refresh → should show next scheduled run

---

## Automatic refresh schedule

| Job | Schedule | What it does |
|-----|----------|-------------|
| Financial data | 1st of every month, 7am IST | Re-fetches all ratios, income, balance sheet |
| News | Every 3 days, 7am IST | Latest news per ticker |

To run manually: GitHub → Actions → Data refresh → Run workflow

---

## File structure

```
india-research/
├── streamlit_app.py          ← Main Streamlit UI (this screener)
├── database.py               ← SQLAlchemy models, reads from Supabase
├── fetcher.py                ← yfinance data fetcher
├── tickers.py                ← 1000 NSE tickers + sector mapping
├── requirements.txt          ← Python dependencies
├── .gitignore                ← Keeps secrets + DB out of GitHub
├── .streamlit/
│   └── secrets.toml.template ← Copy this, fill in your URL, add to Streamlit Cloud
└── .github/
    └── workflows/
        └── data_refresh.yml  ← GitHub Actions scheduler
```

---

## Adding your existing 3 screeners

Your existing Streamlit screener files stay exactly as they are.

To combine everything into one multi-page app later:
1. Create a `pages/` folder
2. Move `streamlit_app.py` → `pages/1_Custom_Screener.py`
3. Move your 3 screener files → `pages/2_Screener_A.py`, `pages/3_Screener_B.py`, etc.
4. Create a `Home.py` as the landing page

Streamlit Cloud auto-detects the `pages/` folder and adds navigation.

---

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Supabase URL (or use local SQLite — no URL needed)
export SUPABASE_DB_URL="postgresql://..."

# OR create .streamlit/secrets.toml (see template)

# Run locally
streamlit run streamlit_app.py
```

---

## Migrating to a proper frontend later

When you're ready to upgrade from Streamlit to React/Next.js:
1. Supabase has a built-in REST API — your new frontend queries it directly
2. The screener logic moves from Python to a FastAPI endpoint (already built in the original `main.py`)
3. The database schema stays identical — no migration needed
4. Streamlit version stays running until the new frontend is ready
