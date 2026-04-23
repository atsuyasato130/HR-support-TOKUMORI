"""overview_routes.py — KPIダッシュボード API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import datetime

from dashboard.db import get_conn

router = APIRouter(tags=["overview"])


@router.get("/overview/kpi")
def get_kpi():
    conn = get_conn()
    active_agents = conn.execute(
        "SELECT COUNT(*) FROM agents WHERE status = '稼働中'"
    ).fetchone()[0]
    total_agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    time_saved = conn.execute(
        "SELECT COALESCE(SUM(time_saved), 0) FROM intel_logs"
    ).fetchone()[0]
    log_count = conn.execute("SELECT COUNT(*) FROM intel_logs").fetchone()[0]
    roi = round(time_saved * 3000, 0)  # 3000円/時間換算
    conn.close()
    return {
        "active_agents": active_agents,
        "total_agents": total_agents,
        "time_saved_total": round(time_saved, 1),
        "log_count": log_count,
        "roi_jpy": int(roi),
    }


@router.get("/overview/agent_map")
def get_agent_map():
    conn = get_conn()
    rows = conn.execute(
        "SELECT canonical_id, name, layer, status, level, apis FROM agents ORDER BY layer, id"
    ).fetchall()
    conn.close()
    result = {}
    for r in rows:
        layer = r["layer"] or "その他"
        if layer not in result:
            result[layer] = []
        result[layer].append(dict(r))
    return result


@router.get("/overview/kpi_manual")
def get_kpi_manual():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM kpi_manual ORDER BY recorded_at DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


class KpiManualIn(BaseModel):
    bu: str
    operator: str
    task_name: str
    time_before: float
    time_after: float
    note: Optional[str] = None


@router.post("/overview/kpi_manual")
def post_kpi_manual(body: KpiManualIn):
    time_saved = body.time_before - body.time_after
    reduction_rate = round((time_saved / body.time_before * 100), 1) if body.time_before > 0 else 0
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO kpi_manual (recorded_at, bu, operator, task_name,
                                time_before, time_after, time_saved, reduction_rate, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now, body.bu, body.operator, body.task_name,
         body.time_before, body.time_after, time_saved, reduction_rate, body.note),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "time_saved": time_saved, "reduction_rate": reduction_rate}
