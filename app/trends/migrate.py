"""
DB Migration for VoiceSQL Trends Support
Run once: python app/trends/migrate.py

Adds:
  - transactions.customer_id
  - transactions.sold_at  (if using created_at instead)
  - inventory.cost_price
"""

import sqlite3
import sys


def migrate(db_path: str = "kirana.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print(f"🔧 Running migration on {db_path}...")

    # ── transactions table ──────────────────────────────────────────
    cur.execute("PRAGMA table_info(transactions)")
    tx_cols = {r[1] for r in cur.fetchall()}

    if "customer_id" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN customer_id TEXT DEFAULT NULL")
        print("  ✅ transactions.customer_id added")

    if "sold_at" not in tx_cols:
        if "created_at" in tx_cols:
            # Rename alias via view (SQLite doesn't support column rename in old versions)
            print("  ℹ️  'created_at' found — VoiceSQL trends will use 'created_at' as 'sold_at'")
            print("      Please set SOLD_AT_COLUMN=created_at in your .env")
        else:
            cur.execute("""
                ALTER TABLE transactions 
                ADD COLUMN sold_at DATETIME DEFAULT (datetime('now'))
            """)
            print("  ✅ transactions.sold_at added")

    if "price" not in tx_cols:
        cur.execute("ALTER TABLE transactions ADD COLUMN price REAL DEFAULT 0.0")
        print("  ✅ transactions.price added")

    # ── inventory table ──────────────────────────────────────────────
    cur.execute("PRAGMA table_info(inventory)")
    inv_cols = {r[1] for r in cur.fetchall()}

    if "cost_price" not in inv_cols:
        cur.execute("ALTER TABLE inventory ADD COLUMN cost_price REAL DEFAULT NULL")
        print("  ✅ inventory.cost_price added (NULL = will default to 70% of selling price)")

    # ── Create indexes for trend query performance ───────────────────
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tx_sold_at 
        ON transactions(sold_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tx_item_sold 
        ON transactions(item_name, sold_at)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_tx_customer 
        ON transactions(customer_id)
    """)
    print("  ✅ Performance indexes created")

    conn.commit()
    conn.close()
    print("\n✅ Migration complete! Trends module is ready.")


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "kirana.db"
    migrate(db)
