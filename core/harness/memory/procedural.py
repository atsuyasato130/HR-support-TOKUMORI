#!/usr/bin/env python3
"""
memory/procedural.py — 手続き的記憶

「どうやるか」の具体的な手順・ベストプラクティスをエージェントタグ別に蓄積する。
タスク実行後の成功パターンを手順として保存し、次回のPlanner/Generatorに提供する。

保存先: ai-empire/core/harness/memory/data/procedural.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("harness.memory.procedural")

_DATA_DIR = Path(__file__).parent / "data"
_FILE = _DATA_DIR / "procedural.json"


class ProceduralMemory:
    """手続き的記憶（どうやるか・成功した手順）。"""

    def __init__(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, List[dict]] = self._load()

    # ── 追加 ────────────────────────────────────────────────────

    def add(
        self,
        agent_tag: str,
        procedure: str,
        context: str = "",
        success_rate: float = 1.0,
    ) -> None:
        """
        特定エージェントタグの手順を追加する。

        Args:
            agent_tag:    対象エージェントタグ（例: "SF-Schema"）
            procedure:    手順の説明（具体的なステップ）
            context:      この手順が有効なコンテキスト
            success_rate: 成功率（0.0〜1.0）
        """
        entry = {
            "id": f"p-{agent_tag}-{len(self._data.get(agent_tag, []))+1:03d}",
            "procedure": procedure,
            "context": context,
            "success_rate": success_rate,
            "use_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_used": None,
        }
        self._data.setdefault(agent_tag, []).append(entry)
        self._save()
        logger.info("手続き的記憶を追加 [%s]: %s", agent_tag, procedure[:60])

    def update_success_rate(self, agent_tag: str, procedure_id: str, success: bool) -> None:
        """手順の成功率を実績で更新する（指数移動平均）。"""
        for entry in self._data.get(agent_tag, []):
            if entry["id"] == procedure_id:
                # EMA: new = 0.9 * old + 0.1 * result
                entry["success_rate"] = 0.9 * entry["success_rate"] + 0.1 * (1.0 if success else 0.0)
                entry["use_count"] = entry.get("use_count", 0) + 1
                entry["last_used"] = datetime.now().isoformat()
                self._save()
                break

    # ── 検索 ────────────────────────────────────────────────────

    def get_for_tag(self, agent_tag: str, min_success_rate: float = 0.6) -> List[str]:
        """
        指定タグの手順を成功率の高い順に返す。

        Args:
            agent_tag:        エージェントタグ
            min_success_rate: 最低成功率フィルタ

        Returns:
            手順の説明リスト
        """
        entries = [
            e for e in self._data.get(agent_tag, [])
            if e.get("success_rate", 1.0) >= min_success_rate
        ]
        entries.sort(key=lambda e: e.get("success_rate", 0), reverse=True)
        result = [e["procedure"] for e in entries[:5]]

        # 使用カウント更新
        used_ids = {e["id"] for e in entries[:5]}
        for entry in self._data.get(agent_tag, []):
            if entry["id"] in used_ids:
                entry["use_count"] = entry.get("use_count", 0) + 1
                entry["last_used"] = datetime.now().isoformat()
        if used_ids:
            self._save()

        return result

    def get_all_tags(self) -> List[str]:
        """記憶のあるタグ一覧を返す。"""
        return list(self._data.keys())

    def get_summary(self) -> Dict[str, int]:
        """タグ別の手順数サマリーを返す。"""
        return {tag: len(entries) for tag, entries in self._data.items()}

    # ── 内部 ────────────────────────────────────────────────────

    def _load(self) -> Dict[str, List[dict]]:
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
