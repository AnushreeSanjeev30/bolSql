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

# Fuzzy matching for robustness
try:
    from rapidfuzz import fuzz
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False
    log.warning("rapidfuzz not installed. Fuzzy matching disabled.")


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
    r"\badd\b", r"\baid\b", r"\bkaro\b", r"\bkro\b",
    r"\bdaal\b", r"\bdo\b", r"\bdalo\b", r"\bdaalo\b",
    r"\benter\b", r"\blikhna\b", r"\blikho\b",
    r"\bstock\s+mein\b", r"\bstock\s+me\b",
    r"\bjama\b", r"\baaya\b", r"\baayi\b",
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
    r"\bpending\b", r"\borders\b", r"\baaj\b.*order",
    r"\bexpire\b", r"\bexpiry\b", r"\bkhatam\b.*hoga",
]

# Price and correction keywords
PRICE_KEYWORDS = [
    # Core price words + common ASR / transliteration variants
    r"\bprice\b", r"\bprais\b", r"\bpraice\b", r"\brate\b", r"\bdaam\b", r"\bkya\s+rate\b",
    # Increase / decrease verbs (Hindi + English + transliteration glitches)
    r"\bbadha\b", r"\bbadhao\b", r"\bbdhao\b", r"\bbadho\b", r"\bkam\b.*karo",
    r"\bupdate\b.*price\b", r"\bchange\b.*price\b", r"\bundo\b", r"\brollback\b",
    r"\bincrease\b", r"\bdecrease\b", r"\bset\b.*price\b",
    # Talking about things being expensive / cheap is also price intent
    r"\bmehenga\b", r"\bmehengi\b", r"\bmahenga\b", r"\bmahengi\b",
    # Hindi keywords for price changes (transliterated from Devanagari)
    r"\bvriddhi\b", r"\bvridhi\b",  # वृद्धि = growth/increase
    r"\bkamzori\b", r"\bkomzori\b",  # कमजोरी could mean decrease (weakening)
    r"\bkeet\b", r"\bkeemt\b",  # कीमत = price
    # Question-style price queries
    r"\bprice.*kya\b", r"\bprice.*kitna\b", r"\brate.*kya\b", r"\brate.*kitna\b",
    r"\bkitna.*rate\b", r"\bkitna.*price\b", r"\bkitna.*daam\b",
    r"\bprice.*hai\b", r"\brate.*hai\b", r"\bdaam.*hai\b",
]

CORRECTION_KEYWORDS = [
    r"\bcorrect\b", r"\bfix\b", r"\bupdate\b", r"\bhai\b.*correct\b",
    r"\bstock\s+count\b", r"\bmanual\b.*count",
    # Hinglish/ASR variants of "correct" (e.g., "karek", "krekt", "karrekt")
    r"\bkarek?t\b", r"\bkrekt\b", r"\bkar+ekt\b",
]

ORDER_KEYWORDS = [
    r"\border\b", r"\bordar\b", r"\bbuya\b", r"\bmangao\b",
    r"\bpending\b", r"\bdelivery\b", r"\bshipping\b",
]

ROLLBACK_KEYWORDS = [
    r"\brollback\b", r"\bunundo\b", r"\brevert\b",
    # Explicit undo words should strongly indicate rollback intent
    r"\bundo\b", r"\bundo karo\b", r"\bundo kar do\b",
    r"\bprevious\b.*price\b", r"\bphle\b.*rate\b",
    r"\bback\b.*price\b", r"\bpichle\b", r"\bpehle\b",
]

EXPIRY_KEYWORDS = [
    r"\bexpiry\b", r"\bexpire\b", r"\bexpires\b",
    r"\bkhatam\b.*hoga\b", r"\bkhatam\b.*honge\b",
    r"\bkhatam\b.*hai\b", r"\bkhatam\b.*ho.*\b",
    r"\bpurani\b", r"\bkhrab\b", r"\bsड़ा\b",
    r"\bvalidity\b", r"\bdate\b.*expiry\b",
    r"\bspoiled\b", r"\bspoil\b", r"\bstale\b",
]

CATEGORY_KEYWORDS = [
    r"\bcategory\b", r"\btype\b", r"\bmasala\b", r"\bvegetable\b",
    r"\bfruit\b", r"\bbesan\b", r"\bgrains\b", r"\bpulses\b",
]

