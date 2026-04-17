# Voice System Improvements

## Problem Diagnosed
Voice input produces different outputs than the same text for these reasons:

1. **ASR Transcription Errors** - Whisper sometimes mishears Hinglish, introducing subtle variations
2. **Confidence Not Tracked** - Low-confidence transcriptions were being processed anyway
3. **NLP Rigidity** - Rule-based extractor couldn't handle slight variations in transcribed text

## Solutions Implemented

### 1. ASR Confidence Tracking ✅
**File: `app/asr/whisper_asr.py`**

- Modified `transcribe_bytes()` to return `(text, confidence)` tuple
- Modified `transcribe_file()` similarly
- Confidence calculated from Whisper's segment-level confidence scores

**Impact:** Now detects low-quality transcriptions

### 2. Confidence Filtering in CLI ✅
**File: `app/interface/cli.py`**

- When recording voice: shows `"Suna: 'text' (confidence: 85%)"`
- Rejects transcriptions with confidence < 50%
- User sees: `"⚠️ Confidence low. Dobara try karein."`

**Example:**
```
🎤 Recording... (speak now)
   Suna: "fifty kg aata add karo" (confidence: 92%)
   ✅ 50kg atta successfully add ho gaya
```

vs.

```
🎤 Recording... (speak now)
   Suna: "foofy kg eeeta add karro" (confidence: 38%)
   ⚠️ Confidence low. Dobara try karein.
```

### 3. Fuzzy Matching for NLP ✅
**File: `app/nlp/extractor.py`**

Added `_fuzzy_match_item()` function using `rapidfuzz` for:
- Handling slight variations in item names from bad transcriptions
- Token-based matching (more robust for Hinglish):
  - Input: "aata" → Matches "atta" ✓
  - Input: "attaa" → Matches "atta" ✓
  - Input: "ayyata" → No match if < 60% similarity

**Why This Helps:**
- If Whisper transcribes "atta" as "ettah", fuzzy matching still finds it
- Reduces NLP failures from ASR errors

---

## Testing the Improvements

### Test 1: Voice with Good Audio
```bash
python main.py --voice
# Speak clearly: "50kg atta add karo"
# Expected: High confidence ✅, immediate processing
```

### Test 2: Voice with Background Noise
```bash
python main.py --voice
# Speak unclearly: "fufty kg eetah add karro" (simulated bad audio)
# Expected: Low confidence, prompt to retry
```

### Test 3: Text Input (unchanged)
```bash
python main.py
# Type: "bhaiya 50kg atta add karo"
# Expected: Normal processing, no confidence filtering
```

---

## Architecture Comparison: RAG vs Fine-tuning

### Current Approach: RAG (Retrieval-Augmented Generation)
✅ **Pros:**
- Quick to iterate (add examples anytime)
- No GPU needed
- Works for Hinglish with ~30 curated examples
- Easy to add new languages (just add examples)

❌ **Cons:**
- Depends on high-quality ASR input
- Struggles with very different phrasing

### Alternative: Fine-tuning
✅ **Pros:**
- More robust to ASR errors
- Can learn Hinglish patterns directly

❌ **Cons:**
- Needs 100+ labeled Hinglish-SQL pairs (expensive data collection)
- Requires GPU for training
- Slower iteration cycle
- Harder to add new languages (retrain entire model)

### Recommendation
**For now: Keep RAG + improve ASR quality**
- The confidence filtering + fuzzy matching addresses most issues
- If you want fine-tuning later, collect voice recordings first:
  ```
  data/
    voice_recordings/
      "50kg atta add karo.wav" → SQL: UPDATE inventory...
      "10 packets biscuit becha.wav" → SQL: UPDATE inventory... (SELL)
      ... (100+ samples)
  ```

---

## Next Steps (Optional Enhancements)

### 1. Improve Whisper Model
```python
# In config.py, change:
WHISPER_MODEL = "base"  # Current
# To:
WHISPER_MODEL = "small"  # Better accuracy, 77MB
# Or:
WHISPER_MODEL = "medium"  # Best for Hinglish, 1.4GB
```

### 2. Add Language Detection
```python
# Detect if user switches to English/Hindi/other languages
if detect_language(text) != "hi-en":
    print("⚠️ Please use Hinglish (mix of Hindi + English)")
```

### 3. Multi-language Support
To support English + Hindi + Marathi + Tamil:
- Keep separate ITEM_ALIASES per language
- Keep separate EXAMPLES in RAG per language
- Classify input language, route appropriately

```
inventory_en.db  # English items
inventory_hi.db  # Hindi items  
inventory_mr.db  # Marathi items
```

---

## Debugging Voice Issues

Enable verbose logging to see what's happening:

```bash
python main.py --voice --verbose
```

Output will show:
```
Transcribed: 'fifty kg aata add karo' (confidence: 0.92)
NLP parsing: 'fifty kg aata add karo'
NLP result: ParsedQuery(intent='ADD', item_name='atta', quantity=50, unit='kg', confidence=0.87)
Fuzzy match: 'aata' → 'atta' (score: 0.95)
```

---

## Summary of Changes

| File | Change | Impact |
|------|--------|--------|
| `app/asr/whisper_asr.py` | Returns (text, confidence) tuples | Detects low-quality transcriptions |
| `app/interface/cli.py` | Filters confidence < 50% | Rejects unclear voice inputs |
| `app/nlp/extractor.py` | Added fuzzy matching | Handles ASR-induced variations |

**Breaking Change:** If you have code calling `asr.transcribe_bytes()` directly, it now returns `(text, confidence)` instead of just `text`.

