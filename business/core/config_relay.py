"""
business/core/config_relay.py
TOKUMO OS v2 — 動的設定リレークラス

Supabase の system_config テーブルから設定値を読み書きする薄いラッパー。
key → jsonb の {"value": <実際の値>} 形式で保存する。

使用例:
    from business.core.config_relay import ConfigRelay

    cfg = ConfigRelay()
    max_items = cfg.get("sf_sync_max_items", default=2000)  # → 2000
    cfg.set("default_grad_year", "2026")
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _get_supabase_admin():
    """Supabase admin クライアントを取得する。"""
    from supabase import create_client  # type: ignore

    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定です")
    return create_client(url, key)


class ConfigRelay:
    """
    Supabase system_config テーブルへの薄いラッパー。

    - get(key)         : 設定値を取得。キー不在時は default を返す。
    - set(key, value)  : 設定値を保存。
    - get_all()        : 全設定を {key: value} dict で返す。
    """

    def __init__(self):
        self._sb = _get_supabase_admin()

    # ── 読み取り ────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """
        指定キーの設定値を返す。キーが存在しない場合は default を返す。

        Args:
            key: 設定キー (例: "sf_sync_max_items")
            default: キー不在・取得失敗時のデフォルト値

        Returns:
            設定値。失敗時は default。
        """
        try:
            res = (
                self._sb.table("system_config")
                .select("value")
                .eq("key", key)
                .maybe_single()
                .execute()
            )
            if res.data:
                return res.data.get("value", {}).get("value", default)
            return default
        except Exception as e:
            logger.warning(f"[ConfigRelay] get({key!r}) failed: {e}")
            return default

    def get_all(self) -> dict[str, Any]:
        """
        全設定を {key: value} の dict で返す。

        Returns:
            設定 dict。取得失敗時は {}。
        """
        try:
            res = self._sb.table("system_config").select("key,value").execute()
            return {
                row["key"]: row["value"].get("value")
                for row in (res.data or [])
            }
        except Exception as e:
            logger.error(f"[ConfigRelay] get_all failed: {e}")
            return {}

    # ── 書き込み ────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> bool:
        """
        設定値を保存する（upsert）。

        Args:
            key: 設定キー
            value: 保存する値（JSON シリアライズ可能な型）

        Returns:
            成功時 True、失敗時 False。
        """
        try:
            self._sb.table("system_config").upsert(
                {"key": key, "value": {"value": value}},
                on_conflict="key",
            ).execute()
            logger.debug(f"[ConfigRelay] set({key!r}) = {value!r}")
            return True
        except Exception as e:
            logger.error(f"[ConfigRelay] set({key!r}) failed: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        設定キーを削除する。

        Returns:
            成功時 True。
        """
        try:
            self._sb.table("system_config").delete().eq("key", key).execute()
            return True
        except Exception as e:
            logger.error(f"[ConfigRelay] delete({key!r}) failed: {e}")
            return False
