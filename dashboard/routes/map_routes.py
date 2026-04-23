"""map_routes.py — オーケストレーションマップ API"""
import math
from fastapi import APIRouter

from dashboard.db import get_conn

router = APIRouter(tags=["map"])

# ── エージェントグラフ 固定座標 ──────────────────────────────
# レイアウト:
#   Row  0 (y=-560): メンバー（人）ノード — 依頼の起点
#   Row  1 (y=-380): BU オーケストレーター — 依頼を受けてサブエージェントへ委譲
#   Row  2 (y=-180): サブオーケストレーター / 直属サブエージェント
#   Row  3 (y=  20): Executor / Watcher / Parser / ツール層
#   Row  4 (y= 220): Processor 層 / 職種ロール層
#   右上: hr_orchestrator_main（全体統括・管理者が利用）
#   右ブロック: 経営戦略 / 組織管理 / 品質管理

AGENT_POSITIONS: dict[str, tuple[int, int]] = {
    # ── BU オーケストレーター層（y=-380） ──────────────────────
    "hr_orchestrator_post_interview": (-550, -380),
    "rpo_orchestrator":               (-280, -380),
    "sales_orchestrator":             (   0, -380),
    "hr_dept_orchestrator":           ( 280, -380),
    "mgmt_orchestrator":              ( 550, -380),
    # ── 全体統括（右上・管理者用） ──────────────────────────────
    "hr_orchestrator_main": ( 950, -500),
    # ── HRsupport サブオーケストレーター（y=-180） ───────────
    "hrsup_chuto":     (-650, -180),
    "hrsup_shinsotsu": (-420, -180),
    # ── HRsupport Executor / Watcher / Parser 層（y=20） ───────
    "hr_watcher_tldv":        (-750,  20),
    "hr_executor_salesforce": (-570,  20),
    "hr_executor_slack":      (-380,  20),   # Messaging グループ
    "hr_executor_google":     (-150,  20),   # Google Suite グループ
    "hr_parser_notion":       (  80,  20),
    # ── Google Suite 子ノード（y=220、hr_executor_google(-150) の下） ─
    "hr_google_gmail":   (-250, 220),
    "hr_google_gdrive":  (-120, 220),
    "hr_google_gsheets": (  10, 220),
    # ── Messaging 子ノード（y=220、hr_executor_slack(-380) の下） ────
    "hr_messaging_line":  (-470, 220),
    "hr_messaging_slack": (-310, 220),
    # ── HRsupport Processor 層（y=380） ─────────────────────────
    "hr_processor_coaching":   (-650, 380),
    "hr_processor_interview":  (-480, 380),
    "hr_processor_report":     (-310, 380),
    "hr_processor_supporter":  (-140, 380),
    # ── HRsupport 職種ロール層（y=560） ──────────────────────
    "hrsup_ca": (-620, 560),
    "hrsup_ra": (-450, 560),
    "hrsup_lg": (-270, 560),
    # ── RPO CS（y=-180、rpo_orchestratorの下） ───────────────
    "rpo_cs": (-280, -180),
    # ── Sales FS/IS（y=-180） ────────────────────────────────
    "sales_fs": ( -80, -180),
    "sales_is": (  80, -180),
    # ── 人事 サブエージェント（y=-180） ──────────────────────
    "hr_dept_employee_hiring":   ( 200, -180),
    "hr_dept_contractor_hiring": ( 350, -180),
    "hr_dept_intern_hiring":     ( 500, -180),
    # ── 経営管理 サブエージェント（y=-180） ──────────────────
    "mgmt_accounting": ( 650, -180),
    "mgmt_legal":      ( 800, -180),
    # ── 経営戦略（x=1050-1250） ─────────────────────────────
    "exec_strategy":    (1050, -200),
    "exec_ai_trend":    (1050,    0),
    "exec_pl":          (1250, -200),
    "exec_team_health": (1250,    0),
    "exec_approval":    (1150,  200),
    # ── 組織管理（x=1500-1700） ─────────────────────────────
    "org_pulse":      (1500, -200),
    "org_recruiting": (1500,    0),
    "org_onboarding": (1700, -200),
    "org_kpi":        (1700,    0),
    # ── 品質管理（x=1950-2150） ─────────────────────────────
    "qa_review":    (1950, -200),
    "qa_design":    (1950,    0),
    "qa_creative":  (2150, -200),
    "qa_brand_mgr": (2150,  200),
}

