#!/usr/bin/env python3
"""Final verification: Hindi percentage price update."""

from app.db.database import init_db, get_item, update_item_price, upsert_item
from pipeline import process
import os

# Clean start
if os.path.exists('kirana_trends.db'):
    os.remove('kirana_trends.db')

init_db()

# Setup
upsert_item("dal", 1, "kg", price=0)
update_item_price("dal", 100)

print("="*70)
print("FINAL VERIFICATION: Hindi percentage price update")
print("="*70)
print()

# The original command from the user
hindi_command = "दालों की कीमत में 10% की वृद्धि करें"
print(f"User command (Hindi): {hindi_command}")
print(f"English meaning: Increase dal price by 10%")
print()

dal_before = get_item("dal")
print(f"Before: ₹{dal_before['price']:.2f}")

result = process(hindi_command, is_voice=False, language="hinglish")
print()
print(f"AI Response: {result.response}")
print()

dal_after = get_item("dal")
print(f"After: ₹{dal_after['price']:.2f}")
print(f"Expected: ₹110.00 (10% of ₹100)")
print()

if abs(dal_after['price'] - 110) < 0.01:
    print("✅ SUCCESS - Hindi percentage price update works!")
else:
    print(f"❌ FAILED - Expected ₹110, got ₹{dal_after['price']:.2f}")
