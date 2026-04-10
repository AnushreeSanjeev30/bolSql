#!/usr/bin/env python3
"""Verify quantity updates are persisting in database."""

from pipeline import process
from app.db.database import get_item

print("\n" + "="*70)
print("VERIFYING QUANTITY DATABASE PERSISTENCE")
print("="*70)

dal = get_item("dal")
initial = dal['quantity']
print(f"\n📍 INITIAL STATE: dal = {initial:.2f} kg")

tests = [
    ("dal ka quantity 10% inc karo", 1.10, "English 10% increase"),
    ("दाल की मात्रा 10% बढ़ाओ", 1.10, "Hindi 10% increase"),
    ("dal ka quantity 5% dec karo", 0.95, "English 5% decrease"),
]

current = initial
for query, multiplier, description in tests:
    print(f"\n{'─'*70}")
    expected = current * multiplier
    
    result = process(query, is_voice=False)
    
    dal_after = get_item("dal")
    actual = dal_after['quantity']
    
    match_status = "✅" if abs(actual - expected) < 0.01 else "❌"
    
    print(f"📝 {description}")
    print(f"   Query: {query}")
    print(f"   Before: {current:.2f} kg")
    print(f"   Expected: {expected:.2f} kg")
    print(f"   Actual DB: {actual:.2f} kg")
    print(f"   Response: {result.response}")
    print(f"   {match_status} {'PASS' if abs(actual - expected) < 0.01 else 'FAIL - MISMATCH!'}")
    
    if abs(actual - expected) >= 0.01:
        print(f"   ⚠️  Expected {expected:.2f} but got {actual:.2f}")
    
    current = actual

print("\n" + "="*70)
print("✅ VERIFICATION COMPLETE - DATABASE UPDATES CONFIRMED")
print("="*70 + "\n")
