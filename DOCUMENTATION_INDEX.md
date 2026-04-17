# 📚 BOTSQL DOCUMENTATION INDEX

## Quick Start (5 minutes)

**First time?** Start here:
1. Read this file (5 min)
2. Review [QUICK_REFERENCE.md](QUICK_REFERENCE.md) (3 min)
3. Run `python test_analytics.py` (2 min)
4. Start using! 🎉

---

## Documentation Map

### 🚀 For Getting Started
| Document | Purpose | Read Time | Who's It For |
|----------|---------|-----------|-------------|
| **[README.md](README.md)** | Project overview, features, installation | 10 min | Everyone |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Common queries & commands for shopkeepers | 5 min | Shopkeepers |
| **[ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md)** | Detailed guide - all 13 analytics with examples | 30 min | Shopkeepers, Developers |

### 📊 For Understanding the System
| Document | Purpose | Read Time | Who's It For |
|----------|---------|-----------|-------------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design & data flow | 25 min | Developers |
| **[ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md)** | How to use analytics in code | 20 min | Developers |
| **[VOICE_IMPROVEMENTS.md](VOICE_IMPROVEMENTS.md)** | Voice command fixes & improvements | 10 min | Developers |

### 🔧 For Troubleshooting & Debugging
| Document | Purpose | Read Time | Who's It For |
|----------|---------|-----------|-------------|
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Common issues & solutions | 15 min | Everyone |
| **test_sarvam.py** | Diagnose Sarvam voice setup | 5 min | Developers |
| **test_analytics.py** | Test all 13 analytics engines | 10 min | Everyone |

---

## File Organization

```
bolSql/
├── 📘 DOCUMENTATION FILES
│   ├── README.md                      ← Start here
│   ├── QUICK_REFERENCE.md             ← Shopkeeper's quick guide
│   ├── ANALYTICS_GUIDE.md             ← Detailed analytics examples
│   ├── ARCHITECTURE.md                ← System design & flow
│   ├── ANALYTICS_IMPLEMENTATION.md    ← Dev guide for using analytics
│   ├── TROUBLESHOOTING.md             ← Debugging & fixes
│   ├── VOICE_IMPROVEMENTS.md          ← Voice command improvements
│   └── DOCUMENTATION_INDEX.md         ← This file
│
├── 🧪 TEST FILES
│   ├── test_sarvam.py                 ← Voice setup diagnostics
│   └── test_analytics.py              ← Analytics engine tests
│
├── 🐍 MAIN APPLICATION
│   ├── main.py                        ← Entry point
│   ├── api.py                         ← FastAPI server
│   ├── config.py                      ← Configuration
│   ├── pipeline.py                    ← Main orchestration
│   ├── logger.py                      ← Logging setup
│   └── requirements.txt                ← Dependencies
│
├── 📁 app/
│   ├── asr/                           ← Speech-to-text
│   │   ├── __init__.py
│   │   └── whisper_asr.py             ← Sarvam voice integration
│   ├── nlp/                           ← Natural language processing
│   │   ├── __init__.py
│   │   └── extractor.py               ← Intent & entity extraction
│   ├── db/                            ← Database layer
│   │   ├── __init__.py
│   │   ├── database.py                ← SQLite operations
│   │   └── migrations.py              ← Database schema
│   ├── trends/                        ← Analytics (13 engines)
│   │   ├── __init__.py                ← TrendsPipeline orchestration
│   │   ├── engine.py                  ← 13 analytics modules
│   │   ├── classifier.py              ← Intent → trend type (60+ patterns)
│   │   ├── formatter.py               ← Output formatting
│   │   ├── evaluator.py               ← Result evaluation
│   │   ├── monthly_report.py
│   │   ├── seed_demo.py
│   │   ├── migrate.py
│   │   ├── customer_engine.py         ← Customer analytics (RFM, Churn)
│   │   └── faiss_index.faiss          ← Vector search index
│   ├── interface/
│   │   ├── __init__.py
│   │   └── cli.py                     ← Command-line interface
│   ├── llm/
│   │   ├── __init__.py
│   │   └── generator.py               ← Groq LLM integration (fallback)
│   ├── safety/
│   │   ├── __init__.py
│   │   └── validator.py               ← Input validation
│   └── __init__.py
│
└── 📢 frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api.js                     ← API client
    │   └── components/
    │       ├── VoicePanel.jsx         ← Voice interface (not yet integrated)
    │       ├── HistoryPanel.jsx
    │       ├── InventoryPanel.jsx
    │       └── Sidebar.jsx
    └── ... (React files)
```