QUANTITY_KEYWORDS = [
    r"\bquantity\b", r"\bqty\b", r"\bstock\b.*quantity\b",
    r"\bquantity\b.*inc", r"\bquantity\b.*increase", r"\bquantity\b.*dec",
    r"\bquantity\b.*decrease", r"\bquantity\b.*badha", r"\bquantity\b.*kam",
    # Hindi transliterated quantity keywords
    r"\bmatra\b", r"\bparimaan\b", r"\bporshan\b",
    # Common Hinglish phrases
    r"\bstock\b.*badha", r"\bstock\b.*increase", r"\bstock\b.*dec",
]


# ── Unit normalization map ─────────────────────────────────────────────────────

UNIT_MAP = {
    # Kilograms
    "kg": "kg", "kilo": "kg", "kilogram": "kg", "kilograms": "kg",
    "kgs": "kg", "किलो": "kg", "किलोग्राम": "kg",
    # Common Devanagari transliteration of "kg" (केजी → kejee)
    "kejee": "kg",
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
    # Common ASR transliteration glitches for "packet"
    "paiket": "packet",
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
    "aata": "atta", "aatto": "atta",
    # Rice
    "rice": "chawal", "chaawal": "chawal", "chaval": "chawal",
    "chaawal": "chawal", "chaol": "chawal",
    # Lentils
    "lentil": "dal", "daal": "dal", "lentils": "dal",
    "dahal": "dal", "dahl": "dal", "dalo": "dal", "dalon": "dal",  # plural forms
    # Oil
    "oil": "tel", "teel": "tel", "cooking oil": "tel",
    "sarso tel": "sarso tel", "mustard oil": "sarso tel",
    "refined oil": "tel", "tel": "tel",
    # Sugar
    "sugar": "chini", "shakkar": "chini",
    "shakkr": "chini", "cheeni": "chini",
    # Salt
    "salt": "namak", "namak": "namak",
    "nummak": "namak",
    # Milk (canonical: "milk" to align with cleaned inventory names)
    "milk": "milk", "dud": "milk",
    "dhudh": "milk", "doodh": "milk",
    # Tea
    "tea": "chai", "chai patti": "chai", "tea leaves": "chai",
    "chai": "chai", "chay": "chai",
    # Biscuits
    "biscuits": "biscuit", "biskut": "biscuit", "biskoot": "biscuit",
    "biscuit": "biscuit", "besuit": "biscuit", "biskit": "biscuit",
    "biscut": "biscuit",
    # Soap
    "soap": "sabun", "sabun": "sabun",
    # Turmeric
    "turmeric": "haldi", "haldi": "haldi",
    # Chilli
    "chilli": "mirchi", "chili": "mirchi", "red chilli": "mirchi",
    "lal mirchi": "mirchi", "mirch": "mirchi", "mirchi": "mirchi",
    # Mango (ASR commonly mishears as "mongos", "mangos", etc.)
    "mango": "mango", "mangos": "mango", "mongos": "mango",
    "maaango": "mango", "maango": "mango", "aam": "mango",
    "aaam": "mango",
    # Apple
    "apple": "apple", "apples": "apple", "aaple": "apple",
    "appel": "apple", "seb": "apple",
    # Potato
    "potato": "aloo", "potatoes": "aloo", "potaj": "aloo",
    "poto": "aloo", "potat": "aloo",
    # Spices
    "jeera": "jeera", "jeera": "jeera",
    "hing": "hing", "asafoetida": "hing",
    # Gram flour
    "besan": "besan", "gram flour": "besan",
    "gramflour": "besan", "bessan": "besan",
    # Coriander
    "dhania": "dhania", "cilantro": "dhania",
    # Ginger
    "ginger": "ginger", "adrak": "ginger",
    # Garlic
    "garlic": "garlic", "lehsun": "garlic", "lasan": "garlic",
    # Savory snacks (namkeen)
    "namkeen": "namkeen", "namkin": "namkeen", "salty": "namkeen",
    # Instant noodles / Maggi
    "maggi": "maggi", "maggie": "maggi", "maigee": "maggi", "megii": "maggi",
    "meggi": "maggi", "मैगी": "maggi",
}


