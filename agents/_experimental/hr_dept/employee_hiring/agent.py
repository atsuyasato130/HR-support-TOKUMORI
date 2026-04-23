#!/usr/bin/env python3
"""
社員採用エージェント
canonical_id: hr_dept_employee_hiring
layer: 人事
level: Level 1（対話型）

責務:
  正社員採用プロセス全体を支援。
  求人票作成 / 書類選考 / 面接調整 / 内定通知 を
  Claude / Salesforce / Notion を通じて自動化する。

利用API: Claude / Salesforce / Notion
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


class EmployeeHiringAgent:
    agent_key  = "hr_dept_employee_hiring"
    agent_name = "社員採用"
    agent_desc = "正社員採用プロセス全体（求人票〜内定）"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError("社員採用エージェント未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    agent = EmployeeHiringAgent()
    result = agent.run(sys.argv[1] if len(sys.argv) > 1 else "社員採用業務を開始してください")
    print(result)
