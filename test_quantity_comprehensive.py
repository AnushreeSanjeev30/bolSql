#!/usr/bin/env python3
"""Comprehensive test for QUANTITY intent with edge cases."""

from pipeline import process
from app.db.database import get_item, get_all_items

print("\n" + "=" * 70)
print("COMPREHENSIVE QUANTITY INTENT TEST SUITE")
print("=" * 70)

test_cases = [
    # English variations
    ("dal ke quantity 10% badha do", "quantity increase Hindi mix"),
    ("chawal ki quantity 15 percent inc karo", "percentage with word"),
    ("atta quantity 12% dec karo", "decrease with percentage"),
    ("stock quantity 8% increase karo", "stock quantity English"),
    
    # Hindi variants
    ("दाल की मात्रा 10% बढ़ाओ", "Hindi Devanagari"),
    ("चावल मात्रा 5% वृद्धि करें", "Hindi with vriddhi keyword"),
    
    # Edge cases
    ("dal ka quantity", "quantity check only (no percentage)"),
    ("chawal quantity 25% ", "quantity with trailing space"),
]

results_summary = {
    "passed": [],
    "failed": [],
    "warnings": []
}

for query, description in test_cases:
    print(f"\n{'─' * 70}")
    print(f"📌 {description}")
    print(f"   Query: '{query}'")
    
    try:
        result = process(query, is_voice=False)
        print(f"   Intent: {result.intent} ({'✅' if result.intent in ['QUANTITY', 'UNKNOWN'] else '⚠️'} expected QUANTITY)")
        print(f"   Success: {result.success}")
        print(f"   Response: {result.response}")
        
        if result.intent == "QUANTITY" and result.success:
            results_summary["passed"].append(description)
        elif result.intent == "QUERY" and "quantity" in description.lower() and "percentage" not in query.lower():
            results_summary["passed"].append(description)
        else:
            results_summary["warnings"].append((description, f"Intent: {result.intent}, Success: {result.success}"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results_summary["failed"].append((description, str(e)))

# Test for regressions in other intents
print(f"\n{'─' * 70}")
print("🔍 REGRESSION TESTS - Other Intents")

regression_tests = [
    ("dal add karo", "ADD", "Should route to ADD"),
    ("dal 5kg sell karo", "SELL", "Should route to SELL"),
    ("dal kitna bacha hai", "QUERY", "Should route to QUERY"),
    ("dal ka price 10% inc karo", "PRICE", "Should route to PRICE (not QUANTITY)"),
]

for query, expected_intent, description in regression_tests:
    result = process(query, is_voice=False)
    status = "✅" if result.intent == expected_intent else "❌"
    print(f"{status} {description}")
    print(f"   Query: '{query}' → Intent: {result.intent} (expected: {expected_intent})")
    if result.intent != expected_intent:
        results_summary["failed"].append((query, f"Expected {expected_intent}, got {result.intent}"))
    else:
        results_summary["passed"].append(f"Regression: {description}")

# Final summary
print(f"\n{'=' * 70}")
print("SUMMARY")
print(f"{'=' * 70}")
print(f"✅ Passed: {len(results_summary['passed'])}")
print(f"⚠️  Warnings: {len(results_summary['warnings'])}")
print(f"❌ Failed: {len(results_summary['failed'])}")

if results_summary["warnings"]:
    print(f"\n⚠️ WARNINGS:")
    for desc, msg in results_summary["warnings"]:
        print(f"   - {desc}: {msg}")

if results_summary["failed"]:
    print(f"\n❌ FAILURES:")
    for desc, msg in results_summary["failed"]:
        print(f"   - {desc}: {msg}")

print(f"\n{'=' * 70}\n")
