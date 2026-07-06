"""
目標管理シート 雛形（新規スプレッドシート）構築 正本スクリプト。
plan: vast-wondering-phoenix

タブ(9): ダッシュボード / 通期 / 上半期 / 下半期 / 評価基準 / 点数定義ガイド / HRbrain貼付用 / 月次振り返り / 90日プラン
評価: 達成=100基準・売上青天井・定量実績で自動・定性◎◯△手動・未評価テンプレ
年度: 6月〜翌5月（上期6-11 / 下期12-5）
月次: 1枚集約（KPI推移＋振り返りログ＋AIサマリー）→ 売上は評価タブへSUM連動
認証: tokumori/agents/hr_support/config/token_sheets.json
SS_IDは .template_ss_id.txt に保存して再実行時に再利用（冪等）。
"""
import os
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# パスは ~ 展開で両マシン（atsuyasato / atsuyasato130＝mini）で正しく解決させる。
# 絶対パス固定だと Syncthing 同期先のマシンで存在せず、新規SS誤作成や認証失敗になる。
_BASE = os.path.expanduser("~/Claude AI")
TOKEN = os.path.join(_BASE, "tokumori/agents/hr_support/config/token_sheets.json")
ID_FILE = os.path.join(_BASE, ".template_ss_id.txt")
TITLE = "目標管理シート_雛形_2026年度"

TABS = ["ダッシュボード", "通期", "上半期", "下半期", "評価基準", "点数定義ガイド",
        "HRbrain貼付用", "月次振り返り", "90日プラン"]
# 旧名→新名（既存SSのタブを正準名へ移行。_ensure_tabs_existの重複追加を防ぐため先に通す）
LEGACY_RENAME = {"HRブレイン貼付用": "HRbrain貼付用"}

# ---- 90日プラン（4クオーター＝360日／進捗ステータス更新可）----
PLAN_QUARTERS = [("Q1", "6〜8月"), ("Q2", "9〜11月"), ("Q3", "12〜2月"), ("Q4", "3〜5月")]
PLAN_STATUS = ["未着手", "進行中", "完了", "保留"]
PLAN_ACTIONS = 10  # 各クオーターのマイルストーン行数
PLAN_WEEKS = 13    # 各クオーターの週（13週×4＝52週＝1年）
PLAN_QSTART_DATES = ["2026/6/1", "2026/9/1", "2026/12/1", "2027/3/1"]  # 各QのW1起点（編集可）

# ---- 評価タブ レイアウト（1目標＝ブロック：定量5行/定性・バリュー3行・各カテゴリ SLOTS 個） ----
# 空ブロック（目標名が空）は集計から自動除外。
SLOTS = 3
QH = 5     # 定量ブロック高（5段階しきい値）

Q_BAN, Q_HDR, Q_R0 = 4, 5, 6
Q_SUB = Q_R0 + SLOTS * QH                       # 6 + 15 = 21
QL_BAN = Q_SUB + 2                              # 23
QL_HDR, QL_R0 = QL_BAN + 1, QL_BAN + 2          # 24 / 25
Q_BLOCKS = [Q_R0 + i * QH for i in range(SLOTS)]    # [6, 11, 16]

# 定性・バリューの段階数(TH=ブロック高)はシートごとに切替（3=◎◯△100/80/60 / 5=100/90/80/70/60点）。
# TH依存の行定数（QL_SUB以降）は _set_qual_levels(n) で再計算する＝build_member冒頭で呼ぶ。
QUAL_LEVELS = 3
TH = 3


def _set_qual_levels(n):
    """定性・バリューの段階数を設定し、TH依存の行定数を再計算（per-sheet切替・ビルドは逐次なのでglobalで安全）。"""
    global QUAL_LEVELS, TH, QL_SUB, V_BAN, V_HDR, V_R0, V_SUB, CARD, CARD_HDR, HERO, BREAK
    global B_QUANT, B_QUAL, B_VALUE, SETROW, REFROW, QL_BLOCKS, V_BLOCKS
    QUAL_LEVELS = n
    TH = n
    QL_SUB = QL_R0 + SLOTS * TH
    V_BAN = QL_SUB + 2
    V_HDR, V_R0 = V_BAN + 1, V_BAN + 2
    V_SUB = V_R0 + SLOTS * TH
    CARD = V_SUB + 2                            # ■総合点バナー
    CARD_HDR, HERO, BREAK = CARD + 1, CARD + 2, CARD + 3
    B_QUANT, B_QUAL, B_VALUE = CARD + 4, CARD + 5, CARD + 6   # 目標評価点は廃止＝定量60/定性20/バリュー20フラット
    SETROW = CARD + 8
    REFROW = CARD + 10
    QL_BLOCKS = [QL_R0 + i * TH for i in range(SLOTS)]
    V_BLOCKS = [V_R0 + i * TH for i in range(SLOTS)]


_set_qual_levels(3)   # 既定=3段階（雛形）。佐藤はbuild_memberで5に切替。

# 定量の参照表示モード（per-sheet切替・build_memberで設定）。
#   False＝OTE支給率テーブル表示（雛形A/B）／ True＝リニア表示（達成率＝評価点・佐藤）。
#   ※採点式は変更しない。佐藤の定量は採点方式「比率」（実績÷目標×100）で既にリニア。
#     段階(OTE)モードは採点方式ドロップダウンに温存（このフラグは「案内表示」だけを切替える）。
QUANT_LINEAR = False

# ---- 評価タブ 列（B=1 起点の0-indexed／A=margin） ----
# 新順：目標情報 B:F（縦結合）｜ OTE参照 G:I（行展開）｜ 採点 J:Q（縦結合）｜ R ヘルパ(非表示)
cKU, cITEM, cSMART, cAP, cTGT = 1, 2, 3, 4, 5                  # B 区分 / C 目標項目 / D SMART / E AP / F 目標値
cRANK, cTHR, cDEF = 6, 7, 8                                    # G 達成率(◎◯△) / H しきい値¥ / I 評価点・定義
cW, cSIN, cSR, cSP = 9, 10, 11, 12                             # J ウェイト / K 自己入力 / L 自己達成率 / M 自己点
cBIN, cBR, cBP, cMODE = 13, 14, 15, 16                         # N 上長入力 / O 上長達成率 / P 上長点 / Q 採点方式
cHELP = 17                                                    # R 段階定義サマリー（非表示ヘルパ＝HRブレイン/評価基準が参照）
EVAL_LASTCOL = 16                                            # Q（可視範囲の右端）
# A1 列文字
LKU, LITEM, LSMART, LAP, LTGT = "B", "C", "D", "E", "F"
LRANK, LTHR, LDEF = "G", "H", "I"
LW, LSIN, LSR, LSP = "J", "K", "L", "M"
LBIN, LBR, LBP, LMODE = "N", "O", "P", "Q"
LHELP = "R"
# 総合点カードの 自己/上長 値列（幅広のD/Eを大きな数値表示に活用）
LCSELF, LCBOSS = "D", "E"


# ---- カラーパレット（build_eval_redesign_v1 と共通） ----
WHITE = {"red": 1, "green": 1, "blue": 1}
RED = {"red": 0.686, "green": 0.196, "blue": 0.173}
RED_TINT = {"red": 0.984, "green": 0.929, "blue": 0.925}
GREY_HEAD = {"red": 0.949, "green": 0.949, "blue": 0.949}
ZEBRA = {"red": 0.980, "green": 0.980, "blue": 0.980}
SUBTOTAL_BG = {"red": 0.965, "green": 0.965, "blue": 0.965}
BORDER_GREY = {"red": 0.851, "green": 0.851, "blue": 0.851}
BORDER_LT = {"red": 0.910, "green": 0.910, "blue": 0.910}
BORDER_STRONG = {"red": 0.60, "green": 0.60, "blue": 0.60}
YELLOW = {"red": 1, "green": 0.988, "blue": 0.875}
TEXT_DARK = {"red": 0.13, "green": 0.13, "blue": 0.13}
TEXT_GREY = {"red": 0.44, "green": 0.44, "blue": 0.44}


# ============================================================
#  共通ヘルパー（build_eval_redesign_v1 と同型）
# ============================================================
def col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def rng(sid, r1, r2, c1, c2):
    return {"sheetId": sid, "startRowIndex": r1 - 1, "endRowIndex": r2,
            "startColumnIndex": c1, "endColumnIndex": c2 + 1}


def border(style="SOLID", color=BORDER_GREY):
    return {"style": style, "color": color}


def repeat_fmt(sid, r1, r2, c1, c2, fmt, fields):
    return {"repeatCell": {"range": rng(sid, r1, r2, c1, c2),
                           "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def merge(sid, r1, r2, c1, c2):
    return {"mergeCells": {"range": rng(sid, r1, r2, c1, c2), "mergeType": "MERGE_ALL"}}


def unmerge(sid, r1, r2, c1, c2):
    return {"unmergeCells": {"range": rng(sid, r1, r2, c1, c2)}}


def set_borders(sid, r1, r2, c1, c2, **kw):
    req = {"updateBorders": {"range": rng(sid, r1, r2, c1, c2)}}
    req["updateBorders"].update(kw)
    return req


def col_width(sid, c, w):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c, "endIndex": c + 1},
        "properties": {"pixelSize": w}, "fields": "pixelSize"}}


def row_height(sid, r, h):
    return {"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "ROWS", "startIndex": r - 1, "endIndex": r},
        "properties": {"pixelSize": h}, "fields": "pixelSize"}}


def tf(color=TEXT_DARK, size=10, bold=False):
    return {"foregroundColor": color, "fontSize": size, "bold": bold}


def grid_off(sid):
    return {"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"hideGridlines": True, "frozenRowCount": 0, "frozenColumnCount": 0}},
        "fields": "gridProperties(hideGridlines,frozenRowCount,frozenColumnCount)"}}


def box(sid, r1, r2, c1, c2, inner=True):
    """中グレーの強い箱で囲う。"""
    kw = dict(top=border("SOLID_MEDIUM", BORDER_STRONG), bottom=border("SOLID_MEDIUM", BORDER_STRONG),
              left=border("SOLID_MEDIUM", BORDER_STRONG), right=border("SOLID_MEDIUM", BORDER_STRONG))
    if inner:
        kw["innerHorizontal"] = border("SOLID", BORDER_LT)
        kw["innerVertical"] = border("SOLID", BORDER_LT)
    return set_borders(sid, r1, r2, c1, c2, **kw)


def banner(sid, r, c1, c2, fields_extra=None):
    """セクションバナー（淡赤＋赤太字＋左赤太罫＋上下右中罫）。"""
    out = [merge(sid, r, r, c1, c2),
           repeat_fmt(sid, r, r, c1, c2,
                      {"backgroundColor": RED_TINT, "textFormat": tf(RED, 11, True),
                       "verticalAlignment": "MIDDLE"},
                      "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"),
           set_borders(sid, r, r, c1, c2, top=border("SOLID_MEDIUM", BORDER_STRONG),
                       bottom=border("SOLID_MEDIUM", BORDER_STRONG), right=border("SOLID_MEDIUM", BORDER_STRONG)),
           set_borders(sid, r, r, c1, c1, left=border("SOLID_THICK", RED)),
           row_height(sid, r, 30)]
    return out


