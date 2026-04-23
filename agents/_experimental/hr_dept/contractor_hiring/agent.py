#!/usr/bin/env python3
"""
業務委託採用エージェント
canonical_id: hr_dept_contractor_hiring
layer: 人事
level: Level 1（対話型）

責務:
  業務委託・フリーランス採用を支援。
  要件定義 / 候補者スクリーニング / 契約書ドラフトを
  Claude / Notion を通じて自動化する。

利用API: Claude / Notion
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / "config" / ".env")
logger = logging.getLogger(__name__)


class ContractorHiringAgent:
    agent_key  = "hr_dept_contractor_hiring"
    agent_name = "業務委託採用"
    agent_desc = "業務委託・フリーランス採用（要件定義〜契約）"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError("業務委託採用エージェント未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    agent = ContractorHiringAgent()
    result = agent.run(sys.argv[1] if len(sys.argv) > 1 else "業務委託採用業務を開始してください")
    print(result)
