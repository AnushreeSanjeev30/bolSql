import sqlite3
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict


def exponential_moving_average(values, alpha=0.6):
    ema = values[0]
    for v in values[1:]:
        ema = alpha * v + (1 - alpha) * ema
    return ema


def predict_demand_ema(db_path: str, days_ahead: int = 3):
    """
    Predict demand using EMA (customer behavior based)
    """

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT customer_id, item_name,
               strftime('%Y-%m-%d', timestamp) as date,
               SUM(quantity)
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id, item_name, date
        ORDER BY customer_id, item_name, date
    """)

    rows = cur.fetchall()
    conn.close()

    timeline = defaultdict(list)

    for cid, item, date, qty in rows:
        timeline[(cid, item)].append({
            "date": datetime.strptime(date, "%Y-%m-%d"),
            "qty": qty
        })

    future_demand = defaultdict(float)
    cutoff = datetime.now() + timedelta(days=days_ahead)

    for (cid, item), events in timeline.items():
        if len(events) < 3:
            continue

        events = sorted(events, key=lambda x: x["date"])

        gaps = [(events[i+1]["date"] - events[i]["date"]).days
                for i in range(len(events)-1)]

        gap_ema = exponential_moving_average(gaps)

        qtys = [e["qty"] for e in events]
        qty_ema = exponential_moving_average(qtys)

        last_date = events[-1]["date"]
        next_date = last_date + timedelta(days=gap_ema)

        if next_date <= cutoff:

            # trend boost
            if len(qtys) >= 3:
                trend = (qtys[-1] - qtys[-3]) / max(1, qtys[-3])
                trend_factor = 1 + max(0, trend)
            else:
                trend_factor = 1

            predicted_qty = qty_ema * trend_factor

            std = np.std(gaps)
            confidence = max(0.3, min(1.0, 1 - std / (gap_ema + 1)))

            future_demand[item] += predicted_qty * confidence

    return dict(future_demand)
