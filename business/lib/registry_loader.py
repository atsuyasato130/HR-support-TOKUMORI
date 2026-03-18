#!/usr/bin/env python3
"""
registry_loader.py — エージェントレジストリ ロード・検索・重複チェック

business/agents/registry.json を読み込み、エージェントの検索・重複検出・
新規登録バリデーションを担う。全 Worker・ツールから統一的に参照する。

## 使い方
  from business.lib.registry_loader import RegistryLoader

  loader = RegistryLoader()
  agent = loader.get("hr_executor_sf_bulk")        # 1件取得
  agents = loader.find_by_role("executor")         # ロールで絞り込み
  ok, msg = loader.can_register("hr_executor_new") # 登録可否チェック
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).parent.parent / "agents" / "registry.json"


class RegistryLoader:
    """
    registry.json のキャッシュ付きローダー。

    インスタンスを作成すると registry.json を読み込む。
    ファイルが更新された場合は reload() を呼ぶこと。
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or _REGISTRY_PATH
        self._data: dict = {}
        self._agents: dict[str, dict] = {}  # id → agent dict
        self.reload()

    def reload(self) -> None:
        """registry.json を再読み込みする。"""
        if not self._path.exists():
            logger.warning("registry.json が見つかりません: %s", self._path)
            self._data = {}
            self._agents = {}
            return
        with open(self._path, encoding="utf-8") as f:
            self._data = json.load(f)
        self._agents = {a["id"]: a for a in self._data.get("agents", [])}
        logger.debug("registry 読み込み完了: %d エージェント", len(self._agents))

    # ── 検索 ────────────────────────────────────────────────────────

    def get(self, agent_id: str) -> Optional[dict]:
        """IDでエージェントを1件取得。なければ None。"""
        return self._agents.get(agent_id)

    def all(self) -> list[dict]:
        """全エージェントをリストで返す。"""
        return list(self._agents.values())

    def find_by_role(self, role: str) -> list[dict]:
        """ロールで絞り込む。例: find_by_role("executor")"""
        return [a for a in self._agents.values() if a.get("role") == role]

    def find_by_domain(self, domain: str) -> list[dict]:
        """ドメインで絞り込む。例: find_by_domain("hr")"""
        return [a for a in self._agents.values() if a.get("domain") == domain]

    def find_by_status(self, status: str) -> list[dict]:
        """ステータスで絞り込む。例: find_by_status("active")"""
        return [a for a in self._agents.values() if a.get("status") == status]

    def find_by_dependency(self, dep: str) -> list[dict]:
        """特定の依存APIを持つエージェントを返す。例: find_by_dependency("salesforce_api")"""
        return [a for a in self._agents.values() if dep in a.get("dependencies", [])]

    # ── 重複チェック ────────────────────────────────────────────────

    def exists(self, agent_id: str) -> bool:
        """IDが既に登録済みか確認する。"""
        return agent_id in self._agents

    def can_register(self, agent_id: str) -> tuple[bool, str]:
        """
        新規エージェントを登録できるか確認する。

        Returns:
            (can_register, message)
            can_register=False の場合、既存エージェントの統合・拡張を推奨するメッセージを返す。
        """
        if self.exists(agent_id):
            existing = self._agents[agent_id]
            return False, (
                f"ID '{agent_id}' は既に登録済みです。\n"
                f"  既存: {existing['description']}\n"
                f"  モジュール: {existing['legacy_module']}\n"
                f"  → 新規作成ではなく「拡張（version up）」または「統合」を検討してください。"
            )

        # 類似エージェント検出（target単語の重複）
        from business.agents.name_validator import find_similar
        registry_data = {"agents": self.all()}
        similar = find_similar(agent_id, registry_data)
        if similar:
            names = [a["id"] for a in similar]
            return True, (
                f"⚠️  類似エージェントが存在します（統合を検討してください）: {names}\n"
                f"登録は可能ですが、本当に独立したエージェントが必要か確認してください。"
            )

        return True, f"✅ '{agent_id}' は新規登録可能です。"

    # ── メタデータ参照 ───────────────────────────────────────────────

    def count(self) -> int:
        """登録エージェント数を返す。"""
        return len(self._agents)

    def summary(self) -> dict:
        """統計サマリーを返す（ロール別カウント等）。"""
        roles: dict[str, int] = {}
        statuses: dict[str, int] = {}
        for a in self._agents.values():
            roles[a.get("role", "unknown")] = roles.get(a.get("role", "unknown"), 0) + 1
            statuses[a.get("status", "unknown")] = statuses.get(a.get("status", "unknown"), 0) + 1
        return {
            "total": self.count(),
            "by_role": roles,
            "by_status": statuses,
            "version": self._data.get("version", "unknown"),
            "updated": self._data.get("updated", "unknown"),
        }
