#!/usr/bin/env python3
"""
memory/store.py — MemoryStore（MUSE Memory 統合ファサード）

3種類の記憶（Strategic / Procedural / ToolUsage）を統合管理する。
HarnessRunner と BaseAgent から単一のインターフェースで全記憶にアクセスできる。

使い方:
    mem = MemoryStore()

    # タスク実行前: Plannerへのコンテキスト取得
    context = mem.get_context_for_task("Salesforceにフィールドを追加")

    # タスク実行後: 記憶を更新（Reflect-Memorize フェーズ）
    mem.reflect(
        task="Salesforceにフィールドを追加",
        agent_tag="SF-Schema",
        success=True,
        duration_sec=42.0,
        lesson="dry-runを必ず先に実行すると安全"
    )
"""

from __future__ import annotations

import logging
from typing import Optional

from .procedural import ProceduralMemory
from .strategic import StrategicMemory
from .tool_usage import ToolUsageMemory

logger = logging.getLogger("harness.memory.store")

# シングルトンインスタンス（プロセス内で共有）
_instance: Optional["MemoryStore"] = None


class MemoryStore:
    """
    MUSE Memory の統合ファサード。

    strategic  : 何をすべきか（ルール・教訓）
    procedural : どうやるか（タグ別手順）
    tool_usage : 何が有効か（ツール成功率・実行時間）
    """

    def __init__(self) -> None:
        self.strategic = StrategicMemory()
        self.procedural = ProceduralMemory()
        self.tool_usage = ToolUsageMemory()

    @classmethod
    def get_instance(cls) -> "MemoryStore":
        """プロセス内シングルトンを返す。"""
        global _instance
        if _instance is None:
            _instance = cls()
        return _instance

    # ── Planner へのコンテキスト提供 ──────────────────────────

    def get_context_for_task(self, task_description: str) -> str:
        """
        タスク記述に関連するすべての記憶をまとめてコンテキスト文字列で返す。
        Plannerのプロンプトに付加して使用する。

        Returns:
            Plannerへ渡すコンテキスト文字列（空文字の場合は記憶なし）
        """
        parts = []

        # 戦略的記憶（関連ルール・教訓）
        strategic_hits = self.strategic.search(task_description, top_k=3)
        if strategic_hits:
            parts.append("【過去の教訓・ルール】")
            parts.extend(f"- {s}" for s in strategic_hits)

        # 手続き的記憶（関連タグの手順）
        # タスク記述からタグを推定して手順を取得
        for tag in self.procedural.get_all_tags():
            if tag.lower() in task_description.lower():
                procs = self.procedural.get_for_tag(tag, min_success_rate=0.7)
                if procs:
                    parts.append(f"【{tag} の成功手順】")
                    parts.extend(f"- {p}" for p in procs[:3])

        # ツール使用実績
        tool_ctx = self.tool_usage.get_context_for_planner()
        if tool_ctx:
            parts.append(tool_ctx)

        return "\n".join(parts)

    # ── Reflect-Memorize フェーズ ──────────────────────────────

    def reflect(
        self,
        task: str,
        agent_tag: str,
        success: bool,
        duration_sec: float = 0.0,
        lesson: str = "",
        error_type: str = "",
    ) -> None:
        """
        タスク実行後の Reflect-Memorize フェーズ。
        成功/失敗から自動的に記憶を更新する。

        Args:
            task:         実行したタスクの説明
            agent_tag:    使用したエージェントタグ
            success:      成功したか
            duration_sec: 実行時間
            lesson:       人間が追記した教訓（省略可）
            error_type:   エラー種別（失敗時）
        """
        # ツール使用記憶を更新（常に）
        self.tool_usage.add(
            agent_tag=agent_tag,
            success=success,
            duration_sec=duration_sec,
            error_type=error_type if not success else None,
            context=task[:100],
        )

        # 教訓がある場合は戦略的記憶に追加
        if lesson:
            if success:
                self.strategic.add_from_success(task, lesson)
            else:
                self.strategic.add_from_failure(task, error_type or "不明なエラー", lesson)

        logger.info(
            "Reflect完了: task=%s tag=%s success=%s lesson=%s",
            task[:40], agent_tag, success, lesson[:40] if lesson else "なし",
        )

    def reflect_from_harness_result(self, result) -> None:
        """
        HarnessResult から自動的に Reflect-Memorize を実行する。
        runner.py から呼び出すユーティリティメソッド。
        """
        if not result.step_results:
            return

        for sr in result.step_results:
            if sr.agent_tag:
                self.tool_usage.add(
                    agent_tag=sr.agent_tag,
                    success=sr.success,
                    error_type=sr.error_msg[:50] if sr.error_msg else None,
                )

        # 評価スコアが低い場合は戦略的記憶に問題を記録
        if result.evaluation and not result.evaluation.passed:
            for issue in result.evaluation.issues[:2]:
                self.strategic.add(
                    content=f"【要注意】{result.plan.goal if result.plan else 'タスク'}: {issue}",
                    source="failure",
                    importance=4,
                )

    # ── 統計・サマリー ────────────────────────────────────────

    def get_summary(self) -> dict:
        """全記憶のサマリーを返す。"""
        return {
            "strategic_count": len(self.strategic.get_all()),
            "procedural_tags": self.procedural.get_summary(),
            "tool_stats": {
                s["agent_tag"]: {
                    "success_rate": round(s["success_rate"], 2),
                    "total_runs": s["total_runs"],
                }
                for s in self.tool_usage.get_all_stats()
            },
        }
