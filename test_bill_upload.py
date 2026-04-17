"""
test_bill_upload.py
Comprehensive test suite for bill upload functionality.
Tests validation, DB updates, atomicity, trends refresh.
"""

import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

from app.bill_processor import BillProcessor, refresh_trends_after_bill
from app.db.database import get_conn, get_all_items
from config import DB_PATH

# ───────────────────────────────────────────────────────────
# Test Cases
# ───────────────────────────────────────────────────────────

def test_valid_bill():
    """✅ Test: Valid bill processing should update DB correctly."""
    print("\n" + "="*60)
    print("TEST: Valid Bill Processing")
    print("="*60)
    
    processor = BillProcessor()
    bill = {
        "bill_id": f"TEST_VALID_{datetime.now().timestamp()}",
        "customer_id": "C_TEST_001",
        "customer_name": "Test Customer Valid",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": 1, "price": 100},
        ]
    }
    
    # Get initial inventory
    conn = get_conn()
    atta_before = conn.execute(
        "SELECT quantity FROM inventory WHERE LOWER(name)='atta'"
    ).fetchone()
    conn.close()
    
    print(f"Atta stock before: {atta_before['quantity']}")
    
    # Process bill
    result = processor.process_bill(bill)
    
    # Get final inventory
    conn = get_conn()
    atta_after = conn.execute(
        "SELECT quantity FROM inventory WHERE LOWER(name)='atta'"
    ).fetchone()
    sales_record = conn.execute(
        "SELECT * FROM transactions WHERE order_id=?",
        (bill["bill_id"],)
    ).fetchone()
    conn.close()
    
    print(f"Atta stock after: {atta_after['quantity']}")
    print(f"Sales recorded: {bool(sales_record)}")
    print(f"Result: {result.success}")
    print(f"Message: {result.message}")
    
    assert result.success, "Bill processing failed"
    assert atta_after["quantity"] == atta_before["quantity"] - 1, "Inventory not updated"
    assert sales_record is not None, "Sales record not created"
    print("✅ PASSED: Valid bill processed successfully")
    

def test_duplicate_bill_id():
    """❌ Test: Duplicate bill ID should be rejected."""
    print("\n" + "="*60)
    print("TEST: Duplicate Bill ID Rejection")
    print("="*60)
    
    processor = BillProcessor()
    bill_id = f"TEST_DUP_{datetime.now().timestamp()}"
    
    # First bill (should succeed)
    bill1 = {
        "bill_id": bill_id,
        "customer_id": "C_TEST_DUP_001",
        "customer_name": "Customer 1",
        "timestamp": datetime.now().isoformat(),
        "items": [{"product_id": "P001", "name": "atta", "quantity": 1, "price": 100}]
    }
    result1 = processor.process_bill(bill1)
    print(f"First bill result: {result1.success}")
    
    # Second bill with same ID (should fail)
    bill2 = {
        "bill_id": bill_id,
        "customer_id": "C_TEST_DUP_002",
        "customer_name": "Customer 2",
        "timestamp": datetime.now().isoformat(),
        "items": [{"product_id": "P001", "name": "atta", "quantity": 1, "price": 100}]
    }
    result2 = processor.process_bill(bill2)
    print(f"Duplicate bill result: {result2.success}")
    print(f"Error: {result2.error}")
    
    assert result1.success, "First bill should succeed"
    assert not result2.success, "Duplicate bill should fail"
    assert "duplicate" in (result2.error or "").lower(), "Error should mention duplicate"
    print("✅ PASSED: Duplicate bill correctly rejected")


def test_insufficient_stock():
    """❌ Test: Insufficient stock should be rejected."""
    print("\n" + "="*60)
    print("TEST: Insufficient Stock Rejection")
    print("="*60)
    
    processor = BillProcessor()
    
    # Get current atta stock
    conn = get_conn()
    atta = conn.execute(
        "SELECT quantity FROM inventory WHERE LOWER(name)='atta'"
    ).fetchone()
    current_qty = atta["quantity"]
    conn.close()
    
    print(f"Current atta stock: {current_qty}")
    
    # Try to sell more than available
    bill = {
        "bill_id": f"TEST_INSUFF_{datetime.now().timestamp()}",
        "customer_id": "C_TEST_INSUFF",
        "customer_name": "Test Insufficient",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": current_qty + 100, "price": 100}
        ]
    }
    
    result = processor.process_bill(bill)
    print(f"Result: {result.success}")
    print(f"Error: {result.error}")
    
    assert not result.success, "Bill should be rejected (insufficient stock)"
    assert "stock" in (result.error or "").lower(), "Error should mention stock"
    print("✅ PASSED: Insufficient stock correctly rejected")


def test_invalid_timestamp():
    """❌ Test: Future timestamp should be rejected."""
    print("\n" + "="*60)
    print("TEST: Future Timestamp Rejection")
    print("="*60)
    
    processor = BillProcessor()
    future_time = (datetime.now() + timedelta(hours=1)).isoformat()
    
    bill = {
        "bill_id": f"TEST_FUTURE_{datetime.now().timestamp()}",
        "customer_id": "C_TEST_FUTURE",
        "customer_name": "Future Test",
        "timestamp": future_time,
        "items": [{"product_id": "P001", "name": "atta", "quantity": 1, "price": 100}]
    }
    
    result = processor.process_bill(bill)
    print(f"Result: {result.success}")
    print(f"Error: {result.error}")
    
    assert not result.success, "Bill with future timestamp should be rejected"
    assert "future" in (result.error or "").lower(), "Error should mention future"
    print("✅ PASSED: Future timestamp correctly rejected")


