"""
app/nlp/extractor.py
Hinglish NLP Layer — intent + entity extraction.
Rule-based first (fast), LLM fallback only if needed.
Handles real-world messy Hinglish input.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from logger import get_logger

log = get_logger("nlp")


@dataclass
class ParsedQuery:
    intent: str                          # ADD | SELL | QUERY | UNKNOWN
    item_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    raw_text: str = ""
    confidence: float = 0.0
    extras: dict = field(default_factory=dict)


# ── Intent keyword maps ────────────────────────────────────────────────────────

ADD_KEYWORDS = [
    r"\badd\b", r"\bdaal\b", r"\bdo\b", r"\bdalo\b", r"\bdaalo\b",
    r"\benter\b", r"\blikhna\b", r"\blikho\b",
    r"\bstock\s+mein\b", r"\bstock\s+me\b",
    r"\bjama\b", r"\bkaro\b.*\badd\b", r"\baaya\b", r"\baayi\b",
    r"\bpahuncha\b", r"\brestock\b", r"\bnaya\b.*\bstock\b",
    r"\bkhareeda\b", r"\bkharida\b", r"\bkharidi\b",
    r"\bmaanga\b", r"\bmangvaya\b",
]

SELL_KEYWORDS = [
    r"\bbecha\b", r"\bbechi\b", r"\bbecho\b",
    r"\bdiya\b", r"\bdiye\b", r"\bde\s+diya\b",
    r"\bgaya\b", r"\bgayi\b", r"\bgaye\b",
    r"\bnikala\b", r"\bnikali\b",
    r"\bsale\b", r"\bbika\b", r"\bbiki\b",
    r"\bkhatam\b.*\bkaro\b", r"\bgharcha\b",
    r"\bbechan\b", r"\bbechna\b",
]

QUERY_KEYWORDS = [
    r"\bkitna\b", r"\bkitni\b", r"\bkitne\b",
    r"\bkya\s+hai\b", r"\bcheck\b", r"\bdekhna\b", r"\bdekho\b",
    r"\bbatao\b", r"\bbata\b", r"\bdikhao\b",
    r"\bstock\s+kya\b", r"\bbacha\s+hai\b", r"\bbaaki\b",
    r"\blist\b", r"\bsab\b", r"\bsabhi\b",
    r"\bkam\b.*\bstock\b", r"\blow\b.*\bstock\b",
    r"\bbachela\b", r"\bbachela\b", r"\bbachi\b.*\bhai\b",
    r"\bavailable\b", r"\bhain\b", r"\bhai\b",
    r"\btotal\b", r"\bcount\b", r"\bsummary\b",
]


# ── Unit normalization map ─────────────────────────────────────────────────────

UNIT_MAP = {
    # Kilograms
    "kg": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
    "kgs": "kg", "किलो": "kg", "किलोग्राम": "kg",
    # Litres
    "litre": "litre", "liter": "litre", "litres": "litre", "liters": "litre",
    "l": "litre", "lt": "litre", "ltr": "litre", "लीटर": "litre",
    # Pieces
    "piece": "piece", "pieces": "piece", "pcs": "piece", "pc": "piece",
    "nug": "piece", "number": "piece", "nos": "piece", "no": "piece",
    "नग": "piece", "नंबर": "piece",
    # Packets
    "packet": "packet", "packets": "packet", "pack": "packet",
    "pkt": "packet", "pouch": "packet", "pouches": "packet",
    "पैकेट": "packet",
    # Dozen
    "dozen": "dozen", "doz": "dozen", "दर्जन": "dozen",
    # Gram
    "gram": "gram", "grams": "gram", "g": "gram", "gm": "gram",
    "ग्राम": "gram",
    # Generic fallbacks
    "bottle": "litre", "bottles": "litre",
    "bag": "packet", "bags": "packet",
    "box": "packet", "boxes": "packet",
}

# ── Item name aliases (Hinglish variants → canonical) ─────────────────────────

ITEM_ALIASES = {
    # Wheat flour
    "aata": "atta", "aatta": "atta", "wheat flour": "atta", "maida": "maida",
    # Rice
    "rice": "chawal", "chaawal": "chawal", "chaval": "chawal",
    # Lentils
    "lentil": "dal", "daal": "dal", "lentils": "dal",
    # Oil
    "oil": "tel", "teel": "tel", "cooking oil": "tel",
    "sarso tel": "sarso tel", "mustard oil": "sarso tel",
    "refined oil": "tel",
    # Sugar
    "sugar": "chini", "shakkar": "chini",
    # Salt
    "salt": "namak",
    # Milk
    "milk": "doodh", "dud": "doodh",
    # Tea
    "tea": "chai", "chai patti": "chai", "tea leaves": "chai",
    # Biscuits
    "biscuits": "biscuit", "biskut": "biscuit", "biskoot": "biscuit",
    # Soap
    "soap": "sabun",
    # Turmeric
    "turmeric": "haldi",
    # Chilli
    "chilli": "mirchi", "chili": "mirchi", "red chilli": "mirchi",
    "lal mirchi": "mirchi",
}


def _normalize_item(name: str) -> str:
    """Apply alias map and basic normalization."""
    n = name.strip().lower()
    return ITEM_ALIASES.get(n, n)


def _score_intent(text: str, patterns: list) -> int:
    """Count how many intent patterns match."""
    text_l = text.lower()
    return sum(1 for p in patterns if re.search(p, text_l))


def _extract_quantity_unit(text: str) -> tuple[Optional[float], Optional[str]]:
    """
    Extract quantity and unit from text.
    Handles: '50kg', '50 kg', '50 kilo', '5.5 litre', 'ek kilo', etc.
    """
    text_l = text.lower()

    # Word number map (Hinglish)
    word_nums = {
        "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
        "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "bees": 20, "tees": 30, "pachas": 50, "sou": 100,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "hundred": 100,
    }

    # Build unit pattern
    unit_pattern = "|".join(re.escape(u) for u in sorted(UNIT_MAP.keys(), key=len, reverse=True))

    # Pattern 1: number + optional space + unit (e.g. "50kg", "5 kilo")
    m = re.search(
        rf"(\d+(?:\.\d+)?)\s*({unit_pattern})\b",
        text_l
    )
    if m:
        qty = float(m.group(1))
        unit = UNIT_MAP.get(m.group(2), m.group(2))
        return qty, unit

    # Pattern 2: word number + unit (e.g. "paanch kilo")
    for word, num in word_nums.items():
        m = re.search(rf"\b{word}\s+({unit_pattern})\b", text_l)
        if m:
            unit = UNIT_MAP.get(m.group(1), m.group(1))
            return float(num), unit

    # Pattern 3: bare number (no unit) — treat as pieces
    m = re.search(r"\b(\d+(?:\.\d+)?)\b", text)
    if m:
        return float(m.group(1)), "piece"

    return None, None


def _extract_item_name(text: str, qty: Optional[float], unit: Optional[str]) -> Optional[str]:
    """
    Extract item name after removing numbers, units, intent words, filler.
    Returns best-guess item name.
    """
    text_l = text.lower()

    # Remove numbers + units
    unit_pattern = "|".join(re.escape(u) for u in sorted(UNIT_MAP.keys(), key=len, reverse=True))
    cleaned = re.sub(rf"\d+(?:\.\d+)?\s*(?:{unit_pattern})?\b", "", text_l)

    # Remove intent words and common fillers
    fillers = [
        r"\badd\b", r"\bkaro\b", r"\bdaal\b", r"\bdalo\b", r"\bdo\b",
        r"\bbecho\b", r"\bbecha\b", r"\bdiya\b", r"\bgaya\b",
        r"\bkitna\b", r"\bkitni\b", r"\bbacha\b", r"\bhai\b",
        r"\bcheck\b", r"\bdekhna\b", r"\bbatao\b", r"\benter\b",
        r"\bstock\b", r"\bmein\b", r"\bme\b", r"\bka\b", r"\bki\b",
        r"\bke\b", r"\bkya\b", r"\blist\b", r"\bsab\b",
        r"\bsabhi\b", r"\bavailable\b", r"\bbaaki\b", r"\bdikha\b",
        r"\bdikhao\b", r"\baaj\b", r"\bkal\b", r"\bpachas\b",
        r"\bpahuncha\b", r"\baaya\b", r"\bnikala\b", r"\bnikali\b",
        r"\bbika\b", r"\bbiki\b", r"\bgayi\b", r"\bgaye\b",
        r"\bcustomer\b", r"\bko\b", r"\bitem\b", r"\bsaman\b",
        r"\bkaunsa\b", r"\bwala\b", r"\bkam\b",
    ]
    for f in fillers:
        cleaned = re.sub(f, " ", cleaned)

    # Collapse spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove leading/trailing punctuation
    cleaned = cleaned.strip(".,?!।-")

    if not cleaned:
        return None

    return _normalize_item(cleaned)


def parse(text: str) -> ParsedQuery:
    """
    Main entry point. Parse raw Hinglish text into structured ParsedQuery.
    """
    text = text.strip()
    if not text:
        return ParsedQuery(intent="UNKNOWN", raw_text=text)

    log.debug("NLP parsing: '%s'", text)

    # Score intents
    add_score = _score_intent(text, ADD_KEYWORDS)
    sell_score = _score_intent(text, SELL_KEYWORDS)
    query_score = _score_intent(text, QUERY_KEYWORDS)

    scores = {"ADD": add_score, "SELL": sell_score, "QUERY": query_score}
    intent = max(scores, key=scores.get)
    max_score = scores[intent]

    # If all zero, default to QUERY
    if max_score == 0:
        intent = "QUERY"
        confidence = 0.3
    else:
        total = sum(scores.values()) or 1
        confidence = max_score / total

    # Extract quantity + unit
    quantity, unit = _extract_quantity_unit(text)

    # Extract item name
    item_name = _extract_item_name(text, quantity, unit)

    result = ParsedQuery(
        intent=intent,
        item_name=item_name,
        quantity=quantity,
        unit=unit,
        raw_text=text,
        confidence=confidence,
    )
    log.debug("NLP result: %s", result)
    return result
