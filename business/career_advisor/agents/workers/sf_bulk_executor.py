#!/usr/bin/env python3
"""
SFBulkExecutor — EXECUTOR ロール

## 役割（突撃兵）
processor_queue から SF 更新命令を読み込み、Salesforce API に書き込む。
ロジックを持たない。判断は PROCESSOR が完了済み。
requires_manual=true のレコードはスキップして警告ログに記録。

## 入力（state/processor_queue.json）
[
  {
    "sf_account_id" : "001xx...",
    "sf_name"       : "会社名",
    "update_fields" : {"SelectionFlow__c": "...", ...},
    "requires_manual": false,
    "skip_reason"   : ""
  }
]

## 出力（state/executor_results.json）
[
  {
    "sf_account_id": "001xx...",
    "sf_name"      : "会社名",
    "success"      : true,
    "error_msg"    : "",
    "timestamp"    : "2026-03-18T12:00:00"
  }
]

## 使い方
  python3 agents/workers/sf_bulk_executor.py
  python3 agents/workers/sf_bulk_executor.py --dry-run

  # 全件同期パイプラインを一括実行
  python3 agents/workers/sf_bulk_executor.py --run-pipeline --full-scan
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

_AGENTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASE_DIR   = os.path.dirname(_AGENTS_DIR)
sys.path.insert(0, _BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

from agents.base_worker import BaseWorker, WorkerResult, WorkerRole
from state.state_manager import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_BASE_DIR, "logs", "sf_bulk_executor.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker.executor.sf_bulk")


class SFBulkExecutor(BaseWorker):
    """
    EXECUTOR: processor_queue の命令を受け取り、SF API に書き込む。
    ビジネスロジックは持たない。受け取った命令を忠実に実行するだけ。
    """

    role        = WorkerRole.EXECUTOR
    worker_name = "sf_bulk_executor"

    def __init__(self, dry_run: bool = False) -> None:
        super().__init__(dry_run=dry_run)
        self._state = StateManager(self.state_path(""))
        self._sf    = None  # 遅延初期化

    def execute(self) -> WorkerResult:
        """
        processor_queue を読み込み、各命令を SF に書き込む。
        """
        queue = self._state.read_queue("processor_queue")
        if not queue:
            logger.info("[Executor] processor_queue が空です。スキップ。")
            return WorkerResult(processed=0)

        logger.info("[Executor] %d件の更新命令を実行開始", len(queue))

        if not self.dry_run:
            self._sf = self._init_sf()
            if not self._sf:
                logger.error("[Executor] SF接続失敗。中断します。")
                return WorkerResult(errors=len(queue))

        results: List[Dict[str, Any]] = []
        processed = 0
        errors    = 0
        skipped   = 0

        for item in queue:
            sf_id          = item.get("sf_account_id", "")
            sf_name        = item.get("sf_name", "unknown")
            update_fields  = item.get("update_fields", {})
            requires_manual= item.get("requires_manual", False)
            skip_reason    = item.get("skip_reason", "")

            timestamp = datetime.utcnow().isoformat()

            # requires_manual=True のレコードはスキップ
            if requires_manual:
                logger.warning("[Executor] 手動対応が必要: %s → %s", sf_name, skip_reason)
                results.append({
                    "sf_account_id": sf_id,
                    "sf_name"      : sf_name,
                    "success"      : False,
                    "error_msg"    : f"[MANUAL] {skip_reason}",
                    "timestamp"    : timestamp,
                })
                skipped += 1
                continue

            if not sf_id:
                logger.error("[Executor] sf_account_id が空: %s", sf_name)
                results.append({
                    "sf_account_id": "",
                    "sf_name"      : sf_name,
                    "success"      : False,
                    "error_msg"    : "sf_account_id が空",
                    "timestamp"    : timestamp,
                })
                errors += 1
                continue

            if not update_fields:
                logger.info("[Executor] 更新フィールドなし（スキップ）: %s", sf_name)
                skipped += 1
                continue

            # SF 更新実行
            success  = True
            error_msg = ""

            if not self.dry_run:
                success, error_msg = self._update_sf_record(sf_id, sf_name, update_fields)
            else:
                logger.info(
                    "[Executor] [DRY-RUN] %s (%s): %d fields → %s",
                    sf_name, sf_id, len(update_fields), list(update_fields.keys()),
                )

            results.append({
                "sf_account_id": sf_id,
                "sf_name"      : sf_name,
                "success"      : success,
                "error_msg"    : error_msg,
                "timestamp"    : timestamp,
            })

            if success:
                processed += 1
                logger.info("[Executor] ✓ 更新成功: %s (%s)", sf_name, sf_id)
            else:
                errors += 1

        # 結果を保存
        self._state.write_queue("executor_results", results)

        if not self.dry_run:
            # 実行済みのキューをクリア
            self._state.clear_queue("processor_queue")

        self._print_summary(results)
        return WorkerResult(processed=processed, errors=errors, skipped=skipped)

    # ── 内部メソッド ──────────────────────────

    def _init_sf(self):
        """Salesforce クライアントを初期化する"""
        try:
            from simple_salesforce import Salesforce  # type: ignore
            return Salesforce(
                username=os.environ["SF_USERNAME"],
                password=os.environ["SF_PASSWORD"],
                security_token=os.environ["SF_SECURITY_TOKEN"],
                domain=os.environ.get("SF_DOMAIN", "login"),
            )
        except Exception as exc:
            logger.error("[Executor] SF接続エラー: %s", exc)
            return None

    def _update_sf_record(
        self,
        sf_id: str,
        sf_name: str,
        update_fields: Dict[str, Any],
    ) -> tuple[bool, str]:
        """
        SF Account を更新する。

        Returns:
            (success: bool, error_msg: str)
        """
        try:
            self._sf.Account.update(sf_id, update_fields)
            return True, ""
        except Exception as exc:
            error_str = str(exc)
            logger.error("[Executor] ✗ 更新失敗: %s (%s) → %s", sf_name, sf_id, error_str)
            return False, error_str

    def _print_summary(self, results: List[Dict[str, Any]]) -> None:
        """実行結果のサマリーをログ出力"""
        total     = len(results)
        successes = sum(1 for r in results if r["success"])
        failures  = [r for r in results if not r["success"]]

        logger.info("=" * 50)
        logger.info("[Executor] 実行完了: %d/%d 成功", successes, total)

        if failures:
            logger.warning("[Executor] 失敗 / 手動対応が必要な企業:")
            for r in failures:
                logger.warning("  ✗ %s (%s): %s", r["sf_name"], r["sf_account_id"], r["error_msg"])


# ──────────────────────────────────────────────
# パイプライン一括実行
# ──────────────────────────────────────────────

def run_full_pipeline(dry_run: bool = False, full_scan: bool = False) -> None:
    """
    WATCHER → PARSER → PROCESSOR → EXECUTOR のフルパイプラインを実行する。

    Args:
        dry_run  : 外部API書き込みをスキップ
        full_scan: Notion全件スキャン（前回実行日時を無視）
    """
    from agents.workers.notion_watcher    import NotionWatcher
    from agents.workers.notion_page_parser import NotionPageParser
    from agents.workers.sf_field_mapper   import SFFieldMapper

    logger.info("=" * 50)
    logger.info("Notion→SF 同期パイプライン開始 (dry_run=%s, full_scan=%s)", dry_run, full_scan)

    # Step 1: WATCHER — 変更検知
    logger.info("[Pipeline] Step 1/4: Notion変更検知（WATCHER）")
    watcher = NotionWatcher(dry_run=dry_run, full_scan=full_scan)
    r1 = watcher.execute()
    logger.info("[Pipeline] WATCHER: %s", r1)

    if r1.processed == 0 and not dry_run:
        logger.info("[Pipeline] 変更なし → パイプライン終了")
        return

    # Step 2: PARSER — フィールド抽出
    logger.info("[Pipeline] Step 2/4: フィールド抽出（PARSER）")
    parser = NotionPageParser(dry_run=dry_run)
    r2 = parser.execute()
    logger.info("[Pipeline] PARSER: %s", r2)

    # Step 3: PROCESSOR — SFフィールドマッピング
    logger.info("[Pipeline] Step 3/4: SFフィールドマッピング（PROCESSOR）")
    mapper = SFFieldMapper(dry_run=dry_run)
    r3 = mapper.execute()
    logger.info("[Pipeline] PROCESSOR: %s", r3)

    # Step 4: EXECUTOR — SF書き込み
    logger.info("[Pipeline] Step 4/4: SF一括更新（EXECUTOR）")
    executor = SFBulkExecutor(dry_run=dry_run)
    r4 = executor.execute()
    logger.info("[Pipeline] EXECUTOR: %s", r4)

    logger.info("=" * 50)
    logger.info(
        "[Pipeline] 完了: 検知=%d, 解析=%d, マッピング=%d, 更新=%d, エラー=%d",
        r1.processed, r2.processed, r3.processed, r4.processed, r4.errors,
    )


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="SF一括更新（EXECUTOR）/ パイプライン実行")
    parser.add_argument("--dry-run",      action="store_true", help="SF書き込みをスキップ")
    parser.add_argument("--run-pipeline", action="store_true", help="全パイプラインを一括実行")
    parser.add_argument("--full-scan",    action="store_true", help="Notion全件スキャン（--run-pipelineと併用）")
    args = parser.parse_args()

    if args.run_pipeline:
        run_full_pipeline(dry_run=args.dry_run, full_scan=args.full_scan)
    else:
        executor = SFBulkExecutor(dry_run=args.dry_run)
        result   = executor.execute()
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}実行結果: {result}")


if __name__ == "__main__":
    main()
