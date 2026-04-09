# 🔧 ANALYTICS TROUBLESHOOTING & DEBUGGING GUIDE

## Quick Diagnosis Checklist

### Issue: "Analytics not working"
```bash
# Step 1: Check database
python -c "
import sqlite3
conn = sqlite3.connect('kirana_trends.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM transactions')
print(f'Transactions: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM inventory')
print(f'Inventory items: {cursor.fetchone()[0]}')
"

# Step 2: Check patterns loaded
python -c "
from app.trends.classifier import Classifier
c = Classifier()
print(f'Loaded patterns: {len(c.TREND_PATTERNS)}')
print(c.classify('Pichle 7 din sales')[:2])
"

# Step 3: Test analytics engine
python -c "
from app.trends import TrendsPipeline
pipeline = TrendsPipeline()
result = pipeline.process('Pichle 7 din sales kya tha')
print(result['data'][:500] if 'data' in result else result)
"
```

---

## Common Issues & Solutions

### 1️⃣ **Classifier Not Recognizing Query**

**Symptom:** Query returns `{"trend": None, "error": "Pattern not matched"}`

**Root Causes:**
```
✗ Hinglish spelling different from patterns
✗ Pattern not added in classifier.py
✗ Query too long/complex for regex
✗ Special characters breaking regex
```

**Debug:**
```python
from app.trends.classifier import Classifier

c = Classifier()

# Check what patterns match
query = "Pichle 7 din sales"
result = c.classify(query)
print(f"Matched: {result}")
print(f"Confidence: {result[1]}")

# Try fuzzy matching
from thefuzz import fuzz
for pattern in c.TREND_PATTERNS:
    score = fuzz.partial_ratio(query.lower(), pattern[0].pattern)
    if score > 80:
        print(f"Close match: {pattern[0].pattern} ({score}%)")
```

**Fix:**
```python
# Add new pattern in app/trends/classifier.py
TREND_PATTERNS = [
    # ... existing patterns
    
    # Your new pattern
    (r"pichle\s+(\d+)\s+(din|hafte|mahine).*sales", 
     "sales_trend", 
     lambda m: {"days": int(m.group(1)), "period": m.group(2)}),
]
```

---

### 2️⃣ **Database Query Error**

**Symptom:** `sqlite3.OperationalError: no such table 'transactions'`

**Root Causes:**
```
✗ Database not initialized
✗ Wrong database path
✗ Tables not created
✗ Migrations not run
```

**Debug:**
```bash
# Check file exists
ls -la kirana_trends.db

# List all tables
sqlite3 kirana_trends.db ".tables"

# Check schema
sqlite3 kirana_trends.db ".schema transactions"
```

**Fix:**
```python
# Initialize database
from app.db.database import Database

db = Database('kirana_trends.db')
db.init_db()  # Creates tables and seeds data

# Verify
db.conn.execute("SELECT * FROM inventory LIMIT 1")
```

---

### 3️⃣ **No Data Returned**

**Symptom:** Returns empty table or "No data available"

**Root Causes:**
```
✗ Database has no transactions
✗ Date range has no data
✗ Item not in inventory
✗ Wrong time period selected
✗ Time zone issues
```

**Debug:**
```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('kirana_trends.db')
c = conn.cursor()

# Check transaction count
c.execute("SELECT COUNT(*) FROM transactions")
print(f"Total transactions: {c.fetchone()[0]}")

# Check date range
c.execute("SELECT MIN(timestamp), MAX(timestamp) FROM transactions")
min_date, max_date = c.fetchone()
print(f"Date range: {min_date} to {max_date}")

# Check specific item
c.execute("SELECT * FROM inventory WHERE name LIKE '%apple%'")
print(f"Items with 'apple': {c.fetchall()}")

# Check last 7 days
seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
c.execute("""
    SELECT COUNT(*) FROM transactions 
    WHERE timestamp > ?
""", (seven_days_ago,))
print(f"Transactions in last 7 days: {c.fetchone()[0]}")
```

**Fix:**
```python
# Add sample transactions
from app.db.database import Database

db = Database('kirana_trends.db')

# Add test transactions
for i in range(10):
    db.sell_item(
        item_name="apple",
        quantity=2 + i,
        price=15,
        customer_id="test_cust"
    )

print("Added 10 test transactions")
```

---

### 4️⃣ **Slow Performance**

**Symptom:** Query takes >5 seconds to respond

**Root Causes:**
```
✗ Too many transactions (>100k)
✗ Complex grouping/aggregation
✗ Missing database indexes
✗ Inefficient SQL queries
✗ Memory issues
```

