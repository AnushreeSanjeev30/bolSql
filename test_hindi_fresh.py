#!/usr/bin/env python3
"""Fresh test of Hindi parsing."""

import sys
sys.path.insert(0, '/Users/ankanamandal/Desktop/bolSql')

# Force reimport
if 'app.nlp.extractor' in sys.modules:
    del sys.modules['app.nlp.extractor']
if 'app' in sys.modules:
    del sys.modules['app']

from app.nlp.extractor import parse

hindi_text = "दालों की कीमत में 10% की वृद्धि करें"
print(f"Input: {hindi_text}\n")

parsed = parse(hindi_text)
print(f"Parsed:")
print(f"  Intent: {parsed.intent}")
print(f"  Item: {parsed.item_name}")
print(f"  Qty: {parsed.quantity}")
print(f"  Unit: {parsed.unit}")
