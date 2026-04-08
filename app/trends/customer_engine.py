import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional


def get_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── 1. RFM Segmentation ────────────────────────────────────────────────────────
def compute_rfm(db_path: str) -> list[dict]:
    """Score every customer on Recency, Frequency, Monetary."""
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT
            customer_id,
            CAST(julianday('now') - julianday(MAX(timestamp)) AS INTEGER) AS recency_days,
            COUNT(*)                                                        AS frequency,
            SUM(price * quantity)                                           AS monetary
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
    """).fetchall()
    conn.close()

    results = []
    for r in rows:
        if not r["customer_id"]:
            continue
        r_score = 5 if r["recency_days"] <= 7  else 4 if r["recency_days"] <= 14 else \
                  3 if r["recency_days"] <= 30 else 2 if r["recency_days"] <= 60 else 1
        f_score = 5 if r["frequency"] >= 20 else 4 if r["frequency"] >= 10 else \
                  3 if r["frequency"] >= 5  else 2 if r["frequency"] >= 2  else 1
        m_score = 5 if r["monetary"] >= 5000 else 4 if r["monetary"] >= 2000 else \
                  3 if r["monetary"] >= 500  else 2 if r["monetary"] >= 100  else 1
        rfm     = (r_score + f_score + m_score) / 3

        segment = (
            "Champion"       if rfm >= 4.5 else
            "Loyal"          if rfm >= 3.5 else
            "Potential"      if rfm >= 2.5 else
            "At Risk"        if rfm >= 1.5 else
            "Lost"
        )
        results.append({
            "customer_id":    r["customer_id"],
            "recency_days":   r["recency_days"],
            "frequency":      r["frequency"],
            "monetary":       round(r["monetary"], 2),
            "rfm_score":      round(rfm, 2),
            "segment":        segment,
        })
    return results


def save_rfm_to_db(db_path: str):
    """Persist RFM scores into customer_segments table."""
    data = compute_rfm(db_path)
    conn = get_conn(db_path)
    for d in data:
        conn.execute("""
            INSERT INTO customer_segments
                (customer_id, rfm_score, segment, recency_days, frequency_count, monetary_total, updated_at)
            VALUES (?,?,?,?,?,?, datetime('now'))
            ON CONFLICT(customer_id) DO UPDATE SET
                rfm_score=excluded.rfm_score, segment=excluded.segment,
                recency_days=excluded.recency_days, frequency_count=excluded.frequency_count,
                monetary_total=excluded.monetary_total, updated_at=excluded.updated_at
        """, (d["customer_id"], d["rfm_score"], d["segment"],
              d["recency_days"], d["frequency"], d["monetary"]))
    conn.commit()
    conn.close()


# ── 2. Customer LTV ────────────────────────────────────────────────────────────
def compute_ltv(db_path: str, months_ahead: int = 6) -> list[dict]:
    """Estimate future LTV = avg_monthly_spend × months_ahead × retention_factor."""
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT
            customer_id,
            SUM(price * quantity)                         AS total_spend,
            COUNT(DISTINCT strftime('%Y-%m', timestamp))  AS active_months,
            CAST(julianday('now') - julianday(MIN(timestamp)) AS INTEGER) AS tenure_days
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
    """).fetchall()
    conn.close()

    results = []
    for r in rows:
        active_months   = max(r["active_months"], 1)
        avg_monthly     = r["total_spend"] / active_months
        # Simple retention: longer tenure → higher factor
        retention       = min(0.95, 0.6 + (r["tenure_days"] / 365) * 0.1)
        predicted_ltv   = avg_monthly * months_ahead * retention
        results.append({
            "customer_id":   r["customer_id"],
            "total_spend":   round(r["total_spend"], 2),
            "avg_monthly":   round(avg_monthly, 2),
            "ltv_6m":        round(predicted_ltv, 2),
        })
    return sorted(results, key=lambda x: -x["ltv_6m"])


