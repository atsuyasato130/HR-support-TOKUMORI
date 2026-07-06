#!/usr/bin/env python3
"""FUSION 中途 歩留まり分析「新タブ」生成（既存タブ非破壊）。

- raw_data を Sheets API(UNFORMATTED_VALUE)で読み、シリアル日付で集計。
- 配色は既存HRMOSタブ（歩留まり分析・レポート出力）に統一：スレート#37474F/#263238・
  サブ#ECEFF1・ゼブラ#F5F5F5・枠#B0BEC5・状態色 good#C8E6C9/warn#FFF59D/bad#FFCDD2。
- シート内ネイティブチャート（週次トレンド折れ線・ファネル横棒）を生成。
- 既存タブは一切変更しない（snapshot前後比較で検証）。冪等（対象タブのみ全クリア→再描画）。
正本: ~/Claude AI/build_hrmos_funnel_v2.py
"""
import os
import re
import datetime as dt
from collections import Counter, defaultdict

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ===== 設定 =====
SID = "1zNv4az6PLaoO2ltdKudvZW3SM7XFzkkrD8E50vhMULU"
TOKEN = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config/token_sheets.json")
TAB = "★歩留まり分析ダッシュボード"
TZ = dt.timezone(dt.timedelta(hours=9))
BASE = dt.date(1899, 12, 30)
N_COLS = 24
N_ROWS = 230
TODAY = dt.datetime.now(TZ).date()


