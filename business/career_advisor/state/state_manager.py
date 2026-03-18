#!/usr/bin/env python3
"""
StateManager — Micro-Workers 間のステートファイル管理

## 役割
Worker 間でのデータ受け渡しを安全に行うためのユーティリティ。
大量テキストではなく、IDや最小JSONのみを保存する設計。

## ステートファイル一覧

  watcher_queue.json  : WATCHER が書き込む「処理待ちNotionページID」リスト
                        [{notion_page_id, name, last_edited_time}]

  parser_queue.json   : PARSER が書き込む「抽出済みフィールド」リスト
                        [{notion_page_id, name, extracted: {field: value}}]

  processor_queue.json: PROCESSOR が書き込む「SF更新命令」リスト
                        [{sf_account_id, sf_name, update_fields: {field: value}}]

  executor_results.json: EXECUTOR が書き込む「実行結果」リスト
                        [{sf_account_id, sf_name, success, error_msg, timestamp}]

## 使い方

  sm = StateManager(state_dir="/path/to/state")
  sm.write_queue("watcher_queue", records)         # 上書き（新しいバッチ）
  sm.append_queue("parser_queue", new_record)      # 追記（逐次処理）
  records = sm.read_queue("processor_queue")       # 全件読み込み
  sm.clear_queue("watcher_queue")                  # 処理完了後のクリア
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ステートファイル定義
QUEUE_FILES = {
    "watcher_queue"   : "watcher_queue.json",
    "parser_queue"    : "parser_queue.json",
    "processor_queue" : "processor_queue.json",
    "executor_results": "executor_results.json",
}


class StateManager:
    """
    Worker 間ステートファイルの読み書きユーティリティ。

    アトミック書き込み（tempfile → rename）でファイル破損を防ぐ。
    """

    def __init__(self, state_dir: str) -> None:
        self._dir = state_dir
        os.makedirs(self._dir, exist_ok=True)

    # ── パブリックAPI ───────────────────────────

    def write_queue(self, queue_name: str, records: List[Dict[str, Any]]) -> None:
        """キューを上書き保存する（新しいバッチの書き込みに使用）"""
        path = self._path(queue_name)
        self._atomic_write(path, records)
        logger.debug("[State] 書き込み: %s (%d件)", queue_name, len(records))

    def append_to_queue(self, queue_name: str, record: Dict[str, Any]) -> None:
        """既存キューに1件追記する（逐次処理時に使用）"""
        records = self.read_queue(queue_name)
        records.append(record)
        self.write_queue(queue_name, records)

    def read_queue(self, queue_name: str) -> List[Dict[str, Any]]:
        """キューを全件読み込む。ファイルが存在しない場合は空リストを返す"""
        path = self._path(queue_name)
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("[State] 読み込みエラー: %s → %s", queue_name, exc)
            return []

    def clear_queue(self, queue_name: str) -> None:
        """キューをクリアする（処理完了後に呼ぶ）"""
        self.write_queue(queue_name, [])
        logger.debug("[State] クリア: %s", queue_name)

    def queue_size(self, queue_name: str) -> int:
        """キューのアイテム数を返す"""
        return len(self.read_queue(queue_name))

    def get_last_run(self, worker_name: str) -> Optional[datetime]:
        """ワーカーの前回実行日時を取得する"""
        meta = self._read_meta()
        ts = meta.get(f"{worker_name}.last_run")
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except ValueError:
                pass
        return None

    def save_last_run(self, worker_name: str, dt: Optional[datetime] = None) -> None:
        """ワーカーの実行日時を記録する（省略時は現在時刻）"""
        meta = self._read_meta()
        meta[f"{worker_name}.last_run"] = (dt or datetime.utcnow()).isoformat()
        self._atomic_write(self._meta_path(), meta)

    def snapshot(self) -> Dict[str, Any]:
        """全キューの件数サマリーを返す（デバッグ用）"""
        return {
            name: self.queue_size(name)
            for name in QUEUE_FILES
        }

    # ── 内部メソッド ───────────────────────────

    def _path(self, queue_name: str) -> str:
        filename = QUEUE_FILES.get(queue_name, f"{queue_name}.json")
        return os.path.join(self._dir, filename)

    def _meta_path(self) -> str:
        return os.path.join(self._dir, "_meta.json")

    def _read_meta(self) -> Dict[str, Any]:
        path = self._meta_path()
        if not os.path.exists(path):
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _atomic_write(path: str, data: Any) -> None:
        """tempfile経由でアトミック書き込みを行う（書き込み中の破損防止）"""
        dir_name = os.path.dirname(path)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=dir_name,
                delete=False,
                suffix=".tmp",
            ) as tmp:
                json.dump(data, tmp, ensure_ascii=False, indent=2)
                tmp_path = tmp.name
            os.replace(tmp_path, path)
        except OSError as exc:
            logger.error("[State] 書き込み失敗: %s → %s", path, exc)
            raise
