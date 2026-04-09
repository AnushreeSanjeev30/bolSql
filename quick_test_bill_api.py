#!/usr/bin/env python3
"""
quick_test_bill_api.py
Quick test script to verify bill upload API works.
Run this before starting development.
"""

import json
from datetime import datetime
from app.bill_processor import BillProcessor

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_valid_bill():
    """Test a valid bill"""
    print_header("✅ Test: Valid Bill Upload")
    
    processor = BillProcessor()
    bill = {
        "bill_id": f"QUICK_TEST_{datetime.now().timestamp()}",
        "customer_id": "C_TEST",
        "customer_name": "Test Customer",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": 1, "price": 500},
            {"product_id": "P002", "name": "chawal", "quantity": 2, "price": 600},
        ]
    }
    
    print("📝 Uploading bill:")
    print(json.dumps(bill, indent=2, default=str))
    
    result = processor.process_bill(bill)
    
    print(f"\n✅ Success: {result.success}")
    print(f"📊 Items Processed: {result.items_processed}")
    print(f"📦 Sales Created: {result.sales_records_created}")
    print(f"💾 Inventory Updated: {result.inventory_updated}")
    print(f"📈 Message: {result.message}\n")
    
    return result.success

def test_duplicate():
    """Test duplicate detection"""
    print_header("❌ Test: Duplicate Bill Detection")
    
    processor = BillProcessor()
    bill_id = f"DUP_TEST_{datetime.now().timestamp()}"
    
    # First upload
    bill1 = {
        "bill_id": bill_id,
        "customer_id": "C_DUP",
        "customer_name": "Customer",
        "timestamp": datetime.now().isoformat(),
        "items": [{"product_id": "P001", "name": "atta", "quantity": 1, "price": 500}]
    }
    
    result1 = processor.process_bill(bill1)
    print(f"First upload: {'✅ Success' if result1.success else '❌ Failed'}")
    
    # Second upload (should fail)
    result2 = processor.process_bill(bill1)
    print(f"Duplicate upload: {'✅ Rejected' if not result2.success else '❌ Allowed (ERROR!)'}")
    print(f"Error: {result2.error}\n")
    
    return not result2.success

def test_insufficient_stock():
    """Test insufficient stock detection"""
    print_header("⚠️ Test: Insufficient Stock Detection")
    
    processor = BillProcessor()
    
    bill = {
        "bill_id": f"STOCK_TEST_{datetime.now().timestamp()}",
        "customer_id": "C_STOCK",
        "customer_name": "Customer",
        "timestamp": datetime.now().isoformat(),
        "items": [
            {"product_id": "P001", "name": "atta", "quantity": 99999, "price": 500}
        ]
    }
    
    print("Attempting to sell 99999 kg of atta (impossible)...")
    result = processor.process_bill(bill)
    
    print(f"Result: {'✅ Rejected' if not result.success else '❌ Allowed'}")
    print(f"Error: {result.error}\n")
    
    return not result.success

def run_quick_tests():
    """Run all quick tests"""
    print("\n" + "🚀 " * 20)
    print("BILL UPLOAD API - QUICK TEST")
    print("🚀 " * 20)
    
    tests = [
        ("Valid Bill", test_valid_bill),
        ("Duplicate Detection", test_duplicate),
        ("Stock Check", test_insufficient_stock),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, "✅ PASS" if result else "❌ FAIL"))
        except Exception as e:
            print(f"❌ ERROR: {str(e)}\n")
            results.append((name, "❌ ERROR"))
    
    print_header("📊 RESULTS")
    for name, status in results:
        print(f"  {name}: {status}")
    print()

if __name__ == "__main__":
    run_quick_tests()
    
    print("\n" + "="*60)
    print("✨ Next Steps:")
    print("="*60)
    print("""
1. Start the API:
   uvicorn api:app --reload

2. Test the endpoint:
   curl -X POST http://localhost:8000/api/upload-bill \\
     -H "Content-Type: application/json" \\
     -d @bill_sample.json

3. Open frontend:
   http://localhost:8000

4. Click "📋 Upload Bill" in sidebar

5. Fill form and submit bill
    """)