def _normalize_item(name: str) -> str:
    """Apply alias map and basic normalization."""
    n = name.strip().lower()
    return ITEM_ALIASES.get(n, n)


def _fuzzy_match_item(text: str, candidates: list, threshold: float = 0.6) -> Optional[str]:
    """
    Fuzzy match input text against known items.
    Useful when ASR transcription slightly differs from exact item name.
    """
    if not HAS_FUZZY or not candidates:
        return None
    
    best_match = None
    best_score = 0.0
    
    text_l = text.strip().lower()
    
    for candidate in candidates:
        candidate_l = candidate.lower()
        # Token-based matching is more robust for Hinglish
        score = fuzz.token_sort_ratio(text_l, candidate_l) / 100.0
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate
    
    if best_match:
        log.debug("Fuzzy match: '%s' → '%s' (score: %.2f)", text, best_match, best_score)
    
    return best_match


def _score_intent(text: str, patterns: list) -> int:
    """Count how many intent patterns match."""
    text_l = text.lower()
    return sum(1 for p in patterns if re.search(p, text_l))


def _extract_quantity_unit(text: str) -> tuple[Optional[float], Optional[str]]:
    """
    Extract quantity and unit from text.
    Handles: '50kg', '50 kg', '50 kilo', '5.5 litre', 'ek kilo', '10%', etc.
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

    # Pattern 0: Percentage (e.g. "10%", "10 percent")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|percentage)", text_l, re.IGNORECASE)
    if m:
        qty = float(m.group(1))
        return qty, "percent"

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
    Returns best-guess item name with fuzzy fallback for unknown items.
    """
    text_l = text.lower()

    # Special handling: commands like
    #   "5 packets biscuit aur 10 pieces chocolate add karo"
    # currently end up creating a fake item "biscuit aur chocolate".
    # For now, we intentionally support only the *first* item in a
    # single command and ignore any extra "aur <qty> <item>" tail.
    #
    # We therefore truncate the text at the first "aur" that is
    # followed by another quantity (a digit). This keeps:
    #   "5 packets biscuit"  from the above example, so the item
    # extracted is just "biscuit".
    #
    # We do *not* truncate for phrases like "thoda aur atta add karo"
    # because there is no quantity after "aur" there.
    aur_match = re.search(r"\baur\b", text_l)
    if aur_match:
        tail = text_l[aur_match.end():]
        if re.search(r"\d", tail):
            text_l = text_l[:aur_match.start()]

    # Remove numbers + units
    unit_pattern = "|".join(re.escape(u) for u in sorted(UNIT_MAP.keys(), key=len, reverse=True))
    cleaned = re.sub(rf"\d+(?:\.\d+)?\s*(?:{unit_pattern})?\b", "", text_l)

    # Remove intent words and common fillers (Hindi + English helpers)
    fillers = [
        r"\badd\b", r"\baid\b", r"\bkaro\b", r"\bkro\b", r"\bdaal\b", r"\bdo\b",  # Note: dalo/dalon are item names, not removed here
        r"\bbecho\b", r"\bbecha\b", r"\bdiya\b", r"\bgaya\b",
        r"\bkitna\b", r"\bkitni\b", r"\bkitne\b", r"\bbacha\b", r"\bhai\b",
        r"\bcheck\b", r"\bdekhna\b", r"\bbatao\b", r"\benter\b",
        r"\bstock\b", r"\bmein\b", r"\bme\b", r"\bka\b", r"\bki\b", r"\bkee\b",  # Hindi possessives: ki/ kee
        r"\bke\b", r"\bkya\b", r"\blist\b", r"\bsab\b",
        r"\bsabhi\b", r"\bavailable\b", r"\bbaaki\b", r"\bdikha\b",
        r"\bdikhao\b", r"\bshow\b", r"\baaj\b", r"\bkal\b", r"\bpachas\b",
        r"\bpahuncha\b", r"\baaya\b", r"\bnikala\b", r"\bnikali\b",
        r"\bbika\b", r"\bbiki\b", r"\bgayi\b", r"\bgaye\b",
        r"\bcustomer\b", r"\bko\b", r"\bitem\b", r"\bsaman\b",
        r"\bkaunsa\b", r"\bwala\b", r"\bkam\b",
        r"\bprice\b", r"\bprais\b", r"\bpraice\b", r"\brate\b", r"\bdaam\b", r"\brupaye\b", r"\brupay\b",
        r"\bkeemt\b", r"\bkeet\b",  # कीमत = price (Hindi transliterated)
        r"\bvriddhi\b", r"\bvridhi\b",  # वृद्धि = increase/growth
        r"\bkre\b", r"\bkaren\b",  # करें/करे = do (Hindi verb)
        r"\bbadha\b", r"\bbadhao\b", r"\bbdhao\b", r"\bbadho\b", r"\bbadhado\b", r"\bincrease\b", r"\bdecrease\b", r"\binc\b", r"\bdec\b",
        r"\bupdate\b", r"\bchange\b", r"\bset\b", r"\brollback\b", r"\bundo\b",
        r"\bkar\b", r"\bkarna\b", r"\bkar do\b",
        r"\bquantity\b", r"\bqty\b", r"\bqts\b",  # Quantity keywords should be removed from item name
        r"\bmatra\b", r"\bparimaan\b", r"\bporshan\b",  # Hindi: quantity words
        # Generic unit words should not be part of item names
        r"\bunit\b", r"\bunits\b",
        # Category / percentage price-change helpers
        r"\bcategory\b", r"\btype\b", r"\bmehenga\b", r"\bmehengi\b", r"\bmahenga\b", r"\bmahengi\b",
        r"%",
        # Quantifiers like "saari"/"sara" (all) should not be part of item/category names
        r"\bsaari\b", r"\bsari\b", r"\bsaare\b", r"\bsaarey\b", r"\bsaara\b", r"\bsara\b", r"\bpura\b", r"\bpoora\b",
        # High-level words that describe transactions, not items
        r"\bsale\b", r"\border\b", r"\borders\b", r"\bordar\b", r"\bpending\b",
        # English glue words that should not be part of item name
        r"\bthe\b", r"\bof\b", r"\bto\b", r"\bfor\b", r"\bon\b",
        r"\bcan\b", r"\byou\b", r"\baap\b", r"\bplease\b", r"\bplz\b",
        r"\brupees?\b", r"\brs\.?\b",
    ]
    for f in fillers:
        cleaned = re.sub(f, " ", cleaned)

    # Collapse spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Remove leading/trailing punctuation
    cleaned = cleaned.strip(".,?!।-")

    # Post-fix for stock-correction style phrases like
    #   "dal ka stock 40kg hai, correct karo"
    # After filler-stripping this can leave
    #   "dal , correct"
    # which then flows through as the item name.
    # Trim any trailing ", correct" / " correct" chunk so we
    # get a clean canonical item ("dal").
    cleaned = re.sub(r",?\s*correct\b.*$", "", cleaned).strip()

    if not cleaned:
        return None

    item = _normalize_item(cleaned)
    
    # Try fuzzy matching against database items if we don't recognize it
    if item and item not in ITEM_ALIASES.values():
        try:
            from app.db.database import get_all_items
            db_items = get_all_items()
            if db_items:
                db_item_names = [row['name'].lower() for row in db_items]
                fuzzy_match = _fuzzy_match_item(item, db_item_names, threshold=0.65)
                if fuzzy_match:
                    # Defensive cleanup: if the DB name itself still
                    # carries artefacts from an old stock-correction
                    # bug (e.g. "dal , correct"), trim that suffix so
                    # NLP returns a clean canonical item name.
                    cleaned_fuzzy = re.sub(r",?\s*correct\b.*$", "", fuzzy_match.lower()).strip()
                    if cleaned_fuzzy:
                        normalized = _normalize_item(cleaned_fuzzy)
                        log.debug("Fuzzy matched item: '%s' → '%s' (cleaned from '%s')", item, normalized, fuzzy_match)
                        return normalized
                    log.debug("Fuzzy matched item (raw DB name): '%s' → '%s'", item, fuzzy_match)
                    return fuzzy_match
        except Exception as e:
            log.debug("Fuzzy matching against DB failed: %s", e)
    
    return item


