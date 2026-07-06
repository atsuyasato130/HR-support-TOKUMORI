"""
人事評価シート（CA 2026 / SmartHR型）リデザイン 正本スクリプト。

対象 SS=1EDXGStE2Jt-ScuMMc_GwQNFCInNKpj27IYCSlBru09c
  A. 総合点カードをハイブリッド型へ再配置 + 入力エリア全面ブラッシュアップ（書式）
  B. ダッシュボードの上長評価参照を新セル(D列)へ追従修正
  C. ランク体系刷新（SmartHR準拠）:
       定量③         S/A/B/C/D → 5/4/3/2/1   （100/90/80/70/60）
       定性①②・バリュー S/B/D     → ◎/○/△       （100/80/60）
     ※点数体系・重み・集計ロジックは不変。既存入力値は等価移行してスコアを保つ。
  D. 評価基準タブ・点数定義ガイドの表記を新ランクへ刷新

冪等: 再実行可。クリーンアップ先行（unmerge→border NONE→bg白）。
認証: tokumori/agents/hr_support/config/token_sheets.json
"""
import re

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SS = "1EDXGStE2Jt-ScuMMc_GwQNFCInNKpj27IYCSlBru09c"
TOKEN = "/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"

EVAL_TABS = {"上半期": 930996632, "下半期": 444414577, "通期": 1350552926}
DASH = "ダッシュボード"
KIJUN = "評価基準"
KIJUN_SID = 780444699
GUIDE = "点数定義ガイド"
GUIDE_SID = 872118080

# ---- カラーパレット ----
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


def dv_list(sid, r1, r2, c1, c2, values):
    return {"setDataValidation": {"range": rng(sid, r1, r2, c1, c2), "rule": {
        "condition": {"type": "ONE_OF_LIST",
                      "values": [{"userEnteredValue": str(v)} for v in values]},
        "strict": True, "showCustomUi": True}}}


# ============================================================
#  ランク刷新 ロジック
# ============================================================
MAP5 = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}        # 定量③ 移行
MAP3 = {"S": "◎", "A": "◎", "B": "○", "C": "△", "D": "△"}  # 定性/バリュー 移行
NEW5 = {5, 4, 3, 2, 1}
NEW3 = {"◎", "○", "△"}


def old_ladder(ref):
    return (f'IF({ref}="S",100,IF({ref}="A",90,IF({ref}="B",80,'
            f'IF({ref}="C",70,IF({ref}="D",60,0)))))')


def new_ladder5(ref):
    return (f'IF({ref}=5,100,IF({ref}=4,90,IF({ref}=3,80,'
            f'IF({ref}=2,70,IF({ref}=1,60,0)))))')


def new_ladder3(ref):
    return f'IF({ref}="◎",100,IF({ref}="○",80,IF({ref}="△",60,0)))'


# (算出セル, 入力参照, 段階) ：定量③=5段階 / 定性①②・バリュー=3段階
RANK_CELLS = [
    ("I8", "H8", 5), ("K8", "J8", 5),
    ("I13", "H13", 3), ("K13", "J13", 3),
    ("I14", "H14", 3), ("K14", "J14", 3),
    ("I19", "H19", 3), ("K19", "J19", 3),
]
INPUT_CELLS = [("H8", 5), ("J8", 5),
               ("H13", 3), ("J13", 3), ("H14", 3), ("J14", 3),
               ("H19", 3), ("J19", 3)]
CRIT_QUANT = ["D6", "D7", "D8"]   # 5段階表記へ
CRIT_QUAL = ["D13", "D14", "D19"]  # ◎○△ 3行へ集約

# インライン評価基準（D列）の明確化版。各タブ共通（売上は¥を入れず汎用）。点数明記・目標ライン明示・略語展開。
CRIT_TEXT = {
    "D6": ("売上は［実績額 ÷ 目標額 × 100］で点数を自動計算（100%超もそのまま加点）\n"
           "　達成率120% → 120点 ／ 110% → 110点 ／ 100%（＝目標達成）→ 100点 ／ 90% → 90点 ／ 80% → 80点\n"
           "　※基準ライン＝達成率100%（目標達成）"),
    "D7": ("売上は［実績額 ÷ 目標額 × 100］で点数を自動計算（100%超もそのまま加点）\n"
           "　達成率120% → 120点 ／ 110% → 110点 ／ 100%（＝目標達成）→ 100点 ／ 90% → 90点 ／ 80% → 80点\n"
           "　※基準ライン＝達成率100%（目標達成）"),
    "D8": ("5（100点）：新規2名以上をアサインし、うち2名を自らリクルーティングして採用\n"
           "4（ 90点）：新規2名のアサインを完了（受け入れ準備も整っている）\n"
           "3（ 80点・目標）：新規1名をアサインし、受け入れ準備まで完了\n"
           "2（ 70点）：新規1名のみアサイン（立ち上げに遅延あり）\n"
           "1（ 60点）：未アサイン、または着手のみ"),
    "D13": ("◎（100点）：研修プログラム完成＋オンボーディング実行＋月商400万円を出せるメンバーを複数輩出（自走状態）\n"
            "○（ 80点・目標）：研修完成・オンボーディング実行・月商400万円を出せる1名のめどが立っている\n"
            "△（ 60点）：研修着手のみ／オンボーディング未実行"),
    "D14": ("◎（100点）：メディアを公開し、安定した母集団流入＋人材紹介・イベントへの送客が回っている\n"
            "○（ 80点・目標）：メディアを立ち上げて公開し、初期流入を確認できている\n"
            "△（ 60点）：企画・設計のみで未公開"),
    "D19": ("◎（100点）：複数部署でAI活用の業務改善を運用＋工数削減＋他部署へ定着\n"
            "○（ 80点・目標）：自部署でAIによる仕組み化・工数削減を実現\n"
            "△（ 60点）：棚卸し・着手のみ"),
}


