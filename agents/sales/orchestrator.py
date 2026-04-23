#!/usr/bin/env python3
"""
Salesオーケストレーター
canonical_id: sales_orchestrator
layer: Sales
level: Level 1（対話型）

責務:
  Sales事業を統括。案件管理・提案書生成・フォローアップを
  Claude / Salesforce / Slack を通じて自動化する。

利用API: Claude / Salesforce / Slack
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


def _route_task(task: str) -> tuple[str, str]:
    """
    タスク内容からチーム（is/fs）と雇用形態（seishain/gyomu）を判定する。

    Returns:
        (team, employment): team="is"|"fs", employment="seishain"|"gyomu"
    """
    res = _get_client().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        system=(
            "営業タスクを分類してください。\n"
            "出力: team=is|fs employment=seishain|gyomu\n"
            "is=リード・アポ・ログ系 / fs=提案書・商談・契約系"
        ),
        messages=[{"role": "user", "content": task}],
    )
    text = res.content[0].text.strip()
    team = "fs" if "team=fs" in text else "is"
    employment = "gyomu" if "employment=gyomu" in text else "seishain"
    return team, employment


class SalesOrchestrator:
    """Sales事業オーケストレーター（Level 1）— IS/FSへタスクを委譲する"""

    agent_key  = "sales_orchestrator"
    agent_name = "Salesオーケストレーター"
    agent_desc = "【Orchestrator】Sales事業全体を統括（IS/FS 2チャネル）"

    # サブエージェント定義（empire_os.py の status 表示用）
    sub_agents = [
        "IS（社員）", "IS（業務委託）",
        "FS（社員）", "FS（業務委託）",
    ]

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task[:60]}")

        team, employment = _route_task(task)
        logger.info(f"[{self.agent_name}] ルーティング → team={team}, employment={employment}")

        if team == "is":
            # "is" はPython予約語のため importlib で動的ロード
            import importlib.util as _ilu
            _spec = _ilu.spec_from_file_location(
                "sales_is_agent",
                _ROOT / "agents" / "sales" / "is" / "agent.py",
            )
            _mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            agent = _mod.IsAgent(employment=employment)
        else:
            from agents.sales.fs.agent import FsAgent  # noqa: PLC0415
            agent = FsAgent(employment=employment)

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
    task = sys.argv[1] if len(sys.argv) > 1 else "新規リードへのアポイント依頼メールを作成してください"
    print(SalesOrchestrator().run(task))
