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


@app.get("/trends/all")
async def get_all_trends():
    """Get all 13 trend analyses."""
    try:
        from app.trends.engine import TrendsEngine
        from app.trends.formatter import format_trend_response
        from config import DB_PATH
        
        engine = TrendsEngine(DB_PATH)
        
        trend_analyses = [
            ("sales_trend", lambda: engine.sales_trend(days=7)),
            ("hourly_rush", lambda: engine.hourly_rush()),
            ("product_demand", lambda: engine.product_demand()),
            ("seasonal_trend", lambda: engine.seasonal_trend()),
            ("stock_depletion", lambda: engine.stock_depletion()),
            ("smart_reorder", lambda: engine.smart_reorder()),
            ("dead_stock", lambda: engine.dead_stock()),
            ("profit_trend", lambda: engine.profit_trend()),
            ("festival_trend", lambda: engine.festival_trend()),
            ("market_basket", lambda: engine.market_basket()),
            ("customer_pattern", lambda: engine.customer_pattern()),
            ("auto_subscription", lambda: engine.auto_subscription()),
            ("weather_trend", lambda: engine.weather_trend()),
        ]
        
        trends = []
        for trend_type, fn in trend_analyses:
            try:
                raw_data = fn()
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
        
        return {"trends": trends}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load trends: {e}")


@app.get("/trends/export-json")
async def export_trends_json():
    """Export all trends as JSON."""
    try:
        from app.trends.engine import TrendsEngine
        from config import DB_PATH
        from datetime import datetime
        
        engine = TrendsEngine(DB_PATH)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "trends": {
                "sales_trend": engine.sales_trend(days=7),
                "hourly_rush": engine.hourly_rush(),
                "product_demand": engine.product_demand(),
                "seasonal_trend": engine.seasonal_trend(),
                "stock_depletion": engine.stock_depletion(),
                "smart_reorder": engine.smart_reorder(),
                "dead_stock": engine.dead_stock(),
                "profit_trend": engine.profit_trend(),
                "festival_trend": engine.festival_trend(),
                "market_basket": engine.market_basket(),
                "customer_pattern": engine.customer_pattern(),
                "auto_subscription": engine.auto_subscription(),
                "weather_trend": engine.weather_trend(),
            }
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
