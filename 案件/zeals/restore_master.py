"""02_マスターを数式駆動(読取専用・自動集計)へ復元する(Step6)。
1) ヘッダーを正しい25列(媒体+テンプレ23列+スカウト種別)に統一
2) 旧・生データ(A3:W535)をクリア
3) YOUTRUST/LinkedInを縦結合する配列数式をA3にセット($A$3:$X = 24列、スカウト種別込み)
"""
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"

HEADER = [
    "媒体", "候補者ID", "流入チャネル", "担当者", "候補者名", "プロフィールURL",
    "職種", "雇用形態希望", "意欲ステータス", "接点ステータス",
    "ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日",
    "有効返信", "御礼連絡", "前日リマインド", "NG理由",
    "次アクション", "次アクション期日", "memo", "最終更新日", "スカウト種別",
]

MEDIA_NAMES = ["YOUTRUST", "LinkedIn"]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def master_union_formula(media_names):
    blocks = []
    for name in media_names:
        blocks.append(
            f'ARRAYFORMULA(IF({name}!$A$3:$A<>"","{name}","")),{name}!$A$3:$X'
        )
    inner = "; ".join(blocks)
    return "={" + inner + "}"


def main():
    svc = get_service()

    # 1) ヘッダーを正しい25列へ
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'02_マスター'!A2:Y2",
        valueInputOption="RAW", body={"values": [HEADER]},
    ).execute()
    print("ヘッダー更新完了")

    # 2) 旧・生データをクリア(A3:W535 + 念のため少し広め)
    svc.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range="'02_マスター'!A3:Y600", body={},
    ).execute()
    print("旧データクリア完了")

    # 3) 統合数式をセット
    formula = master_union_formula(MEDIA_NAMES)
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'02_マスター'!A3",
        valueInputOption="USER_ENTERED", body={"values": [[formula]]},
    ).execute()
    print("統合数式セット完了:", formula)


if __name__ == "__main__":
    main()
