"""
Test to reproduce and verify Taglish issue.
Demonstrates that Taglish queries fail to parse correctly while Hindi queries work.
"""

from pipeline import process
from app.trends.classifier import detect_language

# Test 1: Language Detection (should work)
print("=" * 60)
print("TEST 1: Language Detection")
print("=" * 60)

taglish_add = "100 kg aatta add pannunga"
hindi_add = "100 kg atta add karo"

detected_taglish = detect_language(taglish_add)
detected_hindi = detect_language(hindi_add)

print(f"\nTaglish: '{taglish_add}'")
print(f"  → Detected language: {detected_taglish}")

print(f"\nHindi: '{hindi_add}'")
print(f"  → Detected language: {detected_hindi}")

# Test 2: Processing Taglish vs Hindi (where the issue manifests)
print("\n" + "=" * 60)
print("TEST 2: Intent Parsing - Hindi vs Taglish")
print("=" * 60)

test_cases = [
    # (query, language, description)
    ("100 kg atta add karo", "hinglish", "Hindi ADD"),
    ("100 kg aatta add pannunga", "tamil", "Taglish ADD"),
    ("dal becha", "hinglish", "Hindi SELL"),
    ("dal vendidha", "tamil", "Taglish SELL"),
    ("kitna dal bacha hai", "hinglish", "Hindi QUERY"),
    ("ethra dal irukku", "tamil", "Taglish QUERY"),
]

for query, lang, desc in test_cases:
    print(f"\n{desc}")
    print(f"  Query: {query} (lang={lang})")
    result = process(query, is_voice=False, language=lang)
    print(f"  Intent: {result.intent if result else 'ERROR'}")
    print(f"  Item: {result.intent if result else 'ERROR'}")
    print(f"  Response: {result.response[:80]}...")
    if not result.success:
        print(f"  ❌ FAILED - {result.error}")
    else:
        print(f"  ✓ SUCCESS")

print("\n" + "=" * 60)
