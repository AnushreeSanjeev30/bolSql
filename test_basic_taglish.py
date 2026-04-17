#!/usr/bin/env python3
"""Test basic Taglish parsing"""

from app.nlp.extractor import parse
from app.trends.classifier import detect_language

print("🧪 Testing basic Taglish parsing...\n")

test_cases = [
    ("100 kg aatta add pannunga", "ADD", "aatta"),
    ("dal vendidha", "SELL", "dal"),
    ("ethra dal irukku", "QUERY", "dal"),
    ("100 kg atta add karo", "ADD", "atta"),
    ("dal becha", "SELL", "dal"),
    ("kitna dal bacha hai", "QUERY", "dal"),
]

passed = 0
failed = 0

for query, expected_intent, expected_item in test_cases:
    lang = detect_language(query)
    result = parse(query, language=lang)
    
    intent_ok = result.intent == expected_intent
    item_ok = expected_item.lower() in (result.item_name or "").lower()
    
    if intent_ok and item_ok:
        print(f"✓ '{query}'")
        print(f"  → Intent={result.intent}, Item={result.item_name}\n")
        passed += 1
    else:
        print(f"✗ '{query}'")
        print(f"  → Expected: Intent={expected_intent}, Item={expected_item}")
        print(f"  → Got: Intent={result.intent}, Item={result.item_name}\n")
        failed += 1

print(f"RESULT: {passed}/{len(test_cases)} tests passed")