# ── メンバー（人）ノード定義 ─────────────────────────────────
# 各BUのメンバーが依頼する起点。AIエージェントではなく人間を表す。
_MEMBER_NODES = [
    {"id": "_mem_hrsupport", "label": "👤 HRsupport\nメンバー",  "x": -550, "y": -560, "bu": "HRsupport", "orch": "hr_orchestrator_post_interview"},
    {"id": "_mem_rpo",       "label": "👤 RPO\nメンバー",        "x": -280, "y": -560, "bu": "RPO",       "orch": "rpo_orchestrator"},
    {"id": "_mem_sales",     "label": "👤 Sales\nメンバー",      "x":    0, "y": -560, "bu": "Sales",     "orch": "sales_orchestrator"},
    {"id": "_mem_hr_dept",   "label": "👤 人事\nメンバー",       "x":  280, "y": -560, "bu": "人事",      "orch": "hr_dept_orchestrator"},
    {"id": "_mem_mgmt",      "label": "👤 経営管理\nメンバー",   "x":  550, "y": -560, "bu": "経営管理",  "orch": "mgmt_orchestrator"},
    {"id": "_mem_admin",     "label": "👤 管理者\n（全体統括）", "x":  950, "y": -700, "bu": "全体",      "orch": "hr_orchestrator_main"},
]

# ── スタイル定義 ────────────────────────────────────────────
_STATUS_COLOR = {
    "稼働中": {
        "background": "#10b981", "border": "#059669",
        "highlight": {"background": "#34d399", "border": "#059669"},
        "hover":     {"background": "#34d399", "border": "#059669"},
    },
    "開発中": {
        "background": "#f59e0b", "border": "#d97706",
        "highlight": {"background": "#fbbf24", "border": "#d97706"},
        "hover":     {"background": "#fbbf24", "border": "#d97706"},
    },
    "設計中": {
        "background": "#334155", "border": "#475569",
        "highlight": {"background": "#475569", "border": "#64748b"},
        "hover":     {"background": "#475569", "border": "#64748b"},
    },
}

_EDGE_STYLE = {
    "requests":     {"color": {"color": "#e2e8f0", "highlight": "#ffffff"}, "dashes": [4, 4], "width": 1.8},
    "orchestrates": {"color": {"color": "#7c3aed", "highlight": "#a855f7"}, "dashes": False,  "width": 2.5},
    "triggers":     {"color": {"color": "#10b981", "highlight": "#34d399"}, "dashes": False,  "width": 1.8},
    "reads":        {"color": {"color": "#3b82f6", "highlight": "#60a5fa"}, "dashes": [6, 4], "width": 1.2},
    "writes":       {"color": {"color": "#f59e0b", "highlight": "#fbbf24"}, "dashes": [4, 3], "width": 1.2},
}

_LAYER_LABEL = {
    "全体":     "⚡ 全体",
    "HRsupport": "🤖 HRsupport",
    "RPO":      "📋 RPO",
    "Sales":    "💼 Sales",
    "人事":     "👥 人事",
    "経営管理": "🏦 経営管理",
    "経営戦略": "📊 経営戦略",
    "組織管理": "🏢 組織管理",
    "品質管理": "✅ 品質管理",
}

