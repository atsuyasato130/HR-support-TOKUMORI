#!/usr/bin/env python3
"""
CS（カスタマーサクセス）エージェント — RPO事業
canonical_id: rpo_cs_seishain / rpo_cs_gyomu
layer: RPO / Level 1

責務:
  RPO外部クライアントへの定例報告・採用KPI管理・
  課題提案を Salesforce / GSheets を通じて自動化する。

利用API: Claude / Salesforce / GSheets
"""
from __future__ import annotations
import logging, sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT))
from dotenv import load_dotenv
load_dotenv(_ROOT / "config" / ".env")
logger = logging.getLogger(__name__)


class RpoCsAgent:
    """RPO CS 共通クラス。雇用形態を引数で切り替える"""

    def __init__(self, employment: str = "seishain") -> None:
        assert employment in ("seishain", "gyomu"), "employment must be 'seishain' or 'gyomu'"
        self.employment = employment
        self.agent_key  = f"rpo_cs_{employment}"
        self.agent_name = f"CS（{'社員' if employment == 'seishain' else '業務委託'}）"
        self.agent_desc = "クライアント報告・採用KPI管理"

    def run(self, task: str) -> str:
        logger.info(f"[{self.agent_name}] タスク受信: {task}")
        raise NotImplementedError(f"RPO CS ({self.employment}) 未実装 — 開発中")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    emp = sys.argv[1] if len(sys.argv) > 1 else "seishain"
    print(RpoCsAgent(emp).run("CS業務"))
