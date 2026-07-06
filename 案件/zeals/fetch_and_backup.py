"""ZEALS DR/スカウト管理シート 02_マスターの生データを正確にローカル退避する。
移行前バックアップ(Step0.2)。読み取り専用・書き込みは一切行わない。
"""
import json
import logging
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
OUT_PATH = os.path.expanduser("~/Claude AI/scratch_zeals/raw_master_backup_20260703.json")

HEADER = [
    "媒体", "候補者ID", "流入チャネル", "担当者", "候補者名", "プロフィールURL",
    "職種", "雇用形態希望", "意欲ステータス", "接点ステータス",
    "ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日",
    "有効返信", "御礼連絡", "前日リマインド", "NG理由",
    "次アクション", "次アクション期日", "スカウト種別",
]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def main():
    svc = get_service()
    resp = (
        svc.spreadsheets()
        .values()
        .get(spreadsheetId=SPREADSHEET_ID, range="'02_マスター'!A3:W535")
        .execute()
    )
    rows = resp.get("values", [])
    logging.info("取得行数: %d", len(rows))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "spreadsheet_id": SPREADSHEET_ID,
                "sheet": "02_マスター",
                "range": "A3:W535",
                "header": HEADER,
                "rows": rows,
            },
            f,
            ensure_ascii=False,
            indent=1,
        )
    logging.info("保存先: %s", OUT_PATH)


if __name__ == "__main__":
    main()
