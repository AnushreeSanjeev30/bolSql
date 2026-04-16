"""
VoiceSQL Trends Engine
Implements 13 analytical trend modules for Kirana Intelligence.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict
import math

from app.trends.demand_model import predict_demand_ema


class TrendsEngine:
    """
    Master engine for all 13 trend analyses.
    Called by the NLP pipeline when intent = TREND_QUERY.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _latest_txn_dt(self, cur):
        cur.execute("SELECT MAX(timestamp) FROM transactions")
        row = cur.fetchone()
        raw = row[0] if row else None
        if not raw:
            return None
        text = str(raw).strip().replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        return None

    def _window_bounds(self, cur, days: int):
        latest = self._latest_txn_dt(cur) or datetime.now()
        since = (latest - timedelta(days=days)).strftime("%Y-%m-%d")
        until = latest.strftime("%Y-%m-%d")
        return since, until, latest

    PRICE_FALLBACKS = {
        "atta": 45.0,
        "aata": 45.0,
        "chawal": 70.0,
        "rice": 70.0,
        "dal": 120.0,
        "lentil": 120.0,
        "milk": 28.0,
        "doodh": 28.0,
        "bread": 40.0,
        "biscuit": 20.0,
        "biscuits": 20.0,
        "butter": 55.0,
        "chai": 350.0,
        "chai patti": 350.0,
        "tea": 350.0,
        "oil": 130.0,
        "tel": 130.0,
        "ghee": 220.0,
        "sugar": 55.0,
        "chini": 55.0,
        "salt": 20.0,
        "namak": 20.0,
        "tomato": 32.0,
        "tomatoes": 32.0,
        "onion": 28.0,
        "onions": 28.0,
        "aloo": 30.0,
        "potato": 30.0,
        "potatoes": 30.0,
        "apple": 18.0,
        "bananas": 12.0,
        "banana": 12.0,
        "toothpaste": 95.0,
        "ketchup": 45.0,
        "soft drink": 35.0,
        "cold drink": 35.0,
        "water": 20.0,
        "bottle": 20.0,
        "soap": 25.0,
        "sabun": 25.0,
        "broom": 60.0,
        "pen": 12.0,
    }

    FESTIVAL_WINDOWS = {
        "diwali": [("09-15", "11-30")],
        "holi": [("02-15", "03-31")],
        "christmas": [("12-01", "12-31")],
        "new_year": [("12-20", "01-10")],
        "eid": [("03-15", "05-31")],
        "navratri": [("09-15", "10-31")],
        "dussehra": [("09-20", "11-05")],
        "dusshera": [("09-20", "11-05")],
        "ganesh_chaturthi": [("08-10", "09-20")],
        "raksha_bandhan": [("08-01", "08-31")],
        "onam": [("08-15", "09-30")],
        "pongal": [("01-05", "01-31")],
    }

    FESTIVAL_ALIASES = {
        "valentine": "valentine",
        "valentines": "valentine",
        "valentines day": "valentine",
        "durga": "navratri",
        "durga puja": "navratri",
        "raksha": "raksha_bandhan",
        "rakhi": "raksha_bandhan",
        "ramzan": "eid",
        "ramadan": "eid",
        "diwali": "diwali",
        "holi": "holi",
        "christmas": "christmas",
        "new year": "new_year",
    }

    def _normalize_lookup_key(self, value: str) -> str:
        return " ".join(str(value or "").strip().lower().replace("_", " ").split())

    def _estimate_sale_price(self, item_name: str, unit: str = None, category: str = None) -> float:
        key = self._normalize_lookup_key(item_name)
        for token, price in self.PRICE_FALLBACKS.items():
            if token in key:
                return float(price)

        unit_key = self._normalize_lookup_key(unit)
        category_key = self._normalize_lookup_key(category)
        if unit_key in {"kg", "kilogram"}:
            return 60.0
        if unit_key in {"litre", "liter", "l"}:
            return 50.0
        if unit_key in {"packet", "pack", "piece", "pcs", "bottle"}:
            return 35.0
        if "grocery" in category_key or "general" in category_key:
            return 40.0
        return 40.0

    def _infer_festival_windows(self, festival: str, years: list[int]) -> list[tuple[str, str, str]]:
        festival_key = self.FESTIVAL_ALIASES.get(self._normalize_lookup_key(festival), self._normalize_lookup_key(festival))
        festivals = self.FESTIVAL_WINDOWS.keys() if festival_key in {"", "all", "any", "general", "festivals"} else [festival_key]
        windows = []
        for festival_name in festivals:
            for year in years:
                for start_md, end_md in self.FESTIVAL_WINDOWS.get(festival_name, []):
                    start_year = year
                    end_year = year + 1 if end_md < start_md else year
                    windows.append((festival_name, f"{start_year}-{start_md}", f"{end_year}-{end_md}"))
        return windows

    def _effective_transaction_price(self, item_name: str, txn_price: float, inv_price: float = 0.0, unit: str = None, category: str = None) -> tuple[float, bool]:
        if txn_price and txn_price > 0:
            return float(txn_price), False
        if inv_price and inv_price > 0:
            return float(inv_price), False
        return self._estimate_sale_price(item_name, unit=unit, category=category), True

    # ─────────────────────────────────────────────
    # 1. SALES TREND (Time-based)
    # ─────────────────────────────────────────────
    def sales_trend(self, days: int = 7) -> dict:
        """Total sales per day for the last N days."""
        conn = self._conn()
        cur = conn.cursor()
        since, until, latest = self._window_bounds(cur, days)
        cur.execute("""
            SELECT DATE(timestamp) as day,
                   SUM(quantity * price) as revenue,
                   COUNT(*) as orders
            FROM transactions
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY day
            ORDER BY day
        """, (since, until))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "sales", "data": [], "insight": "Koi data nahi mila."}

        peak = max(rows, key=lambda r: r[1])
        return {
            "trend": "sales",
            "days": days,
            "data": [{"day": r[0], "revenue": r[1], "orders": r[2]} for r in rows],
            "peak_day": peak[0],
            "peak_revenue": peak[1],
            "insight": f"Last {days} din ({until} tak) mein {peak[0]} ko sabse zyada ₹{peak[1]:.0f} ki bikri hui."
        }

    # ─────────────────────────────────────────────
    # 2. HOURLY RUSH TREND
    # ─────────────────────────────────────────────
    def hourly_rush(self, days: int = 7) -> dict:
        """Orders per hour to identify peak times."""
        conn = self._conn()
        cur = conn.cursor()
        since, until, latest = self._window_bounds(cur, days)
        cur.execute("""
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                   COUNT(*) as orders
            FROM transactions
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY hour
            ORDER BY hour
        """, (since, until))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "hourly_rush", "data": [], "insight": "Data nahi hai."}

        peak = max(rows, key=lambda r: r[1])
        hour_label = f"{peak[0]}:00–{peak[0]+1}:00"
        return {
            "trend": "hourly_rush",
            "data": [{"hour": r[0], "orders": r[1]} for r in rows],
            "peak_hour": peak[0],
            "peak_orders": peak[1],
            "insight": f"Sabse zyada rush {hour_label} baje hota hai ({peak[1]} orders)."
        }

    # ─────────────────────────────────────────────
    # 3. PRODUCT DEMAND TREND
    # ─────────────────────────────────────────────
    def product_demand(self, days: int = 30, top_n: int = 10) -> dict:
        """Most sold products by quantity."""
        conn = self._conn()
        cur = conn.cursor()
        since, until, latest = self._window_bounds(cur, days)
        cur.execute("""
            SELECT t.item_name,
                   SUM(t.quantity) as total_qty,
                   SUM(
                       CASE WHEN COALESCE(t.price, 0) > 0
                            THEN t.quantity * t.price
                            ELSE 0
                       END
                   ) as revenue,
                   SUM(
                       CASE WHEN COALESCE(t.price, 0) > 0
                            THEN 1
                            ELSE 0
                       END
                   ) as priced_rows
            FROM transactions t
            WHERE DATE(t.timestamp) BETWEEN ? AND ?
            GROUP BY t.item_name
            ORDER BY total_qty DESC
            LIMIT ?
        """, (since, until, top_n))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "product_demand", "data": [], "insight": "Data nahi mila."}

        top = rows[0]
        has_any_price_data = any((r[3] or 0) > 0 for r in rows)
        insight = f"{top[0]} sabse zyada bik raha hai — {top[1]} units last {days} din ({until} tak) mein."
        if not has_any_price_data:
            insight += " Revenue estimate unavailable: transactions me price data missing hai."

        return {
            "trend": "product_demand",
            "data": [
                {
                    "item": r[0],
                    "qty_sold": r[1],
                    "revenue": r[2],
                    "has_price_data": (r[3] or 0) > 0,
                }
                for r in rows
            ],
            "top_item": top[0],
            "top_qty": top[1],
            "insight": insight
        }

    # ─────────────────────────────────────────────
    # 4. SEASONAL TREND
    # ─────────────────────────────────────────────
    def seasonal_trend(self, item_name: str = None) -> dict:
        """Monthly sales aggregation to detect seasonal patterns."""
        conn = self._conn()
        cur = conn.cursor()
        if item_name:
            cur.execute("""
                SELECT strftime('%Y-%m', timestamp) as month,
                       SUM(quantity) as qty,
                       SUM(quantity * price) as revenue
                FROM transactions
                WHERE LOWER(item_name) LIKE LOWER(?)
                GROUP BY month ORDER BY month
            """, (f"%{item_name}%",))
        else:
            cur.execute("""
                SELECT strftime('%Y-%m', timestamp) as month,
                       SUM(quantity) as qty,
                       SUM(quantity * price) as revenue
                FROM transactions
                GROUP BY month ORDER BY month
            """)
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "seasonal", "data": [], "insight": "Seasonal data nahi hai."}

        peak = max(rows, key=lambda r: r[1])
        label = f"Item: {item_name}" if item_name else "Overall"
        return {
            "trend": "seasonal",
            "label": label,
            "data": [{"month": r[0], "qty": r[1], "revenue": r[2]} for r in rows],
            "peak_month": peak[0],
            "insight": f"{peak[0]} mein sabse zyada demand thi — {peak[1]} units."
        }

    # ─────────────────────────────────────────────
    # 5. STOCK DEPLETION TREND (CRITICAL)
    # ─────────────────────────────────────────────
    def stock_depletion(self, item_name: str = None, days_window: int = 14) -> list:
        """
        Predicts days until stockout using:
            days_left = current_stock / avg_daily_sales
        """
        conn = self._conn()
        cur = conn.cursor()
        since, until, latest = self._window_bounds(cur, days_window)

        # Get avg daily sales per item
        cur.execute("""
            SELECT item_name,
                   SUM(quantity) / ? as avg_daily
            FROM transactions
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY item_name
        """, (days_window, since, until))
        sales_map = {r[0]: r[1] for r in cur.fetchall()}

        # Get current stock
        if item_name:
            cur.execute(
                "SELECT name, quantity FROM inventory WHERE LOWER(name) LIKE LOWER(?)",
                (f"%{item_name}%",),
            )
        else:
            cur.execute("SELECT name, quantity FROM inventory")
        stock_rows = cur.fetchall()
        conn.close()

        # If the specific pattern (e.g. "product", "items") didn't
        # match anything in inventory, fall back to checking the full
        # inventory so that generic questions like
        #   "kaunsa product khatam hone wala hai?"
        # still show the items closest to stockout instead of
        # "All items stock fine".
        if not stock_rows:
            conn = self._conn()
            cur = conn.cursor()
            cur.execute("SELECT name, quantity FROM inventory")
            stock_rows = cur.fetchall()
            conn.close()

        results = []
        for name, qty in stock_rows:
            avg = sales_map.get(name, 0)
            if avg > 0:
                days_left = qty / avg
                urgency = "🔴 CRITICAL" if days_left <= 3 else "🟡 LOW" if days_left <= 7 else "🟢 OK"
            else:
                days_left = float('inf')
                urgency = "⚪ NO SALES"
            results.append({
                "item": name,
                "current_stock": qty,
                "avg_daily_sales": round(avg, 2),
                "days_until_stockout": round(days_left, 1) if days_left != float('inf') else None,
                "urgency": urgency
            })

        results.sort(key=lambda x: x["days_until_stockout"] or 9999)
        return results

    # ─────────────────────────────────────────────
    # 6. SMART REORDER TREND
    # ─────────────────────────────────────────────
    def smart_reorder(self, lead_time_days: int = 3, safety_factor: float = 1.5) -> list:
        """
        Reorder quantity = avg_daily_sales × lead_time × safety_factor
        """
        depletions = self.stock_depletion()
        reorders = []
        for item in depletions:
            avg = item["avg_daily_sales"]
            if avg > 0:
                reorder_qty = math.ceil(avg * lead_time_days * safety_factor)
                reorders.append({
                    "item": item["item"],
                    "reorder_qty": reorder_qty,
                    "days_left": item["days_until_stockout"],
                    "urgency": item["urgency"],
                    "reason": f"Avg {avg:.1f}/day × {lead_time_days}d lead × {safety_factor}x safety"
                })
        reorders.sort(key=lambda x: x["days_left"] or 9999)
        return reorders

    # ─────────────────────────────────────────────
    # 7. DEAD STOCK TREND
    # ─────────────────────────────────────────────
    def dead_stock(self, threshold_days: int = 30) -> list:
        """Items with no sales in threshold_days."""
        conn = self._conn()
        cur = conn.cursor()
        latest = self._latest_txn_dt(cur) or datetime.now()
        cutoff = (latest - timedelta(days=threshold_days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT i.name, i.quantity,
                   MAX(t.timestamp) as last_sold
            FROM inventory i
            LEFT JOIN transactions t ON LOWER(i.name) = LOWER(t.item_name)
            GROUP BY i.name
            HAVING last_sold IS NULL OR last_sold < ?
            ORDER BY last_sold ASC
        """, (cutoff,))
        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            days_idle = None
            if r[2]:
                raw = str(r[2]).replace("T", " ").strip()
                parsed = None
                for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        parsed = datetime.strptime(raw[:19], fmt)
                        break
                    except ValueError:
                        continue
                if parsed:
                    days_idle = (latest - parsed).days

            results.append({
                "item": r[0],
                "stock_qty": r[1],
                "last_sold": r[2] or "Never",
                "days_idle": days_idle,
                "recommendation": "Discount pe becho ya return karo"
            })
        return results

    # ─────────────────────────────────────────────
    # 8. PROFIT TREND
    # ─────────────────────────────────────────────
    def profit_trend(self, days: int = 30, top_n: int = 10) -> dict:
        """Compute profit trend with robust fallback when transaction prices are missing."""
        conn = self._conn()
        cur = conn.cursor()
        since, until, _latest = self._window_bounds(cur, days)

        cur.execute(
            """
            SELECT t.item_name,
                   t.quantity,
                   t.price,
                   i.price,
                   i.cost_price,
                   i.unit,
                   i.category
            FROM transactions t
            LEFT JOIN inventory i ON LOWER(i.name) = LOWER(t.item_name)
            WHERE DATE(t.timestamp) BETWEEN ? AND ?
              AND t.item_name IS NOT NULL
            ORDER BY t.item_name
            """,
            (since, until),
        )
        raw_rows = cur.fetchall()
        conn.close()

        if not raw_rows:
            return {"trend": "profit", "data": [], "insight": "Profit data nahi hai."}

        totals: dict[str, dict] = {}
        inferred_rows = 0
        priced_rows = 0
        for item_name, quantity, txn_price, inv_price, cost_price, unit, category in raw_rows:
            qty = float(quantity or 0)
            sale_price, inferred = self._effective_transaction_price(
                item_name,
                float(txn_price or 0),
                float(inv_price or 0),
                unit=unit,
                category=category,
            )
            if inferred:
                inferred_rows += 1
            else:
                priced_rows += 1
            cogs_unit = float(cost_price or 0)
            if cogs_unit <= 0:
                cogs_unit = sale_price * 0.7

            revenue = qty * sale_price
            cogs = qty * cogs_unit
            profit = revenue - cogs

            bucket = totals.setdefault(item_name, {
                "item": item_name,
                "qty": 0.0,
                "revenue": 0.0,
                "cogs": 0.0,
                "profit": 0.0,
                "margin_pct": 0.0,
            })
            bucket["qty"] += qty
            bucket["revenue"] += revenue
            bucket["cogs"] += cogs
            bucket["profit"] += profit

        rows = sorted(totals.values(), key=lambda r: r["profit"], reverse=True)[:top_n]

        top = rows[0]
        top_profit = round(top["profit"] or 0, 2)
        if inferred_rows and not priced_rows:
            insight = "Profit estimate unavailable in CSV, so missing price rows ke liye inferred market prices use kiye."
        elif top_profit <= 0:
            insight = f"{top['item']} pe margin low hai; profit approx ₹{top_profit:.0f}."
        else:
            insight = f"{top['item']} sabse zyada ₹{top_profit:.0f} ka profit de raha hai."

        return {
            "trend": "profit",
            "data": [
                {
                    "item": r["item"],
                    "qty": round(r["qty"], 2),
                    "revenue": round(r["revenue"], 2),
                    "cogs": round(r["cogs"], 2),
                    "profit": round(r["profit"], 2),
                    "margin_pct": round((r["profit"] / r["revenue"]) * 100, 1) if r["revenue"] > 0 else 0,
                }
                for r in rows
            ],
            "top_item": top["item"],
            "top_profit": top_profit,
            "insight": insight,
            "price_source": "inferred" if inferred_rows and not priced_rows else "mixed",
        }

    # ─────────────────────────────────────────────
    # 9. FESTIVAL TREND
    # ─────────────────────────────────────────────
    def festival_trend(self, festival: str = "diwali") -> dict:
        """Compare sales during festival windows across years."""
        conn = self._conn()
        cur = conn.cursor()
        results = []
        cur.execute("SELECT DISTINCT CAST(strftime('%Y', timestamp) AS INTEGER) FROM transactions")
        years = [r[0] for r in cur.fetchall() if r[0]]
        if not years:
            years = [datetime.now().year]
        windows = self._infer_festival_windows(festival, sorted(years))
        for festival_name, start, end in windows:
            cur.execute(
                """
                    SELECT t.quantity,
                           t.price,
                           i.price,
                           i.cost_price,
                           i.unit,
                           i.category
                    FROM transactions t
                    LEFT JOIN inventory i ON LOWER(i.name) = LOWER(t.item_name)
                    WHERE DATE(t.timestamp) BETWEEN ? AND ?
                      AND t.type = 'sale'
                """,
                (start, end),
            )
            rows = cur.fetchall()
            if not rows:
                continue

            revenue = 0.0
            orders = 0
            units = 0.0
            for quantity, txn_price, inv_price, cost_price, unit, category in rows:
                sale_price, _inferred = self._effective_transaction_price(
                    "",
                    float(txn_price or 0),
                    float(inv_price or 0),
                    unit=unit,
                    category=category,
                )
                qty = float(quantity or 0)
                revenue += qty * sale_price
                units += qty
                orders += 1
            results.append({
                "year": int(start[:4]),
                "festival": festival_name,
                "revenue": round(revenue, 2),
                "orders": orders,
                "units": round(units, 2),
            })
        conn.close()

        if not results:
            festival_label = self._normalize_lookup_key(festival or "festival")
            return {"trend": "festival", "festival": festival_label,
                    "data": [], "insight": f"{festival_label.title()} ka data nahi mila."}

        best = max(results, key=lambda r: r["revenue"])
        festival_counts = defaultdict(int)
        for row in results:
            festival_counts[row["festival"]] += 1
        top_festival = max(festival_counts.items(), key=lambda item: item[1])[0]
        return {
            "trend": "festival",
            "festival": self._normalize_lookup_key(festival) if self._normalize_lookup_key(festival) not in {"", "all", "any", "general", "festivals"} else "general",
            "festivals": sorted(festival_counts.keys()),
            "data": results,
            "best_year": best["year"],
            "top_festival": top_festival,
            "top_revenue": round(best["revenue"], 2),
            "insight": f"{top_festival.replace('_', ' ').title()} {best['year']} mein sabse zyada ₹{best['revenue']:.0f} ki bikri hui."
        }

    # ─────────────────────────────────────────────
    # 10. MARKET BASKET TREND (Apriori-lite)
    # ─────────────────────────────────────────────
    def market_basket(self, min_support: int = 3, top_n: int = 10, product: str = None, item_name: str = None) -> dict:
        """
        Find frequently co-purchased item pairs using
        a simplified Apriori pass on same-session transactions.
        Groups transactions within 5-minute windows as "baskets".
        
        If product or item_name is specified, returns items bought with that product.
        """
        # Use item_name if provided (from NLP extractor), otherwise use product
        if item_name:
            product = item_name
        
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT item_name, timestamp
            FROM transactions
            ORDER BY timestamp
        """)
        rows = cur.fetchall()
        conn.close()

        # Build baskets: group items within 5-minute windows
        baskets = []
        current_basket = []
        last_time = None
        window = timedelta(minutes=5)

        for item, ts_str in rows:
            # Handle timestamps with/without seconds, and both 'T' / space separators.
            ts_raw = (ts_str or "").replace("T", " ").strip()
            ts = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    ts = datetime.strptime(ts_raw[:19], fmt)
                    break
                except ValueError:
                    continue

            # Skip malformed timestamps instead of crashing the full API request.
            if ts is None:
                continue

            if last_time is None or (ts - last_time) > window:
                if current_basket:
                    baskets.append(current_basket)
                current_basket = [item]
            else:
                current_basket.append(item)
            last_time = ts
        if current_basket:
            baskets.append(current_basket)

        # Count co-occurrences
        pair_count = defaultdict(int)
        product_cooccur = defaultdict(int)  # For product-specific analysis
        
        for basket in baskets:
            unique = list(set(basket))
            
            # General pairs
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = tuple(sorted([unique[i], unique[j]]))
                    pair_count[pair] += 1
            
            # Product-specific pairs
            if product:
                product_lower = product.lower()
                for item in unique:
                    if product_lower in item.lower() or item.lower() in product_lower:
                        for other in unique:
                            if other.lower() != product_lower:
                                product_cooccur[other] += 1

        # If product specified, return product-specific results
        if product:
            if product_cooccur:
                sorted_items = sorted(product_cooccur.items(), key=lambda x: -x[1])
                data = [{
                    "item": item,
                    "count": count,
                    "pair": f"{product} + {item}"
                } for item, count in sorted_items[:top_n]]
                
                top_item = sorted_items[0] if sorted_items else None
                return {
                    "trend": "market_basket",
                    "product": product,
                    "data": data,
                    "insight": f"{product} ke saath sabse zyada {top_item[0]} bika hai ({top_item[1]} baar)" if top_item else f"{product} k saath koi combination nahi mila"
                }
            else:
                return {
                    "trend": "market_basket",
                    "product": product,
                    "data": [],
                    "insight": f"{product} k liye koi market basket data nahi hai"
                }

        # General market basket (no specific product)
        frequent = [(p, c) for p, c in pair_count.items() if c >= min_support]
        frequent.sort(key=lambda x: -x[1])

        data = [{
            "pair": f"{p[0][0]} + {p[0][1]}",
            "item_a": p[0][0],
            "item_b": p[0][1],
            "count": p[1],
        } for p in frequent[:top_n]]

        return {
            "trend": "market_basket",
            "data": data,
            "insight": f"Sabse popular combination: {frequent[0][0][0]} aur {frequent[0][0][1]} ({frequent[0][1]} baar)" if frequent else "Koi frequent pairs nahi"
        }

    # ─────────────────────────────────────────────
    # 11. CUSTOMER BUYING PATTERN TREND
    # ─────────────────────────────────────────────
    def customer_pattern(self, customer_id: str = None, top_n: int = 10) -> dict:
        """Purchase frequency and regularity per customer."""
        conn = self._conn()
        cur = conn.cursor()

        if customer_id:
            cur.execute("""
                SELECT item_name, COUNT(*) as freq,
                       AVG(julianday('now') - julianday(timestamp)) as avg_recency,
                       MIN(timestamp) as first, MAX(timestamp) as last
                FROM transactions
                WHERE customer_id = ?
                GROUP BY item_name ORDER BY freq DESC
            """, (customer_id,))
        else:
            cur.execute("""
                SELECT customer_id, COUNT(*) as orders,
                       SUM(quantity * price) as total_spent,
                       COUNT(DISTINCT item_name) as unique_items
                FROM transactions
                WHERE customer_id IS NOT NULL
                GROUP BY customer_id
                ORDER BY orders DESC LIMIT ?
            """, (top_n,))

        rows = cur.fetchall()
        conn.close()

        if customer_id:
            return {
                "trend": "customer_pattern",
                "customer": customer_id,
                "items": [{"item": r[0], "frequency": r[1],
                           "first": r[3], "last": r[4]} for r in rows]
            }
        return {
            "trend": "customer_pattern",
            "top_customers": [{"customer": r[0], "orders": r[1],
                               "spent": round(r[2], 2), "unique_items": r[3]}
                              for r in rows]
        }

    # ─────────────────────────────────────────────
    # 12. AUTO-SUBSCRIPTION TREND
    # ─────────────────────────────────────────────
    def auto_subscription(self, customer_id: str = None) -> dict:
        """
        Predict next purchase date per item using:
            next_purchase = last_purchase + avg_gap_days
        If no customer_id specified, return general subscription recommendations.
        """
        conn = self._conn()
        cur = conn.cursor()
        
        # If no specific customer, analyze all regular items
        if not customer_id:
            cur.execute("""
                SELECT item_name, COUNT(*) as purchases,
                       MAX(timestamp) as last_purchase,
                       AVG(julianday('now') - julianday(timestamp)) as avg_days_between
                FROM transactions
                GROUP BY item_name
                HAVING purchases >= 3
                ORDER BY purchases DESC
            """)
            rows = cur.fetchall()
            conn.close()
            
            if not rows:
                return {
                    "trend": "auto_subscription",
                    "data": [],
                    "insight": "Abhi koi regular subscription pattern nahi hai"
                }
            
            predictions = []
            for item, purchases, last_purchase, avg_days in rows:
                if avg_days:
                    predictions.append({
                        "item": item,
                        "total_purchases": int(purchases),
                        "avg_days_between": round(float(avg_days), 1),
                        "last_purchase": last_purchase[:10] if last_purchase else "Unknown",
                        "recommendation": f"Har {round(float(avg_days), 0)} din mein restock karo"
                    })
            
            return {
                "trend": "auto_subscription",
                "data": predictions[:10],
                "insight": f"Top {len(predictions)} items regularly bikta hai, subscription plan banao"
            }
        
        # Specific customer analysis
        cur.execute("""
            SELECT item_name, timestamp
            FROM transactions
            WHERE customer_id = ?
            ORDER BY item_name, timestamp
        """, (customer_id,))
        rows = cur.fetchall()
        conn.close()

        item_dates = defaultdict(list)
        for item, ts_str in rows:
            item_dates[item].append(datetime.strptime(ts_str[:19], "%Y-%m-%d %H:%M:%S"))

        predictions = []
        for item, dates in item_dates.items():
            if len(dates) < 2:
                continue
            gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            avg_gap = sum(gaps) / len(gaps)
            next_date = dates[-1] + timedelta(days=avg_gap)
            days_until = (next_date - datetime.now()).days
            predictions.append({
                "item": item,
                "avg_gap_days": round(avg_gap, 1),
                "last_purchase": dates[-1].strftime("%Y-%m-%d"),
                "predicted_next": next_date.strftime("%Y-%m-%d"),
                "days_until": days_until,
                "status": "DUE SOON" if days_until <= 2 else "UPCOMING"
            })

        predictions.sort(key=lambda x: x["days_until"])
        return {
            "trend": "auto_subscription",
            "customer": customer_id,
            "data": predictions,
            "insight": f"{len(predictions)} items ke liye subscription plan ban sakti hai"
        }

    # ─────────────────────────────────────────────
    # 13. WEATHER-BASED TREND (BONUS)
    # ─────────────────────────────────────────────
    WEATHER_MAP = {
        "rain": ["chai", "tea", "maggi", "noodles", "biscuit", "umbrella"],
        "summer": ["cold drink", "ice cream", "nimbu", "lassi", "sharbat", "water"],
        "winter": ["blanket", "rum", "gur", "moongfali", "til", "chai"],
        "holi": ["rang", "pichkari", "sweets", "thandai"],
        "diwali": ["diya", "mithai", "dry fruits", "pooja samagri"],
    }

    def weather_trend(self, season: str = "rain", days: int = 90) -> dict:
        """
        Correlate weather/season keywords with actual historical sales.
        """
        keywords = self.WEATHER_MAP.get(season.lower(), [])
        if not keywords:
            return {"trend": "weather", "insight": "Season samajh nahi aaya."}

        conn = self._conn()
        cur = conn.cursor()
        since, until, latest = self._window_bounds(cur, days)

        results = []
        for kw in keywords:
            cur.execute("""
                SELECT item_name, SUM(quantity) as qty,
                       SUM(quantity * price) as revenue
                FROM transactions
                WHERE LOWER(item_name) LIKE LOWER(?) AND DATE(timestamp) BETWEEN ? AND ?
                GROUP BY item_name
                ORDER BY qty DESC
            """, (f"%{kw}%", since, until))
            rows = cur.fetchall()
            for r in rows:
                results.append({"item": r[0], "qty": r[1], "revenue": round(r[2], 2)})

        conn.close()
        results.sort(key=lambda x: -x["qty"])
        top = results[0]["item"] if results else season + " items"
        return {
            "trend": "weather",
            "season": season,
            "expected_items": keywords,
            "sales_data": results[:10],
            "insight": f"{season.title()} mein {top} sabse zyada bikta hai."
        }

    def demand_stock_risk(self, days_ahead: int = 3):
        """Predict future demand and assess stock risk."""
        demand = predict_demand_ema(self.db_path, days_ahead)

        conn = self._conn()
        cur = conn.cursor()

        cur.execute("SELECT name, quantity FROM inventory")
        stock_rows = cur.fetchall()
        conn.close()

        inventory = {name: qty for name, qty in stock_rows}

        results = []

        for item, predicted in demand.items():
            stock = inventory.get(item, 0)

            shortage = predicted - stock
            ratio = predicted / (stock + 1)

            if predicted > stock:
                risk = "🔴 CRITICAL"
            elif ratio > 0.7:
                risk = "🟡 HIGH"
            else:
                risk = "🟢 SAFE"

            results.append({
                "item": item,
                "predicted_demand": round(predicted, 1),
                "current_stock": stock,
                "shortage": round(max(0, shortage), 1),
                "risk": risk,
                "suggested_reorder": round(max(0, shortage * 1.3), 1)
            })

        return sorted(results, key=lambda x: -x["predicted_demand"])

    # ─────────────────────────────────────────────
    # UNIFIED DISPATCH
    # ─────────────────────────────────────────────
    def dispatch(self, trend_type: str, params: dict = None) -> dict:
        """Route a trend query to the right method."""
        params = params or {}
        dispatch_map = {
            "sales_trend":       lambda: self.sales_trend(**params),
            "hourly_rush":       lambda: self.hourly_rush(**params),
            "product_demand":    lambda: self.product_demand(**params),
            "seasonal_trend":    lambda: self.seasonal_trend(**params),
            "stock_depletion":   lambda: self.stock_depletion(**params),
            "smart_reorder":     lambda: self.smart_reorder(**params),
            "dead_stock":        lambda: self.dead_stock(**params),
            "profit_trend":      lambda: self.profit_trend(**params),
            "festival_trend":    lambda: self.festival_trend(**params),
            "market_basket":     lambda: self.market_basket(**params),
            "customer_pattern":  lambda: self.customer_pattern(**params),
            "auto_subscription": lambda: self.auto_subscription(**params),
            "weather_trend":     lambda: self.weather_trend(**params),
            "demand_stock_risk":  lambda: self.demand_stock_risk(**params),
        }
        fn = dispatch_map.get(trend_type)
        if fn:
            return fn()
        return {"error": f"Unknown trend: {trend_type}"}
    
    def calculate_accuracy_metrics(y_true, y_pred, task_type="regression"):
        """
        Computes the rich analytical metrics for your Kirana trends.
        """
        try:
            import numpy as np
            from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_recall_fscore_support
        except ImportError:
            # If sklearn is not available, return basic metrics
            return {"note": "sklearn not available for full metrics"}
        
        if task_type == "regression":
            # Used for Stock Depletion and Next-Purchase Dates
            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            return {"MAE": round(mae, 2), "RMSE": round(rmse, 2)}
        
        elif task_type == "classification":
            # Used for Churn and Dead Stock Classifiers
            precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')
            return {"Precision": round(precision, 2), "Recall": round(recall, 2), "F1": round(f1, 2)}
