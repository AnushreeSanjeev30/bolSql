#!/usr/bin/env python3
"""Add price history for testing rollback, and sample orders"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from config import DB_PATH

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Add some price history records (simulating previous price changes)
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

# Get atta ID
atta = c.execute("SELECT id FROM inventory WHERE LOWER(name)='atta'").fetchone()
if atta:
    # Simulate price changes
    c.execute(
        """INSERT INTO price_history (item_id, item_name, old_price, new_price, changed_by, changed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (atta['id'], 'atta', 20.0, 22.0, 'shopkeeper', yesterday)
    )
    print(f"✓ Added price history: atta ₹20 → ₹22")

# Add some orders
dal = c.execute("SELECT id FROM inventory WHERE LOWER(name)='dal'").fetchone()
chawal = c.execute("SELECT id FROM inventory WHERE LOWER(name)='chawal'").fetchone()

if dal:
    c.execute(
        """INSERT INTO orders 
           (order_id, customer_id, item_id, item_name, quantity, price, order_date, status, delivery_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ORD-001", "CUST001", dal['id'], "dal", 5.0, 90.0, now, "pending", "2026-04-10")
    )
    print(f"✓ Created order ORD-001: dal 5kg pending")

if chawal:
    c.execute(
        """INSERT INTO orders 
           (order_id, customer_id, item_id, item_name, quantity, price, order_date, status, delivery_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ORD-002", "CUST002", chawal['id'], "chawal", 10.0, 55.0, now, "confirmed", "2026-04-10")
    )
    print(f"✓ Created order ORD-002: chawal 10kg confirmed")

if dal:
    c.execute(
        """INSERT INTO orders 
           (order_id, customer_id, item_id, item_name, quantity, price, order_date, status, delivery_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("ORD-003", "CUST001", dal['id'], "dal", 3.0, 90.0, now, "pending", "2026-04-11")
    )
    print(f"✓ Created order ORD-003: dal 3kg pending")

conn.commit()

# Show price history
print("\n💰 Price History:")
rows = c.execute(
    "SELECT item_name, old_price, new_price, changed_by, changed_at FROM price_history ORDER BY changed_at DESC"
).fetchall()
for row in rows:
    print(f"  {row['item_name']:12} | ₹{row['old_price']:6.1f} → ₹{row['new_price']:6.1f} | by {row['changed_by']:12} | {row['changed_at']}")

# Show orders
print("\n📦 Orders:")
rows = c.execute(
    "SELECT order_id, item_name, quantity, price, status, order_date, delivery_date FROM orders ORDER BY order_date DESC"
).fetchall()
for row in rows:
    print(f"  {row['order_id']:12} | {row['item_name']:12} {row['quantity']:5.1f}kg | ₹{row['price']:6.1f} | {row['status']:10} | {row['order_date'][:10]} → {row['delivery_date']}")

conn.close()
print("\n✅ Price history and orders added!")