**Debug:**
```python
import time
from app.trends import TrendsPipeline

pipeline = TrendsPipeline()

# Measure query time
start = time.time()
result = pipeline.process("Pichle 7 din sales")
elapsed = time.time() - start

print(f"Query time: {elapsed:.2f}s")

# If > 1 second, check database
import sqlite3
conn = sqlite3.connect('kirana_trends.db')
c = conn.cursor()

# Count transactions
c.execute("SELECT COUNT(*) FROM transactions")
count = c.fetchone()[0]
print(f"Transaction count: {count}")

# Check if indexes exist
c.execute("SELECT name FROM sqlite_master WHERE type='index'")
indexes = c.fetchall()
print(f"Indexes: {[i[0] for i in indexes]}")
```

**Fix:**
```python
# Add indexes to speed up queries
import sqlite3

conn = sqlite3.connect('kirana_trends.db')
c = conn.cursor()

# Create missing indexes
c.execute("""
    CREATE INDEX IF NOT EXISTS idx_timestamp 
    ON transactions(timestamp)
""")

c.execute("""
    CREATE INDEX IF NOT EXISTS idx_item_id 
    ON transactions(item_id)
""")

c.execute("""
    CREATE INDEX IF NOT EXISTS idx_customer_id 
    ON transactions(customer_id)
""")

conn.commit()
print("Indexes created")
```

---

### 5️⃣ **Incorrect Results**

**Symptom:** Numbers don't match manual calculation

**Root Causes:**
```
✗ Wrong calculation logic
✗ Time zone mismatch
✗ Currency precision
✗ Filter logic error
✗ Duplicate entries
```

**Debug:**
```python
from app.trends import TrendsPipeline

pipeline = TrendsPipeline()

# Get raw data
result = pipeline.process("Pichle 7 din sales", return_raw=True)

print("Raw data returned:")
print(result['sql'])        # Show SQL query used
print(result['data'])        # Show raw numbers
print(result['calculation']) # Show math

# Verify manually
import sqlite3
conn = sqlite3.connect('kirana_trends.db')
c = conn.cursor()

# Run query manually
c.execute(result['sql'])
manual_result = c.fetchall()
print(f"Manual verification: {manual_result}")
```

**Fix:**
```python
# Review calculation in app/trends/engine.py
def sales_trend(self, days=7):
    # Check:
    # 1. Correct date range
    # 2. Only counting sales (type='sale')
    # 3. Price precision (price * quantity)
    # 4. Correct time zone
    # 5. No duplicate rows
```

---

### 6️⃣ **Pattern Matching Too Broad**

**Symptom:** Wrong analytics triggered (e.g., "sales" matching "wholesale")

**Root Causes:**
```
✗ Regex too generic
✗ Pattern order wrong (specific should come first)
✗ Missing word boundaries
✗ Case sensitivity issues
```

**Debug:**
```python
import re

# Test patterns
test_queries = [
    "Pichle 7 din sales",
    "Wholesale price",
    "Sales tax",
    "Today sales"
]

patterns = [
    r"\bsales\b",  # Good: word boundary
    r"sales",      # Bad: too broad
]

for query in test_queries:
    for pattern in patterns:
        if re.search(pattern, query, re.IGNORECASE):
            print(f"'{query}' matches '{pattern}'")
```

**Fix:**
```python
# In app/trends/classifier.py, fix pattern order
TREND_PATTERNS = [
    # SPECIFIC patterns first (more precise)
    (r"pichle\s+(\d+)\s+(din|hafte|mahine|saal).*sales", "sales_trend", ...),
    
    # Then GENERAL patterns (more flexible)
    (r"(sale|bikta|revenue)", "sales_trend", ...),
]
```

---

### 7️⃣ **Item Not Recognized**

**Symptom:** "apple" query doesn't match database items

**Root Causes:**
```
✗ Item not in inventory
✗ Name spelling different
✗ Case mismatch
✗ Alias not defined
✗ Unicode/Devanagari issues
```

**Debug:**
```python
from app.db.database import Database
from app.nlp.extractor import Extractor

db = Database('kirana_trends.db')
extractor = Extractor(db)

# What items are in database
print("Items in database:")
items = db.get_all_items()
for item in items:
    print(f"  - {item['name']}")

# Can extractor find "apple"?
extracted = extractor._extract_item_name("apple")
print(f"\nExtracted item name: {extracted}")

# Check aliases
print(f"\nAliases for apple:")
if 'apple' in extractor.ITEM_ALIASES:
    print(f"  - {extractor.ITEM_ALIASES['apple']}")
else:
    print("  - NOT FOUND IN ALIASES")
```

