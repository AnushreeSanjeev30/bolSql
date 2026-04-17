#!/usr/bin/env python3
"""
test_analytics.py
Comprehensive test of all 13 analytics engines.
Run this to see all capabilities in action!
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.trends import TrendsPipeline
from logger import get_logger

log = get_logger("test_analytics")

print("\n" + "="*70)
print("🎯 RETAIL ANALYTICS SYSTEM - COMPREHENSIVE TEST")
print("="*70)

# Initialize pipeline
pipeline = TrendsPipeline(db_path="kirana_trends.db")

# Test queries (shopkeeper-friendly)
test_queries = [
    # 1. Profit Analysis
    {
        "name": "1. PROFIT ANALYSIS",
        "query": "Subse zyada profit kaun sa item de raha hai?",
        "description": "Find most profitable items",
    },
    
    # 2. Festival Trends
    {
        "name": "2. FESTIVAL TRENDS",
        "query": "Diwali mein kya bikta hai?",
        "description": "Sales during Diwali festival",
    },
    
    # 3. Weather Impact
    {
        "name": "3. WEATHER-BASED INSIGHTS",
        "query": "Baarish mein inventory plan karo",
        "description": "Seasonal demand patterns",
    },
    
    # 4. Dead Stock
    {
        "name": "4. DEAD STOCK DETECTION",
        "query": "Kaun sa maal nahi bik raha?",
        "description": "Identify slow-moving items",
    },
    
    # 5. Customer Patterns
    {
        "name": "5. CUSTOMER BUYING PATTERNS",
        "query": "Customer pattern batao",
        "description": "Regular customer buying habits",
    },
    
    # 6. Smart Reorder
    {
        "name": "6. SMART REORDER RECOMMENDATIONS",
        "query": "Kitna order karna chahiye?",
        "description": "Optimal reorder quantities",
    },
    
    # 7. Sales Trend
    {
        "name": "7. SALES TREND ANALYSIS",
        "query": "Pichle 7 din ka sales batao",
        "description": "Daily revenue for last 7 days",
    },
    
    # 8. Rush Hours
    {
        "name": "8. HOURLY RUSH PATTERNS",
        "query": "Kaunse baje sabse busy hota hai?",
        "description": "Busiest hours breakdown",
    },
    
    # 9. Top Products
    {
        "name": "9. PRODUCT DEMAND ANALYSIS",
        "query": "Sabse zyada kya bik raha hai?",
        "description": "Top 10 selling products",
    },
    
    # 10. Bundle Ideas
    {
        "name": "10. MARKET BASKET ANALYSIS",
        "query": "Log kya saath mein khareedta hain?",
        "description": "Items bought together",
    },
    
    # 11. Customer Segments
    {
        "name": "11. CUSTOMER SEGMENTATION (RFM)",
        "query": "Best customer kaun hai?",
        "description": "VIP and loyal customers",
    },
    
    # 12. Churn Risk
    {
        "name": "12. CHURN PREDICTION",
        "query": "Kaun customer nahi aa rahe?",
        "description": "At-risk customers",
    },
    
    # 13. Stock Adequacy
    {
        "name": "13. STOCK ADEQUACY CHECK",
        "query": "Kitne din ka stock bacha hai?",
        "description": "Days of stock remaining",
    },
]

def run_test(query_dict):
    """Run a single analytics test."""
    name = query_dict["name"]
    query = query_dict["query"]
    desc = query_dict["description"]
    
    print(f"\n{'─'*70}")
    print(f"📌 {name}")
    print(f"   Query: \"{query}\"")
    print(f"   Purpose: {desc}")
    print(f"{'─'*70}")
    
    try:
        # Check if it's a trend query
        if pipeline.is_trend_query(query):
            # Process the query
            result = pipeline.process(query)
            if result:
                print(f"\n✅ RESULT:\n")
                print(result)
            else:
                print("⚠️  No data available yet. System needs 7+ days of transaction data.")
        else:
            print("❌ Query type not recognized as analytics query")
            print("   Try asking: 'Pichle 7 din sales', 'Profit analysis', 'Dead stock', etc.")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests."""
    
    print("\n" + "="*70)
    print("📊 TESTING ALL 13 ANALYTICS ENGINES")
    print("="*70)
    
    # Show system status
    print("\n[System Status]")
    print(f"Database: kirana_trends.db")
    print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pipeline: Ready")
    
    # Run each test
    for i, query_dict in enumerate(test_queries, 1):
        run_test(query_dict)
        
        # Progress indicator
        print(f"\n[Progress: {i}/{len(test_queries)}]")
        
        # Wait between requests to avoid API hammering
        if i < len(test_queries):
            input("Press Enter to continue to next test...")
    
    # Summary
    print("\n" + "="*70)
    print("✅ TEST COMPLETE!")
    print("="*70)
    print("\nNEXT STEPS:")
    print("1. Start API: python main.py --api")
    print("2. Test voice: POST /voice with audio file")
    print("3. Check web: http://localhost:3000 (frontend)")
    print("\nQUICK REFERENCE:")
    print("  - See QUICK_REFERENCE.md for common queries")
    print("  - See ANALYTICS_GUIDE.md for detailed guide")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
