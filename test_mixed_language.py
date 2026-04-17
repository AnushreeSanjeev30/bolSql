#!/usr/bin/env python3
"""Test mixed Hindi-Tamil language support (code-switching)"""

from app.nlp.extractor import parse
from app.trends.classifier import detect_language


def test_mixed_language_queries():
    """Test mixed Hindi-Tamil queries"""
    
    test_cases = [
        # (query, expected_language, expected_intent, expected_item)
        ("arisi kitna irukku", "tamil", "QUERY", "arisi"),  # Rice how much available
        ("dal kitni hai", "hindi", "QUERY", "dal"),  # Lentil how much (Hindi dominant)
        ("maggi kitna vilai", "tamil", "QUERY", "maggi"),  # Noodles how much price (Tamil price word)
        ("rice add pannunga", "tamil", "ADD", "rice"),  # Rice add (English + Tamil verb)
        ("100 kg aatta add karo", "hindi", "ADD", "aatta"),  # Flour add (Hindi + English keyword)
        ("dal becha", "hindi", "SELL", "dal"),  # Lentil sell
        ("arisi vendidha", "tamil", "SELL", "arisi"),  # Rice sold (Tamil verb)
        ("kitna atta bacha hai", "hindi", "QUERY", "atta"),  # Flour how much left (all Hindi)
        ("ethra maggi irukku", "tamil", "QUERY", "maggi"),  # Noodles how much (all Tamil)
        ("200 kg arisi add pannunga", "tamil", "ADD", "arisi"),  # Rice add (quantity + Tamil)
    ]
    
    print("=" * 80)
    print("MIXED LANGUAGE (Sanskrit/Hindi-Tamil) TESTS")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, expected_lang, expected_intent, expected_item in test_cases:
        try:
            detected_lang = detect_language(query)
            result = parse(query, language=detected_lang)
            
            # Check results
            item_match = result.item_name and result.item_name.lower() == expected_item.lower()
            intent_match = result.intent == expected_intent
            lang_match = detected_lang == expected_lang
            
            status = "✓ PASS" if (item_match and intent_match) else "✗ FAIL"
            
            if item_match and intent_match:
                passed += 1
            else:
                failed += 1
            
            print(f"\n{status} | Query: '{query}'")
            print(f"       | Expected: lang={expected_lang}, intent={expected_intent}, item={expected_item}")
            print(f"       | Got:      lang={detected_lang}, intent={result.intent}, item={result.item_name}")
            print(f"       | Confidence: {result.confidence:.2f}")
            
            if not lang_match:
                print(f"       | ⚠ Language mismatch (expected {expected_lang}, got {detected_lang})")
            
        except Exception as e:
            failed += 1
            print(f"\n✗ FAIL | Query: '{query}'")
            print(f"       | Error: {str(e)}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)
    
    return passed, failed


def test_language_detection():
    """Test language detection for mixed queries"""
    
    test_cases = [
        ("arisi kitna irukku", "tamil"),  # 2 Tamil + 1 Hindi
        ("dal kitni hai", "hindi"),       # 3 Hindi
        ("rice add pannunga", "tamil"),   # Tamil verb dominant
        ("100 kg aatta add karo", "hindi"),  # Hindi add keyword
    ]
    
    print("\n" + "=" * 80)
    print("LANGUAGE DETECTION TESTS")
    print("=" * 80)
    
    passed = 0
    for query, expected in test_cases:
        detected = detect_language(query)
        status = "✓" if detected == expected else "✗"
        passed += (1 if detected == expected else 0)
        
        print(f"{status} Query: '{query:30}' | Expected: {expected:10} | Got: {detected}")
    
    print(f"\nDetection Accuracy: {passed}/{len(test_cases)}")
    print("=" * 80)
    
    return passed


if __name__ == "__main__":
    print("\n🧪 Testing Mixed Language Support (Code-Switching)...\n")
    
    lang_passed = test_language_detection()
    passed, failed = test_mixed_language_queries()
    
    total_passed = (6 if lang_passed >= 4 else lang_passed) + passed  # 6 is full detection score
    total_tests = 10 + len(test_mixed_language_queries.__code__.co_consts[1][0])
    
    if failed == 0:
        print("\n✅ All mixed language tests PASSED!")
    else:
        print(f"\n⚠️  {failed} tests failed - review Tamil/Hindi keyword support")
