"""roadmap_routes.py — ロードマップ API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from dashboard.db import get_conn

router = APIRouter(tags=["roadmap"])


@router.get("/roadmap")
def get_roadmap():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM roadmap ORDER BY phase, agent_no"
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        phase = r["phase"]
        if phase not in result:
            result[phase] = []
        result[phase].append(dict(r))
    return result


@router.get("/roadmap/progress")
def get_progress():
    conn = get_conn()
    phases = conn.execute(
        """
        SELECT phase,
               COUNT(*) as total,
               SUM(CASE WHEN status = '稼働中' THEN 1 ELSE 0 END) as done
        FROM roadmap GROUP BY phase ORDER BY phase
        """
    ).fetchall()
    conn.close()
    return [
        {
            "phase": r["phase"],
            "total": r["total"],
            "done": r["done"],
            "rate": round(r["done"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
        }
        for r in phases
    ]


class RoadmapStatusUpdate(BaseModel):
    status: str


@router.put("/roadmap/{id}/status")
def update_roadmap_status(id: int, body: RoadmapStatusUpdate):
    conn = get_conn()
    result = conn.execute(
        "UPDATE roadmap SET status = ? WHERE id = ?", (body.status, id)
    )
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Roadmap item not found")
    conn.commit()
    conn.close()
    return {"ok": True, "id": id, "status": body.status}