# ── 3. Churn Prediction ────────────────────────────────────────────────────────
def predict_churn(db_path: str, churn_threshold_days: int = 30) -> list[dict]:
    """Flag customers who haven't bought in `churn_threshold_days` days."""
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT
            customer_id,
            MAX(timestamp)                                                  AS last_purchase,
            CAST(julianday('now') - julianday(MAX(timestamp)) AS INTEGER)   AS days_silent,
            AVG(CAST(julianday('now') - julianday(timestamp) AS INTEGER))   AS avg_gap_days
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id
    """).fetchall()
    conn.close()

    at_risk = []
    for r in rows:
        if not r["customer_id"]:
            continue
        if r["days_silent"] >= churn_threshold_days:
            risk = min(1.0, r["days_silent"] / (churn_threshold_days * 2))
            at_risk.append({
                "customer_id":   r["customer_id"],
                "last_purchase": r["last_purchase"],
                "days_silent":   r["days_silent"],
                "churn_risk":    round(risk, 2),
                "avg_gap_days":  round(r["avg_gap_days"] or 0, 1),
            })
    return sorted(at_risk, key=lambda x: -x["churn_risk"])


# ── 4. Visit Frequency ─────────────────────────────────────────────────────────
def visit_frequency(db_path: str) -> list[dict]:
    """Average days between visits per customer."""
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT customer_id, timestamp
        FROM transactions
        WHERE customer_id IS NOT NULL
        ORDER BY customer_id, timestamp
    """).fetchall()
    conn.close()

    visits: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        visits[r["customer_id"]].append(r["timestamp"])

    results = []
    for cid, ts_list in visits.items():
        if len(ts_list) < 2:
            continue
        dates   = sorted(datetime.fromisoformat(t[:19]) for t in ts_list)
        gaps    = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_gap = sum(gaps) / len(gaps)
        results.append({
            "customer_id":  cid,
            "visit_count":  len(ts_list),
            "avg_gap_days": round(avg_gap, 1),
            "next_expected": (dates[-1] + timedelta(days=avg_gap)).strftime("%Y-%m-%d"),
        })
    return sorted(results, key=lambda x: x["avg_gap_days"])


