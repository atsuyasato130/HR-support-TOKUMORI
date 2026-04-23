#!/usr/bin/env python3
"""
sync_os.py — Tokumori OS 自動同期スクリプト

empire.db の最新状態から以下を自動更新:
  1. knowledge/hr_support/AGENT_MANIFEST.json  — 全エージェントカタログ再生成
  2. STATUS_REPORT.md                          — エージェント数・BU表・更新日を自動修正

使い方:
  python3 utils/sync_os.py           # 通常実行（変更内容を表示）
  python3 utils/sync_os.py --quiet   # フック用（変更があった場合のみ1行出力）
"""
from __future__ import annotations

import json
import re
import sys
import sqlite3
import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = _ROOT / "dashboard" / "empire.db"
MANIFEST_PATH = _ROOT / "knowledge" / "hr_support" / "AGENT_MANIFEST.json"
STATUS_PATH = _ROOT / "STATUS_REPORT.md"

QUIET = "--quiet" in sys.argv


def _log(msg: str) -> None:
    if not QUIET:
        print(msg)


# ── DB から全エージェントを取得 ────────────────────────────────────────────
def _load_agents() -> list[dict]:
    if not DB_PATH.exists():
        print(f"⚠️  empire.db が見つかりません: {DB_PATH}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT canonical_id, name, layer, status, apis, description FROM agents ORDER BY layer, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── AGENT_MANIFEST.json を empire.db から再生成 ──────────────────────────
def _sync_manifest(agents: list[dict]) -> bool:
    """変更があれば書き込んで True を返す"""
    # BU マッピング（layer → bu）
    layer_to_bu = {
        "全体":     "全体",
        "HRsupport": "HRsupport",
        "RPO":      "RPO",
        "Sales":    "Sales",
        "人事":     "人事",
        "経営管理": "経営管理",
        "組織管理": "組織管理",
        "品質管理": "品質管理",
        "経営戦略": "経営戦略",
    }

    # layer ラベル → manifest layer 種別の推定ルール
    def _infer_layer_type(cid: str, desc: str | None) -> str:
        desc = desc or ""
        if "【Group】" in desc:       return "Group"
        if "orchestrator" in cid:    return "Orchestrator"
        if "sub_orch" in cid:        return "SubOrchestrator"
        if cid.startswith(("hrsup_chuto", "hrsup_shinsotsu")): return "SubOrchestrator"
        if cid.startswith(("hrsup_ca", "hrsup_ra", "hrsup_lg",
                            "rpo_cs", "sales_fs", "sales_is")): return "Role"
        if "_executor_" in cid:      return "Executor"
        if "_processor_" in cid:     return "Processor"
        if "_parser_"    in cid:     return "Parser"
        if "_watcher_"   in cid:     return "Watcher"
        return "Executor"

    entries = []
    for a in agents:
        cid    = a["canonical_id"]
        layer  = a["layer"] or "その他"
        bu     = layer_to_bu.get(layer, layer)
        status_raw = a["status"] or "設計中"
        status_key = {"稼働中": "active", "開発中": "dev", "設計中": "design"}.get(status_raw, "design")
        apis_raw   = a["apis"] or ""
        apis_list  = [x.strip() for x in apis_raw.split(",") if x.strip()]

        entries.append({
            "canonical_id": cid,
            "name":         a["name"],
            "bu":           bu,
            "layer":        _infer_layer_type(cid, a["description"]),
            "desc":         a["description"] or "",
            "apis":         apis_list,
            "status":       status_key,
        })

    manifest = {
        "version":     "3.1",
        "updated":     datetime.date.today().isoformat(),
        "description": f"Tokumori — 全エージェントカタログ（{len(entries)}体・BU別構成）",
        "notice":      "このファイルは sync_os.py により empire.db から自動生成されます。手動編集は次回sync時に上書きされます。",
        "agents":      entries,
    }

    new_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"

    old_text = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    if new_text == old_text:
        _log("  AGENT_MANIFEST.json: 変更なし")
        return False

    MANIFEST_PATH.write_text(new_text, encoding="utf-8")
    _log(f"  ✅ AGENT_MANIFEST.json 更新: {len(entries)}体")
    return True


# ── STATUS_REPORT.md の自動更新箇所を差し替え ──────────────────────────
def _sync_status_report(agents: list[dict]) -> bool:
    """変更があれば書き込んで True を返す"""
    if not STATUS_PATH.exists():
        _log("  STATUS_REPORT.md: ファイルが見つかりません（スキップ）")
        return False

    text = STATUS_PATH.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    total = len(agents)

    # ── ① ヘッダーの「最終更新」日付 ──────────────────────────────────
    text = re.sub(
        r"(\*\*最終更新\*\*:)\s*[\d\-]+",
        rf"\1 {today}",
        text,
    )

    # ── ② 本文の「N体のAIエージェント」 ──────────────────────────────
    text = re.sub(
        r"\d+体のAIエージェント",
        f"{total}体のAIエージェント",
        text,
    )

    # ── ③ BU別エージェント数テーブルの自動再生成 ────────────────────
    # テーブルは <!-- SYNC:BU_TABLE_START --> 〜 <!-- SYNC:BU_TABLE_END --> で囲む
    bu_order = ["HRsupport", "RPO", "Sales", "人事", "経営管理",
                "組織管理", "品質管理", "経営戦略", "全体"]

    from collections import defaultdict
    bu_counts: dict[str, dict] = defaultdict(lambda: {"Orch": 0, "Sub/Role": 0, "Executor/Other": 0, "total": 0})

    for a in agents:
        layer = a["layer"] or "その他"
        bu    = layer
        cid   = a["canonical_id"]
        is_orch = "orchestrator" in cid
        is_sub  = cid.startswith(("hrsup_chuto", "hrsup_shinsotsu")) or \
                  cid.startswith(("hrsup_ca","hrsup_ra","hrsup_lg","rpo_cs","sales_fs","sales_is"))
        bc = bu_counts[layer]
        bc["total"] += 1
        if is_orch:
            bc["Orch"] += 1
        elif is_sub:
            bc["Sub/Role"] += 1
        else:
            bc["Executor/Other"] += 1

    rows = []
    total_orch = total_sub = total_ex = 0
    for bu in bu_order:
        if bu not in bu_counts:
            continue
        c = bu_counts[bu]
        rows.append(f"| {bu} | {c['Orch']} | {c['Sub/Role']} | {c['Executor/Other']} | {c['total']} |")
        total_orch += c["Orch"]
        total_sub  += c["Sub/Role"]
        total_ex   += c["Executor/Other"]

    # その他のBUも追加（bu_orderにない場合）
    for bu, c in bu_counts.items():
        if bu not in bu_order:
            rows.append(f"| {bu} | {c['Orch']} | {c['Sub/Role']} | {c['Executor/Other']} | {c['total']} |")
            total_orch += c["Orch"]
            total_sub  += c["Sub/Role"]
            total_ex   += c["Executor/Other"]

    rows.append(f"| **合計** | **{total_orch}** | **{total_sub}** | **{total_ex}** | **{total}** |")

    new_table = (
        "<!-- SYNC:BU_TABLE_START -->\n"
        "| BU | Orch | サブ/職種 | Executor/Processor 等 | 計 |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n"
        "<!-- SYNC:BU_TABLE_END -->"
    )

    if "<!-- SYNC:BU_TABLE_START -->" in text:
        text = re.sub(
            r"<!-- SYNC:BU_TABLE_START -->.*?<!-- SYNC:BU_TABLE_END -->",
            new_table,
            text,
            flags=re.DOTALL,
        )
    else:
        # マーカーがない場合: 「| BU |」始まりの行から「| **合計** |」行末までを置換
        text = re.sub(
            r"\| BU \| Orch \|[^\n]*\n(?:\|[^\n]*\n)+",
            new_table + "\n",
            text,
        )

    # ── ④ セクション3見出しの「（N体）」を更新 ────────────────────────
    text = re.sub(
        r"(## 3\. エージェント構成)（\d+体）",
        rf"\1（{total}体）",
        text,
    )

    old_text = STATUS_PATH.read_text(encoding="utf-8")
    if text == old_text:
        _log("  STATUS_REPORT.md: 変更なし")
        return False

    STATUS_PATH.write_text(text, encoding="utf-8")
    _log(f"  ✅ STATUS_REPORT.md 更新: {total}体・{today}")
    return True


# ── メイン ─────────────────────────────────────────────────────────────
def main() -> None:
    agents = _load_agents()
    _log(f"sync_os: empire.db から {len(agents)}体 読み込み")

    changed_manifest = _sync_manifest(agents)
    changed_status   = _sync_status_report(agents)

    changed = changed_manifest or changed_status
    if QUIET and changed:
        print(f"[sync_os] OS同期完了 ({datetime.date.today()})")
    elif not QUIET and not changed:
        print("sync_os: 全ファイル最新状態 — 変更なし")


if __name__ == "__main__":
    main()
