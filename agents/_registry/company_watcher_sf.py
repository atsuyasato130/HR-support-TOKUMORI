"""
business/agents/company_watcher_sf.py
TOKUMO OS v2 — SF企業同期ワーカー (WATCHER ロール)

SF の Account オブジェクト（企業）の変更を検知し、
TOKUMO の companies テーブルへ差分同期する。
"""
from __future__ import annotations
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from business.core.base_worker import BaseWorker, WorkerRole, WorkerResult
from business.core.state_manager import StateManager

logger = logging.getLogger(__name__)

# SF企業Accountのカラムマッピング（SF → Supabase）
SF_TO_SUPABASE_COMPANY = {
    "Id":            "sf_account_id",
    "Name":          "name",
    "Industry":      "industry",
    "Website":       "website",
    "Description":   "description",
    "NumberOfEmployees": "employee_count",
    "SystemModstamp": "sf_system_modstamp",
}


def _get_sf_connection():
    """SF接続を取得（business/lib/api_clients.py 経由）"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from lib.api_clients import get_sf_session
    return get_sf_session()


def _get_supabase_admin():
    """Supabase admin クライアント"""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY が未設定です")
    return create_client(url, key)


class CompanyWatcherSF(BaseWorker):
    """
    SF Account（企業）を差分同期する WATCHER。
    - 最後に処理した SystemModstamp をカーソルとして StateManager に保存
    - 変更があった企業のみを upsert する（SSOT = SF）
    """

    role   = WorkerRole.WATCHER
    domain = "hr"

    RECORD_TYPE_COMPANY = "0122w000001Ry2iAAC"  # 企業 RecordType ID（環境変数で上書き可）
    BATCH_SIZE = 200

    def __init__(self):
        self.state = StateManager("hr_watcher_company_sf")
        self.record_type_id = os.environ.get(
            "SF_COMPANY_RECORD_TYPE_ID", self.RECORD_TYPE_COMPANY
        )

    def _execute(self, context: dict) -> WorkerResult:
        cursor = self.state.get_cursor()
        logger.info(f"[CompanyWatcherSF] cursor={cursor}")

        # 1. SF から企業を取得（差分）
        try:
            sf = _get_sf_connection()
            where_clause = f"RecordTypeId = '{self.record_type_id}'"
            if cursor:
                where_clause += f" AND SystemModstamp > {cursor}"

            soql = f"""
                SELECT Id, Name, Industry, Website, Description,
                       NumberOfEmployees, SystemModstamp
                FROM Account
                WHERE {where_clause}
                ORDER BY SystemModstamp ASC
                LIMIT 2000
            """
            result = sf.query(soql)
            records = result.get("records", [])
        except Exception as e:
            return WorkerResult(success=False, error=f"SF取得エラー: {e}")

        if not records:
            logger.info("[CompanyWatcherSF] 差分なし")
            return WorkerResult(success=True, data={"synced": 0})

        # 2. Supabase へ upsert
        try:
            supabase = _get_supabase_admin()
            payloads = []
            new_cursor = cursor

            for rec in records:
                payload = {}
                for sf_key, sb_key in SF_TO_SUPABASE_COMPANY.items():
                    if sf_key in rec:
                        payload[sb_key] = rec[sf_key]
                # SystemModstamp を除外（不要なカラムの混入防止）
                payload.pop("sf_system_modstamp", None)
                if rec.get("Id"):
                    payload["sf_account_id"] = rec["Id"]
                payloads.append(payload)

                # カーソル更新
                if rec.get("SystemModstamp"):
                    if not new_cursor or rec["SystemModstamp"] > new_cursor:
                        new_cursor = rec["SystemModstamp"]

            # バッチ upsert
            for i in range(0, len(payloads), self.BATCH_SIZE):
                batch = payloads[i:i + self.BATCH_SIZE]
                supabase.table("companies").upsert(
                    batch, on_conflict="sf_account_id"
                ).execute()

        except Exception as e:
            return WorkerResult(success=False, error=f"Supabase upsertエラー: {e}")

        # 3. カーソルを更新
        if new_cursor:
            self.state.set_cursor(new_cursor)

        logger.info(f"[CompanyWatcherSF] ✅ {len(records)}件同期完了")
        return WorkerResult(success=True, data={"synced": len(records), "cursor": new_cursor})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = CompanyWatcherSF()
    result = worker.run()
    print(result)