def parse(text: str) -> ParsedQuery:
    """
    Main entry point. Parse raw Hinglish text into structured ParsedQuery.
    """
    text = text.strip()
    if not text:
        return ParsedQuery(intent="UNKNOWN", raw_text=text)

    # If the text contains Devanagari characters (Hindi script),
    # transliterate it first so the same Hinglish rules apply to
    # both voice and typed Hindi input.
    if any("\u0900" <= ch <= "\u097F" for ch in text):
        try:
            text = _transliterate_devanagari(text)
        except Exception:
            # Fail-soft: if transliteration breaks, continue with raw text
            pass

    log.debug("NLP parsing: '%s'", text)

    # Score intents
    add_score = _score_intent(text, ADD_KEYWORDS)
    sell_score = _score_intent(text, SELL_KEYWORDS)
    query_score = _score_intent(text, QUERY_KEYWORDS)
    price_score = _score_intent(text, PRICE_KEYWORDS)
    correction_score = _score_intent(text, CORRECTION_KEYWORDS)
    order_score = _score_intent(text, ORDER_KEYWORDS)
    rollback_score = _score_intent(text, ROLLBACK_KEYWORDS)
    expiry_score = _score_intent(text, EXPIRY_KEYWORDS)
    category_score = _score_intent(text, CATEGORY_KEYWORDS)
    quantity_score = _score_intent(text, QUANTITY_KEYWORDS)

    scores = {
        "ADD": add_score,
        "SELL": sell_score,
        "QUERY": query_score,
        "PRICE": price_score,
        "CORRECTION": correction_score,
        "ORDER": order_score,
        "ROLLBACK": rollback_score,
        "EXPIRY": expiry_score,
        "CATEGORY": category_score,
        "QUANTITY": quantity_score,
    }

    # If PRICE keywords found, strongly prefer PRICE over basic stock intents
    if price_score > 0:
        scores["ADD"] = max(0, scores["ADD"] - price_score)
        scores["SELL"] = max(0, scores["SELL"] - price_score)

        # If rollback/undo words are present, this is almost certainly a
        # ROLLBACK intent rather than a fresh PRICE update. Boost ROLLBACK
        # so it can win against the generic PRICE patterns.
        if rollback_score > 0:
            scores["ROLLBACK"] += rollback_score * 2
            scores["PRICE"] = max(0, scores["PRICE"] - rollback_score)
    
    # If QUANTITY keywords found, strongly prefer QUANTITY over ADD/SELL
    if quantity_score > 0:
        scores["ADD"] = max(0, scores["ADD"] - quantity_score)
        scores["SELL"] = max(0, scores["SELL"] - quantity_score)

    text_l = text.lower()

    # If QUANTITY keywords are present and we have a percentage, strongly prefer QUANTITY
    # E.g., "dal ka quantity 10% inc karo" → QUANTITY (not ADD)
    if quantity_score > 0:
        has_percentage = any(kw in text_l for kw in ["%", "percent", "percentage"])
        if has_percentage:
            # Boost QUANTITY when percentage is detected
            scores["QUANTITY"] += 3
            scores["ADD"] = max(0, scores["ADD"] - 2)
    
    # If CATEGORY keywords are present, downweight ADD/SELL and
    # favour CATEGORY when combined with percentage /
    # "mahenga" style words (category price updates).
    if category_score > 0:
        scores["ADD"] = max(0, scores["ADD"] - category_score)
        scores["SELL"] = max(0, scores["SELL"] - category_score)
        # CRITICAL: Only boost CATEGORY if we don't have PRICE keywords + percentage
        # E.g., "spices 10% badha" → CATEGORY, but "dal ka price 10% badha" → PRICE
        has_percentage = any(kw in text_l for kw in ["%", "percent", "percentage"])
        has_price_keyword = price_score > 0
        if has_percentage and not has_price_keyword:
            # Give CATEGORY a bigger boost so it wins ties against PRICE
            scores["CATEGORY"] += 2
        elif has_percentage and has_price_keyword:
            # If both PRICE and CATEGORY present with percentage, default is item-level PRICE.
            # However, when the user explicitly talks about a "category" update (e.g.
            #   "saari milk category 10% mehengi karo") we still want CATEGORY intent
            # to win, otherwise the system tries to treat it as a single item price
            # change and fails with "'<item>' nahi mila inventory mein".
            explicit_category_words = [
                "category", "type", "masala", "spices", "grains", "pulses",
                "vegetable", "vegetables", "fruit", "fruits", "dairy",
            ]
            if any(kw in text_l for kw in explicit_category_words):
                # Small boost so CATEGORY can beat PRICE when both apply
                scores["CATEGORY"] += 3
            else:
                # No explicit category word – slightly down-weight CATEGORY so PRICE wins
                scores["CATEGORY"] = max(0, scores["CATEGORY"] - 1)

    # Queries with "dikhao/dikha/show" are almost always lookup,
    # not stock movement. Boost QUERY so it wins ties against SELL.
    if any(w in text_l for w in ["dikhao", "dikha", "show"]):
        scores["QUERY"] += 2

    # Sentences like "dal ka stock 30 kg hai" or
    # "दाल का स्टॉक 30 केजी है" are usually stock CORRECTION,
    # not additive restock. When we see 'stock' + a number and
    # 'hai', prefer CORRECTION over ADD/SELL.
    if ("stock" in text_l or "stok" in text_l) and "hai" in text_l:
        if re.search(r"\b\d+(?:\.\d+)?\b", text_l):
            scores["CORRECTION"] += 3
            scores["ADD"] = max(0, scores["ADD"] - 2)
            scores["SELL"] = max(0, scores["SELL"] - 1)
    
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


