"""
Weather API integration using Open-Meteo (free, no API key required)
Provides current weather conditions for product recommendations
"""

import requests
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import sys
import logging

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import get_logger

log = get_logger("weather")


class WeatherClient:
    """Free weather client using Open-Meteo API"""
    
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    # Default location: India (you can change this)
    # Format: latitude, longitude
    DEFAULT_COORDS = {
        "latitude": 28.7041,
        "longitude": 77.1025,
        "name": "Delhi, India"
    }
    
    # Weather code interpretation (WMO codes)
    WEATHER_CODES = {
        0: {"condition": "clear", "description": "Clear sky"},
        1: {"condition": "mostly_clear", "description": "Mainly clear"},
        2: {"condition": "partly_cloudy", "description": "Partly cloudy"},
        3: {"condition": "overcast", "description": "Overcast"},
        45: {"condition": "foggy", "description": "Foggy"},
        48: {"condition": "foggy", "description": "Depositing rime fog"},
        51: {"condition": "light_drizzle", "description": "Light drizzle"},
        53: {"condition": "moderate_drizzle", "description": "Moderate drizzle"},
        55: {"condition": "dense_drizzle", "description": "Dense drizzle"},
        61: {"condition": "rain", "description": "Slight rain"},
        63: {"condition": "rain", "description": "Moderate rain"},
        65: {"condition": "heavy_rain", "description": "Heavy rain"},
        71: {"condition": "snow", "description": "Slight snow"},
        73: {"condition": "snow", "description": "Moderate snow"},
        75: {"condition": "heavy_snow", "description": "Heavy snow"},
        77: {"condition": "snow", "description": "Snow grains"},
        80: {"condition": "rain_showers", "description": "Slight rain showers"},
        81: {"condition": "rain_showers", "description": "Moderate rain showers"},
        82: {"condition": "heavy_rain_showers", "description": "Violent rain showers"},
        85: {"condition": "snow_showers", "description": "Slight snow showers"},
        86: {"condition": "snow_showers", "description": "Heavy snow showers"},
        95: {"condition": "thunderstorm", "description": "Thunderstorm"},
        96: {"condition": "thunderstorm", "description": "Thunderstorm with slight hail"},
        99: {"condition": "thunderstorm", "description": "Thunderstorm with heavy hail"},
    }
    
    def __init__(self, latitude: Optional[float] = None, longitude: Optional[float] = None):
        """
        Initialize weather client with coordinates.
        Defaults to Delhi, India if not provided.
        """
        self.latitude = latitude or self.DEFAULT_COORDS["latitude"]
        self.longitude = longitude or self.DEFAULT_COORDS["longitude"]
    
    def get_current_weather(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current weather from Open-Meteo API
        Returns: {
            "condition": str (e.g., "rain", "clear", "snow"),
            "temperature": float,
            "humidity": int,
            "weather_code": int,
            "description": str,
            "timestamp": str
        }
        """
        try:
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto"
            }
            
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            current = data.get("current", {})
            
            weather_code = current.get("weather_code", 0)
            weather_info = self.WEATHER_CODES.get(weather_code, {"condition": "unknown", "description": "Unknown"})
            
            return {
                "condition": weather_info["condition"],
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "wind_speed": current.get("wind_speed_10m"),
                "weather_code": weather_code,
                "description": weather_info["description"],
                "timestamp": current.get("time")
            }
        except requests.exceptions.RequestException as e:
            log.warning(f"Weather API call failed: {e}")
            return None
        except Exception as e:
            log.error(f"Error parsing weather data: {e}")
            return None
    
    def set_location(self, latitude: float, longitude: float):
        """Change location for weather queries"""
        self.latitude = latitude
        self.longitude = longitude


# Global weather client instance
_weather_client = WeatherClient()


def get_weather() -> Optional[Dict[str, Any]]:
    """Get current weather from global client"""
    return _weather_client.get_current_weather()


def set_weather_location(latitude: float, longitude: float):
    """Set location for weather queries"""
    _weather_client.set_location(latitude, longitude)
