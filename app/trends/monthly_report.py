"""
Monthly Report Generator
========================
Generates a full shop performance report for any given month.
Can be triggered manually or via scheduler.

Usage:
    python app/trends/monthly_report.py              # Last month
    python app/trends/monthly_report.py 2025 3       # March 2025

Scheduled (add to your main.py or a cron job):
    from app.trends.monthly_report import maybe_generate_monthly_report
    maybe_generate_monthly_report(db_path, reports_dir)
"""

import sqlite3
import os
import json
from datetime import datetime, date
from calendar import monthrange
from collections import defaultdict

from config import TRENDS_DB_PATH
from .engine import TrendsEngine
from .customer_engine import compute_rfm, compute_ltv, predict_churn, visit_frequency


# ─────────────────────────────────────────────────────────────────────────────
# Core report builder
# ─────────────────────────────────────────────────────────────────────────────

def generate_monthly_report(db_path: str, year: int, month: int,
                             save_dir: str = "reports") -> dict:
    """
    Builds a complete monthly report dict.
    Also saves it as JSON + a human-readable .txt file.
    """
    engine = TrendsEngine(db_path)
    month_start = f"{year}-{month:02d}-01"
    _, last_day = monthrange(year, month)
    month_end   = f"{year}-{month:02d}-{last_day}"
    month_label = datetime(year, month, 1).strftime("%B %Y")  # e.g. "March 2025"

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # Detect whether transactions has a price column
    cur.execute("PRAGMA table_info(transactions)")
    tx_cols = {r[1] for r in cur.fetchall()}
    has_price = "price" in tx_cols

    # Revenue expression — falls back to quantity-only if no price column
    rev_expr = "SUM(quantity * price)" if has_price else "0"

    # ── 1. Revenue summary (sales only) ──────────────────────────────────────
    cur.execute(f"""
        SELECT COUNT(*) as orders,
               SUM(quantity)  as units_sold,
               {rev_expr}     as revenue
        FROM transactions
        WHERE type = 'sale'
          AND DATE(timestamp) BETWEEN ? AND ?
    """, (month_start, month_end))
    rev = cur.fetchone()
    total_orders   = rev[0] or 0
    total_units    = rev[1] or 0
    total_revenue  = rev[2] or 0.0

    # ── 2. Daily breakdown ───────────────────────────────────────────────────
    cur.execute(f"""
        SELECT DATE(timestamp) as day,
               {rev_expr}      as revenue,
               COUNT(*)        as orders
        FROM transactions
        WHERE type = 'sale'
          AND DATE(timestamp) BETWEEN ? AND ?
        GROUP BY day ORDER BY day
    """, (month_start, month_end))
    daily = [{"day": r[0], "revenue": round(r[1] or 0, 2), "orders": r[2]}
             for r in cur.fetchall()]

    peak_day = max(daily, key=lambda d: d["revenue"]) if daily else {}

    # ── 3. Top 5 products by units sold ──────────────────────────────────────
    cur.execute(f"""
        SELECT item_name,
               SUM(quantity)   as qty,
               {rev_expr}      as revenue
        FROM transactions
        WHERE type = 'sale'
          AND DATE(timestamp) BETWEEN ? AND ?
        GROUP BY item_name ORDER BY qty DESC LIMIT 5
    """, (month_start, month_end))
    top_products = [{"item": r[0], "qty": r[1], "revenue": round(r[2] or 0, 2)}
                    for r in cur.fetchall()]

    # ── 4. Profit (uses cost_price if available, else 30% margin estimate) ───
    if has_price:
        cur.execute("""
            SELECT SUM(t.quantity * (t.price - COALESCE(i.cost_price, t.price * 0.7))) as profit
            FROM transactions t
            LEFT JOIN inventory i ON LOWER(i.name) = LOWER(t.item_name)
            WHERE t.type = 'sale'
              AND DATE(t.timestamp) BETWEEN ? AND ?
        """, (month_start, month_end))
    else:
        # No price data — profit unknown
        cur.execute("SELECT 0")
    profit_row   = cur.fetchone()
    total_profit = round(profit_row[0] or 0.0, 2)
    margin_pct   = round((total_profit / total_revenue * 100), 1) if total_revenue else 0

    # ── 5. Dead stock ────────────────────────────────────────────────────────
    dead = engine.dead_stock(threshold_days=30)

    # ── 6. Critical stock alerts ─────────────────────────────────────────────
    depletions = engine.stock_depletion()
    critical   = [d for d in depletions if d.get("days_until_stockout") and
                  d["days_until_stockout"] <= 7]

    # ── 7. Best selling hour ─────────────────────────────────────────────────
    cur.execute("""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour,
               COUNT(*) as orders
        FROM transactions
        WHERE type = 'sale'
          AND DATE(timestamp) BETWEEN ? AND ?
        GROUP BY hour ORDER BY orders DESC LIMIT 1
    """, (month_start, month_end))
    peak_hour_row = cur.fetchone()
    peak_hour = f"{peak_hour_row[0]:02d}:00–{peak_hour_row[0]+1:02d}:00" if peak_hour_row else "N/A"

    # ── 8. Unique customers (if customer_id column exists) ───────────────────
    if "customer_id" in tx_cols:
        cur.execute("""
            SELECT COUNT(DISTINCT customer_id) as customers
            FROM transactions
            WHERE type = 'sale'
              AND DATE(timestamp) BETWEEN ? AND ?
              AND customer_id IS NOT NULL
        """, (month_start, month_end))
        unique_customers = (cur.fetchone() or [0])[0]
    else:
        unique_customers = 0

    conn.close()

    # ── 9. Customer analytics (RFM, churn, LTV, visit frequency) ────────────
    rfm_data = compute_rfm(db_path)
    segment_counts: dict[str, int] = defaultdict(int)
    for r in rfm_data:
        seg = r.get("segment") or "Unknown"
        segment_counts[seg] += 1

    churn_risks = predict_churn(db_path)
    ltv_ranking = compute_ltv(db_path)
    visit_stats = visit_frequency(db_path)

    # ── Assemble report ──────────────────────────────────────────────────────
    report = {
        "meta": {
            "shop":         "Meri Kirana Dukaan",
            "month":        month_label,
            "generated_at": datetime.now().isoformat(),
            "period":       f"{month_start} to {month_end}",
        },
        "summary": {
            "total_revenue":   round(total_revenue, 2),
            "total_profit":    total_profit,
            "margin_pct":      margin_pct,
            "total_orders":    total_orders,
            "total_units_sold": int(total_units or 0),
            "unique_customers": unique_customers,
            "peak_day":         peak_day,
            "peak_hour":        peak_hour,
        },
        "daily_breakdown":  daily,
        "top_products":     top_products,
        "dead_stock":       dead[:5],
        "critical_stock":   critical,
        "customers": {
            "segments": dict(segment_counts),
            "rfm": rfm_data,
            "top_churn_risks": churn_risks[:10],
            "top_ltv_customers": ltv_ranking[:10],
            "visit_frequency": visit_stats[:10],
        },
    }

    # ── Save files ───────────────────────────────────────────────────────────
    os.makedirs(save_dir, exist_ok=True)
    slug = f"{year}_{month:02d}"

    json_path = os.path.join(save_dir, f"report_{slug}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    txt_path = os.path.join(save_dir, f"report_{slug}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(_render_text(report))

    print(f"📄 Report saved: {txt_path}")
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Human-readable text renderer
# ─────────────────────────────────────────────────────────────────────────────

def _render_text(r: dict) -> str:
    m  = r["meta"]
    s  = r["summary"]
    sep = "─" * 52

    lines = [
        "╔════════════════════════════════════════════════════╗",
        f"║   📊 MONTHLY REPORT — {m['month']:<28} ║",
        "╚════════════════════════════════════════════════════╝",
        "",
        f"  Dukaan  : {m['shop']}",
        f"  Period  : {m['period']}",
        f"  Generated: {m['generated_at'][:19]}",
        "",
        sep,
        "  💰 FINANCIAL SUMMARY",
        sep,
        f"  Total Revenue   : ₹{s['total_revenue']:,.2f}",
        f"  Total Profit    : ₹{s['total_profit']:,.2f}",
        f"  Profit Margin   : {s['margin_pct']}%",
        f"  Total Orders    : {s['total_orders']}",
        f"  Units Sold      : {s['total_units_sold']}",
        f"  Unique Customers: {s['unique_customers']}",
        "",
        sep,
        "  ⏰ PEAK PERFORMANCE",
        sep,
        f"  Peak Day  : {s['peak_day'].get('day', 'N/A')} "
        f"(₹{s['peak_day'].get('revenue', 0):,.0f})",
        f"  Peak Hour : {s['peak_hour']}",
        "",
        sep,
        "  🏆 TOP 5 PRODUCTS",
        sep,
    ]

    for i, p in enumerate(r["top_products"], 1):
        lines.append(f"  {i}. {p['item']:<18} {p['qty']:>5} units  ₹{p['revenue']:>8,.2f}")

    lines += ["", sep, "  📦 DAILY SALES (Last 7 days shown)", sep]
    for d in r["daily_breakdown"][-7:]:
        bar = "█" * min(int(d["revenue"] / 500), 20)
        lines.append(f"  {d['day']}  {bar:<20} ₹{d['revenue']:,.0f}")

    if r["critical_stock"]:
        lines += ["", sep, "  🔴 CRITICAL STOCK ALERTS", sep]
        for item in r["critical_stock"]:
            lines.append(f"  ⚠️  {item['item']}: ~{item['days_until_stockout']} din bacha hai!")

    if r["dead_stock"]:
        lines += ["", sep, "  🧊 DEAD STOCK (30+ days no sale)", sep]
        for item in r["dead_stock"][:5]:
            lines.append(f"  •  {item['item']}: Last sold {item['last_sold']}")

    lines += [
        "",
        sep,
        "  ✅ Report complete. Agla mahina bhi badhiya ho!",
        sep,
        "",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Auto-trigger: call this at startup — generates report if new month started
# ─────────────────────────────────────────────────────────────────────────────

def maybe_generate_monthly_report(db_path: str, reports_dir: str = "reports") -> bool:
    """
    Call this once at app startup.
    If today is the 1st–3rd of the month AND last month's report doesn't exist yet,
    it auto-generates it.

    Returns True if a report was generated.
    """
    today = date.today()
    if today.day > 3:
        return False  # Only generate in first 3 days of new month

    # Figure out last month
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1

    slug      = f"{year}_{month:02d}"
    txt_path  = os.path.join(reports_dir, f"report_{slug}.txt")

    if os.path.exists(txt_path):
        return False  # Already generated

    print(f"\n📊 Auto-generating monthly report for {year}-{month:02d}...")
    generate_monthly_report(db_path, year, month, reports_dir)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    db = str(TRENDS_DB_PATH)
    if len(sys.argv) == 3:
        y, m = int(sys.argv[1]), int(sys.argv[2])
    else:
        today = date.today()
        y = today.year
        m = today.month - 1 if today.month > 1 else 12
        if m == 12:
            y -= 1

    report = generate_monthly_report(db, y, m)
    print(_render_text(report))
