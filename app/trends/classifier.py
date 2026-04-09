"""
Trend Intent Classifier
Maps Hinglish queries to the correct trend type + parameters.
This slots into your existing NLP pipeline as a pre-check.
"""

import re
from typing import Tuple, Optional


# ─────────────────────────────────────────────────────────────────────────────
# PATTERN TABLE
# Each entry: (regex pattern, trend_type, param_extractor_fn)
# ─────────────────────────────────────────────────────────────────────────────

def _days(m) -> dict:
    """Extract number of days from match group 1."""
    try:
        return {"days": int(m.group(1))}
    except Exception:
        return {}


def _item(m) -> dict:
    try:
        return {"item_name": m.group(1).strip()}
    except Exception:
        return {}


def _season(m) -> dict:
    raw = m.group(1).lower()
    mapping = {
        "baarish": "rain", "rain": "rain", "barsat": "rain",
        "garmi": "summer", "summer": "summer", "garam": "summer",
        "sardi": "winter", "winter": "winter", "thand": "winter",
        "holi": "holi", "diwali": "diwali",
    }
    return {"season": mapping.get(raw, raw)}


def _festival(m) -> dict:
    raw = m.group(1).lower().strip()
    return {"festival": raw}


def _customer(m) -> dict:
    try:
        return {"customer_id": m.group(1).strip()}
    except Exception:
        return {}


