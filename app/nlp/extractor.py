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
    "aata": "atta", "aatto": "atta",
    # Rice
    "rice": "chawal", "chaawal": "chawal", "chaval": "chawal",
    "chaawal": "chawal", "chaol": "chawal",
    # Lentils
    "lentil": "dal", "daal": "dal", "lentils": "dal",
    "dahal": "dal", "dahl": "dal",
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
    # Milk
    "milk": "doodh", "dud": "doodh",
    "dhudh": "doodh", "doodh": "doodh",
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
    Returns best-guess item name with fuzzy fallback for unknown items.
    """
    text_l = text.lower()

    # Remove numbers + units
    unit_pattern = "|".join(re.escape(u) for u in sorted(UNIT_MAP.keys(), key=len, reverse=True))
    cleaned = re.sub(rf"\d+(?:\.\d+)?\s*(?:{unit_pattern})?\b", "", text_l)

    # Remove intent words and common fillers
    fillers = [
        r"\badd\b", r"\baid\b", r"\bkaro\b", r"\bkro\b", r"\bdaal\b", r"\bdalo\b", r"\bdo\b",
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
                    log.debug("Fuzzy matched item: '%s' → '%s' (from DB)", item, fuzzy_match)
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
