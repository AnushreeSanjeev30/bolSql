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

# Single unified DB file for both core pipeline and trends
DB_PATH = BASE_DIR / os.getenv("DB_PATH", "kirana_trends.db")
TRENDS_DB_PATH = DB_PATH

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
Tables:
  inventory(id INTEGER PK, name TEXT, quantity REAL, unit TEXT, price REAL)
  transactions(id INTEGER PK, item_id INTEGER FK→inventory.id, type TEXT, quantity REAL, timestamp TEXT)

Notes:
  - inventory.unit: 'kg', 'litre', 'packet', 'piece', 'dozen'
  - transactions.type: 'sale' (item sold/removed) | 'restock' (item added)
  - All quantities are REAL (decimals allowed)
  - timestamp format: 'YYYY-MM-DD HH:MM:SS'
"""