TREND_PATTERNS = [
    # 0. Monthly Report  ← checked FIRST so "monthly report" never reaches LLM
    (r"monthly\s*report",                          "monthly_report", lambda m: {}),
    (r"mahine\s*(?:ka)?\s*report",                 "monthly_report", lambda m: {}),
    (r"report\s*(?:banao|dikhao|do|generate|show|dikh)", "monthly_report", lambda m: {}),
    (r"(?:is|last|pichle)\s*(?:mahine|month)\s*(?:ka)?\s*(?:report|summary)", "monthly_report", lambda m: {}),
    (r"month(?:ly)?\s*summary",                    "monthly_report", lambda m: {}),
    (r"मंथली\s*रिपोर्ट",                          "monthly_report", lambda m: {}),  # Devanagari
    (r"show\s*(?:me\s*)?(?:the\s*)?monthly",       "monthly_report", lambda m: {}),

    # 1. Sales Trend
    (r"(?:pichle|last|guzre hue|previous)\s*(\d+)\s*(?:din|day|dinoM)", "sales_trend", _days),
    (r"(?:pichla|last)?\s*(?:week|hafte|hafta)\s*(?:ka)?\s*(?:sales?|bikri|revenue)", "sales_trend", lambda m: {"days": 7}),
    (r"sales?\s*(?:trend|report|kya hai|batao|dekho)", "sales_trend", lambda m: {}),
    (r"din\s*din\s*(?:sales?|revenue|bikri)", "sales_trend", lambda m: {}),
    (r"weekly\s*(?:sales?|bikri|report)", "sales_trend", lambda m: {"days": 7}),

    # 2. Hourly Rush
    (r"(?:peak|rush|bheed|busy|crowd|rush hour)\s*(?:time|hour|samay|waqt|baje)?", "hourly_rush", lambda m: {}),
    (r"sabse zyada\s*(?:bheed|rush|busy|log|crowd)", "hourly_rush", lambda m: {}),
    (r"kaunse?\s*(?:time|waqt|baje|ghante)\s*(?:sabse)?\s*(?:busy|rush)", "hourly_rush", lambda m: {}),
    (r"kab\s*sabse\s*(?:zyada|ber|busy|log)", "hourly_rush", lambda m: {}),

    # 3. Product Demand
    (r"(?:sabse|most|sab se|top)\s*(?:zyada)?\s*(?:bik|sell|demand|popular|chalta)", "product_demand", lambda m: {}),
    (r"popular\s*(?:item|product|maal|saman)", "product_demand", lambda m: {}),
    (r"(?:kya|kaun sa)\s*(?:zyada)?\s*bik\s*(?:raha|rahe|rahe hain)", "product_demand", lambda m: {}),
    (r"top\s*(?:products?|items?|sellers?)", "product_demand", lambda m: {}),
    (r"best\s*selling|highest\s*demand", "product_demand", lambda m: {}),

    # 4. Seasonal Trend
    (r"(?:garmi|baarish|sardi|holi|diwali|mausam|season)\s*(?:mein)?\s*(?:kya|what|kaun sa)", "seasonal_trend",
     lambda m: {"item_name": None}),
    (r"(?:seasonal|mausam|season|festival)\s*(?:trend|bikri|sales?|demand)", "seasonal_trend", lambda m: {}),
    (r"(?:summer|rain|winter|spring)\s*(?:trend|sales?)", "seasonal_trend", lambda m: {}),

    # 5. Stock Depletion
    (r"(\w+)\s*(?:kab)?\s*(?:khatam|finish|out|nahi rahe ga)\s*(?:hoga|hogi|ho jayega)?", "stock_depletion", _item),
    (r"stock\s*(?:kab)?\s*(?:khatam|finish|end|over)", "stock_depletion", lambda m: {}),
    (r"kitne\s*din\s*(?:ka)?\s*stock\s*(?:bacha)", "stock_depletion", lambda m: {}),
    (r"stock\s*adequacy|days?\s*(?:of\s*)?stock\s*left", "stock_depletion", lambda m: {}),

    # 6. Smart Reorder
    (r"(?:kitna|how much|kaunsa|kaun)\s*(?:order|mangao|reorder|mangvao)", "smart_reorder", lambda m: {}),
    (r"(?:order|reorder|mangao|mangvao)\s*(?:karna|karo|lagao|kaun sa)", "smart_reorder", lambda m: {}),
    (r"kya\s*(?:order|mangana|reorder)\s*(?:chahiye|karna|karo)", "smart_reorder", lambda m: {}),
    (r"reorder\s*(?:quantity|amount|kitna)", "smart_reorder", lambda m: {}),
    (r"ordering\s*(?:guide|help|suggestion)", "smart_reorder", lambda m: {}),

    # 7. Dead Stock
    (r"(?:nahi bik|dead stock|nahi bikta|slow|band|kaunsa maal nahi)", "dead_stock", lambda m: {}),
    (r"(?:purana|old|unused|not selling)\s*(?:stock|maal|saman|item)", "dead_stock", lambda m: {}),
    (r"kaunsa\s*(?:maal|item|saman)\s*(?:nahi|nahin)\s*bik\s*(?:raha|rahe)?", "dead_stock", lambda m: {}),
    (r"unsold\s*(?:inventory|stock|items?)", "dead_stock", lambda m: {}),

    # 8. Profit Trend
    (r"(?:profit|munafa|kamai|margin|earning|profit margin)\b", "profit_trend", lambda m: {}),
    (r"sabse\s*(?:zyada)?\s*(?:profit|munafa|kamai)\s*(?:dene|de raha|wala)", "profit_trend", lambda m: {}),
    (r"profit\s*(?:analysis|trend|report|by\s*item)", "profit_trend", lambda m: {}),

    # 9. Festival Trend
    (r"(?:last|pichla|ane wala|aane wala|coming)\s*(diwali|holi|eid|christmas|navratri|durga|raksha?|ramzan)", "festival_trend", _festival),
    (r"(diwali|holi|eid|christmas|navratri|durga|raksha|ramzan)\s*(?:mein)?\s*(?:kya|sales?|bikri|demand)", "festival_trend", _festival),
    (r"festival\s*(?:sales?|trends?|demand|inventory)", "festival_trend", lambda m: {"festival": "general"}),

    # 10. Market Basket (Hinglish + Hindi + English)
    # Extract product name specifically - product k saath pattern
    (r"(\w+)\s+(?:k|ka|ke|ki)?\s*saath", "market_basket", _item),  # chawal k saath kya bikte h
    
    # English/Hinglish patterns
    (r"(?:saath|together|combo|bundle|pair|market basket|basket analysis)", "market_basket", lambda m: {}),
    (r"(?:log|customers?)\s*kya\s*saath\s*(?:mein)?\s*(?:kharidte|kharidta|buy|lete)", "market_basket", lambda m: {}),
    (r"combo\s*(?:ideas?|suggestions?|selling)", "market_basket", lambda m: {}),
    (r"cross.?sell|upsell|bundle", "market_basket", lambda m: {}),
    
    # Hindi patterns - flexible word order
    (r"एक\s*साथ", "market_basket", lambda m: {}),  # "एक साथ" anywhere
    (r"साथ\s*(?:खरीद|बिक|बिकता|क्या)", "market_basket", lambda m: {}),  # "साथ खरीद/बिक"
    (r"(?:दोनों|donon|दोनो)\s*[\w\s]*(?:एक\s*साथ|together)", "market_basket", lambda m: {}),  # "दोनों ... एक साथ"
    (r"(?:किस|kis)\s*[\w\s]*(?:साथ|saath)\s*[\w\s]*(?:क्या|kya)", "market_basket", lambda m: {}),  # "किस साथ क्या"
    (r"एक\s*?\w*\s*?\w*\s*?साथ", "market_basket", lambda m: {}),  # Flexible "साथ" matching
    (r"combo\s*offer|bundle\s*deal", "market_basket", lambda m: {}),

    # 11. Customer Pattern
    (r"customer\s*(?:(?:ka)?\s*pattern|buying|behavior|kharidta|kharidi)", "customer_pattern", lambda m: {}),
    (r"(?:regular|frequent|loyal)\s*customers?", "customer_pattern", lambda m: {}),
    (r"customers?\s*(?:kya|kaunsa|kaun sa)\s*(?:regularly|regular|usually)", "customer_pattern", lambda m: {}),
    (r"(?:ghar|customer|person)\s*(?:kya|kaun sa)\s*(?:regularly|lagatar)", "customer_pattern", lambda m: {}),

    # 12. Auto Subscription
    (r"(?:subscription|weekly order|biweekly|monthly order|auto order|auto delivery)", "auto_subscription",
     lambda m: {"customer_id": "default"}),
    (r"mera\s*(?:weekly|monthly|regular|biweekly)\s*(?:order|delivery)", "auto_subscription",
     lambda m: {"customer_id": "default"}),
    (r"predict\s*(?:order|next purchase|delivery)", "auto_subscription", lambda m: {}),

    # 13. Weather Trend
    (r"(baarish|monsoon|garmi|summer|sardi|winter|rain|heat|cold|mausam|weather)\s*(?:mein)?\s*(?:kya|what|kaun sa)\s*(?:bik|sell)", "weather_trend", _season),
    (r"(?:weather|mausam|season)\s*(?:mein)?\s*(?:kya|sales?|trends?|demand)", "weather_trend", lambda m: {"season": "general"}),
    (r"seasonal\s*(?:demand|trends?|patterns?)", "weather_trend", lambda m: {}),
]

