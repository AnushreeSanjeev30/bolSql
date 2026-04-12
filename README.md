

# 🏪 VoiceSQL / KiranaSQL — Hinglish Kirana Intelligence

Hinglish voice‑first inventory and analytics system for Indian shopkeepers.  
Say “50kg atta add karo” or “dead stock dikhao” and it updates / analyses your kirana database.

---

## ✨ Features

- **Voice + Text Inventory**
  - Add stock: “50kg atta add karo”
  - Record sales: “10 packet biscuit becha”
  - Check stock: “chawal kitna bacha hai”
- **Modern Web UI**
  - React + Vite single‑page app
  - Panels for Voice Query, Inventory, and History
  - Live API connection status
- **LLM‑powered SQL**
  - Hinglish → SQL over a SQLite inventory DB
  - RAG with curated examples for robust mappings
  - Safety layer that only allows `SELECT`, `INSERT`, `UPDATE`
- **Kirana Trends Analytics (13+ engines)**
  - Sales trends, hourly rush, product demand
  - Seasonal / festival trends
  - Stock depletion & smart re‑order
  - Dead stock, profit analysis
  - Market basket, customer patterns, auto‑subscription
  - Weather‑based recommendations
- **Monthly Auto‑Reports**
  - Human‑readable monthly performance report
  - Auto‑generation in first days of the month
- **Demo Seeder**
  - Script to generate 6 months of realistic demo transactions
  - Lets you play with all trend queries immediately

---

## 📁 Project Structure

```text
final_voicesql/
  api.py              # FastAPI app (REST + optional built UI)
  main.py             # CLI & API entrypoint
  pipeline.py         # Core orchestrator (ASR → NLP → RAG → LLM → DB)
  config.py           # Settings from .env
  logger.py           # Logging setup
  app/
    asr/              # Whisper ASR (voice input)
    nlp/              # Hinglish intent + entity extraction
    rag/              # FAISS + curated examples
    llm/              # LLM wrapper (Groq / Ollama)
    db/               # SQLite inventory + transactions
    safety/           # SQL whitelist validator
    interface/        # Terminal UI (CLI)
    trends/           # Trends engine, classifier, formatter, seeding
  frontend/           # React + Vite UI (dev source)
  frontend_dist/      # Built UI (served by FastAPI if present)
  logs/               # Log files
```

Key modules:

- Core pipeline: pipeline.py  
- API server: api.py  
- Trends engine: engine.py  
- Trends classifier: classifier.py  
- Trend formatter: formatter.py  
- Demo seeder: seed_demo.py  
- Monthly report generator: monthly_report.py  
- Web UI entry: App.jsx

---

## 🔧 Setup

### 1. Python backend

Requirements:

- Python 3.10+ (3.11/3.12/3.13 works)
- Recommended: virtualenv

Install dependencies:

```bash
cd final_voicesql
pip install -r requirements.txt
```

Create .env in the project root:

```env
# LLM provider (default: groq)
GROQ_API_KEY=your_groq_key_here
LLM_PROVIDER=groq          # or: ollama
LLM_MODEL=llama-3.3-70b-versatile

# Optional overrides
# DB_PATH=kirana.db
# LOG_FILE=logs/voicesql.log
# WHISPER_MODEL=base
# RAG_TOP_K=3
```

- For **Groq**, get a free key: https://console.groq.com  
- For **Ollama**, run `ollama pull mistral` and set `LLM_PROVIDER=ollama`.

### 2. React frontend

Requirements:

- Node.js 18+ and npm

Install:

```bash
cd frontend
npm install
```

---

## 🚀 Running the System

### Option A — Terminal only (no UI)

From project root:

```bash
# Text mode (default)
python main.py

# Voice mode (Whisper ASR)
python main.py --voice

# Show generated SQL in output
python main.py --verbose

# Quick self‑tests on the pipeline
python main.py --test
```

### Option B — Backend API + Web UI (recommended)

1. **Start the backend API**

   In one terminal:

   ```bash
   cd final_voicesql
   python main.py --api
   ```

   This runs FastAPI at `http://localhost:8000` with:

   - `POST /query` – main Hinglish query endpoint  
   - `GET /inventory` – current inventory  
   - `GET /health` – health check

