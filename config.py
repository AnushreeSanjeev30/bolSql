"""
config.py - Central configuration for VoiceSQL
Loads from .env file. All modules import from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# === Paths ===
BASE_DIR = Path(__file__).parent

# Core application DB (inventory, transactions, etc.)
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "kirana_trends.db")

# Separate trends / customer-analytics DB. By default this is the
# legacy kirana.db file, as requested, but can be overridden via
# TRENDS_DB_PATH in .env when needed.
TRENDS_DB_PATH = BASE_DIR / os.getenv("TRENDS_DB_PATH", "kirana.db")

LOG_FILE = BASE_DIR / os.getenv("LOG_FILE", "logs/voicesql.log")
RAG_INDEX_PATH = BASE_DIR / "app" / "rag" / "faiss_index"

# === LLM ===
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")          # groq | ollama
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# === ASR ===
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")         # tiny | base | small
ASR_LANGUAGE = os.getenv("ASR_LANGUAGE", "hi")

# === Audio Recording ===
RECORD_SECONDS = int(os.getenv("RECORD_SECONDS", "5"))
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))

# === RAG ===
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

# === Logging ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# === Safety ===
ALLOWED_SQL_COMMANDS = {"SELECT", "INSERT", "UPDATE"}
BLOCKED_SQL_COMMANDS = {"DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "EXEC", "EXECUTE"}

# === DB Schema for prompts ===
DB_SCHEMA = """
Tables (core operations):
  inventory(
    id INTEGER PRIMARY KEY,
    name TEXT,
    quantity REAL,
    unit TEXT,
    price REAL,
    cost_price REAL,
    category TEXT,
    expiry_date TEXT
  )

  transactions(
    id INTEGER PRIMARY KEY,
    item_id INTEGER REFERENCES inventory(id),
    item_name TEXT,
    type TEXT,              -- 'sale' or 'restock'
    quantity REAL,
    price REAL,
    timestamp TEXT,         -- 'YYYY-MM-DD HH:MM:SS'
    customer_id TEXT,       -- links to customers.customer_id
    channel TEXT,
    order_id TEXT,
    cost_price REAL
  )

Customer analytics tables:
  customers(
    customer_id TEXT PRIMARY KEY,
    name TEXT,
    phone TEXT,
    locality TEXT,
    credit_balance REAL,
    first_visit TEXT,
    last_visit TEXT,
    total_lifetime_value REAL
  )

  customer_segments(
    customer_id TEXT PRIMARY KEY REFERENCES customers(customer_id),
    rfm_score REAL,
    segment TEXT,
    recency_days INTEGER,
    frequency_count INTEGER,
    monetary_total REAL,
    ltv_score REAL,
    churn_risk REAL,
    updated_at TEXT
  )

  orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE,
    customer_id TEXT REFERENCES customers(customer_id),
    item_id INTEGER REFERENCES inventory(id),
    item_name TEXT,
    quantity REAL,
    price REAL,
    order_date TEXT,
    status TEXT,
    delivery_date TEXT,
    notes TEXT
  )

  basket_pairs(
    item_a TEXT,
    item_b TEXT,
    co_occurrence_count INTEGER,
    lift_score REAL,
    last_updated TEXT,
    PRIMARY KEY (item_a, item_b)
  )

  predicted_orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT REFERENCES customers(customer_id),
    item_name TEXT,
    predicted_qty REAL,
    predicted_date TEXT,
    confidence REAL,
    fulfilled INTEGER,
    created_at TEXT
  )

  price_history(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER REFERENCES inventory(id),
    item_name TEXT,
    old_price REAL,
    new_price REAL,
    changed_by TEXT,
    changed_at TEXT
  )

Notes:
  - inventory.unit: 'kg', 'litre', 'packet', 'piece', 'dozen'
  - transactions.type: 'sale' (item sold/removed) | 'restock' (item added)
  - Use DATE(timestamp) or strftime('%Y-%m', timestamp) for day/month cohorts
  - Join rules:
      transactions.customer_id = customers.customer_id
      transactions.item_id = inventory.id
      customer_segments.customer_id = customers.customer_id
      orders.customer_id = customers.customer_id
  - All quantities and prices are REAL (decimals allowed)
  - timestamp / *_date fields use 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
"""
