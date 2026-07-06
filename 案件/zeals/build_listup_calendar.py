"""04_日次入力タブをカレンダー形式(ListUp数のみ手入力)に作り替える。
A列(日付)・B列(媒体)・E列(ListUp)の列位置は変更しない(01_サマリー側の数式が
これらを直接参照しているため)。C,D,F,G,H,I,J列は非表示にするだけでデータ・数式は無傷。
"""
import datetime
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SHEET_ID = 499841405  # 04_日次入力
SHEET_NAME = "04_日次入力"

INK = {"red": 0.16, "green": 0.16, "blue": 0.16}
WHITE = {"red": 1, "green": 1, "blue": 1}
HEAD_BG = {"red": 0.1764706, "green": 0.16862746, "blue": 0.15686275}
PALE_RED = {"red": 0.965, "green": 0.918, "blue": 0.914}
TODAY_BG = {"red": 1.0, "green": 0.949, "blue": 0.8}
FONT = "Arial"
NF_DATE = {"type": "DATE", "pattern": "yyyy/mm/dd (aaa)"}

KIHATSU_DATE = datetime.date(2026, 1, 1)  # 03_設定マスタ!B43 実値(2026-01-01)
DAYS_PER_YEAR = 365  # 2026年は平年

MEDIA_LIST = ["YOUTRUST", "LinkedIn"]

# 0-indexed 行位置
BANNER1_ROW = 2       # row3: YOUTRUSTバナー
BLOCK1_START = 3       # row4〜: YOUTRUST 365行
BANNER2_ROW = BLOCK1_START + DAYS_PER_YEAR       # row369: LinkedInバナー
BLOCK2_START = BANNER2_ROW + 1                    # row370〜: LinkedIn 365行
TOTAL_ROWS_NEEDED = BLOCK2_START + DAYS_PER_YEAR  # 734


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def rng(r0, c0, r1, c1):
    return {"sheetId": SHEET_ID, "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def main():
    svc = get_service()

    # 現在の行数を確認し、不足分を追加
    meta = svc.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields="sheets(properties(sheetId,gridProperties))"
    ).execute()
    cur_rows = None
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == SHEET_ID:
            cur_rows = s["properties"]["gridProperties"]["rowCount"]
    need = TOTAL_ROWS_NEEDED + 10 - cur_rows
    reqs = []
    if need > 0:
        reqs.append({"appendDimension": {"sheetId": SHEET_ID, "dimension": "ROWS", "length": need}})

    # ── バナー行 ──
    for banner_row, name in [(BANNER1_ROW, "YOUTRUST"), (BANNER2_ROW, "LinkedIn")]:
        reqs.append({"mergeCells": {"range": rng(banner_row, 0, banner_row + 1, 5),
                                     "mergeType": "MERGE_ALL"}})
        reqs.append({"updateCells": {
            "range": rng(banner_row, 0, banner_row + 1, 1),
            "rows": [{"values": [{"userEnteredValue": {"stringValue": f"▼ {name}"}}]}],
            "fields": "userEnteredValue",
        }})
        reqs.append({"repeatCell": {
            "range": rng(banner_row, 0, banner_row + 1, 5),
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEAD_BG,
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
                "textFormat": {"foregroundColor": WHITE, "fontFamily": FONT,
                                "fontSize": 11, "bold": True},
            }},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat)",
        }})

    # ── E列(ListUp)の書式・列幅 ──
    reqs.append({"repeatCell": {
        "range": rng(0, 4, TOTAL_ROWS_NEEDED, 5),
        "cell": {"userEnteredFormat": {
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
            "textFormat": {"foregroundColor": INK, "fontFamily": FONT, "fontSize": 11, "bold": True},
            "backgroundColor": PALE_RED,
        }},
        "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat,backgroundColor)",
    }})
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 4, "endIndex": 5},
        "properties": {"pixelSize": 90}, "fields": "pixelSize",
    }})

    # ── C,D,F,G,H,I,J列を非表示 ──
    for start, end in [(2, 4), (5, 10)]:
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": start, "endIndex": end},
            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser",
        }})

    # ── 日付・媒体の値、日付書式 ──
    for start_row, name in [(BLOCK1_START, "YOUTRUST"), (BLOCK2_START, "LinkedIn")]:
        dates = [[(KIHATSU_DATE + datetime.timedelta(days=i)).isoformat(), name]
                 for i in range(DAYS_PER_YEAR)]
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!A{start_row+1}:B{start_row+DAYS_PER_YEAR}",
            valueInputOption="USER_ENTERED",
            body={"values": dates},
        ).execute()
        reqs.append({"repeatCell": {
            "range": rng(start_row, 0, start_row + DAYS_PER_YEAR, 1),
            "cell": {"userEnteredFormat": {"numberFormat": NF_DATE, "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(numberFormat,horizontalAlignment)",
        }})
        reqs.append({"repeatCell": {
            "range": rng(start_row, 1, start_row + DAYS_PER_YEAR, 2),
            "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(horizontalAlignment)",
        }})

    # ── 当日ハイライト(条件付き書式) ──
    for start_row in (BLOCK1_START, BLOCK2_START):
        reqs.append({"addConditionalFormatRule": {
            "rule": {
                "ranges": [rng(start_row, 0, start_row + DAYS_PER_YEAR, 5)],
                "booleanRule": {
                    "condition": {"type": "CUSTOM_FORMULA",
                                   "values": [{"userEnteredValue": f"=$A{start_row+1}=TODAY()"}]},
                    "format": {"backgroundColor": TODAY_BG},
                },
            },
            "index": 0,
        }})

    # ── 月単位で行グループ化 ──
    d = KIHATSU_DATE
    for start_row, _ in [(BLOCK1_START, "YOUTRUST"), (BLOCK2_START, "LinkedIn")]:
        day_idx = 0
        for m in range(12):
            month = (KIHATSU_DATE.month - 1 + m) % 12 + 1
            year = KIHATSU_DATE.year + (KIHATSU_DATE.month - 1 + m) // 12
            import calendar
            days_in_month = calendar.monthrange(year, month)[1]
            r0 = start_row + day_idx
            r1 = min(r0 + days_in_month, start_row + DAYS_PER_YEAR)
            if r1 > r0:
                reqs.append({"addDimensionGroup": {"range": {
                    "sheetId": SHEET_ID, "dimension": "ROWS",
                    "startIndex": r0, "endIndex": r1,
                }}})
            day_idx += days_in_month

    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"requests": reqs}
    ).execute()
    print(f"適用完了: リクエスト数={len(reqs)}")


if __name__ == "__main__":
    main()
