#!/usr/bin/env python3
"""
人事オーケストレーター
canonical_id: hr_dept_orchestrator
layer: 人事
level: Level 1（対話型）

責務:
  人事部門全体を統括。社員採用 / 業務委託採用 / インターン採用
  の各サブエージェントへタスクを委譲する。

利用API: Claude / Notion / Slack
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
    タスク内容から採用チャネルを判定する。

    Returns:
        channel: "employee" | "contractor" | "intern"
    """
    res = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "人事採用タスクをチャネル分類してください。\n"
            "出力: channel=employee|contractor|intern\n"
            "employee=正社員 / contractor=業務委託 / intern=インターン"
        ),
        messages=[{"role": "user", "content": task}],
    )
    text = res.content[0].text.strip()
    if "channel=contractor" in text:
        return "contractor"
    if "channel=intern" in text:
        return "intern"
    return "employee"


class HrDeptOrchestrator:
    """人事部門オーケストレーター（Level 1）— 採用3チャネルへ委譲する"""

    agent_key  = "hr_dept_orchestrator"
    agent_name = "人事オーケストレーター"
    agent_desc = "【Orchestrator】人事部門全体を統括（正社員/業務委託/インターン採用）"

    sub_agents = ["社員採用", "業務委託採用", "インターン採用"]

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task[:60]}")

        channel = _route_task(task)
        logger.info(f"[{self.agent_name}] ルーティング → channel={channel}")

        if channel == "contractor":
            from agents._experimental.hr_dept.contractor_hiring.agent import ContractorHiringAgent  # noqa: PLC0415
            agent = ContractorHiringAgent()
        elif channel == "intern":
            from agents._experimental.hr_dept.intern_hiring.agent import InternHiringAgent  # noqa: PLC0415
            agent = InternHiringAgent()
        else:
            from agents._experimental.hr_dept.employee_hiring.agent import EmployeeHiringAgent  # noqa: PLC0415
            agent = EmployeeHiringAgent()

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
    task = sys.argv[1] if len(sys.argv) > 1 else "エンジニア正社員の求人票を作成してください"
    print(HrDeptOrchestrator().run(task))
