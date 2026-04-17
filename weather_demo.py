#!/usr/bin/env python3
"""
weather_demo.py - Test script to demonstrate weather-based product suggestions
Run: python weather_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.weather.weather import get_weather, set_weather_location
from app.weather.suggestions import get_weather_suggestions, format_weather_suggestion


def test_weather_api():
    """Test weather API integration"""
    print("=" * 70)
    print("TESTING WEATHER API INTEGRATION")
    print("=" * 70)
    
    # Test 1: Get current weather
    print("\n1️⃣  Fetching current weather...")
    weather = get_weather()
    
    if weather:
        print(f"\n✓ Weather data retrieved successfully!")
        print(f"  • Condition: {weather.get('condition')}")
        print(f"  • Temperature: {weather.get('temperature')}°C")
        print(f"  • Humidity: {weather.get('humidity')}%")
        print(f"  • Wind Speed: {weather.get('wind_speed')} km/h")
        print(f"  • Description: {weather.get('description')}")
    else:
        print("❌ Could not fetch weather data. (API might be down)")
        print("   Proceeding with sample data...\n")
        weather = {"condition": "rain", "temperature": 28}
    
    # Test 2: Get suggestions for different weather conditions
    print("\n" + "=" * 70)
    print("2️⃣  TESTING WEATHER-BASED SUGGESTIONS")
    print("=" * 70)
    
    test_cases = [
        ("rain", "cupnoodle", "hinglish"),
        ("rain", "maggi", "tamil"),
        ("heavy_rain", "tea", "hinglish"),
        ("clear", "juice", "tamil"),
        ("thunderstorm", "candles", "hinglish"),
        ("snow", "hot chocolate", "tamil"),
    ]
    
    for condition, item, lang in test_cases:
        print(f"\n📍 Weather: {condition.upper()} | Item: {item.upper()} | Language: {lang.upper()}")
        print("-" * 70)
        
        suggestions = get_weather_suggestions(condition, item, lang)
        
        if suggestions:
            print(f"💬 Message:\n   {suggestions['message']}")
            print(f"\n💡 Suggested products to add: {', '.join(suggestions['products'][:3])}")
            print(f"\n📝 Tip: {suggestions['weather_tip']}")
        else:
            print("   (No suggestions available)")
    
    # Test 3: Simulate actual system response
    print("\n" + "=" * 70)
    print("3️⃣  SIMULATING ACTUAL SYSTEM RESPONSE")
    print("=" * 70)
    
    if weather:
        condition = weather.get("condition", "clear")
        
        print(f"\n🎤 User says: 'cupnoodle add karo'")
        print(f"🌦️  Current weather: {condition}")
        print(f"\n📲 System response (Hinglish):")
        print("─" * 70)
        message_hi = format_weather_suggestion(weather, "cupnoodle", "hinglish")
        print(message_hi)
        
        print(f"\n📲 System response (Tamil):")
        print("─" * 70)
        message_ta = format_weather_suggestion(weather, "cupnoodle", "tamil")
        print(message_ta)
    
    # Test 4: Change location
    print("\n" + "=" * 70)
    print("4️⃣  CHANGING LOCATION")
    print("=" * 70)
    print("\nSetting location to Mumbai (19.0760, 72.8777)")
    set_weather_location(19.0760, 72.8777)
    
    weather_mumbai = get_weather()
    if weather_mumbai:
        print(f"✓ Mumbai Weather: {weather_mumbai.get('condition')} ({weather_mumbai.get('temperature')}°C)")
    
    print("\n" + "=" * 70)
    print("✅ WEATHER INTEGRATION TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    try:
        test_weather_api()
    except KeyboardInterrupt:
        print("\n\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
