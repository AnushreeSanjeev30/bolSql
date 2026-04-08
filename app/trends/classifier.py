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
    (r"(?:pichle|last)\s*(\d+)\s*(?:din|day)", "sales_trend", _days),
    (r"(week|hafte)\s*(?:ka)?\s*(?:sales?|bikri)", "sales_trend", lambda m: {"days": 7}),
    (r"sales?\s*(?:trend|report|kya hai)", "sales_trend", lambda m: {}),

    # 2. Hourly Rush
    (r"(?:peak|rush|bheed|busy)\s*(?:time|hour|samay|waqt)", "hourly_rush", lambda m: {}),
    (r"sabse zyada\s*(?:bheed|rush|busy)", "hourly_rush", lambda m: {}),
    (r"kaunse?\s*(?:time|waqt|baje)", "hourly_rush", lambda m: {}),

    # 3. Product Demand
    (r"(?:sabse|most)\s*(?:zyada)?\s*(?:bik|sell|demand)", "product_demand", lambda m: {}),
    (r"popular\s*(?:item|product|maal)", "product_demand", lambda m: {}),
    (r"kya\s*(?:zyada)?\s*bik\s*(?:raha|rahe)", "product_demand", lambda m: {}),

    # 4. Seasonal Trend
    (r"(?:garmi|baarish|sardi|holi|diwali|season)\s*(?:mein)?\s*(?:kya|what)", "seasonal_trend",
     lambda m: {"item_name": None}),
    (r"(?:seasonal|mausam)\s*(?:trend|bikri|sales?)", "seasonal_trend", lambda m: {}),

    # 5. Stock Depletion
    (r"(\w+)\s*(?:kab)?\s*(?:khatam|finish|out)\s*(?:hoga|hogi|ho jayega)", "stock_depletion", _item),
    (r"stock\s*(?:kab)?\s*(?:khatam|finish)", "stock_depletion", lambda m: {}),
    (r"kitne\s*din\s*(?:ka)?\s*stock", "stock_depletion", lambda m: {}),

    # 6. Smart Reorder
    (r"(?:kitna|how much)\s*(?:order|mangao|reorder)", "smart_reorder", lambda m: {}),
    (r"(?:order|reorder)\s*(?:karna|karo|lagao)", "smart_reorder", lambda m: {}),
    (r"kya\s*(?:order|mangana)\s*chahiye", "smart_reorder", lambda m: {}),

    # 7. Dead Stock
    (r"(?:nahi bik|dead stock|slow|band|kaunsa maal nahi)", "dead_stock", lambda m: {}),
    (r"(?:purana|old)\s*(?:stock|maal|saman)", "dead_stock", lambda m: {}),
    (r"kaunsa\s*(?:maal|item|saman)\s*(?:nahi|nahin)\s*bik", "dead_stock", lambda m: {}),

    # 8. Profit Trend
    (r"(?:profit|munafa|kamai|margin)", "profit_trend", lambda m: {}),
    (r"sabse\s*(?:zyada)?\s*(?:profit|munafa)\s*(?:dene|de raha)", "profit_trend", lambda m: {}),

    # 9. Festival Trend
    (r"(?:last|pichla)\s*(diwali|holi|eid|christmas|navratri)\s*(?:mein)?", "festival_trend", _festival),
    (r"(diwali|holi|eid|christmas|navratri)\s*(?:mein)?\s*(?:kya|sales?|bikri)", "festival_trend", _festival),

    # 10. Market Basket
    (r"(?:saath|together|combo|basket|market basket)", "market_basket", lambda m: {}),
    (r"(?:log|customers?|log)\s*kya\s*saath\s*(?:mein)?\s*(?:kharidte|buy|lete)", "market_basket", lambda m: {}),

    # 11. Customer Pattern
    (r"customer\s*(?:(?:ka)?\s*pattern|buying|kharidta)", "customer_pattern", lambda m: {}),
    (r"(?:regular|frequent)\s*customer", "customer_pattern", lambda m: {}),
    (r"customers?\s*(?:kya|kaunsa)\s*(?:regularly|regular)", "customer_pattern", lambda m: {}),

    # 12. Auto Subscription
    (r"(?:subscription|weekly order|monthly order|auto)", "auto_subscription",
     lambda m: {"customer_id": "default"}),
    (r"mera\s*(?:weekly|monthly|regular)\s*order", "auto_subscription",
     lambda m: {"customer_id": "default"}),

    # 13. Weather Trend
    (r"(baarish|garmi|sardi|rain|summer|winter|holi|diwali)\s*(?:mein)?\s*(?:kya|what|kaun)\s*(?:bik|sell)", "weather_trend", _season),
    (r"(?:weather|mausam)\s*(?:mein)?\s*(?:kya|sales?)", "weather_trend", lambda m: {}),
]
CUSTOMER_PATTERNS = [
    # RFM / segmentation
    (r"(rfm|segment|loyal customer|best customer|top customer|vip)", "rfm_analysis"),
    # Churn
    (r"(churn|lost customer|wapas nahi aaya|gayab|inactive|dormant)", "churn_prediction"),
    # LTV
    (r"(ltv|lifetime value|kitna kamaya|total value|high value)", "customer_ltv"),
    # Basket
    (r"(basket|ek baar mein kitna|single visit|items per visit)", "basket_size"),
    # Visit frequency
    (r"(visit frequency|kitne din mein aata|gap between visits|regular customer)", "visit_frequency"),
    # Cohort
    (r"(cohort|retention|purane customer|month 1|returning)", "cohort_retention"),
    # Next purchase / delivery prediction
    (r"(next purchase|delivery order|predict order|kab aayega|auto order|subscription order)", "next_purchase"),
    # Loyalty
    (r"(loyalty score|loyalty|points|rank customer|customer rank)", "loyalty_scoring"),
    # Delivery orders
    (r"(delivery ready|kaun aayega|aaj ki delivery|kal ki delivery|delivery list|order prepare)", "delivery_orders"),
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
