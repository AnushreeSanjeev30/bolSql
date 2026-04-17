path = "app/trends/customer_engine.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# The query inside predict_next_purchases aliases quantity as qty
# so r["qty"] is correct AFTER the alias — problem is the SQL itself
old = "SUM(qty) AS qty"
new = "SUM(quantity) AS qty"
content = content.replace(old, new)

# Also catch any un-aliased quantity references still named qty
old2 = '"quantity":  r["quantity"]'
new2 = '"qty":  r["qty"]'
content = content.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done.")