#!/usr/bin/env python3
"""
NotionWatcher — WATCHER ロール

## 役割（哨戒兵）
Notion企業DBを定期ポーリングし、新規・更新ページのIDのみをステートに書き込む。
LLMを介さずプログラムで差分を抽出する。大量テキストは一切後続に渡さない。

## 出力（state/watcher_queue.json）
[
  {
    "notion_page_id": "xxx-yyy-zzz",
    "name": "会社名",
    "last_edited_time": "2026-03-18T12:00:00.000Z"
  },
  ...
]

## 使い方
  # 1回のみ実行
  python3 agents/workers/notion_watcher.py --once

  # 差分のみ（前回実行以降）
  python3 agents/workers/notion_watcher.py --once --diff

  # 常駐監視（30分間隔）
  python3 agents/workers/notion_watcher.py

  # dry-run（ステートファイル書き込みスキップ）
  python3 agents/workers/notion_watcher.py --once --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# プロジェクトルート設定
_AGENTS_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASE_DIR    = os.path.dirname(_AGENTS_DIR)
_WORKERS_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _BASE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

import httpx

from agents.base_worker import BaseWorker, WorkerResult, WorkerRole
from state.state_manager import StateManager

# ── ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_BASE_DIR, "logs", "notion_watcher.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("worker.watcher.notion")

# ── 定数
NOTION_API_KEY    = os.environ.get("NOTION_API_KEY", "")
NOTION_DB_ID      = os.environ.get("NOTION_COMPANY_DB_ID", "5cdbd39197f94db7b7e275d317166bfd")
NOTION_VERSION    = "2022-06-28"
DEFAULT_INTERVAL  = 30   # 分


class NotionWatcher(BaseWorker):
    """
    WATCHER: Notion企業DBの変更を検知し、ページIDをキューに積む。

    LLM不使用。完全プログラムによる差分抽出。
    大量テキストを後続ワーカーに渡さず、IDと最小限メタデータのみを渡す。
    """

    role        = WorkerRole.WATCHER
    worker_name = "notion_watcher"

    def __init__(
        self,
        dry_run:     bool = False,
        full_scan:   bool = False,
    ) -> None:
        """
        Args:
            dry_run  : ステートファイルへの書き込みをスキップ
            full_scan: 前回実行日時を無視して全件スキャン
        """
        super().__init__(dry_run=dry_run)
        self._state   = StateManager(self.state_path(""))
        self._full    = full_scan

    def execute(self) -> WorkerResult:
        """
        Notionをポーリングし、変更があったページのIDをキューに書き込む。

        Returns:
            WorkerResult: 検知件数（detected=processed）
        """
        since = self._get_since()
        pages = self._fetch_changed_pages(since)

        if not pages:
            logger.info("[Watcher] 変更なし")
            self._state.save_last_run(self.worker_name)
            return WorkerResult(processed=0)

        # IDと最小メタデータのみを抽出（生HTMLやプロパティ全体は渡さない）
        queue_items = [
            {
                "notion_page_id" : p["id"],
                "name"           : p["name"],
                "last_edited_time": p["last_edited_time"],
            }
            for p in pages
        ]

        logger.info("[Watcher] 変更検知: %d件", len(queue_items))
        for item in queue_items:
            logger.info("  - %s (%s)", item["name"], item["notion_page_id"])

        if not self.dry_run:
            self._state.write_queue("watcher_queue", queue_items)
            self._state.save_last_run(self.worker_name)
            logger.info("[Watcher] watcher_queue.json に書き込み完了")
        else:
            logger.info("[Watcher] [DRY-RUN] 書き込みスキップ")

        return WorkerResult(processed=len(queue_items))

    # ── 内部メソッド ──────────────────────────

    def _get_since(self) -> Optional[datetime]:
        """前回実行日時を取得する。full_scan=True または初回は None を返す"""
        if self._full:
            return None
        return self._state.get_last_run(self.worker_name)

    def _fetch_changed_pages(
        self,
        since: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """
        Notion DB から変更ページを取得し、最小限メタデータのみ返す。

        since=None の場合は全件取得。
        """
        if not NOTION_API_KEY:
            logger.error("[Watcher] NOTION_API_KEY が未設定です")
            return []

        headers = {
            "Authorization"  : f"Bearer {NOTION_API_KEY}",
            "Notion-Version" : NOTION_VERSION,
            "Content-Type"   : "application/json",
        }

        payload: Dict[str, Any] = {"page_size": 100}

        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            payload["filter"] = {
                "or": [
                    {"timestamp": "last_edited_time", "last_edited_time": {"after": since_str}},
                    {"timestamp": "created_time",     "created_time":     {"after": since_str}},
                ],
            }
            payload["sorts"] = [{"timestamp": "last_edited_time", "direction": "descending"}]
            logger.info("[Watcher] %s 以降の変更を検索", since.strftime("%Y-%m-%d %H:%M"))
        else:
            logger.info("[Watcher] 全件スキャン")

        results: List[Dict[str, Any]] = []
        has_more = True
        cursor: Optional[str] = None

        with httpx.Client(timeout=30) as client:
            while has_more:
                if cursor:
                    payload["start_cursor"] = cursor

                try:
                    resp = client.post(
                        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.error("[Watcher] Notion API エラー: %s", exc)
                    break

                data     = resp.json()
                has_more = data.get("has_more", False)
                cursor   = data.get("next_cursor")

                for page in data.get("results", []):
                    name = self._extract_title(page)
                    if not name:
                        continue
                    results.append({
                        "id"              : page["id"],
                        "name"            : name,
                        "last_edited_time": page.get("last_edited_time", ""),
                    })

        logger.info("[Watcher] Notion取得完了: %d件", len(results))
        return results

    @staticmethod
    def _extract_title(page: Dict[str, Any]) -> str:
        """ページのtitleプロパティから企業名を抽出する"""
        for _key, prop in page.get("properties", {}).items():
            if prop.get("type") == "title":
                return "".join(
                    r.get("plain_text", "")
                    for r in prop.get("title", [])
                ).strip()
        return ""


# ──────────────────────────────────────────────
# CLI エントリポイント
# ──────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Notion企業DB変更監視（WATCHER）")
    parser.add_argument("--once",      action="store_true", help="1回だけ実行して終了")
    parser.add_argument("--full-scan", action="store_true", help="全件スキャン（前回実行日時を無視）")
    parser.add_argument("--dry-run",   action="store_true", help="ステートファイル書き込みをスキップ")
    parser.add_argument("--interval",  type=int, default=DEFAULT_INTERVAL, help="ポーリング間隔（分）")
    args = parser.parse_args()

    watcher = NotionWatcher(dry_run=args.dry_run, full_scan=args.full_scan)

    if args.once:
        result = watcher.execute()
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}検知結果: {result}")
    else:
        logger.info("[Watcher] 常駐監視開始: %d分間隔", args.interval)
        while True:
            try:
                watcher.execute()
            except KeyboardInterrupt:
                logger.info("[Watcher] 停止しました")
                break
            except Exception as exc:
                logger.error("[Watcher] エラー: %s", exc, exc_info=True)
            logger.info("[Watcher] 次回: %d分後", args.interval)
            time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
