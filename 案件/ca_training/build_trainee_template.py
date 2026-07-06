#!/usr/bin/env python3
"""
新卒“個人用”研修シートのテンプレートを作成する。
- 管理SSのGAS(generateTraineeSheets)がこれを複製→本人＋管理者のみに権限設定して配布する。
- タブ: 研修ホーム(個人) / 進捗チェック(全モジュール) / 学習メモ
- テンプレIDを .trainee_template_id に保存し、管理SSの 設定!I1 にも書き込む(GASが参照)。
- テンプレ自体はドメイン閲覧で共有(管理者がGASで複製できるように)。複製先は本人＋管理者のみ。
"""
import json
import os
import warnings

warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
RED = {"red": 0.686, "green": 0.196, "blue": 0.173}
WHITE = {"red": 1, "green": 1, "blue": 1}
INK = {"red": 0.11, "green": 0.11, "blue": 0.11}
PANEL = {"red": 0.98, "green": 0.972, "blue": 0.968}
LRED = {"red": 0.965, "green": 0.925, "blue": 0.917}


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)
    dr = build("drive", "v3", credentials=c)
    tr = json.load(open(os.path.join(BASE, "data_training.json"), encoding="utf-8"))
    HUB = open(os.path.join(BASE, ".ca_sheet_id")).read().strip()
    huburl = "https://docs.google.com/spreadsheets/d/%s/edit" % HUB

    tabs = ["研修ホーム", "進捗チェック", "学習メモ"]
    ss = sv.spreadsheets().create(body={"properties": {"title": "【テンプレート】新卒研修 個人シート"},
        "sheets": [{"properties": {"title": t, "gridProperties": {"frozenRowCount": (0 if t == "研修ホーム" else 1)}}} for t in tabs]}).execute()
    ssid = ss["spreadsheetId"]
    sid = {s["properties"]["title"]: s["properties"]["sheetId"] for s in ss["sheets"]}
    open(os.path.join(BASE, ".trainee_template_id"), "w").write(ssid)

    # 進捗チェック（全モジュール）
    rows = [["ID", "カテゴリ", "モジュール", "ステータス", "完了日", "自己採点(点)", "上長確認", "メモ"]]
    for r in tr["CURRICULUM"]:
        rows.append([r[0], r[1], r[2], "未着手", "", "", "", ""])
    n = len(rows) - 1
    sv.spreadsheets().values().update(spreadsheetId=ssid, range="進捗チェック!A1",
        valueInputOption="USER_ENTERED", body={"values": rows}).execute()

    # 研修ホーム
    home = [
        ["", "あなたの研修進捗ダッシュボード", "", "", ""],
        ["", "", "", "", ""],
        ["", "進捗率", "修了モジュール", "総モジュール", "平均自己採点"],
        ["", '=IFERROR(COUNTIF(進捗チェック!D2:D,"修了")/COUNTA(進捗チェック!A2:A),0)',
             '=COUNTIF(進捗チェック!D2:D,"修了")', '=COUNTA(進捗チェック!A2:A)',
             '=IFERROR(ROUND(AVERAGE(進捗チェック!F2:F),1),0)'],
        ["", "", "", "", ""],
        ["", "■ 学習リンク", "", "", ""],
        ["", '=HYPERLINK("%s","研修ハブ（カリキュラム・教材・動画・業界×職種）を開く")' % huburl, "", "", ""],
        ["", "■ 使い方", "", "", ""],
        ["", "1. 研修ハブの『カリキュラム一覧』から各モジュールの教材(スライド)・YouTubeで学ぶ", "", "", ""],
        ["", "2. 確認テスト(各モジュールのリンク)を受け、90点以上で合格", "", "", ""],
        ["", "3. このシートの『進捗チェック』でステータス・完了日・自己採点を更新", "", "", ""],
        ["", "4. 半年でStage1〜3をクリア＝独り立ち（売上300万円が実務KPI）", "", "", ""],
        ["", "※ このシートは“あなたと管理者だけ”が見られます。気づき・悩みは学習メモへ。", "", "", ""],
    ]
    sv.spreadsheets().values().update(spreadsheetId=ssid, range="研修ホーム!A1",
        valueInputOption="USER_ENTERED", body={"values": home}).execute()
    sv.spreadsheets().values().update(spreadsheetId=ssid, range="学習メモ!A1",
        valueInputOption="USER_ENTERED", body={"values": [["日付", "学んだこと・気づき", "次にやること"]]}).execute()

    # 体裁
    reqs = []
    def band(tab, ncols, r=0, color=RED):
        reqs.append({"repeatCell": {"range": {"sheetId": sid[tab], "startRowIndex": r, "endRowIndex": r + 1, "startColumnIndex": 0, "endColumnIndex": ncols},
            "cell": {"userEnteredFormat": {"backgroundColor": color, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 10}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}})
    band("進捗チェック", 8); band("学習メモ", 3)
    for t in tabs:
        reqs.append({"updateSheetProperties": {"properties": {"sheetId": sid[t], "gridProperties": {"hideGridlines": True}}, "fields": "gridProperties.hideGridlines"}})
    # ホーム タイトル
    H = "研修ホーム"
    reqs.append({"mergeCells": {"range": {"sheetId": sid[H], "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 1, "endColumnIndex": 6}, "mergeType": "MERGE_ALL"}})
    reqs.append({"repeatCell": {"range": {"sheetId": sid[H], "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 1, "endColumnIndex": 6},
        "cell": {"userEnteredFormat": {"backgroundColor": RED, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 15}, "verticalAlignment": "MIDDLE"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}})
    reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[H], "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 42}, "fields": "pixelSize"}})
    # KPIラベル/数値
    reqs.append({"repeatCell": {"range": {"sheetId": sid[H], "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 1, "endColumnIndex": 5},
        "cell": {"userEnteredFormat": {"backgroundColor": LRED, "textFormat": {"bold": True}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}})
    reqs.append({"repeatCell": {"range": {"sheetId": sid[H], "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1, "endColumnIndex": 5},
        "cell": {"userEnteredFormat": {"textFormat": {"bold": True, "fontSize": 16, "foregroundColor": RED}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(textFormat,horizontalAlignment)"}})
    reqs.append({"repeatCell": {"range": {"sheetId": sid[H], "startRowIndex": 3, "endRowIndex": 4, "startColumnIndex": 1, "endColumnIndex": 2},
        "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0%"}}}, "fields": "userEnteredFormat.numberFormat"}})
    # 進捗率(進捗チェックにも)・ステータス プルダウン
    reqs.append({"setDataValidation": {"range": {"sheetId": sid["進捗チェック"], "startRowIndex": 1, "endRowIndex": n + 1, "startColumnIndex": 3, "endColumnIndex": 4},
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in ["未着手", "学習中", "テスト済", "修了"]]}, "showCustomUi": True}}})
    reqs.append({"setDataValidation": {"range": {"sheetId": sid["進捗チェック"], "startRowIndex": 1, "endRowIndex": n + 1, "startColumnIndex": 6, "endColumnIndex": 7},
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in ["", "確認済"]]}, "showCustomUi": True}}})
    # 条件付き書式(修了=緑)
    reqs.append({"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid["進捗チェック"], "startRowIndex": 1, "startColumnIndex": 3, "endColumnIndex": 4}],
        "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": "修了"}]}, "format": {"backgroundColor": {"red": 0.80, "green": 0.92, "blue": 0.82}}}}, "index": 0}})
    # 列幅
    def colw(tab, ws):
        for i, w in enumerate(ws):
            reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[tab], "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    colw("進捗チェック", [70, 120, 230, 90, 100, 100, 80, 320])
    colw("研修ホーム", [24, 240, 130, 120, 130, 130])
    colw("学習メモ", [110, 460, 320])
    reqs.append({"setBasicFilter": {"filter": {"range": {"sheetId": sid["進捗チェック"], "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": 8}}}})
    sv.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()

    # テンプレをドメイン閲覧で共有(管理者がGASで複製できるように)
    dr.permissions().create(fileId=ssid, body={"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}, sendNotificationEmail=False, fields="id").execute()
    dr.permissions().create(fileId=ssid, body={"type": "user", "role": "writer", "emailAddress": "shun_watanabe@tokumori.co.jp"}, sendNotificationEmail=False, fields="id").execute()

    # 管理SSの 設定!H1/I1 にテンプレIDを書き込む(GASが参照)
    try:
        admid = open(os.path.join(BASE, ".admin_sheet_id")).read().strip()
        sv.spreadsheets().values().update(spreadsheetId=admid, range="設定!H1",
            valueInputOption="RAW", body={"values": [["研修テンプレID", ssid]]}).execute()
    except Exception as e:
        print("admin 設定 write skip:", str(e)[:100])

    print("TRAINEE TEMPLATE:", ssid)
    print("URL: https://docs.google.com/spreadsheets/d/%s/edit" % ssid)
    print("modules in 進捗チェック:", n)


if __name__ == "__main__":
    main()