# ── Voice-specific LLM parser ──────────────────────────────────────────────────

import json
import re as regex

_groq = None

# Devanagari basic transliteration WITHOUT conflicting mappings
DEVANAGARI_VOWELS = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
}

# Vowel diacritics/matras (modifiers on consonants)
DEVANAGARI_MATRAS = {
    'ा': 'a',   # आ  
    'ि': 'i',   # इ  
    'ी': 'ee',  # ई  
    'ु': 'u',   # उ  
    'ू': 'oo',  # ऊ  
    'ृ': 'ri',  # ऋ  
    'े': 'e',   # ए  
    'ै': 'ai',  # ऐ  
    'ो': 'o',   # ओ  
    'ौ': 'au',  # औ  
}

DEVANAGARI_CONSONANTS = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
}

DEVANAGARI_SPECIAL = {
    '्': '',  # Halant (virama) - remove
    'ँ': 'n',  # Anusvara
    'ः': 'h',  # Visarga
    'ॐ': 'om',
}

# Combined mapping for transliteration
DEVANAGARI_MAP = {**DEVANAGARI_VOWELS, **DEVANAGARI_MATRAS, **DEVANAGARI_CONSONANTS, **DEVANAGARI_SPECIAL}

# Item-specific mapping (for common food items only)
ITEM_NAME_MAP = {
    'पोटोज': 'potaj', 'पोटो': 'poto', 'आलू': 'aloo', 'आलो': 'aalo',
    'मंगोज': 'mangoj', 'मंगो': 'mango', 'आम': 'aam',
    'एप्पल': 'apple', 'सेब': 'seb',
    'दूध': 'doodh', 'चाय': 'chai',
    'चावल': 'chawal', 'दाल': 'dal', 'अता': 'atta', 'आटा': 'atta',
    'तेल': 'tel', 'नमक': 'namak', 'चीनी': 'chini',
    'प्याज': 'pyaj', 'लहसुन': 'lahsun',
}



