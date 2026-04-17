#!/usr/bin/env python3
"""
setup_weather.py - Configure weather integration for your location
Run: python setup_weather.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


CITIES = {
    "delhi": (28.7041, 77.1025),
    "mumbai": (19.0760, 72.8777),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "jaipur": (26.9124, 75.7873),
    "ahmedabad": (23.0225, 72.5714),
    "lucknow": (26.8467, 80.9462),
    "ludhiana": (30.9010, 75.8573),
    "indore": (22.7196, 75.8577),
    "goa": (15.4909, 73.8278),
    "kochi": (9.9312, 76.2673),
    "visakhapatnam": (17.6869, 83.2185),
}


def setup_weather():
    """Interactive weather setup"""
    print("=" * 70)
    print("🌤️  WEATHER INTEGRATION SETUP")
    print("=" * 70)
    
    print("\n📍 Select your location or enter custom coordinates:")
    print("\nAvailable cities:")
    cities_list = sorted(CITIES.keys())
    for i, city in enumerate(cities_list, 1):
        lat, lon = CITIES[city]
        print(f"  {i:2d}. {city.title():20s} ({lat}, {lon})")
    
    print(f"  {len(cities_list) + 1:2d}. Custom coordinates (latitude, longitude)")
    
    choice = input("\nEnter your choice (number): ").strip()
    
    try:
        choice_num = int(choice)
        
        if choice_num < 1 or choice_num > len(cities_list) + 1:
            print("❌ Invalid choice!")
            return
        
        if choice_num <= len(cities_list):
            city_name = cities_list[choice_num - 1]
            latitude, longitude = CITIES[city_name]
            location_name = city_name.title()
        else:
            # Custom coordinates
            lat_str = input("\nEnter latitude (e.g., 28.7041): ").strip()
            lon_str = input("Enter longitude (e.g., 77.1025): ").strip()
            
            try:
                latitude = float(lat_str)
                longitude = float(lon_str)
                location_name = f"Custom ({latitude}, {longitude})"
            except ValueError:
                print("❌ Invalid coordinates!")
                return
        
        # Test the connection with new location
        print(f"\n🔍 Testing weather API for {location_name}...")
        
        from app.weather.weather import get_weather, set_weather_location
        
        set_weather_location(latitude, longitude)
        weather = get_weather()
        
        if weather:
            print(f"✅ Success! Retrieved weather data:")
            print(f"   • Condition: {weather.get('condition')}")
            print(f"   • Temperature: {weather.get('temperature')}°C")
            print(f"   • Humidity: {weather.get('humidity')}%")
            print(f"   • Wind Speed: {weather.get('wind_speed')} km/h")
            print(f"   • Description: {weather.get('description')}")
            
            # Save to config
            config_file = Path(__file__).parent / "weather_config.json"
            
            import json
            config = {
                "latitude": latitude,
                "longitude": longitude,
                "location_name": location_name,
                "configured_at": str(Path(__file__).parent / "weather_demo.py")
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print(f"\n✅ Configuration saved to: {config_file}")
            print(f"   • Location: {location_name}")
            print(f"   • Latitude: {latitude}")
            print(f"   • Longitude: {longitude}")
            
        else:
            print("⚠️  Could not retrieve weather data.")
            print("   Please check your internet connection and try again.")
            sys.exit(1)
        
    except ValueError:
        print("❌ Invalid input!")
        return


def test_suggestions():
    """Test weather suggestions for current location"""
    print("\n" + "=" * 70)
    print("🧪 TESTING WEATHER SUGGESTIONS")
    print("=" * 70)
    
    from app.weather.weather import get_weather
    from app.weather.suggestions import get_weather_suggestions
    
    weather = get_weather()
    
    if not weather:
        print("❌ Could not fetch weather data.")
        return
    
    condition = weather.get("condition", "clear")
    print(f"\n🌍 Current Weather: {condition.upper()}")
    print(f"   Temperature: {weather.get('temperature')}°C")
    print(f"   Humidity: {weather.get('humidity')}%")
    
    # Test a sample item
    sample_items = {
        "rain": "noodles",
        "heavy_rain": "tea",
        "clear": "juice",
        "thunderstorm": "candles",
        "snow": "coffee",
    }
    
    test_item = sample_items.get(condition, "tea")
    
    print(f"\n📦 Testing suggestions for: {test_item}")
    print("-" * 70)
    
    # Hinglish
    print("\n🗣️  Hinglish Response:")
    suggestions_hi = get_weather_suggestions(condition, test_item, "hinglish")
    if suggestions_hi:
        print(f"Message: {suggestions_hi['message']}")
        print(f"Products: {', '.join(suggestions_hi['products'][:3])}")
    
    # Tamil
    print("\n🗣️  Tamil Response:")
    suggestions_ta = get_weather_suggestions(condition, test_item, "tamil")
    if suggestions_ta:
        print(f"Message: {suggestions_ta['message']}")
        print(f"Products: {', '.join(suggestions_ta['products'][:3])}")


def show_instructions():
    """Show next steps"""
    print("\n" + "=" * 70)
    print("📚 NEXT STEPS")
    print("=" * 70)
    print("""
1. Start using the system normally:
   python main.py              # Text mode
   python main.py --voice      # Voice mode
   python main.py --api        # API mode

2. When you ADD items, you'll see weather-based suggestions:
   "50kg cupnoodle add karo"
   
   Response will include weather-aware recommendations like:
   "Barish chal rahi hai! cupnoodle ke stock ko badhao..."
   💡 tea, coffee, biscuits ka bhi stock dekh lena!

3. Try different weather scenarios:
   - Test in rain, sun, fog, etc.
   - System automatically adapts suggestions

4. Run demo to verify everything:
   python weather_demo.py
   python pipeline_weather_test.py

5. For detailed docs, see:
   - WEATHER_QUICK_START.md
   - WEATHER_INTEGRATION.md

Support languages:
   ✅ Hindi + English (Hinglish)
   ✅ Tamil + English (Tamglish)
""")


if __name__ == "__main__":
    try:
        setup_weather()
        test_suggestions()
        show_instructions()
        print("\n✅ SETUP COMPLETE - Weather integration is ready! 🌤️\n")
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
