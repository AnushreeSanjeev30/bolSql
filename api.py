"""
api.py — Optional FastAPI wrapper for mobile/web clients.
Start with: python main.py --api
Or: uvicorn api:app --reload
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi import FastAPI, HTTPException
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
