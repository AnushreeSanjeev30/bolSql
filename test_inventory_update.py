#!/usr/bin/env python3
from pipeline import process
from app.db.database import get_all_items

# Get initial state
items_before = get_all_items()
atta_before = next((item for item in items_before if item['name'].lower() == 'atta'), None)
bread_before = next((item for item in items_before if item['name'].lower() == 'bread'), None)

print("BEFORE:")
print(f"  Atta: {atta_before['quantity'] if atta_before else 'NOT FOUND'}")
print(f"  Bread: {bread_before['quantity'] if bread_before else 'NOT FOUND'}\n")

# Test ADD
print("Testing ADD: 'atta ke 50 piece add karo'")
result = process("atta ke 50 piece add karo", is_voice=False)
print(f"  Success: {result.success}")
print(f"  Intent: {result.intent}")
print(f"  Response: {result.response}\n")

# Test SELL
print("Testing SELL: 'bread 10 piece sell'")
result = process("bread 10 piece sell", is_voice=False)
print(f"  Success: {result.success}")
print(f"  Intent: {result.intent}")
print(f"  Response: {result.response}\n")

# Get final state
items_after = get_all_items()
atta_after = next((item for item in items_after if item['name'].lower() == 'atta'), None)
bread_after = next((item for item in items_after if item['name'].lower() == 'bread'), None)

print("AFTER:")
print(f"  Atta: {atta_after['quantity'] if atta_after else 'NOT FOUND'}")
print(f"  Bread: {bread_after['quantity'] if bread_after else 'NOT FOUND'}\n")

# Check if updated
if atta_after and atta_before:
    atta_change = atta_after['quantity'] - atta_before['quantity']
    print(f"  Atta change: {atta_change:+.1f} (expected: +50)")
    
if bread_after and bread_before:
    bread_change = bread_after['quantity'] - bread_before['quantity']
    print(f"  Bread change: {bread_change:+.1f} (expected: -10)")
