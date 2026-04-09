"""
Trend Response Formatter
Converts raw trend data → friendly Hinglish/Tanglish text for the terminal / voice output.
"""

from typing import Union


def format_trend_response(trend_type: str, data: Union[dict, list], language: str = "hinglish") -> str:
    """Main entry point — routes to the right formatter."""
    formatters = {
        "sales_trend":       _fmt_sales,
        "hourly_rush":       _fmt_hourly,
        "product_demand":    _fmt_demand,
        "seasonal_trend":    _fmt_seasonal,
        "stock_depletion":   _fmt_depletion,
        "smart_reorder":     _fmt_reorder,
        "dead_stock":        _fmt_dead,
        "profit_trend":      _fmt_profit,
        "festival_trend":    _fmt_festival,
        "market_basket":     _fmt_basket,
        "customer_pattern":  _fmt_customer,
        "auto_subscription": _fmt_subscription,
        "weather_trend":     _fmt_weather,
        "demand_stock_risk": _fmt_demand_stock,
    }
    fn = formatters.get(trend_type, lambda d, l: str(d))
    return fn(data, language)


def _fmt_sales(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        if language == "tamil":
            return "📊 Sales data available illa."
        else:
            return "📊 Sales data not available."
    if language == "tamil":
        lines = [f"📊 Last {d['days']} Days Sales Trend:\n"]
    else:
        lines = [f"📊 Last {d['days']} Days Sales Trend:\n"]
    for row in d["data"]:
        lines.append(f"  {row['day']}: ₹{row['revenue']:.0f} ({row['orders']} orders)")
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_hourly(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        if language == "tamil":
            return "🕐 Hourly data illa."
        else:
            return "🕐 Hourly data not found."
    if language == "tamil":
        lines = ["🕐 Hourly Rush Analysis:\n"]
    else:
        lines = ["🕐 Hourly Rush Analysis:\n"]
    for row in d["data"]:
        bar = "█" * min(int(row["orders"] / 2), 20)
        lines.append(f"  {row['hour']:02d}:00  {bar} ({row['orders']})")
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_demand(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        if language == "tamil":
            return "📦 Demand data illa."
        else:
            return "📦 Demand data not found."
    if language == "tamil":
        lines = ["📦 Top Selling Products:\n"]
    else:
        lines = ["📦 Top Selling Products:\n"]
    for i, row in enumerate(d["data"][:5], 1):
        lines.append(f"  {i}. {row['item']}: {row['qty_sold']} units (₹{row['revenue']:.0f})")
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_seasonal(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        if language == "tamil":
            return "🌦️ Seasonal data illa."
        else:
            return "🌦️ Seasonal data not found."
    lines = [f"🌦️ Seasonal Trend — {d.get('label', '')}:\n"]
    for row in d["data"]:
        lines.append(f"  {row['month']}: {row['qty']} units (₹{row['revenue']:.0f})")
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_depletion(items: list, language: str = "hinglish") -> str:
    if not items:
        if language == "tamil":
            return "🧊 All items stock fine."
        else:
            return "🧊 All items stock fine."
    if language == "tamil":
        lines = ["⚠️  Stock Depletion Alert:\n"]
    else:
        lines = ["⚠️  Stock Depletion Alert:\n"]
    for item in items[:8]:
        days = item["days_until_stockout"]
        day_str = f"{days} days" if days else "∞"
        lines.append(
            f"  {item['urgency']}  {item['item']}: "
            f"{item['current_stock']} units left → ~{day_str}"
        )
    return "\n".join(lines)


def _fmt_reorder(items: list, language: str = "hinglish") -> str:
    if not items:
        if language == "tamil":
            return "✅ Reorder needed illa."
        else:
            return "✅ No reorder needed."
    if language == "tamil":
        lines = ["🛒 Smart Reorder List:\n"]
        for item in items[:8]:
            lines.append(
                f"  • {item['item']}: {item['reorder_qty']} units order panna "
                f"[{item['urgency']}]"
            )
        lines.append("\n💡 Quantities calculate pannathu lead time aur safety stock based.")
    else:
        lines = ["🛒 Smart Reorder List:\n"]
        for item in items[:8]:
            lines.append(
                f"  • {item['item']}: {item['reorder_qty']} units order "
                f"[{item['urgency']}]"
            )
        lines.append("\n💡 Quantities calculated based on lead time and safety stock.")
    return "\n".join(lines)


def _fmt_dead(items: list, language: str = "hinglish") -> str:
    if not items:
        if language == "tamil":
            return "✅ No dead stock."
        else:
            return "✅ No dead stock."
    if language == "tamil":
        lines = ["🧊 Dead Stock Alert:\n"]
        for item in items[:6]:
            idle = f"{item['days_idle']} days" if item["days_idle"] else "Never sold"
            lines.append(f"  ⚠️  {item['item']}: {item['stock_qty']} units — Last sold: {item['last_sold']} ({idle})")
        lines.append("\n💡 Give discount or return to supplier.")
    else:
        lines = ["🧊 Dead Stock Alert:\n"]
        for item in items[:6]:
            idle = f"{item['days_idle']} days" if item["days_idle"] else "Never sold"
            lines.append(f"  ⚠️  {item['item']}: {item['stock_qty']} units — Last sold: {item['last_sold']} ({idle})")
        lines.append("\n💡 Offer discount or return to supplier.")
    return "\n".join(lines)


def _fmt_profit(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        if language == "tamil":
            return "💰 Profit data illa."
        else:
            return "💰 Profit data not found."
    if language == "tamil":
        lines = ["💰 Profit Analysis:\n"]
    else:
        lines = ["💰 Profit Analysis:\n"]
    for row in d["data"][:5]:
        lines.append(
            f"  {row['item']}: ₹{row['profit']:.0f} profit "
            f"({row['margin_pct']}% margin) on {row['qty']} units"
        )
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_festival(d: dict, language: str = "hinglish") -> str:
    if not d.get("data"):
        return f"🎉 {d.get('festival', 'Festival')} data not found."
    lines = [f"🎉 {d['festival'].title()} Sales History:\n"]
    for row in d["data"]:
        lines.append(f"  {row['year']}: ₹{row['revenue']:.0f} ({row['orders']} orders, {row['units']} units)")
    lines.append(f"\n✅ {d['insight']}")
    return "\n".join(lines)


def _fmt_basket(data: Union[dict, list], language: str = "hinglish") -> str:
    # Handle new dict format with product-specific data
    if isinstance(data, dict):
        items = data.get("data", [])
        product = data.get("product")
        insight = data.get("insight", "")
        
        if not items:
            if language == "tamil":
                return f"🛒 {insight or 'Market basket data illa.'}"
            else:
                return f"🛒 {insight or 'Market basket data not found.'}"
        
        if language == "tamil":
            lines = ["🛒 Frequently Bought Together:\n"]
            for item in items[:10]:
                if "pair" in item:
                    # Display count of times bought together
                    lines.append(f"  • {item['pair']} ({item.get('count', 0)} times)")
                else:
                    lines.append(f"  • {item.get('item', item)} ({item.get('count', 0)} times)")
            
            if insight:
                # Ensure Tanglish insight
                lines.append(f"\n✅ Most popular combination: {insight}")
            else:
                lines.append("\n💡 Place together or create combo offers.")
        else:
            lines = ["🛒 Frequently Bought Together:\n"]
            for item in items[:10]:
                if "pair" in item:
                    lines.append(f"  • {item['pair']} ({item.get('count', 0)} times)")
                else:
                    lines.append(f"  • {item.get('item', item)} ({item.get('count', 0)} times)")
            
            if insight:
                lines.append(f"\n✅ Most popular combination: {insight}")
            else:
                lines.append("\n💡 Place together or create combo offers.")
        return "\n".join(lines)
    
    # Handle old list format
    if not data:
        if language == "tamil":
            return "🛒 Market basket data illa. More transactions needed."
        else:
            return "🛒 Market basket data not found. More transactions needed."
    
    if language == "tamil":
        lines = ["🛒 Frequently Bought Together:\n"]
        for item in data[:6]:
            lines.append(f"  • {item['item_a']} + {item['item_b']} ({item['co_occurrences']} times)")
        lines.append("\n💡 Place together or create combo offers.")
    else:
        lines = ["🛒 Frequently Bought Together:\n"]
        for item in data[:6]:
            lines.append(f"  • {item['item_a']} + {item['item_b']} ({item['co_occurrences']} times together)")
        lines.append("\n💡 Place together or create combo offers.")
    return "\n".join(lines)
    return "\n".join(lines)


def _fmt_customer(d: dict, language: str = "hinglish") -> str:
    if "top_customers" in d:
        if language == "tamil":
            lines = ["👤 Top Customers:\n"]
        else:
            lines = ["👤 Top Customers:\n"]
        for c in d["top_customers"][:5]:
            lines.append(
                f"  {c['customer']}: {c['orders']} orders, "
                f"₹{c['spent']:.0f} spent, {c['unique_items']} unique items"
            )
        return "\n".join(lines)
    if language == "tamil":
        lines = [f"👤 Customer Pattern — {d.get('customer', '')}:\n"]
    else:
        lines = [f"👤 Customer Pattern — {d.get('customer', '')}:\n"]
    for item in d.get("items", []):
        lines.append(f"  • {item['item']}: {item['frequency']} times bought")
    return "\n".join(lines)


def _fmt_subscription(d: dict, language: str = "hinglish") -> str:
    # Handle both old "predictions" and new "data" keys
    preds = d.get("data", d.get("predictions", []))
    if not preds:
        if language == "tamil":
            return "🔁 This customer subscription pattern yet to form."
        else:
            return "🔁 This customer subscription pattern not yet formed."
    
    # General (no customer specified)
    if "customer" not in d:
        if language == "tamil":
            lines = ["🔁 Auto-Subscription Recommendations:\n"]
        else:
            lines = ["🔁 Auto-Subscription Recommendations:\n"]
        for p in preds[:8]:
            if "recommendation" in p:
                lines.append(f"  • {p['item']}: {p['recommendation']}")
            else:
                gap_text = f"{p.get('avg_gap_days', '?')} days gap"
                lines.append(f"  • {p['item']}: {gap_text}")
        lines.append(f"\n✅ {d.get('insight', '')}")
        return "\n".join(lines)
    
    # Specific customer
    lines = [f"🔁 Auto-Subscription Prediction — {d['customer']}:\n"]
    for p in preds[:5]:
        status_icon = "🔴" if p.get("status") == "DUE SOON" else "🟡"
        if language == "tamil":
            lines.append(
                f"  {status_icon} {p['item']}: Next order {p.get('predicted_next', '?')} "
                f"({p.get('days_until', '?')} days) — every {p.get('avg_gap_days', '?')} days"
            )
        else:
            lines.append(
                f"  {status_icon} {p['item']}: Next order {p.get('predicted_next', '?')} "
                f"({p.get('days_until', '?')} days) — every {p.get('avg_gap_days', '?')} days"
            )
    return "\n".join(lines)


def _fmt_weather(d: dict, language: str = "hinglish") -> str:
    lines = [f"🌧️ Weather Trend — {d.get('season', '').title()}:\n"]
    expected = d.get("expected_items", [])
    if expected:
        lines.append(f"  Expected items: {', '.join(expected)}\n")
    for row in d.get("sales_data", [])[:5]:
        lines.append(f"  • {row['item']}: {row['qty']} units sold")
    lines.append(f"\n✅ {d.get('insight', '')}")
    return "\n".join(lines)


def _fmt_demand_stock(data: list, language: str = "hinglish") -> str:
    """Format demand vs stock risk analysis."""
    if not data:
        if language == "tamil":
            return "📦 All stock safe 👍"
        else:
            return "📦 All stock safe 👍"

    lines = ["📦 Demand vs Stock Risk:\n"]

    for item in data[:5]:
        lines.append(
            f"{item['item']} → Demand {item['predicted_demand']}, "
            f"Stock {item['current_stock']} → {item['risk']}"
        )

        if item["shortage"] > 0:
            lines.append(
                f"⚠️ Shortage: {item['shortage']} → Reorder {item['suggested_reorder']}"
            )

        lines.append("")

    return "\n".join(lines)


def format_customer_result(trend_type: str, data: list | dict) -> str:
    if trend_type == "rfm_analysis":
        lines = ["📊 *Customer Segments (RFM)*\n"]
        counts = {}
        for d in data:
            counts[d["segment"]] = counts.get(d["segment"], 0) + 1
        for seg, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {seg}: {cnt} customers")
        top = [d for d in data if d["segment"] == "Champion"][:3]
        if top:
            lines.append("\n🏆 Top Champions:")
            for c in top:
                lines.append(f"  {c['customer_id']} — ₹{c['monetary']:,.0f} spend, {c['recency_days']}d ago")
        return "\n".join(lines)

    elif trend_type == "churn_prediction":
        lines = ["⚠️ *Churn Risk Customers*\n"]
        for d in data[:10]:
            lines.append(
                f"  {d['customer_id']} — {d['days_silent']} days inactive "
                f"(risk: {int(d['churn_risk']*100)}%)"
            )
        return "\n".join(lines) if data else "✅ All customers active!"

    elif trend_type == "next_purchase":
        lines = ["🛒 *Predicted Next Purchases*\n"]
        for d in data[:15]:
            overdue_tag = " ⏰ OVERDUE" if d["overdue"] else ""
            lines.append(
                f"  {d['customer_id']} → {d['item']} ({d['avg_qty']:.0f} units) "
                f"by {d['next_expected']}{overdue_tag} [conf: {int(d['confidence']*100)}%]"
            )
        return "\n".join(lines)

    elif trend_type == "delivery_orders":
        lines = ["🚚 *Delivery Orders Ready*\n"]
        for bundle in data:
            lines.append(f"\n👤 {bundle['name']} ({bundle['locality'] or 'N/A'})")
            lines.append(f"   📞 {bundle['phone'] or 'N/A'}")
            for item in bundle["items"]:
                lines.append(f"   • {item['item']}: {item['quantity']:.0f} units by {item['by_date']}")
        return "\n".join(lines) if data else "📭 No deliveries scheduled for today."

    elif trend_type == "loyalty_scoring":
        lines = ["⭐ *Loyalty Scores*\n"]
        for d in data[:10]:
            bar = "█" * int(d["loyalty_score"] / 10) + "░" * (10 - int(d["loyalty_score"] / 10))
            lines.append(f"  {d['customer_id']:10s} [{bar}] {d['loyalty_score']:.0f}/100 — {d['segment']}")
        return "\n".join(lines)

    return str(data)


def get_greeting(query_text: str) -> str:
    """Return a short Hinglish greeting line for customer analytics.

    Kept deliberately simple so it can be reused across different
    customer trend outputs.
    """

    return "Namaste! Yeh raha aapka customer insights summary:" 

def _fmt_subscription_with_metrics(d: dict, metrics: dict, language: str = "hinglish") -> str:
    preds = d.get("predictions", [])
    if language == "tamil":
        lines = [f"🔁 Auto-Subscription Predictions (Accuracy: {metrics['MAE']} days)\n"]
    else:
        lines = [f"🔁 Auto-Subscription Predictions (Accuracy: {metrics['MAE']} days error)\n"]
    for p in preds[:5]:
        lines.append(f"  • {p['item']}: Expected {p['predicted_next']} (Confidence: {int(p['confidence']*100)}%)")
    return "\n".join(lines)
