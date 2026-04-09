import sqlite3

def run_inventory_migrations(db_path: str):
    """Add new inventory fields and tables for expanded feature support."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Add new columns to inventory table (backwards compatible)
    for col, typedef in [
        ("unit",       "TEXT DEFAULT 'piece'"),
        ("category",   "TEXT DEFAULT 'general'"),
        ("expiry_date", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE inventory ADD COLUMN {col} {typedef}")
            print(f"✅ Added column {col} to inventory table")
        except sqlite3.OperationalError:
            # Column already exists in this DB, safe to ignore
            pass
    
    # Create price_history table
    c.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id    INTEGER REFERENCES inventory(id),
        item_name  TEXT,
        old_price  REAL,
        new_price  REAL,
        changed_by TEXT    DEFAULT 'system',
        changed_at TEXT    NOT NULL
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_price_item ON price_history(item_id)")
    print("✅ price_history table created/updated")
    
    # Create orders table (new dedicated structure)
    c.execute("""
    CREATE TABLE IF NOT EXISTS orders_new (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   TEXT    UNIQUE NOT NULL,
        customer_id TEXT,
        item_id    INTEGER REFERENCES inventory(id),
        item_name  TEXT,
        quantity   REAL    NOT NULL,
        price      REAL,
        order_date TEXT    NOT NULL,
        status     TEXT    DEFAULT 'pending' CHECK(status IN ('pending','confirmed','delivered','cancelled')),
        delivery_date TEXT,
        notes      TEXT
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders_new(customer_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders_new(status)")
    print("✅ orders table created")
    
    conn.commit()
    conn.close()


def run_customer_migrations(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Add missing columns to existing transactions table
    for col, typedef in [
        ("type",       "TEXT DEFAULT 'sale'"),
        ("item_id",    "INTEGER"),
        ("customer_id", "TEXT"),
        ("channel",     "TEXT DEFAULT 'walk-in'"),
        ("order_id",    "TEXT"),
        ("cost_price",  "REAL DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already exists

    # Ensure helpful indexes exist once item_id is present
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_txn_item ON transactions(item_id)")
    except sqlite3.OperationalError:
        # If item_id truly doesn't exist, skip creating the index
        pass

    c.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id       TEXT PRIMARY KEY,
        name              TEXT,
        phone             TEXT,
        locality          TEXT,
        credit_balance    REAL DEFAULT 0,
        first_visit       TEXT,
        last_visit        TEXT,
        total_lifetime_value REAL DEFAULT 0
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id        TEXT PRIMARY KEY,
        customer_id     TEXT REFERENCES customers(customer_id),
        order_date      TEXT,
        status          TEXT DEFAULT 'pending',
        delivery_slot   TEXT,
        is_subscription INTEGER DEFAULT 0,
        notes           TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS predicted_orders (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id     TEXT REFERENCES customers(customer_id),
        item_name       TEXT,
        predicted_qty   REAL,
        predicted_date  TEXT,
        confidence      REAL,
        fulfilled       INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS customer_segments (
        customer_id      TEXT PRIMARY KEY REFERENCES customers(customer_id),
        rfm_score        REAL,
        segment          TEXT,
        recency_days     INTEGER,
        frequency_count  INTEGER,
        monetary_total   REAL,
        ltv_score        REAL,
        churn_risk       REAL,
        updated_at       TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS basket_pairs (
        item_a               TEXT,
        item_b               TEXT,
        co_occurrence_count  INTEGER DEFAULT 1,
        lift_score           REAL,
        last_updated         TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (item_a, item_b)
    )""")

    conn.commit()
    conn.close()
    print("✅ Customer analytics tables created/updated.")