# Hindi Query Routing Fix - Critical Bug Resolution

## Problem
Pure Hindi market basket queries returned inventory lookup results instead of analytics:

**User Query:** "कौन सी चीजें एक साथ बिकती हैं?" (What items sell together?)  
**Expected:** Market basket co-purchase analysis  
**Actual Before Fix:** Inventory list (❌ WRONG)

## Root Cause Analysis

### The Bug
The pipeline was **transliterating Hindi to Latin characters BEFORE checking if the query was an analytics request**:

```
Hindi Query (Devanagari) 
    ↓
[Transliterate to Latin] → "kaun si cheejen ek saath"
    ↓
[NLP Parser] → Misclassifies as inventory QUERY
    ↓
[Check Trends Classifier] → Too late! Intent already set to QUERY
```

**The Issue:** The classifier's Hindi regex patterns look for Devanagari characters:
```python
(r"एक\s*साथ", "market_basket", lambda m: {}),  # Pattern expects Devanagari
```

But after transliteration, the text becomes Latin: `"ek sath"` → Pattern doesn't match! ❌

### Why This Happened

In `pipeline.py` (original code):
```python
# Lines 376-389: NLP parsing happens FIRST with transliteration
text_normalized = _transliterate_devanagari(text)  # ← Transliterates here
text = text_normalized
parsed = parse(text)  # ← Parsed as QUERY (wrong intent)

# Lines 463-464: Trends check happens LATER
if _trends_pipeline is not None and _trends_pipeline.is_trend_query(text):
    # ← Text is already transliterated, patterns don't match!
```

## Solution

**Check trends BEFORE transliteration** to preserve Hindi patterns:

```python
# NEW ORDER (Fixed):
# Step 0: Check trends on ORIGINAL text (before transliteration)
if _trends_pipeline is not None and _trends_pipeline.is_trend_query(text):
    # ← Hindi patterns work here! ✅
    trend_response = _trends_pipeline.process(text)
    return PipelineResult(success=True, response=trend_response, intent="TREND")

# Step 1: THEN do NLP parsing with transliteration
text_normalized = _transliterate_devanagari(text)
text = text_normalized
parsed = parse(text)  # ← Now only used for inventory/cart operations
```

## Implementation Details

### File: `pipeline.py`

**Changed Logic:**
1. Moved trends check (`is_trend_query()`) to the beginning (line ~375)
2. Removed duplicate trends check from line ~463
3. Now transliteration only happens for inventory operations (ADD/SELL/QUERY)

**Result:**
```
Hindi Query (Devanagari)
    ↓
[Check Trends Classifier] → Patterns match! ✅ ("एक साथ" matches)
    ├─ IS trend query? → Route to TrendsPipeline ✅
    └─ NOT trend query? → Then transliterate & parse for inventory
```

## Test Results

### Before Fix (Broken)
```
Input: "कौन सी चीजें एक साथ बिकती हैं?"
Output: "aaple: 86, aloo: 40" (inventory list) ❌
```

### After Fix (Working)
```
Input: "कौन सी चीजें एक साथ बिकती हैं?"  
Output: 🛒 Frequently Bought Together:
        • Chai Patti + Namak (38 baar saath bika)
        • Chai Patti + Pickle (35 baar saath bika) ✅
```

### Verified Queries

**Pure Hindi:**
- ✅ "एक साथ खरीदारी"
- ✅ "दोनों एक साथ क्या बिकता है?"
- ✅ "कौन सी चीजें एक साथ बिकती हैं?"

**Hinglish:**
- ✅ "ek saath kya bikta hai"
- ✅ "items bought together"

**English:**
- ✅ "profit trend"
- ✅ "market basket analysis"

## Technical Details

### Pipeline Execution Order (After Fix)

1. **Trends Check (NEW - EARLY)** - Line ~375
   - Runs: `is_trend_query(text)` on ORIGINAL text
   - If True: Route to TrendsPipeline, return result
   - If False: Continue to step 2

2. **NLP Parsing** - Line ~389  
   - Transliterates: Devanagari → Latin
   - Parses: Extract intent (ADD/SELL/QUERY)
   - Only for inventory operations

3. **Customer Analytics Check** - Line ~398
   - For customer-specific trends

4. **Route by Intent** - Line ~476
   - For ADD: Inventory increment
   - For SELL: Sell items
   - For QUERY: Lookup inventory

### Classifier Pattern Timing

**BEFORE Fix (Broken):**
```
Text → Transliterate → Classifier → Pattern doesn't match ("एक साथ" ≠ "ek sath")
```

**AFTER Fix (Working):**
```
Text → Classifier (Original Devanagari) → Pattern matches! ("एक साथ" ✅) → Trends Pipeline
```

## Impact

### ✅ What's Fixed
- Pure Hindi analytics queries now work correctly
- All 13 analytics accessible via Hindi (not just Hinglish)
- Classifier patterns preserved for original text
- No breaking changes to English/Hinglish queries

### ✅ What Still Works
- English queries: "profit trend", "market basket", etc.
- Hinglish queries: "ek saath kya bikta hai", "dead stock", etc.
- Inventory operations: "bread ke 10 piece add karo", "10kg flour sell karo"
- All 13 analytics across all languages

### 🧪 Database Requirements
- Min 20-30 transactions needed for market basket (was showing empty with 28)
- Seed script creates 6174+ transactions for comprehensive testing
- Run: `python app/trends/seed_demo.py`

## Code Changes Summary

| File | Change | Lines |
|------|--------|-------|
| `pipeline.py` | Moved trends check before transliteration | ~375-380 |
| `pipeline.py` | Removed duplicate trends check | ~463-470 |
| `app/trends/classifier.py` | Added 5 Hindi market basket patterns | ~119-127 |
| `app/trends/engine.py` | Fixed timestamp parsing (ISO format) | ~389 |

## Lessons Learned

1. **Order Matters**: In a multi-stage NLP pipeline, check broader conditions (trends) before narrower ones (inventory NLP)
2. **Text Encoding**: Don't transliterate text before checking patterns that expect the original encoding
3. **Pattern Design**: Consider both Devanagari and Latin variants for comprehensive support
4. **Test Coverage**: Always test with original language first, then transliterated versions

## Testing Checklist

- [x] Hindi market basket queries work
- [x] Hinglish queries still work  
- [x] English queries still work
- [x] Inventory operations (ADD/SELL) still work
- [x] All 13 analytics accessible
- [x] Database properly seeded with co-purchase data
- [x] No regression in other analytics (profit, sales, etc.)

---

**Status:** ✅ RESOLVED & TESTED  
**Date:** 2026-04-09  
**Impact:** Critical - Enables Hindi market basket analytics
