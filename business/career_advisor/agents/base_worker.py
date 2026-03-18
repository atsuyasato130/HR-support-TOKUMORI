#!/usr/bin/env python3
"""
BaseWorker — Micro-Workers アーキテクチャの基底クラス

## 4ロール設計

  WATCHER  (哨戒兵): 外部変更を検知し、IDのみをステートに書き込む
  PARSER   (選別兵): 生データから最小限フィールドを抽出し、コンパクトJSONを出力
  PROCESSOR(策士兵): 抽出データをマッピング・推論し、実行命令を生成
  EXECUTOR (突撃兵): 命令を受け取りAPI書き込みのみを行う（ロジックなし）

## 原則

  - エージェント間で生テキストを直接受け渡さない
  - 入出力は business/career_advisor/state/ 配下のステートファイルを経由する
  - LLM呼び出しは PROCESSOR に集中させる（他ロールは原則不要）

## 使い方

  class MyWatcher(BaseWorker):
      role       = WorkerRole.WATCHER
      worker_name = "notion_watcher"

      def execute(self) -> WorkerResult:
          ...
          return WorkerResult(processed=5, errors=0)
"""

from __future__ import annotations

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# プロジェクトルート: career_advisor/agents/ → career_advisor/
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# WorkerRole: 4つの専門役割
# ──────────────────────────────────────────────

class WorkerRole(str, Enum):
    """Micro-Worker の専門役割"""
    WATCHER   = "watcher"    # 哨戒兵: 変更検知のみ
    PARSER    = "parser"     # 選別兵: 最小データ抽出
    PROCESSOR = "processor"  # 策士兵: 推論・マッピング（LLM使用可）
    EXECUTOR  = "executor"   # 突撃兵: API書き込みのみ


# ──────────────────────────────────────────────
# WorkerResult: 実行結果サマリー
# ──────────────────────────────────────────────

@dataclass
class WorkerResult:
    """Worker.execute() の戻り値"""
    processed: int = 0               # 処理件数
    errors:    int = 0               # エラー件数
    skipped:   int = 0               # スキップ件数
    details:   List[Dict[str, Any]] = field(default_factory=list)  # 詳細（任意）

    @property
    def success_rate(self) -> float:
        total = self.processed + self.errors
        return self.processed / total if total > 0 else 0.0

    def __str__(self) -> str:
        return (
            f"processed={self.processed}, errors={self.errors}, "
            f"skipped={self.skipped}, success_rate={self.success_rate:.0%}"
        )


# ──────────────────────────────────────────────
# BaseWorker: 全 Worker の親クラス
# ──────────────────────────────────────────────

class BaseWorker(ABC):
    """
    すべての Micro-Worker の親クラス。

    子クラスで定義するクラス変数:
        role        (WorkerRole): このワーカーの役割
        worker_name (str)       : 識別名（ログ・ステートファイル名に使用）

    子クラスで実装するメソッド:
        execute() -> WorkerResult:
            ワーカーのメインロジック。
            入力はステートファイルから読み込み、出力もステートファイルへ書き込む。
            大きなテキストや API レスポンス生データを直接返してはならない。
    """

    role:        WorkerRole = WorkerRole.PROCESSOR  # サブクラスでオーバーライド
    worker_name: str        = "base_worker"

    def __init__(self, dry_run: bool = False) -> None:
        """
        Args:
            dry_run: True の場合、外部 API への書き込みをスキップ（確認用）
        """
        self.dry_run   = dry_run
        self._base_dir = _BASE_DIR
        self._state_dir = os.path.join(_BASE_DIR, "state")
        os.makedirs(self._state_dir, exist_ok=True)

        self._logger = logging.getLogger(f"worker.{self.role.value}.{self.worker_name}")

    @abstractmethod
    def execute(self) -> WorkerResult:
        """
        ワーカーのメインロジック（子クラスで必ず実装）。

        設計原則:
          - WATCHER:   外部APIをポーリングし、変更IDをステートに書き込む
          - PARSER:    ステートからIDを読み、最小限フィールドを抽出してステートへ書く
          - PROCESSOR: ステートから抽出データを読み、実行命令を生成してステートへ書く
          - EXECUTOR:  ステートから命令を読み、外部APIへ書き込み、結果を記録する

        Returns:
            WorkerResult: 処理件数・エラー件数のサマリー
        """
        ...

    def state_path(self, filename: str) -> str:
        """state/ 配下のファイルパスを返す"""
        return os.path.join(self._state_dir, filename)

    def base_dir(self) -> str:
        """career_advisor/ のルートパスを返す"""
        return self._base_dir

    # ── ロールバリデーション ─────────────────────

    def _assert_role(self, expected: WorkerRole) -> None:
        """このワーカーが期待するロールか検証する（開発時チェック用）"""
        if self.role != expected:
            raise TypeError(
                f"{self.__class__.__name__} は {self.role.value} ですが、"
                f"{expected.value} として使われています。"
            )
