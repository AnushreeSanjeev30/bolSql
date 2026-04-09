"""
app/db/database.py
SQLite database layer — inventory + transactions.
Auto-creates tables, normalizes item names.
"""

import sqlite3
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import DB_PATH
from logger import get_logger

log = get_logger("db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Safe concurrent access
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if missing. Seed sample data on first run."""
    log.info("Initializing database at %s", DB_PATH)
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS inventory (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE,
            quantity   REAL    NOT NULL DEFAULT 0,
            unit       TEXT    NOT NULL DEFAULT 'piece',
            price      REAL    DEFAULT 0,
            cost_price REAL
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER REFERENCES inventory(id),
            item_name  TEXT,
            type       TEXT    CHECK(type IN ('sale','restock')),
            quantity   REAL    NOT NULL,
            price      REAL    DEFAULT 0,
            timestamp  TEXT    NOT NULL,
            customer_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_txn_item ON transactions(item_id);
        CREATE INDEX IF NOT EXISTS idx_txn_time ON transactions(timestamp);
    """)

    # Seed if empty
    if not c.execute("SELECT 1 FROM inventory LIMIT 1").fetchone():
        log.info("Seeding sample inventory data")
        seed_data = [
            ("atta",     50.0, "kg",     35.0),
            ("chawal",   30.0, "kg",     60.0),
            ("dal",      20.0, "kg",     90.0),
            ("tel",      15.0, "litre",  130.0),
            ("chini",    25.0, "kg",     45.0),
            ("namak",    10.0, "kg",     20.0),
            ("doodh",    20.0, "litre",  60.0),
            ("biscuit",  80.0, "packet", 10.0),
            ("sabun",    30.0, "piece",  40.0),
            ("chai",     5.0,  "kg",     400.0),
            ("mirchi",   3.0,  "kg",     80.0),
            ("haldi",    2.0,  "kg",     120.0),
            ("aloo",     40.0, "kg",     25.0),     # Potatoes
            ("apple",    35.0, "piece",  15.0),    # Apples
            ("mango",    25.0, "piece",  20.0),    # Mangoes
        ]
        c.executemany(
            "INSERT INTO inventory (name, quantity, unit, price) VALUES (?,?,?,?)",
            seed_data
        )
    conn.commit()
    conn.close()
    log.info("Database ready")


def normalize_name(name: str) -> str:
    """Lowercase, strip extra spaces — for consistent item lookup."""
    return re.sub(r"\s+", " ", name.strip().lower())


def get_item(name: str) -> Optional[dict]:
    """Fuzzy-ish item lookup: exact first, then LIKE."""
    norm = normalize_name(name)
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM inventory WHERE LOWER(name)=?", (norm,)
    ).fetchone()
    if not row:
        # Partial match
        row = conn.execute(
            "SELECT * FROM inventory WHERE LOWER(name) LIKE ?", (f"%{norm}%",)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_items() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_item(name: str, quantity: float, unit: str, price: float = 0.0) -> dict:
    """
    Add item if not exists, else add quantity to existing stock.
    Returns updated row.
    """
    norm = normalize_name(name)
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM inventory WHERE LOWER(name)=?", (norm,)
    ).fetchone()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing:
        new_qty = existing["quantity"] + quantity
        conn.execute(
            "UPDATE inventory SET quantity=? WHERE id=?",
            (new_qty, existing["id"])
        )
        item_id = existing["id"]
        item_name = existing["name"]
        item_price = existing["price"] if "price" in existing.keys() else price
        log.info("Restocked %s: +%.1f %s → %.1f total", norm, quantity, unit, new_qty)
    else:
        cur = conn.execute(
            "INSERT INTO inventory (name, quantity, unit, price) VALUES (?,?,?,?)",
            (norm, quantity, unit, price)
        )
        item_id = cur.lastrowid
        item_name = norm
        item_price = price
        log.info("New item %s: %.1f %s added", norm, quantity, unit)

    # Record transaction with item_name/price for trends
    conn.execute(
        "INSERT INTO transactions (item_id, item_name, type, quantity, price, timestamp) VALUES (?,?,?,?,?,?)",
        (item_id, item_name, "restock", quantity, item_price, ts)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return dict(row)


def sell_item(name: str, quantity: float) -> dict:
    """
    Reduce stock. Raises ValueError if item not found or insufficient stock.
    Returns updated row.
    """
    norm = normalize_name(name)
    conn = get_conn()
    existing = conn.execute(
        "SELECT * FROM inventory WHERE LOWER(name)=?", (norm,)
    ).fetchone()

    if not existing:
        conn.close()
        raise ValueError(f"Item '{name}' not found in inventory")

    if existing["quantity"] < quantity:
        conn.close()
        raise ValueError(
            f"Insufficient stock: only {existing['quantity']} {existing['unit']} of {name} available"
        )

    new_qty = existing["quantity"] - quantity
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE inventory SET quantity=? WHERE id=?", (new_qty, existing["id"])
    )
    # Record transaction with item_name/price for trends
    conn.execute(
        "INSERT INTO transactions (item_id, item_name, type, quantity, price, timestamp) VALUES (?,?,?,?,?,?)",
        (existing["id"], existing["name"], "sale", quantity, existing["price"] if "price" in existing.keys() else 0.0, ts)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM inventory WHERE id=?", (existing["id"],)).fetchone()
    conn.close()
    log.info("Sold %s: -%.1f %s → %.1f remaining", norm, quantity, existing["unit"], new_qty)
    return dict(row)


def run_safe_query(sql: str) -> list[dict]:
    """Execute a pre-validated SELECT query. Returns list of row dicts."""
    conn = get_conn()
    try:
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute_safe_sql(sql: str, params: tuple = ()) -> int:
    """Execute a pre-validated INSERT/UPDATE. Returns rowcount."""
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