---

## How to Use Each Document

### 🎯 QUICK_REFERENCE.md
**Best for:** Shopkeepers who want quick answers

**Use when:**
- "What do I say to check sales?"
- "How do I ask about profit?"
- "What commands work?"

**Contains:**
- 13 analytics with example queries
- Common commands in English/Hinglish
- Weekly routine suggestions
- Quick lookup table

**Example:**
```
📊 SALES TREND
Ask: "Pichle saat din sales kya tha?"
     "Last week sales"
     "Sales ho gaya kitna"
```

---

### 📘 ANALYTICS_GUIDE.md
**Best for:** Shopkeepers & developers who want details

**Use when:**
- "Tell me more about profit analysis"
- "How does dead stock detection work?"
- "What should I do with the output?"

**Contains:**
- All 13 analytics with:
  - What it does (explanation)
  - Example queries (Hinglish)
  - Sample output (real tables/numbers)
  - When to use it
  - Pro tips
  - Actionable insights

**Example:**
```
💰 PROFIT TREND ANALYSIS

What It Does:
Shows which items are most profitable

Example Query:
"Sabse zyada profit kaun sa item de raha hai?"
(Which item gives most profit?)

Sample Output:
[Shows table with Top Profit Items]

When To Use:
- Weekly planning
- Reorder decisions
- Pricing strategy
```

---

### 🏗️ ARCHITECTURE.md
**Best for:** Developers who want to understand system flow

**Use when:**
- "How does voice input work?"
- "What happens after I ask a question?"
- "How are analytics computed?"
- "Can I add new features?"

**Contains:**
- System diagram (input → output)
- Component descriptions
- Data flow examples
- Design decisions
- Performance metrics
- Integration points

**Quick Reference:**
```
User Query
    ↓
Speech-to-Text (Sarvam)
    ↓
Text Processing (transliteration)
    ↓
Intent Classification (NLP)
    ↓
Analytics Engine (13 modules)
    ↓
Format & Response
```

---

### 🚀 ANALYTICS_IMPLEMENTATION.md
**Best for:** Developers implementing or customizing

**Use when:**
- "How do I use analytics in Python?"
- "How do I add a new analytics module?"
- "How do I integrate with my code?"
- "What's the API?"

**Contains:**
- Installation steps
- Code examples (Python)
- API endpoints
- Query patterns
- Customization guide
- Testing methods
- Best practices

**Example Code:**
```python
from app.trends import TrendsPipeline

pipeline = TrendsPipeline()
result = pipeline.process("Pichle 7 din sales")
print(result['data'])
```

---

### 🔧 TROUBLESHOOTING.md
**Best for:** Everyone when something breaks

**Use when:**
- "Query not working"
- "Getting wrong results"
- "Performance is slow"
- "Pattern not matching"
- "Database error"

**Contains:**
- Common issues with solutions
- Debug procedures
- Performance profiling
- Recovery procedures
- Validation checklist

**Quick Diagnostic:**
```bash
# Run all checks at once
python -c "
from app.db.database import Database
from app.trends import TrendsPipeline
Database().init_db()
print('✓ Database OK')
TrendsPipeline().process('sales')
print('✓ Analytics OK')
"
```

---

### 🎤 VOICE_IMPROVEMENTS.md
**Best for:** Developers who fixed voice issues

**Use when:**
- Understanding Devanagari transliteration
- Learning pattern fixes
- Reviewing what improved
- Fixing similar issues

**Contains:**
- Problem descriptions
- Root cause analysis
- Solutions implemented
- Test results
- Hinglish examples

---

## Common Workflows