def hx(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


# ===== 配色（既存HRMOSタブに統一） =====
TITLE_BG = hx("263238")
HEAD_BG  = hx("37474F")
SUBBAND  = hx("ECEFF1")
INK      = hx("263238")
SUBINK   = hx("546E7A")
WHITE    = hx("FFFFFF")
ZEBRA    = hx("F5F5F5")
BORDER   = hx("B0BEC5")
GRID_B   = hx("CFD8DC")
GOOD     = hx("C8E6C9")
WARN     = hx("FFF59D")
BAD      = hx("FFCDD2")
PAPER    = WHITE
FONT = "Arial"


# ===== Grid（build_dotz_kpi.py の設計を流用） =====
class Grid:
    def __init__(self, sheet_id, n_rows, n_cols):
        self.sid = sheet_id
        self.vals = [["" for _ in range(n_cols)] for _ in range(n_rows)]
        self.reqs = []
        self.row_h = {}

    def put(self, r, c, v):
        self.vals[r][c] = "" if v is None else v

    def row(self, r, c, items):
        for i, v in enumerate(items):
            self.put(r, c + i, v)

    def rowh(self, r, px):
        self.row_h[r] = px

    def _rng(self, r0, c0, r1, c1):
        return {"sheetId": self.sid, "startRowIndex": r0, "endRowIndex": r1,
                "startColumnIndex": c0, "endColumnIndex": c1}

    def merge(self, r0, c0, r1, c1):
        self.reqs.append({"mergeCells": {"range": self._rng(r0, c0, r1, c1), "mergeType": "MERGE_ALL"}})

    def fmt(self, r0, c0, r1, c1, bg=None, fg=None, bold=False, size=None,
            halign=None, valign="MIDDLE", numfmt=None, wrap=None):
        cf = {}
        tf = {"foregroundColor": fg or INK, "bold": bold, "fontFamily": FONT}
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
        self.reqs.append({"repeatCell": {"range": self._rng(r0, c0, r1, c1),
                          "cell": {"userEnteredFormat": cf}, "fields": fields}})

    def border(self, r0, c0, r1, c1, color=None, outer=True, inner=False, bottom_only=False, style="SOLID"):
        color = color or BORDER
        b = {"style": style, "color": color}
        req = {"updateBorders": {"range": self._rng(r0, c0, r1, c1)}}
        if bottom_only:
            req["updateBorders"]["bottom"] = b
        else:
            if outer:
                req["updateBorders"].update({"top": b, "bottom": b, "left": b, "right": b})
            if inner:
                ib = {"style": "SOLID", "color": GRID_B}
                req["updateBorders"].update({"innerHorizontal": ib, "innerVertical": ib})
        self.reqs.append(req)

    def cellbg(self, r, c, bg):
        self.reqs.append({"repeatCell": {"range": self._rng(r, c, r + 1, c + 1),
                          "cell": {"userEnteredFormat": {"backgroundColor": bg}},
                          "fields": "userEnteredFormat.backgroundColor"}})


def section(g, r, c0, c1, text):
    """既存レポート出力風サブ見出し（#ECEFF1帯・スレート文字・下枠）。"""
    g.put(r, c0, text)
    g.merge(r, c0, r + 1, c1 + 1)
    g.fmt(r, c0, r + 1, c1 + 1, bg=SUBBAND, fg=INK, bold=True, size=11, halign="LEFT")
    g.border(r, c0, r + 1, c1 + 1, color=BORDER)
    g.rowh(r, 24)
    return r + 1


def table(g, r0, c0, headers, data, aligns=None, zebra=True):
    nc = len(headers)
    g.row(r0, c0, headers)
    g.fmt(r0, c0, r0 + 1, c0 + nc, bg=HEAD_BG, fg=WHITE, bold=True, size=9, halign="CENTER", wrap="WRAP")
    g.rowh(r0, 26)
    for i, drow in enumerate(data):
        rr = r0 + 1 + i
        g.row(rr, c0, drow)
        bg = ZEBRA if (zebra and i % 2 == 1) else WHITE
        g.fmt(rr, c0, rr + 1, c0 + nc, bg=bg, fg=INK, size=9, valign="MIDDLE")
        for j in range(nc):
            al = (aligns[j] if aligns else ("LEFT" if j == 0 else "CENTER"))
            g.fmt(rr, c0 + j, rr + 1, c0 + j + 1, halign=al)
        g.rowh(rr, 21)
    g.border(r0, c0, r0 + 1 + len(data), c0 + nc, color=BORDER, inner=True)
    return r0 + 1 + len(data)


def arrow(c, p):
    d = c - p
    return f"前週比 ▲+{d}" if d > 0 else (f"前週比 ▼{d}" if d < 0 else "前週比 →±0")


def render_strip(g, r, title, items, value_bg=None):
    """最上部サマリー帯：タイトル＋カード（ラベル上/値下）。次行を返す。"""
    vbg = value_bg or SUBBAND
    g.put(r, 0, title); g.merge(r, 0, r + 1, N_COLS)
    g.fmt(r, 0, r + 1, N_COLS, bg=SUBBAND, fg=INK, bold=True, size=10, halign="LEFT")
    g.rowh(r, 20)
    rr = r + 1
    n = len(items)
    span = N_COLS // n
    for i, (lab, val) in enumerate(items):
        c0 = i * span
        end = (i + 1) * span if i < n - 1 else N_COLS
        g.put(rr, c0, lab); g.put(rr + 1, c0, val)
        g.merge(rr, c0, rr + 1, end); g.merge(rr + 1, c0, rr + 2, end)
        g.fmt(rr, c0, rr + 1, end, bg=HEAD_BG, fg=WHITE, bold=True, size=9, halign="CENTER")
        g.fmt(rr + 1, c0, rr + 2, end, bg=vbg, fg=INK, bold=True, size=14, halign="CENTER")
        g.border(rr, c0, rr + 2, end, color=BORDER)
    g.rowh(rr, 18); g.rowh(rr + 1, 28)
    return rr + 2


def chart_req(sid, title, ctype, anchor_r, anchor_c, hdr_row, ndata, dom_col, series_cols, w=540, h=300):
    """ネイティブチャート（折れ線/縦棒/横棒）を sourceRanges 連動で生成。"""
    def rng(col):
        return {"sheetId": sid, "startRowIndex": hdr_row, "endRowIndex": hdr_row + 1 + ndata,
                "startColumnIndex": col, "endColumnIndex": col + 1}
    target = "BOTTOM_AXIS" if ctype == "BAR" else "LEFT_AXIS"
    return {"addChart": {"chart": {
        "spec": {"title": title, "basicChart": {
            "chartType": ctype, "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
            "domains": [{"domain": {"sourceRange": {"sources": [rng(dom_col)]}}}],
            "series": [{"series": {"sourceRange": {"sources": [rng(c)]}},
                        "targetAxis": target} for c in series_cols],
        }},
        "position": {"overlayPosition": {
            "anchorCell": {"sheetId": sid, "rowIndex": anchor_r, "columnIndex": anchor_c},
            "widthPixels": w, "heightPixels": h}},
    }}}


# ===== データ取得 / 集計 =====
def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


STEP_COLS = ["1次ステップ実施日", "2次ステップ実施日", "3次ステップ実施日", "4次ステップ実施日", "5次ステップ実施日"]
STEP_LBL = ["カジュアル面談", "1次", "2次", "最終", "会食"]
FLOW = ["エントリー"] + STEP_LBL + ["内定", "承諾"]
SHORT = {"株式会社": "", "パーソルキャリア": "パーソル", "インディードリクルートパートナーズ": "インディード",
         "Ｄｉｇｉｔａｌ Ａｒｒｏｗ Ｐａｒｔｎｅｒｓ": "Digital Arrow", "Ｈｙｐｅ Ａｇｅｎｃｙ": "Hype Agency",
         "Ｈａｊｉｍａｒｉ": "Hajimari"}


def short(s):
    for a, b in SHORT.items():
        s = s.replace(a, b)
    return s.strip()


def load_records(svc):
    vals = svc.spreadsheets().values().get(
        spreadsheetId=SID, range="raw_data!A1:DV3000",
        valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
    hdr = vals[0]
    idx = {str(h).strip(): i for i, h in enumerate(hdr)}

    def gs(row, n):
        i = idx.get(n)
        v = row[i] if i is not None and i < len(row) else ""
        return str(v).strip() if v is not None else ""

    def gd(row, n):
        i = idx.get(n)
        v = row[i] if i is not None and i < len(row) else None
        return BASE + dt.timedelta(days=int(v)) if isinstance(v, (int, float)) and v else None

    def src(row):
        cat = gs(row, "応募経路"); comp = gs(row, "エージェント企業名"); det = gs(row, "応募経路詳細")
        if cat == "エージェント":
            if comp:
                return comp
            m = re.search(r"[（(]([^（）()]+)[）)]\s*$", det)
            return m.group(1) if m else (det or "エージェント不明")
        return det or cat or "（未記入）"

    recs = []
    for row in vals[1:]:
        jobid = gs(row, "求人ID")
        if not jobid:
            continue
        pos = gs(row, "選考ポジション名") or gs(row, "求人名")
        jobname = gs(row, "求人名")
        excluded = pos == "テスト" or jobname == "テスト" or not pos
        koyou = "業務委託" if (
            jobid.startswith("99") or "業務委託" in pos or "業務委託" in jobname
        ) else "正社員"
        recs.append({
            "pos": pos, "koyou": koyou, "jobid": jobid, "src": src(row), "cat": gs(row, "応募経路"),
            "app": gd(row, "応募日"), "steps": [gd(row, c) for c in STEP_COLS],
            "offer": gd(row, "内定日"), "accept": gd(row, "内定承諾日"),
            "join": gd(row, "入社日"), "decline": gd(row, "辞退日"),
            "fail": gd(row, "不合格・重複終了日"), "decline_reason": gs(row, "辞退理由（分類）"),
            "excluded": excluded,
        })
    return recs


def inw(d, a, b):
    return d is not None and a <= d <= b


def funnel_counts(records):
    c = [0] * 8
    c[0] = len(records)
    for x in records:
        for i in range(5):
            if x["steps"][i]:
                c[i + 1] += 1
        if x["offer"]:
            c[6] += 1
        if x["accept"]:
            c[7] += 1
    return c


def weakest_stage(c):
    worst, idx = 2.0, -1
    for i in range(1, 8):
        if c[i - 1] > 0:
            p = c[i] / c[i - 1]
            if p < worst:
                worst, idx = p, i
    if idx < 0:
        return "—", "—"
    return f"{FLOW[idx-1]}→{FLOW[idx]}", f"{round(worst*100)}%"


def pct(n, d):
    return f"{round(n/d*100,1)}%" if d else "—"


def col_letter(c):
    s = ""
    c += 1
    while c:
        c, m = divmod(c - 1, 26)
        s = chr(65 + m) + s
    return s


def main():
    svc = get_service()
    recs = load_records(svc)
    analysis = [r for r in recs if not r["excluded"]]

    last_wed = TODAY - dt.timedelta(days=(TODAY.weekday() - 2) % 7)
    cur_month = (dt.date(TODAY.year, TODAY.month, 1), TODAY)

    def cohort(records, a, b):
        return [r for r in records if inw(r["app"], a, b)]

    a_all = analysis
    a_emp = [r for r in a_all if r["koyou"] == "正社員"]
    a_gyo = [r for r in a_all if r["koyou"] == "業務委託"]
    a_month = cohort(analysis, *cur_month)
    f_all = funnel_counts(a_all)
    f_month = funnel_counts(a_month)
    weak_label, weak_val = weakest_stage(f_all)

    weeks = []
    for i in range(11, -1, -1):
        wed = last_wed - dt.timedelta(days=7 * i)
        thu = wed - dt.timedelta(days=6)
        flow = {"応募": sum(1 for r in analysis if inw(r["app"], thu, wed))}
        for si, lbl in enumerate(["面談", "1次", "2次", "最終"]):
            flow[lbl] = sum(1 for r in analysis if inw(r["steps"][si], thu, wed))
        flow["内定"] = sum(1 for r in analysis if inw(r["offer"], thu, wed))
        flow["承諾"] = sum(1 for r in analysis if inw(r["accept"], thu, wed))
        weeks.append((f"{thu.month}/{thu.day}-{wed.month}/{wed.day}", flow))

    # 今週(直近 木〜水)・前週・当月のフルファネル(flow)＋進行中(在庫)
    this_w = (last_wed - dt.timedelta(days=6), last_wed)
    prev_w = (last_wed - dt.timedelta(days=13), last_wed - dt.timedelta(days=7))

    def flow_counts(a, b):
        c = [0] * 8
        c[0] = sum(1 for r in analysis if inw(r["app"], a, b))
        for i in range(5):
            c[i + 1] = sum(1 for r in analysis if inw(r["steps"][i], a, b))
        c[6] = sum(1 for r in analysis if inw(r["offer"], a, b))
        c[7] = sum(1 for r in analysis if inw(r["accept"], a, b))
        return c
    fw_week = flow_counts(*this_w); fw_prev = flow_counts(*prev_w); fw_month = flow_counts(*cur_month)
    app_tw, app_pw = fw_week[0], fw_prev[0]

    def _stage(r):
        if r["offer"]:
            return "内定"
        for i in range(4, -1, -1):
            if r["steps"][i]:
                return FLOW[i + 1]
        return "エントリー"
    active_by = Counter(_stage(r) for r in a_all if not (r["accept"] or r["join"] or r["decline"] or r["fail"]))
    n_active = sum(active_by.values())

    # 週次×職種 応募マトリクス（プルダウン切替ウィジェット用・直近12週）
    wk_ranges = []
    for i in range(11, -1, -1):
        wd = last_wed - dt.timedelta(days=7 * i)
        thd = wd - dt.timedelta(days=6)
        wk_ranges.append((f"{thd.month}/{thd.day}-{wd.month}/{wd.day}", thd, wd))
    jw = defaultdict(lambda: [0] * 12)
    for x in analysis:
        if x["app"]:
            for wi, (lbl, a, b) in enumerate(wk_ranges):
                if a <= x["app"] <= b:
                    jw[x["pos"]][wi] += 1
                    break
    matrix_jobs = sorted(jw.items(), key=lambda kv: -sum(kv[1]))[:12]
    wk_labels = [lbl for lbl, _, _ in wk_ranges]

    funnel_rows = []
    for i, lbl in enumerate(FLOW):
        prev_pct = "—" if i == 0 else pct(f_all[i], f_all[i - 1])
        cum_pct = "100%" if i == 0 else pct(f_all[i], f_all[0])
        drop = 0 if i == 0 else max(0, f_all[i - 1] - f_all[i])
        funnel_rows.append([lbl, f_all[i], prev_pct, cum_pct, drop])

    def _build_media(records, month_counter):
        by_src = defaultdict(list)
        for r in records:
            by_src[r["src"]].append(r)
        result = []
        for k, rs in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
            cc = funnel_counts(rs)
            offer = cc[6]
            result.append({"name": short(k), "month": month_counter.get(k, 0), "app": cc[0], "cc": cc,
                           "men": pct(cc[1], cc[0]), "first": pct(cc[2], cc[0]),
                           "offer_rate": pct(offer, cc[0]), "offer": offer,
                           "need": (round(cc[0] / offer, 1) if offer else "—")})
        return result

    month_src = Counter(r["src"] for r in a_month if r["koyou"] == "正社員")
    month_src_gyo = Counter(r["src"] for r in a_month if r["koyou"] == "業務委託")
    media = _build_media(a_emp, month_src)
    media_gyo = _build_media(a_gyo, month_src_gyo)

    # エージェント×職種 クロス（正社員のみ・エージェント別グループ・フルファネル）
    ag_groups = defaultdict(list)
    for r in a_emp:
        if r["cat"] == "エージェント":
            ag_groups[short(r["src"])].append(r)
    cross_rows, total_idx = [], []
    for ag, rs in sorted(ag_groups.items(), key=lambda kv: -len(kv[1]))[:8]:
        total_idx.append(len(cross_rows))
        cross_rows.append([ag, "(合計)"] + funnel_counts(rs))
        by_job = defaultdict(list)
        for x in rs:
            by_job[x["pos"]].append(x)
        for job, jr in sorted(by_job.items(), key=lambda kv: -len(kv[1]))[:6]:
            cross_rows.append(["", job] + funnel_counts(jr))

    def _build_jobs(records):
        by_pos = defaultdict(list)
        for r in records:
            by_pos[r["pos"]].append(r)
        result = []
        for k, rs in sorted(by_pos.items(), key=lambda kv: -len(kv[1])):
            cc = funnel_counts(rs)
            result.append([k] + cc + [pct(cc[6], cc[0])])
        return result

    jobs = _build_jobs(a_emp)
    jobs_gyo = _build_jobs(a_gyo)

    n_decline = sum(1 for r in a_all if r["decline"])
    n_fail = sum(1 for r in a_all if r["fail"])
    reasons = Counter(r["decline_reason"] for r in a_all if r["decline"] and r["decline_reason"])

    # ===== タブ作成 or クリア =====
    before = svc.spreadsheets().get(
        spreadsheetId=SID, fields="sheets(properties(sheetId,title))").execute()["sheets"]
    before_map = {s["properties"]["sheetId"]: s["properties"]["title"] for s in before}
    existing = {t: sid for sid, t in before_map.items()}

    if TAB in existing:
        sid = existing[TAB]
        # 既存チャートも削除（冪等）
        meta = svc.spreadsheets().get(spreadsheetId=SID,
                fields="sheets(properties(sheetId),charts(chartId))").execute()["sheets"]
        del_reqs = [{"unmergeCells": {"range": {"sheetId": sid}}},
                    {"updateCells": {"range": {"sheetId": sid}, "fields": "userEnteredValue,userEnteredFormat"}}]
        for s in meta:
            if s["properties"]["sheetId"] == sid:
                for ch in s.get("charts", []):
                    del_reqs.append({"deleteEmbeddedObject": {"objectId": ch["chartId"]}})
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": del_reqs}).execute()
        print(f"[tab] 既存 {TAB} をクリア (id={sid})")
    else:
        resp = svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": [
            {"addSheet": {"properties": {"title": TAB, "index": 2,
             "gridProperties": {"rowCount": N_ROWS, "columnCount": N_COLS, "hideGridlines": True}}}}
        ]}).execute()
        sid = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
        print(f"[tab] {TAB} を新規作成 (id={sid})")

    # ===== レイアウト =====
    g = Grid(sid, N_ROWS, N_COLS)
    r = 0
    g.put(r, 0, "FUSION 中途採用　歩留まり分析ダッシュボード")
    g.merge(r, 0, r + 1, N_COLS)
    g.fmt(r, 0, r + 1, N_COLS, bg=TITLE_BG, fg=WHITE, bold=True, size=15, halign="LEFT")
    g.rowh(r, 40); r += 1
    f_emp = funnel_counts(a_emp)
    f_gyo = funnel_counts(a_gyo)
    g.put(r, 0, (f"最終更新: {dt.datetime.now(TZ):%Y/%m/%d %H:%M}　｜　対象: 全期間累計＋当月＋直近12週"
                 f"　｜　正社員 {len(a_emp)}名 / 業務委託 {len(a_gyo)}名（テスト/無効求人除外 {len(recs)-len(a_all)}件）"))
    g.merge(r, 0, r + 1, N_COLS)
    g.fmt(r, 0, r + 1, N_COLS, bg=SUBBAND, fg=SUBINK, size=9, halign="LEFT")
    g.rowh(r, 20); r += 2

    # ② サマリー（今週＋今月のカード・全フェーズ＋ボトルネック＋雇用区分）
    r = section(g, r, 0, N_COLS - 1, "■ サマリー（今週＝直近 木〜水 ／ 今月＝当月・全フェーズ）")
    r = render_strip(g, r, "▎今月サマリー（当月・全フェーズ）", [
        ("応募", f_month[0]), ("カジュ面談", f_month[1]), ("1次", f_month[2]), ("2次", f_month[3]),
        ("最終", f_month[4]), ("会食", f_month[5]), ("内定", f_month[6]), ("承諾", f_month[7]),
        ("内定率", pct(f_month[6], f_month[0]))])
    r = render_strip(g, r, "▎今週サマリー（直近 木〜水・全フェーズ）", [
        ("応募", f"{fw_week[0]}（{arrow(fw_week[0], fw_prev[0])}）"), ("カジュ面談", fw_week[1]),
        ("1次", fw_week[2]), ("2次", fw_week[3]), ("最終", fw_week[4]), ("会食", fw_week[5]),
        ("内定", fw_week[6]), ("承諾", fw_week[7]), ("進行中", n_active)])
    r = render_strip(g, r, "▎ボトルネック（全期間累計）", [("最弱通過段", f"{weak_label}　{weak_val}")],
                     value_bg=BAD) + 1
    # 雇用区分別（正社員 / 業務委託・フルファネル）
    r = section(g, r, 0, 11, "■ 雇用区分別（正社員 / 業務委託・全期間累計フルファネル）")
    eh = ["区分", "応募"] + STEP_LBL + ["内定", "承諾", "内定率"]
    erows = []
    for label, recs_k in [("正社員", a_emp), ("業務委託", a_gyo)]:
        cc = funnel_counts(recs_k)
        erows.append([f"{label}（{cc[0]}名）", cc[0]] + cc[1:6] + [cc[6], cc[7], pct(cc[6], cc[0])])
    cca = funnel_counts(a_all)
    erows.append([f"合計（{cca[0]}名）", cca[0]] + cca[1:6] + [cca[6], cca[7], pct(cca[6], cca[0])])
    r = table(g, r, 0, eh, erows, aligns=["LEFT"] + ["CENTER"] * 9) + 1

    # ③ 週次トレンド（左）＋ 職種別 応募 週次切替ウィジェット（右）
    tr_top = r
    rL = section(g, tr_top, 0, 7, "■ 週次トレンド（直近12週・各週の発生件数）")
    trend_hdr = rL
    th = ["週(木〜水)", "応募", "面談", "1次", "2次", "最終", "内定", "承諾"]
    tw_rows = [[wk, fl["応募"], fl["面談"], fl["1次"], fl["2次"], fl["最終"], fl["内定"], fl["承諾"]]
               for wk, fl in weeks]
    rL = table(g, rL, 0, th, tw_rows)
    rR = section(g, tr_top, 9, 14, "■ 職種別 応募（週次・切替／右セルの週を選択）")
    g.put(rR, 9, "選択週 ▶")
    g.fmt(rR, 9, rR + 1, 10, fg=INK, bold=True, size=9, halign="RIGHT")
    dd_row, dd_col = rR, 10
    g.put(dd_row, dd_col, wk_labels[-1])
    g.merge(dd_row, dd_col, dd_row + 1, 15)
    g.fmt(dd_row, dd_col, dd_row + 1, 15, bg=WARN, fg=INK, bold=True, size=10, halign="CENTER")
    g.border(dd_row, dd_col, dd_row + 1, 15, color=BORDER)
    wh = rR + 1
    g.row(wh, 9, ["職種", "応募数"])
    g.merge(wh, 10, wh + 1, 15)
    g.fmt(wh, 9, wh + 1, 15, bg=HEAD_BG, fg=WHITE, bold=True, size=9, halign="CENTER")
    widget_cells = []
    for i, (job, _) in enumerate(matrix_jobs):
        rr2 = wh + 1 + i
        g.put(rr2, 9, job)
        g.merge(rr2, 10, rr2 + 1, 15)
        g.fmt(rr2, 9, rr2 + 1, 15, bg=(ZEBRA if i % 2 else WHITE), fg=INK, size=9)
        g.fmt(rr2, 9, rr2 + 1, 10, halign="LEFT", wrap="WRAP")
        g.fmt(rr2, 10, rr2 + 1, 15, halign="CENTER", bold=True)
        widget_cells.append((rr2, 9, 10))
    g.border(wh, 9, wh + 1 + len(matrix_jobs), 15, color=BORDER, inner=True)
    r = max(rL, wh + 1 + len(matrix_jobs)) + 1

    # ④ ファネル
    r = section(g, r, 0, 4, "■ ファネル歩留まり（全期間累計）")
    funnel_hdr = r
    r = table(g, r, 0, ["ステージ", "到達数", "前段通過率", "累積通過率", "離脱数"], funnel_rows,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]) + 1

    # ⑤ 媒体別分析（正社員のみ／業務委託は別セクション）
    r = section(g, r, 0, 11, "■ 媒体別分析【正社員】（全期間累計／各ステージ＝件数（累積通過率%））")

    def _ms(cc, k):
        return f"{cc[k]}（{round(cc[k] / cc[0] * 100)}%）" if cc[0] else str(cc[k])

    def _render_media(g, r, media_list):
        mh = ["経路", "当月", "応募", "カジュ面談", "1次", "2次", "最終", "会食", "内定", "承諾", "内定率", "必要数"]
        m_rows = [[m["name"], m["month"], m["cc"][0]] + [_ms(m["cc"], k) for k in range(1, 7)]
                  + [m["cc"][7], m["offer_rate"], (m["need"] if m["offer"] else "—")]
                  for m in media_list]
        r0 = r
        r = table(g, r0, 0, mh, m_rows or [["（データなし）"] + ["—"] * (len(mh) - 1)],
                  aligns=["LEFT"] + ["CENTER"] * (len(mh) - 1))
        for i, m in enumerate(media_list):
            rr = r0 + 1 + i
            if m["offer"] >= 1 and m["app"] >= 1 and (m["offer"] / m["app"]) >= 0.05:
                g.cellbg(rr, 10, GOOD)
            elif m["app"] >= 10 and m["offer"] == 0:
                g.cellbg(rr, 10, BAD)
        return r + 1

    r = _render_media(g, r, media)
    r = section(g, r, 0, 11, "■ 媒体別分析【業務委託】（全期間累計）")
    r = _render_media(g, r, media_gyo)

    # ⑥ エージェント×職種 クロス（エージェント別グループ・合計＋職種内訳・フルファネル）
    r = section(g, r, 0, 9, "■ エージェント×職種 クロス歩留まり（累計・エージェント別グループ／フルファネル）")
    ch2 = ["エージェント", "職種", "応募"] + STEP_LBL + ["内定", "承諾"]
    r0x = r
    r = table(g, r0x, 0, ch2, cross_rows or [["（エージェント経由なし）", "", 0, 0, 0, 0, 0, 0, 0, 0]],
              aligns=["LEFT", "LEFT"] + ["CENTER"] * 8)
    for ti in total_idx:
        rr = r0x + 1 + ti
        g.fmt(rr, 0, rr + 1, len(ch2), bg=SUBBAND, bold=True)
    g.fmt(r0x + 1, 1, r, 2, wrap="WRAP")
    r += 1

    # ⑦ 職種別（正社員・フルファネル・左）＋ ⑧ 離脱（右）
    r_pair = r
    jh = ["選考ポジション", "応募"] + STEP_LBL + ["内定", "承諾", "内定率"]
    rL = section(g, r_pair, 0, 10, "■ 職種別分析【正社員】（フルファネル・累計）")
    rL = table(g, rL, 0, jh, jobs or [["（データなし）"] + [0] * 10], aligns=["LEFT"] + ["CENTER"] * 10)
    rL = section(g, rL, 0, 10, "■ 職種別分析【業務委託】（フルファネル・累計）")
    rL = table(g, rL, 0, jh, jobs_gyo or [["（データなし）"] + [0] * 10], aligns=["LEFT"] + ["CENTER"] * 10)
    rR = section(g, r_pair, 14, N_COLS - 1, "■ 離脱分析（累計）")
    drop_rows = [["応募(分析母数)", f_all[0], "—"], ["不合格", n_fail, pct(n_fail, f_all[0])],
                 ["辞退", n_decline, pct(n_decline, f_all[0])], ["進行中", n_active, pct(n_active, f_all[0])]]
    rR = table(g, rR, 14, ["区分", "件数", "比率"], drop_rows, aligns=["LEFT", "CENTER", "CENTER"]) + 1
    rR = section(g, rR, 14, N_COLS - 1, "▎辞退理由（分類・上位）")
    rsn_rows = [[rsn, n] for rsn, n in reasons.most_common(5)] or [["（データなし）", 0]]
    rR = table(g, rR, 14, ["理由", "件数"], rsn_rows, aligns=["LEFT", "CENTER"])
    r = max(rL, rR) + 1

    # ⑨ 可視化（ネイティブチャート）
    r = section(g, r, 0, N_COLS - 1, "■ 可視化")
    chart_anchor = r + 1
    r = chart_anchor + 17  # チャート(overlay)の下に余白を確保

    # ⑩ 週次×職種 応募マトリクス（上の『職種別 応募 週次切替』の参照元）
    r = section(g, r, 0, 12, "■ 週次×職種 応募マトリクス（直近12週・切替ウィジェットの参照元）")
    MH = r
    g.row(MH, 0, ["職種"] + wk_labels)
    g.fmt(MH, 0, MH + 1, 13, bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER")
    g.rowh(MH, 24)
    for i, (job, counts) in enumerate(matrix_jobs):
        rr2 = MH + 1 + i
        g.put(rr2, 0, job)
        g.row(rr2, 1, counts)
        g.fmt(rr2, 0, rr2 + 1, 13, bg=(ZEBRA if i % 2 else WHITE), fg=INK, size=8)
        g.fmt(rr2, 0, rr2 + 1, 1, halign="LEFT")
        g.fmt(rr2, 1, rr2 + 1, 13, halign="CENTER")
    g.border(MH, 0, MH + 1 + len(matrix_jobs), 13, color=BORDER, inner=True)
    r = MH + 1 + len(matrix_jobs) + 1

    # ウィジェットの応募数を数式化（選択週で自動切替）＋プルダウン
    njob = len(matrix_jobs)
    jobcol_rng = f"$A${MH + 2}:$A${MH + 1 + njob}"
    wkhdr_rng = f"$B${MH + 1}:$M${MH + 1}"
    cnt_rng = f"$B${MH + 2}:$M${MH + 1 + njob}"
    dd_ref = f"${col_letter(dd_col)}${dd_row + 1}"
    for (rr2, jc, vc) in widget_cells:
        jobcell = f"{col_letter(jc)}{rr2 + 1}"
        g.put(rr2, vc, f"=IFERROR(INDEX({cnt_rng},MATCH({jobcell},{jobcol_rng},0),"
                       f"MATCH({dd_ref},{wkhdr_rng},0)),0)")
    g.reqs.append({"setDataValidation": {"range": {"sheetId": sid, "startRowIndex": dd_row,
        "endRowIndex": dd_row + 1, "startColumnIndex": dd_col, "endColumnIndex": dd_col + 1},
        "rule": {"condition": {"type": "ONE_OF_LIST",
            "values": [{"userEnteredValue": w} for w in wk_labels]},
            "showCustomUi": True, "strict": False}}})

    # ===== 書き込み =====
    svc.spreadsheets().values().update(
        spreadsheetId=SID, range=f"'{TAB}'!A1", valueInputOption="USER_ENTERED",
        body={"values": g.vals}).execute()

    layout_reqs = [
        {"updateSheetProperties": {"properties": {"sheetId": sid,
            "gridProperties": {"hideGridlines": True}}, "fields": "gridProperties.hideGridlines"}},
        {"repeatCell": {"range": {"sheetId": sid},
            "cell": {"userEnteredFormat": {"backgroundColor": PAPER,
                     "textFormat": {"fontFamily": FONT, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid,
            "gridProperties": {"frozenRowCount": 2}}, "fields": "gridProperties.frozenRowCount"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS",
            "startIndex": 0, "endIndex": N_COLS}, "properties": {"pixelSize": 76}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS",
            "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 210}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS",
            "startIndex": 14, "endIndex": 15}, "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
    ]
    for rr, px in g.row_h.items():
        layout_reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid,
            "dimension": "ROWS", "startIndex": rr, "endIndex": rr + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": layout_reqs}).execute()

    for i in range(0, len(g.reqs), 300):
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": g.reqs[i:i + 300]}).execute()
    print(f"[fmt] 書式 {len(g.reqs)} 件適用")

    # チャート（折れ線：週次トレンド／横棒：ファネル）
    chart_reqs = [
        chart_req(sid, "週次トレンド（応募・面談・1次・内定）", "LINE", chart_anchor, 0,
                  trend_hdr, 12, 0, [1, 2, 3, 6], w=560, h=300),
        chart_req(sid, "ファネル到達数（全期間累計）", "BAR", chart_anchor, 8,
                  funnel_hdr, 8, 0, [1], w=460, h=300),
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": chart_reqs}).execute()
    print("[chart] ネイティブチャート2件を生成")

    # ===== 既存タブ不変の検証 =====
    after = svc.spreadsheets().get(
        spreadsheetId=SID, fields="sheets(properties(sheetId,title))").execute()["sheets"]
    after_map = {s["properties"]["sheetId"]: s["properties"]["title"] for s in after}
    for bsid, btitle in before_map.items():
        if bsid not in after_map:
            raise RuntimeError(f"既存タブ消失: {btitle}")
        if after_map[bsid] != btitle and bsid != sid:
            raise RuntimeError(f"既存タブ名変化: {btitle} -> {after_map[bsid]}")
    print(f"[safe] 既存タブ不変を確認（{len(before_map)}→{len(after_map)}タブ）")

    print(f"[done] gid={sid}")
    print(f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={sid}")
    print(f"[chk] 累計応募={f_all[0]} 内定={f_all[6]} 承諾={f_all[7]} 最弱={weak_label}{weak_val} 当月応募={f_month[0]}")

    # 雇用区分別分析タブ
    build_koyou_tab_(svc, a_emp, a_gyo)


def build_koyou_tab_(svc, a_emp, a_gyo):
    """正社員 / 業務委託 を完全分離した専用タブを生成する。"""
    KTAB = "★雇用区分別分析"
    N_K_ROWS, N_K_COLS = 200, 14

    existing = svc.spreadsheets().get(
        spreadsheetId=SID, fields="sheets(properties(sheetId,title),charts(chartId))").execute()["sheets"]
    ktab_info = next((s for s in existing if s["properties"]["title"] == KTAB), None)

    if ktab_info:
        ksid = ktab_info["properties"]["sheetId"]
        del_reqs = [
            {"unmergeCells": {"range": {"sheetId": ksid}}},
            {"updateCells": {"range": {"sheetId": ksid}, "fields": "userEnteredValue,userEnteredFormat"}},
        ]
        for ch in ktab_info.get("charts", []):
            del_reqs.append({"deleteEmbeddedObject": {"objectId": ch["chartId"]}})
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": del_reqs}).execute()
        print(f"[tab] {KTAB} をクリア (id={ksid})")
    else:
        resp = svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": [
            {"addSheet": {"properties": {"title": KTAB, "index": 3,
             "gridProperties": {"rowCount": N_K_ROWS, "columnCount": N_K_COLS, "hideGridlines": True}}}}
        ]}).execute()
        ksid = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
        print(f"[tab] {KTAB} を新規作成 (id={ksid})")

    g = Grid(ksid, N_K_ROWS, N_K_COLS)
    r = 0

    g.put(r, 0, "FUSION 中途採用　雇用区分別分析（正社員 / 業務委託）")
    g.merge(r, 0, r + 1, N_K_COLS)
    g.fmt(r, 0, r + 1, N_K_COLS, bg=TITLE_BG, fg=WHITE, bold=True, size=14, halign="LEFT")
    g.rowh(r, 40); r += 1
    g.put(r, 0, f"最終更新: {dt.datetime.now(TZ):%Y/%m/%d %H:%M}　｜　正社員 {len(a_emp)}名 / 業務委託 {len(a_gyo)}名（全期間累計）")
    g.merge(r, 0, r + 1, N_K_COLS)
    g.fmt(r, 0, r + 1, N_K_COLS, bg=SUBBAND, fg=SUBINK, size=9, halign="LEFT")
    g.rowh(r, 20); r += 2

    jh = ["選考ポジション", "応募"] + STEP_LBL + ["内定", "承諾", "内定率"]
    mh_k = ["経路", "応募", "カジュ面談", "1次", "2次", "最終", "内定", "承諾", "内定率"]

    def _jobs_rows(records):
        by_pos = defaultdict(list)
        for rec in records:
            by_pos[rec["pos"]].append(rec)
        rows = []
        for k, rs in sorted(by_pos.items(), key=lambda kv: -len(kv[1])):
            cc = funnel_counts(rs)
            rows.append([k] + cc + [pct(cc[6], cc[0])])
        return rows or [["（データなし）"] + [0] * 10]

    def _media_rows(records):
        by_src = defaultdict(list)
        for rec in records:
            by_src[rec["src"]].append(rec)
        rows = []
        for k, rs in sorted(by_src.items(), key=lambda kv: -len(kv[1])):
            cc = funnel_counts(rs)
            rows.append([short(k), cc[0]] + cc[1:6] + [cc[6], cc[7], pct(cc[6], cc[0])])
        return rows or [["（データなし）"] + [0] * 8]

    # ─── 正社員 ───
    r = section(g, r, 0, N_K_COLS - 1, "◆ 正社員（全期間累計）")
    r += 1

    f_emp = funnel_counts(a_emp)
    r = section(g, r, 0, 5, "■ 正社員 ファネル歩留まり")
    funnel_emp_rows = []
    for i, lbl in enumerate(["エントリー"] + STEP_LBL + ["内定", "承諾"]):
        prevp = "—" if i == 0 else pct(f_emp[i], f_emp[i - 1])
        cump = "100%" if i == 0 else pct(f_emp[i], f_emp[0])
        drop = 0 if i == 0 else max(0, f_emp[i - 1] - f_emp[i])
        funnel_emp_rows.append([lbl, f_emp[i], prevp, cump, drop])
    r = table(g, r, 0, ["ステージ", "到達数", "前段通過率", "累積通過率", "離脱数"], funnel_emp_rows,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]) + 2

    r = section(g, r, 0, N_K_COLS - 1, "■ 正社員 職種別（フルファネル）")
    r = table(g, r, 0, jh, _jobs_rows(a_emp), aligns=["LEFT"] + ["CENTER"] * 10) + 2

    r = section(g, r, 0, N_K_COLS - 1, "■ 正社員 媒体別")
    r = table(g, r, 0, mh_k, _media_rows(a_emp), aligns=["LEFT"] + ["CENTER"] * 8) + 2

    # ─── 業務委託 ───
    r = section(g, r, 0, N_K_COLS - 1, "◆ 業務委託（全期間累計）")
    r += 1

    f_gyo = funnel_counts(a_gyo)
    r = section(g, r, 0, 5, "■ 業務委託 ファネル歩留まり")
    funnel_gyo_rows = []
    for i, lbl in enumerate(["エントリー"] + STEP_LBL + ["内定", "承諾"]):
        prevp = "—" if i == 0 else pct(f_gyo[i], f_gyo[i - 1])
        cump = "100%" if i == 0 else pct(f_gyo[i], f_gyo[0])
        drop = 0 if i == 0 else max(0, f_gyo[i - 1] - f_gyo[i])
        funnel_gyo_rows.append([lbl, f_gyo[i], prevp, cump, drop])
    r = table(g, r, 0, ["ステージ", "到達数", "前段通過率", "累積通過率", "離脱数"], funnel_gyo_rows,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]) + 2

    r = section(g, r, 0, N_K_COLS - 1, "■ 業務委託 職種内訳（フルファネル）")
    r = table(g, r, 0, jh, _jobs_rows(a_gyo), aligns=["LEFT"] + ["CENTER"] * 10) + 2

    # ===== 書き込み =====
    svc.spreadsheets().values().update(
        spreadsheetId=SID, range=f"'{KTAB}'!A1", valueInputOption="USER_ENTERED",
        body={"values": g.vals}).execute()

    layout_k = [
        {"updateSheetProperties": {"properties": {"sheetId": ksid,
            "gridProperties": {"hideGridlines": True}}, "fields": "gridProperties.hideGridlines"}},
        {"repeatCell": {"range": {"sheetId": ksid},
            "cell": {"userEnteredFormat": {"backgroundColor": PAPER,
                     "textFormat": {"fontFamily": FONT, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        {"updateSheetProperties": {"properties": {"sheetId": ksid,
            "gridProperties": {"frozenRowCount": 2}}, "fields": "gridProperties.frozenRowCount"}},
        {"updateDimensionProperties": {"range": {"sheetId": ksid, "dimension": "COLUMNS",
            "startIndex": 0, "endIndex": N_K_COLS}, "properties": {"pixelSize": 80}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": ksid, "dimension": "COLUMNS",
            "startIndex": 0, "endIndex": 1}, "properties": {"pixelSize": 220}, "fields": "pixelSize"}},
    ]
    for rr, px in g.row_h.items():
        layout_k.append({"updateDimensionProperties": {"range": {"sheetId": ksid,
            "dimension": "ROWS", "startIndex": rr, "endIndex": rr + 1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": layout_k}).execute()
    for i in range(0, len(g.reqs), 300):
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": g.reqs[i:i + 300]}).execute()
    print(f"[koyou-tab] 完了 gid={ksid}")
    print(f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={ksid}")


if __name__ == "__main__":
    main()
