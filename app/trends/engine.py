"""
VoiceSQL Trends Engine
Implements 13 analytical trend modules for Kirana Intelligence.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict
import math


class TrendsEngine:
    """
    Master engine for all 13 trend analyses.
    Called by the NLP pipeline when intent = TREND_QUERY.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ─────────────────────────────────────────────
    # 1. SALES TREND (Time-based)
    # ─────────────────────────────────────────────
    def sales_trend(self, days: int = 7) -> dict:
        """Total sales per day for the last N days."""
        conn = self._conn()
        cur = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT DATE(timestamp) as day,
                   SUM(quantity * price) as revenue,
                   COUNT(*) as orders
            FROM transactions
            WHERE timestamp >= ?
            GROUP BY day
            ORDER BY day
        """, (since,))
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
            "insight": f"Last {days} din mein {peak[0]} ko sabse zyada ₹{peak[1]:.0f} ki bikri hui."
        }

    # ─────────────────────────────────────────────
    # 2. HOURLY RUSH TREND
    # ─────────────────────────────────────────────
    def hourly_rush(self, days: int = 7) -> dict:
        """Orders per hour to identify peak times."""
        conn = self._conn()
        cur = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                   COUNT(*) as orders
            FROM transactions
            WHERE timestamp >= ?
            GROUP BY hour
            ORDER BY hour
        """, (since,))
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
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT t.item_name,
                   SUM(t.quantity) as total_qty,
                   SUM(t.quantity * t.price) as revenue
            FROM transactions t
            WHERE t.timestamp >= ?
            GROUP BY t.item_name
            ORDER BY total_qty DESC
            LIMIT ?
        """, (since, top_n))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "product_demand", "data": [], "insight": "Data nahi mila."}

        top = rows[0]
        return {
            "trend": "product_demand",
            "data": [{"item": r[0], "qty_sold": r[1], "revenue": r[2]} for r in rows],
            "top_item": top[0],
            "top_qty": top[1],
            "insight": f"{top[0]} sabse zyada bik raha hai — {top[1]} units last {days} din mein."
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
        since = (datetime.now() - timedelta(days=days_window)).strftime("%Y-%m-%d")

        # Get avg daily sales per item
        cur.execute("""
            SELECT item_name,
                   SUM(quantity) / ? as avg_daily
            FROM transactions
            WHERE timestamp >= ?
            GROUP BY item_name
        """, (days_window, since))
        sales_map = {r[0]: r[1] for r in cur.fetchall()}

        # Get current stock
        if item_name:
            cur.execute("SELECT name, quantity FROM inventory WHERE LOWER(name) LIKE LOWER(?)",
                        (f"%{item_name}%",))
        else:
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
        cutoff = (datetime.now() - timedelta(days=threshold_days)).strftime("%Y-%m-%d")
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

        return [{
            "item": r[0],
            "stock_qty": r[1],
            "last_sold": r[2] or "Never",
            "days_idle": (datetime.now() - datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S")).days
                         if r[2] else None,
            "recommendation": "Discount pe becho ya return karo"
        } for r in rows]

    # ─────────────────────────────────────────────
    # 8. PROFIT TREND
    # ─────────────────────────────────────────────
    def profit_trend(self, days: int = 30, top_n: int = 10) -> dict:
        """
        Profit = (selling_price - cost_price) × quantity
        Requires cost_price column in inventory.
        """
        conn = self._conn()
        cur = conn.cursor()
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute("""
            SELECT t.item_name,
                   SUM(t.quantity) as qty,
                   SUM(t.quantity * t.price) as revenue,
                   SUM(t.quantity * COALESCE(i.cost_price, t.price * 0.7)) as cogs,
                   SUM(t.quantity * (t.price - COALESCE(i.cost_price, t.price * 0.7))) as profit
            FROM transactions t
            LEFT JOIN inventory i ON LOWER(i.name) = LOWER(t.item_name)
            WHERE t.timestamp >= ?
            GROUP BY t.item_name
            ORDER BY profit DESC
            LIMIT ?
        """, (since, top_n))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {"trend": "profit", "data": [], "insight": "Profit data nahi hai."}

        top = rows[0]
        return {
            "trend": "profit",
            "data": [{
                "item": r[0], "qty": r[1],
                "revenue": round(r[2], 2), "cogs": round(r[3], 2),
                "profit": round(r[4], 2),
                "margin_pct": round((r[4] / r[2]) * 100, 1) if r[2] else 0
            } for r in rows],
            "top_item": top[0],
            "top_profit": round(top[4], 2),
            "insight": f"{top[0]} sabse zyada ₹{top[4]:.0f} ka profit de raha hai."
        }

    # ─────────────────────────────────────────────
    # 9. FESTIVAL TREND
    # ─────────────────────────────────────────────
    FESTIVALS = {
        "diwali": [("10-15", "11-15")],
        "holi":   [("02-25", "03-15")],
        "eid":    [("04-01", "04-10")],
        "christmas": [("12-20", "12-26")],
        "navratri": [("10-01", "10-12")],
    }

    def festival_trend(self, festival: str = "diwali") -> dict:
        """Compare sales during festival windows across years."""
        festival = festival.lower()
        windows = self.FESTIVALS.get(festival, self.FESTIVALS["diwali"])
        conn = self._conn()
        cur = conn.cursor()
        results = []
        for year in range(datetime.now().year - 2, datetime.now().year + 1):
            for start_md, end_md in windows:
                start = f"{year}-{start_md}"
                end = f"{year}-{end_md}"
                cur.execute("""
                    SELECT SUM(quantity * price) as revenue,
                           COUNT(*) as orders,
                           SUM(quantity) as units
                    FROM transactions
                    WHERE DATE(timestamp) BETWEEN ? AND ?
                """, (start, end))
                row = cur.fetchone()
                if row and row[0]:
                    results.append({
                        "year": year, "festival": festival,
                        "revenue": round(row[0], 2),
                        "orders": row[1], "units": row[2]
                    })
        conn.close()

        if not results:
            return {"trend": "festival", "festival": festival,
                    "data": [], "insight": f"{festival.title()} ka data nahi mila."}

        best = max(results, key=lambda r: r["revenue"])
        return {
            "trend": "festival",
            "festival": festival,
            "data": results,
            "best_year": best["year"],
            "insight": f"{festival.title()} {best['year']} mein sabse zyada ₹{best['revenue']:.0f} ki bikri hui."
        }

    # ─────────────────────────────────────────────
    # 10. MARKET BASKET TREND (Apriori-lite)
    # ─────────────────────────────────────────────
    def market_basket(self, min_support: int = 3, top_n: int = 10) -> list:
        """
        Find frequently co-purchased item pairs using
        a simplified Apriori pass on same-session transactions.
        Groups transactions within 5-minute windows as "baskets".
        """
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
            # Handle both ISO format (2026-03-10T14:40:44) and space format (2026-03-10 14:40:44)
            ts_str_normalized = ts_str[:19].replace('T', ' ')
            ts = datetime.strptime(ts_str_normalized, "%Y-%m-%d %H:%M:%S")
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
        for basket in baskets:
            unique = list(set(basket))
            for i in range(len(unique)):
                for j in range(i + 1, len(unique)):
                    pair = tuple(sorted([unique[i], unique[j]]))
                    pair_count[pair] += 1

        # Filter by min_support and rank
        frequent = [(p, c) for p, c in pair_count.items() if c >= min_support]
        frequent.sort(key=lambda x: -x[1])

        return [{
            "item_a": p[0][0], "item_b": p[0][1],
            "co_occurrences": p[1],
            "insight": f"{p[0][0]} aur {p[0][1]} aksar saath bikते hain ({p[1]} baar)"
        } for p in frequent[:top_n]]

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
    def auto_subscription(self, customer_id: str) -> dict:
        """
        Predict next purchase date per item using:
            next_purchase = last_purchase + avg_gap_days
        """
        conn = self._conn()
        cur = conn.cursor()
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
            "predictions": predictions
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
        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        results = []
        for kw in keywords:
            cur.execute("""
                SELECT item_name, SUM(quantity) as qty,
                       SUM(quantity * price) as revenue
                FROM transactions
                WHERE LOWER(item_name) LIKE LOWER(?) AND timestamp >= ?
                GROUP BY item_name
                ORDER BY qty DESC
            """, (f"%{kw}%", since))
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
        }
        fn = dispatch_map.get(trend_type)
        if fn:
            return fn()
        return {"error": f"Unknown trend: {trend_type}"}
    
    import numpy as np
    from sklearn.metrics import mean_absolute_error, mean_squared_error, precision_recall_fscore_support

    def calculate_accuracy_metrics(y_true, y_pred, task_type="regression"):
        """
        Computes the rich analytical metrics for your Kirana trends.
        """
        if task_type == "regression":
            # Used for Stock Depletion and Next-Purchase Dates
            mae = mean_absolute_error(y_true, y_pred)
            rmse = np.sqrt(mean_squared_error(y_true, y_pred))
            return {"MAE": round(mae, 2), "RMSE": round(rmse, 2)}
        
        elif task_type == "classification":
            # Used for Churn and Dead Stock Classifiers
            precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average='binary')
            return {"Precision": round(precision, 2), "Recall": round(recall, 2), "F1": round(f1, 2)}