def conv_quant_crit(text):
    for a, b in (("S：", "5："), ("A：", "4："), ("B：", "3："), ("C：", "2："), ("D：", "1：")):
        text = text.replace(a, b)
    return text


def conv_qual_crit(text):
    mp = {"S": "◎", "B": "○", "D": "△"}
    out = []
    for ln in text.split("\n"):
        if len(ln) >= 2 and ln[0] in "SABCD" and ln[1] == "：":
            if ln[0] in mp:
                out.append(mp[ln[0]] + "：" + ln[2:])
            # A・C 行は破棄
        else:
            out.append(ln)
    return "\n".join(out)


def conv_legend(text):
    reps = [
        ("S=100/A=90/B=80/C=70/D=60", "定量=5段階 5→100・4→90・3→80・2→70・1→60"),
        # 上半期/下半期形式（スペース＋（目標達成）付き）
        ("ランク：S=100 / A=90 / B=80（目標達成）/ C=70 / D=60",
         "ランク：定量=5段階 5=100 / 4=90 / 3=80（目標達成）/ 2=70 / 1=60"),
        ("S=100 / A=90 / B=80（目標達成）/ C=70 / D=60",
         "定量=5段階 5=100 / 4=90 / 3=80（目標達成）/ 2=70 / 1=60"),
        ("定性・バリューは3段階(S/B/D)", "定性・バリュー=3段階 ◎=100 / ○=80 / △=60"),
        ("定性・バリューは3段階（S/B/D）", "定性・バリュー=3段階 ◎=100 / ○=80 / △=60"),
    ]
    for a, b in reps:
        text = text.replace(a, b)
    return text


