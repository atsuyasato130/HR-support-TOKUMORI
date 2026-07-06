"""YOUTRUST / LinkedIn / _媒体テンプレ に「スカウト種別」列(X列・24列目)を追加する。
既存の23列(候補者ID〜最終更新日)には一切触れない。読み取りで確認済みの実際の書式(バナー赤・
ヘッダ濃紺グレー)をそのまま踏襲する。
"""
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"

SHEETS = {
    "YOUTRUST": 1610514289,
    "LinkedIn": 1187381445,
    "_媒体テンプレ": 1144310096,
}

BANNER_BG = {"red": 0.68235296, "green": 0.19215687, "blue": 0.17254902}
WHITE = {"red": 1, "green": 1, "blue": 1}
HEAD_BG = {"red": 0.1764706, "green": 0.16862746, "blue": 0.15686275}
BORDER_DARK = {"red": 0.34901962, "green": 0.32941177, "blue": 0.31764707}
BORDER_LIGHT = {"red": 0.84705883, "green": 0.8392157, "blue": 0.827451}
GREY_TXT = {"red": 0.55, "green": 0.54, "blue": 0.53}
FONT = "Arial"


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def rng(sid, r0, c0, r1, c1):
    return {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def main():
    svc = get_service()
    reqs = []
    for name, sid in SHEETS.items():
        # 1) 列を1つ追加(24列目=Xとなる)
        reqs.append({"appendDimension": {"sheetId": sid, "dimension": "COLUMNS", "length": 1}})
        # 2) バナー(1行目)のマージを23列→24列に拡張
        reqs.append({"unmergeCells": {"range": rng(sid, 0, 0, 1, 23)}})
        reqs.append({"mergeCells": {"range": rng(sid, 0, 0, 1, 24), "mergeType": "MERGE_ALL"}})
        reqs.append({"repeatCell": {
            "range": rng(sid, 0, 0, 1, 24),
            "cell": {"userEnteredFormat": {
                "backgroundColor": BANNER_BG,
                "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
                "textFormat": {"foregroundColor": WHITE, "fontFamily": FONT,
                                "fontSize": 12, "bold": True},
            }},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,textFormat)",
        }})
        # 3) ヘッダー(2行目・X列)に「スカウト種別」を設定
        reqs.append({"updateCells": {
            "range": rng(sid, 1, 23, 2, 24),
            "rows": [{"values": [{"userEnteredValue": {"stringValue": "スカウト種別"}}]}],
            "fields": "userEnteredValue",
        }})
        reqs.append({"repeatCell": {
            "range": rng(sid, 1, 23, 2, 24),
            "cell": {"userEnteredFormat": {
                "backgroundColor": HEAD_BG,
                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                "wrapStrategy": "WRAP",
                "textFormat": {"foregroundColor": WHITE, "fontFamily": FONT,
                                "fontSize": 9, "bold": True},
                "borders": {
                    "top": {"style": "SOLID", "color": BORDER_DARK},
                    "bottom": {"style": "SOLID", "color": BORDER_DARK},
                    "left": {"style": "SOLID", "color": BORDER_LIGHT},
                    "right": {"style": "SOLID", "color": BORDER_LIGHT},
                },
            }},
            "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,"
                      "wrapStrategy,textFormat,borders)",
        }})
        # 4) 列幅
        reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 23, "endIndex": 24},
            "properties": {"pixelSize": 90},
            "fields": "pixelSize",
        }})
        # 5) データ域(行3〜500)の書式(フォント10・中央揃え)
        reqs.append(repeat_cell_data_fmt(sid))

    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"requests": reqs}
    ).execute()
    print(f"適用したリクエスト数: {len(reqs)}")


def repeat_cell_data_fmt(sid):
    return {"repeatCell": {
        "range": rng(sid, 2, 23, 500, 24),
        "cell": {"userEnteredFormat": {
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
            "textFormat": {"foregroundColor": GREY_TXT, "fontFamily": FONT, "fontSize": 9},
        }},
        "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat)",
    }}


if __name__ == "__main__":
    main()