# ── 5. Basket Size Trend ───────────────────────────────────────────────────────
def basket_size_trend(db_path: str) -> list[dict]:
    """Average items (distinct lines) per visit per customer."""
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT
            customer_id,
            strftime('%Y-%m-%d', timestamp) AS visit_date,
            COUNT(DISTINCT item_name)        AS items_in_basket,
            SUM(price * quantity)            AS basket_value
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id, visit_date
    """).fetchall()
    conn.close()

    summary: dict[str, list] = defaultdict(list)
    for r in rows:
        summary[r["customer_id"]].append({
            "date":  r["visit_date"],
            "items": r["items_in_basket"],
            "value": r["basket_value"],
        })

    return [{
        "customer_id":     cid,
        "avg_items":       round(sum(v["items"] for v in visits) / len(visits), 1),
        "avg_basket_value":round(sum(v["value"] for v in visits) / len(visits), 2),
        "visit_count":     len(visits),
    } for cid, visits in summary.items()]


# ── 6. Cohort Retention ────────────────────────────────────────────────────────
def cohort_retention(db_path: str) -> list[dict]:
    """
    Month-1 vs Month-N retention.
    Groups customers by their first-purchase month (cohort),
    then checks how many are still active in each subsequent month.
    """
    conn = get_conn(db_path)
    rows = conn.execute("""
        SELECT customer_id, strftime('%Y-%m', timestamp) AS month
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id, month
    """).fetchall()
    conn.close()

    cohort_map: dict[str, str]       = {}   # customer_id → first month
    activity:   dict[str, set[str]]  = defaultdict(set)

    for r in rows:
        cid, month = r["customer_id"], r["month"]
        activity[cid].add(month)
        if cid not in cohort_map or month < cohort_map[cid]:
            cohort_map[cid] = month

    cohorts: dict[str, list[str]] = defaultdict(list)
    for cid, first_month in cohort_map.items():
        cohorts[first_month].append(cid)

    results = []
    for cohort_month, members in sorted(cohorts.items()):
        size = len(members)
        monthly_retention = {}
        all_months = sorted({m for cid in members for m in activity[cid]})
        for m in all_months:
            retained = sum(1 for cid in members if m in activity[cid])
            monthly_retention[m] = round(retained / size * 100, 1)
        results.append({
            "cohort":     cohort_month,
            "size":       size,
            "retention":  monthly_retention,
        })
    return results


# ── 7. Next Purchase Prediction ────────────────────────────────────────────────
def predict_next_purchases(db_path: str, top_n_customers: int = 20) -> list[dict]:
    """
    For each frequent customer, predict which items they'll buy next
    and roughly when, based on their personal purchase history.
    """
    conn = get_conn(db_path)

    # Get per-customer item purchase intervals
    rows = conn.execute("""
        SELECT customer_id, item_name,
               strftime('%Y-%m-%d', timestamp) AS buy_date,
               SUM(quantity) AS qty
        FROM transactions
        WHERE customer_id IS NOT NULL
        GROUP BY customer_id, item_name, buy_date
        ORDER BY customer_id, item_name, buy_date
    """).fetchall()
    conn.close()

    # Build timeline per (customer, item)
    timeline: dict[tuple, list] = defaultdict(list)
    for r in rows:
        timeline[(r["customer_id"], r["item_name"])].append({
            "date": r["buy_date"],
            "qty":  r["qty"],
        })

    predictions = []
    for (cid, item), events in timeline.items():
        if len(events) < 2:
            continue
        dates = sorted(datetime.strptime(e["date"], "%Y-%m-%d") for e in events)
        gaps  = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_gap     = sum(gaps) / len(gaps)
        avg_qty     = sum(e["qty"] for e in events) / len(events)
        last_date   = dates[-1]
        days_since  = (datetime.now() - last_date).days
        # Confidence: higher if consistent gap and bought recently
        std         = (sum((g - avg_gap)**2 for g in gaps) / len(gaps)) ** 0.5
        confidence  = max(0.1, min(0.99, 1 - std / (avg_gap + 1)))
        next_date   = last_date + timedelta(days=avg_gap)

        predictions.append({
            "customer_id":    cid,
            "item":           item,
            "avg_qty":        round(avg_qty, 1),
            "avg_gap_days":   round(avg_gap, 1),
            "days_since_last":days_since,
            "next_expected":  next_date.strftime("%Y-%m-%d"),
            "overdue":        days_since > avg_gap,
            "confidence":     round(confidence, 2),
        })

    return sorted(predictions, key=lambda x: (-x["confidence"], x["next_expected"]))


def save_predictions_to_db(db_path: str):
    """Persist predictions so you can auto-generate delivery orders."""
    preds = predict_next_purchases(db_path)
    conn  = get_conn(db_path)
    conn.execute("DELETE FROM predicted_orders WHERE fulfilled=0")
    for p in preds:
        conn.execute("""
            INSERT INTO predicted_orders
                (customer_id, item_name, predicted_qty, predicted_date, confidence)
            VALUES (?,?,?,?,?)
        """, (p["customer_id"], p["item"], p["avg_qty"], p["next_expected"], p["confidence"]))
    conn.commit()
    conn.close()


# ── 8. Loyalty Scoring ─────────────────────────────────────────────────────────
def loyalty_scores(db_path: str) -> list[dict]:
    """Recency × Frequency × Value composite score (0–100)."""
    rfm = compute_rfm(db_path)
    if not rfm:
        return []
    max_m = max(r["monetary"] for r in rfm) or 1
    results = []
    for r in rfm:
        recency_score   = max(0, 100 - r["recency_days"] * 2)
        frequency_score = min(100, r["frequency"] * 5)
        monetary_score  = (r["monetary"] / max_m) * 100
        loyalty         = round(
            recency_score * 0.3 + frequency_score * 0.4 + monetary_score * 0.3, 1
        )
        results.append({
            "customer_id":    r["customer_id"],
            "loyalty_score":  loyalty,
            "segment":        r["segment"],
            "recency_days":   r["recency_days"],
        })
    return sorted(results, key=lambda x: -x["loyalty_score"])


# ── 9. Delivery Order Generator ────────────────────────────────────────────────
def generate_delivery_orders(db_path: str, days_ahead: int = 3) -> list[dict]:
    """
    Main output for your use-case: which customers need what delivered soon.
    Returns ready-to-act delivery bundles.
    """
    conn = get_conn(db_path)
    cutoff = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    rows   = conn.execute("""
        SELECT p.customer_id, p.item_name, p.predicted_qty, p.predicted_date, p.confidence,
               c.name, c.phone, c.locality
        FROM predicted_orders p
        LEFT JOIN customers c ON p.customer_id = c.customer_id
        WHERE p.predicted_date <= ? AND p.fulfilled = 0 AND p.confidence >= 0.5
        ORDER BY p.predicted_date, p.customer_id
    """, (cutoff,)).fetchall()
    conn.close()

    # Bundle per customer
    bundles: dict[str, dict] = {}
    for r in rows:
        cid = r["customer_id"]
        if cid not in bundles:
            bundles[cid] = {
                "customer_id": cid,
                "name":        r["name"] or cid,
                "phone":       r["phone"],
                "locality":    r["locality"],
                "items":       [],
                "earliest":    r["predicted_date"],
            }
        bundles[cid]["items"].append({
            "item":       r["item_name"],
            "quantity":        r["predicted_qty"],
            "confidence": r["confidence"],
            "by_date":    r["predicted_date"],
        })

    return list(bundles.values())   