# ============================================================
#  評価タブ レイアウト書式 + 入力規則
# ============================================================
def eval_format_requests(sid, has_ref):
    R = []
    R.append({"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"hideGridlines": True, "frozenRowCount": 0, "frozenColumnCount": 0}},
        "fields": "gridProperties(hideGridlines,frozenRowCount,frozenColumnCount)"}})

    widths = {0: 96, 1: 150, 2: 300, 3: 300, 4: 430, 5: 120, 6: 84, 7: 110, 8: 66, 9: 110, 10: 66}
    for c, w in widths.items():
        R.append(col_width(sid, c, w))

    # クリーンアップ先行
    R.append(unmerge(sid, 21, 31, 0, 10))
    R.append(set_borders(sid, 1, 31, 0, 10, top=border("NONE"), bottom=border("NONE"),
                         left=border("NONE"), right=border("NONE"),
                         innerHorizontal=border("NONE"), innerVertical=border("NONE")))
    R.append(repeat_fmt(sid, 1, 35, 0, 10,
                        {"backgroundColor": WHITE, "horizontalAlignment": "LEFT",
                         "verticalAlignment": "MIDDLE", "wrapStrategy": "OVERFLOW_CELL",
                         "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                        ("userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment,"
                         "wrapStrategy,textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")))

    # タイトル/凡例
    R.append(repeat_fmt(sid, 1, 1, 0, 10, {"textFormat": tf(RED, 14, True)},
                        "userEnteredFormat.textFormat"))
    R.append(set_borders(sid, 1, 1, 0, 10, bottom=border("SOLID_THICK", RED)))
    R.append(row_height(sid, 1, 40))
    R.append(repeat_fmt(sid, 2, 2, 0, 10,
                        {"textFormat": tf(TEXT_GREY, 9, False), "wrapStrategy": "WRAP"},
                        "userEnteredFormat(textFormat,wrapStrategy)"))

    for br in (4, 11, 17):
        R.append(repeat_fmt(sid, br, br, 0, 10,
                            {"backgroundColor": RED_TINT, "textFormat": tf(RED, 11, True)},
                            "userEnteredFormat(backgroundColor,textFormat)"))
        # バナーを箱で囲う（左=赤太/上下右=中グレー）
        R.append(set_borders(sid, br, br, 0, 10, top=border("SOLID_MEDIUM", BORDER_STRONG),
                             bottom=border("SOLID_MEDIUM", BORDER_STRONG),
                             right=border("SOLID_MEDIUM", BORDER_STRONG)))
        R.append(set_borders(sid, br, br, 0, 0, left=border("SOLID_THICK", RED)))
        R.append(row_height(sid, br, 30))

    for hr in (5, 12, 18):
        R.append(repeat_fmt(sid, hr, hr, 0, 10,
                            {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                             "wrapStrategy": "WRAP"},
                            "userEnteredFormat(backgroundColor,textFormat,wrapStrategy)"))
        R.append(repeat_fmt(sid, hr, hr, 5, 10, {"horizontalAlignment": "CENTER"},
                            "userEnteredFormat.horizontalAlignment"))
        R.append(set_borders(sid, hr, hr, 0, 10, bottom=border("SOLID_MEDIUM", BORDER_GREY)))
        R.append(row_height(sid, hr, 26))

    for (istart, iend) in [(6, 8), (13, 14), (19, 19)]:
        R.append(repeat_fmt(sid, istart, iend, 0, 10,
                            {"wrapStrategy": "WRAP", "verticalAlignment": "TOP",
                             "textFormat": tf(TEXT_DARK, 10, False)},
                            "userEnteredFormat(wrapStrategy,verticalAlignment,textFormat)"))
        for k, rr in enumerate(range(istart, iend + 1)):
            if k % 2 == 1:
                R.append(repeat_fmt(sid, rr, rr, 0, 10, {"backgroundColor": ZEBRA},
                                    "userEnteredFormat.backgroundColor"))
        R.append(repeat_fmt(sid, istart, iend, 5, 6, {"horizontalAlignment": "CENTER"},
                            "userEnteredFormat.horizontalAlignment"))
        for pc in (8, 10):
            R.append(repeat_fmt(sid, istart, iend, pc, pc,
                                {"horizontalAlignment": "CENTER", "textFormat": tf(TEXT_DARK, 10, True)},
                                "userEnteredFormat(horizontalAlignment,textFormat)"))
        for ic in (7, 9):
            R.append(repeat_fmt(sid, istart, iend, ic, ic,
                                {"backgroundColor": YELLOW, "horizontalAlignment": "CENTER",
                                 "verticalAlignment": "MIDDLE"},
                                "userEnteredFormat(backgroundColor,horizontalAlignment,verticalAlignment)"))

    for sr in (9, 15):
        R.append(repeat_fmt(sid, sr, sr, 0, 10,
                            {"backgroundColor": SUBTOTAL_BG, "textFormat": tf(TEXT_DARK, 10, True)},
                            "userEnteredFormat(backgroundColor,textFormat)"))
        R.append(repeat_fmt(sid, sr, sr, 6, 10, {"horizontalAlignment": "CENTER"},
                            "userEnteredFormat.horizontalAlignment"))
        R.append(set_borders(sid, sr, sr, 0, 10, top=border("SOLID_MEDIUM", BORDER_GREY)))
        R.append(row_height(sid, sr, 24))

    # 各セクション表を強い箱で囲う（外周=中グレー実線・列区切り=薄・自己/上長間=中）
    for (t1, t2) in [(5, 9), (12, 15), (18, 19)]:
        R.append(set_borders(sid, t1, t2, 0, 10,
                             top=border("SOLID_MEDIUM", BORDER_STRONG),
                             left=border("SOLID_MEDIUM", BORDER_STRONG),
                             right=border("SOLID_MEDIUM", BORDER_STRONG),
                             bottom=border("SOLID_MEDIUM", BORDER_STRONG),
                             innerHorizontal=border("SOLID", BORDER_LT),
                             innerVertical=border("SOLID", BORDER_LT)))
        R.append(set_borders(sid, t1, t2, 9, 10, left=border("SOLID_MEDIUM", BORDER_STRONG)))

    # 入力規則差替（5段階 / ◎○△）
    R.append(dv_list(sid, 8, 8, 7, 7, [5, 4, 3, 2, 1]))   # H8
    R.append(dv_list(sid, 8, 8, 9, 9, [5, 4, 3, 2, 1]))   # J8
    for (c) in (7, 9):  # H,J 列
        R.append(dv_list(sid, 13, 14, c, c, ["◎", "○", "△"]))
        R.append(dv_list(sid, 19, 19, c, c, ["◎", "○", "△"]))

    # ---- 総合点カード（ハイブリッド型） ----
    R.append(merge(sid, 21, 21, 0, 6))
    R.append(repeat_fmt(sid, 21, 21, 0, 6,
                        {"backgroundColor": RED_TINT, "textFormat": tf(RED, 12, True)},
                        "userEnteredFormat(backgroundColor,textFormat)"))
    R.append(set_borders(sid, 21, 21, 0, 0, left=border("SOLID_THICK", RED)))
    R.append(row_height(sid, 21, 30))

    R.append(merge(sid, 22, 22, 0, 1))
    R.append(repeat_fmt(sid, 22, 22, 0, 3,
                        {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_GREY, 10, True),
                         "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))

    R.append(merge(sid, 23, 23, 0, 1))
    R.append(repeat_fmt(sid, 23, 23, 0, 1,
                        {"backgroundColor": RED_TINT, "textFormat": tf(RED, 11, True),
                         "horizontalAlignment": "LEFT"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(sid, 23, 23, 2, 3,
                        {"backgroundColor": RED_TINT, "textFormat": tf(RED, 22, True),
                         "horizontalAlignment": "CENTER",
                         "numberFormat": {"type": "NUMBER", "pattern": "0.0"}},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,numberFormat)"))
    R.append(row_height(sid, 23, 48))

    R.append(merge(sid, 24, 24, 0, 3))
    R.append(repeat_fmt(sid, 24, 24, 0, 3, {"textFormat": tf(TEXT_GREY, 9, False)},
                        "userEnteredFormat.textFormat"))
    R.append(row_height(sid, 24, 22))

    for rr in (25, 26, 27, 28):
        R.append(merge(sid, rr, rr, 0, 1))
        R.append(repeat_fmt(sid, rr, rr, 0, 1, {"textFormat": tf(TEXT_DARK, 10, False)},
                            "userEnteredFormat.textFormat"))
        R.append(repeat_fmt(sid, rr, rr, 2, 3,
                            {"textFormat": tf(TEXT_DARK, 12, False), "horizontalAlignment": "CENTER",
                             "numberFormat": {"type": "NUMBER", "pattern": "0.0"}},
                            "userEnteredFormat(textFormat,horizontalAlignment,numberFormat)"))
        R.append(row_height(sid, rr, 24))

    R.append(set_borders(sid, 22, 28, 0, 3, top=border("SOLID_MEDIUM", BORDER_STRONG),
                         bottom=border("SOLID_MEDIUM", BORDER_STRONG), left=border("SOLID_MEDIUM", BORDER_STRONG),
                         right=border("SOLID_MEDIUM", BORDER_STRONG), innerHorizontal=border("SOLID", BORDER_LT)))
    R.append(set_borders(sid, 22, 28, 3, 3, left=border("SOLID", BORDER_GREY)))

    # 設定・比率パネル
    R.append(merge(sid, 22, 22, 5, 6))
    R.append(repeat_fmt(sid, 22, 22, 5, 6,
                        {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                         "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(repeat_fmt(sid, 23, 26, 5, 5, {"textFormat": tf(TEXT_GREY, 10, False)},
                        "userEnteredFormat.textFormat"))
    R.append(repeat_fmt(sid, 23, 26, 6, 6,
                        {"backgroundColor": YELLOW, "textFormat": tf(TEXT_DARK, 10, True),
                         "horizontalAlignment": "CENTER"},
                        "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    R.append(set_borders(sid, 22, 26, 5, 6, top=border("SOLID_MEDIUM", BORDER_STRONG),
                         bottom=border("SOLID_MEDIUM", BORDER_STRONG), left=border("SOLID_MEDIUM", BORDER_STRONG),
                         right=border("SOLID_MEDIUM", BORDER_STRONG), innerHorizontal=border("SOLID", BORDER_LT),
                         innerVertical=border("SOLID", BORDER_LT)))

    if has_ref:
        R.append(merge(sid, 30, 30, 0, 6))
        R.append(repeat_fmt(sid, 30, 30, 0, 6, {"textFormat": tf(TEXT_GREY, 10, False)},
                            "userEnteredFormat.textFormat"))
        R.append(row_height(sid, 30, 24))

    return R


def card_value_writes(tab, has_ref):
    data = [
        (f"{tab}!A21", [["■ 総合点"]]),
        (f"{tab}!C22", [["自己評価", "上長評価"]]),
        (f"{tab}!A23", [["総合点（100点満点）"]]),
        (f"{tab}!C23", [["=C27*$G$25+C28*$G$26", "=D27*$G$25+D28*$G$26"]]),
        (f"{tab}!A24", [["― 内訳（評価軸別）―"]]),
        (f"{tab}!A25", [["定量 評価点"]]),
        (f"{tab}!C25", [["=I9", "=K9"]]),
        (f"{tab}!A26", [["定性 評価点"]]),
        (f"{tab}!C26", [["=I15", "=K15"]]),
        (f"{tab}!A27", [["目標 評価点"]]),
        (f"{tab}!C27", [["=C25*$G$23+C26*$G$24", "=D25*$G$23+D26*$G$24"]]),
        (f"{tab}!A28", [["バリュー評価点"]]),
        (f"{tab}!C28", [["=I19", "=K19"]]),
        (f"{tab}!F22", [["【設定・比率】"]]),
        (f"{tab}!F23", [["定量の比率", 0.6]]),
        (f"{tab}!F24", [["定性の比率", 0.4]]),
        (f"{tab}!F25", [["目標評価の比率", 0.7]]),
        (f"{tab}!F26", [["バリュー比率", 0.3]]),
    ]
    if has_ref:
        data.append((f"{tab}!A30", [[
            '="参考：半期の総合点（上長）　　上半期 "&TEXT(\'上半期\'!D23,"0.0")&"  ／  下半期 "&TEXT(\'下半期\'!D23,"0.0")'
        ]]))
    return data


def dashboard_value_writes():
    return [
        (f"{DASH}!A6", [["='通期'!D23"]]),
        (f"{DASH}!C6", [["='上半期'!D23"]]),
        (f"{DASH}!E6", [["='下半期'!D23"]]),
        (f"{DASH}!B13", [["='上半期'!D25", "='下半期'!D25", "='通期'!D25"]]),
        (f"{DASH}!B14", [["='上半期'!D26", "='下半期'!D26", "='通期'!D26"]]),
        (f"{DASH}!B15", [["='上半期'!D27", "='下半期'!D27", "='通期'!D27"]]),
        (f"{DASH}!B16", [["='上半期'!D28", "='下半期'!D28", "='通期'!D28"]]),
        (f"{DASH}!B17", [["='上半期'!D23", "='下半期'!D23", "='通期'!D23"]]),
    ]


def dashboard_format(sid):
    """ダッシュボード: 行固定解除＋グリッドOFF＋各ブロックを中グレーの箱で囲う。"""
    R = [{"updateSheetProperties": {
        "properties": {"sheetId": sid,
                       "gridProperties": {"hideGridlines": True, "frozenRowCount": 0, "frozenColumnCount": 0}},
        "fields": "gridProperties(hideGridlines,frozenRowCount,frozenColumnCount)"}}]
    # (ヒーロー, スコア内訳, 目標一覧×3) のブロックを箱囲い
    for (r1, r2) in [(5, 9), (12, 17), (20, 26), (29, 35), (38, 44)]:
        R.append(set_borders(sid, r1, r2, 0, 5, top=border("SOLID_MEDIUM", BORDER_STRONG),
                             bottom=border("SOLID_MEDIUM", BORDER_STRONG),
                             left=border("SOLID_MEDIUM", BORDER_STRONG),
                             right=border("SOLID_MEDIUM", BORDER_STRONG)))
    return R


# ============================================================
#  評価基準タブ / 点数定義ガイド 再構築
# ============================================================
def kijun_content():
    rows = [
        ["評価基準 ｜ 各目標の達成定義"],
        ["売上はバリアブル（実績÷目標×100・100%超も加点）。定量＝5段階(5/4/3/2/1)、定性・バリュー＝3段階(◎/○/△)。"],
        [],
        ["項目", "ランク", "点", "達成の基準（この状態なら、その点）"],
        ["定量① CA個人売上", "5", "100", "達成率 120%以上（通期 ¥44,807,116 〜）"],
        ["", "4", "90", "達成率 110%（¥41,073,189）"],
        ["", "3", "80", "達成率 100%＝目標達成（¥37,339,263）"],
        ["", "2", "70", "達成率 90%（¥33,605,337）"],
        ["", "1", "60", "達成率 80%以下（〜¥29,871,410）"],
        ["定量② CAチーム売上", "5", "100", "達成率 120%以上（通期 ¥123,254,994 〜）"],
        ["", "4", "90", "達成率 110%（¥112,983,745）"],
        ["", "3", "80", "達成率 100%＝目標達成（¥102,712,495）"],
        ["", "2", "70", "達成率 90%（¥92,441,246）"],
        ["", "1", "60", "達成率 80%以下（〜¥82,169,996）"],
        ["定量③ 新規メンバーアサイン", "5", "100", "2名以上アサイン＋うち自ら2名をリクルーティング採用"],
        ["", "4", "90", "2名アサイン完了（受け入れ準備も整っている）"],
        ["", "3", "80", "1名アサイン＋受け入れ準備完了（＝目標）"],
        ["", "2", "70", "1名アサイン（立ち上げに遅延）"],
        ["", "1", "60", "未アサイン・採用着手のみ"],
        ["定性① メンバー育成", "◎", "100", "研修完成＋オンボ実行＋月400万を複数輩出/自走まで到達"],
        ["", "○", "80", "研修完成・オンボ立案実行・月400万1名のめど（＝目標）"],
        ["", "△", "60", "研修着手のみ・オンボ未実行"],
        ["定性② メディア立ち上げ", "◎", "100", "公開＋継続発信＋安定流入＋紹介/イベントへ送客が回る"],
        ["", "○", "80", "メディアを立ち上げ公開し初期流入を確認（＝目標）"],
        ["", "△", "60", "企画・設計のみで未公開"],
        ["バリュー 特盛級の価値貢献", "◎", "100", "複数部署で運用＋工数削減＋質向上＋他部署に定着"],
        ["", "○", "80", "自部署でAI仕組み化し工数削減を実現（＝目標）"],
        ["", "△", "60", "棚卸し・着手のみ"],
    ]
    return rows


def guide_content():
    rows = [
        ["点数定義ガイド ｜ 人事評価シート（CA）2026年度"],
        ["ランクを選ぶと点数が自動で入ります。80点（達成ライン）が基準です。"],
        [],
        ["■ 定量③ アサイン：5段階（数字）"],
        ["ランク", "点数", "達成度の目安", "評価のイメージ"],
        ["5", "100", "目標の120%相当", "大幅に上回って達成"],
        ["4", "90", "110%", "上回って達成"],
        ["3", "80", "100%（目標達成）", "目標どおり達成（標準ライン）"],
        ["2", "70", "90%", "あと一歩・一部未達"],
        ["1", "60", "80%以下", "未達・要改善"],
        [],
        ["■ 定性①② ・ バリュー：3段階（記号）"],
        ["ランク", "点数", "意味"],
        ["◎", "100", "期待を超える（超過達成）"],
        ["○", "80", "目標どおり達成（標準ライン）"],
        ["△", "60", "未達・要改善"],
        [],
        ["■ 売上（定量①②）はバリアブル（100%超も計測）"],
        ["式", "売上の点数 ＝ 実績額 ÷ 目標額 × 100（上限なし・100点超もそのまま反映）"],
        ["例", "目標 ¥1,000万 に対し実績 ¥1,200万 → 120点"],
        [],
        ["■ 計算の流れ"],
        ["①", "各項目：選んだランク（売上は実績額）から点数を自動算出"],
        ["②", "定量 評価点 ＝ 定量内ウェイト × 各点（合計100%）"],
        ["③", "定性 評価点 ＝ 定性内ウェイト × 各点（合計100%）"],
        ["④", "目標評価点 ＝ 定量 × 60% ＋ 定性 × 40%"],
        ["⑤", "総合点 ＝ 目標評価点 × 70% ＋ バリュー評価点 × 30%"],
        [],
        ["■ 入力をラクにする工夫"],
        ["・", "初期値は 定量③=3／定性・バリュー=○（達成）。違う項目だけ変える"],
        ["・", "上長ﾗﾝｸが空欄なら自己評価を自動採用（上長は差分だけ入力）"],
        ["・", "通期は上半期・下半期から自動集計。上書きしたい項目だけ入力する"],
        ["・", "赤いセル（区分内ウェイト・ランク・実績・比率）が入力欄"],
    ]
    return rows


def ref_tab_format(sid, ncols, title_cols):
    """評価基準/ガイド 共通の軽い書式（unmerge→グリッドOFF→タイトル/基本）。"""
    R = [unmerge(sid, 1, 60, 0, 11),
         {"updateSheetProperties": {
             "properties": {"sheetId": sid,
                            "gridProperties": {"hideGridlines": True, "frozenRowCount": 0, "frozenColumnCount": 0}},
             "fields": "gridProperties(hideGridlines,frozenRowCount,frozenColumnCount)"}},
         set_borders(sid, 1, 60, 0, ncols - 1, top=border("NONE"), bottom=border("NONE"),
                     left=border("NONE"), right=border("NONE"),
                     innerHorizontal=border("NONE"), innerVertical=border("NONE")),
         repeat_fmt(sid, 1, 60, 0, 11,
                    {"backgroundColor": WHITE, "verticalAlignment": "MIDDLE",
                     "wrapStrategy": "WRAP",
                     "textFormat": {"foregroundColor": TEXT_DARK, "fontSize": 10, "bold": False}},
                    ("userEnteredFormat(backgroundColor,verticalAlignment,wrapStrategy,"
                     "textFormat.foregroundColor,textFormat.fontSize,textFormat.bold)")),
         merge(sid, 1, 1, 0, title_cols - 1),
         repeat_fmt(sid, 1, 1, 0, 0, {"textFormat": tf(RED, 13, True)}, "userEnteredFormat.textFormat"),
         set_borders(sid, 1, 1, 0, ncols - 1, bottom=border("SOLID_THICK", RED)),
         merge(sid, 2, 2, 0, title_cols - 1),
         repeat_fmt(sid, 2, 2, 0, 0, {"textFormat": tf(TEXT_GREY, 9, False)}, "userEnteredFormat.textFormat"),
         ]
    return R


def main():
    creds = Credentials.from_authorized_user_file(TOKEN)
    svc = build("sheets", "v4", credentials=creds)
    ss = svc.spreadsheets()

    # ===== 評価タブ 3枚 =====
    for tab, sid in EVAL_TABS.items():
        has_ref = (tab == "通期")
        print(f"[{tab}] sid={sid} has_ref={has_ref}")

        # --- 現状読み（ランク式・入力値・基準・凡例） ---
        f_ranges = [f"{tab}!{c}" for c, _, _ in RANK_CELLS]
        v_ranges = ([f"{tab}!{c}" for c, _ in INPUT_CELLS] + [f"{tab}!{c}" for c in CRIT_QUANT]
                    + [f"{tab}!{c}" for c in CRIT_QUAL] + [f"{tab}!A2"])
        fcur = ss.values().batchGet(spreadsheetId=SS, ranges=f_ranges,
                                    valueRenderOption="FORMULA").execute().get("valueRanges", [])
        vcur = ss.values().batchGet(spreadsheetId=SS, ranges=v_ranges,
                                    valueRenderOption="UNFORMATTED_VALUE").execute().get("valueRanges", [])

        def cell_of(vr):
            v = vr.get("values")
            return v[0][0] if v and v[0] else ""

        # ランク式の差替
        rank_writes = []
        for (cell, ref, lvl), vr in zip(RANK_CELLS, fcur):
            cur = cell_of(vr)
            new = cur.replace(old_ladder(ref), new_ladder5(ref) if lvl == 5 else new_ladder3(ref))
            if new == cur and old_ladder(ref) not in cur:
                print(f"   !! {cell} ラダー未検出: {cur[:80]}")
            rank_writes.append((f"{tab}!{cell}", [[new]]))

        # 入力値の移行
        n = len(INPUT_CELLS)
        for (cell, lvl), vr in zip(INPUT_CELLS, vcur[:n]):
            cur = cell_of(vr)
            if cur == "" or cur in (NEW5 if lvl == 5 else NEW3):
                continue
            mp = MAP5 if lvl == 5 else MAP3
            if cur in mp:
                rank_writes.append((f"{tab}!{cell}", [[mp[cur]]]))
            else:
                print(f"   !! {cell} 移行不能な値: {cur!r}")
        # 評価基準(D列) は明確化版CRIT_TEXTへ全置換
        off = n + len(CRIT_QUANT) + len(CRIT_QUAL)
        for cell in CRIT_QUANT + CRIT_QUAL:
            rank_writes.append((f"{tab}!{cell}", [[CRIT_TEXT[cell]]]))
        legend = str(cell_of(vcur[off]))
        rank_writes.append((f"{tab}!A2", [[conv_legend(legend)]]))
        # 列ヘッダー「評価基準（S〜D）」→ ランク表記刷新に合わせて中立表記へ
        for hc in ("D5", "D12", "D18"):
            rank_writes.append((f"{tab}!{hc}", [["評価基準（達成定義）"]]))

        # --- 適用：カード左域クリア → 書式 → 値（カード+ランク） → 項目行を内容に合わせ自動リサイズ ---
        ss.values().batchClear(spreadsheetId=SS, body={"ranges": [f"{tab}!A21:E31"]}).execute()
        ss.batchUpdate(spreadsheetId=SS, body={"requests": eval_format_requests(sid, has_ref)}).execute()
        allw = card_value_writes(tab, has_ref) + rank_writes
        ss.values().batchUpdate(spreadsheetId=SS, body={
            "valueInputOption": "USER_ENTERED",
            "data": [{"range": r, "values": v} for r, v in allw]}).execute()
        # 項目行(6-8,13-14,19)を内容に合わせ自動高さ調整（定量がギュッと潰れる対策）
        auto = []
        for (a, b) in [(5, 7), (12, 13), (18, 18)]:  # 0始まりindex: 行6-8 / 行13-14 / 行19
            auto.append({"autoResizeDimensions": {"dimensions": {
                "sheetId": sid, "dimension": "ROWS", "startIndex": a, "endIndex": b + 1}}})
        ss.batchUpdate(spreadsheetId=SS, body={"requests": auto}).execute()
        print(f"   done. (card {len(card_value_writes(tab, has_ref))} + rank {len(rank_writes)} writes + autoresize)")

    # ===== ダッシュボード =====
    print(f"[{DASH}] 参照追従修正＋枠線強化＋行固定解除")
    ss.values().batchUpdate(spreadsheetId=SS, body={
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": r, "values": v} for r, v in dashboard_value_writes()]}).execute()
    ss.batchUpdate(spreadsheetId=SS, body={"requests": dashboard_format(1183931973)}).execute()

    # ===== 評価基準タブ =====
    print(f"[{KIJUN}] 再構築")
    # ★先にunmerge（旧結合の非アンカーへの書込が無視される事故を防ぐ）
    ss.batchUpdate(spreadsheetId=SS, body={"requests": [unmerge(KIJUN_SID, 1, 60, 0, 11)]}).execute()
    ss.values().batchClear(spreadsheetId=SS, body={"ranges": [f"{KIJUN}!A1:H60"]}).execute()
    kc = kijun_content()
    ss.values().update(spreadsheetId=SS, range=f"{KIJUN}!A1",
                       valueInputOption="USER_ENTERED", body={"values": kc}).execute()
    kreq = ref_tab_format(KIJUN_SID, 4, 4)
    for c, w in {0: 210, 1: 64, 2: 50, 3: 560}.items():
        kreq.append(col_width(KIJUN_SID, c, w))
    kreq.append(repeat_fmt(KIJUN_SID, 4, 4, 0, 3,
                           {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True),
                            "horizontalAlignment": "CENTER"},
                           "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"))
    kreq.append(set_borders(KIJUN_SID, 4, len(kc), 0, 3, innerHorizontal=border("SOLID", BORDER_LT),
                            innerVertical=border("SOLID", BORDER_LT),
                            top=border("SOLID_MEDIUM", BORDER_STRONG), bottom=border("SOLID_MEDIUM", BORDER_STRONG),
                            left=border("SOLID_MEDIUM", BORDER_STRONG), right=border("SOLID_MEDIUM", BORDER_STRONG)))
    kreq.append(repeat_fmt(KIJUN_SID, 5, len(kc), 1, 2, {"horizontalAlignment": "CENTER"},
                           "userEnteredFormat.horizontalAlignment"))
    # 目標名の行を太字＋各目標ブロックの上に中グレー区切り線（囲い強化）
    for i, row in enumerate(kc, 1):
        if i >= 5 and row and row[0]:
            kreq.append(repeat_fmt(KIJUN_SID, i, i, 0, 0, {"textFormat": tf(TEXT_DARK, 10, True)},
                                   "userEnteredFormat.textFormat"))
            if i > 5:
                kreq.append(set_borders(KIJUN_SID, i, i, 0, 3, top=border("SOLID_MEDIUM", BORDER_STRONG)))
    ss.batchUpdate(spreadsheetId=SS, body={"requests": kreq}).execute()

    # ===== 点数定義ガイド =====
    print(f"[{GUIDE}] 再構築")
    # ★先にunmerge（同上）
    ss.batchUpdate(spreadsheetId=SS, body={"requests": [unmerge(GUIDE_SID, 1, 60, 0, 11)]}).execute()
    ss.values().batchClear(spreadsheetId=SS, body={"ranges": [f"{GUIDE}!A1:H60"]}).execute()
    gc = guide_content()
    ss.values().update(spreadsheetId=SS, range=f"{GUIDE}!A1",
                       valueInputOption="USER_ENTERED", body={"values": gc}).execute()
    greq = ref_tab_format(GUIDE_SID, 4, 4)
    for c, w in {0: 70, 1: 70, 2: 220, 3: 360}.items():
        greq.append(col_width(GUIDE_SID, c, w))
    # 小見出し(■)行を強調 / 「ラベル+説明」の2列行は説明をB:Dへ広げて折返し
    for i, row in enumerate(gc, 1):
        if row and isinstance(row[0], str) and row[0].startswith("■"):
            greq.append(merge(GUIDE_SID, i, i, 0, 3))
            greq.append(repeat_fmt(GUIDE_SID, i, i, 0, 3,
                                   {"backgroundColor": RED_TINT, "textFormat": tf(RED, 11, True)},
                                   "userEnteredFormat(backgroundColor,textFormat)"))
        elif len(row) == 2:
            greq.append(merge(GUIDE_SID, i, i, 1, 3))
            greq.append(repeat_fmt(GUIDE_SID, i, i, 1, 3,
                                   {"wrapStrategy": "WRAP", "verticalAlignment": "MIDDLE",
                                    "horizontalAlignment": "LEFT"},
                                   "userEnteredFormat(wrapStrategy,verticalAlignment,horizontalAlignment)"))
            greq.append(repeat_fmt(GUIDE_SID, i, i, 0, 0,
                                   {"horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE",
                                    "textFormat": tf(TEXT_DARK, 10, True)},
                                   "userEnteredFormat(horizontalAlignment,verticalAlignment,textFormat)"))
    # 5段階/3段階テーブルのヘッダ行を強調
    for i, row in enumerate(gc, 1):
        if row and row[0] == "ランク":
            greq.append(repeat_fmt(GUIDE_SID, i, i, 0, 3,
                                   {"backgroundColor": GREY_HEAD, "textFormat": tf(TEXT_DARK, 10, True)},
                                   "userEnteredFormat(backgroundColor,textFormat)"))
    ss.batchUpdate(spreadsheetId=SS, body={"requests": greq}).execute()

    print("ALL DONE")


if __name__ == "__main__":
    main()