CUSTOMER_PATTERNS = [
    # RFM / segmentation
    (r"(rfm|segment|loyal|best customer|top customer|vip|high value|premium)", "rfm_analysis"),
    (r"(?:kaun|kaunsa)\s*(?:customer|ghar)\s*(?:best|top|VIP|loyal|valuable)", "rfm_analysis"),
    
    # Churn
    (r"(churn|lost customer|wapas nahi aaya|gayab|inactive|dormant|nahi aa rahe|banda|quit)", "churn_prediction"),
    (r"kaun\s*(?:customer|ghar)\s*nahi\s*(?:aaya|aa rahe?|visit kar?)", "churn_prediction"),
    
    # LTV
    (r"(ltv|lifetime value|kitna kamaya|total value|high value|spending|spender)", "customer_ltv"),
    (r"(?:customer|ghar)\s*(?:lifetime|saari|total)\s*(?:value|spending)", "customer_ltv"),
    
    # Basket (items per transaction)
    (r"(basket|ek baar mein|single visit|items per visit|khareedne|buying)", "basket_size"),
    (r"ek\s*(?:baar|visit)\s*mein\s*kitna|basket\s*(?:size|value)", "basket_size"),
    
    # Visit frequency
    (r"(visit frequency|kitne din mein aata|gap between|how often|regular|frequency)", "visit_frequency"),
    (r"kitne din mein aata hai|kaunsa ghar roz aata|visit frequency", "visit_frequency"),
    
    # Cohort
    (r"(cohort|retention|purane customer|month 1|returning|repeat purchase|comeback)", "cohort_retention"),
    (r"purana customer|returning customer|wapas aye|repeat", "cohort_retention"),
    
    # Next purchase / delivery prediction
    (r"(next purchase|delivery order|predict order|kab aayega|auto order|subscription order|next order)", "next_purchase"),
    (r"customer.*next.*(?:kya|kaun|order|purchase)|next.*order.*customer", "next_purchase"),
    
    # Loyalty
    (r"(loyalty score|loyalty|points|rank customer|customer rank|reward|badge)", "loyalty_scoring"),
    (r"loyalty|points|rewards|rank|score", "loyalty_scoring"),
    
    # Delivery orders
    (r"(delivery ready|kaun aayega|aaj ki delivery|kal ki delivery|delivery list|order prepare)", "delivery_orders"),
    (r"delivery|aaj.*order|kal.*order|ready|prepare", "delivery_orders"),
]


def classify_trend(query: str) -> Tuple[Optional[str], dict]:
    """
    Returns (trend_type, params) or (None, {}) if no trend matched.
    
    Usage:
        trend_type, params = classify_trend("pichle 7 din ka sales batao")
        # → ("sales_trend", {"days": 7})
    """
    query_lower = query.lower().strip()
    for pattern, trend_type, extractor in TREND_PATTERNS:
        m = re.search(pattern, query_lower)
        if m:
            try:
                params = extractor(m)
            except Exception:
                params = {}
            return trend_type, params
    return None, {}
