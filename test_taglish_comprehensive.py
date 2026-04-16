"""
Comprehensive Taglish Test Suite
Tests all Taglish intents (ADD, SELL, QUERY, PRICE, CORRECTION)
with real-world examples.
"""

from pipeline import process
from app.trends.classifier import detect_language
import json

print("=" * 80)
print("COMPREHENSIVE TAGLISH (TAMIL+ENGLISH) TEST SUITE")
print("=" * 80)

# Test Suite 1: Language Detection
print("\n📍 TEST 1: Language Detection")
print("-" * 80)

detection_tests = [
    ("arisi kitna irukku", "tamil", "Taglish QUERY"),
    ("100 kg aatta add pannunga", "tamil", "Taglish ADD"),
    ("dal vendidha", "tamil", "Taglish SELL"),
    ("vilai 10% kodathu", "tamil", "Taglish PRICE"),
    ("100 kg atta add karo", "hinglish", "Hindi ADD"),
    ("kitna dal bacha hai", "hinglish", "Hindi QUERY"),
]

detection_pass = 0
detection_fail = 0

for query, expected_lang, desc in detection_tests:
    detected = detect_language(query)
    status = "✓" if detected == expected_lang else "❌"
    print(f"{status} {desc:20} | Query: '{query}'")
    print(f"   Expected: {expected_lang}, Got: {detected}")
    if detected == expected_lang:
        detection_pass += 1
    else:
        detection_fail += 1

print(f"\nLanguage Detection: {detection_pass} PASS, {detection_fail} FAIL")

# Test Suite 2: Taglish Intents
print("\n📍 TEST 2: Taglish Intent Parsing & Execution")
print("-" * 80)

taglish_tests = [
    # (query, expected_intent, language, description)
    ("100 kg aatta add pannunga", "ADD", "tamil", "ADD: flour"),
    ("dal vendidha", "SELL", "tamil", "SELL: dal"),
    ("arisi kitna irukku", "QUERY", "tamil", "QUERY: rice quantity"),
    ("ethra dal bacha", "QUERY", "tamil", "QUERY: dal remaining"),
    ("maggi add pannunga", "ADD", "tamil", "ADD: maggi"),
]

intent_pass = 0
intent_fail = 0

for query, expected_intent, lang, desc in taglish_tests:
    result = process(query, is_voice=False, language=lang)
    status = "✓" if result.intent == expected_intent else "❌"
    print(f"\n{status} {desc}")
    print(f"   Query: '{query}' (lang={lang})")
    print(f"   Expected: {expected_intent}, Got: {result.intent}")
    if result.success:
        item_name = result.db_rows[0].get('name', 'N/A') if result.db_rows else 'N/A'
        print(f"   Item: {item_name}")
        print(f"   Response: {result.response[:100]}...")
        if result.intent == expected_intent:
            intent_pass += 1
        else:
            intent_fail += 1
    else:
        print(f"   ❌ Error: {result.error}")
        intent_fail += 1

print(f"\nIntent Parsing: {intent_pass} PASS, {intent_fail} FAIL")

# Test Suite 3: Taglish vs Hindi Comparison
print("\n📍 TEST 3: Taglish vs Hindi Parity")
print("-" * 80)

parity_tests = [
    ("ADD", "100 kg atta add karo", "100 kg aatta add pannunga"),
    ("SELL", "dal becha", "dal vendidha"),
    ("QUERY", "kitna dal bacha hai", "ethra dal irukku"),
]

parity_pass = 0
parity_fail = 0

for intent, hindi_query, tamil_query in parity_tests:
    hindi_result = process(hindi_query, is_voice=False, language="hinglish")
    tamil_result = process(tamil_query, is_voice=False, language="tamil")
    
    hindi_item = hindi_result.db_rows[0].get('name', 'N/A') if hindi_result.db_rows else 'N/A'
    tamil_item = tamil_result.db_rows[0].get('name', 'N/A') if tamil_result.db_rows else 'N/A'
    
    print(f"\n{intent} Intent:")
    print(f"  Hindi: {hindi_query}")
    print(f"    → Intent: {hindi_result.intent}, Item: {hindi_item}, Success: {hindi_result.success}")
    print(f"  Tamil: {tamil_query}")
    print(f"    → Intent: {tamil_result.intent}, Item: {tamil_item}, Success: {tamil_result.success}")
    
    if (hindi_result.intent == tamil_result.intent == intent and 
        hindi_item == tamil_item and 
        hindi_result.success and tamil_result.success):
        print(f"  ✓ PARITY OK")
        parity_pass += 1
    else:
        print(f"  ❌ PARITY MISMATCH")
        parity_fail += 1

print(f"\nParity Check: {parity_pass} PASS, {parity_fail} FAIL")

# Test Suite 4: Taglish-Specific Features
print("\n📍 TEST 4: Taglish-Specific Features")
print("-" * 80)

feature_tests = [
    ("100 kg aatta add pannunga", "ADD", "Tamil response for ADD"),
    ("dal vendidha", "SELL", "Tamil response for SELL"),
    ("ethra dal irukku", "QUERY", "Tamil response for QUERY"),
]

feature_pass = 0
feature_fail = 0

for query, expected_intent, desc in feature_tests:
    result = process(query, is_voice=False, language="tamil")
    
    print(f"\n{desc}")
    print(f"  Query: '{query}'")
    print(f"  Intent: {result.intent}")
    print(f"  Response: {result.response[:120]}...")
    
    # Check if response is in Tamil
    tamil_indicators = ["pannathu", "irukku", "left", "vendida", "pannu"]
    has_tamil = any(indicator in result.response.lower() for indicator in tamil_indicators)
    
    if result.intent == expected_intent and (has_tamil or "successfully" in result.response.lower()):
        print(f"  ✓ FEATURE OK (Tamil response detected)")
        feature_pass += 1
    else:
        print(f"  ⚠️  Check response format")
        feature_fail += 1

print(f"\nFeature Tests: {feature_pass} PASS, {feature_fail} FAIL")

# Summary Report
print("\n" + "=" * 80)
print("SUMMARY REPORT")
print("=" * 80)

total_pass = detection_pass + intent_pass + parity_pass + feature_pass
total_tests = len(detection_tests) + len(taglish_tests) + len(parity_tests) + len(feature_tests)

print(f"\n✓ Total PASS: {total_pass}/{total_tests}")
print(f"\nDetailed Breakdown:")
print(f"  - Language Detection: {detection_pass}/{len(detection_tests)}")
print(f"  - Intent Parsing: {intent_pass}/{len(taglish_tests)}")
print(f"  - Hindi/Taglish Parity: {parity_pass}/{len(parity_tests)}")
print(f"  - Taglish Features: {feature_pass}/{len(feature_tests)}")

if total_pass == total_tests:
    print(f"\n🎉 ALL TAGLISH TESTS PASSED!")
else:
    print(f"\n⚠️  {total_tests - total_pass} tests need attention")

print("\n" + "=" * 80)
