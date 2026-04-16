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
from .migrations import run_inventory_migrations, run_customer_migrations

log = get_logger("db")


# Cross-language item synonym groups (all variants map to one canonical name).
ITEM_SYNONYM_GROUPS = {
    "atta": {"atta", "aata", "aatta", "wheat flour", "flour", "maavu"},
    "chawal": {"chawal", "chaawal", "chaval", "rice", "arisi"},
    "dal": {"dal", "daal", "lentil", "lentils", "paruppu"},
    "tel": {"tel", "teel", "oil", "cooking oil", "refined oil", "ennai", "ennei", "enai", "nallennai"},
    "chini": {"chini", "cheeni", "sugar", "shakkar"},
    "namak": {"namak", "salt", "uppu"},
    "doodh": {"doodh", "dud", "dhudh", "milk", "paal"},
    "biscuit": {"biscuit", "biscuits", "biskut", "biskit", "biskoot", "biscut"},
    "sabun": {"sabun", "soap"},
    "chai": {"chai", "tea", "tea leaves", "chai patti"},
    "haldi": {"haldi", "turmeric"},
    "mirchi": {"mirchi", "mirch", "chilli", "chili", "red chilli", "lal mirchi"},
    "aloo": {"aloo", "potato", "potatoes"},
    "apple": {"apple", "apples", "seb"},
    "mango": {"mango", "mangos", "mongos", "aam"},
}

ITEM_ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in ITEM_SYNONYM_GROUPS.items()
    for alias in aliases
}


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
            cost_price REAL,
            category   TEXT    DEFAULT 'general',
            expiry_date TEXT
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

        CREATE TABLE IF NOT EXISTS price_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    INTEGER REFERENCES inventory(id),
            item_name  TEXT,
            old_price  REAL,
            new_price  REAL,
            changed_by TEXT    DEFAULT 'system',
            changed_at TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id   TEXT    UNIQUE NOT NULL,
            customer_id TEXT    REFERENCES customers(customer_id),
            item_id    INTEGER REFERENCES inventory(id),
            item_name  TEXT,
            quantity   REAL    NOT NULL,
            price      REAL,
            order_date TEXT    NOT NULL,
            status     TEXT    DEFAULT 'pending' CHECK(status IN ('pending','confirmed','delivered','cancelled')),
            delivery_date TEXT,
            notes      TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_txn_item ON transactions(item_id);
        CREATE INDEX IF NOT EXISTS idx_txn_time ON transactions(timestamp);
        CREATE INDEX IF NOT EXISTS idx_price_item ON price_history(item_id);
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
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
    
    # Run migrations for new fields/tables
    log.info("Running database migrations")
    run_inventory_migrations(str(DB_PATH))
    run_customer_migrations(str(DB_PATH))

    # Consolidate legacy alias rows (e.g., arisi/chawal/rice -> one row).
    conn = get_conn()
    merged = _merge_inventory_alias_duplicates(conn)
    if merged:
        log.info("Merged %d alias-duplicate inventory group(s)", merged)
    conn.commit()
    conn.close()
    
    log.info("Database ready")


def normalize_name(name: str) -> str:
    """Lowercase, strip extra spaces — for consistent item lookup."""
    return re.sub(r"\s+", " ", name.strip().lower())


def canonicalize_name(name: str) -> str:
    """Map aliases like rice/chawal/arisi to one canonical inventory name."""
    norm = normalize_name(name)
    return ITEM_ALIAS_TO_CANONICAL.get(norm, norm)


def _name_candidates(name: str) -> list[str]:
    """Return all known aliases for the item's canonical family."""
    norm = normalize_name(name)
    canonical = ITEM_ALIAS_TO_CANONICAL.get(norm)
    if not canonical:
        return [norm]
    aliases = ITEM_SYNONYM_GROUPS.get(canonical, {canonical})
    # Keep stable ordering for deterministic SQL params/logging.
    return sorted({normalize_name(a) for a in aliases} | {canonical})


