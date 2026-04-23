#!/usr/bin/env python3
"""
managed_agent_runner.py — Claude Managed Agents 統合（Phase 5）

【役割】
  Anthropic の Claude Managed Agents API ($0.08/セッション時間) を使って
  HarnessRunner のタスクをフルマネージドで実行する。

  既存の HarnessRunner はローカル実行（PC常時ON必要）。
  ManagedAgentRunner は Anthropic インフラ上で実行されるため
  Level 3（VPS不要・PC電源不要）を実現できる。

【料金試算】
  1日10タスク × 平均5分 = 50分/日 × 30日 = 1500分 = 25時間/月
  25時間 × $0.08 = $2/月（約300円）で Level 3 が実現

【使い方】
  # 通常実行（ローカルHarnessRunner）
  python3 core/infrastructure/empire_os.py dispatch "タスク"

  # Managed Agents で実行
  python3 core/infrastructure/empire_os.py dispatch "タスク" --managed

  # コスト見積もり確認
  runner = ManagedAgentRunner()
  print(runner.estimate_cost(tasks_per_day=10, avg_minutes=5))

【前提条件】
  - ANTHROPIC_API_KEY が設定済み
  - claude-agent-sdk がインストール済み（pip install claude-agent-sdk）
  - 現時点では Public Beta: https://platform.claude.com/docs/en/managed-agents/overview
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("managed_agent_runner")

_EMPIRE_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ManagedRunResult:
    """ManagedAgentRunner の実行結果。"""
    task: str
    success: bool
    output: str
    session_id: str = ""
    duration_sec: float = 0.0
    estimated_cost_usd: float = 0.0
    error: str = ""


class ManagedAgentRunner:
    """
    Claude Managed Agents API を使ってタスクを実行するランナー。

    claude-agent-sdk が利用可能な場合は Managed Agents を使用し、
    利用不可の場合は通常の HarnessRunner にフォールバックする。

    Args:
        model:          使用するモデル（デフォルト: claude-sonnet-4-6）
        max_turns:      最大ターン数（デフォルト: 20）
        system_prompt:  エージェントのシステムプロンプト（省略時はデフォルト使用）
    """

    HOURLY_RATE_USD = 0.08  # $0.08/セッション時間

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_turns: int = 20,
        system_prompt: Optional[str] = None,
    ) -> None:
        self._model = model
        self._max_turns = max_turns
        self._system_prompt = system_prompt or self._default_system_prompt()
        self._sdk_available = self._check_sdk()

    # ── パブリックAPI ──────────────────────────────────────────

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> ManagedRunResult:
        """
        タスクを Managed Agents で実行する。
        SDK が利用不可の場合は HarnessRunner にフォールバック。

        Args:
            task:    実行するタスク（自然言語）
            context: 追加コンテキスト

        Returns:
            ManagedRunResult
        """
        if self._sdk_available:
            return self._run_managed(task, context or {})
        else:
            logger.info("claude-agent-sdk 未インストール → HarnessRunner にフォールバック")
            return self._run_fallback(task, context or {})

    def estimate_cost(
        self,
        tasks_per_day: int = 10,
        avg_minutes: float = 5.0,
        days: int = 30,
    ) -> dict:
        """
        月間コスト見積もりを返す。

        Args:
            tasks_per_day: 1日あたりのタスク数
            avg_minutes:   1タスクの平均実行時間（分）
            days:          月間日数

        Returns:
            {"monthly_hours": float, "monthly_usd": float, "monthly_jpy": int}
        """
        monthly_hours = (tasks_per_day * avg_minutes * days) / 60.0
        monthly_usd = monthly_hours * self.HOURLY_RATE_USD
        monthly_jpy = int(monthly_usd * 150)  # 概算レート
        return {
            "tasks_per_day": tasks_per_day,
            "avg_minutes": avg_minutes,
            "monthly_hours": round(monthly_hours, 1),
            "monthly_usd": round(monthly_usd, 2),
            "monthly_jpy": monthly_jpy,
            "note": f"$0.08/時間 × {monthly_hours:.1f}h = ${monthly_usd:.2f}/月（約{monthly_jpy:,}円）",
        }

    @property
    def is_managed_available(self) -> bool:
        """Managed Agents が利用可能かどうか。"""
        return self._sdk_available

    # ── 内部実装 ──────────────────────────────────────────────

    def _check_sdk(self) -> bool:
        """claude-agent-sdk のインストール状態を確認する。"""
        try:
            import claude_agent_sdk  # noqa: F401
            logger.info("claude-agent-sdk が利用可能です")
            return True
        except ImportError:
            logger.info(
                "claude-agent-sdk が未インストールです。"
                "インストール: pip install claude-agent-sdk"
            )
            return False

    def _run_managed(self, task: str, context: Dict[str, Any]) -> ManagedRunResult:
        """Managed Agents SDK を使って実行する。"""
        import claude_agent_sdk as sdk

        start = time.time()
        session_id = ""
        output = ""

        try:
            # コンテキストをプロンプトに付加
            prompt = task
            if context:
                ctx_str = "\n".join(f"- {k}: {v}" for k, v in context.items() if v)
                prompt = f"{task}\n\n【コンテキスト】\n{ctx_str}"

            logger.info("Managed Agents 実行開始: %s", task[:60])

            # セッション作成・実行
            with sdk.Session(
                model=self._model,
                system=self._system_prompt,
                max_turns=self._max_turns,
            ) as session:
                session_id = session.id
                result = session.run(prompt)
                output = result.text or ""

            duration = time.time() - start
            cost = (duration / 3600.0) * self.HOURLY_RATE_USD

            logger.info(
                "Managed Agents 完了: session=%s duration=%.1fs cost=$%.4f",
                session_id, duration, cost,
            )
            return ManagedRunResult(
                task=task,
                success=True,
                output=output,
                session_id=session_id,
                duration_sec=duration,
                estimated_cost_usd=cost,
            )

        except Exception as exc:
            duration = time.time() - start
            logger.error("Managed Agents エラー: %s", exc)
            return ManagedRunResult(
                task=task,
                success=False,
                output="",
                session_id=session_id,
                duration_sec=duration,
                error=str(exc),
            )

    def _run_fallback(self, task: str, context: Dict[str, Any]) -> ManagedRunResult:
        """SDK未インストール時のフォールバック（HarnessRunner使用）。"""
        start = time.time()
        try:
            import sys
            sys.path.insert(0, str(_EMPIRE_ROOT))
            from core.harness import HarnessRunner
            runner = HarnessRunner()
            result = runner.run(task, context=context)
            duration = time.time() - start
            return ManagedRunResult(
                task=task,
                success=result.status.value == "done",
                output=result.final_output,
                duration_sec=duration,
                estimated_cost_usd=0.0,  # ローカル実行はゼロ
            )
        except Exception as exc:
            duration = time.time() - start
            return ManagedRunResult(
                task=task,
                success=False,
                output="",
                duration_sec=duration,
                error=str(exc),
            )

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "あなたはTokumoriのエージェントです。\n"
            "HRsupport事業（採用支援）のタスクを自律的に実行します。\n"
            "Salesforce・Notion・Slack・Gmail・Google Slidesなどの外部ツールを活用してください。\n"
            "タスク完了後は結果を簡潔に報告してください。"
        )


def install_guide() -> str:
    """claude-agent-sdk のインストール手順を返す。"""
    return """
