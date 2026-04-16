"""
Weather-based product suggestions for Indian kirana shops
Maps weather conditions to recommended products to increase stock
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import get_logger

log = get_logger("weather_suggestions")


class WeatherSuggestions:
    """Maps weather conditions to product recommendations"""
    
    # Weather condition to product suggestions mapping
    SUGGESTIONS_MAP = {
        "rain": {
            "hinglish": {
                "products": ["cupnoodle", "instant noodles", "biscuits", "tea", "coffee", "maggi", "packed snacks"],
                "message": "Barish chal rahi hai! {item} ke stock ko badhao — ache se bikrega. Sath mein noodles, chai, biscuits bhi lelo! ☔",
                "weather_tip": "Logon ko ghar pe rehne se instant food aur chai ka bahut demand hota hai.",
            },
            "tamil": {
                "products": ["cupnoodle", "instant noodles", "biscuits", "tea", "coffee", "maggi", "packed snacks"],
                "message": "Mazhai varuthu! {item} kum stoch increase pannanum — nalla bikum. Noodles, chai, biscuits la irunthu order panniidum! ☔",
                "weather_tip": "Mazhai time la indoor snacks um hot beverages um romba pogum.",
            }
        },
        "heavy_rain": {
            "hinglish": {
                "products": ["cupnoodle", "tea", "coffee", "biscuits", "maggi", "packed snacks", "instant food"],
                "message": "Bahut badi barish aa rahi hai! {item} ke stock ko urgently badhao — aaj bikri bahut hogi! ☔☔",
                "weather_tip": "Barish ke din instant food, chai aur packed snacks ki demand maximum hoti hai.",
            },
            "tamil": {
                "products": ["cupnoodle", "tea", "coffee", "biscuits", "maggi", "packed snacks", "instant food"],
                "message": "Kudaiyana mazhai! {item} stock baagu ve increase pannanum — innikki sales romba irukkum! ☔☔",
                "weather_tip": "Kattura mazhaila veetla use panna items demand romba jasthi.",
            }
        },
        "thunderstorm": {
            "hinglish": {
                "products": ["tea", "coffee", "biscuits", "maggi", "packed snacks", "candles", "flashlight batteries"],
                "message": "Toofan aa raha hai! {item} stock ke saath candles aur batteries bhi stock mein rakh — power cut ho sakta hai! ⛈️",
                "weather_tip": "Bijli chali jaane se logon ko candles, batteries aur indoor snacks chahiye.",
            },
            "tamil": {
                "products": ["tea", "coffee", "biscuits", "maggi", "snacks", "candles", "batteries"],
                "message": "Kalaichchi varuthu! {item} kum saayum candles, batteries stock irukka venum — current poay jayum! ⛈️",
                "weather_tip": "Current pogalaam, appadi na candles um batteries um ready-a vainga.",
            }
        },
        "snow": {
            "hinglish": {
                "products": ["tea", "coffee", "hot chocolate", "biscuits", "packed snacks", "warm clothes"],
                "message": "{item} stock mein aur hot beverages bhi add karo — sardi mein tea-coffee aur maggi bahut chalta hai! ❄️",
                "weather_tip": "Barfi/sardi mein garam chai, coffee aur instant noodles ki bahut demand hoti hai.",
            },
            "tamil": {
                "products": ["tea", "coffee", "hot chocolate", "biscuits", "snacks"],
                "message": "{item} kooda hot tea, coffee add pannunga — kuliru naal la demand adhigam irukkum! ❄️",
                "weather_tip": "Kuliru nerathula hot tea um coffee um romba move aagum.",
            }
        },
        "clear": {
            "hinglish": {
                "products": ["cold drinks", "ice cream", "fruit juice", "water bottles", "energy drinks"],
                "message": "{item} stock sahi hai! Aaj dhoop tezi hai — cold drinks, ice cream aur juice bhi rakh dena. ☀️",
                "weather_tip": "Garam din par cold drinks, ice cream aur juices ki demand zyada hoti hai.",
            },
            "tamil": {
                "products": ["cold drinks", "ice cream", "juice", "water", "energy drinks"],
                "message": "{item} stock sariyana. Innikki heat adhigam — cold drinks, ice cream, juice order pannikonga! ☀️",
                "weather_tip": "Veyil naal la cold drinks um ice cream um nalla sell aagum.",
            }
        },
        "mostly_clear": {
            "hinglish": {
                "products": ["cold drinks", "juice", "water bottles", "energy drinks"],
                "message": "{item} stock ko badhao! Aaj garmi hai — cold drinks aur juice ka stock dekh lena. ☀️",
                "weather_tip": "Garm mausam mein cold beverages aur bottled water ki achhi demand hoti hai.",
            },
            "tamil": {
                "products": ["cold drinks", "juice", "water", "energy drinks"],
                "message": "{item} stock update panninum. Kaatradu miga iruppu — cold drinks, water bottle stoch ensure panninum! ☀️",
                "weather_tip": "Soodaana weather la cold beverages demand adhigam.",
            }
        },
        "overcast": {
            "hinglish": {
                "products": ["tea", "coffee", "biscuits", "snacks"],
                "message": "{item} add kar diya! Badalon ke din — chai-coffee aur biscuits ke stock dekh lena. ☁️",
                "weather_tip": "Badlon ke din chai, coffee aur pakora ki demand theek rheti hai.",
            },
            "tamil": {
                "products": ["tea", "coffee", "biscuits", "snacks"],
                "message": "{item} stock update aachu. Meghangal iruppu — tea, coffee vithu snacks stoch check pannum! ☁️",
                "weather_tip": "Megam irukkum naal la tea, coffee, snacks steady-a pogum.",
            }
        },
        "foggy": {
            "hinglish": {
                "products": ["tea", "coffee", "biscuits", "snacks", "ginger tea"],
                "message": "{item} stock mein ginger tea aur chai-coffee ko emphasize karo — fog mein immunity badani padti hai! 🌫️",
                "weather_tip": "Fog mein log immunity badhane ke liye ginger chai aur herbal products prefer karte hain.",
            },
            "tamil": {
                "products": ["tea", "coffee", "ginger tea", "snacks", "biscuits"],
                "message": "{item} stock sariyaa irukku. Kodi nerathula ginger tea, sukku tea nalla pogum! 🌫️",
                "weather_tip": "Mooku moodum weather la ginger tea um immunity drinks um nalla pogum.",
            }
        }
    }
    
    def get_suggestions(self, weather_condition: str, item_name: str, language: str = "hinglish") -> Optional[Dict[str, Any]]:
        """
        Get product suggestions based on weather condition
        Args:
            weather_condition: e.g., "rain", "clear", "snow"
            item_name: Item being added to stock
            language: "hinglish", "hindi", or "tamil"
        Returns:
            {
                "products": [list of suggested products],
                "message": formatted message with item name,
                "weather_tip": explanation for the suggestion
            }
        """
        # Normalize language input
        if language.lower() in ["hindi", "hinglish"]:
            language = "hinglish"
        elif language.lower() in ["tamil", "tamglish", "tanglish"]:
            language = "tamil"
        
        # Get suggestions for this weather condition
        suggestions_data = self.SUGGESTIONS_MAP.get(weather_condition.lower())
        
        if not suggestions_data:
            # Return generic suggestion if weather condition not mapped
            return self._get_generic_suggestion(item_name, language)
        
        lang_data = suggestions_data.get(language, suggestions_data.get("hinglish"))
        
        if not lang_data:
            return self._get_generic_suggestion(item_name, language)
        
        return {
            "products": lang_data.get("products", []),
            "message": lang_data.get("message", "").format(item=item_name),
            "weather_tip": lang_data.get("weather_tip", ""),
            "weather_condition": weather_condition
        }
    
    def _get_generic_suggestion(self, item_name: str, language: str) -> Dict[str, Any]:
        """Generic suggestion when weather doesn't match specific condition"""
        if language == "tamil":
            return {
                "products": ["tea", "coffee", "biscuits", "snacks"],
                "message": f"{item_name} stock update aachu! Tea, coffee, biscuits vithu panthukkittai normal sales iruppa.",
                "weather_tip": "Stock update pannanum",
                "weather_condition": "unknown"
            }
        else:  # hinglish/hindi
            return {
                "products": ["tea", "coffee", "biscuits", "snacks"],
                "message": f"{item_name} stock ba dhiya! Regular items jaise chai-chai aur biscuits to hmesha rakha karo.",
                "weather_tip": "Stock maintain karo",
                "weather_condition": "unknown"
            }

    def get_condition_overview(self, weather_condition: str, language: str = "hinglish") -> Dict[str, Any]:
        """Return weather-driven playbook without requiring a specific inventory item."""
        if language.lower() in ["hindi", "hinglish"]:
            language = "hinglish"
        elif language.lower() in ["tamil", "tamglish", "tanglish"]:
            language = "tamil"

        condition = (weather_condition or "").lower()
        suggestions_data = self.SUGGESTIONS_MAP.get(condition)
        if not suggestions_data:
            return {
                "weather_condition": condition or "unknown",
                "products": ["tea", "coffee", "biscuits", "snacks"],
                "weather_tip": "Stock mix balanced vainga" if language == "tamil" else "Keep stock mix balanced",
                "headline": "Mausam neutral hai — essentials ready rakho",
            }

        lang_data = suggestions_data.get(language, suggestions_data.get("hinglish", {}))
        return {
            "weather_condition": condition,
            "products": lang_data.get("products", []),
            "weather_tip": lang_data.get("weather_tip", ""),
            # Safe generic headline (no item placeholder)
            "headline": (
                "Innikki weather-ku top moving items ready-a vainga"
                if language == "tamil" else
                "Aaj ke mausam ke hisaab se top moving items ready rakho"
            ),
        }
    
    def format_suggestion_message(self, weather_data: Dict, item_name: str, language: str = "hinglish") -> str:
        """
        Create a formatted response message combining weather data and suggestions
        """
        if not weather_data:
            return f"{item_name.title()} stock add ho gaya! ✓"
        
        suggestions = self.get_suggestions(weather_data.get("condition"), item_name, language)
        
        if not suggestions:
            return f"{item_name.title()} stock add ho gaya! ✓"
        
        return suggestions["message"]


# Global suggestions engine
_suggestions_engine = WeatherSuggestions()


def get_weather_suggestions(weather_condition: str, item_name: str, language: str = "hinglish") -> Optional[Dict[str, Any]]:
    """Get suggestions using global engine"""
    return _suggestions_engine.get_suggestions(weather_condition, item_name, language)


def format_weather_suggestion(weather_data: Dict, item_name: str, language: str = "hinglish") -> str:
    """Format suggestion message using global engine"""
    return _suggestions_engine.format_suggestion_message(weather_data, item_name, language)


def get_weather_condition_overview(weather_condition: str, language: str = "hinglish") -> Dict[str, Any]:
    """Get condition-level recommendations using global engine."""
    return _suggestions_engine.get_condition_overview(weather_condition, language)
