"""
core/base_worker.py
TOKUMO OS v2 — 全Workerの抽象基底クラス
4ロール標準: WATCHER / PARSER / PROCESSOR / EXECUTOR
"""
from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WorkerRole(str, Enum):
    WATCHER   = "watcher"    # 哨戒: 差分検知（LLM不使用）
    PARSER    = "parser"     # 選別: データ抽出（Haiku等）
    PROCESSOR = "processor"  # 思考: 戦略判断（Sonnet等）
    EXECUTOR  = "executor"   # 実行: API実行/書き込み


class WorkerResult:
    def __init__(self, success: bool, data: Any = None, error: str | None = None):
        self.success = success
        self.data    = data
        self.error   = error

    def __repr__(self) -> str:
        return f"WorkerResult(success={self.success}, error={self.error})"


class BaseWorker(ABC):
    """
    全Workerが継承する抽象基底クラス。
    - ロール・ドメイン・バージョンをメタデータとして持つ
    - run() を唯一の実行エントリポイントとする
    - 自動リトライ・エラーハンドリングを標準装備
    """

    role: WorkerRole          # サブクラスで上書き必須
    domain: str = "hr"        # ドメイン識別子
    version: str = "1.0.0"

    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 2.0  # seconds

    def run(self, context: dict | None = None) -> WorkerResult:
        """
        外部から呼び出す唯一のエントリポイント。
        _execute() をリトライ付きで実行する。
        """
        ctx = context or {}
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"[{self.__class__.__name__}] attempt {attempt}/{self.MAX_RETRIES}")
                result = self._execute(ctx)
                if result.success:
                    logger.info(f"[{self.__class__.__name__}] ✅ success")
                    return result
                logger.warning(f"[{self.__class__.__name__}] ⚠ attempt {attempt} failed: {result.error}")
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] ❌ exception: {e}")
                result = WorkerResult(success=False, error=str(e))
            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
        return result  # type: ignore[return-value]

    @abstractmethod
    def _execute(self, context: dict) -> WorkerResult:
        """サブクラスが実装するビジネスロジック"""
        ...

    @property
    def canonical_name(self) -> str:
        """registry.json の id と対応する命名: {domain}_{role}_{class_snake}"""
        import re
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", self.__class__.__name__).lower()
        snake = snake.replace("_worker", "")
        return f"{self.domain}_{self.role.value}_{snake}"
