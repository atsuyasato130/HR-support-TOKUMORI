"""intel_routes.py — 実行ログ API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import datetime

from dashboard.db import get_conn

router = APIRouter(tags=["intel"])


@router.get("/intel")
def list_intel(
    bu: Optional[str] = None,
    result: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
):
    conn = get_conn()
    query = "SELECT * FROM intel_logs WHERE 1=1"
    params = []
    if bu:
        query += " AND bu = ?"
        params.append(bu)
    if result:
        query += " AND result = ?"
        params.append(result)
    if date_from:
        query += " AND executed_at >= ?"
        params.append(date_from)
    if date_to:
        query += " AND executed_at <= ?"
        params.append(date_to + " 23:59:59")
    query += " ORDER BY executed_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/intel/summary")
def get_intel_summary():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM intel_logs").fetchone()[0]
    success = conn.execute(
        "SELECT COUNT(*) FROM intel_logs WHERE result = 'SUCCESS'"
    ).fetchone()[0]
    time_saved = conn.execute(
        "SELECT COALESCE(SUM(time_saved), 0) FROM intel_logs"
    ).fetchone()[0]
    avg_saved = conn.execute(
        "SELECT COALESCE(AVG(time_saved), 0) FROM intel_logs"
    ).fetchone()[0]
    conn.close()
    return {
        "total_logs": total,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0,
        "total_time_saved": round(time_saved, 1),
        "avg_time_saved": round(avg_saved, 2),
    }


@router.get("/intel/by_agent")
def get_intel_by_agent():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT agent_name, canonical_id,
               COUNT(*) as log_count,
               SUM(time_saved) as total_saved,
               SUM(CASE WHEN result='SUCCESS' THEN 1 ELSE 0 END) as success_count
        FROM intel_logs
        GROUP BY canonical_id, agent_name
        ORDER BY total_saved DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class IntelIn(BaseModel):
    agent_name: str
    canonical_id: Optional[str] = None
    bu: Optional[str] = None
    operator: Optional[str] = None
    time_saved: float = 0
    result: str = "SUCCESS"
    task_summary: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    duration_sec: float = 0
    error_message: Optional[str] = None


@router.post("/intel")
def post_intel(body: IntelIn):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO intel_logs
            (executed_at, agent_name, canonical_id, bu, operator, time_saved,
             result, task_summary, input_summary, output_summary, duration_sec, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now, body.agent_name, body.canonical_id, body.bu, body.operator,
         body.time_saved, body.result, body.task_summary, body.input_summary,
         body.output_summary, body.duration_sec, body.error_message),
    )
    if body.canonical_id:
        conn.execute(
            """
            UPDATE agents SET
                run_count_total = run_count_total + 1,
                run_count_month = run_count_month + 1,
                time_saved_month = time_saved_month + ?,
                last_run_at = ?
            WHERE canonical_id = ?
            """,
            (body.time_saved, now, body.canonical_id),
        )
    conn.commit()
    conn.close()
    return {"ok": True}