# ── エージェントグラフ ──────────────────────────────────────
@router.get("/map/agent_graph")
def get_agent_graph():
    """エージェント依存グラフ（vis-network / 固定座標）"""
    conn = get_conn()
    agents = conn.execute("SELECT * FROM agents ORDER BY layer, id").fetchall()
    edges  = conn.execute("SELECT * FROM agent_edges").fetchall()
    conn.close()

    nodes = []
    for a in agents:
        cid    = a["canonical_id"]
        status = a["status"] or "設計中"
        layer  = a["layer"]  or "その他"
        is_orch  = "orchestrator" in cid
        is_group = "【Group】" in (a["description"] or "")

        pos = AGENT_POSITIONS.get(cid)
        node: dict = {
            "id":    cid,
            "label": a["name"],
            "title": (
                f"<b style='color:#e2e8f0'>{a['name']}</b>"
                f"<br><code style='font-size:10px;color:#94a3b8'>{cid}</code>"
                f"<br><span style='color:#cbd5e1'>{a['description'] or ''}</span>"
                f"<br>APIs: <b>{a['apis'] or '—'}</b>"
                f"<br>Status: <b>{status}</b>"
            ),
            "color":       _STATUS_COLOR.get(status, _STATUS_COLOR["設計中"]),
            "shape":       "ellipse" if is_orch else ("hexagon" if is_group else "box"),
            "size":        28 if is_orch else (22 if is_group else 18),
            "font":        {"color": "#f1f5f9", "size": 13 if is_orch else 12, "bold": is_orch or is_group},
            "borderWidth": 3 if is_orch else (2.5 if is_group else 1.5),
            "shadow":      {"enabled": True, "color": "rgba(0,0,0,0.6)", "size": 10},
            "status":      status,
            "layer":       layer,
            "apis":        a["apis"] or "",
            "physics":     False,
        }
        if pos:
            node["x"], node["y"] = pos

        nodes.append(node)

    vis_edges = []
    for e in edges:
        style = _EDGE_STYLE.get(e["edge_type"], _EDGE_STYLE["triggers"])
        vis_edges.append({
            "from":           e["from_id"],
            "to":             e["to_id"],
            "label":          e["label"] or "",
            "edge_type":      e["edge_type"],
            "is_parallel":    bool(e["is_parallel"]),
            "parallel_group": e["parallel_group"],
            "arrows":         {"to": {"enabled": True, "scaleFactor": 0.8}},
            "font":           {"color": "#94a3b8", "size": 10, "align": "middle", "strokeWidth": 0},
            "smooth":         {"type": "curvedCW", "roundness": 0.1},
            **style,
        })

    # ── メンバー（人）ノードとリクエストエッジを追加 ──────────
    member_nodes = []
    member_color = {
        "background": "#1e293b", "border": "#94a3b8",
        "highlight": {"background": "#334155", "border": "#e2e8f0"},
        "hover":     {"background": "#334155", "border": "#e2e8f0"},
    }
    req_style = _EDGE_STYLE["requests"]
    for m in _MEMBER_NODES:
        member_nodes.append({
            "id":    m["id"],
            "label": m["label"],
            "x": m["x"], "y": m["y"],
            "shape": "ellipse",
            "size":  22,
            "color": member_color,
            "font":  {"color": "#94a3b8", "size": 11, "bold": False},
            "borderWidth": 1.5,
            "borderDashes": [3, 3],
            "shadow": {"enabled": False},
            "physics": False,
            "status": "人",
            "layer": m["bu"],
            "apis":  "",
            "title": f"<b style='color:#e2e8f0'>{m['label'].replace(chr(10), ' ')}</b><br>依頼者（人間）",
        })
        vis_edges.append({
            "from":      m["id"],
            "to":        m["orch"],
            "label":     "依頼",
            "edge_type": "requests",
            "is_parallel": False,
            "parallel_group": None,
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.7}},
            "font":   {"color": "#64748b", "size": 10, "align": "middle", "strokeWidth": 0},
            "smooth": {"type": "straightCross"},
            **req_style,
        })

    # Layer ラベルノード（区切り見出し用）
    label_nodes = _make_layer_labels()

    return {"nodes": nodes + label_nodes + member_nodes, "edges": vis_edges}


def _make_layer_labels() -> list[dict]:
    """各 Layer のセクション見出しノード（クリック不可）"""
    labels = [
        {"id": "_lbl_hr",   "label": "── HRsupport ──", "x": -600, "y": -470, "layer": "HRsupport"},
        {"id": "_lbl_rpo",  "label": "── RPO ──",        "x": -280, "y": -470, "layer": "RPO"},
        {"id": "_lbl_sales","label": "── Sales ──",      "x":    0, "y": -470, "layer": "Sales"},
        {"id": "_lbl_hr2",  "label": "── 人事 ──",       "x":  280, "y": -470, "layer": "人事"},
        {"id": "_lbl_mgmt", "label": "── 経営管理 ──",   "x":  550, "y": -470, "layer": "経営管理"},
        {"id": "_lbl_exec", "label": "── 経営戦略 ──",   "x": 1150, "y": -300, "layer": "経営戦略"},
        {"id": "_lbl_org",  "label": "── 組織管理 ──",   "x": 1600, "y": -300, "layer": "組織管理"},
        {"id": "_lbl_qa",   "label": "── 品質管理 ──",   "x": 2050, "y": -300, "layer": "品質管理"},
    ]
    result = []
    for lb in labels:
        result.append({
            "id": lb["id"], "label": lb["label"],
            "x": lb["x"], "y": lb["y"],
            "shape": "text",
            "font": {"color": "#475569", "size": 11, "bold": False},
            "physics": False,
            "fixed": True,
            "chosen": False,
            "layer": lb["layer"],
            "status": "",
            "apis": "",
        })
    return result


