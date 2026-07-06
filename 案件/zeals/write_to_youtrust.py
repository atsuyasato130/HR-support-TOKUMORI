"""transformed_youtrust_rows.json をYOUTRUSTタブ A3:X523 へ書き込む(Step4)。
02_マスターの生データにはこの時点では一切触れない(Step6で別途対応)。
"""
import json
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SRC = os.path.expanduser("~/Claude AI/scratch_zeals/transformed_youtrust_rows.json")

COLUMN_ORDER = [
    "候補者ID", "流入チャネル", "担当者", "候補者名", "プロフィールURL",
    "職種", "雇用形態希望", "意欲ステータス", "接点ステータス",
    "ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日",
    "有効返信", "御礼連絡", "前日リマインド", "NG理由",
    "次アクション", "次アクション期日", "memo", "最終更新日", "スカウト種別",
]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def main():
    with open(SRC, encoding="utf-8") as f:
        rows = json.load(f)

    grid = [[r.get(col, "") for col in COLUMN_ORDER] for r in rows]
    n = len(grid)
    last_row = 2 + n  # データは3行目開始(1-indexed)

    svc = get_service()
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"YOUTRUST!A3:X{last_row}",
        valueInputOption="USER_ENTERED",
        body={"values": grid},
    ).execute()
    print(f"書き込み完了: YOUTRUST!A3:X{last_row} ({n}行)")


if __name__ == "__main__":
    main()