def _find_inventory_row(conn: sqlite3.Connection, name: str, allow_like: bool = True):
    """Find an inventory row by exact alias family match, with optional LIKE fallback."""
    norm = normalize_name(name)
    canonical = canonicalize_name(name)
    candidates = _name_candidates(name)

    placeholders = ",".join(["?"] * len(candidates))
    row = conn.execute(
        f"""
        SELECT * FROM inventory
        WHERE LOWER(name) IN ({placeholders})
        ORDER BY
            CASE
                WHEN LOWER(name) = ? THEN 0
                ELSE 1
            END,
            id ASC
        LIMIT 1
        """,
        (*candidates, canonical),
    ).fetchone()

    if not row and allow_like:
        row = conn.execute(
            "SELECT * FROM inventory WHERE LOWER(name) LIKE ? ORDER BY id ASC LIMIT 1",
            (f"%{norm}%",),
        ).fetchone()

    return row


def _merge_inventory_alias_duplicates(conn: sqlite3.Connection) -> int:
    """Merge legacy duplicate rows that belong to the same synonym family."""
    merged_groups = 0

    for canonical in ITEM_SYNONYM_GROUPS.keys():
        candidates = sorted({normalize_name(a) for a in ITEM_SYNONYM_GROUPS[canonical]} | {canonical})
        placeholders = ",".join(["?"] * len(candidates))

        rows = conn.execute(
            f"""
            SELECT * FROM inventory
            WHERE LOWER(name) IN ({placeholders})
            ORDER BY
                CASE WHEN LOWER(name) = ? THEN 0 ELSE 1 END,
                id ASC
            """,
            (*candidates, canonical),
        ).fetchall()

        if len(rows) <= 1:
            continue

        keeper = rows[0]
        dupes = rows[1:]

        merged_qty = sum(float(r["quantity"] or 0.0) for r in rows)
        merged_unit = keeper["unit"] or next((r["unit"] for r in rows if r["unit"]), "piece")

        merged_price = float(keeper["price"] or 0.0)
        if merged_price == 0.0:
            for r in rows:
                p = float(r["price"] or 0.0)
                if p > 0:
                    merged_price = p
                    break

        conn.execute(
            "UPDATE inventory SET name=?, quantity=?, unit=?, price=? WHERE id=?",
            (canonical, merged_qty, merged_unit, merged_price, keeper["id"]),
        )

        for d in dupes:
            conn.execute(
                "UPDATE transactions SET item_id=?, item_name=? WHERE item_id=?",
                (keeper["id"], canonical, d["id"]),
            )
            conn.execute(
                "UPDATE price_history SET item_id=?, item_name=? WHERE item_id=?",
                (keeper["id"], canonical, d["id"]),
            )
            conn.execute(
                "UPDATE orders SET item_id=?, item_name=? WHERE item_id=?",
                (keeper["id"], canonical, d["id"]),
            )
            conn.execute("DELETE FROM inventory WHERE id=?", (d["id"],))

        merged_groups += 1

    return merged_groups


def get_item(name: str) -> Optional[dict]:
    """Fuzzy-ish item lookup: exact first, then LIKE."""
    conn = get_conn()
    row = _find_inventory_row(conn, name, allow_like=True)
    conn.close()
    return dict(row) if row else None


def get_all_items() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM inventory ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_customers(limit: int = 100) -> list[dict]:
    """Return a list of customers ordered by last_visit (most recent first).

    Limit the result size to avoid flooding the UI for large shops.
    """
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM customers ORDER BY last_visit DESC, customer_id LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def upsert_item(name: str, quantity: float, unit: str, price: float = 0.0) -> dict:
    """
    Add item if not exists, else add quantity to existing stock.
    Returns updated row.
    """
    norm = canonicalize_name(name)
    conn = get_conn()
    existing = _find_inventory_row(conn, name, allow_like=False)

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
    norm = canonicalize_name(name)
    conn = get_conn()
    existing = _find_inventory_row(conn, name, allow_like=False)

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
    return dict(row)


