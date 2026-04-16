"""
api.py — Optional FastAPI wrapper for mobile/web clients.
Start with: python main.py --api
Or: uvicorn api:app --reload
"""

import sys
import sqlite3
from pathlib import Path
from typing import Optional
import tempfile

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi import FastAPI, HTTPException, File, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    raise ImportError("Install FastAPI: pip install fastapi uvicorn")

from app.db.database import init_db, get_all_items
from pipeline import process
from app.trends.classifier import detect_language
from config import TRENDS_DB_PATH, DB_PATH
from app.weather.weather import get_weather
from app.weather.suggestions import get_weather_condition_overview

from app.trends.customer_engine import (
    compute_rfm,
    compute_ltv,
    predict_churn,
    visit_frequency,
    basket_size_trend,
    cohort_retention,
    predict_next_purchases,
    loyalty_scores,
    generate_delivery_orders,
    save_predictions_to_db,
)

app = FastAPI(
    title="VoiceSQL — Kirana Intelligence API",
    description="Hinglish voice → SQL inventory system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Centralized trend catalog to avoid repeating hardcoded lists in multiple endpoints.
TREND_CATALOG = [
    ("sales_trend", {"days": 7}),
    ("hourly_rush", {}),
    ("product_demand", {}),
    ("seasonal_trend", {}),
    ("stock_depletion", {}),
    ("smart_reorder", {}),
    ("dead_stock", {}),
    ("profit_trend", {}),
    ("festival_trend", {"festival": "general"}),
    ("market_basket", {}),
    ("customer_pattern", {}),
    ("auto_subscription", {}),
    ("weather_trend", {}),
]


def _execute_all_trends(engine, festival: str = "general") -> list[dict]:
    """Run all trends from centralized catalog and return UI-ready payload."""
    from app.trends.formatter import format_trend_response

    trends = []
    for trend_type, params in TREND_CATALOG:
        try:
            effective_params = dict(params)
            if trend_type == "festival_trend":
                effective_params["festival"] = festival or "general"
            raw_data = engine.dispatch(trend_type, effective_params)
            formatted = format_trend_response(trend_type, raw_data)
            insight = raw_data.get("insight", "") if isinstance(raw_data, dict) else ""
            trends.append({
                "type": trend_type,
                "raw": raw_data,
                "formatted": formatted,
                "insight": insight,
            })
        except Exception as e:
            trends.append({
                "type": trend_type,
                "error": str(e),
                "formatted": f"❌ Error loading {trend_type}: {str(e)}",
            })
    return trends


@app.on_event("startup")
async def startup():
    init_db()


class QueryRequest(BaseModel):
    text: str
    verbose: Optional[bool] = False
    language: Optional[str] = "hinglish"  # "hinglish", "hindi", or "tamil"


class QueryResponse(BaseModel):
    success: bool
    response: str
    intent: Optional[str]
    sql: Optional[str]
    rows: Optional[list]
    db_rows: Optional[list] = None
    error: Optional[str]


class VoiceQueryResponse(BaseModel):
    success: bool
    transcribed_text: str           # What Whisper heard
    transcription_confidence: float  # 0-1 confidence score
    response: str                    # Business logic response
    intent: Optional[str]
    sql: Optional[str]
    db_rows: Optional[list] = None
    error: Optional[str]
    skipped: Optional[bool] = False  # True if confidence too low
    language: Optional[str] = "hinglish"  # Language used for response


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """Process a Hinglish text query."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty query")

    # Auto-detect language if not explicitly provided
    lang = req.language if req.language != "hinglish" else detect_language(req.text)
    result = process(req.text, language=lang)

    return QueryResponse(
        success=result.success,
        response=result.response,
        intent=result.intent,
        sql=result.sql if req.verbose else None,
        rows=result.db_rows,
        db_rows=result.db_rows,
        error=result.error,
    )


@app.post("/voice", response_model=VoiceQueryResponse)
async def voice_endpoint(audio: UploadFile = File(...), verbose: bool = False, language: str = "hinglish"):
    """
    Process voice input: transcribe (with confidence) → process query.
    
    Returns:
    - transcribed_text: What Whisper heard
    - transcription_confidence: 0-1 (reject if < 0.5)
    - response: Business logic response
    - skipped: True if confidence too low to process
    """
    # Read audio file
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio: {e}")
    
    # Transcribe with confidence
    try:
        from app.asr.whisper_asr import get_asr
        asr = get_asr()
        
        if not asr or not asr.available:
            raise HTTPException(status_code=503, detail="ASR model not available")
        
        result = asr.transcribe_bytes(audio_bytes, language=language)
        if not result:
            raise HTTPException(status_code=400, detail="Transcription failed")
        
        transcribed_text, confidence = result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR error: {e}")
    
    # Auto-detect language if not explicitly provided
    lang = language if language != "hinglish" else detect_language(transcribed_text)
    
    # Check confidence threshold
    if confidence < 0.5:
        return VoiceQueryResponse(
            success=False,
            transcribed_text=transcribed_text,
            transcription_confidence=confidence,
            response=f"⚠️ Confidence low ({confidence:.0%}). Dobara boliye.",
            intent=None,
            sql=None,
            db_rows=None,
            skipped=True,
            error="Low transcription confidence",
            language=lang,
        )
    
    # Process the transcribed text
    try:
        proc_result = process(transcribed_text, is_voice=True, language=lang)
        
        return VoiceQueryResponse(
            success=proc_result.success,
            transcribed_text=transcribed_text,
            transcription_confidence=confidence,
            response=proc_result.response,
            intent=proc_result.intent,
            sql=proc_result.sql if verbose else None,
            db_rows=proc_result.db_rows,
            skipped=False,
            error=proc_result.error,
            language=lang,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")


@app.get("/inventory")
async def get_inventory():
    """Return full inventory list."""
    return {"items": get_all_items()}


@app.api_route("/api/inventory/clear", methods=["POST", "DELETE"])
async def clear_inventory():
    """Clear inventory completely by deleting all inventory items."""
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM inventory")
        row = cur.fetchone()
        items_deleted = int(row[0] if row else 0)

        # Keep history tables but detach item_id pointers before deleting inventory rows.
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for table_row in tables:
            table_name = table_row[0]
            if table_name == "inventory":
                continue
            cols = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
            if any(col[1] == "item_id" for col in cols):
                cur.execute(f"UPDATE {table_name} SET item_id=NULL WHERE item_id IS NOT NULL")

        cur.execute("DELETE FROM inventory")
        conn.commit()

        return {
            "success": True,
            "message": "✅ Inventory cleared successfully",
            "items_deleted": items_deleted,
        }
    except Exception as e:
        if conn:
            conn.rollback()
        return {
            "success": False,
            "message": "Failed to clear inventory",
            "items_deleted": 0,
            "error": str(e),
        }
    finally:
        if conn:
            conn.close()


@app.get("/weather/current")
async def get_current_weather(language: str = "hinglish"):
    """Return current live weather + weather-aware product playbook."""
    weather = get_weather()
    if not weather:
        return {
            "success": False,
            "error": "Weather service unavailable",
            "weather": None,
            "playbook": None,
        }

    playbook = get_weather_condition_overview(weather.get("condition", "unknown"), language=language)
    return {
        "success": True,
        "weather": weather,
        "playbook": playbook,
    }


@app.get("/trends/metadata")
async def get_trends_metadata(language: str = "hinglish"):
    """Return UI metadata for all trend types (icons, narratives, playbooks, etc.)."""
    metadata = {
        "sales_trend": {
            "icon": "📊",
            "narrative_hinglish": "Revenue pulse",
            "narrative_tamil": "Viola mudhal analysis",
            "description_hinglish": "Daily revenue and order tracking over 7 days",
            "description_tamil": "7 naal viola mudhal analysis",
            "playbook_hinglish": ["Top-selling SKU pe stock buffer 20% badhao", "Slow SKU pe combo offer test karo"],
            "playbook_tamil": ["Top selling items-ku 20% stock buffer vainga", "Slow moving items-ku combo offer podunga"],
            "tone": "ok",
            "priority": 1,
        },
        "hourly_rush": {
            "icon": "🕐",
            "narrative_hinglish": "Rush window",
            "narrative_tamil": "Peak neram",
            "description_hinglish": "Identify peak shopping hours for staffing",
            "description_tamil": "Peak neram identify pannunga",
            "playbook_hinglish": ["Peak hour ke pehle counter prep karo", "Fast-moving items front rack pe rakho"],
            "playbook_tamil": ["Peak hour-ku munna counter prep pannunga", "Fast movers front rack la vainga"],
            "tone": "accent",
            "priority": 3,
        },
        "product_demand": {
            "icon": "📦",
            "narrative_hinglish": "Top mover spotlight",
            "narrative_tamil": "Top bikne wala items",
            "description_hinglish": "Top 10 most in-demand products this month",
            "description_tamil": "Month ku top 10 items",
            "playbook_hinglish": ["Top items ka stock lavel maintain karo", "Slow movers pe bundle offers do"],
            "playbook_tamil": ["Top items stock la vainga", "Slow items-ku bundle offers podunga"],
            "tone": "ok",
            "priority": 2,
        },
        "seasonal_trend": {
            "icon": "🌦️",
            "narrative_hinglish": "Seasonal pattern",
            "narrative_tamil": "Kalam pattern",
            "description_hinglish": "Monthly sales patterns and seasonal spikes",
            "description_tamil": "Monthly pattern analysis",
            "playbook_hinglish": ["Festival prep ke 2 hafta pehle stock badho", "Off-season pe discounts chalaao"],
            "playbook_tamil": ["Festival munna stock badhandi", "Off-season la discount podunga"],
            "tone": "accent",
            "priority": 4,
        },
        "stock_depletion": {
            "icon": "⚠️",
            "narrative_hinglish": "Stock risk monitor",
            "narrative_tamil": "Stock risk warning",
            "description_hinglish": "Items at risk of stockout within 7 days",
            "description_tamil": "7 naal la khatam hone wala items",
            "playbook_hinglish": ["Critical items ka reorder aaj hi place karo", "Safety stock threshold set karo"],
            "playbook_tamil": ["Critical items reorder innaikke podunga", "Safety stock limit set pannunga"],
            "tone": "warn",
            "priority": 0,
        },
        "smart_reorder": {
            "icon": "🛒",
            "narrative_hinglish": "Reorder command",
            "narrative_tamil": "Smart reorder quantity",
            "description_hinglish": "Auto-calculated quantities based on demand and lead time",
            "description_tamil": "Auto-calculated reorder quantities",
            "playbook_hinglish": ["Suggested reorder list ko supplier ke saath lock karo", "High margin items ko priority do"],
            "playbook_tamil": ["Suggested reorder list supplier-oda confirm pannunga", "High margin items-ku priority kudunga"],
            "tone": "ok",
            "priority": 1,
        },
        "dead_stock": {
            "icon": "💀",
            "narrative_hinglish": "Dead stock cleanup",
            "narrative_tamil": "Dead stock removal",
            "description_hinglish": "Items not sold in 30+ days — recommend discount or return",
            "description_tamil": "30+ days la bikka items",
            "playbook_hinglish": ["Dead stock pe discount bundle launch karo", "Shelf space ko fast movers ko do"],
            "playbook_tamil": ["Dead stock-ku discount bundle podunga", "Shelf space fast movers-ku maathunga"],
            "tone": "warn",
            "priority": 2,
        },
        "profit_trend": {
            "icon": "💰",
            "narrative_hinglish": "Margin heatmap",
            "narrative_tamil": "Profit analysis",
            "description_hinglish": "Top 10 most profitable products and margin %",
            "description_tamil": "Top 10 profit wala products",
            "playbook_hinglish": ["High margin items pa stock buffer rakho", "Low margin items par combo offers do"],
            "playbook_tamil": ["High margin items stock buffer vainga", "Low margin items-ku combo offers podunga"],
            "tone": "ok",
            "priority": 2,
        },
        "festival_trend": {
            "icon": "🎉",
            "narrative_hinglish": "Festival spike radar",
            "narrative_tamil": "Festival spike detection",
            "description_hinglish": "Compare sales across festivals across multiple years",
            "description_tamil": "Festival-to-festival comparison",
            "playbook_hinglish": ["Festival 2 hafta pehle prep start karo", "Festival-specific stock level plan karo"],
            "playbook_tamil": ["Festival munna planning start pannunga", "Festival stock plan pannunga"],
            "tone": "accent",
            "priority": 3,
        },
        "market_basket": {
            "icon": "🧺",
            "narrative_hinglish": "Bundle discovery",
            "narrative_tamil": "Co-purchase patterns",
            "description_hinglish": "Frequently co-purchased item pairs",
            "description_tamil": "Saathaa bikne items",
            "playbook_hinglish": ["Top pairs pe combo pricing do", "Co-purchase items ko paas-pass display karo"],
            "playbook_tamil": ["Top pairs-ku combo price kudunga", "Saathaa vangara items side-by-side display pannunga"],
            "tone": "neutral",
            "priority": 4,
        },
        "customer_pattern": {
            "icon": "👥",
            "narrative_hinglish": "Customer behavior",
            "narrative_tamil": "Customer patterns",
            "description_hinglish": "Top customers and purchasing habits",
            "description_tamil": "Top customer analysis",
            "playbook_hinglish": ["Top customers ke liye loyalty perks do", "VIP customers ke liye exclusive offers"],
            "playbook_tamil": ["Top customers-ku loyalty offers podunga", "VIP treatment pannunga"],
            "tone": "neutral",
            "priority": 3,
        },
        "auto_subscription": {
            "icon": "🔄",
            "narrative_hinglish": "Repeat-buy signal",
            "narrative_tamil": "Subscription pattern",
            "description_hinglish": "Items purchased regularly — ideal for subscription model",
            "description_tamil": "Regular bikne items",
            "playbook_hinglish": ["Regular items ke liye subscription offer banao", "Monthly bundles suggest karo"],
            "playbook_tamil": ["Regular items-ku subscription offer podunga", "Monthly bundle suggest pannunga"],
            "tone": "neutral",
            "priority": 4,
        },
        "weather_trend": {
            "icon": "🌤️",
            "narrative_hinglish": "Weather demand signal",
            "narrative_tamil": "Weather impact",
            "description_hinglish": "Weather-based demand prediction and product recommendations",
            "description_tamil": "Weather-based demand",
            "playbook_hinglish": ["Weather-led top items ka display front pe rakho", "2-day demand spike ke liye quick reorder karo"],
            "playbook_tamil": ["Weather-led top items front display la podunga", "2-naal spike-ku quick reorder pannunga"],
            "tone": "accent",
            "priority": 2,
        },
    }

    # Select language variant
    lang_key_narrative = f"narrative_{language}"
    lang_key_playbook = f"playbook_{language}"

    result = {}
    for trend_type, info in metadata.items():
        result[trend_type] = {
            "icon": info["icon"],
            "narrative": info.get(lang_key_narrative, info["narrative_hinglish"]),
            "description": info.get(f"description_{language}", info.get("description_hinglish", "")),
            "playbook": info.get(lang_key_playbook, info.get("playbook_hinglish", [])),
            "tone": info["tone"],
            "priority": info["priority"],
        }

    return {"metadata": result}


@app.get("/trends/all")
async def get_all_trends(festival: str = "general"):
    """Get all 13 trend analyses."""
    try:
        from app.trends.engine import TrendsEngine
        from config import DB_PATH
        
        engine = TrendsEngine(DB_PATH)

        trends = _execute_all_trends(engine, festival=festival)
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load trends: {e}")


@app.get("/trends/export-json")
async def export_trends_json(festival: str = "general"):
    """Export all trends as JSON."""
    try:
        from app.trends.engine import TrendsEngine
        from datetime import datetime
        engine = TrendsEngine(DB_PATH)

        trends = _execute_all_trends(engine, festival=festival)
        report = {
            "generated_at": datetime.now().isoformat(),
            "trends": {t["type"]: t.get("raw", {}) for t in trends}
        }
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export JSON: {e}")


@app.get("/trends/export-pdf")
async def export_trends_pdf():
    """Export trends as PDF."""
    try:
        from app.trends.monthly_report import generate_monthly_report
        from config import DB_PATH
        from datetime import datetime
        
        # Generate latest month report
        today = datetime.now()
        year, month = today.year, today.month
        
        report = generate_monthly_report(DB_PATH, year, month)
        
        # Return as file
        from fastapi.responses import FileResponse
        import os
        
        # Report should be saved to reports/ directory
        report_path = f"reports/report_{year:04d}_{month:02d}.json"
        if os.path.exists(report_path):
            return FileResponse(report_path, media_type='application/json', filename=f'trends-report-{year:04d}-{month:02d}.json')
        
        # Fallback: Return as JSON response
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {e}")


@app.get("/customer-trends")
async def get_customer_trends():
    """Aggregate key customer analytics for the dashboard."""
    try:
        from datetime import datetime

        db_path = str(TRENDS_DB_PATH)

        rfm = compute_rfm(db_path)
        ltv = compute_ltv(db_path)
        churn = predict_churn(db_path)
        visits = visit_frequency(db_path)
        baskets = basket_size_trend(db_path)
        cohorts = cohort_retention(db_path)
        loyalty = loyalty_scores(db_path)

        # Refresh predictive tables and delivery suggestions
        save_predictions_to_db(db_path)
        next_purchases = predict_next_purchases(db_path)
        deliveries = generate_delivery_orders(db_path)

        return {
            "generated_at": datetime.now().isoformat(),
            "rfm": rfm,
            "ltv": ltv,
            "churn": churn,
            "visit_frequency": visits,
            "basket_size": baskets,
            "cohort_retention": cohorts,
            "loyalty": loyalty,
            "next_purchases": next_purchases,
            "delivery_orders": deliveries,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load customer trends: {e}")


class BillUploadRequest(BaseModel):
    """Schema for bill upload."""
    bill_id: str
    customer_id: str
    customer_name: str
    timestamp: str
    items: list


class BillUploadResponse(BaseModel):
    """Response after bill processing."""
    success: bool
    bill_id: str
    message: str
    items_processed: int
    sales_records_created: int
    inventory_updated: bool
    trends_refreshed: bool
    warnings: Optional[list] = None
    error: Optional[str] = None


class SalesCsvImportRequest(BaseModel):
    csv_text: str
    mode: Optional[str] = "transaction"


class SalesCsvImportResponse(BaseModel):
    success: bool
    message: str
    rows_processed: int
    rows_succeeded: int
    rows_failed: int
    inventory_updated: bool
    trends_refreshed: bool
    warnings: Optional[list] = None
    error: Optional[str] = None


@app.post("/api/upload-bill", response_model=BillUploadResponse)
async def upload_bill(bill: BillUploadRequest):
    """
    Process shopkeeper-uploaded JSON bill.
    
    Updates inventory and records sales in real-time.
    Automatically triggers trends recalculation.
    
    Input:
    {
        "bill_id": "B1002",
        "customer_id": "C001",
        "customer_name": "Rahul",
        "timestamp": "2026-04-09T11:00:00",
        "items": [
            {"product_id": "P001", "name": "Atta 50kg", "quantity": 2, "price": 500},
            {"product_id": "P002", "name": "Sugar 5kg", "quantity": 1, "price": 300}
        ]
    }
    
    Output:
    {
        "success": true,
        "bill_id": "B1002",
        "message": "✅ Bill B1002 processed. 2 items recorded. Inventory updated.",
        "items_processed": 2,
        "sales_records_created": 2,
        "inventory_updated": true,
        "trends_refreshed": true
    }
    """
    try:
        from app.bill_processor import BillProcessor, refresh_trends_after_bill
        
        # Convert request to dict
        bill_dict = bill.dict()
        
        # Process bill
        processor = BillProcessor()
        result = processor.process_bill(bill_dict)
        
        if not result.success:
            # Return error response (don't raise HTTPException)
            return BillUploadResponse(
                success=False,
                bill_id=result.bill_id,
                message=result.message,
                items_processed=result.items_processed,
                sales_records_created=result.sales_records_created,
                inventory_updated=result.inventory_updated,
                trends_refreshed=False,
                warnings=result.warnings if hasattr(result, 'warnings') else None,
                error=result.error,
            )
        
        # Refresh trends after successful bill processing
        from config import DB_PATH as CONFIG_DB_PATH
        trends_refreshed = refresh_trends_after_bill(str(CONFIG_DB_PATH))
        
        return BillUploadResponse(
            success=True,
            bill_id=result.bill_id,
            message=result.message,
            items_processed=result.items_processed,
            sales_records_created=result.sales_records_created,
            inventory_updated=result.inventory_updated,
            trends_refreshed=trends_refreshed,
            warnings=result.warnings if hasattr(result, 'warnings') else None,
        )
    
    except Exception as e:
        import traceback
        log_msg = traceback.format_exc()
        return BillUploadResponse(
            success=False,
            bill_id="ERROR",
            message="Internal server error processing bill",
            items_processed=0,
            sales_records_created=0,
            inventory_updated=False,
            trends_refreshed=False,
            error=str(e),
        )


@app.post("/api/import-sales-csv", response_model=SalesCsvImportResponse)
async def import_sales_csv(payload: SalesCsvImportRequest):
    """Import a flat shop CSV and update inventory + trends."""
    try:
        from app.bill_processor import process_sales_csv
        from config import DB_PATH as CONFIG_DB_PATH

        result = process_sales_csv(payload.csv_text, str(CONFIG_DB_PATH), inventory_mode=payload.mode)
        return SalesCsvImportResponse(
            success=bool(result.get("success")),
            message=result.get("message", ""),
            rows_processed=int(result.get("rows_processed", 0)),
            rows_succeeded=int(result.get("rows_succeeded", 0)),
            rows_failed=int(result.get("rows_failed", 0)),
            inventory_updated=bool(result.get("inventory_updated")),
            trends_refreshed=bool(result.get("trends_refreshed")),
            warnings=result.get("warnings") or None,
            error=result.get("error"),
        )
    except Exception as e:
        return SalesCsvImportResponse(
            success=False,
            message="Internal server error processing CSV",
            rows_processed=0,
            rows_succeeded=0,
            rows_failed=0,
            inventory_updated=False,
            trends_refreshed=False,
            error=str(e),
        )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "VoiceSQL"}


# ── Serve built React frontend ─────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

_dist = Path(__file__).parent / "frontend_dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        # Don't catch API routes
        if full_path.startswith(("query", "inventory", "health", "assets")):
            raise HTTPException(status_code=404)
        index = _dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
        raise HTTPException(status_code=404, detail="Frontend not built")
