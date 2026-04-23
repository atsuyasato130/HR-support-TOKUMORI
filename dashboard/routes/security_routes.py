"""security_routes.py — セキュリティ管理 API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dashboard.db import get_conn

router = APIRouter(tags=["security"])


@router.get("/security")
def list_security():
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT s.*, a.name, a.layer, a.status
        FROM security_info s
        LEFT JOIN agents a ON s.canonical_id = a.canonical_id
        ORDER BY
            CASE s.risk_level WHEN '高' THEN 1 WHEN '中' THEN 2 ELSE 3 END,
            a.layer
        """
    ).fetchall()
    summary = conn.execute(
        "SELECT risk_level, COUNT(*) as cnt FROM security_info GROUP BY risk_level"
    ).fetchall()
    conn.close()
    return {
        "summary": {r["risk_level"]: r["cnt"] for r in summary},
        "items": [dict(r) for r in rows],
    }


@router.get("/security/{canonical_id}")
def get_security(canonical_id: str):
    conn = get_conn()
    row = conn.execute(
        """
        SELECT s.*, a.name, a.layer, a.status, a.apis, a.description
        FROM security_info s
        LEFT JOIN agents a ON s.canonical_id = a.canonical_id
        WHERE s.canonical_id = ?
        """,
        (canonical_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Security info not found")
    return dict(row)


@router.get("/security/levels/definitions")
def get_level_definitions():
    """セキュリティレベル定義 (0〜4) を返す"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM security_level_defs ORDER BY level"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/security/levels/usecases")
def get_usecase_requirements():
    """ユースケース別必要セキュリティレベルを返す"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM usecase_requirements ORDER BY sort_order"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/security/levels/matrix")
def get_security_matrix():
    """エージェント × ユースケース の達成状況マトリクスを返す"""
    conn = get_conn()
    agents = conn.execute(
        """
        SELECT s.canonical_id, s.current_security_level, s.risk_level,
               a.name, a.layer, a.status
        FROM security_info s
        LEFT JOIN agents a ON s.canonical_id = a.canonical_id
        ORDER BY a.layer, a.id
        """
    ).fetchall()
    usecases = conn.execute(
        "SELECT * FROM usecase_requirements ORDER BY sort_order"
    ).fetchall()
    level_defs = conn.execute(
        "SELECT * FROM security_level_defs ORDER BY level"
    ).fetchall()
    conn.close()

    matrix = []
    for ag in agents:
        cur = ag["current_security_level"] or 0
        uc_results = {}
        for uc in usecases:
            req = uc["required_level"]
            gap = req - cur
            uc_results[uc["usecase"]] = {
                "required": req,
                "current":  cur,
                "gap":      gap,
                "ok":       gap <= 0,
            }
        matrix.append({
            "canonical_id":           ag["canonical_id"],
            "name":                   ag["name"],
            "layer":                  ag["layer"],
            "status":                 ag["status"],
            "current_security_level": cur,
            "risk_level":             ag["risk_level"],
            "usecases":               uc_results,
        })

    return {
        "agents":     matrix,
        "usecases":   [dict(u) for u in usecases],
        "level_defs": [dict(d) for d in level_defs],
    }


class SecurityLevelUpdate(BaseModel):
    current_security_level: int


@router.put("/security/{canonical_id}/level")
def update_security_level(canonical_id: str, body: SecurityLevelUpdate):
    if not 0 <= body.current_security_level <= 4:
        raise HTTPException(status_code=400, detail="level は 0〜4 で指定してください")
    conn = get_conn()
    conn.execute(
        "UPDATE security_info SET current_security_level = ? WHERE canonical_id = ?",
        (body.current_security_level, canonical_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "canonical_id": canonical_id, "level": body.current_security_level}
