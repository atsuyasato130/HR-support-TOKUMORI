#!/usr/bin/env python3
"""
IS（インサイドセールス）エージェント — Sales事業
canonical_id: sales_is_seishain / sales_is_gyomu
layer: Sales / Level 1

責務:
  リード育成・アポイント管理・商談ログ記録を
  Salesforce / Slack を通じて自動化する。

利用API: Claude / Salesforce / Slack
"""
from __future__ import annotations
import logging, sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
from dotenv import load_dotenv
load_dotenv(_ROOT / "config" / ".env")
logger = logging.getLogger(__name__)


class IsAgent:
    def __init__(self, employment: str = "seishain") -> None:
        assert employment in ("seishain", "gyomu")
        self.employment = employment
        self.agent_key  = f"sales_is_{employment}"
        self.agent_name = f"IS（{'社員' if employment == 'seishain' else '業務委託'}）"
        self.agent_desc = "リード育成・アポイント管理・商談ログ記録"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError(f"IS ({self.employment}) 未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    emp = sys.argv[1] if len(sys.argv) > 1 else "seishain"
    print(IsAgent(emp).run("IS業務"))
