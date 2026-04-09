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


def _handle_add(parsed: ParsedQuery) -> PipelineResult:
    """Direct ADD: no LLM needed when NLP extracted enough info."""
    if not parsed.item_name:
        return PipelineResult(
            success=False,
            response="Kaunsa item add karna hai? Dobara boliye.",
            error="item_name missing",
        )

    qty = parsed.quantity or 1.0
    unit = parsed.unit or "piece"

    try:
        row = upsert_item(parsed.item_name, qty, unit)
        response = (
            f"✓ {qty} {unit} {parsed.item_name} add ho gaya. "
            f"Ab total {row['quantity']} {row['unit']} hai."
        )
        return PipelineResult(
            success=True,
            response=response,
            intent="ADD",
            db_rows=[row],
        )
    except Exception as e:  # pragma: no cover - defensive
        log.error("ADD failed: %s", e)
        return PipelineResult(
            success=False,
            response=f"Add karne mein problem aayi: {e}",
            error=str(e),
        )


def _handle_sell(parsed: ParsedQuery) -> PipelineResult:
    """Direct SELL: no LLM needed when NLP extracted enough info."""
    if not parsed.item_name:
        return PipelineResult(
            success=False,
            response="Kaunsa item becha? Dobara boliye.",
            error="item_name missing",
        )

    qty = parsed.quantity or 1.0

    try:
        row = sell_item(parsed.item_name, qty)
        response = (
            f"✓ {qty} {row['unit']} {parsed.item_name} ka sale record ho gaya. "
            f"Ab {row['quantity']} {row['unit']} bacha hai."
        )
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
        return PipelineResult(
            success=False,
            response=f"Sale record karne mein problem: {e}",
            error=str(e),
        )


def _handle_query_direct(parsed: ParsedQuery) -> Optional[PipelineResult]:
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
            return PipelineResult(success=True, response="Sab badhiya hai! Koi bhi saman kam nahi hai.", intent="QUERY")
        
        lines = [f"  • {r['name']}: {r['quantity']} {r['unit']}" for r in low_stock]
        response = "⚠️ Yeh saman kam hai:\n" + "\n".join(lines)
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
            return PipelineResult(
                success=True,
                response="Inventory khaali hai. Kuch add karo pehle.",
                intent="QUERY",
                db_rows=[],
            )

        lines = [f"  • {r['name']}: {r['quantity']} {r['unit']}" for r in rows]
        response = "📦 Aapka poora stock:\n" + "\n".join(lines)
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
            response = f"⚠️  {name} ka stock khatam ho gaya hai! Restock karo."
        elif qty < 5:
            response = f"⚠️  {name} kam bacha hai — sirf {qty} {unit}."
        else:
            response = f"Aapke paas {qty} {unit} {name} bacha hai."
        return PipelineResult(
            success=True,
            response=response,
            intent="QUERY",
            db_rows=[row],
        )

    # Item not found directly — let LLM try
    return None


# ---------------------------------------------------------------------------
# LLM + RAG path
# ---------------------------------------------------------------------------


def _handle_with_llm(raw_text: str, parsed: ParsedQuery) -> PipelineResult:
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

    # Step 5: Generate Hinglish response
    response = llm.generate_response(raw_text, sql, rows, parsed.intent)

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


def process(text: str, is_voice: bool = False) -> PipelineResult:
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
        trend_response = _trends_pipeline.process(text)
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
        return _handle_add(parsed)

    if parsed.intent == "SELL" and parsed.item_name and parsed.confidence >= 0.4:
        return _handle_sell(parsed)

    if parsed.intent == "QUERY":
        direct = _handle_query_direct(parsed)
        if direct is not None:
            return direct

    # Step 4: LLM fallback
    return _handle_with_llm(text, parsed)
