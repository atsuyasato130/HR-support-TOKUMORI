"""activity_routes.py — 更新ログ API"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import datetime

from dashboard.db import get_conn

router = APIRouter(tags=["activity"])


@router.get("/activity")
def list_activity(limit: int = 50, keyword: Optional[str] = None):
    conn = get_conn()
    if keyword:
        rows = conn.execute(
            """
            SELECT * FROM activity_log
            WHERE summary LIKE ? OR targets LIKE ? OR details LIKE ?
            ORDER BY logged_at DESC LIMIT ?
            """,
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY logged_at DESC LIMIT ?", (limit,)
        ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    now_month = datetime.datetime.now().strftime("%Y-%m")
    month_count = conn.execute(
        "SELECT COUNT(*) FROM activity_log WHERE logged_at LIKE ?", (f"{now_month}%",)
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "month_count": month_count,
        "items": [dict(r) for r in rows],
    }


class ActivityIn(BaseModel):
    icon: str
    summary: str
    targets: Optional[str] = None
    details: Optional[str] = None
    status: str = "✅ 完了"


@router.post("/activity")
def post_activity(body: ActivityIn):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO activity_log (logged_at, icon, summary, targets, details, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (now, body.icon, body.summary, body.targets, body.details, body.status),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
