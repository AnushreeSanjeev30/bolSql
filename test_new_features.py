#!/usr/bin/env python3
"""Test all new database features"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
time.sleep(2)  # Wait for server

def test_query(text, label):
    """Test a query and print results"""
    print(f"\n📝 {label}")
    print(f"   Query: {text}")
    try:
        resp = requests.post(
            f"{BASE_URL}/query",
            json={"text": text},
            timeout=5
        )
        data = resp.json()
        if data.get('success'):
            print(f"   ✅ Response: {data.get('response')[:100]}")
        else:
            print(f"   ⚠️  {data.get('response', data.get('error'))[:100]}")
        return data
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

print("=" * 70)
print("🧪 Testing New Database Features")
print("=" * 70)

# Test 1: Price Rollback
test_query(
    "atta ka price rollback karo",
    "Test 1: Price Rollback Feature"
)

# Test 2: Expiry Check
test_query(
    "kaunse items expire hone wale hain",
    "Test 2: Expiry Check Feature"
)

# Test 3: Category Price Update
test_query(
    "spices ke price 10 percent badha do",
    "Test 3: Category Price Update Feature"
)

# Test 4: View Pending Orders
test_query(
    "aaj ke pending orders dikhao",
    "Test 4: View Pending Orders"
)

# Test 5: Stock Items with Category
test_query(
    "grains mein kya kya hai",
    "Test 5: Category Filter Query"
)

# Test 6: Expiry Alert on Low Stock
test_query(
    "kaunse items khatam hone wale hain",
    "Test 6: Items About to Expire"
)

print("\n" + "=" * 70)
print("✅ Feature testing complete!")
print("=" * 70)
