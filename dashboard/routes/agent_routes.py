"""agent_routes.py — エージェント管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import datetime

from dashboard.db import get_conn

router = APIRouter(tags=["agents"])


@router.get("/agents")
def list_agents(layer: Optional[str] = None, status: Optional[str] = None):
    conn = get_conn()
    query = "SELECT * FROM agents WHERE 1=1"
    params = []
    if layer:
        query += " AND layer = ?"
        params.append(layer)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY layer, id"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/agents/{canonical_id}")
def get_agent(canonical_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM agents WHERE canonical_id = ?", (canonical_id,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return dict(row)


class StatusUpdate(BaseModel):
    status: str


@router.put("/agents/{canonical_id}/status")
def update_agent_status(canonical_id: str, body: StatusUpdate):
    valid = {"稼働中", "開発中", "設計中"}
    if body.status not in valid:
        raise HTTPException(status_code=400, detail=f"status は {valid} のいずれかで指定してください")
    conn = get_conn()
    conn.execute(
        "UPDATE agents SET status = ? WHERE canonical_id = ?",
        (body.status, canonical_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "canonical_id": canonical_id, "status": body.status}


@router.get("/agents/{canonical_id}/logs")
def get_agent_logs(canonical_id: str, limit: int = 20):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT * FROM intel_logs WHERE canonical_id = ?
        ORDER BY executed_at DESC LIMIT ?
        """,
        (canonical_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class RunLogIn(BaseModel):
    bu: Optional[str] = None
    operator: Optional[str] = None
    time_saved: float = 0
    result: str = "SUCCESS"
    task_summary: Optional[str] = None
    duration_sec: float = 0
    error_message: Optional[str] = None


@router.post("/agents/{canonical_id}/run_log")
def post_run_log(canonical_id: str, body: RunLogIn):
    conn = get_conn()
    agent = conn.execute(
        "SELECT name FROM agents WHERE canonical_id = ?", (canonical_id,)
    ).fetchone()
    if not agent:
        conn.close()
        raise HTTPException(status_code=404, detail="Agent not found")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO intel_logs
            (executed_at, agent_name, canonical_id, bu, operator,
             time_saved, result, task_summary, duration_sec, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now, agent["name"], canonical_id, body.bu, body.operator,
         body.time_saved, body.result, body.task_summary, body.duration_sec, body.error_message),
    )
    conn.execute(
        """
        UPDATE agents SET
            run_count_total = run_count_total + 1,
            run_count_month = run_count_month + 1,
            time_saved_month = time_saved_month + ?,
            last_run_at = ?
        WHERE canonical_id = ?
        """,
        (body.time_saved, now, canonical_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
