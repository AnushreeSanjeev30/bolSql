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
)

from app.trends import TrendsPipeline
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
    """Direct ADD: no LLM needed when NLP extracted enough info."""
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

    qty = parsed.quantity or 1.0
    unit = parsed.unit or "piece"

    try:
        row = upsert_item(parsed.item_name, qty, unit)
        if language == "tamil":
            response = f"✓ {qty} {unit} {parsed.item_name} successfully add pannathu. Total {row['quantity']} {row['unit']} irukku."
        else:
            response = f"✓ {qty} {unit} {parsed.item_name} add ho gaya. Ab total {row['quantity']} {row['unit']} hai."
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


def _handle_query_direct(parsed: ParsedQuery, language: str = "hinglish") -> Optional[PipelineResult]:
    """Handle simple QUERY directly from DB (no LLM needed).

    Returns PipelineResult if handled, None if LLM fallback needed.
    """
    item = parsed.item_name
    raw_lower = parsed.raw_text.lower()
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
        qty = row["quantity"]
        unit = row["unit"]
        name = row["name"]
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
        from app.db.database import rollback_item_price
        item = rollback_item_price(parsed.item_name)
        if language == "tamil":
            response = f"✓ {parsed.item_name.title()} price rollback pannathu: ₹{item['price']}"
        else:
            response = f"✓ {parsed.item_name.title()} ka price rollback ho gaya: ₹{item['price']}"
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
        category = parsed.item_name
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

            is_increase = any(kw in raw_l for kw in ["badha", "badhao", "increase"])
            is_decrease = any(kw in raw_l for kw in ["kam kar", "kam karo", "kam kar do", "kam kardo", "decrease", "ghata"])

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

    # CRITICAL FIX: Check trends BEFORE transliteration to preserve Hindi patterns
    # This ensures Hindi market basket queries work correctly
    if _trends_pipeline is not None and _trends_pipeline.is_trend_query(text):
        trend_response = _trends_pipeline.process(text, language=language)
        if trend_response:
            return PipelineResult(
                success=True,
                response=trend_response,
                intent="TREND",
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
    
    if parsed.intent == "PRICE" and parsed.item_name:
        return _handle_price_check(parsed, language=language)

    # Step 4: LLM fallback
    return _handle_with_llm(text, parsed, language=language)