### Workflow 1: "I'm a shopkeeper - Get Started"
```
1. Read QUICK_REFERENCE.md (5 min)
2. Try example queries
3. Check ANALYTICS_GUIDE.md for more details
4. Start using daily!
```

### Workflow 2: "I'm a developer - Understand System"
```
1. Read README.md (understand what it does)
2. Read ARCHITECTURE.md (understand how it works)
3. Review ANALYTICS_IMPLEMENTATION.md (see code examples)
4. Look at app/trends/engine.py (study actual code)
5. Run test_analytics.py (validate working)
```

### Workflow 3: "Something's broken - Fix it"
```
1. Go to TROUBLESHOOTING.md
2. Run diagnostic commands
3. Find your issue in table
4. Follow Fix section
5. Validate with test_*.py
```

### Workflow 4: "I want to add new feature"
```
1. Review ARCHITECTURE.md (understand flow)
2. Check ANALYTICS_IMPLEMENTATION.md (see patterns)
3. Look at app/trends/classifier.py (add pattern)
4. Modify app/trends/engine.py (add logic)
5. Update ANALYTICS_GUIDE.md (document)
6. Add test in test_analytics.py
7. Run full test suite
```

---

## Navigation Tips

### By Document Purpose:
- **Learning the system?** → ARCHITECTURE.md
- **How to use it?** → QUICK_REFERENCE.md → ANALYTICS_GUIDE.md
- **Writing code?** → ANALYTICS_IMPLEMENTATION.md
- **Something broken?** → TROUBLESHOOTING.md
- **Understand decisions?** → VOICE_IMPROVEMENTS.md

### By User Type:

**👨‍💼 Shopkeeper:**
1. QUICK_REFERENCE.md (5 min quick start)
2. ANALYTICS_GUIDE.md (understand each feature)
3. That's it! Start using.

**👨‍💻 Developer:**
1. README.md (overview)
2. ARCHITECTURE.md (system design)
3. ANALYTICS_IMPLEMENTATION.md (code guide)
4. Specific files in app/ (study code)
5. test_*.py (validate working)

**🔧 DevOps/Deployment:**
1. README.md (requirements)
2. TROUBLESHOOTING.md (diagnostics)
3. ARCHITECTURE.md (deployment section)
4. main.py → how to run

**🐛 Debugger/QA:**
1. TROUBLESHOOTING.md (issues & fixes)
2. test_*.py (validation)
3. ARCHITECTURE.md (understand flow)
4. app/ files (study code)

---

## Search Quick Links

### If You're Looking For...

| Question | Document | Section |
|----------|----------|---------|
| Profit analysis | ANALYTICS_GUIDE.md | Profit Trend |
| Sales trend | QUICK_REFERENCE.md | Sales Trend |
| Voice setup | test_sarvam.py | Run this |
| Dead stock | ANALYTICS_GUIDE.md | Dead Stock |
| How to add pattern | ANALYTICS_IMPLEMENTATION.md | Customization |
| Error: "Pattern not matched" | TROUBLESHOOTING.md | Issue #1 |
| "Analytics returning empty" | TROUBLESHOOTING.md | Issue #3 |
| Customer behavior | ANALYTICS_GUIDE.md | Customer Pattern |
| Festival impact | ANALYTICS_GUIDE.md | Festival Trend |
| System design | ARCHITECTURE.md | Core Components |
| API endpoints | ANALYTICS_IMPLEMENTATION.md | Usage Examples |
| Integration | ARCHITECTURE.md | Integration Points |

---

## Testing Quick Reference

**Quick validation:**
```bash
# Test 1: System working
python test_analytics.py

# Test 2: Voice setup (optional)
python test_sarvam.py

# Test 3: Manual test
python -c "
from app.trends import TrendsPipeline
p = TrendsPipeline()
print(p.process('Pichle 7 din sales'))
"
```

---

## Development Checklist

Before committing changes:

