#!/usr/bin/env python3
"""
memory/strategic.py — 戦略的記憶

「何をすべきか・何を避けるべきか」の高レベルなルール・教訓を蓄積する。
失敗から学んだ教訓・成功パターン・ドメイン知識を保存する。

保存先: ai-empire/core/harness/memory/data/strategic.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("harness.memory.strategic")

_DATA_DIR = Path(__file__).parent / "data"
_FILE = _DATA_DIR / "strategic.json"


class StrategicMemory:
    """戦略的記憶（何をすべきか・何を避けるべきか）。"""

    def __init__(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._entries: List[dict] = self._load()

    # ── 追加 ────────────────────────────────────────────────────

    def add(
        self,
        content: str,
        source: str = "manual",
        tags: Optional[List[str]] = None,
        importance: int = 3,
    ) -> None:
        """
        戦略的記憶を追加する。

        Args:
            content:    記憶の内容（ルール・教訓・パターン）
            source:     記憶の出所（"failure", "success", "manual"）
            tags:       関連タグ（例: ["SF-Schema", "Salesforce"]）
            importance: 重要度 1〜5（5が最重要）
        """
        entry = {
            "id": f"s-{len(self._entries)+1:04d}",
            "content": content,
            "source": source,
            "tags": tags or [],
            "importance": importance,
            "use_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_used": None,
        }
        self._entries.append(entry)
        self._save()
        logger.info("戦略的記憶を追加: %s", content[:60])

    def add_from_failure(self, task: str, error: str, lesson: str) -> None:
        """失敗から教訓を自動生成して記憶に追加する。"""
        content = f"【失敗パターン】{task[:50]} → {error[:80]}\n【教訓】{lesson}"
        self.add(content, source="failure", importance=4)

    def add_from_success(self, task: str, pattern: str) -> None:
        """成功パターンを記憶に追加する。"""
        content = f"【成功パターン】{task[:50]} → {pattern}"
        self.add(content, source="success", importance=3)

    # ── 検索 ────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        クエリに関連する記憶を検索する（キーワードマッチ）。

        Returns:
            関連する記憶の content リスト（重要度・使用頻度順）
        """
        query_lower = query.lower()
        scored = []
        for e in self._entries:
            score = 0
            content_lower = e["content"].lower()
            # キーワードマッチ
            for word in query_lower.split():
                if word in content_lower:
                    score += 1
            # タグマッチ
            for tag in e.get("tags", []):
                if tag.lower() in query_lower:
                    score += 2
            if score > 0:
                scored.append((score * e.get("importance", 3), e))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [e["content"] for _, e in scored[:top_k]]

        # 使用カウントを更新
        used_ids = {e["id"] for _, e in scored[:top_k]}
        for entry in self._entries:
            if entry["id"] in used_ids:
                entry["use_count"] = entry.get("use_count", 0) + 1
                entry["last_used"] = datetime.now().isoformat()
        if used_ids:
            self._save()

        return results

    def get_all(self, source: Optional[str] = None) -> List[dict]:
        """全記憶を返す（source でフィルタ可能）。"""
        if source:
            return [e for e in self._entries if e.get("source") == source]
        return list(self._entries)

    def prune_low_importance(self, min_importance: int = 2) -> int:
        """重要度が低い記憶を削除してストレージを整理する。"""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.get("importance", 3) >= min_importance]
        removed = before - len(self._entries)
        if removed:
            self._save()
            logger.info("戦略的記憶を%d件削除（重要度<%d）", removed, min_importance)
        return removed

    # ── 内部 ────────────────────────────────────────────────────

    def _load(self) -> List[dict]:
        if _FILE.exists():
            try:
                return json.loads(_FILE.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        _FILE.write_text(
            json.dumps(self._entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