def test_missing_fields():
    """❌ Test: Missing required fields should be rejected."""
    print("\n" + "="*60)
    print("TEST: Missing Fields Rejection")
    print("="*60)
    
    processor = BillProcessor()
    
    # Missing customer_name
    bill = {
        "bill_id": "TEST_MISSING_001",
        "customer_id": "C_TEST_MISSING",
        "timestamp": datetime.now().isoformat(),
        "items": [{"product_id": "P001", "name": "atta", "quantity": 1, "price": 100}]
    }
    
    result = processor.process_bill(bill)
    print(f"Result: {result.success}")
    print(f"Error (missing customer_name): {result.error}")
    
    assert not result.success, "Bill with missing customer_name should fail"
    print("✅ PASSED: Missing fields correctly rejected")


def test_multiple_items():
    """✅ Test: Multiple items in one bill should all update correctly."""
    print("\n" + "="*60)
    print("TEST: Multiple Items Processing")
    print("="*60)
    
    processor = BillProcessor()
    
    bill = {
        "bill_id": f"TEST_MULTI_{datetime.now().timestamp()}",
        "customer_id": "C_TEST_MULTI",
        "customer_name": "Multi Item Test",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": 2, "price": 500},
            {"product_id": "P002", "name": "chawal", "quantity": 1, "price": 600},
            {"product_id": "P003", "name": "dal", "quantity": 3, "price": 900},
        ]
    }
    
    # Get initial quantities
    conn = get_conn()
    atta_before = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='atta'").fetchone()
    chawal_before = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='chawal'").fetchone()
    dal_before = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='dal'").fetchone()
    conn.close()
    
    print(f"Before: atta={atta_before['quantity']}, chawal={chawal_before['quantity']}, dal={dal_before['quantity']}")
    
    # Process
    result = processor.process_bill(bill)
    
    # Get final quantities
    conn = get_conn()
    atta_after = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='atta'").fetchone()
    chawal_after = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='chawal'").fetchone()
    dal_after = conn.execute("SELECT quantity FROM inventory WHERE LOWER(name)='dal'").fetchone()
    
    sales_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE order_id=?",
        (bill["bill_id"],)
    ).fetchone()
    conn.close()
    
    print(f"After: atta={atta_after['quantity']}, chawal={chawal_after['quantity']}, dal={dal_after['quantity']}")
    print(f"Sales records created: {sales_count['cnt']}")
    print(f"Result: {result.success}")
    
    assert result.success, "Multiple item bill should succeed"
    assert atta_after["quantity"] == atta_before["quantity"] - 2, "Atta not updated correctly"
    assert chawal_after["quantity"] == chawal_before["quantity"] - 1, "Chawal not updated correctly"
    assert dal_after["quantity"] == dal_before["quantity"] - 3, "Dal not updated correctly"
    assert sales_count["cnt"] == 3, "All 3 sales records should be created"
    print("✅ PASSED: Multiple items processed correctly")


def test_atomicity():
    """✅ Test: All-or-nothing transaction (atomicity)."""
    print("\n" + "="*60)
    print("TEST: Transaction Atomicity")
    print("="*60)
    
    processor = BillProcessor()
    
    # Get current atta stock
    conn = get_conn()
    atta_before = conn.execute(
        "SELECT quantity FROM inventory WHERE LOWER(name)='atta'"
    ).fetchone()
    conn.close()
    
    # Create bill with one valid item and one that causes failure
    bill = {
        "bill_id": f"TEST_ATOMIC_{datetime.now().timestamp()}",
        "customer_id": "C_TEST_ATOMIC",
        "customer_name": "Atomicity Test",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": 1, "price": 100},
            {"product_id": "P_BAD", "name": "nonexistent_product", "quantity": atta_before["quantity"] + 1000, "price": 100},
        ]
    }
    
    result = processor.process_bill(bill)
    
    # Check if atta was updated (it shouldn't be, because transaction should rollback)
    conn = get_conn()
    atta_after = conn.execute(
        "SELECT quantity FROM inventory WHERE LOWER(name)='atta'"
    ).fetchone()
    sales_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM transactions WHERE order_id=?",
        (bill["bill_id"],)
    ).fetchone()
    conn.close()
    
    print(f"Atta before: {atta_before['quantity']}, after: {atta_after['quantity']}")
    print(f"Result success: {result.success}")
    print(f"Sales records created: {sales_count['cnt']}")
    
    assert not result.success, "Transaction should fail due to insufficient stock"
    assert atta_after["quantity"] == atta_before["quantity"], "Atomicity violated: atta stock should not change"
    assert sales_count["cnt"] == 0, "No sales should be recorded if transaction fails"
    print("✅ PASSED: Transaction atomicity maintained (rollback worked)")


def test_trends_refresh():
    """✅ Test: Trends refresh after bill processing."""
    print("\n" + "="*60)
    print("TEST: Trends Refresh After Bill")
    print("="*60)
    
    result = refresh_trends_after_bill(str(DB_PATH))
    print(f"Trends refresh result: {result}")
    
    assert result, "Trends refresh should complete successfully"
    print("✅ PASSED: Trends refreshed successfully")


# ───────────────────────────────────────────────────────────
# Run All Tests
# ───────────────────────────────────────────────────────────

def run_all_tests():
    """Run complete test suite."""
    print("\n" + "🧪 " * 20)
    print("BILL UPLOAD TEST SUITE")
    print("🧪 " * 20)
    
    tests = [
        test_valid_bill,
        test_duplicate_bill_id,
        test_insufficient_stock,
        test_invalid_timestamp,
        test_missing_fields,
        test_multiple_items,
        test_atomicity,
        test_trends_refresh,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {len(tests)}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