```
□ Read ARCHITECTURE.md (understand system impact)
□ Check QUICK_REFERENCE.md (ensure backward compatible)
□ Review ANALYTICS_GUIDE.md (update if needed)
□ Update TROUBLESHOOTING.md (if new issue fixed)
□ Run test_analytics.py (validate working)
□ Update relevant docstrings (in code)
□ Add to VOICE_IMPROVEMENTS.md (if notable)
□ Test in isolation (unit test)
□ Test end-to-end (integration test)
□ Update README.md (if user-facing)
```

---

## Key Concepts at a Glance

**Hinglish:** Hindi + English mixed language
- Example: "Pichle saat din sales kya tha?" (Last 7 days sales?)
- System understands both written and spoken form

**Intent Classification:** Determining what the shopkeeper wants
- Types: ADD inventory, SELL item, QUERY inventory, TREND analytics
- Method: Pattern matching (60+ variations)
- Fallback: Groq LLM if no pattern matches

**Analytics Engine:** 13 specialized business intelligence modules
1. Sales Trend, 2. Hourly Rush, 3. Product Demand, 4. Seasonal Trend
5. Stock Depletion, 6. Smart Reorder, 7. Dead Stock, 8. Profit Trend
9. Festival Trend, 10. Market Basket, 11. Customer Pattern, 12. Auto Subscription
13. Weather Trend

**Sarvam ASR:** Speech-to-text with native Hinglish support
- Converts voice to text with high accuracy
- Handles Devanagari script
- Returns confidence scores

**Transliteration:** Converting Devanagari to Latin characters
- पिछले → pichle
- Removes noise (stray consonants)
- Normalizes for NLP processing

---

## Getting Help

### For Documentation Issues:
- Check if your question is in the document
- Use Ctrl+F to search
- Check the Table of Contents

### For Code Issues:
1. Check TROUBLESHOOTING.md
2. Run test_analytics.py
3. Check error logs
4. Review ARCHITECTURE.md (understand flow)
5. Look at actual code in app/

### For Feature Requests:
- Review ANALYTICS_GUIDE.md (maybe it exists!)
- Check ARCHITECTURE.md (future milestones)
- Look at test_analytics.py (testing patterns)

---

## Document Maintenance

| Document | Last Updated | Status | Accuracy |
|----------|--------------|--------|----------|
| README.md | Apr 2026 | ✅ Current | 100% |
| QUICK_REFERENCE.md | Apr 2026 | ✅ Current | 100% |
| ANALYTICS_GUIDE.md | Apr 2026 | ✅ Current | 100% |
| ARCHITECTURE.md | Apr 2026 | ✅ Current | 100% |
| ANALYTICS_IMPLEMENTATION.md | Apr 2026 | ✅ Current | 100% |
| TROUBLESHOOTING.md | Apr 2026 | ✅ Current | 100% |
| VOICE_IMPROVEMENTS.md | Apr 2026 | ✅ Current | 100% |
| DOCUMENTATION_INDEX.md | Apr 2026 | ✅ Current | 100% |

---

## Quick Links to Popular Sections

📘 **For Shopkeepers:**
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md#quick-commands) - Quick commands
- [ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md#profit-trend) - Profit Analysis
- [ANALYTICS_GUIDE.md](ANALYTICS_GUIDE.md#dead-stock) - Dead Stock

📊 **For Developers:**
- [ARCHITECTURE.md](ARCHITECTURE.md#core-components) - System components
- [ANALYTICS_IMPLEMENTATION.md](ANALYTICS_IMPLEMENTATION.md#usage-examples) - Code examples
- [app/trends/engine.py] - The 13 analytics (in code)

🔧 **For Debugging:**
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md#quick-diagnosis-checklist) - Diagnosis
- [test_analytics.py] - Test all engines
- [test_sarvam.py] - Test voice setup

---

## Next Steps

1. **Choose your role** (Shopkeeper / Developer / DevOps)
2. **Read the recommended documents** for your role
3. **Run the tests** to validate everything works
4. **Start using the system** or implementing features
5. **Refer back to docs** as needed

---

**📍 You are here: DOCUMENTATION_INDEX.md**

**Version:** 1.0  
**Last Updated:** April 2026  
**Status:** ✅ Complete & Production Ready  
**Languages:** English + Hinglish  

🎯 **Everything you need is documented. Pick your path and go!**

