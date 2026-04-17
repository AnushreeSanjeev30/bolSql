#!/usr/bin/env python3

import re

text = "dalo kee keemt me 10% kee vriddhi kre"
text_l = text.lower()

print(f"Original: {text}")
print()

# Remove numbers + units
cleaned = re.sub(r"\d+(?:\.\d+)?\s*(?:%|percent|percentage)?", "", text_l)
print(f"After number/% removal: '{cleaned}'")
print()

# Remove fillers - key ones for Hindi transliterated text
fillers_to_remove = [
    (r"\bkee\b", "kee"),
    (r"\bkeemt\b", "keemt"),
    (r"\bme\b", "me"),
    (r"\bvriddhi\b", "vriddhi"),
    (r"\bkre\b", "kre"),
    (r"\bka\b", "ka"),
    (r"\bki\b", "ki"),
]

for pattern, name in fillers_to_remove:
    before = cleaned
    cleaned = re.sub(pattern, " ", cleaned)
    if before != cleaned:
        print(f"After removing '{name}': '{cleaned}'")

print()
print(f"Final:  '{cleaned.strip()}'")

# Collapse spaces
final = re.sub(r"\s+", " ", cleaned).strip()
print(f"Collapsed: '{final}'")
