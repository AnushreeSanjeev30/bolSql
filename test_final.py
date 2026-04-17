#!/usr/bin/env python3
"""Test final percentage price update with live database."""

from app.db.database import init_db, get_item, update_item_price, upsert_item
from pipeline import process

# Initialize DB with seed data
init_db()

# Ensure dal exists with a price
try:
    dal = get_item("dal")
    if dal:
        print(f"Found dal: {dal}")
        if dal['price'] == 0:
            update_item_price("dal", 100)
            dal = get_item("dal")
            print(f"Updated dal price: {dal['price']}")
    else:
        print("Dal not found, creating...")
        upsert_item("dal", 1, "kg", price=100)
        dal = get_item("dal")
        print(f"Created dal: {dal}")
except Exception as e:
    print(f"Error: {e}")
    upsert_item("dal", 1, "kg", price=100)

print("\n" + "="*60)
print("Testing: dal ka price 10% inc karo")
print("="*60 + "\n")

result = process("dal ka price 10% inc karo", is_voice=False, language="hinglish")
print(f"Success: {result.success}")
print(f"Response: {result.response}")
print(f"Intent: {result.intent}")

if result.success:
    dal = get_item("dal")
    print(f"Updated price: ₹{dal['price']:.2f}")
else:
    print(f"Error: {result.error}")