2. **Run the React dev server**

   In another terminal:

   ```bash
   cd final_voicesql/frontend
   npm run dev
   ```

   Open the printed URL (usually `http://localhost:5173`).

   The frontend talks to the backend via:

   - Base URL: `VITE_API_URL` env, or `http://localhost:8000` by default  
   - Endpoints used:
     - `GET /health` (to show “API connected” / “API offline” in the sidebar)
     - `GET /inventory`
     - `POST /query`

3. **(Optional) Serve the built UI via FastAPI**

   Build the frontend:

   ```bash
   cd final_voicesql/frontend
   npm run build
   ```

   This writes to `../frontend_dist`.  
   When that folder exists, api.py will:

   - Serve `index.html` at `/`
   - Serve static assets under `/assets`

   Then `python main.py --api` gives you both the API and the SPA on the same port.

---

## 📊 Trends & Analytics

The trends module adds rich analytics on top of your sales history.

Supported trend types (internally):

- `sales_trend` — last N days revenue/orders
- `hourly_rush` — peak hours in the day
- `product_demand` — top‑selling products
- `seasonal_trend` — month‑wise demand
- `stock_depletion` — days until stock‑out
- `smart_reorder` — recommended reorder quantities
- `dead_stock` — items not selling
- `profit_trend` — profit by item
- `festival_trend` — Diwali/Holi/Eid windows across years
- `market_basket` — frequently bought together items
- `customer_pattern` — customer‑level patterns
- `auto_subscription` — next expected purchase dates
- `weather_trend` — season → likely items

### How a trend query flows

1. Your text (“dead stock dikhao”, “pichle 7 din ka sales batao”) is sent to `/query`.
2. `process()` in pipeline.py calls `_trends_pipeline.is_trend_query(text)`.
3. classifier.py uses regex patterns over Hinglish / English to map it to a `trend_type` + params.
4. engine.py runs SQLite queries over `transactions` + `inventory`.
5. formatter.py converts raw data into a Hinglish text summary (with emojis and bullet‑style lines).
6. The result comes back as `PipelineResult(intent="TREND", response=...)` which the UI displays as a normal AI answer.

Examples of queries that will hit trends:

- “pichle 7 din ka sales batao”
- “dead stock dikhao”
- “peak time kab hota hai”
- “diwali mein kya bikta hai”
- “stock kab khatam hoga”
- “sabse zyada profit kaunsa item de raha hai”

---

## 🧪 Seeding Demo Data

To quickly test all trend engines, seed demo data into a fresh kirana.db:

```bash
cd final_voicesql
python app/trends/seed_demo.py
```

What it does:

- Creates `inventory` and `transactions` tables if they don’t exist.
- Populates ~15 common kirana items with a starting stock and cost price.
- Generates ~180 days of realistic transactions:
  - Peak hours morning & evening
  - Seasonal boosts (summer drinks, monsoon chai, winter items)
  - Festival peaks (Diwali, Holi)
  - Multiple customers with IDs like `C001`, `C002`, …

After running this, trend queries in the UI / CLI will output rich analytics instead of “data nahi mila”.

---

## 📄 Monthly Reports

monthly_report.py can generate detailed monthly reports:

- Revenue, profit, and margin
- Daily breakdown
- Top products
- Dead stock and critical stock
- Peak day and peak hour

You can run manually:
  
```bash
cd final_voicesql
python app/trends/monthly_report.py           # last month
python app/trends/monthly_report.py 2025 3   # March 2025
```

The pipeline also calls `maybe_generate_monthly_report(DB_PATH)` at startup (guarded), so in the first 3 days of a month it auto‑creates the previous month’s report if missing.

Outputs:

- JSON: `reports/report_YYYY_MM.json`
- Text: `reports/report_YYYY_MM.txt` (nicely formatted)

---

## 🧰 Troubleshooting

- **UI says “API offline / cannot connect”**
  - Ensure backend is running:  
    `python main.py --api`
  - Check: `http://localhost:8000/health` → should return JSON with `"status": "ok"`.
- **UI shows “API se connect nahi ho saka…” when sending query**
  - Look at backend terminal for a stack trace on `/query`.
  - Common causes: missing `GROQ_API_KEY`, DB issues, or syntax error in pipeline.
- **Trends say “data nahi mila”**
  - Run the seeder: `python app/trends/seed_demo.py`.
  - Or check that your own `transactions` table has enough history.
- **LLM errors / too slow**
  - Verify .env keys.
  - For Ollama, ensure the model is pulled and the server is running.

