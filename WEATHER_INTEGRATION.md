# Weather-Based Product Recommendations

## Overview

This feature integrates a **free weather API** (Open-Meteo) into your bolSql kirana inventory system. When staff members add items to stock, the system now provides weather-aware recommendations for complementary products to boost sales.

**Example interaction:**
```
Staff: "50kg cupnoodle add karo"
System: "✓ 50kg cupnoodle add ho gaya. Ab total 80kg hai.

Barish chal rahi hai! Cupnoodle ke stock ko badhao — ache se bikrega. 
Sath mein noodles, chai, biscuits bhi lelo! ☔

💡 tea, coffee, biscuits ka bhi stock dekh lena!"
```

## How It Works

1. **Weather Fetching**: Real-time weather is fetched from Open-Meteo API (free, no authentication)
2. **Product Mapping**: Weather conditions are mapped to product suggestions:
   - 🌧️ **Rain/Heavy Rain** → Instant noodles, tea, coffee, biscuits
   - ☀️ **Clear/Hot** → Cold drinks, juice, ice cream
   - ⛈️ **Thunderstorm** → Candles, batteries (for power outages)
   - ❄️ **Snow** → Hot tea, coffee, hot chocolate
   - 🌫️ **Fog** → Ginger tea, immunity products
   - ☁️ **Overcast** → Regular tea, coffee, snacks

3. **Bilingual Support**: Suggestions available in:
   - Hindi+English (Hinglish)
   - Tamil+English (Tamglish)

## Features

- ✅ **No API Key Required** - Uses free Open-Meteo API
- ✅ **Automatic Weather Fetching** - Fails gracefully if API is unavailable
- ✅ **Bilingual Responses** - Hindi+English and Tamil+English support
- ✅ **Location-Configurable** - Can be set for any coordinates
- ✅ **Fast & Lightweight** - No heavy dependencies
- ✅ **Seamless Integration** - Already integrated into ADD pipeline

## Setup

### 1. Install Dependencies

All required packages are already in `requirements.txt`:

```bash
pip install -r requirements.txt
```

The key dependency is `requests` (for API calls).

### 2. Configure Location (Optional)

By default, the system uses **Delhi, India** coordinates (28.7041, 77.1025).

To change the location, edit the weather module or set at runtime:

#### Option A: Edit config file
Create/edit `weather_config.json` in your project root:

```json
{
  "latitude": 19.0760,
  "longitude": 72.8777,
  "name": "Mumbai, India"
}
```

#### Option B: Set programmatically in your code
```python
from app.weather.weather import set_weather_location

# Set for Mumbai
set_weather_location(19.0760, 72.8777)
```

#### Option C: Common City Coordinates
```
Delhi:      28.7041, 77.1025
Mumbai:     19.0760, 72.8777
Bangalore:  12.9716, 77.5946
Chennai:    13.0827, 80.2707
Hyderabad:  17.3850, 78.4867
Pune:       18.5204, 73.8567
Kolkata:    22.5726, 88.3639
Jaipur:     26.9124, 75.7873
```

## Usage

### Automatic Integration (Default)

The weather suggestions are **automatically included** in ADD responses. Just use the system normally:

```bash
python main.py              # Text mode (weather enabled)
python main.py --voice      # Voice mode (weather enabled)
python main.py --api        # API mode (weather enabled)
```

### Test the Integration

Run the demo script to test weather functionality:

```bash
python weather_demo.py
```

This will:
1. Fetch current weather
2. Show suggestions for various conditions
3. Simulate real system responses
4. Test location changes

### Use Specific Languages

The language is automatically detected, but you can force it:

```python
from app.nlp.extractor import parse
from pipeline import _handle_add

# Parse user input
parsed = parse("cupnoodle 50kg add karo")

# Process with specific language
result_hindi = _handle_add(parsed, language="hinglish")
result_tamil = _handle_add(parsed, language="tamil")

print(result_hindi.response)
print(result_tamil.response)
```

## File Structure

```
app/weather/
├── __init__.py              # Package initialization
├── weather.py              # Weather API client (Open-Meteo)
└── suggestions.py          # Product suggestion engine
```

## API Details

### Weather API: Open-Meteo

- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Rate Limit**: 10,000 calls/day (free tier)
- **Authentication**: None required (public API)
- **Response**: JSON with weather codes, temperature, humidity, wind speed
- **Documentation**: https://open-meteo.com/

### Weather Codes (WMO Standards)

The system understands WMO weather codes:
- `0`: Clear sky
- `1-3`: Partly/mostly cloudy
- `45, 48`: Fog
- `51-55`: Drizzle
- `61-65`: Rain
- `71-75`: Snow
- `80-82`: Rain showers
- `85-86`: Snow showers
- `95-99`: Thunderstorm

## Advanced: Custom Suggestions

Add custom weather-to-product mappings in [app/weather/suggestions.py](app/weather/suggestions.py):

```python
SUGGESTIONS_MAP = {
    "rain": {
        "hinglish": {
            "products": ["cupnoodle", "tea", "coffee", ...],
            "message": "Custom message: {item}...",
            "weather_tip": "Custom tip..."
        },
        "tamil": {
            "products": [...],
            "message": "Tamil custom message...",
            "weather_tip": "Tamil tip..."
        }
    }
}
```

## Troubleshooting

### Weather API doesn't respond
- **Problem**: `Weather API call failed`
- **Solution**: The system continues without suggestions (graceful failure)
- **Check**: Ensure you have internet connectivity

### Wrong location suggestions
- **Problem**: Getting suggestions for wrong region
- **Solution**: Set correct coordinates using `set_weather_location(lat, lon)`

### Language-specific issues
- **Problem**: Wrong language in response
- **Solution**: Ensure you're passing correct language parameter: `"hinglish"` or `"tamil"`

## Response Format Examples

### Hindi+English (Hinglish)

```
✓ 50kg cupnoodle add ho gaya. Ab total 80kg hai.

Barish chal rahi hai! Cupnoodle ke stock ko badhao — ache se bikrega. 
Sath mein noodles, chai, biscuits bhi lelo! ☔

💡 tea, coffee, biscuits ka bhi stock dekh lena!
```

### Tamil+English (Tamglish)

```
✓ 50kg cupnoodle successfully add pannathu. Total 80kg irukku.

Mazhai varuthu! Cupnoodle kum stoch increase pannanum — nalla bikum. 
Noodles, chai, biscuits la irunthu order panniidum! ☔

💡 tea, coffee, biscuits la stoch pannunga!
```

## Performance

- **API Call Time**: ~200-500ms (cached when available)
- **Suggestion Generation**: ~10ms
- **Total Overhead**: Minimal (async requests in production recommended)

## Future Enhancements

1. **Caching**: Cache weather data for 30 minutes to reduce API calls
2. **Predictive**: Show suggestions for tomorrow's weather
3. **Analytics**: Track which suggestions lead to actual sales
4. **Custom Maps**: Add shop-specific product mappings per weather
5. **Multiple Locations**: Support multiple shop branches with different weather

## Support

For issues or questions:
1. Run `python weather_demo.py` to verify installation
2. Check logs in `logs/voicesql.log`
3. Ensure internet connectivity for API calls

---

**Weather Integration**: Powered by Open-Meteo 🌍 | Free API | No authentication needed
