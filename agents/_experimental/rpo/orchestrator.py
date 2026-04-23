#!/usr/bin/env python3
"""
RPOオーケストレーター
canonical_id: rpo_orchestrator
layer: RPO
level: Level 1 → Level 2（予定）

責務:
  RPO事業全体の指揮。採用支援業務タスクを分解し、
  組織管理エージェント（org_recruiting）等へ委譲する。

利用API: Claude / Salesforce / GSheets
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
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


def _route_task(task: str) -> tuple[str, str]:
    """
    タスク内容からチーム（cs）と雇用形態を判定する。

    Returns:
        (team, employment): team="cs", employment="seishain"|"gyomu"
    """
    res = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "RPOタスクを分類してください。\n"
            "出力: team=cs employment=seishain|gyomu\n"
            "雇用形態が不明な場合は seishain"
        ),
        messages=[{"role": "user", "content": task}],
    )
    text = res.content[0].text.strip()
    employment = "gyomu" if "employment=gyomu" in text else "seishain"
    return "cs", employment


class RpoOrchestrator:
    """RPO事業オーケストレーター（Level 1）— CSエージェントへタスクを委譲する"""

    agent_key  = "rpo_orchestrator"
    agent_name = "RPOオーケストレーター"
    agent_desc = "【Orchestrator】RPO事業全体の指揮（CS 2チャネル）"

    sub_agents = ["CS（社員）", "CS（業務委託）"]

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task[:60]}")

        _, employment = _route_task(task)
        logger.info(f"[{self.agent_name}] ルーティング → CS employment={employment}")

        from agents._experimental.rpo.cs.agent import RpoCsAgent  # noqa: PLC0415
        agent = RpoCsAgent(employment=employment)

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
    task = sys.argv[1] if len(sys.argv) > 1 else "クライアントへの週次採用レポートを作成してください"
    print(RpoOrchestrator().run(task))