**Fix:**
```python
# Add to ITEM_ALIASES in app/nlp/extractor.py
ITEM_ALIASES = {
    # ... existing
    "apple": "apple",
    "सेब": "apple",        # Hindi
    "सब": "apple",         # Hindi short form
    "sebu": "apple",       # Transliterated
}

# Or add to database
db.add_item("apple", quantity=0, unit="piece", price=15, cost_price=10)
```

---

### 8️⃣ **API Returns HTML Instead of JSON**

**Symptom:** 
```
{"error": "...", "status": 500}
or
HTML error page
```

**Root Causes:**
```
✗ API server crashed
✗ Dependencies not installed
✗ Database locked
✗ Port already in use
```

**Debug:**
```bash
# Check if API is running
curl -s http://localhost:8000/health || echo "API not responding"

# Watch logs
tail -f logs/api.log

# Manually test endpoint
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "hello"}'

# Check port
lsof -i :8000
```

**Fix:**
```bash
# Kill any old process
lsof -ti :8000 | xargs kill -9

# Restart API with debug
python main.py --api --debug

# Install missing dependencies
pip install -r requirements.txt
```

---

## Validation Checklist

Before going to production:

```bash
# 1. Database initialized
python -c "from app.db.database import Database; Database().init_db(); print('✓ Database OK')"

# 2. All patterns loaded
python -c "from app.trends.classifier import Classifier; print(f'✓ {len(Classifier().TREND_PATTERNS)} patterns loaded')"

# 3. Sample data exists
python -c "from app.db.database import Database; items = Database().get_all_items(); print(f'✓ {len(items)} items in database')"

# 4. Analytics engine works
python -c "from app.trends import TrendsPipeline; result = TrendsPipeline().process('Pichle 7 din sales'); print('✓ Analytics engine working')"

# 5. API responds
curl -s http://localhost:8000/query -d '{}' -H "Content-Type: application/json" && echo "✓ API responding" || echo "✗ API not responding"

# 6. Voice (if enabled)
python -c "from app.asr.whisper_asr import WhisperASR; WhisperASR().health_check(); print('✓ Voice setup OK')" 2>/dev/null || true
```

---

## Debug Mode

Enable detailed logging:

```python
# In your code
import logging
logging.basicConfig(level=logging.DEBUG)

# Create logger for each module
logger = logging.getLogger(__name__)
logger.debug(f"Processing query: {query}")
logger.debug(f"Matched pattern: {result['trend']}")
logger.debug(f"SQL: {sql_query}")
logger.debug(f"Raw data: {data}")
```

In `main.py`:
```python
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('analytics.log'),
            logging.StreamHandler()
        ]
    )
    run_api()
```

---

## Performance Profiling

```python
import cProfile
import pstats

def profile_analytics():
    from app.trends import TrendsPipeline
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    pipeline = TrendsPipeline()
    pipeline.process("Pichle 7 din sales")
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 slowest functions

# Run it
profile_analytics()
```

---

## Recovery Procedures

### If Database Corrupted:
```bash
# Backup current
cp kirana_trends.db kirana_trends.db.backup

# Reinitialize
rm kirana_trends.db
python -c "from app.db.database import Database; Database().init_db()"

# Verify
python -c "from app.db.database import Database; print('✓ Database recovered')"
```

### If Patterns Broken:
```bash
# Restore from git
git checkout app/trends/classifier.py

# Or manually fix in editor
# Review app/trends/classifier.py TREND_PATTERNS
```

### If Performance Degraded:
```bash
# Clear old transactions (>1 year)
python -c "
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('kirana_trends.db')
c = conn.cursor()

# Keep only last 1 year
one_year_ago = (datetime.now() - timedelta(days=365)).isoformat()
c.execute('DELETE FROM transactions WHERE timestamp < ?', (one_year_ago,))
conn.commit()

print(f'Deleted old transactions. Remaining: {c.execute(\"SELECT COUNT(*) FROM transactions\").fetchone()[0]}')
"
```

---

## Contact Support

**If stuck:**

1. Run all diagnostics
2. Check `analytics.log`
3. Review relevant README
4. Try test script: `python test_analytics.py`

**Files for reference:**
- 📘 [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md) - Full guide
- 📋 [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick queries
- 📚 [ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md) - Shopkeeper guide
- 🧪 [test_analytics.py](test_analytics.py) - Testing suite

---

**Version:** 1.0 | **Last Updated:** April 2026

