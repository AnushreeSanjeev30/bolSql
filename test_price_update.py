#!/usr/bin/env python3
"""Test script for percentage price updates."""

from app.db.database import init_db, get_item, update_item_price, upsert_item
from pipeline import process

# Initialize DB
init_db()

# Test cases: (command, description, item_name, initial_price, expected_price)
test_cases = [
    ("dal ka price 10% inc karo", "Increase by 10%", "dal", 100, 110),
    ("chawal ka price 5% badha do", "Hindi: Increase by 5%", "chawal", 50, 52.5),
    ("atta ka price 20% dec karo", "Decrease by 20%", "atta", 40, 32),
    ("tel ka price 15% decrease karo", "Decrease by 15%", "tel", 200, 170),
]

# Set initial prices for items
print("Setting up test items...")
for command, description, item_name, initial_price, expected_price in test_cases:
    upsert_item(item_name, 1, "kg", price=0)
    update_item_price(item_name, initial_price)

print("=" * 70)
print("Testing percentage-based price updates")
print("=" * 70)
print()

for command, description, item_name, initial_price, expected_price in test_cases:
    try:
        print(f"Test: {description}")
        print(f"Command: '{command}'")
        
        result = process(command, is_voice=False, language="hinglish")
        
        updated = get_item(item_name)
        updated_price = updated['price'] if updated else 0
        
        print(f"Initial: ₹{initial_price:.2f} → Updated: ₹{updated_price:.2f} (Expected: ₹{expected_price:.2f})")
        print(f"Response: {result.response}")
        print(f"Success: {result.success}")
        
        # Validate
        if abs(updated_price - expected_price) < 0.01:
            print("✓ PASSED")
        else:
            print(f"✗ FAILED - Got ₹{updated_price:.2f}, expected ₹{expected_price:.2f}")
        
        print()
    except Exception as e:
        print(f"✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()

print("=" * 70)
