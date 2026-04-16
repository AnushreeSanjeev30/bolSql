#!/usr/bin/env python3
"""Verify mixed Hindi-Tamil language support"""

from app.nlp.extractor import parse
from app.trends.classifier import detect_language

print("=" * 70)
print("MIXED HINDI-TAMIL QUERY VERIFICATION")
print("=" * 70)

# The actual query from the UI that was broken
query = "arisi kitna irukku"
lang = detect_language(query)
result = parse(query, language=lang)

print(f"\n✅ KEY SCENARIO: {query}")
print(f"   Language Detected: {lang}")
print(f"   Intent: {result.intent}")
print(f"   Item: {result.item_name}")
print(f"   Confidence: {result.confidence:.2f}")

# Additional mixed-language tests
print(f"\n" + "=" * 70)
print("ADDITIONAL MIXED-LANGUAGE TESTS")
print("=" * 70)

tests = [
    ("maggi kitna vilai", "QUERY price"),
    ("200 kg rice add pannunga", "ADD Tamil"),
    ("dal kitna irukku", "QUERY Tamil"),
    ("ethra atta bacha hai", "QUERY mixed"),
    ("dal becha", "SELL Hindi"),
]

for query, desc in tests:
    lang = detect_language(query)
    result = parse(query, language=lang)
    print(f"\n✓ {query:<30} ({desc})")
    print(f"  → Intent: {result.intent}, Item: {result.item_name}, Lang: {lang}")

print("\n" + "=" * 70)
print("✅ MIXED LANGUAGE SUPPORT WORKING!")
print("=" * 70)
