#!/usr/bin/env python3
"""
ReviewWatcher — Pythonファイル変更を監視して自動レビューを実行する

対象ディレクトリ内の .py ファイルが保存されると、3秒のデバウンス後に
ReviewAgent を呼び出してレビューを実行する。

使い方:
  python3 watcher.py          # デフォルトディレクトリを監視
  python3 watcher.py --once   # 直近1時間の変更ファイルを1回レビューして終了
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
from pathlib import Path

# プロジェクトルート設定
_WATCHER_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR    = str(Path(_WATCHER_DIR).parents[2])  # ai-empire/

sys.path.insert(0, _WATCHER_DIR)
sys.path.insert(0, _ROOT_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT_DIR, "agents/hr_support/config/.env"))

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

import agent as review_agent

# ── ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(_ROOT_DIR, "logs", "review_watcher.log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("quality.review.watcher")

# ── 監視対象ディレクトリ（ai-empire/ 配下の主要エージェント）
_WATCH_DIRS = [
    os.path.join(_ROOT_DIR, "agents", "hr_support"),
    os.path.join(_ROOT_DIR, "agents", "quality"),
    os.path.join(_ROOT_DIR, "agents", "rpo"),
    os.path.join(_ROOT_DIR, "agents", "sales"),
    os.path.join(_ROOT_DIR, "utils"),
]

# デバウンス時間（秒）: 連続保存でレビューが多重発火しないよう待機
_DEBOUNCE_SEC = 5

# 同一ファイルの最小レビュー間隔（秒）: 頻繁な保存でAPIを叩きすぎない
_MIN_REVIEW_INTERVAL = 120


class _DebounceReviewHandler(FileSystemEventHandler):
    """ファイル変更を検知してデバウンス後にレビューを実行するハンドラ。"""

    def __init__(self) -> None:
        super().__init__()
        self._timers: dict[str, threading.Timer] = {}
        self._last_reviewed: dict[str, float] = {}
        self._lock = threading.Lock()

    def on_modified(self, event: FileModifiedEvent) -> None:
        self._handle(event)

    def on_created(self, event: FileCreatedEvent) -> None:
        self._handle(event)

    def _handle(self, event) -> None:
        if event.is_directory:
            return
        path = event.src_path
        if not path.endswith(".py"):
            return
        if review_agent.should_skip(path):
            return

        with self._lock:
            # 既存タイマーをリセット（デバウンス）
            if path in self._timers:
                self._timers[path].cancel()
            timer = threading.Timer(_DEBOUNCE_SEC, self._run_review, args=(path,))
            self._timers[path] = timer
            timer.start()

    def _run_review(self, path: str) -> None:
        """デバウンス後に呼ばれる実際のレビュー実行。"""
        with self._lock:
            self._timers.pop(path, None)
            last = self._last_reviewed.get(path, 0)
            if time.time() - last < _MIN_REVIEW_INTERVAL:
                logger.info("レビュースキップ（インターバル制限）: %s", os.path.relpath(path, _ROOT_DIR))
                return
            self._last_reviewed[path] = time.time()

        logger.info("変更検知 → レビュー開始: %s", os.path.relpath(path, _ROOT_DIR))
        try:
            review_agent.run(path)
        except Exception as e:
            logger.exception("レビュー実行エラー: %s — %s", path, e)


def _review_recent_files(hours: int = 1) -> None:
    """直近N時間以内に変更されたPythonファイルをレビューする（--once用）。"""
    since = time.time() - hours * 3600
    targets = []

    for watch_dir in _WATCH_DIRS:
        if not os.path.exists(watch_dir):
            continue
        for root, dirs, files in os.walk(watch_dir):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if not review_agent.should_skip(d)]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                if review_agent.should_skip(fpath):
                    continue
                if os.path.getmtime(fpath) >= since:
                    targets.append(fpath)

    if not targets:
        logger.info("直近%d時間に変更されたPythonファイルなし", hours)
        return

    logger.info("対象ファイル: %d件", len(targets))
    for i, fpath in enumerate(targets):
        if i > 0:
            time.sleep(3)  # APIレート制限回避
        review_agent.run(fpath)


def start_watching() -> None:
    """ファイル監視を開始する（常駐）。"""
    handler  = _DebounceReviewHandler()
    observer = Observer()

    active_dirs = []
    for watch_dir in _WATCH_DIRS:
        if os.path.exists(watch_dir):
            observer.schedule(handler, watch_dir, recursive=True)
            active_dirs.append(os.path.relpath(watch_dir, _ROOT_DIR))
        else:
            logger.warning("監視対象ディレクトリが存在しない: %s", watch_dir)

    observer.start()
    logger.info("ReviewWatcher 起動 — 監視対象: %s", ", ".join(active_dirs))
    logger.info("デバウンス: %ds | 最小レビュー間隔: %ds", _DEBOUNCE_SEC, _MIN_REVIEW_INTERVAL)

    try:
        while True:
            time.sleep(10)
            if not observer.is_alive():
                logger.error("Observer が停止しました。再起動します。")
                observer.start()
    except KeyboardInterrupt:
        logger.info("ReviewWatcher 停止")
    finally:
        observer.stop()
        observer.join()


def main() -> None:
    parser = argparse.ArgumentParser(description="ReviewWatcher: .pyファイル変更を監視して自動レビュー")
    parser.add_argument("--once", action="store_true", help="直近1時間の変更ファイルをレビューして終了")
    parser.add_argument("--hours", type=int, default=1, help="--once 時の対象時間（デフォルト: 1時間）")
    args = parser.parse_args()

    if args.once:
        _review_recent_files(hours=args.hours)
    else:
        start_watching()


if __name__ == "__main__":
    main()