def correct_stock(name: str, quantity: float, unit: Optional[str] = None) -> dict:
    """Set absolute stock level for an item (manual correction).

    - If the item exists, overwrite its quantity (and optionally unit).
    - If it doesn't exist, create it with the given quantity and unit.
    This does NOT insert a sale/restock transaction to avoid skewing
    demand analytics; it is meant for counting/correction only.
    """
    norm = canonicalize_name(name)
    conn = get_conn()
    existing = _find_inventory_row(conn, name, allow_like=False)

    chosen_unit = unit
    if existing and not chosen_unit:
        # Preserve existing unit if caller didn't specify one
        chosen_unit = existing.get("unit") if isinstance(existing, dict) else existing["unit"]
    if not chosen_unit:
        chosen_unit = "piece"

    if existing:
        conn.execute(
            "UPDATE inventory SET quantity=?, unit=? WHERE id=?",
            (quantity, chosen_unit, existing["id"]),
        )
        item_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO inventory (name, quantity, unit, price) VALUES (?,?,?,?)",
            (norm, quantity, chosen_unit, 0.0),
        )
        item_id = cur.lastrowid

    conn.commit()
    row = conn.execute("SELECT * FROM inventory WHERE id=?", (item_id,)).fetchone()
    conn.close()
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

def update_item_price(name: str, new_price: float, reason: str = "manual") -> dict:
    """Update item price and log to price_history."""
    norm = canonicalize_name(name)
    conn = get_conn()
    
    # Get current price
    item = _find_inventory_row(conn, name, allow_like=False)
    
    if not item:
        conn.close()
        raise ValueError(f"Item '{name}' not found")
    
    old_price = item["price"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update price
    conn.execute(
        "UPDATE inventory SET price=? WHERE id=?",
        (new_price, item["id"])
    )
    
    # Log to price_history
    conn.execute(
        "INSERT INTO price_history (item_id, item_name, old_price, new_price, changed_by, changed_at) VALUES (?,?,?,?,?,?)",
        (item["id"], item["name"], old_price, new_price, reason, ts)
    )
    
    conn.commit()
    updated = conn.execute("SELECT * FROM inventory WHERE id=?", (item["id"],)).fetchone()
    conn.close()
    
    log.info("Price updated for %s: %.1f → %.1f", norm, old_price, new_price)
    return dict(updated)


def rollback_item_price(name: str) -> dict:
    """Rollback item price to previous value from price_history."""
    norm = canonicalize_name(name)
    conn = get_conn()
    
    item = _find_inventory_row(conn, name, allow_like=False)
    
    if not item:
        conn.close()
        raise ValueError(f"Item '{name}' not found")
    
    # Get most recent price change
    prev_price = conn.execute(
        "SELECT old_price FROM price_history WHERE item_id=? ORDER BY changed_at DESC LIMIT 1",
        (item["id"],)
    ).fetchone()
    
    if not prev_price:
        conn.close()
        raise ValueError(f"No price history found for '{name}'")
    
    old_price = item["price"]
    new_price = prev_price["old_price"]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update price to previous
    conn.execute(
        "UPDATE inventory SET price=? WHERE id=?",
        (new_price, item["id"])
    )
    
    # Log the rollback
    conn.execute(
        "INSERT INTO price_history (item_id, item_name, old_price, new_price, changed_by, changed_at) VALUES (?,?,?,?,?,?)",
        (item["id"], item["name"], old_price, new_price, "rollback", ts)
    )
    
    conn.commit()
    updated = conn.execute("SELECT * FROM inventory WHERE id=?", (item["id"],)).fetchone()
    conn.close()
    
    log.info("Price rolled back for %s: %.1f → %.1f", norm, old_price, new_price)
    return dict(updated)


def rollback_last_price_change() -> dict:
    """Rollback the most recent price change across all items.

    Looks at price_history ordered by changed_at and reverts the latest
    change by setting the item's price back to that row's old_price.
    """
    conn = get_conn()

    # Get the most recent price change event
    last_change = conn.execute(
        "SELECT * FROM price_history ORDER BY changed_at DESC LIMIT 1"
    ).fetchone()

    if not last_change:
        conn.close()
        raise ValueError("Pehle se koi price change nahi hua hai, toh undo kuch nahi hai")

    item_id = last_change["item_id"]

    item = conn.execute(
        "SELECT * FROM inventory WHERE id=?",
        (item_id,),
    ).fetchone()

    if not item:
        conn.close()
        raise ValueError("Last price change ka item inventory mein nahi mila")

    old_price = float(item["price"] or 0.0)
    new_price = float(last_change["old_price"] or 0.0)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Apply rollback to inventory
    conn.execute(
        "UPDATE inventory SET price=? WHERE id=?",
        (new_price, item_id),
    )

    # Log the rollback event as another price_history entry
    conn.execute(
        "INSERT INTO price_history (item_id, item_name, old_price, new_price, changed_by, changed_at) VALUES (?,?,?,?,?,?)",
        (item_id, item["name"], old_price, new_price, "rollback", ts),
    )

    conn.commit()
    updated = conn.execute(
        "SELECT * FROM inventory WHERE id=?",
        (item_id,),
    ).fetchone()
    conn.close()

    log.info(
        "Global price rollback for %s: %.1f → %.1f",
        item["name"],
        old_price,
        new_price,
    )
    return dict(updated)


def add_order(customer_id: str, item_id: int, quantity: float, price: float, delivery_date: str = None) -> dict:
    """Add new order to orders table."""
    conn = get_conn()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_id = f"ORD-{ts.replace(' ', '-').replace(':', '')}"
    
    # Get item name
    item = conn.execute("SELECT name FROM inventory WHERE id=?", (item_id,)).fetchone()
    if not item:
        conn.close()
        raise ValueError(f"Item with id {item_id} not found")
    
    conn.execute(
        """INSERT INTO orders 
           (order_id, customer_id, item_id, item_name, quantity, price, order_date, status, delivery_date) 
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (order_id, customer_id, item_id, item["name"], quantity, price, ts, delivery_date)
    )
    
    conn.commit()
    order = conn.execute(
        "SELECT * FROM orders WHERE order_id=?", (order_id,)
    ).fetchone()
    conn.close()
    
    log.info("Order created: %s for %s", order_id, item["name"])
    return dict(order)


def get_orders_by_status(status: str = "pending", customer_id: str = None) -> list[dict]:
    """Get orders filtered by status and optionally by customer."""
    conn = get_conn()
    
    if customer_id:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status=? AND customer_id=? ORDER BY order_date DESC",
            (status, customer_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status=? ORDER BY order_date DESC",
            (status,)
        ).fetchall()
    
    conn.close()
    return [dict(r) for r in rows]


def get_items_by_expiry(days_until_expiry: int = 7) -> list[dict]:
    """Get items expiring within specified days."""
    conn = get_conn()
    rows = conn.execute(
        """SELECT * FROM inventory 
           WHERE expiry_date IS NOT NULL 
           AND datetime(expiry_date) <= datetime('now', '+' || ? || ' days')
           ORDER BY expiry_date ASC""",
        (days_until_expiry,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_item_expiry(name: str, expiry_date: str) -> dict:
    """Set expiry date for an item (format: YYYY-MM-DD)."""
    norm = canonicalize_name(name)
    conn = get_conn()

    item = _find_inventory_row(conn, name, allow_like=False)
    
    if not item:
        conn.close()
        raise ValueError(f"Item '{name}' not found")
    
    conn.execute(
        "UPDATE inventory SET expiry_date=? WHERE id=?",
        (expiry_date, item["id"])
    )
    
    conn.commit()
    updated = conn.execute("SELECT * FROM inventory WHERE id=?", (item["id"],)).fetchone()
    conn.close()
    
    log.info("Expiry date set for %s: %s", norm, expiry_date)
    return dict(updated)


def get_today_orders(include_all_status: bool = True) -> list[dict]:
    """Get today's orders.

    By default returns all statuses for today's date, newest first.
    """
    conn = get_conn()
    try:
        if include_all_status:
            rows = conn.execute(
                """
                SELECT * FROM orders
                WHERE DATE(order_date) = DATE('now')
                ORDER BY order_date DESC
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM orders
                WHERE DATE(order_date) = DATE('now') AND status = 'pending'
                ORDER BY order_date DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_today_sales_summary() -> list[dict]:
    """Return aggregated sales for today, grouped by item.

    Each row contains: name, quantity, unit, and total_amount (quantity * price).
    """
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT
                COALESCE(t.item_name, i.name) AS name,
                SUM(t.quantity) AS quantity,
                COALESCE(i.unit, 'piece') AS unit,
                SUM(t.quantity * COALESCE(t.price, 0)) AS total_amount
            FROM transactions t
            LEFT JOIN inventory i ON i.id = t.item_id
            WHERE t.type = 'sale' AND DATE(t.timestamp) = DATE('now')
            GROUP BY COALESCE(t.item_name, i.name), COALESCE(i.unit, 'piece')
            ORDER BY quantity DESC, name
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()