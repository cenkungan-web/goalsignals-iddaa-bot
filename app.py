import asyncio
import os
import json
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from bilyoner_service import BilyonerService
from cache_engine import CacheEngine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

service = BilyonerService(max_workers=20)
# Auto refresh cache every 15 minutes (900 seconds)
engine = CacheEngine(service, auto_refresh_interval=900)

app = FastAPI(
    title="Goal Signals Iddaa Bot API",
    description="GoalSignals.com.tr İddaa Oran Eşleştirme & Bülten Botu API",
    version="2.0.0"
)

# CORS Middleware (Crucial for GoalSignals.com.tr integration and cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows GoalSignals.com.tr and any client
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ScanRequest(BaseModel):
    tab_type: int = 1         # 1 = Futbol, 2 = Basketbol, etc.
    bulletin_type: int = 2    # 2 = Maç Öncesi, 1 = Canlı
    limit: Optional[int] = None

class Criterion(BaseModel):
    market: Optional[str] = None          # e.g. "İlk Yarı Skoru"
    selection: Optional[str] = None       # e.g. "0:0"
    target_odd: Optional[float] = None    # e.g. 2.20
    tolerance: float = 0.0                # e.g. 0.05
    min_odd: Optional[float] = None
    max_odd: Optional[float] = None

class SearchRequest(BaseModel):
    # Support for list of criteria (Multi-search)
    criteria: Optional[List[Criterion]] = None
    match_mode: str = "AND"               # "AND" (same match matches all) or "OR" (matches any)

    # Legacy single-search backward compatibility:
    market: Optional[str] = None
    selection: Optional[str] = None
    target_odd: Optional[float] = None
    tolerance: float = 0.0
    min_odd: Optional[float] = None
    max_odd: Optional[float] = None

    league: Optional[str] = None
    match_text: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker / Kubernetes / VPS monitoring."""
    status = engine.get_status()
    return {
        "status": "healthy",
        "cached_matches": status["matches_count"],
        "is_scanning": status["is_scanning"],
        "last_updated": status["last_updated"]
    }

@app.get("/api/status")
async def get_status():
    return engine.get_status()

@app.post("/api/scan")
async def start_scan(req: ScanRequest):
    started = engine.start_background_scan(
        tab_type=req.tab_type,
        bulletin_type=req.bulletin_type,
        limit=req.limit
    )
    return {"started": started, "status": engine.get_status()}

@app.get("/api/markets")
async def get_markets():
    """Returns all distinct markets and their available outcomes in the cache."""
    return engine.get_catalog()

@app.post("/api/search")
async def search_odds(req: SearchRequest):
    # Determine criteria list
    criteria_list = []
    if req.criteria and len(req.criteria) > 0:
        criteria_list = [c.dict() for c in req.criteria]
    else:
        # Fallback to single fields
        criteria_list = [{
            "market": req.market,
            "selection": req.selection,
            "target_odd": req.target_odd,
            "tolerance": req.tolerance,
            "min_odd": req.min_odd,
            "max_odd": req.max_odd
        }]

    results = engine.search_multi(
        criteria=criteria_list,
        match_mode=req.match_mode,
        league_query=req.league,
        match_text=req.match_text
    )

    return {
        "count": len(results),
        "results": results,
        "match_mode": req.match_mode,
        "criteria_count": len(criteria_list),
        "is_cached": len(engine.matches) > 0,
        "total_cached_matches": len(engine.matches)
    }

@app.get("/api/stream-progress")
async def stream_progress():
    """SSE endpoint for live progress streaming."""
    async def event_generator():
        while True:
            status = engine.get_status()
            yield f"data: {json.dumps(status)}\n\n"
            if not status["is_scanning"] and status["progress"]["percent"] in (0, 100):
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.on_event("startup")
async def startup_event():
    # 1. Trigger initial scan
    engine.start_background_scan(tab_type=1, bulletin_type=2, limit=None)
    # 2. Start 24/7 auto-refresh daemon so it stays fresh continuously without PC interaction
    engine.start_auto_refresh_daemon()

if __name__ == "__main__":
    import uvicorn
    # Use port 8000 (configurable via PORT env for cloud hosts)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