def _transliterate_devanagari(text: str) -> str:
    """
    Convert Devanagari script to transliteration intelligently.
    * First applies full-word item name mappings (most accurate)
    * Then character-by-character transliteration
    * Removes standalone consonant clusters and noise
    * Finally removes remaining non-Latin characters
    
    Example: "मंगोज 5 किलो ऐड करो" → "mangoj 5 kilo add karo"
    Example: "5 क एप्पल ऐड करो" → "5 apple add karo"
    Example: "5 कस एप्पल ऐड करो" → "5 apple add karo"
    """
    result = text
    
    # Step 1: Replace full item names (highest priority)
    for devanagari_item, transliterated in ITEM_NAME_MAP.items():
        result = result.replace(devanagari_item, transliterated)
    
    # Step 2: Character-by-character transliteration
    transliterated_chars = []
    for char in result:
        if char in DEVANAGARI_MAP:
            transliterated_chars.append(DEVANAGARI_MAP[char])
        elif char in '0123456789 .,!?':
            transliterated_chars.append(char)
        elif ord(char) < 128:  # Already ASCII
            transliterated_chars.append(char)
        # else: skip unknown Devanagari characters
    
    result = ''.join(transliterated_chars)
    
    # Step 3: Remove standalone consonant clusters (noise from stray Devanagari)
    # Remove: single consonants (k, s, etc), common clusters (ks, dh, ph, th, sh, ch, etc)
    # when they appear as standalone words
    result = regex.sub(
        r'\b([bdfghjklmnpqrstvwxyz]{1,3})\b',  # 1-3 consonants without vowels
        '',
        result,
        flags=regex.IGNORECASE
    )
    
    # Step 4: Clean up spacing and remove artifacts
    result = regex.sub(r'\s+', ' ', result).strip()
    
    return result


