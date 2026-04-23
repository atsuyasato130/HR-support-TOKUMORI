#!/usr/bin/env python3
"""
経理エージェント
canonical_id: mgmt_accounting
layer: 経営管理
level: Level 1（対話型）

責務:
  月次P&L集計 / 経費申請処理 / 請求書管理 を
  Claude / GSheets を通じて自動化する。

利用API: Claude / GSheets
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


class AccountingAgent:
    agent_key  = "mgmt_accounting"
    agent_name = "経理"
    agent_desc = "月次P&L集計・経費申請・請求書管理"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError("経理エージェント未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    agent = AccountingAgent()
    result = agent.run(sys.argv[1] if len(sys.argv) > 1 else "経理業務を開始してください")
    print(result)
