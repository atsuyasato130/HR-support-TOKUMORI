"""04_日次入力を「月×日の格子(カレンダー)」でListUp数を入力できる形に作り直す。

構成:
  上段(スタッフが実際に触る): 媒体×月(12ヶ月)の表、列=日1〜31、セルに数字を入れるだけ
  下段(自動生成・編集不要): 従来の「1行=1日」ログ形式を維持し、E列(ListUp)は
    上段の格子をINDEX/MATCHで参照する数式に変更。A列(日付)・B列(媒体)は不変。
    → 01_サマリー側の数式(SUMIFS('04_日次入力'!$A:$A / $E:$E ...))は一切変更不要。
"""
import calendar
import datetime
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SHEET_ID = 499841405
SHEET_NAME = "04_日次入力"

INK = {"red": 0.16, "green": 0.16, "blue": 0.16}
WHITE = {"red": 1, "green": 1, "blue": 1}
HEAD_BG = {"red": 0.1764706, "green": 0.16862746, "blue": 0.15686275}
RED_DK = {"red": 0.494, "green": 0.110, "blue": 0.094}
PALE_RED = {"red": 0.965, "green": 0.918, "blue": 0.914}
GREY_TXT = {"red": 0.55, "green": 0.54, "blue": 0.53}
TODAY_BG = {"red": 1.0, "green": 0.949, "blue": 0.8}
FONT = "Arial"
NF_DATE = {"type": "DATE", "pattern": "yyyy/mm/dd (aaa)"}
NF_YM = {"type": "DATE", "pattern": "yyyy年m月"}
NF_INT = {"type": "NUMBER", "pattern": "#,##0"}

KIHATSU_DATE = datetime.date(2026, 1, 1)
MEDIA_LIST = ["YOUTRUST", "LinkedIn"]
N_MEDIA = len(MEDIA_LIST)

# ── 上段(格子)のレイアウト ──
GRID_TITLE_ROW = 1          # row2: "▼ カレンダー入力"
GRID_HEADER_ROW = 2          # row3: 媒体,月,1..31,計
GRID_DATA_START = 3          # row4〜: media×12ヶ月
GRID_ROWS = N_MEDIA * 12     # 24行
GRID_DATA_END = GRID_DATA_START + GRID_ROWS   # 27 (exclusive)

# ── 下段(ログ・自動生成)のレイアウト ──
LOG_TITLE_ROW = GRID_DATA_END + 1              # 空行を1つ挟む
LOG_HEADER_ROW = LOG_TITLE_ROW + 1
LOG_DATA_START = LOG_HEADER_ROW + 1
DAYS_PER_YEAR = 365
LOG_BLOCK_STARTS = []  # [(start_row, media_name), ...]
r = LOG_DATA_START
for name in MEDIA_LIST:
    LOG_BLOCK_STARTS.append((r, name))
    r += DAYS_PER_YEAR + 1  # +1 for sub-banner between blocks (banner precedes each block)
# 上のループはバナー分を考慮していないので組み直す
LOG_BLOCK_STARTS = []
r = LOG_DATA_START
for i, name in enumerate(MEDIA_LIST):
    banner_row = r
    data_row = r + 1
    LOG_BLOCK_STARTS.append((banner_row, data_row, name))
    r = data_row + DAYS_PER_YEAR
TOTAL_ROWS_NEEDED = r + 5


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def rng(r0, c0, r1, c1):
    return {"sheetId": SHEET_ID, "startRowIndex": r0, "endRowIndex": r1,
            "startColumnIndex": c0, "endColumnIndex": c1}


def repeat_fmt(r0, c0, r1, c1, **kw):
    bg = kw.get("bg")
    fg = kw.get("fg", INK)
    bold = kw.get("bold", False)
    size = kw.get("size")
    halign = kw.get("halign")
    numfmt = kw.get("numfmt")
    tf = {"foregroundColor": fg, "bold": bold, "fontFamily": FONT}
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


