#!/usr/bin/env python3
"""
Clean up duplicate items and reset inventory to a clean state.
This script:
1. Backs up current database
2. Removes all duplicates and unwanted items
3. Resets to 15 standard items only
4. Preserves transaction history for analytics
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = "./kirana.db"
TRENDS_DB_PATH = "./kirana_trends.db"

def backup_db():
    """Backup existing database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{DB_PATH}.backup_{timestamp}"
    if Path(DB_PATH).exists():
        shutil.copy(DB_PATH, backup_file)
        print(f"✅ Backed up to: {backup_file}")
        return backup_file
    return None

def clean_inventory():
    """Remove duplicates and keep only standard items"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Standard 15 items to keep
    STANDARD_ITEMS = {
        "atta": ("Atta", "kg"),
        "chawal": ("Chawal", "kg"),
        "dal": ("Dal", "kg"),
        "milk": ("Milk", "litre"),
        "maggi": ("Maggi", "piece"),
        "bread": ("Bread", "piece"),
        "butter": ("Butter", "piece"),
        "chai patti": ("Chai Patti", "kg"),
        "biscuit": ("Biscuit", "packet"),
        "cold drink": ("Cold Drink", "piece"),
        "ice cream": ("Ice Cream", "piece"),
        "pickle": ("Pickle", "kg"),
        "sauce": ("Sauce", "bottle"),
        "namak": ("Namak", "kg"),
        "oil": ("Oil", "litre"),
    }
    
    # Get all current items
    cur.execute("SELECT id, name FROM inventory")
    current_items = cur.fetchall()
    
    print(f"\n📦 Found {len(current_items)} items in inventory")
    print("Cleaning up duplicates and unwanted items...\n")
    
    # Identify items to delete
    to_delete = []
    for item_id, item_name in current_items:
        name_lower = item_name.lower().strip()
        # Check if this is a duplicate or unwanted
        if name_lower not in STANDARD_ITEMS:
            to_delete.append((item_id, item_name))
    
    print(f"🗑️  Removing {len(to_delete)} duplicate/unwanted items:")
    for item_id, name in to_delete:
        print(f"   ❌ {name}")
        cur.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    
    conn.commit()
    conn.close()
    
    print("\n✅ Duplicates removed!")

def reset_inventory():
    """Reset inventory to standard 15 items with clean quantities"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Clear existing inventory (but keep transaction history)
    cur.execute("DELETE FROM inventory")
    
    # Standard 15 items with initial quantities
    STANDARD_ITEMS = [
        ("Atta", 100.0, "kg", 22, 18),
        ("Chawal", 80.0, "kg", 55, 42),
        ("Dal", 60.0, "kg", 90, 70),
        ("Milk", 50.0, "litre", 28, 22),
        ("Maggi", 100.0, "piece", 14, 10),
        ("Bread", 80.0, "piece", 40, 30),
        ("Butter", 90.0, "piece", 55, 42),
        ("Chai Patti", 50.0, "kg", 280, 210),
        ("Biscuit", 100.0, "packet", 20, 14),
        ("Cold Drink", 100.0, "piece", 40, 28),
        ("Ice Cream", 80.0, "piece", 50, 35),
        ("Pickle", 60.0, "kg", 60, 45),
        ("Sauce", 50.0, "bottle", 80, 58),
        ("Namak", 80.0, "kg", 20, 14),
        ("Oil", 70.0, "litre", 130, 100),
    ]
    
    print(f"\n🔄 Resetting inventory to 15 standard items:\n")
    for name, qty, unit, price, cost_price in STANDARD_ITEMS:
        cur.execute("""
            INSERT INTO inventory(name, quantity, unit, price, cost_price)
            VALUES (?, ?, ?, ?, ?)
        """, (name, qty, unit, price, cost_price))
        print(f"   ✅ {name}: {qty} {unit}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Inventory reset to {len(STANDARD_ITEMS)} clean items!")

def verify_cleanup():
    """Verify cleanup was successful"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT name) FROM inventory")
    count, distinct = cur.fetchone()
    
    cur.execute("SELECT name, quantity, unit FROM inventory ORDER BY name")
    items = cur.fetchall()
    
    print(f"\n✅ Verification:")
    print(f"   Total items: {count}")
    print(f"   Unique items: {distinct}")
    print(f"\n📋 Final inventory:")
    for name, qty, unit in sorted(items):
        print(f"   • {name}: {qty} {unit}")
    
    conn.close()

if __name__ == "__main__":
    print("=" * 70)
    print("🧹 DATABASE CLEANUP & RESET SCRIPT")
    print("=" * 70)
    
    # Step 1: Backup
    print("\n[1/4] Backing up current database...")
    backup = backup_db()
    if not backup:
        print("⚠️  No existing database to backup")
    
    # Step 2: Clean duplicates
    print("\n[2/4] Removing duplicate items...")
    clean_inventory()
    
    # Step 3: Reset inventory
    print("\n[3/4] Resetting to 15 standard items...")
    reset_inventory()
    
    # Step 4: Verify
    print("\n[4/4] Verifying cleanup...")
    verify_cleanup()
    
    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 70)
    print("\n💡 Your inventory is now clean with 15 standard items.")
    print("⚠️  Analytics transaction history is preserved in kirana_trends.db")
    print("\nNext: Restart the API server")
