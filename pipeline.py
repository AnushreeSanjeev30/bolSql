"""
pipeline.py
Core orchestrator — wires ASR → NLP → RAG → LLM → Safety → DB → Response.
Each step is modular and independently testable.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from datetime import date
import re

sys.path.insert(0, str(Path(__file__).parent))

from config import RAG_TOP_K, DB_PATH, TRENDS_DB_PATH
from logger import get_logger

from app.nlp.extractor import parse, ParsedQuery
from app.rag.retriever import get_retriever
from app.llm.generator import get_llm
from app.safety.validator import validate_sql, safe_error_hinglish
from app.db.database import (
    get_item,
    get_all_items,
    run_safe_query,
    sell_item,
    upsert_item,
    correct_stock,
    get_orders_by_status,
)

from app.trends import TrendsPipeline, classify_trend
from app.trends.monthly_report import maybe_generate_monthly_report, generate_monthly_report
from app.trends.customer_engine import (
    compute_rfm,
    predict_churn,
    compute_ltv,
    loyalty_scores,
    predict_next_purchases,
    cohort_retention,
    generate_delivery_orders,
    visit_frequency,
    basket_size_trend,
)
from app.trends.formatter import format_customer_result, get_greeting
from app.weather.weather import get_weather
from app.weather.suggestions import get_weather_suggestions, format_weather_suggestion

log = get_logger("pipeline")


# ── ASR Normalization (Remove filler words, handle lack of punctuation) ────────

ASR_STRIP = re.compile(
    r"\b(kro|kr|kar|karo|please|na|haan|dena|chahiye|chaiye|aro|aur|par|lekin|bas|lo|ho|raha|rahaa|hai|hain)\b",
    re.IGNORECASE
)

def normalize_asr_input(text: str, is_voice: bool = False) -> str:
    """
    Normalize ASR output: remove filler words, normalize spacing.
    
    ASR outputs are:
    - All lowercase
    - No punctuation
    - May have filler words (karo, please, na, etc.)
    - Multiple spaces
    
    This normalizer removes common fillers to match text input.
    """
    if not is_voice:
        return text
    
    # Remove common Hinglish filler words
    text = ASR_STRIP.sub("", text)
    
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    
    return text


# ── Trends Pipeline ───────────────────────────────────────────────────────────
try:
    _trends_pipeline = TrendsPipeline(db_path=str(TRENDS_DB_PATH))
    maybe_generate_monthly_report(str(TRENDS_DB_PATH))
except Exception as e:  # pragma: no cover - defensive
    log.warning("Trends pipeline init failed: %s", e)
    _trends_pipeline = None


@dataclass
class PipelineResult:
    success: bool
    response: str  # Hinglish response for the user
    sql: Optional[str] = None
    intent: Optional[str] = None
    trend_type: Optional[str] = None
    db_rows: Optional[list] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Inventory operations (ADD / SELL / simple QUERY)
# ---------------------------------------------------------------------------


def _handle_add(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Direct ADD: no LLM needed when NLP extracted enough info.
    
    Includes weather-based product suggestions when available.
    """
    if not parsed.item_name:
        response_map = {
            "hinglish": "Kaunsa item add karna hai? Dobara boliye.",
            "tamil": "Yaar item add panna? Repeat solgal."
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="item_name missing",
        )

    # First, try to detect multiple "qty + unit + item" patterns in a single
    # sentence, e.g. "5 packets biscuit aur 10 pieces chocolate add karo".
    # If we find more than one, treat this as a multi-item ADD.
    raw_l = parsed.raw_text.lower()
    multi_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s+"  # quantity
        r"(kg|kgs|kilo|kilogram|kilograms|litre|liter|litres|liters|l|lt|ltr|"
        r"packet|packets|pack|pkt|piece|pieces|pc|pcs|dozen|doz)\s+"  # unit
        # Item phrase ends before 'aur/and/or/add/karo' or end of sentence
        r"([a-zA-Z ]+?)(?=\s+aur\b|\s+and\b|\s+or\b|\s+add\b|\s+karo\b|$)",
    )
    matches = list(multi_pattern.finditer(raw_l))

    def _normalize_unit(u: str) -> str:
        u = u.lower()
        if u in {"kg", "kgs", "kilo", "kilogram", "kilograms"}:
            return "kg"
        if u in {"litre", "liter", "litres", "liters", "l", "lt", "ltr"}:
            return "litre"
        if u in {"packet", "packets", "pack", "pkt"}:
            return "packet"
        if u in {"piece", "pieces", "pc", "pcs"}:
            return "piece"
        if u in {"dozen", "doz"}:
            return "dozen"
        return u

    if len(matches) > 1:
        rows = []
        lines = []
        for m in matches:
            qty_str, unit_raw, name_raw = m.groups()
            qty = float(qty_str)
            # Ignore no-op segments like "0 packet chai" in multi-add
            if qty <= 0:
                continue
            unit = _normalize_unit(unit_raw)
            item_name = name_raw.strip()
            # Clean trailing filler words that may stick to the item segment
            for suffix in ["add", "karo", "kr", "kar", "please", "na"]:
                if item_name.endswith(" " + suffix):
                    item_name = item_name[: -len(suffix) - 1].strip()

            try:
                row = upsert_item(item_name, qty, unit)
                rows.append(row)
                if language == "tamil":
                    lines.append(
                        f"✓ {qty} {unit} {item_name} successfully add pannathu. Total {row['quantity']} {row['unit']} irukku."
                    )
                else:
                    lines.append(
                        f"✓ {qty} {unit} {item_name} add ho gaya. Ab total {row['quantity']} {row['unit']} hai."
                    )
            except Exception as e:
                log.error("Multi-ADD failed for %s: %s", item_name, e)

        response = "\n".join(lines) if lines else (
            "Kuch bhi add nahi ho paya." if language == "hinglish" else "Yedhume add panna mudiyala."
        )

        # Optionally still add weather-based suggestions using the last item
        if rows:
            try:
                weather_data = get_weather()
                if weather_data:
                    suggestions = get_weather_suggestions(
                        weather_data.get("condition", "clear"),
                        rows[-1]["name"],
                        language,
                    )
                    if suggestions:
                        response += "\n\n" + suggestions["message"]
                        if suggestions.get("products"):
                            products_str = ", ".join(suggestions["products"][:3])
                            if language == "tamil":
                                response += f"\n💡 {products_str} la stoch pannunga!"
                            else:
                                response += f"\n💡 {products_str} ka bhi stock dekh lena!"
            except Exception as e:  # pragma: no cover - defensive
                log.warning("Weather suggestion addition failed (multi-add): %s", e)

        return PipelineResult(
            success=bool(rows),
            response=response,
            intent="ADD",
            db_rows=rows,
        )

    # Fallback: single-item ADD using parsed entities
    qty = parsed.quantity or 1.0
    unit = parsed.unit or "piece"

    try:
        row = upsert_item(parsed.item_name, qty, unit)
        
        # Get base response
        if language == "tamil":
            response = f"✓ {qty} {unit} {parsed.item_name} successfully add pannathu. Total {row['quantity']} {row['unit']} irukku."
        else:
            response = f"✓ {qty} {unit} {parsed.item_name} add ho gaya. Ab total {row['quantity']} {row['unit']} hai."
        
        # Try to add weather-based suggestions
        try:
            weather_data = get_weather()
            if weather_data:
                suggestions = get_weather_suggestions(
                    weather_data.get("condition", "clear"),
                    parsed.item_name,
                    language
                )
                if suggestions:
                    response += "\n\n" + suggestions["message"]
                    if suggestions.get("products"):
                        products_str = ", ".join(suggestions["products"][:3])
                        if language == "tamil":
                            response += f"\n💡 {products_str} la stoch pannunga!"
                        else:
                            response += f"\n💡 {products_str} ka bhi stock dekh lena!"
        except Exception as e:
            log.warning(f"Weather suggestion addition failed: {e}")
            pass  # Continue without weather suggestions if API fails
        
        return PipelineResult(
            success=True,
            response=response,
            intent="ADD",
            db_rows=[row],
        )
    except Exception as e:  # pragma: no cover - defensive
        log.error("ADD failed: %s", e)
        response_map = {
            "hinglish": f"Add karne mein problem aayi: {e}",
            "tamil": f"Add pannrathu vela problem irukku: {e}"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_weather_recommendation(language: str = "hinglish") -> PipelineResult:
    """Answer high-level "weather ke hisaab se kya saman rakho" style queries.

    Uses the live weather API + suggestion map instead of treating the
    sentence as an ADD for a fake item name like "weather hisaab se
    suggestion rakhna chahiye".
    """
    try:
        weather_data = get_weather()
    except Exception as e:  # pragma: no cover - defensive
        log.warning("Weather API error: %s", e)
        weather_data = None

    if not weather_data:
        if language == "tamil":
            response = (
                "Weather data available illa, aana general-aa tea, coffee, biscuits, "
                "snacks, cold drinks la konjam extra stock vachi irunga."
            )
        else:
            response = (
                "Weather API se data nahi mila, lekin generally chai, coffee, biscuits, "
                "snacks aur thande drinks ka stock ready rakhna safe rehta hai."
            )
        return PipelineResult(success=True, response=response, intent="QUERY")

    condition = weather_data.get("condition", "unknown")
    suggestions = get_weather_suggestions(condition, "dukaan", language)

    if not suggestions:
        if language == "tamil":
            response = (
                "Innikki weather normal maathiri irukku. Tea, coffee, biscuits, snacks, "
                "cold drinks la standard stock podhum."
            )
        else:
            response = (
                "Aaj ka weather normal lag raha hai. Chai, coffee, biscuits, snacks aur "
                "cold drinks ka normal stock rakho."
            )
        return PipelineResult(success=True, response=response, intent="QUERY")

    products = suggestions.get("products", [])
    weather_desc = weather_data.get("description", condition).title()
    temp = weather_data.get("temperature")

    lines = []
    if language == "tamil":
        if temp is not None:
            lines.append(f"Innikki weather: {weather_desc} (~{temp:.1f}°C).")
        else:
            lines.append(f"Innikki weather: {weather_desc}.")
    else:
        if temp is not None:
            lines.append(f"Aaj ka weather: {weather_desc} (~{temp:.1f}°C).")
        else:
            lines.append(f"Aaj ka weather: {weather_desc}.")

    msg = suggestions.get("message")
    tip = suggestions.get("weather_tip")
    if msg:
        lines.append(msg)
    if products:
        if language == "tamil":
            lines.append("Suggested items stock pannunga: " + ", ".join(products[:6]))
        else:
            lines.append("In items ka stock ready rakho: " + ", ".join(products[:6]))
    if tip:
        lines.append(f"💡 {tip}")

    return PipelineResult(success=True, response="\n".join(lines), intent="QUERY")


def _handle_sell(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Direct SELL: no LLM needed when NLP extracted enough info."""
    if not parsed.item_name:
        response_map = {
            "hinglish": "Kaunsa item becha? Dobara boliye.",
            "tamil": "Yaar item venditha? Repeat solgal."
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="item_name missing",
        )

    qty = parsed.quantity or 1.0

    try:
        row = sell_item(parsed.item_name, qty)
        if language == "tamil":
            response = f"✓ {qty} {row['unit']} {parsed.item_name} sale record pannathu. Ab {row['quantity']} {row['unit']} left irukku."
        else:
            response = f"✓ {qty} {row['unit']} {parsed.item_name} ka sale record ho gaya. Ab {row['quantity']} {row['unit']} bacha hai."
        return PipelineResult(
            success=True,
            response=response,
            intent="SELL",
            db_rows=[row],
        )
    except ValueError as e:
        # Business logic error (not found, insufficient stock)
        log.warning("SELL rejected: %s", e)
        return PipelineResult(
            success=False,
            response=f"⚠️  {e}",
            error=str(e),
        )
    except Exception as e:  # pragma: no cover - defensive
        log.error("SELL failed: %s", e)
        response_map = {
            "hinglish": f"Sale record karne mein problem: {e}",
            "tamil": f"Sale record pannrathu vela problem: {e}"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_stock_correction(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Handle manual stock corrections like 'dal ka stock 30 kg hai/correct karo'."""
    if not parsed.item_name or parsed.quantity is None:
        response_map = {
            "hinglish": "Kaunsa item aur kitna stock? E.g., 'dal ka stock 30 kg hai correcct karo'",
            "tamil": "Yaar item, evlo stock? Example: 'dal stock 30 kg correct pannunga'",
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="missing item or quantity",
        )

    # Prefer the parsed unit, else fall back to existing item's unit, else 'piece'.
    unit = parsed.unit
    try:
        existing = get_item(parsed.item_name)
    except Exception:
        existing = None
    if not unit and existing:
        unit = existing.get("unit")
    if not unit:
        unit = "piece"

    try:
        row = correct_stock(parsed.item_name, float(parsed.quantity), unit)
        if language == "tamil":
            response = f"✓ {row['name']} stock correct pannathu: {row['quantity']} {row['unit']}"
        else:
            response = f"✓ {row['name']} ka stock correct ho gaya: {row['quantity']} {row['unit']}"
        return PipelineResult(
            success=True,
            response=response,
            intent="CORRECTION",
            db_rows=[row],
        )
    except Exception as e:
        log.error("Stock correction failed: %s", e)
        response_map = {
            "hinglish": f"Stock correction mein problem aayi: {e}",
            "tamil": f"Stock correct panna problem: {e}",
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_query_direct(parsed: ParsedQuery, language: str = "hinglish") -> Optional[PipelineResult]:
    """Handle simple QUERY directly from DB (no LLM needed).

    Returns PipelineResult if handled, None if LLM fallback needed.
    """
    item = parsed.item_name
    raw_lower = parsed.raw_text.lower()

    # If the query is clearly about customers (jin customers, customer list, etc.),
    # skip direct inventory handling and let the LLM+RAG path or customer analytics
    # handle it. This avoids returning "poora stock" for customer-based questions
    # like "jin customers ne ek hi din dal aur chawal dono kharida...".
    #
    # Include common Hindi script variants as well so queries like
    # "कस्टमर की लिस्ट दिखाओ" or "सब्सक्रिप्शन कस्टमर" don't trigger
    # the generic "poora stock" handler.
    customer_tokens = [
        "customer", "customers", "grahak", "client",
        "कस्टमर", "कस्टमर", "ग्राहक", "ग्राहकों",
    ]
    if any(w in raw_lower for w in customer_tokens):
        return None

    # Pending orders (e.g., "aaj ke pending orders dikhao")
    if "pending" in raw_lower and ("order" in raw_lower or "orders" in raw_lower):
        try:
            orders = get_orders_by_status(status="pending")
        except Exception as e:
            log.error("Pending orders query failed: %s", e)
            response_map = {
                "hinglish": "Pending orders dekhne mein problem aayi.",
                "tamil": "Pending orders paarthathula problem irukku.",
            }
            return PipelineResult(
                success=False,
                response=response_map.get(language, response_map["hinglish"]),
                error=str(e),
            )

        if not orders:
            response_map = {
                "hinglish": "Aaj koi pending order nahi hai.",
                "tamil": "Innikki pending order illa.",
            }
            return PipelineResult(
                success=True,
                response=response_map.get(language, response_map["hinglish"]),
                intent="QUERY",
                db_rows=[],
            )

        lines = []
        for o in orders:
            item_name = o.get("item_name", "?")
            qty = o.get("quantity", 0)
            order_id = o.get("order_id", "?")
            delivery = o.get("delivery_date") or "-"
            lines.append(f"  • {order_id}: {item_name} {qty} (delivery: {delivery})")

        response_map = {
            "hinglish": "📦 Pending orders:\n",
            "tamil": "📦 Pending orders:\n",
        }
        response = response_map.get(language, response_map["hinglish"]) + "\n".join(lines)
        return PipelineResult(
            success=True,
            response=response,
            intent="QUERY",
            db_rows=orders,
        )
    if any(word in raw_lower for word in ["kam", "low", "khatam", "shortage"]):
        rows = get_all_items()
        # Filter for items where quantity is low (e.g., < 5)
        low_stock = [r for r in rows if r['quantity'] < 10] # Adjust threshold as needed
        
        if not low_stock:
            response_map = {
                "hinglish": "Sab badhiya hai! Koi bhi saman kam nahi hai.",
                "tamil": "Sab nalla irukku! Yaar samaan less illai."
            }
            return PipelineResult(success=True, response=response_map.get(language, response_map["hinglish"]), intent="QUERY")
        
        lines = [f"  • {r['name']}: {r['quantity']} {r['unit']}" for r in low_stock]
        response_map = {
            "hinglish": "⚠️ Yeh saman kam hai:\n",
            "tamil": "⚠️ Yeh samaan less irukku:\n"
        }
        response = response_map.get(language, response_map["hinglish"]) + "\n".join(lines)
        return PipelineResult(success=True, response=response, intent="QUERY", db_rows=low_stock)

    # "list sab" / "sabhi items" type query
    list_all_terms = {
        "sab",
        "sabhi",
        "all",
        "list",
        "poora",
        "sara",
        "items",
        "item",
        "",
    }

    if (
        not item
        or item in list_all_terms
        or "sab" in parsed.raw_text.lower()
        or "list" in parsed.raw_text.lower()
    ):
        rows = get_all_items()
        if not rows:
            response_map = {
                "hinglish": "Inventory khaali hai. Kuch add karo pehle.",
                "tamil": "Inventory empty. Kuch add panna."
            }
            return PipelineResult(
                success=True,
                response=response_map.get(language, response_map["hinglish"]),
                intent="QUERY",
                db_rows=[],
            )

        lines = [f"  • {r['name']}: {r['quantity']} {r['unit']}" for r in rows]
        response_map = {
            "hinglish": "📦 Aapka poora stock:\n",
            "tamil": "📦 Your complete stock:\n"
        }
        response = response_map.get(language, response_map["hinglish"]) + "\n".join(lines)
        return PipelineResult(
            success=True,
            response=response,
            intent="QUERY",
            db_rows=rows,
        )

    # Specific item query
    row = get_item(item)
    if row:
        qty = row.get("quantity", 0)
        # Older databases might not have a 'unit' column; default gracefully
        unit = row.get("unit", "piece")
        name = row.get("name", item)
        if qty == 0:
            response = f"⚠️  {name} ka stock khatam ho gaya hai! Restock karo." if language == "hinglish" else f"⚠️  {name} stock over. Restock panna."
        elif qty < 5:
            response = f"⚠️  {name} kam bacha hai — sirf {qty} {unit}." if language == "hinglish" else f"⚠️  {name} less irukku — only {qty} {unit}."
        else:
            response = f"Aapke paas {qty} {unit} {name} bacha hai." if language == "hinglish" else f"You have {qty} {unit} {name} left."
        return PipelineResult(
            success=True,
            response=response,
            intent="QUERY",
            db_rows=[row],
        )

    # Item not found directly — let LLM try
    return None


# ── New Feature Handlers (Category, Expiry, Rollback) ────────────────────────

def _handle_price_rollback(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Rollback price to previous value from price_history."""
    try:
        from app.db.database import rollback_item_price, rollback_last_price_change

        # If the NLP couldn't cleanly extract an item name (or picked up
        # stray tokens like 'aj/aaj'), treat it as a global "last change"
        # rollback instead of forcing the user to repeat the item.
        item_name = (parsed.item_name or "").strip() if parsed.item_name else ""
        if item_name.lower() in {"aj", "aaj", "aaj ki", "aj ki", "price", "change"}:
            item_name = ""

        if item_name:
            item = rollback_item_price(item_name)
            label = item_name.title()
        else:
            item = rollback_last_price_change()
            label = item.get("name", "item")

        if language == "tamil":
            response = f"✓ {label} price rollback pannathu: ₹{item['price']}"
        else:
            response = f"✓ {label} ka price rollback ho gaya: ₹{item['price']}"
        return PipelineResult(
            success=True,
            response=response,
            intent="ROLLBACK",
            db_rows=[item],
        )
    except ValueError as e:
        return PipelineResult(
            success=False,
            response=f"❌ {str(e)}",
            error=str(e),
        )
    except Exception as e:
        log.error("Price rollback error: %s", e)
        response_map = {
            "hinglish": "Price rollback mein dikkat aayi",
            "tamil": "Price rollback vela problem"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_expiry_check(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Check items expiring within 7 days."""
    try:
        from app.db.database import get_items_by_expiry
        items = get_items_by_expiry(days_until_expiry=7)
        
        if not items:
            response_map = {
                "hinglish": "✓ Koi item expire hone wala nahi hai aaj kal. Sab fresh hai!",
                "tamil": "✓ No items expiring soon. All fresh!"
            }
            return PipelineResult(
                success=True,
                response=response_map.get(language, response_map["hinglish"]),
                intent="EXPIRY",
                db_rows=[],
            )
        
        # Format response
        items_list = []
        for item in items:
            name = item.get('name', '?')
            expiry = item.get('expiry_date', '?')
            items_list.append(f"{name} (expire: {expiry})")
        
        items_text = "\n  • ".join(items_list)
        response_map = {
            "hinglish": f"⚠️  Yeh {len(items)} items expire hone wale hain 7 din mein:\n  • ",
            "tamil": f"⚠️  These {len(items)} items expiring in 7 days:\n  • "
        }
        response = response_map.get(language, response_map["hinglish"]) + items_text
        
        return PipelineResult(
            success=True,
            response=response,
            intent="EXPIRY",
            db_rows=items,
        )
    except Exception as e:
        log.error("Expiry check error: %s", e)
        response_map = {
            "hinglish": "Expiry check mein dikkat aayi",
            "tamil": "Expiry check vela problem"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_category_update(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Handle category-based price updates."""
    if not parsed.item_name or not parsed.quantity:
        response_map = {
            "hinglish": "Category aur percentage dono batao. E.g., 'spices ke price 10% badha do'",
            "tamil": "Category and percentage both tell. E.g., 'masala price 10% increase panna'"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="missing category or percentage",
        )
    
    try:
        # Extract category from item_name (fuzzy match against categories)
        # For some common phrases, map product words to their logical
        # category so that queries like "saari milk category 10% mehengi karo"
        # correctly target the "dairy" category instead of looking for an
        # item called "doodh".
        raw_l = parsed.raw_text.lower()
        category = (parsed.item_name or "").lower()

        category_aliases = {
            "milk": "dairy",
            "doodh": "dairy",
            "dairy": "dairy",
            "oil": "oils",
            "tel": "oils",
            "oils": "oils",
            "sugar": "sweeteners",
            "chini": "sweeteners",
            "namak": "seasonings",
            "salt": "seasonings",
            "biscuit": "snacks",
            "biscuits": "snacks",
            "snacks": "snacks",
            "mirchi": "spices",
            "haldi": "spices",
            "spice": "spices",
            "spices": "spices",
            "sabzi": "vegetables",
            "vegetable": "vegetables",
            "vegetables": "vegetables",
            "fruit": "fruits",
            "fruits": "fruits",
            "apple": "fruits",
            "mango": "fruits",
        }

        # Try to map either the extracted item_name or any keyword
        # in the raw text to a known category label.
        for key, cat in category_aliases.items():
            if key in category or key in raw_l:
                category = cat
                break

        # If user said things like "dairy items" or "milk products",
        # strip generic suffixes so LIKE matches the stored category.
        for suffix in [" items", " item", " products", " product"]:
            if category.endswith(suffix):
                category = category.replace(suffix, "").strip()

        if not category:
            response = (
                "Category samajh nahi aayi. E.g., 'spices', 'dairy', 'snacks'."
                if language == "hinglish"
                else "Category puriyala. E.g., 'spices', 'dairy', 'snacks' solunga."
            )
            return PipelineResult(
                success=False,
                response=response,
                error="unknown category",
            )

        percentage = parsed.quantity  # Used as percentage multiplier
        
        # Execute update
        from app.db.database import execute_safe_sql
        count = execute_safe_sql(
            f"UPDATE inventory SET price = price * ? WHERE LOWER(category) LIKE ?",
            (1 + (percentage / 100), f"%{category.lower()}%")
        )
        
        if count == 0:
            response = f"❌ {category} category nahi mila" if language == "hinglish" else f"❌ {category} category not found"
            return PipelineResult(
                success=False,
                response=response,
                error="category not found",
            )
        
        response = f"✓ {category} category ke {count} items ka price {percentage}% badha diya" if language == "hinglish" else f"✓ {category} category ke {count} items price {percentage}% increase pannathu"
        return PipelineResult(
            success=True,
            response=response,
            intent="CATEGORY",
            db_rows=[{"category": category, "items_updated": count, "percentage": percentage}],
        )
    except Exception as e:
        log.error("Category update error: %s", e)
        response_map = {
            "hinglish": "Category price update mein dikkat aayi",
            "tamil": "Category price update vela problem"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_price_check(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Check or update item price - don't create new items."""
    if not parsed.item_name:
        response_map = {
            "hinglish": "Kaunsa item? Item naam bataao.",
            "tamil": "Yaar item? Item name solgal."
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="missing item name",
        )
    
    try:
        item = get_item(parsed.item_name)
        if not item:
            response = f"❌ '{parsed.item_name}' nahi mila inventory mein" if language == "hinglish" else f"❌ '{parsed.item_name}' inventory le kanukkala"
            return PipelineResult(
                success=False,
                response=response,
                error="item not found",
            )
        
        # If quantity provided with PRICE intent, it's a price UPDATE.
        # Interpret phrases like "5 rupaye badha do" / "kam kar do" as delta changes,
        # otherwise treat the number as the absolute new price.
        if parsed.quantity:
            from app.db.database import update_item_price

            raw_l = parsed.raw_text.lower()
            current_price = float(item.get("price") or 0.0)

            # Handle common Hinglish / Devanagari-transliterated variants.
            # Devanagari "बढ़ाओ" often becomes "bdhao" after transliteration.
            is_increase = any(kw in raw_l for kw in ["badha", "badhao", "bdhao", "badho", "increase", "inc"])
            is_decrease = any(kw in raw_l for kw in ["kam kar", "kam karo", "kam kar do", "kam kardo", "decrease", "ghata", "dec"])

            # Check if this is a percentage-based update
            if parsed.unit == "percent":
                percentage = float(parsed.quantity)
                if is_increase:
                    new_price = current_price * (1 + (percentage / 100))
                elif is_decrease:
                    new_price = max(0.0, current_price * (1 - (percentage / 100)))
                else:
                    # Default to increase if not specified
                    new_price = current_price * (1 + (percentage / 100))
                
                updated = update_item_price(parsed.item_name, new_price, reason="voice_command")
                response = (
                    f"✓ {item['name']} ka price {percentage}% {'badha' if is_increase or not is_decrease else 'kam'} diya: ₹{updated['price']:.2f}"
                    if language == "hinglish"
                    else f"✓ {item['name']} price {percentage}% {'increase' if is_increase or not is_decrease else 'decrease'} pannathu: ₹{updated['price']:.2f}"
                )
            else:
                # Absolute or delta price change
                if is_increase:
                    new_price = current_price + float(parsed.quantity)
                elif is_decrease:
                    new_price = max(0.0, current_price - float(parsed.quantity))
                else:
                    new_price = float(parsed.quantity)

                updated = update_item_price(parsed.item_name, new_price, reason="voice_command")
                response = (
                    f"✓ {item['name']} ka price update ho gaya: ₹{updated['price']}"
                    if language == "hinglish"
                    else f"✓ {item['name']} price update pannathu: ₹{updated['price']}"
                )
            return PipelineResult(
                success=True,
                response=response,
                intent="PRICE",
                db_rows=[updated],
            )
        else:
            # Just PRICE CHECK - no quantity means show current price
            response = f"{item['name']} ka current rate: ₹{item['price']}" if language == "hinglish" else f"{item['name']} current rate: ₹{item['price']}"
            return PipelineResult(
                success=True,
                response=response,
                intent="PRICE",
                db_rows=[item],
            )
    except Exception as e:
        log.error("Price check error: %s", e)
        response_map = {
            "hinglish": "Price check mein dikkat aayi",
            "tamil": "Price check vela problem"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


def _handle_quantity_update(parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Handle percentage-based or absolute quantity updates (e.g., 'dal ka quantity 10% inc karo')."""
    if not parsed.item_name:
        response_map = {
            "hinglish": "Kaunsa item? Item naam bataao.",
            "tamil": "Yaar item? Item name solgal."
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error="missing item name",
        )
    
    try:
        item = get_item(parsed.item_name)
        if not item:
            response = (
                f"❌ '{parsed.item_name}' nahi mila inventory mein"
                if language == "hinglish"
                else f"❌ '{parsed.item_name}' inventory le kanukkala"
            )
            return PipelineResult(
                success=False,
                response=response,
                error="item not found",
            )

        # If quantity provided with QUANTITY intent, it's a quantity UPDATE.
        if parsed.quantity is not None:
            from app.db.database import execute_safe_sql

            raw_l = parsed.raw_text.lower()
            current_qty = float(item.get("quantity") or 0.0)
            item_unit = item.get("unit", "piece")

            # Determine if increase or decrease
            is_increase = any(kw in raw_l for kw in ["badha", "badhao", "bdhao", "badho", "increase", "inc"])
            is_decrease = any(kw in raw_l for kw in ["kam kar", "kam karo", "kam kar do", "kam kardo", "decrease", "ghata", "dec"])

            # Check if this is a percentage-based update
            if parsed.unit == "percent":
                percentage = float(parsed.quantity)
                if is_increase:
                    new_qty = current_qty * (1 + (percentage / 100))
                elif is_decrease:
                    new_qty = max(0.0, current_qty * (1 - (percentage / 100)))
                else:
                    # Default to increase if not specified
                    new_qty = current_qty * (1 + (percentage / 100))
                
                # Update quantity directly in inventory
                execute_safe_sql(
                    "UPDATE inventory SET quantity = ? WHERE LOWER(name) = ?",
                    (new_qty, parsed.item_name.lower())
                )
                
                # Fetch updated item
                updated = get_item(parsed.item_name)
                response = (
                    f"✓ {item['name']} ka quantity {percentage}% {'badha' if is_increase or not is_decrease else 'kam'} diya: {new_qty:.1f} {item_unit}"
                    if language == "hinglish"
                    else f"✓ {item['name']} quantity {percentage}% {'increase' if is_increase or not is_decrease else 'decrease'} pannathu: {new_qty:.1f} {item_unit}"
                )
            else:
                # Absolute or delta quantity change
                if is_increase:
                    new_qty = current_qty + float(parsed.quantity)
                elif is_decrease:
                    new_qty = max(0.0, current_qty - float(parsed.quantity))
                else:
                    new_qty = float(parsed.quantity)

                execute_safe_sql(
                    "UPDATE inventory SET quantity = ? WHERE LOWER(name) = ?",
                    (new_qty, parsed.item_name.lower())
                )
                
                updated = get_item(parsed.item_name)
                response = (
                    f"✓ {item['name']} ka quantity update ho gaya: {new_qty:.1f} {item_unit}"
                    if language == "hinglish"
                    else f"✓ {item['name']} quantity update pannathu: {new_qty:.1f} {item_unit}"
                )
            return PipelineResult(
                success=True,
                response=response,
                intent="QUANTITY",
                db_rows=[updated] if updated else [item],
            )
        else:
            # Just QUANTITY CHECK - no quantity means show current quantity
            response = f"{item['name']} ka current quantity: {item.get('quantity', 0)} {item.get('unit', 'piece')}" if language == "hinglish" else f"{item['name']} current quantity: {item.get('quantity', 0)} {item.get('unit', 'piece')}"
            return PipelineResult(
                success=True,
                response=response,
                intent="QUANTITY",
                db_rows=[item],
            )
    except Exception as e:
        log.error("Quantity update error: %s", e)
        response_map = {
            "hinglish": "Quantity update mein dikkat aayi",
            "tamil": "Quantity update vela problem"
        }
        return PipelineResult(
            success=False,
            response=response_map.get(language, response_map["hinglish"]),
            error=str(e),
        )


# ---------------------------------------------------------------------------
# LLM + RAG path
# ---------------------------------------------------------------------------


def _handle_with_llm(raw_text: str, parsed: ParsedQuery, language: str = "hinglish") -> PipelineResult:
    """Full LLM pipeline: RAG retrieval → SQL → safety → execute → response."""

    # Step 1: RAG retrieval
    retriever = get_retriever()
    examples = retriever.retrieve(raw_text, top_k=RAG_TOP_K)
    examples_text = retriever.format_for_prompt(examples)

    # Step 2: SQL generation
    llm = get_llm()
    sql = llm.generate_sql(
        raw_query=raw_text,
        intent=parsed.intent,
        item=parsed.item_name,
        quantity=parsed.quantity,
        unit=parsed.unit,
        examples_text=examples_text,
    )

    if not sql:
        return PipelineResult(
            success=False,
            response=(
                "Samajh nahi aaya. Dobara boliye — e.g. 'chawal kitna bacha hai'"
            ),
            error="LLM failed to generate SQL",
        )

    # Step 3: Safety validation
    is_safe, reason = validate_sql(sql)
    if not is_safe:
        return PipelineResult(
            success=False,
            response=safe_error_hinglish(reason),
            sql=sql,
            error=reason,
        )

    # Step 4: Execute
    try:
        rows = run_safe_query(sql)
    except Exception as e:  # pragma: no cover - defensive
        log.error("SQL execution error: %s | SQL: %s", e, sql)
        return PipelineResult(
            success=False,
            response="Database mein kuch problem aayi. Dobara try karein.",
            sql=sql,
            error=str(e),
        )

    # Step 5: Generate response (in appropriate language)
    response = llm.generate_response(raw_text, sql, rows, parsed.intent, language=language)

    return PipelineResult(
        success=True,
        response=response,
        sql=sql,
        intent=parsed.intent,
        db_rows=rows,
    )


# ---------------------------------------------------------------------------
# Customer analytics helpers
# ---------------------------------------------------------------------------


def _classify_customer_query(text: str) -> Optional[str]:
    """Return a trend_type string if text matches a customer pattern, else None."""

    text_lower = text.lower()
    pattern_map = {
        "delivery_orders": r"(delivery list|kaun aayega|kal ki delivery|aaj ki delivery|delivery ready|order prepare|yaar varuvanga|evaru vastaru|ke asbe|kon yeil| डेलिवरी|डिलीवरी|kaun aayega|order prepare)",
        "rfm_analysis": r"(rfm|segment|loyal customer|best customer|top customer|vip|champion|rfm|segment|loyal customer|लॉयल|वफादार|best customer|top customer)",
        "churn_prediction": r"(churn|lost customer|wapas nahi aaya|gayab|inactive|dormant|din se nahi|churn|lost customer|wapas nahi aaya|गायब|inactive|din se nahi)",
        "customer_ltv": r"(ltv|lifetime value|kitna kamaya|total value|high value customer)",
        "loyalty_scoring": r"(loyalty score|loyalty|customer rank|rank customer|top customer)",
        "next_purchase": r"(next purchase|predict order|kab aayega|auto order|next order)",
        "visit_frequency": r"(visit frequency|kitne din mein aata|gap between visits|regular customer)",
        "cohort_retention": r"(cohort|retention|purane customer|returning customer)",
        "basket_size": r"(basket|ek baar mein kitna|items per visit|single visit)",
        "monthly_report": r"(monthly report|mahine ki report|pichle mahine ka hisab|report dikhao|महीने की रिपोर्ट)",
    }

    for trend_type, pattern in pattern_map.items():
        if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
            return trend_type
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def process(text: str, is_voice: bool = False, language: str = "hinglish") -> PipelineResult:
    """Main pipeline entry point.

    text: transcribed/typed Hinglish query
    is_voice: True if input came from ASR (applies normalization)
    Returns PipelineResult with response and metadata.
    """

    text = text.strip()
    
    # Normalize ASR output: remove fillers, normalize spacing
    text = normalize_asr_input(text, is_voice=is_voice)
    
    if not text:
        return PipelineResult(
            success=False,
            response="Kuch bola nahi gaya. Phir se boliye.",
            error="empty input",
        )

    log.info("Processing: '%s' (voice=%s)", text, is_voice)

    text_lower = text.lower()

    # CRITICAL FIX: Check trends BEFORE transliteration to preserve Hindi patterns
    # This ensures Hindi market basket queries work correctly.
    #
    # Additionally, for weather-related trend questions like
    #   "garmi bahut hai, kaunse thande drinks aur ice cream zyada bikenge"
    # we want BOTH:
    #   1) historical analytics from the trends engine, and
    #   2) a live-weather suggestion line from the WeatherSuggestions helper.
    #
    # However, for explicit "weather ke hisaab se suggestion do" style
    # questions, we *skip* the trends engine and go directly to the
    # weather suggestion helper further below.
    is_explicit_weather_suggestion = (
        ("weather" in text_lower or "mausam" in text_lower)
        and ("suggestion" in text_lower or "saman" in text_lower or "stock" in text_lower)
    )

    if _trends_pipeline is not None and not is_explicit_weather_suggestion:
        trend_type, _ = classify_trend(text)
        if trend_type and trend_type != "monthly_report":
            trend_response = _trends_pipeline.process(text, language=language)
            if trend_response:
                # For weather_trend, append a live-weather suggestion block
                # on top of the historical analytics from the trends engine.
                if trend_type == "weather_trend":
                    try:
                        weather_result = _handle_weather_recommendation(language=language)
                        extra = f"\n\n{weather_result.response}" if weather_result and weather_result.response else ""
                    except Exception as e:  # pragma: no cover - defensive
                        log.warning("Weather suggestion for weather_trend failed: %s", e)
                        extra = ""

                    return PipelineResult(
                        success=True,
                        response=trend_response + extra,
                        intent="TREND",
                        trend_type=trend_type,
                    )

                # All other trend types behave as before
                return PipelineResult(
                    success=True,
                    response=trend_response,
                    intent="TREND",
                    trend_type=trend_type,
                )

    # Step 1: NLP parsing — route to LLM parser for voice, rule-based for text
    if is_voice:
        from app.nlp.extractor import parse_voice
        parsed = parse_voice(text)  # parse_voice handles Devanagari transliteration
    else:
        # For text input with Devanagari, transliterate first
        from app.nlp.extractor import _transliterate_devanagari
        text_normalized = _transliterate_devanagari(text)
        if text_normalized != text:
            log.debug("Devanagari transliterated: '%s' → '%s'", text, text_normalized)
            text = text_normalized  # Use transliterated text for all downstream processing
        parsed = parse(text)
    log.info(
        "Intent=%s item=%s qty=%s unit=%s conf=%.2f",
        parsed.intent,
        parsed.item_name,
        parsed.quantity,
        parsed.unit,
        parsed.confidence,
    )

    # Weather recommendation queries like
    #   "aaj ke weather ke hisaab se suggestion do ki kya saman rakhna chahiye"
    # should not be treated as ADD for a fake item name. If the user explicitly
    # mentions "weather" and asks for a "suggestion" / "kya saman/stock rakhna",
    # answer via the weather suggestion engine instead of inventory ADD.
    if (
        "weather" in text_lower or "mausam" in text_lower
    ) and (
        "suggestion" in text_lower or "saman" in text_lower or "stock" in text_lower
    ):
        return _handle_weather_recommendation(language=language)

    # Step 1.5: customer analytics specific patterns (including monthly report)
    customer_trend_type = _classify_customer_query(text)
    if customer_trend_type is not None:
        db_path = str(TRENDS_DB_PATH)
        greeting = get_greeting(text)

        # Monthly report needs special date logic and PDF-friendly payload
        if customer_trend_type == "monthly_report":
            try:
                today = date.today()
                year, month = (
                    (today.year, today.month - 1)
                    if today.month > 1
                    else (today.year - 1, 12)
                )

                report_data = generate_monthly_report(db_path, year, month)

                return PipelineResult(
                    success=True,
                    response=(
                        f"Aapki {year}-{month:02d} ki report taiyaar hai! "
                        "PDF download karein."
                    ),
                    intent="REPORT",
                    trend_type="monthly_report",
                    db_rows=[report_data],
                )
            except Exception as e:  # pragma: no cover - defensive
                log.error("Monthly report generation failed: %s", e)
                return PipelineResult(
                    success=False,
                    response="Report banane mein dikkat aayi.",
                    error=str(e),
                )

        # Other customer analytics via direct DB queries
        dispatch = {
            "rfm_analysis": lambda: compute_rfm(db_path),
            "churn_prediction": lambda: predict_churn(db_path),
            "customer_ltv": lambda: compute_ltv(db_path),
            "visit_frequency": lambda: visit_frequency(db_path),
            "basket_size": lambda: basket_size_trend(db_path),
            "cohort_retention": lambda: cohort_retention(db_path),
            "next_purchase": lambda: predict_next_purchases(db_path),
            "loyalty_scoring": lambda: loyalty_scores(db_path),
            "delivery_orders": lambda: generate_delivery_orders(db_path),
        }

        fn = dispatch.get(customer_trend_type)
        if fn:
            data = fn()
            response = greeting + "\n" + format_customer_result(
                customer_trend_type, data
            )
            return PipelineResult(
                success=True,
                response=response,
                intent="TREND",
                trend_type=customer_trend_type,
            )

    # Step 2: route by intent + confidence (general inventory/cart operations)
    if parsed.intent == "CORRECTION" and parsed.item_name and parsed.quantity is not None:
        return _handle_stock_correction(parsed, language=language)

    if parsed.intent == "ADD" and parsed.item_name and parsed.confidence >= 0.4:
        return _handle_add(parsed, language=language)

    if parsed.intent == "SELL" and parsed.item_name and parsed.confidence >= 0.4:
        return _handle_sell(parsed, language=language)

    if parsed.intent == "QUERY":
        direct = _handle_query_direct(parsed, language=language)
        if direct is not None:
            return direct

    # Handle new inventory features with template SQL
    if parsed.intent == "ROLLBACK":
        return _handle_price_rollback(parsed, language=language)

    if parsed.intent == "EXPIRY":
        return _handle_expiry_check(parsed, language=language)
    
    if parsed.intent == "CATEGORY":
        return _handle_category_update(parsed, language=language)
    
    if parsed.intent == "QUANTITY" and parsed.item_name:
        return _handle_quantity_update(parsed, language=language)
    
    if parsed.intent == "PRICE" and parsed.item_name:
        return _handle_price_check(parsed, language=language)

    # Step 4: LLM fallback
    return _handle_with_llm(text, parsed, language=language)
