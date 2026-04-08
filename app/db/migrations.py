import sqlite3

def run_customer_migrations(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Add missing columns to existing transactions table
    for col, typedef in [
        ("customer_id", "TEXT"),
        ("channel",     "TEXT DEFAULT 'walk-in'"),
        ("order_id",    "TEXT"),
        ("cost_price",  "REAL DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typedef}")
        except sqlite3.OperationalError:
            pass  # column already exists

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