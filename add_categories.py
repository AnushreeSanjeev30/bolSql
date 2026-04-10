#!/usr/bin/env python3
"""Add categories and expiry dates to existing inventory"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from config import DB_PATH

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Define categories for items
item_categories = {
    "atta": "grains",
    "chawal": "grains",
    "dal": "pulses",
    "tel": "oils",
    "chini": "sweeteners",
    "namak": "seasonings",
    "doodh": "dairy",
    "biscuit": "snacks",
    "sabun": "toiletries",
    "chai": "beverages",
    "mirchi": "spices",
    "haldi": "spices",
    "aloo": "vegetables",
    "apple": "fruits",
    "mango": "fruits",
}

# Set expiry dates (some items 30 days out, some 60)
future_30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
future_60 = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")

item_expiry = {
    "doodh": future_30,  # Milk expires soon
    "biscuit": future_60,  # Biscuits last longer
    "chai": future_60,
    "apple": future_30,  # Fresh fruit
    "mango": future_30,
    "aloo": future_60,
}

# Update items with categories
for item, category in item_categories.items():
    c.execute(
        "UPDATE inventory SET category=? WHERE LOWER(name)=?",
        (category, item)
    )
    print(f"✓ {item}: category={category}")

# Update items with expiry dates
for item, expiry in item_expiry.items():
    c.execute(
        "UPDATE inventory SET expiry_date=? WHERE LOWER(name)=?",
        (expiry, item)
    )
    print(f"✓ {item}: expiry_date={expiry}")

conn.commit()

# Show all items with new fields
print("\n📋 Inventory with new fields:")
rows = c.execute("SELECT name, quantity, unit, price, category, expiry_date FROM inventory ORDER BY name").fetchall()
for row in rows:
    print(f"  {row['name']:12} | {row['quantity']:5.1f} {row['unit']:6} | ₹{row['price']:6.1f} | {row['category']:12} | {row['expiry_date'] or 'N/A'}")

conn.close()
print("\nCategories and expiry dates added!")
