"""
api.py — Optional FastAPI wrapper for mobile/web clients.
Start with: python main.py --api
Or: uvicorn api:app --reload
"""

import sys
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
    ("festival_trend", {}),
    ("market_basket", {}),
    ("customer_pattern", {}),
    ("auto_subscription", {}),
    ("weather_trend", {}),
]


def _execute_all_trends(engine) -> list[dict]:
    """Run all trends from centralized catalog and return UI-ready payload."""
    from app.trends.formatter import format_trend_response

    trends = []
    for trend_type, params in TREND_CATALOG:
        try:
            raw_data = engine.dispatch(trend_type, params)
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


@app.get("/trends/all")
async def get_all_trends():
    """Get all 13 trend analyses."""
    try:
        from app.trends.engine import TrendsEngine
        from config import DB_PATH
        
        engine = TrendsEngine(DB_PATH)

        trends = _execute_all_trends(engine)
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load trends: {e}")


@app.get("/trends/export-json")
async def export_trends_json():
    """Export all trends as JSON."""
    try:
        from app.trends.engine import TrendsEngine
        from datetime import datetime
        engine = TrendsEngine(DB_PATH)

        trends = _execute_all_trends(engine)
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
