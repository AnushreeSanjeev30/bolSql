# Database Schema Enhancements - Implementation Summary

## ✅ Completed Tasks

### 1. **Category Field Added to Inventory Table**
- **File**: `/Users/bhavana/bolSql/app/db/database.py`
- **Change**: Added `category TEXT DEFAULT 'general'` column to inventory table
- **Migration**: Automated via `run_inventory_migrations()` in `migrations.py`
- **Data**: 15 items categorized (grains, pulses, oils, seasonings, dairy, snacks, toiletries, beverages, spices, fruits, vegetables)
- **SQL Example**: `SELECT * FROM inventory WHERE category = 'spices'`

### 2. **Expiry Date Field Added to Inventory Table**
- **File**: `/Users/bhavana/bolSql/app/db/database.py`
- **Change**: Added `expiry_date TEXT` column to inventory table (format: YYYY-MM-DD)
- **Migration**: Automated via `run_inventory_migrations()` in `migrations.py`
- **Data**: 6 items have expiry dates set (doodh, biscuit, chai, apple, mango, aloo)
- **Helper Functions**:
  - `get_items_by_expiry(days_until_expiry=7)`: Get items expiring within N days
  - `set_item_expiry(name, expiry_date)`: Set expiry date for an item
- **Feature**: Expiry check query in pipeline detects items expiring in 7 days

### 3. **Price History Table Created**
- **File**: `/Users/bhavana/bolSql/app/db/database.py`, `database.py`
- **Schema**:
  ```sql
  CREATE TABLE price_history (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id    INTEGER REFERENCES inventory(id),
      item_name  TEXT,
      old_price  REAL,
      new_price  REAL,
      changed_by TEXT    DEFAULT 'system',
      changed_at TEXT    NOT NULL
  )
  ```
- **Helper Functions**:
  - `update_item_price(name, new_price, reason='manual')`: Update price and log to history
  - `rollback_item_price(name)`: Revert price to previous value
- **Data**: 1 price history entry (atta: ₹20 → ₹22)
- **Feature**: Price rollback query retrieves previous price from history

### 4. **Orders Table Created (Dedicated)**
- **File**: `/Users/bhavana/bolSql/app/db/database.py`
- **Schema**:
  ```sql
  CREATE TABLE orders (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      order_id   TEXT    UNIQUE NOT NULL,
      customer_id TEXT,
      item_id    INTEGER REFERENCES inventory(id),
      item_name  TEXT,
      quantity   REAL    NOT NULL,
      price      REAL,
      order_date TEXT    NOT NULL,
      status     TEXT    DEFAULT 'pending' CHECK(status IN ('pending','confirmed','delivered','cancelled')),
      delivery_date TEXT,
      notes      TEXT
  )
  ```
- **Helper Functions**:
  - `add_order(customer_id, item_id, quantity, price, delivery_date)`: Create new order
  - `get_orders_by_status(status='pending', customer_id=None)`: Query orders by status
- **Data**: 3 sample orders created (ORD-001, ORD-002, ORD-003)
- **Feature**: View pending orders query

## 🔧 NLP Enhancements

### New Intent Types Added
- **ROLLBACK**: Price rollback queries
- **EXPIRY**: Item expiry check queries  
- **CATEGORY**: Category-based price updates

### New Keywords Added (`app/nlp/extractor.py`)
```python
ROLLBACK_KEYWORDS = [r"\brollback\b", r"\bundo\b", r"\brevert\b", ...]
EXPIRY_KEYWORDS = [r"\bexpiry\b", r"\bexpire\b", r"\bkhatam\b", ...]
CATEGORY_KEYWORDS = [r"\bcategory\b", r"\btype\b", r"\bmasala\b", ...]
```

### Intent Scoring Updated
- Added scoring for ROLLBACK, EXPIRY, CATEGORY intents in `parse()` function
- Updated `ParsedQuery` to handle new intent types

## 🗄️ Generator Updates

