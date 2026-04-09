#!/usr/bin/env python3
"""Debug market basket query through pipeline."""

from app.trends.classifier import Classifier
from app.trends.engine import TrendsEngine
from app.trends.formatter import format_trend_response

query = "Log dono saath khareedta?"

print(f"🔍 Debugging: '{query}'\n")

# Step 1: Classify
classifier = Classifier()
trend_type, params = classifier.classify(query)
print(f"Step 1 - Classification:")
print(f"  Trend type: {trend_type}")
print(f"  Params: {params}")

# Step 2: Get engine result
engine = TrendsEngine('kirana_trends.db')
print(f"\nStep 2 - Engine dispatch:")
if trend_type == "market_basket":
    result = engine.dispatch(trend_type, params)
    print(f"  Dispatch returned: {type(result)}")
    print(f"  Is empty? {not result}")
    print(f"  Content: {result}")

# Step 3: Format
print(f"\nStep 3 - Format:")
formatted = format_trend_response(trend_type, result)
print(f"  Formatted: {formatted}")
