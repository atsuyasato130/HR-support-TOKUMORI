#!/usr/bin/env python3
"""
インターン生採用エージェント
canonical_id: hr_dept_intern_hiring
layer: 人事
level: Level 1（対話型）

責務:
  インターン採用・研修プログラム管理。
  募集 / 選考 / オンボーディング / 評価レポートを
  Claude / Notion / Slack を通じて自動化する。

利用API: Claude / Notion / Slack
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


class InternHiringAgent:
    agent_key  = "hr_dept_intern_hiring"
    agent_name = "インターン生採用"
    agent_desc = "インターン採用・研修プログラム管理（募集〜評価）"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError("インターン生採用エージェント未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    agent = InternHiringAgent()
    result = agent.run(sys.argv[1] if len(sys.argv) > 1 else "インターン採用業務を開始してください")
    print(result)