# ── ビジネスマップ（同心円固定レイアウト） ─────────────────
_BU_ORDER = ["HRsupport", "RPO", "Sales", "人事", "経営管理", "Strategy"]

# BU ごとのツール一覧（Claude を除く）
_BU_TOOLS: dict[str, list[str]] = {
    "HRsupport": ["Salesforce", "Notion", "LINE", "Slack", "tldv", "Gmail", "GDrive", "GSheets"],
    "RPO":       ["Salesforce", "GSheets"],
    "Sales":     ["Salesforce", "Slack"],
    "人事":      ["Notion", "Slack"],
    "経営管理":  ["GSheets", "Notion", "Slack"],
    "Strategy":  ["GSheets"],
}

_TOOL_COLOR: dict[str, str] = {
    "Salesforce": "#0ea5e9",
    "Notion":     "#e2e8f0",
    "LINE":       "#22c55e",
    "Slack":      "#4ade80",
    "tldv":       "#f97316",
    "Gmail":      "#ef4444",
    "GDrive":     "#fbbf24",
    "GSheets":    "#34d399",
    "GitHub":     "#94a3b8",
}

_BU_COLOR: dict[str, str] = {
    "HRsupport": "#7c3aed",
    "RPO":       "#3b82f6",
    "Sales":     "#ef4444",
    "人事":      "#06b6d4",
    "経営管理":  "#f59e0b",
    "Strategy":  "#10b981",
}


def _polar(r: float, deg: float) -> tuple[int, int]:
    rad = math.radians(deg)
    return (round(r * math.cos(rad)), round(r * math.sin(rad)))


