#!/usr/bin/env python3
import sys
from app.trends.engine import AnalyticsEngine
from datetime import datetime, timedelta
import sqlite3

db_path = "./kirana_trends.db"

# Test 1: Check raw data
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT item_name, timestamp FROM transactions ORDER BY timestamp").fetchall()
print(f"Total transactions in DB: {len(rows)}\n")

# Build baskets manually to debug
baskets = []
current_basket = []
last_time = None
window = timedelta(minutes=5)

for item, ts_str in rows:
    ts_str_normalized = ts_str[:19].replace('T', ' ')
    ts = datetime.strptime(ts_str_normalized, "%Y-%m-%d %H:%M:%S")
    if last_time is None or (ts - last_time) > window:
        if current_basket:
            baskets.append(current_basket)
        current_basket = [item]
    else:
        current_basket.append(item)
    last_time = ts

if current_basket:
    baskets.append(current_basket)

print(f"Baskets created: {len(baskets)}")
print("Multi-item baskets:")
multi_baskets = [b for b in baskets if len(b) > 1]
for i, basket in enumerate(multi_baskets[:10]):
    print(f"  Basket {i}: {basket}")

conn.close()

# Test 2: Call market_basket function
print("\n" + "="*70)
print("Calling market_basket() function:")
engine = AnalyticsEngine(db_path)
result = engine.market_basket(min_support=1, top_n=20)
print(f"Results (min_support=1): {len(result)} pairs\n")
if result:
    for r in result[:5]:
        print(f"  {r}")
else:
    print("  (no results)")