def write_values(svc, sid_name, data):
    """data: list[(a1_range, 2d_values)] を USER_ENTERED で一括。"""
    svc.spreadsheets().values().batchUpdate(spreadsheetId=sid_name, body={
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": r, "values": v} for r, v in data]}).execute()


def svc_get():
    creds = Credentials.from_authorized_user_file(TOKEN)
    return build("sheets", "v4", credentials=creds)


def get_or_create_ss(svc, id_file, title):
    if os.path.exists(id_file):
        sid = open(id_file).read().strip()
        if sid:
            print(f"既存SS再利用: {sid}")
            return sid
    body = {"properties": {"title": title},
            "sheets": [{"properties": {"title": t, "index": i}} for i, t in enumerate(TABS)]}
    ss = svc.spreadsheets().create(body=body, fields="spreadsheetId").execute()
    sid = ss["spreadsheetId"]
    open(id_file, "w").write(sid)
    print(f"新規SS作成: {sid}")
    return sid


def sheet_ids(svc, sid):
    meta = svc.spreadsheets().get(spreadsheetId=sid,
                                  fields="sheets(properties(sheetId,title))").execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


MONTHS = ["6月", "7月", "8月", "9月", "10月", "11月", "12月", "1月", "2月", "3月", "4月", "5月"]
# 月次振り返りシートの売上行（評価タブがSUM参照する固定位置）
M_KOJIN_ROW = 12   # 個人売上 C12:N12
M_TEAM_ROW = 13    # チーム売上 C13:N13


def build_monthly(svc, SS, gid, member="（メンバー名）"):
    # 列: A=margin / B=項目 / C..N=6〜5月(12) / O上期計 P下期計 / Q..T=Q1..Q4 / U通期
    # KPI行: 6担当母数 7企業推薦 8面談実施 9内定 10内定承諾 11承諾率 12個人売上 13チーム売上
    def sums(r):
        return [[f"=SUM(C{r}:H{r})", f"=SUM(I{r}:N{r})",
                 f"=SUM(C{r}:E{r})", f"=SUM(F{r}:H{r})", f"=SUM(I{r}:K{r})", f"=SUM(L{r}:N{r})",
                 f"=O{r}+P{r}"]]
    vals = [
        (f"月次振り返り!B1", [[f"月次振り返り｜{member}　2026年度（6月〜翌5月）"]]),
        (f"月次振り返り!B2", [["毎月のKPIと振り返りを記録。売上は評価へ自動で連動します。"]]),
        (f"月次振り返り!B4", [["■ KPIトラッキング（人材紹介）"]]),
        (f"月次振り返り!B5", [["項目"] + MONTHS + ["上期計", "下期計", "Q1", "Q2", "Q3", "Q4", "通期"]]),
        (f"月次振り返り!B6", [["担当母数（件）"]]), (f"月次振り返り!O6", sums(6)),
        (f"月次振り返り!B7", [["企業推薦（件）"]]), (f"月次振り返り!O7", sums(7)),
        (f"月次振り返り!B8", [["面談実施（件）"]]), (f"月次振り返り!O8", sums(8)),
        (f"月次振り返り!B9", [["内定（件）"]]), (f"月次振り返り!O9", sums(9)),
        (f"月次振り返り!B10", [["内定承諾（件）"]]), (f"月次振り返り!O10", sums(10)),
        (f"月次振り返り!B11", [["承諾率（％）"]]),
        (f"月次振り返り!B14", [["■ 月次振り返りログ"]]),
        (f"月次振り返り!B15", [["月"]]),
        (f"月次振り返り!C15", [["できたこと"]]),
        (f"月次振り返り!I15", [["課題"]]),
        (f"月次振り返り!N15", [["来月のアクション"]]),
        (f"月次振り返り!R15", [["上長コメント"]]),
        (f"月次振り返り!B30", [["■ サマリー（半期・四半期・通期）"]]),
        (f"月次振り返り!B31", [["上半期サマリー（6-11月）"]]),
        (f"月次振り返り!B32", [["下半期サマリー（12-5月）"]]),
        (f"月次振り返り!B33", [["Q1（6-8月）"]]), (f"月次振り返り!B34", [["Q2（9-11月）"]]),
        (f"月次振り返り!B35", [["Q3（12-2月）"]]), (f"月次振り返り!B36", [["Q4（3-5月）"]]),
        (f"月次振り返り!B37", [["通期サマリー"]]),
    ]
    # 承諾率: 各月＝内定承諾/担当母数, 期計も同様
    rate_cells = [f"{col(c)}11" for c in range(2, 21)]  # C..U
    rate_num = [f"{col(c)}10" for c in range(2, 21)]
    rate_den = [f"{col(c)}6" for c in range(2, 21)]
    rate_row = [[f'=IFERROR({n}/{d},"")' for n, d in zip(rate_num, rate_den)]]
    vals.append((f"月次振り返り!C11", rate_row))
    # 個人売上/チーム売上: ラベル＋期計SUM
    vals.append((f"月次振り返り!B12", [["個人売上（¥）"]])); vals.append((f"月次振り返り!O12", sums(12)))
    vals.append((f"月次振り返り!B13", [["チーム売上（¥）"]])); vals.append((f"月次振り返り!O13", sums(13)))
    # 振り返りログ 月ラベル(17-28)
    for i, m in enumerate(MONTHS):
        vals.append((f"月次振り返り!B{17 + i}", [[m]]))
    write_values(svc, SS, vals)

    # ---- 書式 ----
    R = [grid_off(gid), unmerge(gid, 1, 60, 0, 25)]
    R.append(col_width(gid, 0, 28))   # A margin
    R.append(col_width(gid, 1, 120))  # B 項目
    for c in range(2, 14):
        R.append(col_width(gid, c, 64))   # C-N months
    for c in range(14, 21):
        R.append(col_width(gid, c, 72))   # O-U calc
    # 全体リセット
    R.append(repeat_fmt(gid, 1, 40, 0, 20,
                        {"backgroundColor": WHITE, "verticalAlignment": "MIDDLE", "wrapStrategy": "OVERFLOW_CELL",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    # タイトル/凡例
    R.append(merge(gid, 1, 1, 1, 20))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 14, True)}, "userEnteredFormat.textFormat"))
    R.append(set_borders(gid, 1, 1, 1, 20, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(gid, 1, 38))
    R.append(merge(gid, 2, 2, 1, 20))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    # KPIバナー
    R += banner(gid, 4, 1, 20)
    # KPIヘッダ行5
    R.append(repeat_fmt(gid, 5, 5, 1, 20,
                        {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9.5 if False else 9, True),
                         "horizontalAlignment": "CENTER", "wrapStrategy": "WRAP"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,wrapStrategy)"))
    R.append(repeat_fmt(gid, 5, 5, 1, 1, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    R.append(row_height(gid, 5, 30))
    # KPI本体 6-13: 入力(C-N)黄, 計(O-U)淡グレー
    R.append(repeat_fmt(gid, 6, 13, 1, 1, {"textFormat": tf(TEXT_DARK, 10, False)}, "userEnteredFormat.textFormat"))
    R.append(repeat_fmt(gid, 6, 13, 2, 13, {"backgroundColor": YELLOW, "horizontalAlignment": "RIGHT"},
                        "userEnteredFormat(backgroundColor,horizontalAlignment)"))
    R.append(repeat_fmt(gid, 6, 13, 14, 20, {"backgroundColor": SUBTOTAL_BG, "horizontalAlignment": "RIGHT",
                                             "textFormat": tf(TEXT_DARK, 10, True)},
                        "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)"))
    # 承諾率行(11)は自動なので黄を外す＋%表示
    R.append(repeat_fmt(gid, 11, 11, 2, 20, {"backgroundColor": WHITE,
                                             "numberFormat": {"type": "PERCENT", "pattern": "0.0%"}},
                        "userEnteredFormat(backgroundColor,numberFormat)"))
    R.append(repeat_fmt(gid, 11, 11, 14, 20, {"backgroundColor": SUBTOTAL_BG}, "userEnteredFormat.backgroundColor"))
    # 売上行(12,13) ¥表示
    R.append(repeat_fmt(gid, 12, 13, 2, 20, {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}},
                        "userEnteredFormat.numberFormat"))
    R.append(box(gid, 5, 13, 1, 20))
    # 上期/下期/通期 区切り強調
    R.append(set_borders(gid, 5, 13, 13, 14, left=border("SOLID_MEDIUM", BORDER_STRONG)))
    R.append(set_borders(gid, 5, 13, 19, 20, left=border("SOLID_MEDIUM", BORDER_STRONG)))

    # 振り返りログ
    R += banner(gid, 14, 1, 20)
    # ログ列をマージ（できたこと C:H / 課題 I:M / 来月 N:Q / 上長 R:U）
    log_spans = [("できたこと", 2, 7), ("課題", 8, 12), ("来月のアクション", 13, 16), ("上長コメント", 17, 20)]
    for rr in range(15, 29):  # header15 + 12行(16..27→17..28?) 実際は header15→ B15ヘッダ, 17-28データ
        pass
    # ヘッダ15
    R.append(repeat_fmt(gid, 15, 15, 1, 20, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9.5 if False else 10, True),
                                             "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    for label, c1, c2 in log_spans:
        R.append(merge(gid, 15, 15, c1, c2))
    R.append(row_height(gid, 15, 26))
    # データ 17-28
    for rr in range(17, 29):
        for label, c1, c2 in log_spans:
            R.append(merge(gid, rr, rr, c1, c2))
        R.append(repeat_fmt(gid, rr, rr, 2, 20, {"backgroundColor": YELLOW, "wrapStrategy": "WRAP",
                                                 "verticalAlignment": "TOP", "horizontalAlignment": "LEFT"},
                            "userEnteredFormat(backgroundColor,wrapStrategy,verticalAlignment,horizontalAlignment)"))
        R.append(repeat_fmt(gid, rr, rr, 1, 1, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 10, True)},
                            "userEnteredFormat(horizontalAlignment,textFormat)"))
        R.append(row_height(gid, rr, 48))
    R.append(box(gid, 15, 28, 1, 20))

    # AIサマリー
    R += banner(gid, 30, 1, 20)
    for rr in range(31, 38):
        R.append(merge(gid, rr, rr, 1, 2))    # B:C ラベル
        R.append(merge(gid, rr, rr, 3, 20))   # D:U テキスト
        R.append(repeat_fmt(gid, rr, rr, 1, 2, {"textFormat": tf(RED, 10, True), "verticalAlignment": "MIDDLE",
                                                "backgroundColor": RED_TINT},
                            "userEnteredFormat(textFormat,verticalAlignment,backgroundColor)"))
        R.append(repeat_fmt(gid, rr, rr, 3, 20, {"wrapStrategy": "WRAP", "verticalAlignment": "TOP",
                                                 "backgroundColor": {"red": 0.992, "green": 0.992, "blue": 0.992}},
                            "userEnteredFormat(wrapStrategy,verticalAlignment,backgroundColor)"))
        R.append(row_height(gid, rr, 56))
    R.append(box(gid, 31, 37, 1, 20))

    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    print("  月次振り返り: done")


# ============================================================
#  評価タブ（通期/上半期/下半期）
# ============================================================
def rankmap3(ref):
    return f'IF({ref}="◎",100,IF({ref}="◯",80,IF({ref}="△",60,"未評価")))'


# 定性・バリュー 5段階（佐藤）：レベル＝点（100/90/80/70/60）。達成=100が上限。
# ラベルは「点」付きテキスト固定（"100%"等はUSER_ENTERED/ドロップダウンで数値0.9等に化け比較が崩れるため）。
RANK5_LEVELS = ["100点", "90点", "80点", "70点", "60点"]


def rankmap5(ref):
    return (f'IF({ref}="100点",100,IF({ref}="90点",90,IF({ref}="80点",80,'
            f'IF({ref}="70点",70,IF({ref}="60点",60,"未評価")))))')


def rankmap(ref):
    """段階数(QUAL_LEVELS)に応じた定性ランク→点の写像。"""
    return rankmap5(ref) if QUAL_LEVELS == 5 else rankmap3(ref)


def qual_scale_text():
    """定性・バリューの段階スケール説明（凡例/ガイド/HRブレイン用・段階数で切替）。"""
    return ("5段階＝100/90/80/70/60点（達成＝100が上限）" if QUAL_LEVELS == 5
            else "◎/◯/△＝100/80/60（達成＝100が上限）")


def qual_score_label():
    """90日プラン年間目標等の短い採点ラベル。"""
    return "5段階 100/90/80/70/60" if QUAL_LEVELS == 5 else "◎100 / ◯80 / △60"


# 売上の月次レンジ（個人=12行 / チーム=13行）
MR = {"上半期": ("C12:H12", "C13:H13"), "下半期": ("I12:N12", "I13:N13"), "通期": ("C12:N12", "C13:N13")}

# ---- 定量＝OTE公式 支給率テーブル準拠（達成率→評価点＝支給率×100）。150%超は青天井 ----
# 全11段（評価基準タブに共通表示）。スコアは pt_quant の step 式で算出。
OTE_TABLE = [          # (達成率レンジ, 支給率, 評価点表記)
    ("〜69%", "0.00", "0"), ("70〜79%", "0.30", "30"), ("80〜84%", "0.50", "50"),
    ("85〜89%", "0.60", "60"), ("90〜94%", "0.70", "70"), ("95〜96%", "0.80", "80"),
    ("97〜98%", "0.90", "90"), ("99%", "0.95", "95"), ("100%（達成）", "1.00", "100"),
    ("101〜124%", "1.15", "115"), ("125〜149%", "1.30", "130"), ("150%以上", "1.50〜", "150〜（青天井）"),
]
# 目標ブロックに表示する代表ウェイポイント（5行・¥＝目標×割合・点はOTE準拠）
# ラベルは「〜」「以上」「（達成）」入りでテキスト固定（"125%"等は%で数値変換されるため）
OTE_WAYPOINTS = [      # (達成率ラベル, 割合, 評価点表記)
    ("150%以上", 1.50, "150点＋青天井"),
    ("125〜149%", 1.25, "130点"),
    ("100%（達成）", 1.00, "100点・基準"),
    ("90〜94%", 0.90, "70点"),
    ("70〜79%", 0.70, "30点（69%以下=0）"),
]
# リニア表示（達成率＝評価点）の代表ウェイポイント（5行・¥＝目標×割合）。
# ラベルは「%」単独だと USER_ENTERED で数値化されるため 〜/以上/（）入りでテキスト固定。
LINEAR_WAYPOINTS = [   # (達成率ラベル, 割合, 評価点表記)
    ("150%以上", 1.50, "150点（上限なし）"),
    ("125%（超過）", 1.25, "125点"),
    ("100%（達成）", 1.00, "100点・基準"),
    ("80%（未達）", 0.80, "80点"),
    ("70%（未達）", 0.70, "70点"),
]
DEF3 = {"◎": "しっかり達成", "◯": "概ね達成", "△": "未達"}
RANK3_SYMS = ["◎", "◯", "△"]

# ---- 役職マスタ（資料P7）：役職｜区分(OTE/MBO)｜Base:Variable｜支給タイミング ----
# OTE系は日次/月次で数字が見える職種（スプリント型）、MBO系は四半期/半期の戦略的成果（プロジェクト型）。
ROLE_MASTER = [
    ("Field Sales MG", "OTE", "58 : 42", "年2回"),
    ("Inside Sales MG", "OTE", "71 : 29", "年2回"),
    ("新卒CARA MG", "OTE", "59 : 41", "年2回"),
    ("中途CARA MG", "OTE", "53 : 47", "年2回"),
    ("Marketing MG", "OTE", "73 : 27", "年2回"),
    ("RPO SV", "OTE", "77 : 23", "年2回"),
    ("新卒CARA", "OTE", "60 : 40", "年2回"),
    ("中途CARA", "OTE", "58 : 42", "年2回"),
    ("RPO CSメンバー", "OTE", "74 : 26", "年2回"),
    ("Recruitment", "MBO", "—（定量60/定性20/V20）", "年2回(6/12月)"),
    ("Corporate", "MBO", "—（定量60/定性20/V20）", "年2回(6/12月)"),
    ("Strategy", "MBO", "—（定量60/定性20/V20）", "年2回(6/12月)"),
    ("Ops", "MBO", "—（定量60/定性20/V20）", "年2回(6/12月)"),
]
ROLE_NAMES = [r[0] for r in ROLE_MASTER]

METRIC_CRIT = ("採点方式『比率』＝実績÷目標×100（連続・150%超も青天井）／"
               "『段階』＝OTE公式 支給率テーブル準拠（90%→70/100%→100/125%→130/150%→150・150%超は青天井）")


def parse_crit(crit):
    """段階定義テキスト（'◎：… / ◯：…'）を {key: 定義} に分解（定性◎◯△用）。"""
    out = {}
    if not crit:
        return out
    for part in re.split(r"[\n/]", str(crit)):
        m = re.match(r"^\s*([◎◯△])\s*[：:]\s*(.+?)\s*$", part)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


QUAL_PTS = {"◎": "100点", "◯": "80点", "△": "60点"}


def qual_def(crit, sym):
    # 定義に点数を付記（達成=100点が上限。括弧は1つに統一＝冗長回避）
    return f"{parse_crit(crit).get(sym, DEF3[sym])}（{QUAL_PTS[sym]}）"


# kind: sales(実績=月次)/metric(実績=手入力)→N列の採点方式(比率/段階)で自動 ／ rank3=手動◎◯△
def G(ku, item, smart, ap, tgt, w, kind, crit="", mode="比率"):
    return {"ku": ku, "item": item, "smart": smart, "ap": ap, "tgt": tgt, "w": w,
            "kind": kind, "crit": crit, "mode": mode}

AP_PH = "（アクションプランを記入）"
# --- 雛形（空テンプレ・プレースホルダ）：各カテゴリ3スロット ---
_C5 = "5：大きく超過 / 4：超過 / 3：目標達成（基準） / 2：やや未達 / 1：未達"
_C3 = "◎：しっかり達成 / ◯：概ね達成 / △：未達"
TPL_QUANT = [
    G("定量①", "個人売上", "（記入）個人売上 ¥◯◯◯（通期）。人材紹介を主軸に、イベント・メディアでも創出して到達。", AP_PH, "", 0.33, "sales", _C5, mode="比率"),
    G("定量②", "チーム売上", "（記入）チーム売上 ¥◯◯◯（通期・自分含む）。", AP_PH, "", 0.50, "sales", _C5, mode="比率"),
    G("定量③", "（目標名を記入）", "（記入）達成したい目標を数値で（SMART）。実績を入れると自動採点。", AP_PH, "◯◯", 0.17, "metric", _C5, mode="段階"),
]
TPL_QUAL = [
    G("定性①", "（目標名を記入）", "（記入）達成したい状態を記述（SMART）。", AP_PH, "—（状態目標）", 0.6, "rank3", _C3),
    G("定性②", "（目標名を記入）", "（記入）達成したい状態を記述（SMART）。", AP_PH, "—（状態目標）", 0.4, "rank3", _C3),
    G("定性③", "", "", "", "", "", "rank3", ""),
]
TPL_VALUE = [
    G("バリュー①", "特盛級の価値貢献", "（記入）バリュー体現の目標を記述。", AP_PH, "—（状態目標）", 1.0, "rank3", _C3),
    G("バリュー②", "", "", "", "", "", "rank3", ""),
    G("バリュー③", "", "", "", "", "", "rank3", ""),
]


def load_sato():
    import json
    sg = json.load(open(os.path.join(_BASE, "sato_goals.json")))

    def w(r):
        s = str(sg[str(r)].get("w", "")).strip().rstrip("%")
        return float(s) / 100 if s else ""

    def crit(r, default=""):
        c = sg[str(r)].get("crit", "")
        return c if c else default
    quant = [
        G("定量①", sg["6"]["item"], sg["6"]["smart"], sg["6"]["ap"],
          {"通期": sg["6"]["tgt_full"], "上半期": sg["6"]["tgt_h1"], "下半期": sg["6"]["tgt_h2"]},
          w(6), "sales", crit(6, _C5), mode="比率"),
        G("定量②", sg["7"]["item"], sg["7"]["smart"], sg["7"]["ap"],
          {"通期": sg["7"]["tgt_full"], "上半期": sg["7"]["tgt_h1"], "下半期": sg["7"]["tgt_h2"]},
          w(7), "sales", crit(7, _C5), mode="比率"),
        G("定量③", sg["8"]["item"], sg["8"]["smart"], sg["8"]["ap"],
          {"通期": 2, "上半期": 1, "下半期": 1}, w(8), "metric", crit(8, _C5), mode="比率"),
    ]
    qual = [
        G("定性①", sg["13"]["item"], sg["13"]["smart"], sg["13"]["ap"], "—（状態目標）", w(13), "rank3", crit(13, _C3)),
        G("定性②", sg["14"]["item"], sg["14"]["smart"], sg["14"]["ap"], "—（状態目標）", w(14), "rank3", crit(14, _C3)),
        G("定性③", "", "", "", "", "", "rank3", ""),
    ]
    value = [
        G("バリュー①", sg["19"]["item"], sg["19"]["smart"], sg["19"]["ap"], "—（状態目標）", 1.0, "rank3", crit(19, _C3)),
        G("バリュー②", "", "", "", "", "", "rank3", ""),
        G("バリュー③", "", "", "", "", "", "rank3", ""),
    ]
    return quant, qual, value


# 佐藤の定性・バリュー評価基準（5段階＝100/90/80/70/60点の順）。期別に I列へ記載（_seed_qual_criteria）。
# 上半期＝上期版／通期＝無印版／バリューは全期同じ／下半期の定性は後日（プレースホルダのまま）。
SATO_QUAL_CRIT = {
    "定性①": {
        "上半期": [
            "新規メンバーが2名採用されており、研修プログラムを作成し、配属後のオンボーディングを立案・実行されていること。そして、少なくともそのうちの1名の面談数についてトータル60名以上の面談実施がなされていること",
            "新規メンバーが2名採用されており、研修プログラムを作成し、配属後のオンボーディングを立案・実行されていること。そして、少なくともそのうちの1名の面談数についてトータル30名以上の面談実施がなされていること",
            "新規メンバーが1名採用されており、研修プログラムを作成し、配属後のオンボーディングを立案・実行されていること。そして、少なくともそのうちの1名の面談数についてトータル60名以上の面談実施がなされていること",
            "新規メンバーが1名採用されており、研修プログラムを作成し、配属後のオンボーディングを立案・実行されていること。そして、少なくともそのうちの1名の面談数についてトータル30名以上の面談実施がなされていること",
            "新規メンバーが1名採用されており、研修プログラムを作成し、配属後のオンボーディングを立案・実行されていること。",
        ],
        "通期": [
            "新規メンバーの研修プログラムを作成し、配属後のオンボーディングを立案・実行する。メンバーを育て、月間売上400万円を出せるメンバーを1名以上輩出できている状態にする。またはメンバーを育て、月間売上平均300万円を出せるメンバーを2名以上輩出できている状態にする。",
            "新規メンバーの研修プログラムを作成し、配属後のオンボーディングを立案・実行する。メンバーを育て、月間売上300万円を出せるメンバーを1名以上輩出できている状態にする。またはメンバーを育て、月間売上平均250万円を出せるメンバーを2名以上輩出できている状態にする。",
            "新規メンバーの研修プログラムを作成し、配属後のオンボーディングを立案・実行する。メンバーを育て、月間売上250万円を出せるメンバーを1名以上輩出できている状態にする。またはメンバーを育て、月間売上平均200万円を出せるメンバーを2名以上輩出できている状態にする。",
            "新規メンバーの研修プログラムを作成し、配属後のオンボーディングを立案・実行する。メンバーを育て、月間売上250万円を出せるメンバーを1名以上輩出できている状態にする。またはメンバーを育て、月間売上平均150万円を出せるメンバーを2名以上輩出できている状態にする。",
            "新規メンバーの研修プログラムを作成し、配属後のオンボーディングを立案・実行する。メンバーを育て、月間売上200万円を出せるメンバーを1名以上輩出できている状態にする。またはメンバーを育て、月間売上平均100万円を出せるメンバーを2名以上輩出できている状態にする。",
        ],
    },
    "定性②": {
        "上半期": [
            "新しい集客経路として自社メディアについて、UIUXの完成／裏側のセキュリティ周りの設定がなされており、経営承認が取れたうえで、公開後。",
            "新しい集客経路として自社メディアについて、UIUXの完成／裏側のセキュリティ周りの設定がなされており、経営承認が取れており、公開前",
            "新しい集客経路として自社メディアについて、UIUXの完成／裏側のセキュリティ周りの設定がなされており、経営承認が取れていない",
            "新しい集客経路として自社メディアについて、UIUXの完成／裏側のセキュリティ周りの設定に課題が残っており、経営承認が取れていない",
            "新しい集客経路として自社メディアについて、UIUXについて課題が残っている／裏側のセキュリティ周りの設定に課題が残っており、経営承認が取れていない",
        ],
        "通期": [
            "新しい集客経路として自社メディアを立ち上げ、運用が出来ており、公開後、月平均30名以上の28卒学生を集客が出来ており、マネタイズ導線が完成し、メディア経由の売上が計上されていること",
            "新しい集客経路として自社メディアを立ち上げ、運用が出来ており、公開後、月平均30名以上の28卒学生を集客が出来ており、マネタイズ導線が未完成",
            "新しい集客経路として自社メディアを立ち上げ、運用が出来ており、公開後、月平均20名以上の28卒学生を集客が出来ている状態。",
            "新しい集客経路として自社メディアを立ち上げ、運用が出来ており、公開後、月平均10名以上の28卒学生を集客が出来ている状態。",
            "新しい集客経路として自社メディアを立ち上げ、運用が出来ており、公開されていること",
        ],
    },
    "バリュー①": {
        "全期": [
            "AIを活用した業務改善が複数の部署で4つ以上実装されており、運用されていること。そして、対象業務の工数が少なくとも週単位で5hの削減が出来ていること。",
            "AIを活用した業務改善が複数の部署で2つ以上実装されており、運用されていること。そして、対象業務の工数が少なくとも週単位で5hの削減が出来ていること。",
            "AIを活用した業務改善が単一部署で4つ以上実装されており、運用されていること。そして、対象業務の工数が少なくとも週単位で5hの削減が出来ていること。",
            "AIを活用した業務改善が単一部署で2つ以上実装されており、運用されていること。そして、対象業務の工数が少なくとも週単位で5hの削減が出来ていること。",
            "AIを活用した業務改善が単一部署で2つ以上実装されており、運用されていること。そして、対象業務の工数が少なくとも週単位で2hの削減が出来ていること。",
        ],
    },
}


def _seed_qual_criteria(svc, SS):
    """佐藤の定性・バリューの評価基準（5段階）を期別にI列へ記載。help_join→R列→HRブレインに自動反映。
    QUAL_LEVELS==5（=5段階の行配置）前提で QL_BLOCKS/V_BLOCKS を参照する。"""
    q1, q2 = QL_BLOCKS[0], QL_BLOCKS[1]   # 定性①/② ブロック先頭行（5段階＝各5行）
    v1 = V_BLOCKS[0]                       # バリュー① ブロック先頭行
    vals = []

    def put(period, r0, texts):
        for i, t in enumerate(texts):     # I列(=LDEF)の5行へ 100/90/80/70/60 の基準
            vals.append((f"{period}!{LDEF}{r0 + i}", [[t]]))

    put("上半期", q1, SATO_QUAL_CRIT["定性①"]["上半期"])
    put("上半期", q2, SATO_QUAL_CRIT["定性②"]["上半期"])
    put("上半期", v1, SATO_QUAL_CRIT["バリュー①"]["全期"])
    put("通期", q1, SATO_QUAL_CRIT["定性①"]["通期"])
    put("通期", q2, SATO_QUAL_CRIT["定性②"]["通期"])
    put("通期", v1, SATO_QUAL_CRIT["バリュー①"]["全期"])
    put("下半期", v1, SATO_QUAL_CRIT["バリュー①"]["全期"])   # 定性①②の下半期は後日（プレースホルダのまま）
    write_values(svc, SS, vals)
    print("  佐藤の評価基準（5段階・期別）: seeded")


def build_eval(svc, SS, gid, period, member, quant, qual, value):
    # 新列順：目標情報 B:F（縦結合）｜ OTE参照 G達成率/Hしきい値¥/I評価点・定義（行展開）｜
    #          採点 J重み/K自己入力/L率/M自己点/N上長入力/O率/P上長点/Q採点方式（縦結合）｜ R ヘルパ(非表示)
    full = (period == "通期")

    def tgt_for(g):
        t = g["tgt"]
        return t.get(period, "") if isinstance(t, dict) else t

    def pt_quant(r0, sales, idx):
        # K自己入力(=実績)／L達成率／M自己点／N上長入力(実績ミラー)／O達成率／P上長点
        if sales:
            rng_k, rng_t = MR[period]
            rg = rng_k if idx == 0 else rng_t
            k = f'=IF(COUNT(月次振り返り!{rg})=0,"",SUM(月次振り返り!{rg}))'   # 売上=月次集計
        else:
            k = ""  # metric=実績を手入力
        sr = f'=IF(OR({LSIN}{r0}="",{LTGT}{r0}=""),"",IFERROR({LSIN}{r0}/{LTGT}{r0},""))'
        r = f"{LSIN}{r0}/{LTGT}{r0}"
        ratio = f"ROUND({r}*100,1)"   # 比率＝実績÷目標×100（連続・150%超も青天井）
        # 段階＝OTE公式 支給率テーブル準拠（達成率→評価点＝支給率×100）。150%超は青天井(150+(率-150))
        step = (f"IF({r}>=1.5,150+ROUND(({r}-1.5)*100,1),"
                f"IF({r}>=1.25,130,IF({r}>=1.01,115,IF({r}>=1,100,"
                f"IF({r}>=0.99,95,IF({r}>=0.97,90,IF({r}>=0.95,80,"
                f"IF({r}>=0.9,70,IF({r}>=0.85,60,IF({r}>=0.8,50,"
                f"IF({r}>=0.7,30,0)))))))))))")
        sp = (f'=IF(${LITEM}{r0}="","",IF({LSIN}{r0}="","未評価",'
              f'IFERROR(IF(${LMODE}{r0}="段階",{step},{ratio}),"目標未設定")))')
        bin_ = f'=IF({LSIN}{r0}="","",{LSIN}{r0})'
        br = f"={LSR}{r0}"
        bp = f"={LSP}{r0}"
        return k, sr, sp, bin_, br, bp

    def pt_rank(r0):
        rm = rankmap   # 段階数(3/5)に応じた写像
        if full:
            sp = (f'=IF(${LITEM}{r0}="","",IF({LSIN}{r0}<>"",{rm(f"{LSIN}{r0}")},'
                  f'IF(OR(\'上半期\'!{LSP}{r0}="未評価",\'下半期\'!{LSP}{r0}="未評価"),"未評価",'
                  f'IFERROR(AVERAGE(\'上半期\'!{LSP}{r0},\'下半期\'!{LSP}{r0}),"未評価"))))')
            bp = (f'=IF(${LITEM}{r0}="","",IF({LBIN}{r0}<>"",{rm(f"{LBIN}{r0}")},'
                  f'IF(OR(\'上半期\'!{LBP}{r0}="未評価",\'下半期\'!{LBP}{r0}="未評価"),"未評価",'
                  f'IFERROR(AVERAGE(\'上半期\'!{LBP}{r0},\'下半期\'!{LBP}{r0}),"未評価"))))')
        else:
            sp = f'=IF(${LITEM}{r0}="","",IF({LSIN}{r0}="","未評価",{rm(f"{LSIN}{r0}")}))'
            bp = f'=IF(${LITEM}{r0}="","",IF({LBIN}{r0}="","未評価",{rm(f"{LBIN}{r0}")}))'
        return sp, bp

    def subtotal(pcol, blocks):
        # 使用ブロック(目標名非空)のウェイト(J)正規化平均。未評価が1つでもあれば未評価。
        unrated = "+".join(f'(N(${LITEM}{r}<>"")*N({pcol}{r}="未評価"))' for r in blocks)
        wsum = "+".join(f'(N(${LITEM}{r}<>"")*N(${LW}{r}))' for r in blocks)
        num = "+".join(f'(N(${LITEM}{r}<>"")*N(${LW}{r})*N({pcol}{r}))' for r in blocks)
        return (f'=IF(({unrated})>0,"未評価",'
                f'IF(({wsum})=0,"未評価",'
                f'ROUND(({num})/({wsum}),1)))')

    def wsum_display(blocks):
        return "=" + "+".join(f'N(${LITEM}{r}<>"")*N(${LW}{r})' for r in blocks)

    title = f"目標管理シート｜{member}　2026年度・{period}"
    quant_legend = ("定量は 評価点＝達成率%（70%→70点／100%→100点／超過で100点超・上限なし）。"
                    if QUANT_LINEAR else "定量は超過で100点超（OTE支給率テーブル）。")
    legend = ("100点＝目標達成が基準。" + quant_legend +
              f"定性・バリューは{qual_scale_text()}。"
              "定性・バリューの「評価基準（各段階の定義）」は黄色セルに記入（自分と上長で定義・上期/下期は各タブで別々に・HRブレインへ自動反映）。"
              "総合点＝定量60%＋定性20%＋バリュー20%（各カテゴリ内は目標ごとのウェイトで加重）。")
    if full:
        legend = "通期は上半期・下半期から自動集計。" + legend

    role_strip = ('="役職： "&IF(\'ダッシュボード\'!C5="（役職を選択）","（未設定）",'
                  '\'ダッシュボード\'!C5)&"　｜　報酬区分： "&\'ダッシュボード\'!C6&'
                  '"　｜　Base:Variable "&\'ダッシュボード\'!F6&"　｜　支給： "&\'ダッシュボード\'!H6')
    vals = [(f"{period}!B1", [[title]]), (f"{period}!B2", [[legend]]), (f"{period}!B3", [[role_strip]])]
    hdr = ["区分", "目標項目", "目標（SMART）", "アクションプラン", "目標値",
           "達成率", "しきい値(¥)", "評価点・状態",
           "ウェイト", "自己入力", "自己率", "自己点", "上長入力", "上長率", "上長点", "採点方式"]

    def quant_thresholds(r0):
        # 代表ウェイポイント（5行）：達成率ラベル(G) / しきい値¥=目標×割合(H) / 評価点表記(I)
        # QUANT_LINEAR＝リニア表示（達成率＝評価点・佐藤）／既定＝OTE支給率テーブル（雛形）
        wp = LINEAR_WAYPOINTS if QUANT_LINEAR else OTE_WAYPOINTS
        return [[label, f'=IF(ISNUMBER(${LTGT}{r0}),${LTGT}{r0}*{ratio},"")', pts]
                for label, ratio, pts in wp]

    def qual_thresholds(crit):
        if QUAL_LEVELS == 5:
            # 5段階：レベル(G)＋基準記入欄(I・後段で具体基準を_seed_qual_criteriaが上書き)
            return [[lv, "", "（基準を記入）"] for lv in RANK5_LEVELS]
        return [[sym, "", qual_def(crit, sym)] for sym in RANK3_SYMS]

    def help_join(r0, h, money=False, quant=False):
        # ランク（しきい値）：評価点 形式。しきい値が数値ならカッコ書きで併記（売上は¥）。
        # quant=True（HRブレイン記載用）＝経営層との齟齬防止のため「〜100%達成」までに絞る：
        #   OTEウェイポイントの下位3行（100%達成/90-94/70-79）のみ join し、100%超は注記1行で補う。
        #   （フルOTEテーブル＝150/125…とその計算は本シートのG:I参照とM/P点に残す）
        amt = (f'"¥"&TEXT({LTHR}{{rr}},"#,##0")' if money else f'TEXT({LTHR}{{rr}},"#,##0")')
        rows = range(r0 + 2, r0 + h) if quant else range(r0, r0 + h)
        parts = []
        for rr in rows:
            thr = (f'IF({LTHR}{rr}="","",IF(ISNUMBER({LTHR}{rr}),'
                   f'"（"&{amt.format(rr=rr)}&"）","（"&{LTHR}{rr}&"）"))')
            parts.append(f'{LRANK}{rr}&{thr}&"："&{LDEF}{rr}')
        joined = "TEXTJOIN(CHAR(10),TRUE," + ",".join(parts) + ")"
        if quant:
            note = ('"100%＝達成＝100点が基準。評価点＝達成率%（70%→70点）。100%超も達成率分だけ加点（上限なし）。"'
                    if QUANT_LINEAR else
                    '"100%＝達成＝100点が基準。100%超は実績に応じOTE支給率で自動加点（本シートで算出）。"')
            return f"={joined}&CHAR(10)&{note}"
        return "=" + joined

    def goal_row(r0, g, idx):
        vals.append((f"{period}!{LKU}{r0}", [[g["ku"], g["item"], g["smart"], g["ap"], tgt_for(g)]]))  # B:F
        vals.append((f"{period}!{LW}{r0}", [[g["w"]]]))   # J ウェイト
        if g["kind"] in ("sales", "metric"):
            k, sr, sp, bin_, br, bp = pt_quant(r0, g["kind"] == "sales", idx)
            vals.append((f"{period}!{LSIN}{r0}", [[k, sr, sp, bin_, br, bp]]))   # K..P
            vals.append((f"{period}!{LMODE}{r0}", [[g.get("mode", "比率")]]))    # Q 採点方式
            if g["item"]:
                vals.append((f"{period}!{LRANK}{r0}", quant_thresholds(r0)))     # G/H/I × 5（OTE）
                vals.append((f"{period}!{LHELP}{r0}", [[help_join(r0, QH, money=(g["kind"] == "sales"), quant=True)]]))
        else:
            sp, bp = pt_rank(r0)
            vals.append((f"{period}!{LSP}{r0}", [[sp]]))   # M 自己点
            vals.append((f"{period}!{LBP}{r0}", [[bp]]))   # P 上長点
            if g["item"]:
                vals.append((f"{period}!{LRANK}{r0}", qual_thresholds(g["crit"])))  # G/_/I × 3
                vals.append((f"{period}!{LHELP}{r0}", [[help_join(r0, TH)]]))

    def section(ban, hdr_r, blocks, sub, label, cat):
        vals.append((f"{period}!B{ban}", [[label]]))
        vals.append((f"{period}!B{hdr_r}", [hdr]))
        for idx, r0 in enumerate(blocks):
            goal_row(r0, cat[idx], idx)
        vals.append((f"{period}!B{sub}", [["小計"]]))
        vals.append((f"{period}!{LDEF}{sub}", [["ウェイト合計 →"]]))   # I（J=合計の直前）
        vals.append((f"{period}!{LW}{sub}", [[wsum_display(blocks)]]))     # J ウェイト合計
        vals.append((f"{period}!{LSP}{sub}", [[subtotal(LSP, blocks)]]))   # M 自己点小計
        vals.append((f"{period}!{LBP}{sub}", [[subtotal(LBP, blocks)]]))   # P 上長点小計

    section(Q_BAN, Q_HDR, Q_BLOCKS, Q_SUB, "■ 定量目標　［配点60%］", quant)
    section(QL_BAN, QL_HDR, QL_BLOCKS, QL_SUB, "■ 定性目標　［配点20%］", qual)
    section(V_BAN, V_HDR, V_BLOCKS, V_SUB, "■ バリュー　［配点20%］", value)

    # カード（ラベルB:E / 自己F:H / 上長I:L はカード内レイアウト）。内訳は各小計の M(自己)/P(上長)を参照。
    S = SETROW
    cs, cb = LCSELF, LCBOSS   # 自己=D / 上長=E
    vals += [
        (f"{period}!B{CARD}", [["■ 総合点"]]),
        (f"{period}!{cs}{CARD_HDR}", [["自己評価"]]), (f"{period}!{cb}{CARD_HDR}", [["上長評価"]]),
        (f"{period}!B{HERO}", [["総合点（100点＝目標達成）"]]),
        (f"{period}!{cs}{HERO}", [[f'=IF(OR({cs}{B_QUANT}="未評価",{cs}{B_QUAL}="未評価",{cs}{B_VALUE}="未評価"),"未評価",'
                                   f'ROUND({cs}{B_QUANT}*$E${S}+{cs}{B_QUAL}*$G${S}+{cs}{B_VALUE}*$I${S},1))']]),
        (f"{period}!{cb}{HERO}", [[f'=IF(OR({cb}{B_QUANT}="未評価",{cb}{B_QUAL}="未評価",{cb}{B_VALUE}="未評価"),"未評価",'
                                   f'ROUND({cb}{B_QUANT}*$E${S}+{cb}{B_QUAL}*$G${S}+{cb}{B_VALUE}*$I${S},1))']]),
        (f"{period}!B{BREAK}", [["― 内訳（評価軸別・配点）―"]]),
        (f"{period}!B{B_QUANT}", [["定量 評価点　［60%］"]]), (f"{period}!{cs}{B_QUANT}", [[f"={LSP}{Q_SUB}"]]), (f"{period}!{cb}{B_QUANT}", [[f"={LBP}{Q_SUB}"]]),
        (f"{period}!B{B_QUAL}", [["定性 評価点　［20%］"]]), (f"{period}!{cs}{B_QUAL}", [[f"={LSP}{QL_SUB}"]]), (f"{period}!{cb}{B_QUAL}", [[f"={LBP}{QL_SUB}"]]),
        (f"{period}!B{B_VALUE}", [["バリュー評価点　［20%］"]]), (f"{period}!{cs}{B_VALUE}", [[f"={LSP}{V_SUB}"]]), (f"{period}!{cb}{B_VALUE}", [[f"={LBP}{V_SUB}"]]),
        (f"{period}!B{S}", [["【設定・比率】", "", "定量", 0.6, "定性", 0.2, "バリュー", 0.2, "合計", f"=$E${S}+$G${S}+$I${S}"]]),
    ]
    if full:
        vals.append((f"{period}!B{REFROW}", [[
            f'="参考：半期の総合点（上長）　　上半期 "&IF(\'上半期\'!{cb}{HERO}="未評価","未評価",TEXT(\'上半期\'!{cb}{HERO},"0.0"))&"  ／  下半期 "&IF(\'下半期\'!{cb}{HERO}="未評価","未評価",TEXT(\'下半期\'!{cb}{HERO},"0.0"))']]))

    write_values(svc, SS, vals)
    _format_eval(svc, SS, gid, full, quant, qual, value)
    # ドロップダウン：定量=N列(比率/段階) ／ 定性・バリュー=H・K(◎◯△)。ブロック先頭セルへ。
    dv = []

    def add_dv(r0, kind):
        if kind in ("sales", "metric"):
            dv.append({"setDataValidation": {"range": rng(gid, r0, r0, cMODE, cMODE), "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ["比率", "段階"]]},
                "strict": True, "showCustomUi": True}}})
            return
        qlv = RANK5_LEVELS if QUAL_LEVELS == 5 else RANK3_SYMS   # 定性=5段階(100%〜60%)or3段階(◎◯△)
        for c in (cSIN, cBIN):
            dv.append({"setDataValidation": {"range": rng(gid, r0, r0, c, c), "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in qlv]},
                "strict": True, "showCustomUi": True}}})
    for idx, r0 in enumerate(Q_BLOCKS):
        add_dv(r0, quant[idx]["kind"])
    for idx, r0 in enumerate(QL_BLOCKS):
        add_dv(r0, qual[idx]["kind"])
    for idx, r0 in enumerate(V_BLOCKS):
        add_dv(r0, value[idx]["kind"])
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": dv}).execute()
    print(f"  {period}: done")


def _format_eval(svc, SS, gid, full, quant, qual, value):
    # 旧4スロット版の結合・データ検証を全消去してから再構築（点列に残る％書式の残骸も後段で上書き）
    R = [grid_off(gid), unmerge(gid, 1, REFROW + 2, 0, cHELP),
         {"setDataValidation": {"range": rng(gid, 1, REFROW + 2, 0, cHELP)}}]
    widths = {0: 28, cKU: 66, cITEM: 116, cSMART: 270, cAP: 226, cTGT: 104,
              cRANK: 72, cTHR: 116, cDEF: 188,
              cW: 60, cSIN: 92, cSR: 60, cSP: 54, cBIN: 92, cBR: 60, cBP: 54, cMODE: 70,
              cHELP: 20}
    for c, w in widths.items():
        R.append(col_width(gid, c, w))
    R.append({"updateDimensionProperties": {
        "range": {"sheetId": gid, "dimension": "COLUMNS", "startIndex": cHELP, "endIndex": cHELP + 1},
        "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    R.append(repeat_fmt(gid, 1, REFROW + 1, 0, EVAL_LASTCOL,
                        {"backgroundColor": WHITE, "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE",
                         "wrapStrategy": "OVERFLOW_CELL",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    R.append(merge(gid, 1, 1, 1, EVAL_LASTCOL))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 14, True)}, "userEnteredFormat.textFormat"))
    R.append(set_borders(gid, 1, 1, 1, EVAL_LASTCOL, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(gid, 1, 38))
    R.append(merge(gid, 2, 2, 1, EVAL_LASTCOL))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False), "wrapStrategy": "WRAP"},
                        "userEnteredFormat(textFormat,wrapStrategy)"))
    R.append(row_height(gid, 2, 34))
    # 役職ストリップ（行3・ダッシュボードの役職パネルを参照）
    R.append(merge(gid, 3, 3, 1, EVAL_LASTCOL))
    R.append(repeat_fmt(gid, 3, 3, 1, 1, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 10, True),
                                          "verticalAlignment": "MIDDLE", "horizontalAlignment": "LEFT"},
                        "userEnteredFormat(backgroundColor,textFormat,verticalAlignment,horizontalAlignment)"))
    R.append(set_borders(gid, 3, 3, 1, 1, left=border("SOLID_THICK", RED)))
    R.append(set_borders(gid, 3, 3, 1, EVAL_LASTCOL, top=border("SOLID", BORDER_LT), bottom=border("SOLID", BORDER_LT),
                         right=border("SOLID", BORDER_LT)))
    R.append(row_height(gid, 3, 26))
    secs = [(Q_BAN, Q_HDR, Q_BLOCKS, QH, Q_SUB, "quant", quant),
            (QL_BAN, QL_HDR, QL_BLOCKS, TH, QL_SUB, "qual", qual),
            (V_BAN, V_HDR, V_BLOCKS, TH, V_SUB, "value", value)]
    for ban, hr, blocks, bh, sub, cat, goals in secs:
        is_q = (cat == "quant")
        R += banner(gid, ban, 1, EVAL_LASTCOL)
        R.append(repeat_fmt(gid, hr, hr, 1, EVAL_LASTCOL,
                            {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9, True), "wrapStrategy": "WRAP",
                             "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(backgroundColor,textFormat,wrapStrategy,horizontalAlignment,verticalAlignment)"))
        R.append(repeat_fmt(gid, hr, hr, cITEM, cAP, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
        R.append(row_height(gid, hr, 32))
        for bi, r0 in enumerate(blocks):
            re_ = r0 + bh - 1
            active = bool(goals[bi]["item"])
            is_sales = (is_q and quant[bi]["kind"] == "sales")
            # 縦結合：B:F（目標情報）と J:Q（採点）。G:I（OTE参照）は行展開＝非結合。
            for c in list(range(cKU, cTGT + 1)) + list(range(cW, cMODE + 1)):
                R.append(merge(gid, r0, re_, c, c))
            # 地：B:F＝WRAP/TOP、J:Q＝中央/MIDDLE・素の数値（旧％/¥書式の残骸を一掃）
            R.append(repeat_fmt(gid, r0, re_, cKU, cTGT, {"wrapStrategy": "WRAP", "verticalAlignment": "TOP",
                                                          "textFormat": tf(TEXT_DARK, 10, False)},
                                "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)"))
            R.append(repeat_fmt(gid, r0, re_, cW, cMODE, {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                                                          "textFormat": tf(TEXT_DARK, 10, False),
                                                          "numberFormat": {"type": "NUMBER"}},
                                "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat,numberFormat)"))
            # 区分(B)：中央・折返さない（「バリュー①」が複数行化しないようOVERFLOW）
            R.append(repeat_fmt(gid, r0, re_, cKU, cKU, {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                                                         "wrapStrategy": "OVERFLOW_CELL", "textFormat": tf(TEXT_GREY, 9, True)},
                                "userEnteredFormat(horizontalAlignment,verticalAlignment,wrapStrategy,textFormat)"))
            if not active:
                # 空き枠：淡グレーで沈める（黄/赤ティント無し・行も詰める）。目標名を入れると有効化。
                R.append(repeat_fmt(gid, r0, re_, cKU, cMODE, {"backgroundColor": {"red": 0.966, "green": 0.966, "blue": 0.966},
                                                               "textFormat": tf(TEXT_GREY, 9, False)},
                                    "userEnteredFormat(backgroundColor,textFormat)"))
                R.append(repeat_fmt(gid, r0, re_, cKU, cKU, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
                R.append(repeat_fmt(gid, r0, re_, cRANK, cDEF, {"backgroundColor": {"red": 0.975, "green": 0.975, "blue": 0.975}},
                                    "userEnteredFormat.backgroundColor"))
                for tr in range(r0, re_ + 1):
                    R.append(row_height(gid, tr, 22))
                continue
            # ゼブラは廃止（採点セルに灰が乗って黄入力とまだらに見えるため）。
            # 色は3種に統一：黄＝入力する所／白＝自動計算／薄灰＝OTE参照。ブロック区切りは箱の細罫で表現。
            # 入力黄：D(SMART)・E(AP)・F(目標値)
            for ic in (cSMART, cAP, cTGT):
                R.append(repeat_fmt(gid, r0, re_, ic, ic, {"backgroundColor": YELLOW}, "userEnteredFormat.backgroundColor"))
            # ウェイト(J)＝黄・％
            R.append(repeat_fmt(gid, r0, re_, cW, cW, {"backgroundColor": YELLOW,
                                                       "numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                                "userEnteredFormat(backgroundColor,numberFormat)"))
            # 自己入力(K)・上長入力(N)：定量はK/Nとも白で統一（売上=月次自動／metric実績の手入力も白）、
            # 定性・バリューはK/Nとも黄（◎◯△を自己・上長で手入力）。→ 列内で黄/白が混ざらない。
            bg_in = WHITE if is_q else YELLOW
            for ic in (cSIN, cBIN):
                R.append(repeat_fmt(gid, r0, re_, ic, ic, {"backgroundColor": bg_in}, "userEnteredFormat.backgroundColor"))
            # 達成率 L/O＝％（定量のみ）
            if is_q:
                for pc in (cSR, cBR):
                    R.append(repeat_fmt(gid, r0, re_, pc, pc, {"numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                                        "userEnteredFormat.numberFormat"))
            # 点 M/P＝太字
            for tc in (cSP, cBP):
                R.append(repeat_fmt(gid, r0, re_, tc, tc, {"textFormat": tf(TEXT_DARK, 11, True)}, "userEnteredFormat.textFormat"))
            # 採点方式 Q＝定量のみ黄
            if is_q:
                R.append(repeat_fmt(gid, r0, re_, cMODE, cMODE, {"backgroundColor": YELLOW, "textFormat": tf(TEXT_DARK, 9, True)},
                                    "userEnteredFormat(backgroundColor,textFormat)"))
            # ¥（売上ブロック）：目標値F・自己入力K・上長入力N
            if is_sales:
                for cc in (cTGT, cSIN, cBIN):
                    R.append(repeat_fmt(gid, r0, re_, cc, cc, {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}},
                                        "userEnteredFormat.numberFormat"))
            elif is_q:
                R.append(repeat_fmt(gid, r0, re_, cTGT, cTGT, {"numberFormat": {"type": "NUMBER"}},
                                    "userEnteredFormat.numberFormat"))
            # ---- OTE参照ブロック（G達成率/Hしきい値¥/I評価点・定義／行展開・非結合） ----
            R.append(repeat_fmt(gid, r0, re_, cRANK, cDEF, {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE",
                                                            "textFormat": tf(TEXT_DARK, 9, False),
                                                            "backgroundColor": {"red": 0.992, "green": 0.992, "blue": 0.992}},
                                "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat,backgroundColor)"))
            R.append(repeat_fmt(gid, r0, re_, cRANK, cRANK, {"horizontalAlignment": "CENTER", "wrapStrategy": "OVERFLOW_CELL",
                                                             "textFormat": tf(TEXT_GREY, 10, True)},
                                "userEnteredFormat(horizontalAlignment,wrapStrategy,textFormat)"))
            R.append(repeat_fmt(gid, r0, re_, cTHR, cTHR, {"horizontalAlignment": "RIGHT", "textFormat": tf(TEXT_GREY, 9, False)},
                                "userEnteredFormat(horizontalAlignment,textFormat)"))
            R.append(repeat_fmt(gid, r0, re_, cDEF, cDEF, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
            if is_q:
                thr_nf = {"type": "CURRENCY", "pattern": "¥#,##0"} if is_sales else {"type": "NUMBER"}
                R.append(repeat_fmt(gid, r0, re_, cTHR, cTHR, {"numberFormat": thr_nf},
                                    "userEnteredFormat.numberFormat"))
            elif active:
                # 定性/バリュー：評価基準（◎◯△の定義）を黄色の記入欄に。
                # 上期/下期は各タブで別々に・自分と上長で「どこまで目指すか」を定義（HRブレインへ自動反映）。
                R.append(repeat_fmt(gid, r0, re_, cDEF, cDEF, {"backgroundColor": YELLOW}, "userEnteredFormat.backgroundColor"))
            # 達成（基準）行を淡赤で強調：定量=100%行(r0+2)／定性=◎行(r0=100点・記入欄Iは黄のまま記号Gのみ着色)
            base_row = r0 + 2 if is_q else r0
            hl_end = cDEF if is_q else cRANK
            R.append(repeat_fmt(gid, base_row, base_row, cRANK, hl_end, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 9, True)},
                                "userEnteredFormat(backgroundColor,textFormat)"))
            # ブロック境界（下辺をやや強い細罫で・ゼブラ廃止の代替）
            R.append(set_borders(gid, re_, re_, cKU, cMODE, bottom=border("SOLID", BORDER_GREY)))
            for tr in range(r0, re_ + 1):
                R.append(row_height(gid, tr, 30 if is_q else 34))
        # 小計
        R.append(repeat_fmt(gid, sub, sub, 1, EVAL_LASTCOL, {"backgroundColor": SUBTOTAL_BG, "textFormat": tf(TEXT_DARK, 10, True)},
                            "userEnteredFormat(backgroundColor,textFormat)"))
        R.append(repeat_fmt(gid, sub, sub, cW, cW, {"horizontalAlignment": "CENTER",
                                                    "numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                            "userEnteredFormat(horizontalAlignment,numberFormat)"))
        # 「使用ブロックのウェイト計 →」を100%(J)の直前(I)で右寄せ
        R.append(repeat_fmt(gid, sub, sub, cDEF, cDEF, {"horizontalAlignment": "RIGHT", "wrapStrategy": "OVERFLOW_CELL",
                                                        "textFormat": tf(TEXT_GREY, 9, False)},
                            "userEnteredFormat(horizontalAlignment,wrapStrategy,textFormat)"))
        for cc in (cSP, cBP):
            R.append(repeat_fmt(gid, sub, sub, cc, cc, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 11, True),
                                                        "numberFormat": {"type": "NUMBER"}},
                                "userEnteredFormat(horizontalAlignment,textFormat,numberFormat)"))
        R.append(box(gid, hr, sub, 1, EVAL_LASTCOL))
        # 縦区切り：F|G（目標情報とOTE参照）／I|J（OTEと採点）／M|N（自己と上長）
        for sc in (cRANK, cW, cBIN):
            R.append(set_borders(gid, hr, sub, sc, sc, left=border("SOLID_MEDIUM", BORDER_STRONG)))
        # セクション間の余白行（小計の1行下）＝細い白の余白に統一（中途半端な隙間の解消）
        R.append(repeat_fmt(gid, sub + 1, sub + 1, 0, EVAL_LASTCOL, {"backgroundColor": WHITE},
                            "userEnteredFormat.backgroundColor"))
        R.append(row_height(gid, sub + 1, 12))

    # ---- カード（ラベルB:C / 自己D / 上長E：幅広のD/Eに大きな数値） ----
    R.append(merge(gid, CARD, CARD, 1, EVAL_LASTCOL))
    R.append(repeat_fmt(gid, CARD, CARD, 1, EVAL_LASTCOL, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 12, True)},
                        "userEnteredFormat(backgroundColor,textFormat)"))
    R.append(set_borders(gid, CARD, CARD, 1, 1, left=border("SOLID_THICK", RED)))
    R.append(row_height(gid, CARD, 30))
    # ヘッダ：B:C（空）/ D 自己評価 / E 上長評価
    R.append(merge(gid, CARD_HDR, CARD_HDR, 1, 2))
    R.append(repeat_fmt(gid, CARD_HDR, CARD_HDR, 1, 4, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_GREY, 9, True),
                                                        "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    # ヒーロー：B:C ラベル / D・E 大きな総合点
    R.append(merge(gid, HERO, HERO, 1, 2))
    R.append(repeat_fmt(gid, HERO, HERO, 1, 2, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 11, True),
                                                "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,verticalAlignment)"))
    R.append(repeat_fmt(gid, HERO, HERO, 3, 4, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 22, True),
                                                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                                                "numberFormat": {"type": "NUMBER"}},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,numberFormat)"))
    R.append(row_height(gid, HERO, 48))
    R.append(merge(gid, BREAK, BREAK, 1, 4))
    R.append(repeat_fmt(gid, BREAK, BREAK, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    for r in (B_QUANT, B_QUAL, B_VALUE):
        R.append(merge(gid, r, r, 1, 2))
        R.append(repeat_fmt(gid, r, r, 3, 4, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 12, False),
                                              "numberFormat": {"type": "NUMBER"}},
                            "userEnteredFormat(horizontalAlignment,textFormat,numberFormat)"))
        R.append(row_height(gid, r, 24))
    R.append(box(gid, CARD_HDR, B_VALUE, 1, 4))
    R.append(set_borders(gid, CARD_HDR, B_VALUE, 3, 3, left=border("SOLID", BORDER_GREY)))         # C|D（ラベル|自己）
    R.append(set_borders(gid, CARD_HDR, B_VALUE, 4, 4, left=border("SOLID_MEDIUM", BORDER_STRONG)))  # D|E（自己|上長）
    # 設定・比率ストリップ（定量=E 定性=G バリュー=I／合計=K自動）。E/G/I＝編集可（黄）、K＝自動計算（白）
    R.append(merge(gid, SETROW, SETROW, 1, 2))
    R.append(repeat_fmt(gid, SETROW, SETROW, 1, 2, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9, True),
                                                    "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    for lc in (3, 5, 7, 9):
        R.append(repeat_fmt(gid, SETROW, SETROW, lc, lc, {"textFormat": tf(TEXT_GREY, 9, False), "horizontalAlignment": "RIGHT"},
                            "userEnteredFormat(textFormat,horizontalAlignment)"))
    for vc in (4, 6, 8):   # 定量/定性/バリューの配点＝編集可（黄）
        R.append(repeat_fmt(gid, SETROW, SETROW, vc, vc, {"backgroundColor": YELLOW, "textFormat": tf(TEXT_DARK, 10, True),
                                                          "horizontalAlignment": "CENTER",
                                                          "numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                            "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,numberFormat)"))
    R.append(repeat_fmt(gid, SETROW, SETROW, 10, 10, {"backgroundColor": WHITE, "textFormat": tf(RED, 10, True),  # 合計＝自動（100%確認用）
                                                      "horizontalAlignment": "CENTER",
                                                      "numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,numberFormat)"))
    R.append(box(gid, SETROW, SETROW, 1, 10, inner=False))
    R.append(row_height(gid, SETROW, 26))
    if full:
        R.append(merge(gid, REFROW, REFROW, 1, 11))
        R.append(repeat_fmt(gid, REFROW, REFROW, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    # ブロックは縦結合＋明示行高のため auto-resize は行わない（結合と競合するため）


# ============================================================
#  ダッシュボード
# ============================================================
def build_dashboard(svc, SS, gid, member="（メンバー名）"):
    # 全セクション B:I（8列＝4グループ×2列：項目/役職=B:C、通期=D:E、上半期=F:G、下半期=H:I）に統一。
    mb = "ダッシュボード"
    LAST = 8                                  # I列（content右端）
    PCOL = [("通期", "D"), ("上半期", "F"), ("下半期", "H")]   # 各期の自己列（+1が上長列）
    PGRP = {"通期": (3, 4), "上半期": (5, 6), "下半期": (7, 8)}  # merge用 列番号(B=1)：D:E / F:G / H:I
    ROWS = [("総合点", HERO), ("定量 評価点", B_QUANT), ("定性 評価点", B_QUAL),
            ("バリュー評価点", B_VALUE)]
    RB, P0 = 4, 5                             # 役職パネル banner / 5-7
    SB, PH, SH, S0 = 9, 10, 11, 12            # サマリー banner / 期ヘッダ / 自己上長ヘッダ / データ先頭
    SEND = S0 + len(ROWS) - 1                 # 16
    GB, GH, G0 = SEND + 2, SEND + 3, SEND + 4  # 18 / 19 / 20 グラフ banner/ヘッダ/データ
    GEND = G0 + len(ROWS) - 1                 # 24
    MB, MH, M0 = GEND + 9, GEND + 10, GEND + 11  # 33 / 34 / 35 役職マスタ
    MEND = M0 + len(ROLE_MASTER) - 1          # 47

    def look(col):
        return f'=IFERROR(INDEX(${col}${M0}:${col}${MEND},MATCH($C${P0},$B${M0}:$B${MEND},0)),"")'

    vals = [
        (f"{mb}!B1", [[f"目標管理シート｜{member}　2026年度　ダッシュボード"]]),
        (f"{mb}!B2", [["役職・報酬区分と、通期・上半期・下半期の評価サマリー（自己評価／上長評価）。"]]),
        # 役職・報酬区分パネル
        (f"{mb}!B{RB}", [["■ 役職・報酬区分（OTE設定）"]]),
        (f"{mb}!B{P0}", [["役職を選択 →"]]), (f"{mb}!C{P0}", [["（役職を選択）"]]),
        (f"{mb}!B{P0+1}", [["報酬区分"]]), (f"{mb}!C{P0+1}", [[look("C")]]),
        (f"{mb}!D{P0+1}", [["Base : Variable"]]), (f"{mb}!F{P0+1}", [[look("D")]]),
        (f"{mb}!G{P0+1}", [["支給"]]), (f"{mb}!H{P0+1}", [[look("E")]]),
        (f"{mb}!B{P0+2}", [["評価方式"]]),
        (f"{mb}!C{P0+2}", [['=IF($C${0}="OTE","スプリント型：達成率→OTE支給率で採点（日次/月次で数字が出る職種）",'
                            'IF($C${0}="MBO","プロジェクト型：定量60%＋定性20%＋バリュー20%（×会社業績係数・半期の戦略的成果）",'
                            '"役職を選択してください"))'.format(P0 + 1)]]),
        # 評価サマリー（クロス期間表）
        (f"{mb}!B{SB}", [["■ 評価サマリー（自己／上長・期別）"]]),
        (f"{mb}!B{PH}", [["項目"]]),   # 項目ヘッダ＝B:C を PH:SH 縦結合（アンカー=PH行）
    ]
    for p, sc in PCOL:
        vals.append((f"{mb}!{sc}{PH}", [[p]]))         # 期ヘッダ（自己列に・上で merge）
        vals.append((f"{mb}!{sc}{SH}", [["自己", "上長"]]))   # 自己/上長
    for i, (label, row) in enumerate(ROWS):
        r = S0 + i
        vals.append((f"{mb}!B{r}", [[label]]))
        for p, sc in PCOL:
            vals.append((f"{mb}!{sc}{r}", [[f"='{p}'!{LCSELF}{row}", f"='{p}'!{LCBOSS}{row}"]]))
    # グラフ用データ（評価軸 × 通期/上半期/下半期 上長点）＋チャート
    short = {"総合点": "総合", "定量 評価点": "定量", "定性 評価点": "定性", "バリュー評価点": "バリュー"}
    vals.append((f"{mb}!B{GB}", [["■ 評価点グラフ（上長評価・期別）"]]))
    vals.append((f"{mb}!B{GH}", [["評価軸", "通期", "上半期", "下半期"]]))
    for i, (label, row) in enumerate(ROWS):
        vals.append((f"{mb}!B{G0 + i}", [[short[label], f"='通期'!{LCBOSS}{row}", f"='上半期'!{LCBOSS}{row}", f"='下半期'!{LCBOSS}{row}"]]))
    # 役職マスタ（B:C役職／D:E区分／F:G Base:Variable／H:I支給）
    vals.append((f"{mb}!B{MB}", [["■ 役職マスタ（参照：資料P7）"]]))
    vals += [(f"{mb}!B{MH}", [["役職"]]), (f"{mb}!D{MH}", [["区分"]]),
             (f"{mb}!F{MH}", [["Base : Variable"]]), (f"{mb}!H{MH}", [["支給"]])]
    for i, (rn, ku, ratio, pay) in enumerate(ROLE_MASTER):
        r = M0 + i
        vals += [(f"{mb}!B{r}", [[rn]]), (f"{mb}!D{r}", [[ku]]), (f"{mb}!F{r}", [[ratio]]), (f"{mb}!H{r}", [[pay]])]
    write_values(svc, SS, vals)

    R = [grid_off(gid), unmerge(gid, 1, MEND + 2, 0, 13)]
    for c, w in {0: 28, 1: 140, 2: 110, 3: 88, 4: 88, 5: 88, 6: 88, 7: 88, 8: 88}.items():
        R.append(col_width(gid, c, w))
    R.append(repeat_fmt(gid, 1, MEND + 1, 0, LAST,
                        {"backgroundColor": WHITE, "verticalAlignment": "MIDDLE", "wrapStrategy": "OVERFLOW_CELL",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    R.append(merge(gid, 1, 1, 1, LAST))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 14, True)}, "userEnteredFormat.textFormat"))
    R.append(set_borders(gid, 1, 1, 1, LAST, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(gid, 1, 38))
    R.append(merge(gid, 2, 2, 1, LAST))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    # --- 役職パネル（B:I） ---
    R += banner(gid, RB, 1, LAST)
    for lc in (1, 3, 6):  # row6 ラベル列（B=報酬区分 / D=Base:Variable / G=支給）
        R.append(repeat_fmt(gid, P0 + 1, P0 + 1, lc, lc, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT"},
                            "userEnteredFormat(textFormat,horizontalAlignment)"))
    for lr in (P0, P0 + 2):
        R.append(repeat_fmt(gid, lr, lr, 1, 1, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT",
                                                "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"))
    R.append(merge(gid, P0, P0, 2, LAST))   # 役職ドロップダウン C:I
    R.append(repeat_fmt(gid, P0, P0, 2, LAST, {"backgroundColor": YELLOW, "textFormat": tf(RED, 11, True),
                                               "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    R.append(merge(gid, P0 + 1, P0 + 1, 3, 4))   # Base:Variableラベル D:E
    R.append(merge(gid, P0 + 1, P0 + 1, 7, LAST))  # 支給値 H:I
    R.append(repeat_fmt(gid, P0 + 1, P0 + 1, 2, 2, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 11, True)},
                        "userEnteredFormat(horizontalAlignment,textFormat)"))
    R.append(repeat_fmt(gid, P0 + 1, P0 + 1, 3, 4, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT"},
                        "userEnteredFormat(textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(gid, P0 + 1, P0 + 1, 5, 5, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 11, True)},
                        "userEnteredFormat(horizontalAlignment,textFormat)"))
    R.append(repeat_fmt(gid, P0 + 1, P0 + 1, 7, 7, {"horizontalAlignment": "CENTER"}, "userEnteredFormat.horizontalAlignment"))
    R.append(merge(gid, P0 + 2, P0 + 2, 2, LAST))   # 評価方式 説明 C:I
    R.append(repeat_fmt(gid, P0 + 2, P0 + 2, 2, LAST, {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE",
                                                       "textFormat": tf(TEXT_DARK, 10, False)},
                        "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)"))
    R.append(box(gid, P0, P0 + 2, 1, LAST))
    R.append(row_height(gid, P0 + 2, 30))
    # --- 評価サマリー（クロス期間表 B:I） ---
    R += banner(gid, SB, 1, LAST)
    R.append(merge(gid, PH, SH, 1, 2))   # 「項目」B:C を2行ぶん（期ヘッダ行と自己上長行）
    R.append(repeat_fmt(gid, PH, SH, 1, 2, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                            "horizontalAlignment": "LEFT", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    for p, (c1, c2) in PGRP.items():
        R.append(merge(gid, PH, PH, c1, c2))
        R.append(repeat_fmt(gid, PH, PH, c1, c2, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                                  "horizontalAlignment": "CENTER"},
                            "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(gid, SH, SH, 3, LAST, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_GREY, 9, True),
                                               "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    for i in range(len(ROWS)):
        R.append(merge(gid, S0 + i, S0 + i, 1, 2))   # 項目 B:C
    R.append(repeat_fmt(gid, S0, SEND, 3, LAST, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 11, False),
                                                 "numberFormat": {"type": "NUMBER"}},
                        "userEnteredFormat(horizontalAlignment,textFormat,numberFormat)"))
    R.append(repeat_fmt(gid, S0, S0, 1, LAST, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 12, True)},
                        "userEnteredFormat(backgroundColor,textFormat)"))   # 総合点 行を強調
    R.append(row_height(gid, S0, 30))
    R.append(box(gid, PH, SEND, 1, LAST))
    for c in (3, 5, 7):   # 期グループの区切り（D/F/H の左）
        R.append(set_borders(gid, PH, SEND, c, c, left=border("SOLID_MEDIUM", BORDER_STRONG)))
    # --- 評価点グラフ（データ表 B:E ＋ 右隣チャート） ---
    R += banner(gid, GB, 1, LAST)
    R.append(repeat_fmt(gid, GH, GH, 1, 4, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                            "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(gid, GH, GH, 1, 1, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    R.append(repeat_fmt(gid, G0, GEND, 2, 4, {"horizontalAlignment": "CENTER", "numberFormat": {"type": "NUMBER"}},
                        "userEnteredFormat(horizontalAlignment,numberFormat)"))
    R.append(repeat_fmt(gid, G0, G0, 1, 4, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 10, True)},
                        "userEnteredFormat(backgroundColor,textFormat)"))
    R.append(box(gid, GH, GEND, 1, 4))
    # --- 役職マスタ（B:C役職/D:E区分/F:G Base:Variable/H:I支給） ---
    R += banner(gid, MB, 1, LAST)
    R.append(repeat_fmt(gid, MH, MH, 1, LAST, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                               "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    for (c1, c2) in [(1, 2), (3, 4), (5, 6), (7, 8)]:
        R.append(merge(gid, MH, MH, c1, c2))
    R.append(repeat_fmt(gid, MH, MH, 1, 2, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    for i in range(len(ROLE_MASTER)):
        r = M0 + i
        for (c1, c2) in [(1, 2), (3, 4), (5, 6), (7, 8)]:
            R.append(merge(gid, r, r, c1, c2))
        R.append(repeat_fmt(gid, r, r, 3, 8, {"horizontalAlignment": "CENTER"}, "userEnteredFormat.horizontalAlignment"))
        if i % 2 == 1:
            R.append(repeat_fmt(gid, r, r, 1, LAST, {"backgroundColor": ZEBRA}, "userEnteredFormat.backgroundColor"))
    R.append(box(gid, MH, MEND, 1, LAST))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    # 役職プルダウン（C5:I5＝ドロップダウン本体）
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": [{"setDataValidation": {
        "range": rng(gid, P0, P0, 2, LAST), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": r} for r in ROLE_NAMES]},
            "strict": False, "showCustomUi": True}}}]}).execute()
    # 既存チャート削除（冪等）→ 縦棒グラフを右隣に追加
    meta = svc.spreadsheets().get(spreadsheetId=SS, fields="sheets(properties(sheetId),charts(chartId))").execute()
    del_reqs = [{"deleteEmbeddedObject": {"objectId": ch["chartId"]}}
                for sh in meta["sheets"] if sh["properties"]["sheetId"] == gid for ch in sh.get("charts", [])]
    if del_reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": del_reqs}).execute()
    chart_req = {"addChart": {"chart": {
        "spec": {
            "title": "評価点（上長評価・期別）", "titleTextFormat": {"fontSize": 11, "bold": True},
            "basicChart": {
                "chartType": "COLUMN", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
                "axis": [{"position": "LEFT_AXIS", "title": "評価点"}],
                "domains": [{"domain": {"sourceRange": {"sources": [rng(gid, GH, GEND, 1, 1)]}}}],
                "series": [{"series": {"sourceRange": {"sources": [rng(gid, GH, GEND, c, c)]}},
                            "targetAxis": "LEFT_AXIS"} for c in (2, 3, 4)],
            }},
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": gid, "rowIndex": GH - 1, "columnIndex": 5},
            "offsetXPixels": 6, "offsetYPixels": 2, "widthPixels": 430, "heightPixels": 240}}
    }}}
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": [chart_req]}).execute()
    print("  ダッシュボード: done")


# ============================================================
#  評価基準 / 点数定義ガイド / HRブレイン貼付
# ============================================================
def build_kijun(svc, SS, gid, quant, qual, value):
    # ① OTE公式 支給率テーブル（全ロール共通）＋ ② 目標ごとの基準（各評価タブのR列サマリ参照＝単一ソース）
    GOAL_ROWS = ([Q_BLOCKS[i] for i, g in enumerate(quant) if g["item"]]
                 + [QL_BLOCKS[i] for i, g in enumerate(qual) if g["item"]]
                 + [V_BLOCKS[i] for i, g in enumerate(value) if g["item"]])  # 実目標のあるブロックのみ
    # 行位置：OTE表=6..(5+|OTE|)、目標基準=その2行下からヘッダ→明細
    OTE_R0 = 6
    OTE_END = OTE_R0 + len(OTE_TABLE) - 1
    GOAL_BAN = OTE_END + 2
    GOAL_HDR = GOAL_BAN + 1
    GOAL_R0 = GOAL_HDR + 1
    last = GOAL_R0 + len(GOAL_ROWS) - 1
    ote_done = OTE_R0 + 8   # 「100%（達成）」行（OTE_TABLE index 8）

    # OTE表の備考（E列）
    ote_notes = ["支給なし", "", "", "", "", "", "", "", "目標達成（基準）",
                 "アクセラレーター", "アクセラレーター", "上限なし（青天井）"]
    # 佐藤＝リニア既定（達成率＝評価点）。段階(OTE)は採点方式ドロップダウンに温存するため表は残し「段階モード時」と位置づける。
    quant_kijun = ("定量＝評価点＝達成率%（70%→70点・100%→100点・超過で100点超／上限なし）。"
                   "下のOTE表は採点方式＝『段階』を選んだとき用（既定は比率＝リニア）。"
                   if QUANT_LINEAR else
                   "定量＝OTE公式 支給率テーブル準拠（達成率→評価点＝支給率×100・150%超は青天井）。")
    ote_hdr = ("■ OTE支給率テーブル（採点方式＝『段階』選択時・参考）" if QUANT_LINEAR
               else "■ OTE支給率テーブル（全ロール共通・達成率→評価点）")
    rows = [
        ["評価基準｜100点＝目標達成が基準（定量は超過で100超・定性/バリューは達成100が上限）"],
        [f"{quant_kijun}　｜　定性・バリュー＝{qual_scale_text()}"],
        [],
        [ote_hdr],
        ["達成率", "支給率", "評価点", "備考"],
    ]
    rows += [list(t) + [ote_notes[i]] for i, t in enumerate(OTE_TABLE)]
    rows += [
        [],
        ["■ 目標ごとの基準（各評価タブのしきい値ブロックと自動連動）"],
        ["目標項目", "達成率＝評価点・¥目安（段階）"],
    ]
    for r in GOAL_ROWS:
        rows.append([f"='通期'!B{r}&\" \"&'通期'!C{r}", f"='通期'!R{r}"])
    write_values(svc, SS, [("評価基準!B1", rows)])

    R = [grid_off(gid), unmerge(gid, 1, last + 2, 0, 11)]
    for c, w in {0: 28, 1: 180, 2: 90, 3: 100, 4: 470}.items():   # B達成率/項目 C支給率 D評価点 E備考/定義
        R.append(col_width(gid, c, w))
    R.append(repeat_fmt(gid, 1, last + 1, 0, 5,
                        {"backgroundColor": WHITE, "verticalAlignment": "TOP", "wrapStrategy": "WRAP",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    R.append(merge(gid, 1, 1, 1, 4))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 13, True), "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(textFormat,verticalAlignment)"))
    R.append(set_borders(gid, 1, 1, 1, 4, bottom=border("SOLID_THICK", RED)))
    R.append(merge(gid, 2, 2, 1, 4))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False), "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(textFormat,verticalAlignment)"))
    # ① OTE表（達成率｜支給率｜評価点｜備考＝B:E）
    R += banner(gid, 4, 1, 4)
    R.append(repeat_fmt(gid, 5, 5, 1, 4, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                          "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    R.append(repeat_fmt(gid, OTE_R0, OTE_END, 1, 1, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    R.append(repeat_fmt(gid, OTE_R0, OTE_END, 2, 3, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 10, True)},
                        "userEnteredFormat(horizontalAlignment,textFormat)"))
    R.append(repeat_fmt(gid, OTE_R0, OTE_END, 4, 4, {"horizontalAlignment": "LEFT", "textFormat": tf(TEXT_GREY, 9, False)},
                        "userEnteredFormat(horizontalAlignment,textFormat)"))
    R.append(repeat_fmt(gid, ote_done, ote_done, 1, 4, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 10, True)},
                        "userEnteredFormat(backgroundColor,textFormat)"))
    R.append(box(gid, 5, OTE_END, 1, 4))
    # ② 目標ごとの基準（B目標項目｜C:E定義）
    R += banner(gid, GOAL_BAN, 1, 4)
    R.append(merge(gid, GOAL_HDR, GOAL_HDR, 2, 4))   # ヘッダ右はC:E結合
    R.append(repeat_fmt(gid, GOAL_HDR, GOAL_HDR, 1, 4, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                                        "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(gid, GOAL_HDR, GOAL_HDR, 1, 1, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    for r in range(GOAL_R0, last + 1):
        R.append(merge(gid, r, r, 2, 4))   # 定義は C:E 結合（広め）
        R.append(repeat_fmt(gid, r, r, 1, 1, {"textFormat": tf(TEXT_DARK, 10, True), "verticalAlignment": "TOP"},
                            "userEnteredFormat(textFormat,verticalAlignment)"))
        R.append(repeat_fmt(gid, r, r, 2, 4, {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"},
                            "userEnteredFormat(wrapStrategy,verticalAlignment)"))
    R.append(box(gid, GOAL_HDR, last, 1, 4))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    auto = [{"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "ROWS",
                                                     "startIndex": GOAL_R0 - 1, "endIndex": last}}}]
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": auto}).execute()
    print("  評価基準: done")


def build_guide(svc, SS, gid):
    rows = [
        ["点数定義ガイド｜目標管理シート（雛形）2026年度"],
        ["100点＝目標達成（基準）。定量は超過で100点超（総合点も100超）。定性・バリューは達成＝100が上限。"],
        [],
        ["■ 採点の基本"],
        ["・", "100点＝目標達成（基準ライン）。100%超は加点、未達は100点未満。"],
        ["・", "定量は採点方式を選択。『比率』＝実績÷目標×100（連続・150%超も青天井）。"],
        ["・", "『段階』＝OTE公式 支給率テーブル準拠（達成率→評価点）。90%→70・95%→80・99%→95・100%→100・125%→130・150%→150、150%超は青天井。全11段は『評価基準』タブ。"],
        ["・", "定量の各ブロックはOTE代表点（150/125/100/90/70%）ごとに「しきい値＝目標×割合（金額）」を自動表示。"],
        ["・", f"定性・バリュー＝{qual_scale_text()}を自己・上長で選択。"],
        ["・", "空欄＝未評価。1つでも未入力なら小計・総合点も「未評価」と表示。"],
        [],
        ["■ 計算の流れ"],
        ["①", "各項目：売上＝実績から自動／その他＝選んだランクから点数を自動算出"],
        ["②", "定量 評価点＝定量内の目標ごとウェイト×各点（カテゴリ内で合計100%に正規化）"],
        ["③", "定性・バリューも同様に、カテゴリ内のウェイト×各点で評価点を算出"],
        ["④", "総合点＝定量×60%＋定性×20%＋バリュー×20%（カテゴリ間の配点・合計100%）"],
        [],
        ["■ 入力をラクにする工夫"],
        ["・", "売上は「月次振り返り」タブに毎月入れるだけ。上期/下期/通期の実績は自動集計。"],
        ["・", "定量③・定性・バリューは期末にランクを選ぶ。空欄は未評価のまま。"],
        ["・", "通期は上半期・下半期から自動集計。上書きしたい項目だけ入力。"],
        ["・", "黄色いセル（目標値・ウェイト・実績・自己/上長入力・採点方式）が入力欄。"],
    ]
    write_values(svc, SS, [("点数定義ガイド!B1", rows)])
    R = [grid_off(gid), unmerge(gid, 1, 40, 0, 11)]
    for c, w in {0: 28, 1: 60, 2: 720}.items():
        R.append(col_width(gid, c, w))
    R.append(repeat_fmt(gid, 1, 24, 0, 4,
                        {"backgroundColor": WHITE, "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    R.append(merge(gid, 1, 1, 1, 2))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 13, True)}, "userEnteredFormat.textFormat"))
    R.append(set_borders(gid, 1, 1, 1, 2, bottom=border("SOLID_THICK", RED)))
    R.append(merge(gid, 2, 2, 1, 2))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    for i, row in enumerate(rows, 1):
        if row and isinstance(row[0], str) and row[0].startswith("■"):
            R.append(merge(gid, i, i, 1, 2))
            R.append(repeat_fmt(gid, i, i, 1, 2, {"backgroundColor": RED_TINT, "textFormat": tf(RED, 10.0 if False else 11, True)},
                                "userEnteredFormat(backgroundColor,textFormat)"))
        elif len(row) == 2:
            R.append(repeat_fmt(gid, i, i, 1, 1, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 10, True)},
                                "userEnteredFormat(horizontalAlignment,textFormat)"))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    print("  点数定義ガイド: done")


def build_hrbrain(svc, SS, gid, quant):
    # 経営層が読む想定。各目標セル＝項目／SMART／──区切り線／【評価基準】(期別の段階定義)。
    sn = "HRbrain貼付用"
    HD = ["目標", "ウェイト", "アクションプラン"]
    rule = "─" * 28   # セル内の区切り線（目標本文と評価基準を視覚的に分ける）

    def gref(er, with_w=True, quant5=False, sales=False):
        # 「目標」＝ 項目／SMART／──/【評価基準】(R列サマリ＝対象期間の段階定義)。清書はHRbrain側、計算は本シート。
        p = "$C$3"
        c = f'INDIRECT("\'"&{p}&"\'!C{er}")'
        d = f'INDIRECT("\'"&{p}&"\'!D{er}")'
        if quant5 and sales:
            # 定量(売上)：各レベルの具体金額＝目標値(F)×達成率。対象期間に応じ自動表示。
            tgt = f'INDIRECT("\'"&{p}&"\'!F{er}")'
            if QUANT_LINEAR:   # リニア＝評価点＝達成率%（金額も達成率と同じ割合）
                lv = [("100点", 1.00, "100%"), ("90点", 0.90, "90%"), ("80点", 0.80, "80%"),
                      ("70点", 0.70, "70%"), ("60点", 0.60, "60%")]
                note = '"※評価点＝達成率%（70%→70点）。100%超も達成率分だけ加点（上限なし）。"'
            else:              # OTE支給率テーブル
                lv = [("100点", 1.00, "100%"), ("90点", 0.97, "97%"), ("80点", 0.95, "95%"),
                      ("70点", 0.90, "90%"), ("60点", 0.85, "85%")]
                note = '"※100%超は加点・85%未満は段階減点（本シートのOTEで自動算出）"'
            body = '&CHAR(10)&'.join(
                f'"{pt}：¥"&TEXT({tgt}*{ratio},"#,##0")&"（{pct}）"' for pt, ratio, pct in lv)
            gdef = f'IF(NOT(ISNUMBER({tgt})),"目標金額を入力してください",{body}&CHAR(10)&{note})'
        elif quant5:
            # 定量(件数metric)：金額が無いので達成率の代表点で表示。
            if QUANT_LINEAR:   # リニア＝評価点＝達成率%
                lines = ["100点：100%達成", "90点：90%達成", "80点：80%達成",
                         "70点：70%達成", "60点：60%達成",
                         "※評価点＝達成率%（70%→70点）。100%超も達成率分だけ加点（上限なし・本シートで自動算出）。"]
            else:              # OTE支給率テーブル
                lines = ["100点：目標100%達成", "90点：達成率97〜98%", "80点：達成率95〜96%",
                         "70点：達成率90〜94%", "60点：達成率85〜89%",
                         "※実際の点数は達成率に応じ本シートのOTEで自動算出（100%超の加点・中間値・85%未満の減点を含む）"]
            gdef = "&CHAR(10)&".join(f'"{ln}"' for ln in lines)
        else:
            gdef = f'INDIRECT("\'"&{p}&"\'!R{er}")'
        g = (f'=IF({c}="","",'
             f'{c}&CHAR(10)&{d}&CHAR(10)&"{rule}"&CHAR(10)&"【評価基準】"&CHAR(10)&{gdef})')
        w = f'=IFERROR(INDIRECT("\'"&{p}&"\'!{LW}{er}")*100,"")' if with_w else ""   # ウェイト=J列
        a = f'=INDIRECT("\'"&{p}&"\'!E{er}")'
        return [g, w, a]

    q_rows, l_rows, v_rows = Q_BLOCKS, QL_BLOCKS, V_BLOCKS
    HB_NOTE = 4
    HB_Q_BAN, HB_Q_HDR, HB_Q0 = 5, 6, 7
    HB_L_BAN = HB_Q0 + SLOTS + 1
    HB_L_HDR, HB_L0 = HB_L_BAN + 1, HB_L_BAN + 2
    HB_V_BAN = HB_L0 + SLOTS + 1
    HB_V_HDR, HB_V0 = HB_V_BAN + 1, HB_V_BAN + 2
    HB_END = HB_V0 + SLOTS

    if QUANT_LINEAR:
        quant_note = "定量＝評価点＝達成率%（70%→70点・100%→100点・超過で100点超／上限なし）"
    elif QUAL_LEVELS == 5:
        quant_note = "定量＝100〜60点表記（達成率→本シートのOTEで自動算出・100%超は加点）"
    else:
        quant_note = "定量＝達成率に応じてOTE支給率で加点（100%超も評価）"
    vals = [
        (f"{sn}!B1", [["HRbrain貼付用｜目標設定（HRbrainの「目標設定」画面へコピー）"]]),
        (f"{sn}!B2", [["下の各セルをHRbrainの「目標設定」画面へ貼り付けます。内容は［対象期間］で選んだタブ（通期／上半期／下半期）から自動で表示されます。"]]),
        (f"{sn}!B3", [["対象期間 →", "通期"]]),
        (f"{sn}!B{HB_NOTE}", [[f"評価の考え方：100点＝達成が基準。{quant_note}。定性・バリュー＝{qual_scale_text()}。"]]),
        (f"{sn}!B{HB_Q_BAN}", [["■ 定量目標　［配点60%］"]]),
        (f"{sn}!B{HB_Q_HDR}", [HD]),
        (f"{sn}!B{HB_L_BAN}", [["■ 定性目標　［配点20%］"]]),
        (f"{sn}!B{HB_L_HDR}", [HD]),
        (f"{sn}!B{HB_V_BAN}", [["■ バリュー　［配点20%］"]]),
        (f"{sn}!B{HB_V_HDR}", [HD]),
    ]
    for k, er in enumerate(q_rows):
        # 5段階版＝定量も5段階表記。売上(sales)は各レベルの¥金額、件数(metric)は達成率で表示。
        vals.append((f"{sn}!B{HB_Q0 + k}", [gref(er, quant5=(QUAL_LEVELS == 5),
                                                 sales=(quant[k]["kind"] == "sales"))]))
    for k, er in enumerate(l_rows):
        vals.append((f"{sn}!B{HB_L0 + k}", [gref(er)]))
    for k, er in enumerate(v_rows):
        vals.append((f"{sn}!B{HB_V0 + k}", [gref(er, with_w=False)]))
    write_values(svc, SS, vals)

    R = [grid_off(gid), unmerge(gid, 1, HB_END + 2, 0, 11)]
    for c, w in {0: 28, 1: 470, 2: 78, 3: 470}.items():
        R.append(col_width(gid, c, w))
    R.append(repeat_fmt(gid, 1, HB_END + 1, 0, 4,
                        {"backgroundColor": WHITE, "verticalAlignment": "TOP", "wrapStrategy": "WRAP",
                         "horizontalAlignment": "LEFT",   # 旧書式の中央寄せ残骸を一掃（行で不揃いを防ぐ）
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,horizontalAlignment,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    # タイトル（赤太下線）
    R.append(merge(gid, 1, 1, 1, 3))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 13, True), "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(textFormat,verticalAlignment)"))
    R.append(set_borders(gid, 1, 1, 1, 3, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(gid, 1, 34))
    # サブタイトル（使い方・必要な説明）
    R.append(merge(gid, 2, 2, 1, 3))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False), "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(textFormat,verticalAlignment)"))
    # 対象期間セレクタ
    R.append(repeat_fmt(gid, 3, 3, 1, 1, {"textFormat": tf(TEXT_DARK, 10, True), "horizontalAlignment": "RIGHT",
                                          "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"))
    R.append(repeat_fmt(gid, 3, 3, 2, 2, {"backgroundColor": YELLOW, "textFormat": tf(RED, 11, True),
                                          "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    R.append(box(gid, 3, 3, 2, 2, inner=False))
    R.append(row_height(gid, 3, 28))
    # 評価の考え方（必要な説明を1回だけ・線で囲った淡いコールアウト）
    R.append(merge(gid, HB_NOTE, HB_NOTE, 1, 3))
    R.append(repeat_fmt(gid, HB_NOTE, HB_NOTE, 1, 1, {"backgroundColor": {"red": 0.972, "green": 0.972, "blue": 0.972},
                                                      "textFormat": tf(TEXT_GREY, 9, False), "wrapStrategy": "WRAP",
                                                      "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,wrapStrategy,verticalAlignment)"))
    R.append(box(gid, HB_NOTE, HB_NOTE, 1, 3, inner=False))
    R.append(row_height(gid, HB_NOTE, 36))
    # セクション（定量／定性／バリュー）
    for (br, hr, r0) in [(HB_Q_BAN, HB_Q_HDR, HB_Q0), (HB_L_BAN, HB_L_HDR, HB_L0), (HB_V_BAN, HB_V_HDR, HB_V0)]:
        R += banner(gid, br, 1, 3)
        R.append(repeat_fmt(gid, hr, hr, 1, 3, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                                                "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
        R.append(repeat_fmt(gid, hr, hr, 1, 1, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
        for r in range(r0, r0 + SLOTS):
            R.append(repeat_fmt(gid, r, r, 1, 3, {"wrapStrategy": "WRAP", "verticalAlignment": "TOP"},
                                "userEnteredFormat(wrapStrategy,verticalAlignment)"))
            R.append(repeat_fmt(gid, r, r, 2, 2, {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                                "userEnteredFormat(horizontalAlignment,verticalAlignment)"))
        R.append(box(gid, hr, r0 + SLOTS - 1, 1, 3))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": [{"setDataValidation": {
        "range": rng(gid, 3, 3, 2, 2), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": v} for v in ["通期", "上半期", "下半期"]]},
            "strict": True, "showCustomUi": True}}}]}).execute()
    auto = [{"autoResizeDimensions": {"dimensions": {"sheetId": gid, "dimension": "ROWS", "startIndex": a, "endIndex": b}}}
            for (a, b) in [(HB_Q0 - 1, HB_Q0 + SLOTS - 1), (HB_L0 - 1, HB_L0 + SLOTS - 1), (HB_V0 - 1, HB_V0 + SLOTS - 1)]]
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": auto}).execute()
    print("  HRbrain貼付用: done")


def _ensure_canonical_tabs(svc, SS):
    """タブ名が正準名(TABS)からドリフトしていたら位置基準で復元（手動リネーム耐性）。
    ※ビルドはタブ名で参照するため並び替えは無害。正準名のタブ（並び替えのみ）は改名しない＝
      ユーザーが90日プラン/月次振り返り等をドラッグで入替えても衝突しない（既存名への改名を回避）。"""
    meta = svc.spreadsheets().get(
        spreadsheetId=SS, fields="sheets(properties(sheetId,title,index))").execute()
    ordered = sorted(meta["sheets"], key=lambda s: s["properties"]["index"])
    present = {sh["properties"]["title"] for sh in ordered}
    canon = set(TABS)
    reqs = []
    for i, sh in enumerate(ordered[:len(TABS)]):
        title = sh["properties"]["title"]
        target = TABS[i]
        # ドリフト名（正準名でない）だけ位置基準で復元。target既存なら衝突回避でスキップ。
        if title != target and title not in canon and target not in present:
            print(f"  タブ名復元: '{title}' → '{target}'")
            reqs.append({"updateSheetProperties": {
                "properties": {"sheetId": sh["properties"]["sheetId"], "title": target}, "fields": "title"}})
            present.discard(title)
            present.add(target)
    if reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": reqs}).execute()


def _rename_legacy_tabs(svc, SS):
    """旧名タブ(LEGACY_RENAME)を新名へリネーム（_ensure_tabs_existが新名を重複追加する前に通す）。"""
    meta = svc.spreadsheets().get(spreadsheetId=SS, fields="sheets(properties(sheetId,title))").execute()
    titles = {sh["properties"]["title"] for sh in meta["sheets"]}
    reqs = []
    for sh in meta["sheets"]:
        old = sh["properties"]["title"]
        new = LEGACY_RENAME.get(old)
        if new and new not in titles:   # 新名がまだ無ければリネーム（重複回避）
            print(f"  タブ名移行: '{old}' → '{new}'")
            reqs.append({"updateSheetProperties": {
                "properties": {"sheetId": sh["properties"]["sheetId"], "title": new}, "fields": "title"}})
    if reqs:
        svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": reqs}).execute()


def _ensure_tabs_exist(svc, SS):
    """TABSに無いタブを末尾に追加（既存SSへの90日プラン等の追加用）。"""
    have = set(sheet_ids(svc, SS).keys())
    add = [{"addSheet": {"properties": {"title": t, "index": i}}}
           for i, t in enumerate(TABS) if t not in have]
    if add:
        svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": add}).execute()


def build_plan90(svc, SS, gid, member, quant, qual, value):
    # 90日プラン×4（=360日／52週WBS）。年間目標＋四半期ごとに「ガント型1表」
    #   行＝マイルストーン × 列＝W1〜W13（横）。各行に開始日/終了日を入れると、期間が重なる週に
    #   CFカスタム式でバーが自動で引かれる（週ヘッダ＝クオーター開始日から自動算出の日付・編集可）。
    sn = "90日プラン"
    cl = lambda i: chr(65 + i)        # 0基点の列インデックス→列文字（B=1,C=2,…）
    WK = PLAN_WEEKS                   # 13週（横方向の列）
    MS = PLAN_ACTIONS                 # マイルストーン行（縦）＝10
    cMS, cST0, cEN = 1, 2, 3          # B=名前 / C=開始 / D=終了
    cW0 = 4                           # E=W1
    cWE = cW0 + WK - 1                # Q=W13（=16）
    cSTA, cPR, cMM = cWE + 1, cWE + 2, cWE + 3   # R状態(17)/S進捗(18)/Tメモ(19)
    LAST = cMM                        # T列
    GHDR = ["マイルストーン（達成までの打ち手）", "開始", "終了"] + [f"W{i+1}" for i in range(WK)] + ["ステータス", "進捗", "メモ"]
    BAR = {"red": 0.80, "green": 0.33, "blue": 0.29}   # ガントのバー色（期間が重なる週）

    # 年間目標（通期参照＝達成の起点）
    GOALS = []
    for i, g in enumerate(quant):
        if g["item"]:
            GOALS.append((g["ku"], Q_BLOCKS[i], "OTE支給率", "yen" if g["kind"] == "sales" else "num"))
    for i, g in enumerate(qual):
        if g["item"]:
            GOALS.append((g["ku"], QL_BLOCKS[i], qual_score_label(), "txt"))
    for i, g in enumerate(value):
        if g["item"]:
            GOALS.append((g["ku"], V_BLOCKS[i], qual_score_label(), "txt"))
    NG = len(GOALS)
    # 参照表(年間目標)はセル結合で可読幅にする（0基点・包含）：項目C:I / 値J:N / 採点O:T
    GM = [(2, 8), (9, 13), (14, LAST)]

    TGB, TGH, TG0 = 4, 5, 6
    TGEND = TG0 + NG - 1
    QSTART = TGEND + 2
    BLK = 6 + MS                      # banner+theme+ヘッダ+日付行+MS+振り返り+余白 ＝ 6+MS（=16）
    END = QSTART + 4 * BLK - 1         # Q4の余白行

    # ---- 値 ----
    vals = [
        (f"{sn}!B1", [[f"90日プラン｜{member}　2026年度（90日 × 4 ＝ 360日／52週WBS・ガント）"]]),
        (f"{sn}!B2", [["年間目標に向けて、各マイルストーンに開始日・終了日を入れると、期間が重なる週にバーが自動で引かれます。ステータス・進捗も更新して達成まで管理します。"]]),
        (f"{sn}!B{TGB}", [["■ 年間目標（このプランで達成を目指す｜通期と連動）"]]),
        (f"{sn}!B{TGH}", [["区分"]]), (f"{sn}!C{TGH}", [["目標項目"]]),
        (f"{sn}!J{TGH}", [["目標値"]]), (f"{sn}!O{TGH}", [["採点方式"]]),
    ]
    for i, (ku, row, score, _fmt) in enumerate(GOALS):
        r = TG0 + i
        vals.append((f"{sn}!B{r}", [[ku]]))
        vals.append((f"{sn}!C{r}", [[f"='通期'!C{row}"]]))
        vals.append((f"{sn}!J{r}", [[f"='通期'!F{row}"]]))
        vals.append((f"{sn}!O{r}", [[score]]))
    for qi, (q, period) in enumerate(PLAN_QUARTERS):
        qb = QSTART + qi * BLK
        theme, ghdr, gh2 = qb + 1, qb + 2, qb + 3
        g0 = qb + 4
        gend = g0 + MS - 1
        rev = gend + 1
        vals.append((f"{sn}!B{qb}", [[f"■ {q}　90日プラン（{period}）"]]))
        vals.append((f"{sn}!B{theme}", [["重点テーマ"]]))
        vals.append((f"{sn}!B{ghdr}", [GHDR]))
        # 日付サブヘッダ：B:D=ラベル / E=クオーター開始日(編集可) / F:Q=自動算出 / R:T=注記
        vals.append((f"{sn}!{cl(cMS)}{gh2}", [["週の開始日（W1）→"]]))
        vals.append((f"{sn}!{cl(cW0)}{gh2}", [[PLAN_QSTART_DATES[qi]]]))
        for n in range(2, WK + 1):
            vals.append((f"{sn}!{cl(cW0 + n - 1)}{gh2}", [[f"=${cl(cW0)}${gh2}+{7 * (n - 1)}"]]))
        vals.append((f"{sn}!{cl(cSTA)}{gh2}", [["← 各行に開始日・終了日を入れるとバーが自動で引かれます"]]))
        for i in range(MS):
            # 名前(B)/開始(C)/終了(D) ＋ 週×13(E:Q) ＋ 状態(R)/進捗(S)/メモ(T) ＝19セル
            vals.append((f"{sn}!B{g0+i}", [[""] * (cW0 - cMS) + [""] * WK + ["未着手", "", ""]]))
        vals.append((f"{sn}!B{rev}", [["クオーター振り返り"]]))
    write_values(svc, SS, vals)

    # ---- 書式 ----
    R = [grid_off(gid), unmerge(gid, 1, END + 1, 0, 25)]
    R.append(col_width(gid, 0, 28))
    R.append(col_width(gid, cMS, 200))
    R.append(col_width(gid, cST0, 60))
    R.append(col_width(gid, cEN, 60))
    for c in range(cW0, cWE + 1):
        R.append(col_width(gid, c, 33))
    R.append(col_width(gid, cSTA, 90))
    R.append(col_width(gid, cPR, 54))
    R.append(col_width(gid, cMM, 150))
    R.append(repeat_fmt(gid, 1, END, 0, LAST,
                        {"backgroundColor": WHITE, "verticalAlignment": "MIDDLE", "wrapStrategy": "OVERFLOW_CELL",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                         "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))
    R.append(merge(gid, 1, 1, 1, LAST))
    R.append(repeat_fmt(gid, 1, 1, 1, 1, {"textFormat": tf(RED, 14, True)}, "userEnteredFormat.textFormat"))
    R.append(set_borders(gid, 1, 1, 1, LAST, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(gid, 1, 38))
    R.append(merge(gid, 2, 2, 1, LAST))
    R.append(repeat_fmt(gid, 2, 2, 1, 1, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"))
    # 年間目標表（週列が狭いので結合で可読化）
    R += banner(gid, TGB, 1, LAST)
    R.append(repeat_fmt(gid, TGH, TGH, 1, LAST, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9, True),
                                                 "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
    for c1, c2 in GM:
        R.append(merge(gid, TGH, TGH, c1, c2))
    R.append(repeat_fmt(gid, TGH, TGH, 2, 2, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
    R.append(row_height(gid, TGH, 28))
    for i, (ku, row, score, fmt) in enumerate(GOALS):
        r = TG0 + i
        for c1, c2 in GM:
            R.append(merge(gid, r, r, c1, c2))
        R.append(repeat_fmt(gid, r, r, 1, 1, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_GREY, 9, True)},
                            "userEnteredFormat(horizontalAlignment,textFormat)"))
        R.append(repeat_fmt(gid, r, r, 2, 2, {"horizontalAlignment": "LEFT", "wrapStrategy": "WRAP",
                                              "textFormat": tf(TEXT_DARK, 10, False)},
                            "userEnteredFormat(horizontalAlignment,wrapStrategy,textFormat)"))
        R.append(repeat_fmt(gid, r, r, 9, 9, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 10, True)},
                            "userEnteredFormat(horizontalAlignment,textFormat)"))
        if fmt == "yen":
            R.append(repeat_fmt(gid, r, r, 9, 9, {"numberFormat": {"type": "CURRENCY", "pattern": "¥#,##0"}},
                                "userEnteredFormat.numberFormat"))
        elif fmt == "num":
            R.append(repeat_fmt(gid, r, r, 9, 9, {"numberFormat": {"type": "NUMBER"}}, "userEnteredFormat.numberFormat"))
        R.append(repeat_fmt(gid, r, r, 14, 14, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_GREY, 9, False)},
                            "userEnteredFormat(horizontalAlignment,textFormat)"))
        R.append(row_height(gid, r, 26))
    R.append(box(gid, TGH, TGEND, 1, LAST))

    DATEFMT = {"type": "DATE", "pattern": "m/d"}
    bar_rules = []
    for qi in range(4):
        qb = QSTART + qi * BLK
        theme, ghdr, gh2 = qb + 1, qb + 2, qb + 3
        g0 = qb + 4
        gend = g0 + MS - 1
        rev = gend + 1
        R += banner(gid, qb, 1, LAST)
        # 重点テーマ（B=ラベル / C:T=入力）
        R.append(repeat_fmt(gid, theme, theme, 1, 1, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT",
                                                      "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"))
        R.append(merge(gid, theme, theme, 2, LAST))
        R.append(repeat_fmt(gid, theme, theme, 2, LAST, {"backgroundColor": YELLOW, "horizontalAlignment": "LEFT",
                                                         "wrapStrategy": "WRAP"},
                            "userEnteredFormat(backgroundColor,horizontalAlignment,wrapStrategy)"))
        R.append(row_height(gid, theme, 26))
        # ガント・ヘッダ（B=名前左 / C,D=開始終了 / E:Q=週 / R:T=右側）
        R.append(repeat_fmt(gid, ghdr, ghdr, 1, LAST, {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 9, True),
                                                       "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"))
        R.append(repeat_fmt(gid, ghdr, ghdr, cMS, cMS, {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment"))
        R.append(repeat_fmt(gid, ghdr, ghdr, cW0, cWE, {"textFormat": tf(TEXT_GREY, 8, True)}, "userEnteredFormat.textFormat"))
        R.append(row_height(gid, ghdr, 22))
        # 日付サブヘッダ（gh2）：B:D ラベル / E 開始日入力 / F:Q 自動日付 / R:T 注記
        R.append(merge(gid, gh2, gh2, cMS, cEN))
        R.append(repeat_fmt(gid, gh2, gh2, cMS, cEN, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT",
                                                      "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"))
        R.append(repeat_fmt(gid, gh2, gh2, cW0, cW0, {"backgroundColor": YELLOW, "horizontalAlignment": "CENTER",
                                                      "textFormat": tf(TEXT_DARK, 9, True), "numberFormat": DATEFMT},
                            "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat,numberFormat)"))
        R.append(repeat_fmt(gid, gh2, gh2, cW0 + 1, cWE, {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_GREY, 8, False),
                                                          "numberFormat": DATEFMT},
                            "userEnteredFormat(horizontalAlignment,textFormat,numberFormat)"))
        R.append(merge(gid, gh2, gh2, cSTA, cMM))
        R.append(repeat_fmt(gid, gh2, gh2, cSTA, cSTA, {"textFormat": tf(TEXT_GREY, 8, False), "horizontalAlignment": "LEFT",
                                                        "wrapStrategy": "WRAP"},
                            "userEnteredFormat(textFormat,horizontalAlignment,wrapStrategy)"))
        R.append(row_height(gid, gh2, 22))
        # マイルストーン行
        R.append(repeat_fmt(gid, g0, gend, 1, LAST, {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE",
                                                     "textFormat": tf(TEXT_DARK, 10, False)},
                            "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)"))
        R.append(repeat_fmt(gid, g0, gend, cMS, cMS, {"backgroundColor": YELLOW, "horizontalAlignment": "LEFT"},
                            "userEnteredFormat(backgroundColor,horizontalAlignment)"))
        # 開始/終了（入力黄・日付 m/d・中央）
        R.append(repeat_fmt(gid, g0, gend, cST0, cEN, {"backgroundColor": YELLOW, "horizontalAlignment": "CENTER",
                                                       "numberFormat": DATEFMT},
                            "userEnteredFormat(backgroundColor,horizontalAlignment,numberFormat)"))
        # 週セル（白・CFカスタム式でバー自動描画＝入力不要）
        R.append(repeat_fmt(gid, g0, gend, cW0, cWE, {"backgroundColor": WHITE}, "userEnteredFormat.backgroundColor"))
        # ステータス（入力黄・中央・ドロップダウン）
        R.append(repeat_fmt(gid, g0, gend, cSTA, cSTA, {"backgroundColor": YELLOW, "horizontalAlignment": "CENTER"},
                            "userEnteredFormat(backgroundColor,horizontalAlignment)"))
        # 進捗（入力黄・中央・%）
        R.append(repeat_fmt(gid, g0, gend, cPR, cPR, {"backgroundColor": YELLOW, "horizontalAlignment": "CENTER",
                                                      "numberFormat": {"type": "PERCENT", "pattern": "0%"}},
                            "userEnteredFormat(backgroundColor,horizontalAlignment,numberFormat)"))
        # メモ（入力黄・左）
        R.append(repeat_fmt(gid, g0, gend, cMM, cMM, {"backgroundColor": YELLOW, "horizontalAlignment": "LEFT"},
                            "userEnteredFormat(backgroundColor,horizontalAlignment)"))
        for r in range(g0, gend + 1):
            R.append(row_height(gid, r, 28))
        R.append(box(gid, ghdr, gend, 1, LAST))
        R.append(set_borders(gid, ghdr, gend, cST0, cST0, left=border("SOLID_MEDIUM", BORDER_STRONG)))   # 名前|開始
        R.append(set_borders(gid, ghdr, gend, cW0, cW0, left=border("SOLID_MEDIUM", BORDER_STRONG)))     # 終了|週
        R.append(set_borders(gid, ghdr, gend, cSTA, cSTA, left=border("SOLID_MEDIUM", BORDER_STRONG)))   # 週|状態
        # 振り返り（B=ラベル / C:T=入力）
        R.append(repeat_fmt(gid, rev, rev, 1, 1, {"textFormat": tf(TEXT_GREY, 9, True), "horizontalAlignment": "RIGHT",
                                                  "verticalAlignment": "MIDDLE"},
                            "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment)"))
        R.append(merge(gid, rev, rev, 2, LAST))
        R.append(repeat_fmt(gid, rev, rev, 2, LAST, {"backgroundColor": YELLOW, "horizontalAlignment": "LEFT",
                                                     "wrapStrategy": "WRAP", "verticalAlignment": "TOP"},
                            "userEnteredFormat(backgroundColor,horizontalAlignment,wrapStrategy,verticalAlignment)"))
        R.append(row_height(gid, rev, 32))
        # 期間→バーのCFカスタム式（開始/終了が週[E$gh2 .. +6]と重なる週を塗る）
        bar_formula = (f'=AND(${cl(cST0)}{g0}<>"",${cl(cEN)}{g0}<>"",'
                       f'${cl(cST0)}{g0}<={cl(cW0)}${gh2}+6,${cl(cEN)}{g0}>={cl(cW0)}${gh2})')
        bar_rules.append((rng(gid, g0, gend, cW0, cWE), bar_formula))
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": R}).execute()

    # ステータスのドロップダウン（各クオーターのR列マイルストーン域）
    dv = []
    for qi in range(4):
        g0 = QSTART + qi * BLK + 4
        gend = g0 + MS - 1
        dv.append({"setDataValidation": {"range": rng(gid, g0, gend, cSTA, cSTA), "rule": {
            "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": s} for s in PLAN_STATUS]},
            "strict": False, "showCustomUi": True}}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": dv}).execute()

    # CF（既存削除→①期間バー=カスタム式 ②ステータス色）
    meta = svc.spreadsheets().get(spreadsheetId=SS, fields="sheets(properties(sheetId),conditionalFormats)").execute()
    ncf = 0
    for sh in meta["sheets"]:
        if sh["properties"]["sheetId"] == gid:
            ncf = len(sh.get("conditionalFormats", []))
    cf = [{"deleteConditionalFormatRule": {"sheetId": gid, "index": 0}} for _ in range(ncf)]
    for rg, formula in bar_rules:   # ① 期間が重なる週にバー（自動）
        cf.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [rg],
            "booleanRule": {"condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]},
                            "format": {"backgroundColor": BAR}}}}})
    srange = rng(gid, QSTART, END, cSTA, cSTA)   # ② ステータス色（R列クオーター域）
    for st, col in [("完了", {"red": 0.84, "green": 0.93, "blue": 0.84}),
                    ("進行中", {"red": 0.86, "green": 0.92, "blue": 0.99}),
                    ("保留", {"red": 0.93, "green": 0.93, "blue": 0.93})]:
        cf.append({"addConditionalFormatRule": {"index": 0, "rule": {
            "ranges": [srange],
            "booleanRule": {"condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": st}]},
                            "format": {"backgroundColor": col}}}}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": cf}).execute()
    print("  90日プラン: done")


def build_member(svc, member, id_file, title, quant, qual, value, qual_levels=3, seed_qual=False,
                 quant_linear=False):
    global QUANT_LINEAR
    QUANT_LINEAR = quant_linear       # 定量の参照表示（True=リニア / False=OTE）。ビルドは逐次なのでglobalで安全
    _set_qual_levels(qual_levels)     # 定性・バリューの段階数(3=◎◯△ / 5=100/90/80/70/60)を先に確定
    SS = get_or_create_ss(svc, id_file, title)
    print(f"[{member}] URL: https://docs.google.com/spreadsheets/d/{SS}/edit（定性{qual_levels}段階）")
    _rename_legacy_tabs(svc, SS)      # 旧名タブ（HRブレイン貼付用→HRbrain貼付用）を先に移行
    _ensure_tabs_exist(svc, SS)       # 不足タブ（90日プラン等）を追加
    _ensure_canonical_tabs(svc, SS)   # 手動リネームを正準名に戻してから参照
    gids = sheet_ids(svc, SS)
    # 再構築前に全タブの値をクリア（旧レイアウト残骸の防止）
    # 90日プランが最も縦長（年間目標＋4Q×週次13週WBS）なので余裕をもって130行までクリア。
    svc.spreadsheets().values().batchClear(
        spreadsheetId=SS, body={"ranges": [f"{t}!A1:Z130" for t in TABS]}).execute()
    # 旧レイアウトを「綺麗に削除」してから再構築（値クリアだけでは書式が残るため）：
    #   全タブで 結合解除＋背景を白＋罫線を全消去＋数値書式をGeneral へリセット。
    #   これをしないと旧レイアウトの赤ティント・罫線が新レイアウトの非対象セルに残る（残骸バグ）。
    wipe = []
    for t in TABS:
        g = gids[t]
        wipe.append(unmerge(g, 1, 130, 0, 25))
        wipe.append(repeat_fmt(g, 1, 130, 0, 25, {"backgroundColor": WHITE}, "userEnteredFormat.backgroundColor"))
        wipe.append({"updateBorders": {"range": rng(g, 1, 130, 0, 25),
                                       "top": {"style": "NONE"}, "bottom": {"style": "NONE"},
                                       "left": {"style": "NONE"}, "right": {"style": "NONE"},
                                       "innerHorizontal": {"style": "NONE"}, "innerVertical": {"style": "NONE"}}})
        # 旧レイアウトのドロップダウン（入力規則）も消す（再構築で正しい位置に貼り直す）
        wipe.append({"setDataValidation": {"range": rng(g, 1, 130, 0, 25)}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SS, body={"requests": wipe}).execute()
    build_monthly(svc, SS, gids["月次振り返り"], member)
    for p in ["上半期", "下半期", "通期"]:
        build_eval(svc, SS, gids[p], p, member, quant, qual, value)
    build_dashboard(svc, SS, gids["ダッシュボード"], member)
    build_kijun(svc, SS, gids["評価基準"], quant, qual, value)
    build_guide(svc, SS, gids["点数定義ガイド"])
    build_hrbrain(svc, SS, gids["HRbrain貼付用"], quant)
    build_plan90(svc, SS, gids["90日プラン"], member, quant, qual, value)
    if seed_qual:                     # 佐藤：定性・バリューの評価基準（5段階）を期別にI列へ記載
        _seed_qual_criteria(svc, SS)
    return SS


if __name__ == "__main__":
    import sys
    svc = svc_get()
    import time
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    tasks = []   # (member, id_file, title, quant, qual, value, qual_levels, seed_qual, quant_linear)
    if target in ("template", "both", "all"):
        tasks.append(("（メンバー名）", ID_FILE, TITLE, TPL_QUANT, TPL_QUAL, TPL_VALUE, 3, False, False))
    if target in ("template2", "all"):   # 雛形B＝5段階版（定性・バリュー100〜60点／定量もHRブレイン5段階表記）。基準は空(各自記入)
        tasks.append(("（メンバー名）", os.path.join(_BASE, ".template2_ss_id.txt"),
                      "目標管理シート_雛形（5段階版）_2026年度", TPL_QUANT, TPL_QUAL, TPL_VALUE, 5, False, False))
    if target in ("sato", "both", "all"):
        sq, sl, sv = load_sato()
        # 佐藤＝定性5段階＋基準記載＋定量リニア表示（達成率＝評価点。70%→70点）
        tasks.append(("佐藤篤也", os.path.join(_BASE, ".sato_ss_id.txt"),
                      "目標管理シート_佐藤篤也_2026年度", sq, sl, sv, 5, True, True))
    for i, (m, idf, ti, q, l, v, ql, sq_, qlin) in enumerate(tasks):
        if i > 0:
            print(f"  …クォータ回避のため {50}s 待機…")
            time.sleep(50)   # 書込60/分/ユーザー制限の回避（シート間スペース）
        build_member(svc, m, idf, ti, q, l, v, qual_levels=ql, seed_qual=sq_, quant_linear=qlin)
    print("DONE")