Claude Managed Agents を使うには claude-agent-sdk が必要です:

  pip install claude-agent-sdk

インストール後の動作確認:
  python3 -c "import claude_agent_sdk; print('OK')"

公式ドキュメント:
  https://platform.claude.com/docs/en/managed-agents/overview

コスト試算:
  python3 core/infrastructure/managed_agent_runner.py --estimate
""".strip()


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Claude Managed Agents Runner")
    parser.add_argument("--estimate", action="store_true", help="月間コスト見積もりを表示")
    parser.add_argument("--tasks-per-day", type=int, default=10)
    parser.add_argument("--avg-minutes", type=float, default=5.0)
    parser.add_argument("task", nargs="?", help="実行するタスク（自然言語）")
    args = parser.parse_args()

    runner = ManagedAgentRunner()

    if args.estimate or not args.task:
        est = runner.estimate_cost(
            tasks_per_day=args.tasks_per_day,
            avg_minutes=args.avg_minutes,
        )
        print("\n📊 月間コスト見積もり")
        print(f"  タスク数:    {est['tasks_per_day']}件/日")
        print(f"  平均時間:    {est['avg_minutes']}分/タスク")
        print(f"  月間実行時間: {est['monthly_hours']}時間")
        print(f"  月間コスト:  ${est['monthly_usd']} ({est['monthly_jpy']:,}円)")
        print(f"\n  SDK利用可否: {'✅ 利用可能' if runner.is_managed_available else '❌ 未インストール'}")
        if not runner.is_managed_available:
            print(f"\n{install_guide()}")
    elif args.task:
        result = runner.run(args.task)
        print(f"\n{'✅' if result.success else '❌'} {result.task[:60]}")
        print(f"  時間: {result.duration_sec:.1f}s")
        if result.estimated_cost_usd > 0:
            print(f"  コスト: ${result.estimated_cost_usd:.4f}")
        print(f"\n{result.output}")
