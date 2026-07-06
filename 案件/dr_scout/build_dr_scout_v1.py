#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DR/スカウト管理シート（汎用テンプレ v1）を新規作成して構築する。

アーキテクチャ:
  設定マスタ → 媒体別タブ(候補者単位で入力) → マスター(全媒体を自動統合) → サマリー(一目で進捗)

- 媒体タブは全て同一フォーマット。媒体を追加したいときは _媒体テンプレ を複製して
  設定マスタ「媒体リスト」に1行足すだけ（GASメニューでワンクリック追加も可）。
- マスター/サマリーは数式駆動（GAS不要で日常利用可）。
- 再実行で冪等にしたい場合は SPREADSHEET_ID を固定して --rebuild で本文だけ再描画する。

正本: ~/Claude AI/build_dr_scout_v1.py
出力先: 新規スプレッドシート（既存【SAKIYOMI】DR管理シートには一切触れない）
ファネル: ListUp → 送付 → 返信 → 面談 → 採用
"""

import os
import sys
import json
import datetime as dt

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ───────────────────────── 認証 ─────────────────────────
CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
ID_CACHE = os.path.expanduser("~/Claude AI/.dr_scout_sheet_id")

TZ = dt.timezone(dt.timedelta(hours=9))  # JST
TODAY = dt.datetime.now(TZ).date()

TITLE = "DR/スカウト管理シート（テンプレ v1）"

# ───────────────────────── ブランドカラー（Tokumori方式: 深い赤 + 黒）──────
RED = {"red": 0.686, "green": 0.196, "blue": 0.173}        # #AF322C
RED_DK = {"red": 0.494, "green": 0.110, "blue": 0.094}     # 濃赤
INK = {"red": 0.16, "green": 0.16, "blue": 0.16}           # 黒に近い文字
WHITE = {"red": 1, "green": 1, "blue": 1}
PAPER = {"red": 0.99, "green": 0.985, "blue": 0.98}        # わずかに温かい白
ZEBRA = {"red": 0.965, "green": 0.957, "blue": 0.949}
HEAD_BG = {"red": 0.18, "green": 0.17, "blue": 0.16}       # 見出し帯（黒に近い）
PALE_RED = {"red": 0.965, "green": 0.918, "blue": 0.914}   # 淡赤（KPI枠）
SIG_GREEN = {"red": 0.851, "green": 0.937, "blue": 0.882}
SIG_AMBER = {"red": 0.996, "green": 0.929, "blue": 0.792}
SIG_RED = {"red": 0.984, "green": 0.847, "blue": 0.835}
GRID_BORDER = {"red": 0.85, "green": 0.84, "blue": 0.83}
BOX_BORDER = {"red": 0.35, "green": 0.33, "blue": 0.32}
GREY_TXT = {"red": 0.55, "green": 0.54, "blue": 0.53}
NOTE_BG = {"red": 0.97, "green": 0.965, "blue": 0.96}

FONT = "Arial"

# ───────────────────────── 構成定義 ─────────────────────────
# 媒体タブ（候補者単位ログ）の列。順序が全タブ/マスターで一致する。
MEDIA_HEADERS = [
    "候補者ID", "流入チャネル", "担当者", "候補者名", "プロフィールURL",
    "職種", "雇用形態希望", "意欲ステータス", "接点ステータス",
    "ListUp日", "送付日", "返信日", "面談調整日", "面談実施日", "採用日",
    "有効返信", "御礼連絡", "前日リマインド", "NG理由",
    "次アクション", "次アクション期日", "memo", "最終更新日",
]
NCOL_MEDIA = len(MEDIA_HEADERS)  # 23  (A..W)
MEDIA_ROWS = 500                 # 各媒体タブの行数（データは3行目以降）
DATA_START = 3                   # データ開始行（1-indexed）

# 媒体タブ内の列位置（0-indexed）
C_ID, C_CH, C_TANTO, C_NAME, C_URL = 0, 1, 2, 3, 4
C_SHOKU, C_KOYO, C_IYOKU, C_SETTEN = 5, 6, 7, 8
C_LISTUP, C_SOUFU, C_HENSHIN, C_CHOSEI, C_JISSHI, C_SAIYO = 9, 10, 11, 12, 13, 14
C_YUKO, C_OREI, C_REMIND, C_NG = 15, 16, 17, 18
C_NEXT, C_NEXTDUE, C_MEMO, C_UPD = 19, 20, 21, 22

DATE_COLS = [C_LISTUP, C_SOUFU, C_HENSHIN, C_CHOSEI, C_JISSHI, C_SAIYO, C_NEXTDUE, C_UPD]
CHECK_COLS = [C_YUKO, C_OREI, C_REMIND]

# 初期の媒体（媒体名, 略号, 主チャネル）
INITIAL_MEDIA = [
    ("YOUTRUST", "YT", "有料スカウト"),
    ("LinkedIn", "LI", "無料スカウト"),
]
TEMPLATE_TAB = "_媒体テンプレ"

# プルダウン候補（設定マスタの各列）
PULLDOWNS = {
    "流入チャネル": ["有料スカウト", "無料スカウト", "自己応募", "スカウト返信", "その他"],
    "担当者": ["田中", "岡見", "向"],
    "職種": ["エンジニア", "デザイナー", "PM・ディレクター", "マーケ", "セールス", "コーポレート", "その他"],
    "雇用形態希望": ["正社員", "副業", "業務委託", "インターン", "未確認"],
    "意欲ステータス": ["積極的に検討", "検討している", "良い案件があれば", "考えていない", "未確認"],
    "接点ステータス": ["未送付", "送付済", "返信あり", "面談調整中", "面談実施", "採用", "NG", "無反応"],
    "NG理由": ["辞退（他社決定）", "条件不一致", "興味なし", "連絡つかず", "副業のみ希望", "その他"],
}
PD_ORDER = ["流入チャネル", "担当者", "職種", "雇用形態希望", "意欲ステータス", "接点ステータス", "NG理由"]

# 設定マスタ レイアウト座標（1-indexed 行）――参照式で使うので固定する
MEDIA_LIST_HDR = 4      # 媒体リスト ヘッダ行
MEDIA_LIST_FIRST = 5    # 媒体リスト データ先頭行
MEDIA_LIST_SLOTS = 12   # 媒体スロット数（A5:A16）
MEDIA_LIST_LAST = MEDIA_LIST_FIRST + MEDIA_LIST_SLOTS - 1  # 16
PD_HDR = 19             # プルダウン ヘッダ行
PD_FIRST = 20           # プルダウン データ先頭行
PD_LAST = 40            # プルダウン データ末尾行（A20:G40）

# 設定（コントロール）
KIHATSU_ROW = 43        # 期初セル B43（この月から12ヶ月を通期とする）
GOALUSE_ROW = 44        # 目標を使う B44（はい/いいえ）

# 月次目標（全体・期初から12ヶ月）: A=月(date) B=ListUp C=送付 D=返信 E=面談 F=採用
GOAL_HDR = 47
GOAL_FIRST = 48
GOAL_MONTHS = 12
GOAL_LAST = GOAL_FIRST + GOAL_MONTHS - 1   # 59

SET_TAB = "03_設定マスタ"
SUM_TAB = "01_サマリー"
MST_TAB = "02_マスター"
README_TAB = "00_使い方"
DAILY_TAB = "04_日次入力"   # 集計方式=日次集計の媒体用（日付×媒体×職種でカウント手打ち）

# 日次入力タブ（集計方式=日次集計）の列。下流(返信/面談/採用)は空欄可＝max-DR企業向け。
DAILY_HEADERS = ["日付", "媒体", "職種", "担当者", "ListUp", "送付", "返信", "面談", "採用", "memo"]
NCOL_DAILY = len(DAILY_HEADERS)  # 10 (A..J)
DAILY_ROWS = 400                 # データは3行目以降
DC_DATE, DC_MEDIA, DC_SHOKU, DC_TANTO = 0, 1, 2, 3
DC_LISTUP, DC_SOUFU, DC_HENSHIN, DC_JISSHI, DC_SAIYO = 4, 5, 6, 7, 8
DC_MEMO = 9

# ステージ → (マスター日付列, 日次入力カウント列)。
# マスター=媒体A＋候補者列(B..)で候補者列index+1。日次入力は DC_* 準拠。
#   ListUp: master K / daily E   送付: L / F   返信: M / G   面談(実施): O / H   採用: P / I
STAGE_DEFS = [
    ("ListUp", "K", "E"),
    ("送付", "L", "F"),
    ("返信", "M", "G"),
    ("面談", "O", "H"),
    ("採用", "P", "I"),
]
# マスター上の絞り込み列（媒体A＋候補者列+1シフト）
MST_COL_MEDIA = "A"
MST_COL_TANTO = "D"   # 担当者
MST_COL_SHOKU = "G"   # 職種
# 日次入力上の絞り込み列
DLY_COL_DATE = "A"
DLY_COL_MEDIA = "B"
DLY_COL_SHOKU = "C"
DLY_COL_TANTO = "D"

# サマリー 媒体スロット
SUM_MEDIA_SLOTS = MEDIA_LIST_SLOTS
SUM_SHOKU = list(PULLDOWNS["職種"])      # 職種別/媒体×職種で使う職種一覧
SUM_NROWS = 180         # サマリーの高さ（全体↑＋月別↓で縦に伸びる）
SUM_NCOLS = 36          # 全体ブロック/日次グリッドを収める幅


# ───────────────────────── ユーティリティ ─────────────────────────
def col_a1(idx0):
    """0-indexed 列番号 → A1 列文字。"""
    s = ""
    n = idx0 + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


class Grid:
    """値と書式リクエストを蓄積するレイアウトビルダー（1タブ分）。"""

    def __init__(self, sheet_id, n_rows, n_cols):
        self.sid = sheet_id
        self.nrows = n_rows
        self.ncols = n_cols
        self.vals = [["" for _ in range(n_cols)] for _ in range(n_rows)]
        self.reqs = []

    def put(self, r, c, v):
        self.vals[r][c] = "" if v is None else v

    def row(self, r, c, items):
        for i, v in enumerate(items):
            self.put(r, c + i, v)

    def _rng(self, r0, c0, r1, c1):
        return {"sheetId": self.sid, "startRowIndex": r0, "endRowIndex": r1,
                "startColumnIndex": c0, "endColumnIndex": c1}

    def merge(self, r0, c0, r1, c1):
        self.reqs.append({"mergeCells": {"range": self._rng(r0, c0, r1, c1),
                                         "mergeType": "MERGE_ALL"}})

    def fmt(self, r0, c0, r1, c1, bg=None, fg=None, bold=False, size=None,
            halign=None, valign="MIDDLE", numfmt=None, wrap=None, italic=False):
        cf = {}
        tf = {"foregroundColor": fg or INK, "bold": bold,
              "fontFamily": FONT, "italic": italic}
        if size:
            tf["fontSize"] = size
        cf["textFormat"] = tf
        if bg is not None:
            cf["backgroundColor"] = bg
        if halign:
            cf["horizontalAlignment"] = halign
        cf["verticalAlignment"] = valign
        if wrap:
            cf["wrapStrategy"] = wrap
        if numfmt:
            cf["numberFormat"] = numfmt
        fields = "userEnteredFormat(textFormat,verticalAlignment"
        fields += ",backgroundColor" if bg is not None else ""
        fields += ",horizontalAlignment" if halign else ""
        fields += ",wrapStrategy" if wrap else ""
        fields += ",numberFormat" if numfmt else ""
        fields += ")"
        self.reqs.append({"repeatCell": {
            "range": self._rng(r0, c0, r1, c1),
            "cell": {"userEnteredFormat": cf},
            "fields": fields,
        }})

    def border(self, r0, c0, r1, c1, color=None, outer=True, inner=False):
        color = color or BOX_BORDER
        b = {"style": "SOLID", "color": color}
        req = {"updateBorders": {"range": self._rng(r0, c0, r1, c1)}}
        if outer:
            req["updateBorders"].update({"top": b, "bottom": b, "left": b, "right": b})
        if inner:
            ib = {"style": "SOLID", "color": GRID_BORDER}
            req["updateBorders"].update({"innerHorizontal": ib, "innerVertical": ib})
        self.reqs.append(req)

    def colwidth(self, c0, c1, px):
        self.reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": self.sid, "dimension": "COLUMNS",
                      "startIndex": c0, "endIndex": c1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})

    def rowheight(self, r0, r1, px):
        self.reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": self.sid, "dimension": "ROWS",
                      "startIndex": r0, "endIndex": r1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})

    def validation_range(self, r0, c0, r1, c1, src_a1, strict=True):
        self.reqs.append({"setDataValidation": {
            "range": self._rng(r0, c0, r1, c1),
            "rule": {
                "condition": {"type": "ONE_OF_RANGE",
                              "values": [{"userEnteredValue": "=" + src_a1}]},
                "strict": strict, "showCustomUi": True}}})

    def checkbox(self, r0, c0, r1, c1):
        self.reqs.append({"setDataValidation": {
            "range": self._rng(r0, c0, r1, c1),
            "rule": {"condition": {"type": "BOOLEAN"}, "showCustomUi": True}}})


# 数値/パーセントの表示形式
NF_PCT = {"type": "PERCENT", "pattern": "0.0%"}
NF_PCT0 = {"type": "PERCENT", "pattern": "0%"}
NF_INT = {"type": "NUMBER", "pattern": "#,##0"}
NF_DATE = {"type": "DATE", "pattern": "yyyy/mm/dd"}


# ───────────────────────── スプレッドシート作成/タブ準備 ─────────────────
def create_spreadsheet(svc):
    body = {"properties": {"title": TITLE, "locale": "ja_JP",
                           "timeZone": "Asia/Tokyo"}}
    ss = svc.spreadsheets().create(body=body, fields="spreadsheetId,sheets.properties").execute()
    sid = ss["spreadsheetId"]
    default_sheet_id = ss["sheets"][0]["properties"]["sheetId"]
    return sid, default_sheet_id


def add_tabs(svc, sid, media_names):
    """全タブを作成し、title→sheetId を返す。"""
    reqs = []
    specs = [
        (README_TAB, 60, 12, False),
        (SUM_TAB, SUM_NROWS, SUM_NCOLS, True),
        (MST_TAB, MEDIA_ROWS * (len(media_names) + 1) + 50, NCOL_MEDIA + 1, True),
        (SET_TAB, 70, 10, False),
        (DAILY_TAB, DAILY_ROWS, NCOL_DAILY, True),
    ]
    for name in media_names:
        specs.append((name, MEDIA_ROWS, NCOL_MEDIA, False))
    specs.append((TEMPLATE_TAB, MEDIA_ROWS, NCOL_MEDIA, False))

    for name, rows, cols, hide_grid in specs:
        gp = {"rowCount": rows, "columnCount": cols}
        if hide_grid:
            gp["hideGridlines"] = True
        if name == TEMPLATE_TAB:
            hidden = True
        else:
            hidden = False
        props = {"title": name, "gridProperties": gp, "hidden": hidden}
        reqs.append({"addSheet": {"properties": props}})

    res = svc.spreadsheets().batchUpdate(
        spreadsheetId=sid, body={"requests": reqs}).execute()
    title2id = {}
    for r in res["replies"]:
        p = r["addSheet"]["properties"]
        title2id[p["title"]] = p["sheetId"]
    return title2id


# ───────────────────────── 設定マスタ ─────────────────────────
def build_settei(sid):
    g = Grid(sid, 70, 10)
    g.put(0, 0, "設定マスタ｜媒体・プルダウン・月次目標")
    g.merge(0, 0, 1, 8)
    g.fmt(0, 0, 1, 8, bg=RED, fg=WHITE, bold=True, size=13, halign="LEFT")
    g.rowheight(0, 1, 34)

    g.put(1, 0, "媒体を追加したら 媒体リストに1行（集計方式＝個別/日次集計を選択）＋月次目標に1行。GASメニュー『媒体を追加』でも可")
    g.merge(1, 0, 2, 8)
    g.fmt(1, 0, 2, 8, fg=GREY_TXT, italic=True, size=9, halign="LEFT")

    # ── 媒体リスト
    r = MEDIA_LIST_HDR - 2  # section title row (0-indexed) = row before header
    g.put(r, 0, "■ 媒体リスト")
    g.fmt(r, 0, r + 1, 8, fg=RED_DK, bold=True, size=11)
    head = ["媒体名", "略号", "主チャネル", "状態", "集計方式", "アカウント", "URL", "memo"]
    hr = MEDIA_LIST_HDR - 1  # 0-indexed header row
    g.row(hr, 0, head)
    g.fmt(hr, 0, hr + 1, len(head), bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER")
    for i, (name, abbr, ch) in enumerate(INITIAL_MEDIA):
        rr = hr + 1 + i
        # 媒体名/略号/主チャネル/状態/集計方式/アカウント/URL/memo
        g.row(rr, 0, [name, abbr, ch, "利用中", "個別", "", "", ""])
    # 空スロットを罫線で
    g.border(hr, 0, hr + 1 + MEDIA_LIST_SLOTS, len(head), inner=True)
    for i in range(MEDIA_LIST_SLOTS):
        rr = hr + 1 + i
        g.fmt(rr, 0, rr + 1, len(head),
              bg=(ZEBRA if i % 2 else PAPER), size=10, halign="LEFT")
    # 状態のプルダウン（D列＝index 3）
    g.validation_range(hr + 1, 3, hr + 1 + MEDIA_LIST_SLOTS, 4,
                       f"{q(SET_TAB)}!$J$5:$J$8", strict=False)
    # 集計方式のプルダウン（E列＝index 4）
    g.validation_range(hr + 1, 4, hr + 1 + MEDIA_LIST_SLOTS, 5,
                       f"{q(SET_TAB)}!$J$11:$J$12", strict=False)

    # ── プルダウン値
    r = PD_HDR - 2
    g.put(r, 0, "■ プルダウン値（各列が候補リスト・ここに足すと媒体タブの選択肢が増える）")
    g.fmt(r, 0, r + 1, 8, fg=RED_DK, bold=True, size=11)
    hr = PD_HDR - 1
    g.row(hr, 0, PD_ORDER)
    g.fmt(hr, 0, hr + 1, len(PD_ORDER), bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER")
    for ci, key in enumerate(PD_ORDER):
        for vi, val in enumerate(PULLDOWNS[key]):
            g.put(hr + 1 + vi, ci, val)
    nrows_pd = PD_LAST - PD_FIRST + 1
    g.border(hr, 0, hr + 1 + nrows_pd, len(PD_ORDER), inner=True)
    g.fmt(hr + 1, 0, hr + 1 + nrows_pd, len(PD_ORDER), size=10, halign="LEFT")

    # 媒体リストの「状態」候補（離れた列 J に置く）
    g.put(3, 9, "（状態候補）")
    g.fmt(3, 9, 4, 10, fg=GREY_TXT, size=8)
    for i, v in enumerate(["利用中", "停止中", "契約予定", "解約"]):
        g.put(4 + i, 9, v)
    g.fmt(4, 9, 8, 10, fg=GREY_TXT, size=9)
    # 「集計方式」候補（J11:J12）
    g.put(9, 9, "（集計方式候補）")
    g.fmt(9, 9, 10, 10, fg=GREY_TXT, size=8)
    for i, v in enumerate(["個別", "日次集計"]):
        g.put(10 + i, 9, v)
    g.fmt(10, 9, 12, 10, fg=GREY_TXT, size=9)

    # ── 設定（コントロール）
    r = KIHATSU_ROW - 2
    g.put(r, 0, "■ 設定")
    g.fmt(r, 0, r + 1, 8, fg=RED_DK, bold=True, size=11)
    NF_YM = {"type": "DATE", "pattern": "yyyy年m月"}
    kr = KIHATSU_ROW - 1
    g.put(kr, 0, "期初（この月から12ヶ月を通期とする）")
    g.merge(kr, 0, kr + 1, 1)
    g.fmt(kr, 0, kr + 1, 1, fg=WHITE, bg=RED_DK, bold=True, size=10, halign="LEFT")
    g.put(kr, 1, f"=DATE({TODAY.year},1,1)")
    g.fmt(kr, 1, kr + 1, 2, bg=PALE_RED, bold=True, size=11, halign="CENTER", numfmt=NF_YM)
    gr = GOALUSE_ROW - 1
    g.put(gr, 0, "目標を使う")
    g.merge(gr, 0, gr + 1, 1)
    g.fmt(gr, 0, gr + 1, 1, fg=WHITE, bg=RED_DK, bold=True, size=10, halign="LEFT")
    g.put(gr, 1, "はい")
    g.fmt(gr, 1, gr + 1, 2, bg=PALE_RED, bold=True, size=11, halign="CENTER")
    g.reqs.append({"setDataValidation": {
        "range": g._rng(gr, 1, gr + 1, 2),
        "rule": {"condition": {"type": "ONE_OF_LIST", "values": [
            {"userEnteredValue": "はい"}, {"userEnteredValue": "いいえ"}]},
            "strict": False, "showCustomUi": True}}})
    g.put(gr, 2, "（いいえ にするとサマリーの目標／達成率を非表示）")
    g.fmt(gr, 2, gr + 1, 7, fg=GREY_TXT, italic=True, size=9, halign="LEFT")

    # ── 月次目標（全体・期初から12ヶ月）
    r = GOAL_HDR - 2
    g.put(r, 0, "■ 月次目標（全体・期初から12ヶ月／月ラベルは自動）")
    g.fmt(r, 0, r + 1, 8, fg=RED_DK, bold=True, size=11)
    ghead = ["月", "ListUp", "送付", "返信", "面談", "採用"]
    hr = GOAL_HDR - 1
    g.row(hr, 0, ghead)
    g.fmt(hr, 0, hr + 1, len(ghead), bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER")
    kcell = f"$B${KIHATSU_ROW}"
    for i in range(GOAL_MONTHS):
        rr = hr + 1 + i
        g.put(rr, 0, f"=EDATE({kcell},{i})")
    # サンプル目標（先頭3ヶ月だけ／残りは手入力）
    sample = [[80, 250, 42, 14, 2], [80, 250, 42, 14, 2], [90, 270, 46, 16, 3]]
    for i, vals in enumerate(sample):
        g.row(hr + 1 + i, 1, vals)
    g.border(hr, 0, hr + 1 + GOAL_MONTHS, len(ghead), inner=True)
    for i in range(GOAL_MONTHS):
        rr = hr + 1 + i
        bg = ZEBRA if i % 2 else PAPER
        g.fmt(rr, 0, rr + 1, 1, bg=bg, size=10, halign="CENTER", numfmt=NF_YM)
        g.fmt(rr, 1, rr + 1, len(ghead), bg=bg, size=10, halign="CENTER", numfmt=NF_INT)

    g.colwidth(0, 1, 230)
    g.colwidth(1, 2, 70)
    g.colwidth(2, 8, 90)
    return g


def build_daily(sid):
    """日次入力タブ：集計方式＝『日次集計』の媒体用。日付×媒体×職種でカウントを手打ち。"""
    g = Grid(sid, DAILY_ROWS, NCOL_DAILY)
    g.put(0, 0, "日次入力｜集計方式＝『日次集計』の媒体用（日付×媒体×職種でカウントを手打ち・採用まで追わない企業向け）")
    g.merge(0, 0, 1, NCOL_DAILY)
    g.fmt(0, 0, 1, NCOL_DAILY, bg=RED, fg=WHITE, bold=True, size=12, halign="LEFT")
    g.rowheight(0, 1, 30)

    g.row(1, 0, DAILY_HEADERS)
    g.fmt(1, 0, 2, NCOL_DAILY, bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER", wrap="WRAP")
    g.rowheight(1, 2, 30)

    last = DAILY_ROWS
    g.fmt(2, 0, last, NCOL_DAILY, size=10, halign="CENTER", valign="MIDDLE")
    g.fmt(2, DC_DATE, last, DC_DATE + 1, numfmt=NF_DATE, halign="CENTER")
    g.fmt(2, DC_LISTUP, last, DC_SAIYO + 1, numfmt=NF_INT, halign="CENTER")
    g.fmt(2, DC_MEMO, last, DC_MEMO + 1, halign="LEFT")
    # ゼブラ（表示域だけ軽く）
    for r in range(2, min(last, 120)):
        if (r - 2) % 2:
            g.fmt(r, 0, r + 1, NCOL_DAILY, bg=ZEBRA)
    # プルダウン（設定マスタ参照）
    g.validation_range(2, DC_MEDIA, last, DC_MEDIA + 1,
                       f"{q(SET_TAB)}!$A${MEDIA_LIST_FIRST}:$A${MEDIA_LIST_LAST}", strict=False)
    g.validation_range(2, DC_SHOKU, last, DC_SHOKU + 1,
                       f"{q(SET_TAB)}!$C${PD_FIRST}:$C${PD_LAST}", strict=False)
    g.validation_range(2, DC_TANTO, last, DC_TANTO + 1,
                       f"{q(SET_TAB)}!$B${PD_FIRST}:$B${PD_LAST}", strict=False)
    # 罫線
    g.border(1, 0, min(last, 120), NCOL_DAILY, inner=True, color=GRID_BORDER)
    g.border(1, 0, 2, NCOL_DAILY, inner=False)
    # フリーズ（バナー＋ヘッダ）
    g.reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
        "fields": "gridProperties.frozenRowCount"}})
    # 列幅
    widths = {DC_DATE: 100, DC_MEDIA: 120, DC_SHOKU: 110, DC_TANTO: 80,
              DC_LISTUP: 78, DC_SOUFU: 78, DC_HENSHIN: 78, DC_JISSHI: 78, DC_SAIYO: 78,
              DC_MEMO: 220}
    for c, px in widths.items():
        g.colwidth(c, c + 1, px)
    return g


def q(name):
    """シート名を数式用にクォート。"""
    return "'" + name.replace("'", "''") + "'"


# ───────────────────────── 媒体タブ / テンプレ ─────────────────────────
def build_media_tab(sid, tab_name, abbr, channel):
    g = Grid(sid, MEDIA_ROWS, NCOL_MEDIA)
    # バナー（媒体名）
    g.put(0, 0, f"媒体：{tab_name}")
    g.merge(0, 0, 1, NCOL_MEDIA)
    g.fmt(0, 0, 1, NCOL_MEDIA, bg=RED, fg=WHITE, bold=True, size=12, halign="LEFT")
    g.rowheight(0, 1, 30)

    # ヘッダ（2行目）
    g.row(1, 0, MEDIA_HEADERS)
    g.fmt(1, 0, 2, NCOL_MEDIA, bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER", wrap="WRAP")
    g.rowheight(1, 2, 30)

    # 候補者ID（A3、候補者名が入った行だけ採番）
    g.put(2, C_ID,
          f'=ARRAYFORMULA(IF($D$3:$D="","","{abbr}-"&TEXT(ROW($D$3:$D)-2,"000")))')

    # 既定の流入チャネルを薄く表示（任意。空でも可）
    # データ域の書式
    last = MEDIA_ROWS
    g.fmt(2, 0, last, NCOL_MEDIA, size=10, halign="LEFT", valign="MIDDLE")
    g.fmt(2, C_ID, last, C_ID + 1, fg=GREY_TXT, size=9, halign="CENTER")
    # ゼブラ
    for r in range(2, min(last, 120)):  # 表示域だけ軽くゼブラ
        if (r - 2) % 2:
            g.fmt(r, 0, r + 1, NCOL_MEDIA, bg=ZEBRA)
    # 日付列フォーマット
    for c in DATE_COLS:
        g.fmt(2, c, last, c + 1, numfmt=NF_DATE, halign="CENTER")
    # チェックボックス
    for c in CHECK_COLS:
        g.checkbox(2, c, last, c + 1)
        g.fmt(2, c, last, c + 1, halign="CENTER")
    # プルダウン（設定マスタ参照）
    pd_col_map = {
        C_CH: "A", C_TANTO: "B", C_SHOKU: "C", C_KOYO: "D",
        C_IYOKU: "E", C_SETTEN: "F", C_NG: "G",
    }
    for c, col in pd_col_map.items():
        src = f"{q(SET_TAB)}!${col}${PD_FIRST}:${col}${PD_LAST}"
        g.validation_range(2, c, last, c + 1, src, strict=False)

    # 罫線（ヘッダ＋表示域）
    g.border(1, 0, min(last, 120), NCOL_MEDIA, inner=True, color=GRID_BORDER)
    g.border(1, 0, 2, NCOL_MEDIA, inner=False)

    # フリーズ（2行＝バナー+ヘッダ）。列固定はバナー結合と競合するため行のみ。
    g.reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"frozenRowCount": 2}},
        "fields": "gridProperties.frozenRowCount"}})

    # 列幅
    widths = {
        C_ID: 70, C_CH: 95, C_TANTO: 70, C_NAME: 120, C_URL: 170,
        C_SHOKU: 110, C_KOYO: 90, C_IYOKU: 110, C_SETTEN: 95,
        C_LISTUP: 90, C_SOUFU: 90, C_HENSHIN: 90, C_CHOSEI: 90, C_JISSHI: 90, C_SAIYO: 90,
        C_YUKO: 60, C_OREI: 60, C_REMIND: 80, C_NG: 130,
        C_NEXT: 140, C_NEXTDUE: 100, C_MEMO: 200, C_UPD: 100,
    }
    for c, px in widths.items():
        g.colwidth(c, c + 1, px)
    return g


# ───────────────────────── マスター ─────────────────────────
def master_union_formula(media_names):
    """全媒体タブを縦結合する数式（媒体名を1列目に付与）。"""
    blocks = []
    for name in media_names:
        qn = q(name)
        blocks.append(
            f'ARRAYFORMULA(IF({qn}!$A${DATA_START}:$A<>"","{name}","")),'
            f'{qn}!$A${DATA_START}:$W'
        )
    inner = "; ".join(blocks)
    return "={" + inner + "}"


def build_master(sid, media_names):
    ncol = NCOL_MEDIA + 1  # 媒体 + 23
    nrows = MEDIA_ROWS * (len(media_names) + 1) + 50
    g = Grid(sid, min(nrows, 8000), ncol)
    g.put(0, 0, "マスター（統合ログ）｜全媒体タブを自動結合・読取専用（編集は各媒体タブで）")
    g.merge(0, 0, 1, ncol)
    g.fmt(0, 0, 1, ncol, bg=INK, fg=WHITE, bold=True, size=12, halign="LEFT")
    g.rowheight(0, 1, 30)

    headers = ["媒体"] + MEDIA_HEADERS
    g.row(1, 0, headers)
    g.fmt(1, 0, 2, ncol, bg=HEAD_BG, fg=WHITE, bold=True, size=9,
          halign="CENTER", wrap="WRAP")
    g.rowheight(1, 2, 28)

    # 結合式（A3）
    g.put(2, 0, master_union_formula(media_names))

    # 日付列フォーマット（媒体列が増えるので+1シフト）
    for c in DATE_COLS:
        g.fmt(2, c + 1, min(nrows, 8000), c + 2, numfmt=NF_DATE, halign="CENTER")
    g.fmt(2, 0, min(nrows, 8000), ncol, size=9, valign="MIDDLE")
    g.fmt(2, 0, min(nrows, 8000), 1, bg=NOTE_BG, fg=RED_DK, bold=True,
          size=9, halign="CENTER")

    g.reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"frozenRowCount": 2}},
        "fields": "gridProperties.frozenRowCount"}})
    g.colwidth(0, 1, 90)
    g.colwidth(1, 2, 70)
    g.colwidth(4, 5, 120)
    return g


# ───────────────────────── サマリー ─────────────────────────
def build_summary(sid):
    """サマリー v2：上＝全体(通期累計)／下＝月別。媒体別・職種別・媒体×職種。
    全指標は二刀流合算 = COUNTIFS(マスター)+SUMIFS(日次入力)。"""
    NC = SUM_NCOLS
    g = Grid(sid, SUM_NROWS, NC)
    M = q(MST_TAB)
    SET = q(SET_TAB)
    D = q(DAILY_TAB)

    USE_GOAL = f'{SET}!$B${GOALUSE_ROW}="はい"'
    KIHATSU = f'{SET}!$B${KIHATSU_ROW}'
    NF_YM = {"type": "DATE", "pattern": "yyyy年m月"}
    NF_MH = {"type": "DATE", "pattern": "yy/m"}
    # 期間ヘルパセル（row2）: 対象月 AE/AF・全体 AG/AH
    MS, ME = "$AE$2", "$AF$2"     # 対象月 開始/終了
    AS, AZ = "$AG$2", "$AH$2"     # 全体(通期) 開始/終了
    STAGE_LABELS = [s[0] for s in STAGE_DEFS]
    SEL_ARR = '{"' + '";"'.join(STAGE_LABELS) + '"}'
    sel_holder = {"row": None}   # 媒体×職種マトリクスの指標セレクタ行（cross_matrixが設定）

    # ── 二刀流の合算プリミティブ（指定ステージ・期間・絞り込みのカウント）
    def cnt(si, start, end, media=None, shoku=None, tanto=None):
        _, sdc, dcc = STAGE_DEFS[si]
        mc = ""
        dc = ""
        if media is not None:
            mc += f',{M}!${MST_COL_MEDIA}:${MST_COL_MEDIA},{media}'
            dc += f',{D}!${DLY_COL_MEDIA}:${DLY_COL_MEDIA},{media}'
        if shoku is not None:
            mc += f',{M}!${MST_COL_SHOKU}:${MST_COL_SHOKU},{shoku}'
            dc += f',{D}!${DLY_COL_SHOKU}:${DLY_COL_SHOKU},{shoku}'
        if tanto is not None:
            mc += f',{M}!${MST_COL_TANTO}:${MST_COL_TANTO},{tanto}'
            dc += f',{D}!${DLY_COL_TANTO}:${DLY_COL_TANTO},{tanto}'
        master = (f'COUNTIFS({M}!${sdc}:${sdc},">="&{start},'
                  f'{M}!${sdc}:${sdc},"<="&{end}{mc})')
        daily = (f'SUMIFS({D}!${dcc}:${dcc},{D}!${DLY_COL_DATE}:${DLY_COL_DATE},">="&{start},'
                 f'{D}!${DLY_COL_DATE}:${DLY_COL_DATE},"<="&{end}{dc})')
        return f'({master}+{daily})'

    def choose(exprs):
        return f'CHOOSE(MATCH($I${sel_holder["row"]},{SEL_ARR},0),' + ",".join(exprs) + ')'

    # ── バナー
    g.put(0, 0, "サマリー｜DR/スカウト進捗（全媒体・個別／日次集計の二刀流対応）")
    g.merge(0, 0, 1, NC)
    g.fmt(0, 0, 1, NC, bg=RED, fg=WHITE, bold=True, size=14, halign="LEFT")
    g.rowheight(0, 1, 38)

    # ── コントロールバー（row2）
    g.put(1, 0, "対象月")
    g.fmt(1, 0, 2, 1, fg=WHITE, bg=RED_DK, bold=True, size=10, halign="CENTER")
    g.put(1, 1, f"=DATE({TODAY.year},{TODAY.month},1)")
    g.merge(1, 1, 2, 3)
    g.fmt(1, 1, 2, 3, bg=PALE_RED, bold=True, size=11, halign="CENTER", numfmt=NF_YM)
    g.put(1, 3, "目標表示")
    g.fmt(1, 3, 2, 4, fg=WHITE, bg=RED_DK, bold=True, size=10, halign="CENTER")
    g.put(1, 4, f'=IF({USE_GOAL},"ON","OFF")')
    g.merge(1, 4, 2, 5)
    g.fmt(1, 4, 2, 5, bg=PALE_RED, bold=True, size=11, halign="CENTER")
    g.put(1, 5, "（対象月は下段[月別]に連動・全体は通期12ヶ月の累計／目標は設定マスタ）")
    g.fmt(1, 5, 2, 28, fg=GREY_TXT, italic=True, size=9, halign="LEFT")
    # 期間ヘルパ
    g.put(1, 30, '=DATE(YEAR($B$2),MONTH($B$2),1)')
    g.put(1, 31, '=EOMONTH($B$2,0)')
    g.put(1, 32, f'={KIHATSU}')
    g.put(1, 33, f'=EOMONTH(EDATE({KIHATSU},11),0)')
    g.put(1, 29, "集計期間")
    g.fmt(1, 29, 2, 30, fg=GREY_TXT, size=8, halign="RIGHT")
    g.fmt(1, 30, 2, 34, fg=GREY_TXT, size=8, halign="CENTER",
          numfmt={"type": "DATE", "pattern": "m/d"})

    # ── KPIヒーロー（5箱：ListUp/送付/返信/面談/採用）
    def kpi_hero(R, start, end):
        prev = [None, 0, 1, 2, 3]
        rlbl = [None, "送付率", "返信率", "面談率", "採用率"]
        for i, label in enumerate(STAGE_LABELS):
            c0 = i * 4
            c1 = (i + 1) * 4
            g.put(R, c0, label)
            g.merge(R, c0, R + 1, c1)
            g.fmt(R, c0, R + 1, c1, bg=RED_DK, fg=WHITE, bold=True, size=11, halign="CENTER")
            g.put(R + 1, c0, "=" + cnt(i, start, end))
            g.merge(R + 1, c0, R + 3, c1)
            g.fmt(R + 1, c0, R + 3, c1, bg=PALE_RED, fg=RED_DK, bold=True, size=20,
                  halign="CENTER", numfmt=NF_INT)
            if i == 0:
                sub = '="（ファネル母数）"'
            else:
                num = cnt(i, start, end)
                den = cnt(prev[i], start, end)
                sub = (f'=IFERROR("{rlbl[i]} "&TEXT(({num})/({den}),"0.0%"),'
                       f'"{rlbl[i]} —")')
            g.put(R + 3, c0, sub)
            g.merge(R + 3, c0, R + 4, c1)
            g.fmt(R + 3, c0, R + 4, c1, bg=NOTE_BG, fg=GREY_TXT, size=9, halign="CENTER")
            g.border(R, c0, R + 4, c1, color=BOX_BORDER)
        g.rowheight(R + 1, R + 3, 40)
        return R + 4

    # ── ファネル表（行=媒体 or 職種）
    def funnel_table(R, title, ent_head, labels, dim, start, end):
        g.put(R, 0, title)
        g.fmt(R, 0, R + 1, 10, fg=RED_DK, bold=True, size=11)
        R += 1
        head = [ent_head, "ListUp", "送付", "返信", "面談", "採用",
                "送付率", "返信率", "面談率", "採用率"]
        hr = R
        g.row(hr, 0, head)
        g.fmt(hr, 0, hr + 1, len(head), bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER")
        R += 1
        first = R
        for i, label in enumerate(labels):
            rr = R
            g.put(rr, 0, label)
            ref = f"$A{rr+1}"
            for si in range(5):
                g.put(rr, 1 + si, f'=IF({ref}="","",{cnt(si, start, end, **{dim: ref})})')
            lu, sf, hn, js, sa = (f"$B{rr+1}", f"$C{rr+1}", f"$D{rr+1}", f"$E{rr+1}", f"$F{rr+1}")
            g.put(rr, 6, f'=IF(OR({ref}="",{lu}=0),"",{sf}/{lu})')
            g.put(rr, 7, f'=IF(OR({ref}="",{sf}=0),"",{hn}/{sf})')
            g.put(rr, 8, f'=IF(OR({ref}="",{hn}=0),"",{js}/{hn})')
            g.put(rr, 9, f'=IF(OR({ref}="",{js}=0),"",{sa}/{js})')
            bg = ZEBRA if i % 2 else PAPER
            g.fmt(rr, 0, rr + 1, 1, bg=bg, size=10, halign="LEFT", bold=True)
            g.fmt(rr, 1, rr + 1, 6, bg=bg, size=10, halign="CENTER", numfmt=NF_INT)
            g.fmt(rr, 6, rr + 1, 10, bg=bg, size=10, halign="CENTER", numfmt=NF_PCT0)
            R += 1
        tot = R
        g.put(tot, 0, "合計")
        for si in range(5):
            g.put(tot, 1 + si, "=" + cnt(si, start, end))
        g.put(tot, 6, f'=IF($B{tot+1}=0,"",$C{tot+1}/$B{tot+1})')
        g.put(tot, 7, f'=IF($C{tot+1}=0,"",$D{tot+1}/$C{tot+1})')
        g.put(tot, 8, f'=IF($D{tot+1}=0,"",$E{tot+1}/$D{tot+1})')
        g.put(tot, 9, f'=IF($E{tot+1}=0,"",$F{tot+1}/$E{tot+1})')
        g.fmt(tot, 0, tot + 1, 1, bg=INK, fg=WHITE, bold=True, size=10, halign="LEFT")
        g.fmt(tot, 1, tot + 1, 6, bg=PALE_RED, bold=True, size=10, halign="CENTER", numfmt=NF_INT)
        g.fmt(tot, 6, tot + 1, 10, bg=PALE_RED, bold=True, size=10, halign="CENTER", numfmt=NF_PCT0)
        g.border(hr, 0, tot + 1, len(head), inner=True, color=GRID_BORDER)
        g.border(hr, 0, tot + 1, len(head), inner=False)
        g.reqs.append(_cf_rel(sid, first, 6, tot, 10))
        return tot + 1

    # ── 媒体×職種マトリクス（指標セレクタ・全体）
    def cross_matrix(R, start, end):
        g.put(R, 0, "■ 媒体×職種（全体・指標を選択）")
        g.fmt(R, 0, R + 1, 7, fg=RED_DK, bold=True, size=11)
        g.put(R, 7, "指標→")
        g.fmt(R, 7, R + 1, 8, fg=GREY_TXT, size=9, halign="RIGHT")
        g.put(R, 8, "送付")
        g.fmt(R, 8, R + 1, 9, bg=PALE_RED, bold=True, size=10, halign="CENTER")
        g.reqs.append({"setDataValidation": {
            "range": g._rng(R, 8, R + 1, 9),
            "rule": {"condition": {"type": "ONE_OF_LIST",
                                   "values": [{"userEnteredValue": s} for s in STAGE_LABELS]},
                     "strict": True, "showCustomUi": True}}})
        sel_holder["row"] = R + 1   # 1-indexed row of $I selector
        R += 1
        shoku = SUM_SHOKU
        nsh = len(shoku)
        head = ["媒体＼職種"] + shoku + ["計"]
        hr = R
        g.row(hr, 0, head)
        g.fmt(hr, 0, hr + 1, len(head), bg=HEAD_BG, fg=WHITE, bold=True, size=8,
              halign="CENTER", wrap="WRAP")
        R += 1
        first = R
        for i in range(SUM_MEDIA_SLOTS):
            rr = R
            mlist = MEDIA_LIST_FIRST + i
            g.put(rr, 0, f'=IF({SET}!$A${mlist}="","",{SET}!$A${mlist})')
            mref = f"$A{rr+1}"
            for j in range(nsh):
                sref = f"{col_a1(1 + j)}${hr+1}"
                ex = choose([cnt(si, start, end, media=mref, shoku=sref) for si in range(5)])
                g.put(rr, 1 + j, f'=IF(OR({mref}="",{sref}=""),"",{ex})')
            cex = choose([cnt(si, start, end, media=mref) for si in range(5)])
            g.put(rr, 1 + nsh, f'=IF({mref}="","",{cex})')
            bg = ZEBRA if i % 2 else PAPER
            g.fmt(rr, 0, rr + 1, 1, bg=bg, size=10, halign="LEFT", bold=True)
            g.fmt(rr, 1, rr + 1, 1 + nsh, bg=bg, size=10, halign="CENTER", numfmt=NF_INT)
            g.fmt(rr, 1 + nsh, rr + 1, 2 + nsh, bg=PALE_RED, bold=True, size=10,
                  halign="CENTER", numfmt=NF_INT)
            R += 1
        tot = R
        g.put(tot, 0, "計")
        for j in range(nsh):
            sref = f"{col_a1(1 + j)}${hr+1}"
            g.put(tot, 1 + j, "=" + choose([cnt(si, start, end, shoku=sref) for si in range(5)]))
        g.put(tot, 1 + nsh, "=" + choose([cnt(si, start, end) for si in range(5)]))
        g.fmt(tot, 0, tot + 1, 1, bg=INK, fg=WHITE, bold=True, size=10, halign="LEFT")
        g.fmt(tot, 1, tot + 1, 2 + nsh, bg=PALE_RED, bold=True, size=10, halign="CENTER", numfmt=NF_INT)
        g.border(hr, 0, tot + 1, len(head), inner=True, color=GRID_BORDER)
        g.border(hr, 0, tot + 1, len(head), inner=False)
        g.reqs.append(_cf_rel(sid, first, 1, tot, 1 + nsh))
        return tot + 1

    # ── 担当者別
    def tanto_table(R, start, end):
        g.put(R, 0, "■ 担当者別（対象月）")
        g.fmt(R, 0, R + 1, 5, fg=RED_DK, bold=True, size=11)
        R += 1
        head = ["担当者", "送付", "面談", "採用", "返信率"]
        hr = R
        g.row(hr, 0, head)
        g.fmt(hr, 0, hr + 1, len(head), bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER")
        R += 1
        n = 8
        for i in range(n):
            rr = R
            src = PD_FIRST + i
            ref = f"$A{rr+1}"
            g.put(rr, 0, f'=IF({SET}!$B${src}="","",{SET}!$B${src})')
            g.put(rr, 1, f'=IF({ref}="","",{cnt(1, start, end, tanto=ref)})')
            g.put(rr, 2, f'=IF({ref}="","",{cnt(3, start, end, tanto=ref)})')
            g.put(rr, 3, f'=IF({ref}="","",{cnt(4, start, end, tanto=ref)})')
            g.put(rr, 4, f'=IF(OR({ref}="",$B{rr+1}=0),"",{cnt(2, start, end, tanto=ref)}/$B{rr+1})')
            bg = ZEBRA if i % 2 else PAPER
            g.fmt(rr, 0, rr + 1, 1, bg=bg, size=10, halign="LEFT")
            g.fmt(rr, 1, rr + 1, 4, bg=bg, size=10, halign="CENTER", numfmt=NF_INT)
            g.fmt(rr, 4, rr + 1, 5, bg=bg, size=10, halign="CENTER", numfmt=NF_PCT0)
            R += 1
        g.border(hr, 0, R, len(head), inner=True, color=GRID_BORDER)
        g.border(hr, 0, R, len(head), inner=False)
        return R + 1

    # ── 推移ブロック（行=ステージ＋歩留・列=期間）
    def trend_block(R, title, labels, periods, total_period):
        n = len(periods)
        g.put(R, 0, title)
        g.fmt(R, 0, R + 1, 8, fg=RED_DK, bold=True, size=11)
        R += 1
        hh = R
        g.put(hh, 0, "指標")
        g.put(hh, 1, "計")
        for pi, (lab, nf) in enumerate(labels):
            g.put(hh, 2 + pi, lab)
        g.fmt(hh, 0, hh + 1, 2 + n, bg=HEAD_BG, fg=WHITE, bold=True, size=8,
              halign="CENTER", wrap="WRAP")
        for pi, (lab, nf) in enumerate(labels):
            if nf:
                g.fmt(hh, 2 + pi, hh + 1, 3 + pi, bg=HEAD_BG, fg=WHITE, bold=True,
                      size=8, halign="CENTER", numfmt=nf)
        R += 1
        stage0 = R
        for si in range(5):
            rr = R
            g.put(rr, 0, STAGE_LABELS[si])
            g.put(rr, 1, "=" + cnt(si, total_period[0], total_period[1]))
            for pi, (st, en, guard) in enumerate(periods):
                expr = cnt(si, st, en)
                g.put(rr, 2 + pi, f'=IF({guard},"",{expr})' if guard else "=" + expr)
            g.fmt(rr, 0, rr + 1, 1, bg=PAPER, fg=INK, bold=True, size=9, halign="LEFT")
            g.fmt(rr, 1, rr + 1, 2, bg=PALE_RED, bold=True, size=9, halign="CENTER", numfmt=NF_INT)
            g.fmt(rr, 2, rr + 1, 2 + n, bg=(ZEBRA if si % 2 else PAPER),
                  size=9, halign="CENTER", numfmt=NF_INT)
            R += 1
        RATES = [("送付率", 1, 0), ("返信率", 2, 1), ("面談率", 3, 2), ("採用率", 4, 3)]
        for rl, ni, di in RATES:
            rr = R
            nrow = stage0 + ni + 1
            drow = stage0 + di + 1
            g.put(rr, 0, rl)
            g.put(rr, 1, f'=IFERROR(B{nrow}/B{drow},"")')
            for pi in range(n):
                cl = col_a1(2 + pi)
                g.put(rr, 2 + pi, f'=IFERROR({cl}{nrow}/{cl}{drow},"")')
            g.fmt(rr, 0, rr + 1, 1, bg=NOTE_BG, fg=GREY_TXT, italic=True, size=9, halign="LEFT")
            g.fmt(rr, 1, rr + 1, 2 + n, bg=NOTE_BG, fg=GREY_TXT, italic=True,
                  size=9, halign="CENTER", numfmt=NF_PCT0)
            R += 1
        g.border(hh, 0, R, 2 + n, inner=True, color=GRID_BORDER)
        g.border(hh, 0, R, 2 + n, inner=False)
        return R + 1

    # ── 月次 目標達成率（全体）
    def goal_table(R):
        g.put(R, 0, "■ 月次 目標達成率（全体）")
        g.fmt(R, 0, R + 1, 6, fg=RED_DK, bold=True, size=11)
        g.put(R, 7, '←「目標を使う＝いいえ」の時は空欄')
        g.fmt(R, 7, R + 1, 18, fg=GREY_TXT, italic=True, size=9, halign="LEFT")
        R += 1
        head = ["月", "ListUp", "送付", "返信", "面談", "採用"]
        hr = R
        g.row(hr, 0, head)
        g.fmt(hr, 0, hr + 1, len(head), bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER")
        R += 1
        GOAL_SETCOL = {"ListUp": "B", "送付": "C", "返信": "D", "面談": "E", "採用": "F"}
        for i in range(12):
            rr = R
            mcell = f"$A{rr+1}"
            g.put(rr, 0, f"=EDATE({KIHATSU},{i})")
            mstart = mcell
            mend = f"EOMONTH({mcell},0)"
            for ci, si in enumerate(range(5)):
                gc = GOAL_SETCOL[STAGE_LABELS[si]]
                grow = GOAL_FIRST + i
                actual = cnt(si, mstart, mend)
                tgt = f'{SET}!${gc}${grow}'
                g.put(rr, 1 + ci,
                      f'=IF(OR(NOT({USE_GOAL}),{tgt}="",{tgt}=0),"",IFERROR(({actual})/({tgt}),""))')
            bg = ZEBRA if i % 2 else PAPER
            g.fmt(rr, 0, rr + 1, 1, bg=bg, size=10, halign="CENTER", numfmt=NF_YM)
            g.fmt(rr, 1, rr + 1, len(head), bg=bg, size=10, halign="CENTER", numfmt=NF_PCT0)
            R += 1
        g.border(hr, 0, R, len(head), inner=True, color=GRID_BORDER)
        g.border(hr, 0, R, len(head), inner=False)
        g.reqs.append(_cf_gradient(sid, hr + 1, 1, R, len(head)))
        return R + 1

    # ========================= 描画 =========================
    R = 3
    # 【全体】
    g.put(R, 0, "【全体】通期累計（期初〜12ヶ月）")
    g.merge(R, 0, R + 1, NC)
    g.fmt(R, 0, R + 1, NC, bg=INK, fg=WHITE, bold=True, size=12, halign="LEFT")
    g.rowheight(R, R + 1, 26)
    R += 1
    R = kpi_hero(R, AS, AZ)
    R += 1
    R = funnel_table(R, "■ 媒体別ファネル（全体）", "媒体",
                     [f'=IF({SET}!$A${MEDIA_LIST_FIRST+i}="","",{SET}!$A${MEDIA_LIST_FIRST+i})'
                      for i in range(SUM_MEDIA_SLOTS)], "media", AS, AZ)
    R += 1
    R = funnel_table(R, "■ 職種別ファネル（全体）", "職種", list(SUM_SHOKU), "shoku", AS, AZ)
    R += 1
    R = cross_matrix(R, AS, AZ)
    R += 1

    # 【月別】
    g.put(R, 0, "【月別】対象月の内訳＋通期トレンド")
    g.merge(R, 0, R + 1, NC)
    g.fmt(R, 0, R + 1, NC, bg=INK, fg=WHITE, bold=True, size=12, halign="LEFT")
    g.rowheight(R, R + 1, 26)
    R += 1
    R = kpi_hero(R, MS, ME)
    R += 1
    R = funnel_table(R, "■ 媒体別ファネル（対象月）", "媒体",
                     [f'=IF({SET}!$A${MEDIA_LIST_FIRST+i}="","",{SET}!$A${MEDIA_LIST_FIRST+i})'
                      for i in range(SUM_MEDIA_SLOTS)], "media", MS, ME)
    R += 1
    R = tanto_table(R, MS, ME)
    R += 1
    # 日次推移（対象月 1〜31日）
    daily_labels = [(d, None) for d in range(1, 32)]
    daily_periods = [(f'DATE(YEAR($B$2),MONTH($B$2),{d})',
                      f'DATE(YEAR($B$2),MONTH($B$2),{d})',
                      f'{d}>DAY({ME})') for d in range(1, 32)]
    R = trend_block(R, "■ 日次推移（対象月）", daily_labels, daily_periods, (MS, ME))
    R += 1
    # 週次推移（対象月）
    weekly_labels = [("週1\n1-7", None), ("週2\n8-14", None), ("週3\n15-21", None),
                     ("週4\n22-28", None), ("週5\n29-", None)]
    weekly_periods = []
    for p in range(5):
        sd = p * 7 + 1
        ed = f'MIN({(p + 1) * 7},DAY({ME}))' if p < 4 else f'DAY({ME})'
        st = f'DATE(YEAR($B$2),MONTH($B$2),{sd})'
        en = f'DATE(YEAR($B$2),MONTH($B$2),{ed})'
        weekly_periods.append((st, en, f'{sd}>DAY({ME})'))
    R = trend_block(R, "■ 週次推移（対象月）", weekly_labels, weekly_periods, (MS, ME))
    R += 1
    # 月次推移（通期12ヶ月）
    monthly_labels = [(f"=EDATE({KIHATSU},{i})", NF_MH) for i in range(12)]
    monthly_periods = [(f'EDATE({KIHATSU},{i})', f'EOMONTH(EDATE({KIHATSU},{i}),0)', None)
                       for i in range(12)]
    R = trend_block(R, "■ 月次推移（通期・期初から12ヶ月）", monthly_labels, monthly_periods, (AS, AZ))
    R += 1
    R = goal_table(R)

    # ── 列幅・フリーズ
    g.colwidth(0, 1, 150)
    g.colwidth(1, 2, 66)
    g.colwidth(2, NC, 60)
    g.reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
        "fields": "gridProperties.frozenRowCount"}})
    return g


def _cf_gradient(sid, r0, c0, r1, c1):
    """達成率用：0=赤 / 0.7=琥珀 / 1=緑（絶対基準）。"""
    return {"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,
                    "startColumnIndex": c0, "endColumnIndex": c1}],
        "gradientRule": {
            "minpoint": {"color": SIG_RED, "type": "NUMBER", "value": "0"},
            "midpoint": {"color": SIG_AMBER, "type": "NUMBER", "value": "0.7"},
            "maxpoint": {"color": SIG_GREEN, "type": "NUMBER", "value": "1"}}},
        "index": 0}}


def _cf_rel(sid, r0, c0, r1, c1):
    """歩留用：相対（最小=赤 / 中央=琥珀 / 最大=緑）。"""
    return {"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,
                    "startColumnIndex": c0, "endColumnIndex": c1}],
        "gradientRule": {
            "minpoint": {"color": SIG_RED, "type": "MIN"},
            "midpoint": {"color": SIG_AMBER, "type": "PERCENTILE", "value": "50"},
            "maxpoint": {"color": SIG_GREEN, "type": "MAX"}}},
        "index": 0}}


# ───────────────────────── README ─────────────────────────
def build_readme(sid):
    g = Grid(sid, 60, 12)
    g.put(0, 0, "使い方｜DR/スカウト管理シート")
    g.merge(0, 0, 1, 10)
    g.fmt(0, 0, 1, 10, bg=RED, fg=WHITE, bold=True, size=14, halign="LEFT")
    g.rowheight(0, 1, 38)

    lines = [
        ("■ 2つの入力方式（媒体ごとに選ぶ＝二刀流）", True),
        ("『03_設定マスタ』の媒体リストの[集計方式]で、媒体ごとに『個別』か『日次集計』を選ぶ。", False),
        ("・個別 … 候補者1人=1行で媒体タブ（例: YOUTRUST）に入力。採用まで丁寧に追う企業向け。", False),
        ("・日次集計 … 『04_日次入力』に 日付×媒体×職種 でカウントを手打ち。下流(返信/面談/採用)は空欄OK。", False),
        ("   送付数を最大化したいだけ／採用まで追わない企業向け。全部手入力せず日次のカウントだけで回せる。", False),
        ("★ 1つの媒体は必ず片方だけで入力する（個別と日次集計を両方入れると二重計上になる）。", False),
        ("", False),
        ("■ 日々の運用", True),
        ("［個別の媒体］その媒体タブに1行追加 → ListUp日/送付日/返信日/面談実施日/採用日 を進捗で入れる。", False),
        ("   候補者IDは自動採番（候補者名を入れた行だけ）。集計は『日付が入っているか』で判定。", False),
        ("［日次集計の媒体］『04_日次入力』に1行 = 日付・媒体・職種(・担当者) と各カウント。下流は空欄可。", False),
        ("", False),
        ("■ 進捗を見る（01_サマリー）＝ 上『全体』／下『月別』", True),
        ("すべての数値は 個別(マスター)＋日次集計(日次入力) を自動で合算して表示する。", False),
        ("【全体】通期累計（期初〜12ヶ月）: KPIヒーロー / 媒体別ファネル / 職種別ファネル / 媒体×職種マトリクス。", False),
        ("   ・媒体×職種は上の[指標→]で ListUp/送付/返信/面談/採用 を切替えると、媒体(行)×職種(列)で表示。", False),
        ("【月別】: 上部『対象月』を切替えると連動。対象月のKPI/媒体別/担当者別/日次・週次推移＋通期12ヶ月推移。", False),
        ("   ファネル定義: ListUp → 送付 → 返信 → 面談 → 採用（5段階）。歩留は各隣接段の比。", False),
        ("", False),
        ("■ 目標の設定", True),
        ("『03_設定マスタ』の[設定]で『期初』（通期12ヶ月の起点）と『目標を使う(はい/いいえ)』を選ぶ。", False),
        ("[月次目標]に月×段階（ListUp/送付/返信/面談/採用）の目標を入力（全体・媒体合算）。", False),
        ("『目標を使う＝いいえ』にするとサマリーの目標／達成率は自動で非表示になる。", False),
        ("", False),
        ("■ スカウト媒体を追加するには", True),
        ("方法A（GAS）: メニュー『DRスカウト管理 > 媒体を追加』→ 媒体名と略号を入力（既定で集計方式=個別）。", False),
        ("   日次集計で使うなら、追加後に設定マスタの[集計方式]を『日次集計』へ変更する。", False),
        ("方法B（手動）: 個別なら『_媒体テンプレ』を複製→媒体名に改名＋設定マスタ登録。日次集計なら設定マスタに", False),
        ("   媒体を1行足して[集計方式]=日次集計にし、04_日次入力に打つだけ（媒体タブは不要）。", False),
        ("", False),
        ("■ タブの役割", True),
        ("00_使い方 … このページ / 01_サマリー … 進捗ダッシュボード（全体↑・月別↓）", False),
        ("02_マスター … 個別媒体の統合ログ（自動・編集禁止） / 03_設定マスタ … 媒体・集計方式・選択肢・目標", False),
        ("04_日次入力 … 日次集計の媒体のカウント入力 / YOUTRUST, LinkedIn … 個別媒体の入力タブ", False),
        ("_媒体テンプレ … 個別媒体の追加用の雛形（非表示）", False),
    ]
    r = 2
    for text, is_head in lines:
        g.put(r, 0, text)
        g.merge(r, 0, r + 1, 11)
        if is_head:
            g.fmt(r, 0, r + 1, 11, fg=RED_DK, bold=True, size=12, halign="LEFT")
        elif text == "":
            pass
        else:
            g.fmt(r, 0, r + 1, 11, fg=INK, size=10, halign="LEFT")
        r += 1
    g.colwidth(0, 1, 40)
    return g


# ───────────────────────── 書き込み ─────────────────────────
def values_payload(sheet_title, grid):
    return {"range": f"{q(sheet_title)}!A1",
            "majorDimension": "ROWS", "values": grid.vals}


def write_grid(svc, sid, title, grid):
    svc.spreadsheets().values().update(
        spreadsheetId=sid, range=f"{q(title)}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": grid.vals}).execute()
    if grid.reqs:
        # チャンクに分けて投げる（リクエスト数が多い場合に備える）
        CH = 200
        for i in range(0, len(grid.reqs), CH):
            svc.spreadsheets().batchUpdate(
                spreadsheetId=sid, body={"requests": grid.reqs[i:i + CH]}).execute()


def get_titles(svc, sid):
    meta = svc.spreadsheets().get(
        spreadsheetId=sid, fields="sheets(properties(sheetId,title))").execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def _cf_count(svc, sid, sheet_id):
    meta = svc.spreadsheets().get(
        spreadsheetId=sid, fields="sheets(properties.sheetId,conditionalFormats)").execute()
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == sheet_id:
            return len(s.get("conditionalFormats", []))
    return 0


def _batch(svc, sid, reqs):
    CH = 200
    for i in range(0, len(reqs), CH):
        svc.spreadsheets().batchUpdate(
            spreadsheetId=sid, body={"requests": reqs[i:i + CH]}).execute()


def clean_sheet(svc, sid, sheet_id, nrows, ncols):
    """再描画前のクリーンアップ（結合/塗り/罫線/データ検証/条件付き書式/値の残骸除去）。"""
    full = {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": nrows,
            "startColumnIndex": 0, "endColumnIndex": ncols}
    reqs = [
        {"updateSheetProperties": {
            "properties": {"sheetId": sheet_id,
                           "gridProperties": {"rowCount": nrows, "columnCount": ncols}},
            "fields": "gridProperties.rowCount,gridProperties.columnCount"}},
        {"unmergeCells": {"range": {"sheetId": sheet_id}}},
        {"updateCells": {"range": full, "fields": "userEnteredValue"}},
        {"repeatCell": {"range": full, "cell": {"userEnteredFormat": {}},
                        "fields": "userEnteredFormat"}},
        {"setDataValidation": {"range": full}},
        {"updateBorders": {"range": full,
                           "top": {"style": "NONE"}, "bottom": {"style": "NONE"},
                           "left": {"style": "NONE"}, "right": {"style": "NONE"},
                           "innerHorizontal": {"style": "NONE"},
                           "innerVertical": {"style": "NONE"}}},
    ]
    for idx in range(_cf_count(svc, sid, sheet_id) - 1, -1, -1):
        reqs.append({"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": idx}})
    return reqs


def rebuild(svc, sid):
    """既存スプレッドシートの 設定マスタ／日次入力／サマリー／使い方 をインプレース再描画（URL不変）。
    日次入力タブが無ければ作成する。"""
    t = get_titles(svc, sid)
    if DAILY_TAB not in t:
        print("→ 日次入力タブを新規作成")
        res = svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": [
            {"addSheet": {"properties": {"title": DAILY_TAB, "gridProperties": {
                "rowCount": DAILY_ROWS, "columnCount": NCOL_DAILY,
                "hideGridlines": True}}}}]}).execute()
        t[DAILY_TAB] = res["replies"][0]["addSheet"]["properties"]["sheetId"]
    print("→ 設定マスタ クリーンアップ＆再描画")
    _batch(svc, sid, clean_sheet(svc, sid, t[SET_TAB], 70, 10))
    write_grid(svc, sid, SET_TAB, build_settei(t[SET_TAB]))
    print("→ 日次入力 クリーンアップ＆再描画")
    _batch(svc, sid, clean_sheet(svc, sid, t[DAILY_TAB], DAILY_ROWS, NCOL_DAILY))
    write_grid(svc, sid, DAILY_TAB, build_daily(t[DAILY_TAB]))
    print("→ サマリー クリーンアップ＆再描画")
    _batch(svc, sid, clean_sheet(svc, sid, t[SUM_TAB], SUM_NROWS, SUM_NCOLS))
    write_grid(svc, sid, SUM_TAB, build_summary(t[SUM_TAB]))
    print("→ 使い方 クリーンアップ＆再描画")
    _batch(svc, sid, clean_sheet(svc, sid, t[README_TAB], 60, 12))
    write_grid(svc, sid, README_TAB, build_readme(t[README_TAB]))
    # タブ順（日次入力を設定マスタの後ろへ）
    order = [README_TAB, SUM_TAB, MST_TAB, SET_TAB, DAILY_TAB]
    reqs = []
    for idx, name in enumerate(order):
        if name in t:
            reqs.append({"updateSheetProperties": {
                "properties": {"sheetId": t[name], "index": idx}, "fields": "index"}})
    if reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": reqs}).execute()
    print("\n✓ 再構築完了")
    print("URL:", f"https://docs.google.com/spreadsheets/d/{sid}/edit")


def main():
    svc = get_service()
    media_names = [m[0] for m in INITIAL_MEDIA]

    print("→ 新規スプレッドシート作成中...")
    sid, default_id = create_spreadsheet(svc)
    print(f"   spreadsheetId = {sid}")

    title2id = add_tabs(svc, sid, media_names)
    # デフォルト Sheet を削除
    svc.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{"deleteSheet": {"sheetId": default_id}}]}).execute()

    # 各タブ構築
    print("→ 設定マスタ")
    write_grid(svc, sid, SET_TAB, build_settei(title2id[SET_TAB]))

    print("→ 日次入力")
    write_grid(svc, sid, DAILY_TAB, build_daily(title2id[DAILY_TAB]))

    print("→ 媒体タブ + テンプレ")
    for name, abbr, ch in INITIAL_MEDIA:
        write_grid(svc, sid, name, build_media_tab(title2id[name], name, abbr, ch))
    write_grid(svc, sid, TEMPLATE_TAB,
               build_media_tab(title2id[TEMPLATE_TAB], "（媒体名）", "XX", ""))

    print("→ マスター")
    write_grid(svc, sid, MST_TAB, build_master(title2id[MST_TAB], media_names))

    print("→ サマリー")
    write_grid(svc, sid, SUM_TAB, build_summary(title2id[SUM_TAB]))

    print("→ 使い方")
    write_grid(svc, sid, README_TAB, build_readme(title2id[README_TAB]))

    # タブ順を整える
    order = [README_TAB, SUM_TAB, MST_TAB, SET_TAB, DAILY_TAB] + media_names + [TEMPLATE_TAB]
    reqs = []
    for idx, t in enumerate(order):
        reqs.append({"updateSheetProperties": {
            "properties": {"sheetId": title2id[t], "index": idx},
            "fields": "index"}})
    svc.spreadsheets().batchUpdate(spreadsheetId=sid, body={"requests": reqs}).execute()

    with open(ID_CACHE, "w", encoding="utf-8") as f:
        f.write(sid)

    url = f"https://docs.google.com/spreadsheets/d/{sid}/edit"
    print("\n✓ 完成")
    print("URL:", url)
    print("ID :", sid)


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        _svc = get_service()
        _sid = None
        for a in sys.argv[1:]:
            if a != "--rebuild" and not a.startswith("-"):
                _sid = a
        if not _sid:
            with open(ID_CACHE, encoding="utf-8") as f:
                _sid = f.read().strip()
        print("→ 再構築対象:", _sid)
        rebuild(_svc, _sid)
    else:
        main()
