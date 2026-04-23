#!/usr/bin/env python3
"""
memory/tool_usage.py — ツール使用記憶

「何が有効だったか」のツール別パフォーマンス統計を蓄積する。
成功率・平均実行時間・エラーパターンを記録し、
Plannerがコスト効率の良いツール選択をできるようにする。

保存先: ai-empire/core/harness/memory/data/tool_usage.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("harness.memory.tool_usage")

_DATA_DIR = Path(__file__).parent / "data"
_FILE = _DATA_DIR / "tool_usage.json"


class ToolUsageMemory:
    """ツール使用実績の記憶（何が有効だったか）。"""

    def __init__(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, dict] = self._load()

    # ── 記録 ────────────────────────────────────────────────────

    def add(
        self,
        agent_tag: str,
        success: bool,
        duration_sec: float = 0.0,
        error_type: Optional[str] = None,
        context: str = "",
    ) -> None:
        """
        ツール使用結果を記録する。

        Args:
            agent_tag:    エージェントタグ
            success:      成功したか
            duration_sec: 実行時間（秒）
            error_type:   エラー種別（失敗時）
            context:      実行コンテキストのメモ
        """
        if agent_tag not in self._data:
            self._data[agent_tag] = {
                "total_runs": 0,
                "success_count": 0,
                "fail_count": 0,
                "total_duration_sec": 0.0,
                "error_types": {},
                "last_run": None,
                "history": [],
            }

        stats = self._data[agent_tag]
        stats["total_runs"] += 1
        if success:
            stats["success_count"] += 1
        else:
            stats["fail_count"] += 1
            if error_type:
                stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1

        stats["total_duration_sec"] += duration_sec
        stats["last_run"] = datetime.now().isoformat()

        # 直近20件の履歴を保持
        stats["history"] = (stats.get("history", []) + [{
            "success": success,
            "duration_sec": duration_sec,
            "error_type": error_type,
            "context": context[:100] if context else "",
            "at": datetime.now().isoformat(),
        }])[-20:]

        self._save()

    # ── 統計取得 ─────────────────────────────────────────────────

    def get_stats(self, agent_tag: str) -> Optional[dict]:
        """タグの統計情報を返す。"""
        if agent_tag not in self._data:
            return None
        stats = self._data[agent_tag]
        total = stats["total_runs"]
        return {
            "agent_tag": agent_tag,
            "total_runs": total,
            "success_rate": stats["success_count"] / total if total else 0.0,
            "avg_duration_sec": stats["total_duration_sec"] / total if total else 0.0,
            "top_errors": sorted(
                stats.get("error_types", {}).items(),
                key=lambda x: x[1], reverse=True,
            )[:3],
            "last_run": stats.get("last_run"),
        }

    def get_all_stats(self) -> List[dict]:
        """全タグの統計を成功率降順で返す。"""
        result = []
        for tag in self._data:
            s = self.get_stats(tag)
            if s:
                result.append(s)
        return sorted(result, key=lambda x: x["success_rate"], reverse=True)

    def get_reliable_tags(self, min_success_rate: float = 0.7, min_runs: int = 3) -> List[str]:
        """信頼性の高いタグ一覧を返す（Plannerのタグ選択に使用）。"""
        reliable = []
        for tag, stats in self._data.items():
            total = stats["total_runs"]
            if total >= min_runs:
                rate = stats["success_count"] / total
                if rate >= min_success_rate:
                    reliable.append(tag)
        return reliable

    def get_context_for_planner(self) -> str:
        """Plannerへ渡す「ツール信頼性コンテキスト」を文字列で返す。"""
        stats_list = self.get_all_stats()
        if not stats_list:
            return ""
        lines = ["【ツール使用実績（参考）】"]
        for s in stats_list[:8]:  # 上位8件
            if s["total_runs"] >= 2:
                lines.append(
                    f"- {s['agent_tag']}: 成功率{s['success_rate']:.0%} "
                    f"({s['total_runs']}回) 平均{s['avg_duration_sec']:.0f}秒"
                )
        return "\n".join(lines) if len(lines) > 1 else ""

    def get_error_patterns(self, agent_tag: str) -> List[str]:
        """過去のエラーパターンを返す（Evaluatorの改善提案に使用）。"""
        if agent_tag not in self._data:
            return []
        errors = self._data[agent_tag].get("error_types", {})
        return [f"{err}（{cnt}回）" for err, cnt in sorted(errors.items(), key=lambda x: x[1], reverse=True)[:3]]

    # ── 内部 ────────────────────────────────────────────────────

    def _load(self) -> Dict[str, dict]:
        if _FILE.exists():
            try:
                return json.loads(_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self) -> None:
        _FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
