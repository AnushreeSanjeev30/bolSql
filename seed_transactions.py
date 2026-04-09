#!/usr/bin/env python3
"""
Seed database with realistic transaction data for market basket analysis.
This creates 100+ transactions with co-purchase patterns.
"""

import sqlite3
from datetime import datetime, timedelta
import random

def seed_transactions():
    """Add realistic transaction data to test analytics."""
    
    conn = sqlite3.connect('kirana_trends.db')
    cursor = conn.cursor()
    
    # Define realistic co-purchase patterns (items bought together)
    # These represent shopping baskets - multiple items in same transaction
    purchase_patterns = [
        # Breakfast combos
        ['milk', 'bread', 'butter'],
        ['milk', 'chai patti'],
        ['oil', 'atta'],
        
        # Lunch combos
        ['chawal', 'dal', 'namak'],
        ['oil', 'namak'],
        
        # Dinner combos
        ['bread', 'butter'],
        ['biscuit'],
        ['maggi'],
        
        # Common pairs
        ['namak', 'oil'],
        ['oil', 'sauce'],
        ['chai patti', 'milk'],
        ['chawal', 'dal'],
    ]
    
    # Get all items from database (item_name is TEXT, not id)
    cursor.execute("SELECT name FROM inventory")
    all_items = [row[0].lower() for row in cursor.fetchall()]
    
    print(f"📌 Found {len(all_items)} items in inventory:")
    print(f"   {', '.join(all_items)}")
    print()
    
    # Generate transactions for last 30 days
    base_date = datetime.now() - timedelta(days=30)
    transaction_count = 0
    customer_id_counter = 1
    
    for day in range(30):
        current_date = base_date + timedelta(days=day)
        
        # 3-5 shopping baskets (customer visits) per day
        num_baskets = random.randint(3, 5)
        
        for basket_idx in range(num_baskets):
            # Pick a random purchase pattern
            pattern = random.choice(purchase_patterns)
            
            # ALL items in pattern get SAME timestamp (within same basket)
            basket_time = current_date + timedelta(hours=random.randint(6, 22), minutes=random.randint(0, 59))
            customer_id = f"cust_{customer_id_counter}"
            customer_id_counter += 1
            
            # Add all items from pattern with SAME timestamp
            for item_name in pattern:
                item_name_lower = item_name.lower()
                
                # Find matching item in database
                matched_item = None
                if item_name_lower in all_items:
                    matched_item = item_name_lower
                else:
                    # Try to find similar
                    for db_item in all_items:
                        if item_name_lower in db_item or db_item in item_name_lower:
                            matched_item = db_item
                            break
                
                if matched_item:
                    quantity = random.uniform(0.5, 3)
                    price = random.uniform(10, 80)
                    
                    cursor.execute("""
                        INSERT INTO transactions 
                        (item_name, quantity, price, sold_at, customer_id, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (matched_item, quantity, price, basket_time.isoformat(), customer_id, basket_time.isoformat()))
                    
                    transaction_count += 1
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total = cursor.fetchone()[0]
    
    print(f"✅ Seeded {transaction_count} transactions")
    print(f"📊 Total transactions now: {total}")
    
    # Show date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM transactions")
    min_date, max_date = cursor.fetchone()
    print(f"📅 Date range: {min_date} to {max_date}")
    
    # Show some stats
    cursor.execute("""
        SELECT item_name, COUNT(*) as count 
        FROM transactions 
        GROUP BY item_name
        ORDER BY count DESC 
        LIMIT 5
    """)
    
    print(f"\n📈 Top 5 items by transaction count:")
    for item_name, count in cursor.fetchall():
        print(f"   {item_name}: {count} transactions")
    
    conn.close()

if __name__ == "__main__":
    print("🌱 Seeding database with realistic transactions...\n")
    seed_transactions()
    print("\n✨ Done! Now analytics will have data to analyze.")
    print("\n🎤 Try: 'Log dono saath khareedta?' (Market basket)")
    print("   Or: 'Pichle 7 din sales' (Sales trend)")
