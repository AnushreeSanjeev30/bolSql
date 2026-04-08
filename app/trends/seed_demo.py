"""
Demo Data Seeder
Generates realistic Kirana transaction data for testing all 13 trends.

Run: python app/trends/seed_demo.py  (uses TRENDS_DB_PATH from config)
"""

import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import TRENDS_DB_PATH


import random
CUSTOMER_IDS = [f"C{str(i).zfill(3)}" for i in range(1, 16)]

customer_id = random.choice(CUSTOMER_IDS)
ITEMS = [
    ("Atta",         22, 18),   # name, sell_price, cost_price
    ("Chawal",       55, 42),
    ("Dal",          90, 70),
    ("Milk",         28, 22),
    ("Maggi",        14, 10),
    ("Bread",        40, 30),
    ("Butter",       55, 42),
    ("Chai Patti",   280, 210),
    ("Biscuit",      20, 14),
    ("Cold Drink",   40, 28),
    ("Ice Cream",    50, 35),
    ("Pickle",       60, 45),
    ("Sauce",        80, 58),
    ("Namak",        20, 14),
    ("Oil",          130, 100),
]

CUSTOMERS = [f"C{str(i).zfill(3)}" for i in range(1, 20)]

FESTIVAL_WINDOWS = {
    "diwali": ("2024-11-01", "2024-11-05"),
    "holi":   ("2024-03-24", "2024-03-26"),
}

SEASONAL_BOOST = {
    4: ["Cold Drink", "Ice Cream"],   # April (summer)
    5: ["Cold Drink", "Ice Cream"],
    6: ["Cold Drink", "Ice Cream"],
    7: ["Chai Patti", "Maggi"],       # July (monsoon)
    8: ["Chai Patti", "Maggi"],
    12: ["Chai Patti", "Namak"],      # December (winter)
    1:  ["Chai Patti"],
}

def seed(db_path: str | None = None, days_back: int = 180):
    if db_path is None:
        db_path = str(TRENDS_DB_PATH)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure tables exist (aligned with trends engine + core app expectations)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            quantity REAL DEFAULT 0,
            unit TEXT DEFAULT 'piece',
            price REAL DEFAULT 0,
            cost_price REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            item_name TEXT,
            type TEXT,
            quantity REAL,
            price REAL,
            timestamp DATETIME,
            customer_id TEXT
        )
    """)

    # Backward compat: add any missing columns if DB already existed
    cur.execute("PRAGMA table_info(inventory)")
    inv_cols = {r[1] for r in cur.fetchall()}
    if "unit" not in inv_cols:
        cur.execute("ALTER TABLE inventory ADD COLUMN unit TEXT DEFAULT 'piece'")
    if "price" not in inv_cols:
        cur.execute("ALTER TABLE inventory ADD COLUMN price REAL DEFAULT 0")

    cur.execute("PRAGMA table_info(transactions)")
    tx_cols = {r[1] for r in cur.fetchall()}
    if "timestamp" not in tx_cols and "sold_at" in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN timestamp DATETIME")
        cur.execute("UPDATE transactions SET timestamp = sold_at WHERE timestamp IS NULL")
    if "item_id" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN item_id INTEGER")
    if "type" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN type TEXT")
    if "item_name" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN item_name TEXT")
    if "price" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN price REAL DEFAULT 0")
    if "customer_id" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN customer_id TEXT")

    # Seed inventory
    for name, sell, cost in ITEMS:
        stock = random.randint(5, 200)
        cur.execute("""
            INSERT OR IGNORE INTO inventory(name, quantity, cost_price)
            VALUES (?, ?, ?)
        """, (name, stock, cost))

    # Build name → id map (after INSERT OR IGNORE)
    cur.execute("SELECT id, name FROM inventory")
    name_to_id = {row[1]: row[0] for row in cur.fetchall()}

    print(f"  ✅ Inventory seeded with {len(ITEMS)} items")

    # Seed transactions (180 days of history)
    now = datetime.now()
    tx_count = 0

    for day_offset in range(days_back, 0, -1):
        day = now - timedelta(days=day_offset)
        month = day.month

        # Peak hours: 9-11 AM and 6-8 PM
        rush_hours = list(range(9, 12)) + list(range(18, 21))
        slow_hours = list(range(7, 9)) + list(range(12, 18))
        all_hours = rush_hours * 3 + slow_hours

        # Number of transactions per day (weekend boost)
        base_tx = 40 if day.weekday() >= 5 else 25
        n_tx = random.randint(base_tx - 5, base_tx + 15)

        for _ in range(n_tx):
            hour = random.choice(all_hours)
            minute = random.randint(0, 59)
            ts = day.replace(hour=hour, minute=minute, second=random.randint(0, 59))

            # Seasonal boost: build weighted pool without mutating during iteration
            boosted = SEASONAL_BOOST.get(month, [])
            base_pool = ITEMS
            pool = list(base_pool)
            for name, sell, cost in base_pool:
                if name in boosted:
                    pool.extend([(name, sell, cost)] * 3)  # 4x weight

            item_name, sell_price, _ = random.choice(pool)
            item_id = name_to_id.get(item_name)
            qty = random.randint(1, 5)

            # Customer assignment (70% known customers)
            customer = random.choice(CUSTOMERS) if random.random() < 0.7 else None

            cur.execute("""
                INSERT INTO transactions(item_id, item_name, type, quantity, price, timestamp, customer_id)
                VALUES (?, ?, 'sale', ?, ?, ?, ?)
            """, (item_id, item_name, qty, sell_price, ts.strftime("%Y-%m-%d %H:%M:%S"), customer))
            tx_count += 1

        # Festival boost
        day_str = day.strftime("%Y-%m-%d")
        for fest, (start, end) in FESTIVAL_WINDOWS.items():
            if start <= day_str <= end:
                for _ in range(20):
                    item_name, sell_price, _ = random.choice(ITEMS)
                    item_id = name_to_id.get(item_name)
                    qty = random.randint(2, 10)
                    cur.execute("""
                        INSERT INTO transactions(item_id, item_name, type, quantity, price, timestamp, customer_id)
                        VALUES (?, ?, 'sale', ?, ?, ?, ?)
                    """, (item_id, item_name, qty, sell_price,
                          day.strftime("%Y-%m-%d %H:%M:%S"), random.choice(CUSTOMERS)))
                    tx_count += 1

    conn.commit()
    conn.close()
    print(f"  ✅ {tx_count} transactions seeded across {days_back} days")
    print("  ✅ Demo data ready! All 13 trends can now be tested.")


if __name__ == "__main__":
    seed()
