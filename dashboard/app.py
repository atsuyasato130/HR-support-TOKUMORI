"""
Tokumori Web Dashboard
起動: uvicorn dashboard.app:app --port 8889 --reload
または: bash start_dashboard.sh
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pathlib import Path

from dashboard.routes.overview_routes import router as overview_router
from dashboard.routes.agent_routes import router as agent_router
from dashboard.routes.roadmap_routes import router as roadmap_router
from dashboard.routes.activity_routes import router as activity_router
from dashboard.routes.intel_routes import router as intel_router
from dashboard.routes.security_routes import router as security_router
from dashboard.routes.map_routes import router as map_router

app = FastAPI(title="Tokumori Dashboard", version="1.0")

app.include_router(overview_router, prefix="/api")
app.include_router(agent_router,    prefix="/api")
app.include_router(roadmap_router,  prefix="/api")
app.include_router(activity_router, prefix="/api")
app.include_router(intel_router,    prefix="/api")
app.include_router(security_router, prefix="/api")
app.include_router(map_router,      prefix="/api")

_TEMPLATE = Path(__file__).parent / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    return _TEMPLATE.read_text(encoding="utf-8")
