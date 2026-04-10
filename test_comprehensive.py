#!/usr/bin/env python3
"""Final comprehensive test of percentage price updates in English and Hindi."""

import os
import sqlite3
from app.db.database import init_db, get_item, update_item_price, upsert_item
from pipeline import process

# Clean start
if os.path.exists('kirana_trends.db'):
    os.remove('kirana_trends.db')

# Initialize DB
init_db()

# Set up test data
test_items = [
    ("dal", 100),
    ("chawal", 50),
    ("atta", 40),
    ("tel", 200),
]

print("Setting up test items...\n")
for name, price in test_items:
    upsert_item(name, 1, "kg", price=0)
    update_item_price(name, price)

# Test cases: (command, language, expected_item, initial_price, expected_new_price)
test_cases = [
    ("dal ka price 10% inc karo", "hinglish", "dal", 100, 110),
    ("दालों की कीमत में 10% की वृद्धि करें", "hinglish", "dal", 110, 121),  # 10% of 110
    ("chawal ka price 5% badha do", "hinglish", "chawal", 50, 52.5),
    ("चावल की कीमत में 5% की बढ़ोतरी करें", "hinglish", "chawal", 52.5, 55.125),
]

print("=" * 70)
print("Testing Percentage-Based Price Updates (English & Hindi)")
print("=" * 70)
print()

for command, language, item_name, expected_initial, expected_final in test_cases:
    try:
        item = get_item(item_name)
        actual_initial = item['price']
        
        print(f"Command: {command}")
        print(f"Language: {language}")
        
        result = process(command, is_voice=False, language=language)
        
        updated = get_item(item_name)
        actual_final = updated['price']
        
        print(f"Price: ₹{actual_initial:.2f} → ₹{actual_final:.2f}")
        print(f"Response: {result.response}")
        
        # Validate
        if abs(actual_final - expected_final) < 0.01:
            print("✓ PASSED")
        else:
            print(f"✗ FAILED - Expected ₹{expected_final:.2f}, got ₹{actual_final:.2f}")
        
        print()
    except Exception as e:
        print(f"✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()

print("=" * 70)
