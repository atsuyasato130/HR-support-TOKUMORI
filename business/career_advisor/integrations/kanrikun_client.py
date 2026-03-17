#!/usr/bin/env python3
"""
採用一括かんりくん API クライアント

認証:
  POST /auth/v1.0/token/get  → access_token（有効期限1時間）
  ヘッダー: X-KANRIKUN-TOKEN

新卒エンドポイント:
  POST /new-graduate/v1.0/student/get  → 学生一覧

レート制限: 1,000回/時
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests  # type: ignore

KANRIKUN_BASE = "https://api.career-cloud.asia"
AUTH_ENDPOINT = f"{KANRIKUN_BASE}/auth/v1.0/token/get"
STUDENT_ENDPOINT = f"{KANRIKUN_BASE}/new-graduate/v1.0/student/get"

# 同期時にデフォルトで取得するフィールド
DEFAULT_FIELDS: List[str] = [
    "id",
    "sei_kanji", "mei_kanji",
    "sei_kana", "mei_kana",
    "pc_email", "mobile_email",
    "mobile_number",
    "status",
    "school_name",
    "entry_date",
    "ef_items",      # カスタム項目（推薦先企業情報など）
]

# かんりくん選考ステータスコード
STATUS_LABELS: Dict[int, str] = {
    1: "書類選考",
    2: "選考中",
    3: "内定",
    4: "内定承諾",
    5: "選考辞退",
    6: "承諾辞退",
    7: "内定辞退",
    8: "不採用",
}


class KanrikunAuthError(Exception):
    pass


class KanrikunApiError(Exception):
    pass


class KanrikunClient:
    """採用一括かんりくん API クライアント"""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expires: float = 0.0

    def _ensure_token(self) -> str:
        """トークンを取得（有効期限60秒前に再取得）"""
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        resp = requests.post(
            AUTH_ENDPOINT,
            json={"client_id": self.client_id, "client_secret": self.client_secret},
            timeout=30,
        )
        if resp.status_code == 401:
            raise KanrikunAuthError("CLIENT_ID / CLIENT_SECRET が無効です")
        if not resp.ok:
            raise KanrikunApiError(f"認証エラー: {resp.status_code} {resp.text[:200]}")

        data = resp.json()
        self._token = data["access_token"]
        # expire_in はUNIXタイムスタンプ（秒）
        self._token_expires = float(data["expire_in"])
        return self._token

    def get_students(
        self,
        search: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        page: int = 1,
        size: int = 100,
    ) -> Dict[str, Any]:
        """学生情報を1ページ分取得

        Args:
            search: 検索条件 {status: 1-8, name: str, email: str, entry_date: {start, end}, ...}
            fields: 取得フィールドのリスト（None でデフォルト）
            page:   ページ番号（1始まり）
            size:   1ページあたりの件数（最大100）

        Returns:
            {"total": N, "students": [...]}
        """
        token = self._ensure_token()
        body: Dict[str, Any] = {"page": page, "size": min(size, 100)}
        if search:
            body["search"] = search
        body["request"] = fields or DEFAULT_FIELDS

        resp = requests.post(
            STUDENT_ENDPOINT,
            headers={
                "X-KANRIKUN-TOKEN": token,
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )
        if resp.status_code == 429:
            raise KanrikunApiError("レートリミット超過（1時間1,000回）")
        if not resp.ok:
            raise KanrikunApiError(f"学生取得エラー: {resp.status_code} {resp.text[:200]}")

        return resp.json()

    def get_all_students(
        self,
        search: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """全学生をページネーションで全件取得"""
        all_students: List[Dict[str, Any]] = []
        page = 1

        while True:
            data = self.get_students(search=search, fields=fields, page=page, size=100)
            students = data.get("students", [])
            all_students.extend(students)

            total = int(data.get("total", 0))
            if not students or len(all_students) >= total:
                break
            page += 1

        return all_students

    def get_students_by_statuses(
        self,
        statuses: List[int],
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """複数ステータスを指定して学生を取得（ステータスごとにAPIコール）"""
        results: List[Dict[str, Any]] = []
        for status_code in statuses:
            students = self.get_all_students(
                search={"status": status_code},
                fields=fields,
            )
            results.extend(students)
        return results
