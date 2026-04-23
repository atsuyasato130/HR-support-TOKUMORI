"""
core/auth/roles.py
TOKUMO OS v2 — RBAC ロール定義
ADMIN (大将) / EDITOR (メンバー) / VIEWER の権限マトリクス
"""
from __future__ import annotations
from enum import Enum
from typing import FrozenSet


class Role(str, Enum):
    ADMIN  = "owner"    # 大将: 全機能
    EDITOR = "staff"    # メンバー: 閲覧 + 編集（private 機能除外）
    VIEWER = "viewer"   # 閲覧のみ


# ─── 権限セット ───────────────────────────────────────────────
PERMISSIONS: dict[Role, FrozenSet[str]] = {
    Role.ADMIN: frozenset([
        "students:read", "students:write", "students:delete",
        "selections:read", "selections:write", "selections:delete",
        "companies:read", "companies:write",
        "sf:sync", "sf:bulk_import",
        "dashboard:read", "dashboard:kpi",
        "agents:run", "agents:manage",
        "private:read", "private:write",          # 大将のみ
        "settings:manage",
    ]),
    Role.EDITOR: frozenset([
        "students:read", "students:write",
        "selections:read", "selections:write",
        "companies:read", "companies:write",
        "sf:sync",
        "dashboard:read", "dashboard:kpi",
        "agents:run",
    ]),
    Role.VIEWER: frozenset([
        "students:read",
        "selections:read",
        "companies:read",
        "dashboard:read",
    ]),
}


def has_permission(role: str, permission: str) -> bool:
    """
    ロール文字列と権限文字列を受け取り、許可されているか返す。
    不明なロールは VIEWER として扱う。
    """
    try:
        r = Role(role)
    except ValueError:
        r = Role.VIEWER
    return permission in PERMISSIONS.get(r, frozenset())


def is_private_allowed(role: str) -> bool:
    """private/ 関連機能へのアクセス可否（ADMIN のみ）"""
    return has_permission(role, "private:read")
