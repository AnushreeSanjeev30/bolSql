import re

path = "app/trends/customer_engine.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("sale_price * qty", "price * quantity")
content = content.replace("sale_price * quantity", "price * quantity")
content = content.replace("SUM(qty)", "SUM(quantity)")
content = content.replace("sale_price", "price")
content = content.replace('"qty"', '"quantity"')
content = content.replace("r[\"qty\"]", "r[\"quantity\"]")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done. Column names fixed.")