def main():
    svc = get_service()

    # 0) 既存内容を全クリア(値・書式・条件付き書式・グループ) してから作り直す
    svc.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID, range=f"'{SHEET_NAME}'!A1:AH2000", body={},
    ).execute()

    meta = svc.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID, fields="sheets(properties(sheetId,gridProperties))"
    ).execute()
    cur_rows = cur_cols = None
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == SHEET_ID:
            cur_rows = s["properties"]["gridProperties"]["rowCount"]
            cur_cols = s["properties"]["gridProperties"]["columnCount"]

    pre_reqs = []
    # 既存の条件付き書式・行グループを一旦削除
    pre_reqs.append({"deleteConditionalFormatRule": {"sheetId": SHEET_ID, "index": 0}})
    pre_reqs.append({"deleteConditionalFormatRule": {"sheetId": SHEET_ID, "index": 0}})
    if cur_rows < TOTAL_ROWS_NEEDED:
        pre_reqs.append({"appendDimension": {"sheetId": SHEET_ID, "dimension": "ROWS",
                                              "length": TOTAL_ROWS_NEEDED - cur_rows + 10}})
    need_cols = 34  # A..AH
    if cur_cols < need_cols:
        pre_reqs.append({"appendDimension": {"sheetId": SHEET_ID, "dimension": "COLUMNS",
                                              "length": need_cols - cur_cols}})
    # 全列いったん再表示(前回のhiddenをリセットしてから必要な列だけ再度隠す)
    pre_reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 0, "endIndex": need_cols},
        "properties": {"hiddenByUser": False}, "fields": "hiddenByUser",
    }})
    # 白背景・罫線NONEでクリーンアップ
    pre_reqs.append(repeat_fmt(0, 0, TOTAL_ROWS_NEEDED, need_cols, bg=WHITE, fg=INK))
    pre_reqs.append({"updateBorders": {"range": rng(0, 0, TOTAL_ROWS_NEEDED, need_cols),
                                        "top": {"style": "NONE"}, "bottom": {"style": "NONE"},
                                        "left": {"style": "NONE"}, "right": {"style": "NONE"},
                                        "innerHorizontal": {"style": "NONE"}, "innerVertical": {"style": "NONE"}}})
    try:
        svc.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": pre_reqs}).execute()
    except Exception as e:
        print("事前クリーンアップで一部スキップ:", e)

    reqs = []

    # ── メインバナー(row1) ──
    reqs.append({"mergeCells": {"range": rng(0, 0, 1, need_cols), "mergeType": "MERGE_ALL"}})
    reqs.append({"updateCells": {"range": rng(0, 0, 1, 1), "rows": [{"values": [
        {"userEnteredValue": {"stringValue": "日次入力｜ListUp数（カレンダー形式で入力）"}}]}],
        "fields": "userEnteredValue"}})
    reqs.append(repeat_fmt(0, 0, 1, need_cols, bg=RED_DK, fg=WHITE, bold=True, size=13, halign="LEFT"))

    # ── グリッドタイトル(row2) ──
    reqs.append({"mergeCells": {"range": rng(GRID_TITLE_ROW, 0, GRID_TITLE_ROW + 1, need_cols), "mergeType": "MERGE_ALL"}})
    reqs.append({"updateCells": {"range": rng(GRID_TITLE_ROW, 0, GRID_TITLE_ROW + 1, 1), "rows": [{"values": [
        {"userEnteredValue": {"stringValue": "▼ カレンダー入力（媒体×月ごとに、その日のListUp数を入力してください）"}}]}],
        "fields": "userEnteredValue"}})
    reqs.append(repeat_fmt(GRID_TITLE_ROW, 0, GRID_TITLE_ROW + 1, need_cols, fg=RED_DK, bold=True, size=11))

    # ── グリッドヘッダー(row3): 媒体,月,1..31,計 ──
    header_vals = [{"userEnteredValue": {"stringValue": "媒体"}},
                    {"userEnteredValue": {"stringValue": "月"}}]
    for d in range(1, 32):
        header_vals.append({"userEnteredValue": {"numberValue": d}})
    header_vals.append({"userEnteredValue": {"stringValue": "計"}})
    reqs.append({"updateCells": {"range": rng(GRID_HEADER_ROW, 0, GRID_HEADER_ROW + 1, 34),
                                  "rows": [{"values": header_vals}], "fields": "userEnteredValue"}})
    reqs.append(repeat_fmt(GRID_HEADER_ROW, 0, GRID_HEADER_ROW + 1, 34, bg=HEAD_BG, fg=WHITE,
                            bold=True, size=9, halign="CENTER"))

    # ── グリッドデータ(media×12ヶ月) ──
    grid_values = []
    for name in MEDIA_LIST:
        for m in range(12):
            month_date = datetime.date(
                KIHATSU_DATE.year + (KIHATSU_DATE.month - 1 + m) // 12,
                (KIHATSU_DATE.month - 1 + m) % 12 + 1, 1)
            row = [name, month_date.isoformat()] + [""] * 31
            grid_values.append(row)
    # 計列は数式で
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'!A{GRID_DATA_START+1}:AG{GRID_DATA_END}",
        valueInputOption="USER_ENTERED", body={"values": grid_values},
    ).execute()
    sum_formulas = [[f"=SUM(C{GRID_DATA_START+1+i}:AG{GRID_DATA_START+1+i})"] for i in range(GRID_ROWS)]
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'!AH{GRID_DATA_START+1}:AH{GRID_DATA_END}",
        valueInputOption="USER_ENTERED", body={"values": sum_formulas},
    ).execute()

    reqs.append(repeat_fmt(GRID_DATA_START, 0, GRID_DATA_END, 1, size=10, halign="LEFT", bold=True))
    reqs.append(repeat_fmt(GRID_DATA_START, 1, GRID_DATA_END, 2, size=10, halign="CENTER", numfmt=NF_YM))
    reqs.append(repeat_fmt(GRID_DATA_START, 2, GRID_DATA_END, 33, size=10, halign="CENTER",
                            numfmt=NF_INT, bg=PALE_RED))
    reqs.append(repeat_fmt(GRID_DATA_START, 33, GRID_DATA_END, 34, size=10, halign="CENTER",
                            numfmt=NF_INT, bold=True, bg=HEAD_BG, fg=WHITE))
    for i in range(GRID_ROWS):
        rr = GRID_DATA_START + i
        bg = {"red": 0.965, "green": 0.965, "blue": 0.965} if i % 2 else WHITE
        if i % 12 == 0 and i > 0:
            reqs.append({"updateBorders": {"range": rng(rr, 0, rr + 1, 34),
                                            "top": {"style": "SOLID", "color": {"red": 0.35, "green": 0.33, "blue": 0.32}}}})
    reqs.append({"updateBorders": {"range": rng(GRID_HEADER_ROW, 0, GRID_DATA_END, 34), "innerHorizontal": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}}, "innerVertical": {"style": "SOLID", "color": {"red": 0.85, "green": 0.85, "blue": 0.85}}}})
    reqs.append({"updateBorders": {"range": rng(GRID_HEADER_ROW, 0, GRID_DATA_END, 34),
                                    "top": {"style": "SOLID", "color": {"red": 0.35, "green": 0.33, "blue": 0.32}},
                                    "bottom": {"style": "SOLID", "color": {"red": 0.35, "green": 0.33, "blue": 0.32}},
                                    "left": {"style": "SOLID", "color": {"red": 0.35, "green": 0.33, "blue": 0.32}},
                                    "right": {"style": "SOLID", "color": {"red": 0.35, "green": 0.33, "blue": 0.32}}}})

    # 列幅
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
        "properties": {"pixelSize": 90}, "fields": "pixelSize"}})
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
        "properties": {"pixelSize": 80}, "fields": "pixelSize"}})
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 33},
        "properties": {"pixelSize": 32}, "fields": "pixelSize"}})
    reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": 33, "endIndex": 34},
        "properties": {"pixelSize": 60}, "fields": "pixelSize"}})

    # 当月ハイライト(グリッド行)
    reqs.append({"addConditionalFormatRule": {
        "rule": {"ranges": [rng(GRID_DATA_START, 0, GRID_DATA_END, 34)],
                 "booleanRule": {"condition": {"type": "CUSTOM_FORMULA",
                                                "values": [{"userEnteredValue": f"=$B{GRID_DATA_START+1}=EOMONTH(TODAY(),-1)+1"}]},
                                  "format": {"backgroundColor": TODAY_BG}}},
        "index": 0}})

    # ── ログセクション(自動生成・編集不要) ──
    reqs.append({"mergeCells": {"range": rng(LOG_TITLE_ROW, 0, LOG_TITLE_ROW + 1, 10), "mergeType": "MERGE_ALL"}})
    reqs.append({"updateCells": {"range": rng(LOG_TITLE_ROW, 0, LOG_TITLE_ROW + 1, 1), "rows": [{"values": [
        {"userEnteredValue": {"stringValue": "▼ 詳細ログ（自動生成・編集不要／上のカレンダーの値をサマリー集計用に展開したものです）"}}]}],
        "fields": "userEnteredValue"}})
    reqs.append(repeat_fmt(LOG_TITLE_ROW, 0, LOG_TITLE_ROW + 1, 10, fg=GREY_TXT, italic=False, bold=True, size=10))

    log_header = ["日付", "媒体", "職種", "担当者", "ListUp", "送付", "返信", "面談", "採用", "memo"]
    reqs.append({"updateCells": {"range": rng(LOG_HEADER_ROW, 0, LOG_HEADER_ROW + 1, 10),
                                  "rows": [{"values": [{"userEnteredValue": {"stringValue": h}} for h in log_header]}],
                                  "fields": "userEnteredValue"}})
    reqs.append(repeat_fmt(LOG_HEADER_ROW, 0, LOG_HEADER_ROW + 1, 10, bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER"))

    svc.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": reqs}).execute()
    print("グリッド・バナー部分を適用完了")

    # ── ログの日付・媒体・E列(グリッド参照数式)を書き込み ──
    reqs2 = []
    for banner_row, data_row, name in LOG_BLOCK_STARTS:
        reqs2.append({"mergeCells": {"range": rng(banner_row, 0, banner_row + 1, 5), "mergeType": "MERGE_ALL"}})
        reqs2.append({"updateCells": {"range": rng(banner_row, 0, banner_row + 1, 1),
                                       "rows": [{"values": [{"userEnteredValue": {"stringValue": f"▼ {name}"}}]}],
                                       "fields": "userEnteredValue"}})
        reqs2.append(repeat_fmt(banner_row, 0, banner_row + 1, 5, bg=HEAD_BG, fg=WHITE, bold=True, size=10, halign="LEFT"))

        dates = [[(KIHATSU_DATE + datetime.timedelta(days=i)).isoformat(), name] for i in range(DAYS_PER_YEAR)]
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!A{data_row+1}:B{data_row+DAYS_PER_YEAR}",
            valueInputOption="USER_ENTERED", body={"values": dates},
        ).execute()
        e_formulas = []
        for i in range(DAYS_PER_YEAR):
            rr = data_row + 1 + i
            f = (f'=IFERROR(INDEX($C${GRID_DATA_START+1}:$AG${GRID_DATA_END},'
                 f'MATCH($B{rr}&"|"&DATE(YEAR($A{rr}),MONTH($A{rr}),1),'
                 f'$A${GRID_DATA_START+1}:$A${GRID_DATA_END}&"|"&$B${GRID_DATA_START+1}:$B${GRID_DATA_END},0),'
                 f'DAY($A{rr})),"")')
            e_formulas.append([f])
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{SHEET_NAME}'!E{data_row+1}:E{data_row+DAYS_PER_YEAR}",
            valueInputOption="USER_ENTERED", body={"values": e_formulas},
        ).execute()
        reqs2.append(repeat_fmt(data_row, 0, data_row + DAYS_PER_YEAR, 1, numfmt=NF_DATE, halign="CENTER", size=9))
        reqs2.append(repeat_fmt(data_row, 4, data_row + DAYS_PER_YEAR, 5, halign="CENTER", size=9))

    # 不要列(C,D,F,G,H,I,J)を非表示(ログ部分のみ影響。グリッド部分は別列レンジなので無関係)
    for start, end in [(2, 4), (5, 10)]:
        reqs2.append({"updateDimensionProperties": {
            "range": {"sheetId": SHEET_ID, "dimension": "COLUMNS", "startIndex": start, "endIndex": end},
            "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})

    # ログ行を折りたたみ(自動生成なので普段は隠す)
    for banner_row, data_row, name in LOG_BLOCK_STARTS:
        reqs2.append({"addDimensionGroup": {"range": {
            "sheetId": SHEET_ID, "dimension": "ROWS",
            "startIndex": data_row, "endIndex": data_row + DAYS_PER_YEAR}}})

    svc.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={"requests": reqs2}).execute()
    print("ログ部分(数式・非表示・折りたたみ)を適用完了")
    print("GRID_DATA_START(0idx)=", GRID_DATA_START, "GRID_DATA_END=", GRID_DATA_END)
    print("LOG_BLOCK_STARTS=", LOG_BLOCK_STARTS)


if __name__ == "__main__":
    main()
