#!/usr/bin/env python3
"""
経営管理オーケストレーター
canonical_id: mgmt_orchestrator
layer: 経営管理
level: Level 1（対話型）

責務:
  経営管理部門全体を統括。経理 / 法務 / 経営戦略サブエージェントへ
  タスクを委譲し、月次レポート・法令遵守・承認フローを管理する。

利用API: Claude / GSheets / Slack
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / "config" / ".env")
logger = logging.getLogger(__name__)


import os
import anthropic

_CLIENT = None


def _get_client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _CLIENT


def _route_task(task: str) -> str:
    """
    タスク内容から担当部門（accounting/legal/strategy）を判定する。

    Returns:
        domain: "accounting" | "legal" | "strategy"
    """
    res = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "経営管理タスクを分類してください。\n"
            "出力: domain=accounting|legal|strategy\n"
            "accounting=経理/請求書/P&L / legal=契約書/法務/規約 / strategy=戦略/KPI/報告"
        ),
        messages=[{"role": "user", "content": task}],
    )
    text = res.content[0].text.strip()
    if "domain=legal" in text:
        return "legal"
    if "domain=strategy" in text:
        return "strategy"
    return "accounting"


class MgmtOrchestrator:
    """経営管理オーケストレーター（Level 1）— 経理/法務/戦略へ委譲する"""

    agent_key  = "mgmt_orchestrator"
    agent_name = "経営管理オーケストレーター"
    agent_desc = "【Orchestrator】経営管理部門全体を統括（経理・法務・戦略）"

    sub_agents = ["経理", "法務", "経営戦略"]

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task[:60]}")

        domain = _route_task(task)
        logger.info(f"[{self.agent_name}] ルーティング → domain={domain}")

        if domain == "legal":
            from agents._experimental.management.legal.agent import LegalAgent  # noqa: PLC0415
            agent = LegalAgent()
        elif domain == "strategy":
            # 戦略エージェントは経理を代理（将来実装）
            from agents._experimental.management.accounting.agent import AccountingAgent  # noqa: PLC0415
            agent = AccountingAgent()
            agent.agent_name = "経営戦略（準備中）"
        else:
            from agents._experimental.management.accounting.agent import AccountingAgent  # noqa: PLC0415
            agent = AccountingAgent()

        try:
            return agent.run(task)
        except NotImplementedError:
            return (
                f"[{agent.agent_name}] は現在開発中です。\n"
                f"タスク: {task}\n"
                f"担当: {agent.agent_name} → Phase 2 以降で実装予定"
            )

    def status(self) -> dict:
        return {
            "key": self.agent_key,
            "name": self.agent_name,
            "sub_agents": self.sub_agents,
            "status": "dev",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    task = sys.argv[1] if len(sys.argv) > 1 else "今月の売上請求書一覧を作成してください"
    print(MgmtOrchestrator().run(task))