### SQL Template Enhancements (`app/llm/generator.py`)
- Updated `SQL_SYSTEM_PROMPT` with rules for:
  - Category price updates: `UPDATE inventory SET price = price * 1.1 WHERE category LIKE '%masala%'`
  - Price rollback: Query `price_history` table
  - Expiry checks: `SELECT * FROM inventory WHERE expiry_date <= datetime('now', '+7 days')`
  - Order viewing: `SELECT * FROM orders WHERE status = 'pending'`

### Response Templates Added
- `ROLLBACK` intent: `"✓ Price rollback ho gaya previous rate pe: ₹{old_price}"`
- `EXPIRY` intent: `"⚠️  Yeh {count} items expire hone wale hain 7 din mein..."`
- `CATEGORY` intent: `"✓ Category ka price update ho gaya"`

## 🚀 Pipeline Route Handlers Added

### New Handlers in `pipeline.py`
1. **`_handle_price_rollback(parsed)`**: Manages price rollback feature
2. **`_handle_expiry_check(parsed)`**: Checks and displays expiring items
3. **`_handle_category_update(parsed)`**: Updates category prices

## 📊 Database Statistics

### Inventory Snapshot
```
Total Items: 15
Categories: 9 (grains, pulses, oils, seasonings, dairy, snacks, toiletries, beverages, spices, fruits, vegetables)
Items with Expiry Dates: 6 (doodh, biscuit, chai, apple, mango, aloo)
Items with Price History: 1 (atta)
Total Orders: 3 (all pending or confirmed status)
```

### Sample Queries

#### Expiry Check
```sql
SELECT name, expiry_date FROM inventory 
WHERE expiry_date IS NOT NULL 
AND datetime(expiry_date) <= datetime('now', '+7 days')
ORDER BY expiry_date ASC
```

#### Price Rollback
```sql
SELECT old_price FROM price_history 
WHERE item_id = (SELECT id FROM inventory WHERE LOWER(name)='atta')
ORDER BY changed_at DESC LIMIT 1
```

#### Category Price Update
```sql
UPDATE inventory 
SET price = price * 1.10 
WHERE LOWER(category) LIKE '%spices%'
```

#### View Orders
```sql
SELECT * FROM orders 
WHERE status = 'pending' 
ORDER BY order_date DESC
```

## 🧪 Testing

### Data Setup Scripts Created
1. **`add_categories.py`**: Populates categories for all 15 items
2. **`add_price_history.py`**: Creates price history records and sample orders

### Feature Status
- ✅ Category field: Functional, all items categorized
- ✅ Expiry dates: Functional, dates set for perishable items
- ✅ Price history: Functional, rollback ready to use
- ✅ Orders table: Functional, sample orders created
- ⏳ NLP intent detection: Needs fine-tuning for ROLLBACK/EXPIRY/CATEGORY (keywords added, scoring may need adjustment)
- ⏳ Voice integration: Ready, pending voice query testing

## 📝 Migration Strategy

### For Existing Databases
Migrations automatically run on server startup via `init_db()` → `run_inventory_migrations()` → `run_customer_migrations()`

### Schema Changes
- Non-destructive: Uses `ALTER TABLE ADD COLUMN IF NOT EXISTS`
- Creates new tables without affecting existing data
- All changes backward compatible

## 🎯 Next Steps (Optional)

1. **Voice Testing**: Test new features with voice input ("atta price rollback karo")
2. **NLP Tuning**: Adjust keyword weights for better intent classification
3. **UI Integration**: Display category filters and expiry alerts in frontend
4. **Analytics**: Add reports on price changes and order fulfillment

---

**Implementation Date**: April 9, 2026  
**Files Modified**: 6 (database.py, migrations.py, generator.py, extractor.py, pipeline.py)  
**Scripts Created**: 2 (add_categories.py, add_price_history.py)  
**Database Tables Added**: 2 (price_history, orders)  
**Database Columns Added**: 2 (category, expiry_date)
