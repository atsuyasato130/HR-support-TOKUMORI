#!/usr/bin/env python3
"""
Tokumori新卒研修 管理者ダッシュボード（充実版）。
- 2Dレイアウト: 全幅タイトル/6枚KPIヒーロー/左右ペア(要強化モジュール×進捗ランキング)/要フォロー/埋め込み棒グラフ。
- タブ: 管理ダッシュボード / 受講者名簿 / 進捗・成績 / モジュール別集計 / 結果ログ / 設定
- 既存 .admin_sheet_id があれば再利用(URL維持)。GAS(gas_admin_v1.js)がForms回答→集計を自動更新。
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
REDD = {"red": 0.478, "green": 0.129, "blue": 0.110}
INK = {"red": 0.11, "green": 0.11, "blue": 0.11}
WHITE = {"red": 1, "green": 1, "blue": 1}
PANEL = {"red": 0.980, "green": 0.972, "blue": 0.968}
LRED = {"red": 0.965, "green": 0.925, "blue": 0.917}
RULE = {"red": 0.886, "green": 0.878, "blue": 0.871}
SUB = {"red": 0.42, "green": 0.42, "blue": 0.42}

import importlib.util
spec = importlib.util.spec_from_file_location("bs", os.path.join(BASE, "build_slides.py"))
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)
DECK_NAME = {mid: name for mid, (t, fn, name) in bs.DECKS.items()}
EXTRA = {"F2": "業界・職種理解", "C3": "スプレッドシート関数"}
CATNAME = {"A": "自社・マインド", "B": "ビジネス基礎", "C": "PC・ツール", "D": "思考・分析", "E": "自己・対人", "F": "CA職種特化", "G": "リスク・コンプラ"}
TABS = ["管理ダッシュボード", "受講者名簿", "進捗・成績", "受講者カルテ", "1on1・コンディション", "モジュール別集計", "設問別分析", "WBS進捗", "結果ログ", "設定"]


def cat_of(mid):
    return mid[0]


def main():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    sv = build("sheets", "v4", credentials=c)
    forms = build("forms", "v1", credentials=c)
    fmap = json.load(open(os.path.join(BASE, ".forms_map.json"), encoding="utf-8"))

    idf = os.path.join(BASE, ".admin_sheet_id")
    ssid = open(idf).read().strip() if os.path.exists(idf) else None
    if ssid:
        meta = sv.spreadsheets().get(spreadsheetId=ssid).execute()
        # 既存タブを一旦最小化：必要タブを確保しつつ余剰削除
        cur = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
        reqs = []
        # 足りないタブを追加
        for t in TABS:
            if t not in cur:
                reqs.append({"addSheet": {"properties": {"title": t}}})
        if reqs:
            sv.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()
            meta = sv.spreadsheets().get(spreadsheetId=ssid).execute()
            cur = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
        # 余剰タブ削除
        delr = [{"deleteSheet": {"sheetId": cur[t]}} for t in cur if t not in TABS]
        if delr:
            sv.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": delr}).execute()
            meta = sv.spreadsheets().get(spreadsheetId=ssid).execute()
        sid = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    else:
        body = {"properties": {"title": "Tokumori新卒研修 管理ダッシュボード"},
                "sheets": [{"properties": {"title": t}} for t in TABS]}
        ss = sv.spreadsheets().create(body=body).execute()
        ssid = ss["spreadsheetId"]
        sid = {s["properties"]["title"]: s["properties"]["sheetId"] for s in ss["sheets"]}
        open(idf, "w").write(ssid)

    # ===== 値の投入 =====
    set_rows = [["モジュールID", "モジュール名", "カテゴリ", "満点", "合格点", "FormID", "Form回答URL"]]
    for mid, fid in fmap.items():
        name = DECK_NAME.get(mid) or EXTRA.get(mid, mid)
        try:
            uri = forms.forms().get(formId=fid).execute().get("responderUri", "")
        except Exception:
            uri = "https://docs.google.com/forms/d/%s/viewform" % fid
        set_rows.append([mid, name, CATNAME.get(cat_of(mid), ""), 100, 90, fid, uri])

    roster = [["No", "氏名", "メールアドレス", "配属/チーム", "開始日", "研修シートURL", "ステータス"]]
    # 既存の登録（氏名 or メールが入っている行）は再ビルドで消さずに保持する
    existing = []
    try:
        cur_ros = sv.spreadsheets().values().get(
            spreadsheetId=ssid, range="受講者名簿!A2:G").execute().get("values", [])
        for rr in cur_ros:
            nm = (rr[1] if len(rr) > 1 else "").strip()
            ml = (rr[2] if len(rr) > 2 else "").strip()
            if nm or ml:
                existing.append((list(rr) + [""] * 7)[:7])
    except Exception:
        existing = []
    for i, rr in enumerate(existing):
        rr[0] = i + 1
        roster.append(rr)
    for i in range(len(existing) + 1, max(31, len(existing) + 6)):
        roster.append([i, "", "", "", "", "", "未開始"])

    prog = [["氏名", "メールアドレス", "進捗率", "受験数", "合格数", "平均点", "最終提出日", "未合格モジュール", "遅延"]]
    modagg = [["モジュールID", "モジュール名", "カテゴリ", "受験者数", "合格者数", "合格率", "平均点"]]
    logs = [["提出日時", "メールアドレス", "氏名", "モジュールID", "モジュール名", "点数", "満点", "合否"]]
    qana = [["モジュールID", "モジュール名", "設問", "正答率", "回答数"]]
    onen = [["日付", "受講者", "メールアドレス", "モチベ(1-5)", "コンディション", "面談メモ", "次アクション"]]
    wbsp = [["氏名", "メールアドレス", "全体WBS%", "Stage1%", "Stage2%", "Stage3%", "完了モジュール", "着手中", "最終更新"]]

    def put(tab, rows, a="A1"):
        sv.spreadsheets().values().update(spreadsheetId=ssid, range="%s!%s" % (tab, a),
            valueInputOption="USER_ENTERED", body={"values": rows}).execute()

    # ダッシュボードの値（KPI・セクション・QUERY）
    NMOD = len(fmap)
    dash = [["" for _ in range(13)] for _ in range(26)]
    dash[0][1] = "Tokumori 新卒研修　管理ダッシュボード"
    dash[1][1] = "①『受講者名簿』に氏名・メールを入力 → 個別研修シートを生成（管理者＋本人のみ・本人=編集可）　②テストの点数/進捗/弱点はフォーム回答からこのSSへ自動集計（誰が何点かは『結果ログ』、個人の詳細は『受講者カルテ』で確認）"
    # KPIカード（ラベル行=2, 数値行=3）
    kpis = [
        ("受講者数", '=COUNTIF(受講者名簿!C2:C,"?*")'),
        ("修了者数", '=COUNTIF(受講者名簿!G2:G,"修了")'),
        ("平均進捗率", '=IFERROR(AVERAGE(進捗・成績!C2:C),0)'),
        ("平均点", '=IFERROR(ROUND(AVERAGE(進捗・成績!F2:F),1),0)'),
        ("ﾓｼﾞｭｰﾙ合格率", '=IFERROR(COUNTIF(結果ログ!H2:H,"合格")/COUNTA(結果ログ!H2:H),0)'),
        ("要フォロー", '=COUNTIF(進捗・成績!C2:C,"<0.5")+COUNTIF(進捗・成績!I2:I,"⚠ 遅延")'),
    ]
    for i, (lab, f) in enumerate(kpis):
        col = 1 + i * 2
        dash[2][col] = lab
        dash[3][col] = f
    dash[5][1] = "■ 要強化モジュール（合格率が低い順）"
    dash[5][7] = "■ 進捗ランキング（上位）"
    dash[6][1] = "モジュール"; dash[6][3] = "合格率"; dash[6][4] = "平均点"
    dash[6][7] = "氏名"; dash[6][9] = "進捗率"; dash[6][11] = "平均点"
    dash[7][1] = '=IFERROR(QUERY(モジュール別集計!B2:G,"select B,F,G where D>0 order by F asc limit 6",0),"（集計待ち）")'
    dash[7][7] = '=IFERROR(QUERY(進捗・成績!A2:F,"select A,C,F where B is not null order by C desc limit 8",0),"（集計待ち）")'
    dash[16][1] = "■ 要フォロー（進捗率50%未満 または 遅延）"
    dash[17][1] = "氏名"; dash[17][3] = "進捗率"; dash[17][5] = "未合格モジュール"
    dash[18][1] = '=IFERROR(QUERY(進捗・成績!A2:I,"select A,C,H where (C<0.5 or I=\'⚠ 遅延\') and B is not null order by C asc limit 12",0),"（集計待ち / 要フォローなし）")'

    # ===== 受講者カルテ（個人ドリルダウン）=====
    karte = [["" for _ in range(11)] for _ in range(40)]
    karte[0][1] = "受講者カルテ（個人ドリルダウン）"
    karte[2][1] = "受講者を選択 →"; karte[2][4] = "想定完了日数"; karte[2][5] = 90
    S = [
        (4, "氏名", "=C3"),
        (5, "メール", '=IFERROR(VLOOKUP(C3,受講者名簿!B:C,2,0),"")'),
        (6, "開始日", '=IFERROR(VLOOKUP(C3,受講者名簿!B:G,4,0),"")'),
        (7, "ステータス", '=IFERROR(VLOOKUP(C3,受講者名簿!B:G,6,0),"")'),
        (8, "進捗率", '=IFERROR(VLOOKUP(C6,進捗・成績!B:I,2,0),0)'),
        (9, "受験/合格", '=IFERROR(VLOOKUP(C6,進捗・成績!B:I,3,0)&" 受験 / "&VLOOKUP(C6,進捗・成績!B:I,4,0)&" 合格","")'),
        (10, "平均点", '=IFERROR(VLOOKUP(C6,進捗・成績!B:I,5,0),0)'),
        (11, "経過日数", '=IF(C7="","",TODAY()-C7)'),
        (12, "想定進捗", '=IF(C12="","",MIN(1,C12/$F$3))'),
        (13, "遅延判定", '=IF(C6="","",IF(N(C9)<N(C13)-0.15,"⚠ 遅延気味","OK"))'),
        (14, "最新モチベ(1-5)", '=IFERROR(QUERY(\'1on1・コンディション\'!A2:G,"select D where C=\'"&C6&"\' order by A desc limit 1",0),"未記録")'),
        (15, "弱点(未合格)", '=IFERROR(VLOOKUP(C6,進捗・成績!B:I,7,0),"")'),
    ]
    for r, lab, f in S:
        karte[r][1] = lab; karte[r][2] = f
    karte[17][1] = "■ テスト履歴（新しい順）"
    karte[18][1] = "提出日時"; karte[18][2] = "モジュール"; karte[18][3] = "点数"; karte[18][4] = "合否"
    karte[19][1] = '=IFERROR(QUERY(結果ログ!A2:H,"select A,E,F,H where B=\'"&C6&"\' order by A desc",0),"（回答なし／集計待ち）")'
    karte[2][7] = "■ コンディション・モチベーション履歴（1on1）"
    karte[3][7] = "日付"; karte[3][8] = "モチベ"; karte[3][9] = "状態"; karte[3][10] = "メモ"
    karte[4][7] = '=IFERROR(QUERY(\'1on1・コンディション\'!A2:G,"select A,D,E,F where C=\'"&C6&"\' order by A desc",0),"（1on1記録なし）")'

    # ===== 設問別分析 ＋ カテゴリ別合格率 =====
    qana = [["モジュールID", "モジュール名", "設問", "正答率", "回答数", "", "カテゴリ別 合格率", ""]]
    qana.append(["", "", "", "", "", "", "カテゴリ", "合格率"])
    qana.append(["", "", "", "", "", "", '=IFERROR(QUERY(モジュール別集計!C2:F,"select C, avg(F) where D>0 group by C label avg(F) \'\'",0),"（集計待ち）")', ""])

    put("設定", set_rows)
    put("受講者名簿", roster)
    put("進捗・成績", prog)
    put("受講者カルテ", karte)
    put("1on1・コンディション", onen)
    put("モジュール別集計", modagg)
    put("設問別分析", qana)
    put("WBS進捗", wbsp)
    put("結果ログ", logs)
    put("管理ダッシュボード", dash)

    # ===== 体裁 =====
    reqs = []
    # クリーンアップ先行: 既存の結合を解除（再利用SSの結合競合を防ぐ）
    for t in TABS:
        reqs.append({"unmergeCells": {"range": {"sheetId": sid[t], "startRowIndex": 0, "endRowIndex": 40, "startColumnIndex": 0, "endColumnIndex": 16}}})

    def band(tab, r, ncols, color=RED, fg=WHITE, size=10, bold=True):
        reqs.append({"repeatCell": {"range": {"sheetId": sid[tab], "startRowIndex": r, "endRowIndex": r + 1, "startColumnIndex": 0, "endColumnIndex": ncols},
            "cell": {"userEnteredFormat": {"backgroundColor": color, "textFormat": {"foregroundColor": fg, "bold": bold, "fontSize": size}, "verticalAlignment": "MIDDLE"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"}})

    def box(tab, r0, r1, c0, c1, color=None):
        rng = {"sheetId": sid[tab], "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}
        st = {"style": "SOLID", "width": 1, "color": RULE}
        reqs.append({"updateBorders": {"range": rng, "top": st, "bottom": st, "left": st, "right": st, "innerHorizontal": st, "innerVertical": st}})
        if color:
            reqs.append({"repeatCell": {"range": rng, "cell": {"userEnteredFormat": {"backgroundColor": color}}, "fields": "userEnteredFormat.backgroundColor"}})

    def merge(tab, r0, r1, c0, c1):
        reqs.append({"mergeCells": {"range": {"sheetId": sid[tab], "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}, "mergeType": "MERGE_ALL"}})

    def fmt(tab, r0, r1, c0, c1, f):
        reqs.append({"repeatCell": {"range": {"sheetId": sid[tab], "startRowIndex": r0, "endRowIndex": r1, "startColumnIndex": c0, "endColumnIndex": c1}, "cell": {"userEnteredFormat": f}, "fields": "userEnteredFormat"}})

    # ヘッダ赤帯（各表）
    band("設定", 0, 7); band("受講者名簿", 0, 7); band("進捗・成績", 0, 8); band("モジュール別集計", 0, 7); band("結果ログ", 0, 8)
    for t in TABS:
        reqs.append({"updateSheetProperties": {"properties": {"sheetId": sid[t], "gridProperties": {"hideGridlines": True, "frozenRowCount": (0 if t == "管理ダッシュボード" else 1)}}, "fields": "gridProperties.hideGridlines,gridProperties.frozenRowCount"}})

    D = "管理ダッシュボード"
    # タイトル
    merge(D, 0, 1, 1, 13)
    fmt(D, 0, 1, 1, 13, {"backgroundColor": RED, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 16}, "verticalAlignment": "MIDDLE", "horizontalAlignment": "LEFT"})
    reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[D], "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 46}, "fields": "pixelSize"}})
    # ガイド行（行2）
    merge(D, 1, 2, 1, 13)
    fmt(D, 1, 2, 1, 13, {"backgroundColor": PANEL, "textFormat": {"foregroundColor": SUB, "fontSize": 9}, "verticalAlignment": "MIDDLE"})
    # KPIカード（6枚）: ラベル(行2)・数値(行3)を2列ずつ枠囲い
    for i in range(6):
        c0 = 1 + i * 2; c1 = c0 + 2
        merge(D, 2, 3, c0, c1); merge(D, 3, 5, c0, c1)
        box(D, 2, 5, c0, c1, PANEL)
        fmt(D, 2, 3, c0, c1, {"backgroundColor": REDD, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 9}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
        fmt(D, 3, 5, c0, c1, {"textFormat": {"foregroundColor": RED, "bold": True, "fontSize": 22}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
    reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[D], "dimension": "ROWS", "startIndex": 3, "endIndex": 5}, "properties": {"pixelSize": 26}, "fields": "pixelSize"}})
    # ％表示（平均進捗率=card3, 合格率=card5）
    fmt(D, 3, 5, 5, 7, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}, "textFormat": {"foregroundColor": RED, "bold": True, "fontSize": 22}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
    fmt(D, 3, 5, 9, 11, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}, "textFormat": {"foregroundColor": RED, "bold": True, "fontSize": 22}, "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"})
    # セクション見出し
    for (r, c0, c1, label) in [(5, 1, 6, None), (5, 7, 13, None), (16, 1, 13, None)]:
        merge(D, r, r + 1, c0, c1)
        fmt(D, r, r + 1, c0, c1, {"textFormat": {"foregroundColor": RED, "bold": True, "fontSize": 11}})
    # 小見出し行(6,17)
    for (r, cols) in [(6, [1, 3, 4, 7, 9, 11]), (17, [1, 3, 5])]:
        fmt(D, r, r + 1, 1, 13, {"backgroundColor": LRED, "textFormat": {"bold": True, "fontSize": 9, "foregroundColor": INK}})
    # 表の枠
    box(D, 6, 15, 1, 6); box(D, 6, 15, 7, 13); box(D, 17, 25, 1, 13)
    # 進捗率列%（QUERY出力 C列=列9 of dash → dashboard col index 9? QUERY配置: 左表 合格率 at col3(D), 右表 進捗率 at col9(J)）
    fmt(D, 7, 15, 3, 4, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt(D, 7, 15, 9, 10, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt(D, 18, 25, 3, 4, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    # 列幅（ダッシュボード）
    widths = [30, 150, 30, 90, 90, 60, 30, 150, 30, 90, 70, 30, 60]
    for i, w in enumerate(widths):
        reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[D], "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})

    # 進捗・成績の％
    fmt("進捗・成績", 1, 400, 2, 3, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt("モジュール別集計", 1, 200, 5, 6, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})

    # 列幅（各表）
    def colw(tab, ws):
        for i, w in enumerate(ws):
            reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[tab], "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1}, "properties": {"pixelSize": w}, "fields": "pixelSize"}})
    colw("設定", [100, 220, 130, 50, 50, 250, 300])
    colw("受講者名簿", [36, 130, 240, 130, 95, 300, 86])
    colw("進捗・成績", [130, 240, 76, 64, 64, 70, 100, 360])
    colw("モジュール別集計", [100, 230, 130, 80, 80, 80, 80])
    colw("結果ログ", [150, 230, 120, 90, 200, 60, 56, 64])

    # フィルタ
    for tab, nc in [("結果ログ", 8), ("進捗・成績", 8), ("モジュール別集計", 7), ("受講者名簿", 7)]:
        reqs.append({"setBasicFilter": {"filter": {"range": {"sheetId": sid[tab], "startRowIndex": 0, "startColumnIndex": 0, "endColumnIndex": nc}}}})
    # ステータス プルダウン＋条件付き書式
    reqs.append({"setDataValidation": {"range": {"sheetId": sid["受講者名簿"], "startRowIndex": 1, "endRowIndex": 60, "startColumnIndex": 6, "endColumnIndex": 7},
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ["未開始", "受講中", "遅延", "修了"]]}, "showCustomUi": True}}})
    # 進捗・成績 進捗率に三色グラデ
    reqs.append({"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid["進捗・成績"], "startRowIndex": 1, "startColumnIndex": 2, "endColumnIndex": 3}],
        "gradientRule": {"minpoint": {"color": {"red": 0.96, "green": 0.80, "blue": 0.78}, "type": "NUMBER", "value": "0"},
                         "maxpoint": {"color": {"red": 0.70, "green": 0.85, "blue": 0.72}, "type": "NUMBER", "value": "1"}}}, "index": 0}})
    # 進捗・成績 遅延列に赤
    reqs.append({"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid["進捗・成績"], "startRowIndex": 1, "startColumnIndex": 8, "endColumnIndex": 9}],
        "booleanRule": {"condition": {"type": "TEXT_CONTAINS", "values": [{"userEnteredValue": "遅延"}]}, "format": {"backgroundColor": {"red": 0.96, "green": 0.80, "blue": 0.78}, "textFormat": {"bold": True, "foregroundColor": REDD}}}}, "index": 0}})

    # ===== 新タブ体裁 =====
    band("1on1・コンディション", 0, 7); band("設問別分析", 0, 5); band("WBS進捗", 0, 9)
    colw("1on1・コンディション", [100, 140, 240, 90, 130, 320, 240])
    colw("設問別分析", [90, 200, 380, 70, 70, 24, 150, 80])
    colw("受講者カルテ", [24, 130, 240, 90, 110, 90, 24, 110, 70, 100, 260])
    colw("WBS進捗", [150, 230, 90, 80, 80, 80, 110, 80, 150])
    fmt("WBS進捗", 1, 200, 2, 6, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})  # 全体/Stage% (C-F)
    # 1on1: 受講者・モチベ プルダウン＋低モチベ赤
    O = "1on1・コンディション"
    reqs.append({"setDataValidation": {"range": {"sheetId": sid[O], "startRowIndex": 1, "endRowIndex": 400, "startColumnIndex": 1, "endColumnIndex": 2},
        "rule": {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=受講者名簿!$B$2:$B$60"}]}, "showCustomUi": True}}})
    reqs.append({"setDataValidation": {"range": {"sheetId": sid[O], "startRowIndex": 1, "endRowIndex": 400, "startColumnIndex": 3, "endColumnIndex": 4},
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in ["1", "2", "3", "4", "5"]]}, "showCustomUi": True}}})
    reqs.append({"addConditionalFormatRule": {"rule": {"ranges": [{"sheetId": sid[O], "startRowIndex": 1, "startColumnIndex": 3, "endColumnIndex": 4}],
        "booleanRule": {"condition": {"type": "NUMBER_LESS_THAN_EQ", "values": [{"userEnteredValue": "2"}]}, "format": {"backgroundColor": {"red": 0.96, "green": 0.80, "blue": 0.78}}}}, "index": 0}})
    # 設問別分析: 正答率%・カテゴリ別見出し
    fmt("設問別分析", 1, 400, 3, 4, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt("設問別分析", 0, 1, 6, 8, {"backgroundColor": RED, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 10}})
    fmt("設問別分析", 1, 2, 6, 8, {"backgroundColor": LRED, "textFormat": {"bold": True}})
    fmt("設問別分析", 2, 30, 7, 8, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    # 受講者カルテ: タイトル帯・サマリー・履歴見出し・選択ドロップダウン
    K = "受講者カルテ"
    merge(K, 0, 1, 1, 11); fmt(K, 0, 1, 1, 11, {"backgroundColor": RED, "textFormat": {"foregroundColor": WHITE, "bold": True, "fontSize": 14}, "verticalAlignment": "MIDDLE"})
    reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid[K], "dimension": "ROWS", "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 40}, "fields": "pixelSize"}})
    fmt(K, 2, 3, 1, 2, {"textFormat": {"bold": True, "foregroundColor": RED}})
    fmt(K, 2, 3, 4, 5, {"textFormat": {"bold": True, "foregroundColor": INK}})
    fmt(K, 4, 16, 1, 2, {"backgroundColor": LRED, "textFormat": {"bold": True, "foregroundColor": INK, "fontSize": 9}})
    box(K, 4, 16, 1, 3)
    fmt(K, 8, 9, 2, 3, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt(K, 12, 13, 2, 3, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}})
    fmt(K, 17, 18, 1, 5, {"textFormat": {"bold": True, "foregroundColor": RED, "fontSize": 11}})
    fmt(K, 18, 19, 1, 5, {"backgroundColor": LRED, "textFormat": {"bold": True, "fontSize": 9}})
    fmt(K, 2, 3, 7, 11, {"textFormat": {"bold": True, "foregroundColor": RED, "fontSize": 11}})
    fmt(K, 3, 4, 7, 11, {"backgroundColor": LRED, "textFormat": {"bold": True, "fontSize": 9}})
    reqs.append({"setDataValidation": {"range": {"sheetId": sid[K], "startRowIndex": 2, "endRowIndex": 3, "startColumnIndex": 2, "endColumnIndex": 3},
        "rule": {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=受講者名簿!$B$2:$B$60"}]}, "showCustomUi": True}}})

    sv.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": reqs}).execute()

    # 埋め込みグラフ（カテゴリ別合格率 → モジュール別集計から作成は集計後。ここではモジュール別集計の合格率を棒グラフ化）
    try:
        chart = {"addChart": {"chart": {"spec": {"title": "モジュール別 合格率",
            "basicChart": {"chartType": "BAR", "legendPosition": "NO_LEGEND",
                "axis": [{"position": "BOTTOM_AXIS", "title": "合格率"}],
                "domains": [{"domain": {"sourceRange": {"sources": [{"sheetId": sid["モジュール別集計"], "startRowIndex": 0, "endRowIndex": 60, "startColumnIndex": 1, "endColumnIndex": 2}]}}}],
                "series": [{"series": {"sourceRange": {"sources": [{"sheetId": sid["モジュール別集計"], "startRowIndex": 0, "endRowIndex": 60, "startColumnIndex": 5, "endColumnIndex": 6}]}}}]}},
            "position": {"overlayPosition": {"anchorCell": {"sheetId": sid["管理ダッシュボード"], "rowIndex": 6, "columnIndex": 1}, "widthPixels": 740, "heightPixels": 280, "offsetXPixels": 0, "offsetYPixels": 0}}}}}
        # チャートはモジュール別集計タブ内に配置（ダッシュボードは表で密、グラフは集計タブ側に）
        chart["addChart"]["chart"]["position"] = {"overlayPosition": {"anchorCell": {"sheetId": sid["モジュール別集計"], "rowIndex": 1, "columnIndex": 8}, "widthPixels": 520, "heightPixels": 520}}
        sv.spreadsheets().batchUpdate(spreadsheetId=ssid, body={"requests": [chart]}).execute()
    except Exception as e:
        print("chart skip:", str(e)[:120])

    print("ADMIN SHEET (rich):", ssid)
    print("URL: https://docs.google.com/spreadsheets/d/%s/edit" % ssid)
    print("modules:", len(set_rows) - 1)


if __name__ == "__main__":
    main()
