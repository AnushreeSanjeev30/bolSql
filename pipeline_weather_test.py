#!/usr/bin/env python3
"""
pipeline_weather_test.py - Test weather integration in actual pipeline
Run: python pipeline_weather_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import init_db
from app.nlp.extractor import parse
from pipeline import process


def test_pipeline_with_weather():
    """Test weather suggestions in actual pipeline"""
    
    print("=" * 80)
    print("WEATHER INTEGRATION - PIPELINE TESTS")
    print("=" * 80)
    
    # Initialize database
    init_db()
    
    test_cases = [
        ("50kg cupnoodle add karo", "hinglish"),
        ("100 litre orange juice add karo", "tamil"),
        ("20kg tea add karo", "hinglish"),
        ("30 pack biscuits daal do", "tamil"),
        ("15kg ice cream add karo", "hinglish"),
    ]
    
    for query, language in test_cases:
        print(f"\n{'─' * 80}")
        print(f"🎤 Input: {query}")
        print(f"🗣️  Language: {language.upper()}")
        print(f"{'─' * 80}")
        
        try:
            result = process(query, language=language)
            
            print(f"✅ Success: {result.success}")
            print(f"📝 Intent: {result.intent}")
            print(f"\n📞 System Response:")
            print(f"{'─' * 80}")
            print(result.response)
            print(f"{'─' * 80}")
            
            if result.db_rows:
                for row in result.db_rows:
                    print(f"\n💾 Database Entry:")
                    print(f"   • Name: {row.get('name', 'N/A')}")
                    print(f"   • Quantity: {row.get('quantity', 'N/A')}")
                    print(f"   • Unit: {row.get('unit', 'N/A')}")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 80}")
    print("✅ PIPELINE WEATHER TEST COMPLETE")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    try:
        test_pipeline_with_weather()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
