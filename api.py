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


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    """Process a Hinglish text query."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty query")

    result = process(req.text)

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
async def voice_endpoint(audio: UploadFile = File(...), verbose: bool = False):
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
        
        result = asr.transcribe_bytes(audio_bytes)
        if not result:
            raise HTTPException(status_code=400, detail="Transcription failed")
        
        transcribed_text, confidence = result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ASR error: {e}")
    
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
        )
    
    # Process the transcribed text
    try:
        proc_result = process(transcribed_text, is_voice=True)
        
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
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")


@app.get("/inventory")
async def get_inventory():
    """Return full inventory list."""
    return {"items": get_all_items()}


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