def _get_groq():
    """Lazy-load Groq client."""
    global _groq
    if _groq is None:
        try:
            from groq import Groq
            import os
            _groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        except Exception as e:
            log.warning("Groq initialization failed: %s", e)
            _groq = False  # Sentinel to avoid retrying
    return _groq if _groq is not False else None


def parse_voice(text: str) -> ParsedQuery:
    """
    LLM-based parser for VOICE input only.
    Handles Hinglish naturally with Sarvam codemix — supports Devanagari input.
    Falls back to rule-based parse() if LLM fails.
    
    Args:
        text: Transcribed voice input (from Sarvam codemix, may contain Devanagari)
    
    Returns:
        ParsedQuery with intent, item_name, quantity, unit
    """
    # Step 1: Convert Devanagari to transliteration
    text_transliterated = _transliterate_devanagari(text)
    log.info("Voice input transliterated: '%s' → '%s'", text, text_transliterated)
    
    client = _get_groq()
    if not client:
        log.warning("Voice LLM parser unavailable, using rule-based fallback")
        return parse(text_transliterated)

    prompt = f"""You are parsing a Hinglish kirana store voice command.
Raw input (may have Devanagari): "{text}"
Transliterated: "{text_transliterated}"

Rules:
- Extract item name, quantity, and unit from the transliterated text
- Strip command words: kro, kar, karo, karna, dena, chahiye, please, na, haan, aro, aur, par, ek, do
- Map all common items to standard names:
  potaj/poto/aloo/aalo=potato, mangoj/mango/aam=mango, apple/seb=apple,
  doodh=milk, chawal=rice, atta=flour, dal=lentils, tel=oil,
  namak=salt, chini=sugar, sabun=soap, chai=tea, biscuit=biscuit
- intent: ADD | SELL | QUERY
- quantity: number (e.g., 5, 100) or null
- unit: kg | litre | piece | packet | gm | ml or null

Return ONLY valid JSON:
{{"intent": "ADD", "item_name": "potato", "quantity": 5.0, "unit": "kg"}}

Examples:
- "potaj 5 kg add karo" → {{"intent": "ADD", "item_name": "potato", "quantity": 5.0, "unit": "kg"}}
- "mangoj add" → {{"intent": "ADD", "item_name": "mango", "quantity": null, "unit": null}}
- "doodh kitna hai" → {{"intent": "QUERY", "item_name": "milk", "quantity": null, "unit": null}}
- "apple 2 kg sell kro" → {{"intent": "SELL", "item_name": "apple", "quantity": 2.0, "unit": "kg"}}"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0,
        )
        content = resp.choices[0].message.content.strip()
        
        # Extract JSON from response (in case model adds extra text)
        json_match = regex.search(r'\{.*\}', content, regex.DOTALL)
        if not json_match:
            raise ValueError("No JSON found in response")
        
        data = json.loads(json_match.group())
        
        return ParsedQuery(
            intent=data.get("intent", "QUERY").upper(),
            item_name=data.get("item_name"),
            quantity=data.get("quantity"),
            unit=data.get("unit"),
            raw_text=text,
            confidence=0.95,  # LLM parse = high confidence
        )
    except Exception as e:
        log.warning("Voice LLM parse failed ('%s'), falling back to rule-based: %s", text, e)
        return parse(text_transliterated)
