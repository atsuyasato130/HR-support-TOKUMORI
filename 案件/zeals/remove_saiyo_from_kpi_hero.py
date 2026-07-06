"""KPIヒーローから「採用」ボックスを外し、残る4指標(ListUp/送付/返信/面談)を5列/箱で均等再配置する。
採用のデータ・数式(funnel_table等)は一切触れない。ヒーロー表示からだけ外す。
"""
import json
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SHEET_ID = 54361115
SHEET_NAME = "01_サマリー"
NC = 36

RED_DK = {"red": 0.494, "green": 0.110, "blue": 0.094}
INK = {"red": 0.16, "green": 0.16, "blue": 0.16}
WHITE = {"red": 1, "green": 1, "blue": 1}
PALE_RED = {"red": 0.965, "green": 0.918, "blue": 0.914}
BOX_BORDER = {"red": 0.35, "green": 0.33, "blue": 0.32}
GREY_TXT = {"red": 0.55, "green": 0.54, "blue": 0.53}
NOTE_BG = {"red": 0.97, "green": 0.965, "blue": 0.96}
FONT = "Arial"
NF_INT = {"type": "NUMBER", "pattern": "#,##0"}

STAGE_LABELS = ["ListUp", "送付", "返信", "面談"]  # 採用を除いた4指標
OLD_COLS_A1 = ["A", "E", "I", "M"]   # 現行(5列/箱の名残=4列/箱アンカー)
NEW_COLS_A1 = ["A", "F", "K", "P"]   # 新アンカー(5列/箱: 0,5,10,15)

FORMULAS_PATH = os.path.expanduser("~/Claude AI/scratch_zeals/kpi_hero_formulas_4box.json")

BLOCKS = [
    {"label": 5, "value": 6, "subtitle": 8},
    {"label": 54, "value": 55, "subtitle": 57},
]
BLOCK_RANGES_0IDX = [(4, 8), (53, 57)]


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def rng(r0, c0, r1, c1):
    return {"sheetId": SHEET_ID, "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def repeat_cell_fmt(r0, c0, r1, c1, bg=None, fg=None, bold=False, size=None,
                     halign=None, numfmt=None):
    tf = {"foregroundColor": fg or INK, "bold": bold, "fontFamily": FONT}
    if size:
        tf["fontSize"] = size
    cf = {"textFormat": tf, "verticalAlignment": "MIDDLE"}
    if bg is not None:
        cf["backgroundColor"] = bg
    if halign:
        cf["horizontalAlignment"] = halign
    if numfmt:
        cf["numberFormat"] = numfmt
    fields = "userEnteredFormat(textFormat,verticalAlignment"
    fields += ",backgroundColor" if bg is not None else ""
    fields += ",horizontalAlignment" if halign else ""
    fields += ",numberFormat" if numfmt else ""
    fields += ")"
    return {"repeatCell": {"range": rng(r0, c0, r1, c1),
                            "cell": {"userEnteredFormat": cf}, "fields": fields}}


def border_none(r0, c0, r1, c1):
    n = {"style": "NONE"}
    return {"updateBorders": {"range": rng(r0, c0, r1, c1),
                               "top": n, "bottom": n, "left": n, "right": n,
                               "innerHorizontal": n, "innerVertical": n}}


def border_box(r0, c0, r1, c1):
    b = {"style": "SOLID", "color": BOX_BORDER}
    return {"updateBorders": {"range": rng(r0, c0, r1, c1),
                               "top": b, "bottom": b, "left": b, "right": b}}


def unmerge(r0, c0, r1, c1):
    return {"unmergeCells": {"range": rng(r0, c0, r1, c1)}}


def merge(r0, c0, r1, c1):
    return {"mergeCells": {"range": rng(r0, c0, r1, c1), "mergeType": "MERGE_ALL"}}


def main():
    svc = get_service()
    with open(FORMULAS_PATH, encoding="utf-8") as f:
        formulas = json.load(f)

    # Step1: クリーンアップ
    step1_reqs = []
    for r0, r1 in BLOCK_RANGES_0IDX:
        step1_reqs.append(unmerge(r0, 0, r1, NC))
        step1_reqs.append(repeat_cell_fmt(r0, 0, r1, NC, bg=WHITE, fg=INK, bold=False))
        step1_reqs.append(border_none(r0, 0, r1, NC))
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"requests": step1_reqs}
    ).execute()
    print(f"Step1 クリーンアップ完了 ({len(step1_reqs)}件)")

    # Step2: 数式移設(旧アンカー→新アンカー、旧アンカーは空に)
    value_data = []
    for block in BLOCKS:
        for row_key in ("label", "value", "subtitle"):
            row = block[row_key]
            for old_col, new_col in zip(OLD_COLS_A1, NEW_COLS_A1):
                formula = formulas[f"'{SHEET_NAME}'!{old_col}{row}"]
                value_data.append({"range": f"'{SHEET_NAME}'!{new_col}{row}",
                                    "values": [[formula]]})
                if old_col != new_col:
                    value_data.append({"range": f"'{SHEET_NAME}'!{old_col}{row}",
                                        "values": [[""]]})
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"valueInputOption": "USER_ENTERED", "data": value_data},
    ).execute()
    print(f"Step2 数式移設完了 ({len(value_data)}件)")

    # Step3: 5列/箱で再構築(4箱のみ)
    step3_reqs = []
    for block in BLOCKS:
        label_row0 = block["label"] - 1
        value_row0 = block["value"] - 1
        subtitle_row0 = block["subtitle"] - 1
        for i, label in enumerate(STAGE_LABELS):
            c0, c1 = i * 5, (i + 1) * 5
            step3_reqs.append(merge(label_row0, c0, label_row0 + 1, c1))
            step3_reqs.append(repeat_cell_fmt(label_row0, c0, label_row0 + 1, c1,
                                               bg=RED_DK, fg=WHITE, bold=True, size=11,
                                               halign="CENTER"))
            step3_reqs.append(merge(value_row0, c0, value_row0 + 2, c1))
            step3_reqs.append(repeat_cell_fmt(value_row0, c0, value_row0 + 2, c1,
                                               bg=PALE_RED, fg=RED_DK, bold=True, size=20,
                                               halign="CENTER", numfmt=NF_INT))
            step3_reqs.append(merge(subtitle_row0, c0, subtitle_row0 + 1, c1))
            step3_reqs.append(repeat_cell_fmt(subtitle_row0, c0, subtitle_row0 + 1, c1,
                                               bg=NOTE_BG, fg=GREY_TXT, size=9, halign="CENTER"))
            step3_reqs.append(border_box(label_row0, c0, subtitle_row0 + 1, c1))
    svc.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body={"requests": step3_reqs}
    ).execute()
    print(f"Step3 再構築完了 ({len(step3_reqs)}件)")


if __name__ == "__main__":
    main()
