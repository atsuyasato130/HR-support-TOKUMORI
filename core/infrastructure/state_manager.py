"""
core/state_manager.py
TOKUMO OS v2 — Supabase system_state テーブルとの同期
Worker の進捗・上限値・カーソルを永続化し再起動時に自動復帰する
"""
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _get_admin_client():
    """Supabase admin クライアントを取得（service_role key 使用）"""
    from supabase import create_client, Client
    url  = os.environ.get("SUPABASE_URL", "")
    key  = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定です")
    return create_client(url, key)


class StateManager:
    """
    worker_id をキーに system_state テーブルで状態を永続化する。

    state 構造:
      {
        "cursor":      str | None,   # 最後に処理した ID / タイムスタンプ
        "progress":    float,        # 0.0〜1.0
        "max_items":   int,          # 処理上限値
        "extra":       dict          # Worker 独自データ
      }
    """

    TABLE = "system_state"

    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self._client   = None

    @property
    def client(self):
        if self._client is None:
            self._client = _get_admin_client()
        return self._client

    # ─── 読み取り ───────────────────────────────────────────
    def load(self) -> dict:
        """DB から最新ステートを取得。存在しない場合は空 dict を返す。"""
        try:
            res = (
                self.client.table(self.TABLE)
                .select("state_data")
                .eq("worker_id", self.worker_id)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows[0].get("state_data") or {}
        except Exception as e:
            logger.warning(f"[StateManager] load failed for {self.worker_id}: {e}")
        return {}

    # ─── 書き込み ───────────────────────────────────────────
    def save(self, state: dict) -> bool:
        """ステートを upsert（insert or update）する。"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            self.client.table(self.TABLE).upsert(
                {
                    "worker_id":  self.worker_id,
                    "state_data": state,
                    "updated_at": now,
                },
                on_conflict="worker_id",
            ).execute()
            return True
        except Exception as e:
            logger.error(f"[StateManager] save failed for {self.worker_id}: {e}")
            return False

    # ─── 便利メソッド ─────────────────────────────────────
    def get_cursor(self) -> str | None:
        return self.load().get("cursor")

    def set_cursor(self, cursor: str) -> bool:
        state = self.load()
        state["cursor"] = cursor
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        return self.save(state)

    def get_progress(self) -> float:
        return float(self.load().get("progress", 0.0))

    def set_progress(self, progress: float) -> bool:
        state = self.load()
        state["progress"] = round(min(max(progress, 0.0), 1.0), 4)
        return self.save(state)

    def reset(self) -> bool:
        """ステートを初期化する。"""
        return self.save({"cursor": None, "progress": 0.0, "max_items": 0, "extra": {}})
