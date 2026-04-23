#!/usr/bin/env python3
"""
state_io.py — State ファイル読み書き統一インターフェース

Micro-Workers 間の Stateless Handover を支える薄いラッパー。
StateManager（career_advisor/state/state_manager.py）の上位互換 API として
全 Worker から同じインターフェースで state/ ファイルを操作する。

## 設計原則
  - atomic write（tempfile → os.replace）で書き込み中クラッシュを防ぐ
  - 読み込み失敗時は空リスト [] を返す（None を返さない）
  - パスは CAREER_ADVISOR_DIR 環境変数 または デフォルト位置から解決

## 使い方
  from business.lib.state_io import read_state, write_state, append_state

  queue = read_state("watcher_queue")          # → list[dict]
  write_state("parser_queue", records)         # → None (atomic)
  append_state("executor_results", new_item)   # → None (既存に追記)
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── state ディレクトリ解決 ────────────────────────────────────────────

def _state_dir() -> Path:
    """state/ ディレクトリのパスを返す。"""
    env = os.environ.get("CAREER_ADVISOR_DIR")
    if env:
        d = Path(env) / "state"
    else:
        # business/lib/ → business/ → career_advisor/state/
        d = Path(__file__).parent.parent / "career_advisor" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _state_path(name: str) -> Path:
    """'watcher_queue' → '/path/to/state/watcher_queue.json'"""
    if not name.endswith(".json"):
        name = name + ".json"
    return _state_dir() / name


# ── 読み書き API ──────────────────────────────────────────────────────

def read_state(name: str) -> list[dict[str, Any]]:
    """
    state ファイルを読み込む。

    Args:
        name: ファイル名（拡張子不要。例: "watcher_queue"）

    Returns:
        list[dict]。ファイル不在・空・パースエラーは [] を返す。
    """
    path = _state_path(name)
    if not path.exists():
        logger.debug("state ファイルなし: %s", path)
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("state 読み込みエラー (%s): %s", path.name, e)
        return []


def write_state(name: str, data: list[dict[str, Any]]) -> None:
    """
    state ファイルをアトミック書き込みする（tempfile → os.replace）。

    Args:
        name: ファイル名（拡張子不要）
        data: 書き込むリスト
    """
    path = _state_path(name)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        logger.debug("state 書き込み完了: %s (%d 件)", path.name, len(data))
    except OSError as e:
        logger.error("state 書き込みエラー (%s): %s", path.name, e)
        raise


def append_state(name: str, item: dict[str, Any]) -> None:
    """
    既存の state ファイルに 1 件追記する。

    Args:
        name: ファイル名（拡張子不要）
        item: 追記する辞書
    """
    existing = read_state(name)
    existing.append(item)
    write_state(name, existing)


def clear_state(name: str) -> None:
    """state ファイルを空リストで上書きする（キュークリア）。"""
    write_state(name, [])


def state_exists(name: str) -> bool:
    """state ファイルが存在し、かつ空でないか確認する。"""
    path = _state_path(name)
    if not path.exists():
        return False
    data = read_state(name)
    return len(data) > 0