@router.get("/map/business_map")
def get_business_map():
    """全社ビジネスマップ（Claude ハブ / 同心円固定レイアウト）"""
    conn = get_conn()
    connections = conn.execute("SELECT * FROM tool_connections ORDER BY bu, tool").fetchall()
    conn.close()

    R_BU   = 300   # BU リング半径
    R_TOOL = 560   # ツール リング半径
    SPREAD = 55    # BU 周囲にツールを広げる角度（±度）

    # BU の角度（-90° 真上スタート、時計回り）
    n_bu = len(_BU_ORDER)
    bu_angles = {bu: -90 + i * (360 / n_bu) for i, bu in enumerate(_BU_ORDER)}

    nodes: list[dict] = []
    edges: list[dict] = []
    added: set[str]   = set()

    # Claude ハブ
    nodes.append({
        "id": "claude_hub", "label": "⚡ Claude\nAI Hub",
        "shape": "star", "size": 44,
        "color": {"background": "#7c3aed", "border": "#a855f7",
                  "highlight": {"background": "#a855f7", "border": "#c084fc"}},
        "font": {"color": "#ffffff", "size": 13, "bold": True},
        "x": 0, "y": 0, "physics": False, "fixed": True,
        "title": "<b style='color:#e2e8f0'>Claude (AI Hub)</b><br>全事業の推論・生成エンジン",
        "node_type": "hub",
    })
    added.add("claude_hub")

    # ツール→使用BUリスト（共有ツールの位置計算用）
    tool_bu_angles: dict[str, list[float]] = {}
    for bu, tools in _BU_TOOLS.items():
        for tool in tools:
            tool_bu_angles.setdefault(tool, []).append(bu_angles[bu])

    # 各ツールの最終角度（使用BUの平均角度）
    def avg_angle(angles: list[float]) -> float:
        # 円形平均
        sx = sum(math.cos(math.radians(a)) for a in angles)
        sy = sum(math.sin(math.radians(a)) for a in angles)
        return math.degrees(math.atan2(sy, sx))

    # BU ノード
    for bu in _BU_ORDER:
        bu_id  = f"bu_{bu}"
        angle  = bu_angles[bu]
        bx, by = _polar(R_BU, angle)
        color  = _BU_COLOR.get(bu, "#475569")
        nodes.append({
            "id": bu_id, "label": bu,
            "shape": "box",
            "color": {"background": color, "border": color,
                      "highlight": {"background": color, "border": "#ffffff"}},
            "font": {"color": "#ffffff", "size": 13, "bold": True},
            "x": bx, "y": by, "physics": False, "fixed": True,
            "title": f"<b style='color:#e2e8f0'>{bu}</b>",
            "node_type": "bu",
        })
        added.add(bu_id)
        # Claude → BU
        edges.append({
            "from": "claude_hub", "to": bu_id,
            "color": {"color": color, "opacity": 0.7},
            "width": 2.5, "dashes": False, "arrows": {"to": {"scaleFactor": 0.8}},
            "smooth": {"type": "straightCross"}, "edge_type": "hub",
        })

    # ツールノード（BU ごとにファン配置）
    for bu in _BU_ORDER:
        bu_id  = f"bu_{bu}"
        tools  = _BU_TOOLS.get(bu, [])
        angle  = bu_angles[bu]
        n      = len(tools)
        if n == 0:
            continue
        step   = (SPREAD * 2) / max(n - 1, 1)

        for i, tool in enumerate(tools):
            tool_id = f"tool_{tool}"
            t_angle = (angle - SPREAD + i * step) if n > 1 else angle

            if tool_id not in added:
                tx, ty = _polar(R_TOOL, t_angle)
                tcolor = _TOOL_COLOR.get(tool, "#64748b")
                nodes.append({
                    "id": tool_id, "label": tool,
                    "shape": "diamond", "size": 22,
                    "color": {"background": tcolor, "border": tcolor,
                              "highlight": {"background": tcolor, "border": "#ffffff"}},
                    "font": {"color": "#0d0d14", "size": 11, "bold": True},
                    "x": tx, "y": ty, "physics": False, "fixed": True,
                    "title": f"<b>{tool}</b>",
                    "node_type": "tool",
                })
                added.add(tool_id)

            # BU → ツール エッジ（connection ごと）
            conn_row = next(
                (c for c in connections if c["bu"] == bu and c["tool"] == tool), None
            )
            direction = conn_row["direction"] if conn_row else "both"
            note      = conn_row["note"]      if conn_row else ""
            dir_style = {
                "read":  {"color": "#3b82f6", "dashes": [6, 4]},
                "write": {"color": "#f59e0b", "dashes": [4, 3]},
                "both":  {"color": "#10b981", "dashes": False},
            }.get(direction, {"color": "#64748b", "dashes": False})

            edges.append({
                "from": bu_id, "to": tool_id,
                "color": {"color": dir_style["color"]},
                "width": 1.5, "dashes": dir_style["dashes"],
                "arrows": {"to": {"scaleFactor": 0.7}},
                "smooth": {"type": "curvedCW", "roundness": 0.15},
                "label": direction,
                "font": {"size": 9, "color": "#64748b", "strokeWidth": 0},
                "edge_type": "tool_connection",
                "title": note,
            })

    # BU→Claude の双方向エッジ（Claude利用を明示）
    for c in connections:
        if c["tool"] != "Claude":
            continue
        bu_id = f"bu_{c['bu']}"
        edges.append({
            "from": bu_id, "to": "claude_hub",
            "color": {"color": "#a855f7", "opacity": 0.5},
            "width": 1, "dashes": [4, 4],
            "arrows": {"to": {"scaleFactor": 0.6}},
            "smooth": {"type": "curvedCCW", "roundness": 0.2},
            "label": "uses", "font": {"size": 9, "color": "#7c3aed", "strokeWidth": 0},
            "edge_type": "uses_claude",
            "title": c["note"] or "",
        })

    return {"nodes": nodes, "edges": edges}


@router.get("/map/agent_edges")
def list_agent_edges():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM agent_edges").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/map/tool_connections")
def list_tool_connections():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tool_connections ORDER BY bu, tool").fetchall()
    conn.close()
    return [dict(r) for r in rows]
