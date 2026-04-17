#!/usr/bin/env python3
"""Test QUANTITY intent for percentage-based quantity updates."""

from pipeline import process
from app.db.database import get_item

print("=" * 70)
print("Testing QUANTITY Intent - Percentage-Based Updates")
print("=" * 70)

# Get initial state
dal_before = get_item("dal")
print(f"\n📦 INITIAL STATE:")
print(f"   Dal quantity: {dal_before['quantity']} {dal_before['unit']}")

# Test 1: Increase dal quantity by 10%
print(f"\n🔄 TEST 1: 'dal ka quantity 10% inc karo'")
result1 = process("dal ka quantity 10% inc karo", is_voice=False)
print(f"   Intent: {result1.intent}")
print(f"   Success: {result1.success}")
print(f"   Response: {result1.response}")

dal_after = get_item("dal")
print(f"   New quantity: {dal_after['quantity']} {dal_after['unit']}")
if dal_before and dal_after:
    qty_change = dal_after['quantity'] - dal_before['quantity']
    expected_change = dal_before['quantity'] * 0.10
    print(f"   Change: {qty_change:+.2f} {dal_after['unit']} (expected: {expected_change:+.2f})")
    print(f"   ✅ PASS" if abs(qty_change - expected_change) < 0.01 else f"   ❌ FAIL")

# Test 2: Test with chawal
print(f"\n🔄 TEST 2: 'chawal ka quantity 5% badha do'")
chawal_before = get_item("chawal")
if chawal_before:
    print(f"   Initial quantity: {chawal_before['quantity']}")
    result2 = process("chawal ka quantity 5% badha do", is_voice=False)
    print(f"   Intent: {result2.intent}")
    print(f"   Success: {result2.success}")
    print(f"   Response: {result2.response}")
    chawal_after = get_item("chawal")
    qty_change = chawal_after['quantity'] - chawal_before['quantity']
    expected_change = chawal_before['quantity'] * 0.05
    print(f"   Change: {qty_change:+.2f} (expected: {expected_change:+.2f})")
    print(f"   ✅ PASS" if abs(qty_change - expected_change) < 0.01 else f"   ❌ FAIL")
else:
    print(f"   ❌ Chawal not found in inventory")

# Test 3: Test decrease (kam kar do)
print(f"\n🔄 TEST 3: 'atta ka quantity 20% dec karo'")
atta_before = get_item("atta")
if atta_before:
    print(f"   Initial quantity: {atta_before['quantity']}")
    result3 = process("atta ka quantity 20% dec karo", is_voice=False)
    print(f"   Intent: {result3.intent}")
    print(f"   Success: {result3.success}")
    print(f"   Response: {result3.response}")
    atta_after = get_item("atta")
    qty_change = atta_after['quantity'] - atta_before['quantity']
    expected_change = -atta_before['quantity'] * 0.20
    print(f"   Change: {qty_change:+.2f} (expected: {expected_change:+.2f})")
    print(f"   ✅ PASS" if abs(qty_change - expected_change) < 0.01 else f"   ❌ FAIL")
else:
    print(f"   ❌ Atta not found in inventory")

# Test 4: Hindi variant - दाल की मात्रा 10% बढ़ाओ
print(f"\n🔄 TEST 4: Hindi - 'दाल की मात्रा 10% बढ़ाओ'")
dal_before = get_item("dal")
if dal_before:
    print(f"   Initial quantity: {dal_before['quantity']}")
    result4 = process("दाल की मात्रा 10% बढ़ाओ", is_voice=False)
    print(f"   Intent: {result4.intent}")
    print(f"   Success: {result4.success}")
    print(f"   Response: {result4.response}")
    dal_after = get_item("dal")
    qty_change = dal_after['quantity'] - dal_before['quantity']
    print(f"   Change: {qty_change:+.2f}")
    print(f"   ✅ PASS" if result4.success else f"   ⚠️ Check response")
else:
    print(f"   ❌ Dal not found in inventory")

print("\n" + "=" * 70)
