#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTZ 28卒採用シートに「★KPIサマリー」タブを新規追加する（自動集計ダッシュボード）。

- 既存タブは一切変更しない。書き込みは新規タブ ★KPIサマリー のみ。
- 自社採用管理シートの 22_新卒 と同じブランド品質・1枚KPIダッシュボードを
  DOTZの実データ構造に最適化して生成する。
- 再実行で冪等（タブが在れば中身をクリアして再描画、無ければ作成）。

参照元レイアウト/ロジック: ~/Claude AI/gas_saiyo_v1.js の 22_新卒 ダッシュボード。
正本: ~/Claude AI/build_dotz_kpi.py
"""

import os
import sys
import datetime as dt

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ───────────────────────── 設定 ─────────────────────────
SID = "1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA"
CONFIG_DIR = os.path.expanduser(
    "~/Claude AI/tokumori/agents/hr_support/config"
)
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")

KPI_TAB = "★KPIサマリー"
TZ = dt.timezone(dt.timedelta(hours=9))  # JST

# ブランドカラー（Tokumori方式: 深い赤 + 黒）
RED = {"red": 0.686, "green": 0.196, "blue": 0.173}        # #AF322C
RED_DK = {"red": 0.494, "green": 0.110, "blue": 0.094}     # 濃赤
INK = {"red": 0.16, "green": 0.16, "blue": 0.16}           # #292929
WHITE = {"red": 1, "green": 1, "blue": 1}
PAPER = {"red": 0.99, "green": 0.985, "blue": 0.98}        # わずかに温かい白
ZEBRA = {"red": 0.965, "green": 0.957, "blue": 0.949}
HEAD_BG = {"red": 0.18, "green": 0.17, "blue": 0.16}       # 見出し帯（黒に近い）
PALE_RED = {"red": 0.965, "green": 0.918, "blue": 0.914}   # 淡赤（KPI枠）
# ペース信号（絵文字でなく塗り色で表現）
SIG_GREEN = {"red": 0.851, "green": 0.937, "blue": 0.882}
SIG_AMBER = {"red": 0.996, "green": 0.929, "blue": 0.792}
SIG_RED = {"red": 0.984, "green": 0.847, "blue": 0.835}
GRID_BORDER = {"red": 0.85, "green": 0.84, "blue": 0.83}
BOX_BORDER = {"red": 0.35, "green": 0.33, "blue": 0.32}

FONT = "Arial"  # 日本語数値の視認性重視（Sheetsの既定で代替）

N_COLS = 18
N_ROWS = 190
LABEL_COLS = (0, 7)  # ラベル用に幅広にする列（左表/右表の見出し列）

# DOTZ ファネル段階（001_04 GOALノードに整合）
# 各ステータス接頭辞 → 到達ノード(0始まり) と アクティブ判定
# ノード定義:
NODES = [
    "エントリー",       # 0  (母数=エントリーマスター)
    "説明選考会参加",   # 1
    "説明選考会合格",   # 2
    "1次面接",          # 3
    "1次合格",          # 4
    "カジュアル面談",   # 5
    "2次面接",          # 6
    "最終(役員)面接",   # 7
    "オファー面談",     # 8
    "内定出し",         # 9
    "内定承諾",         # 10
    "入社",             # 11
]
# GOAL（001_04 総合計列）を各ノードへ対応づけ（無いノードはNone）
GOAL = {
    "エントリー": 555,
    "説明選考会参加": 411,     # GD選考
    "説明選考会合格": 129,     # GD合格
    "1次面接": 115,
    "1次合格": 43,
    "カジュアル面談": 39,
    "2次面接": None,           # GOAL上は1day/役員系で別管理→対比省略
    "最終(役員)面接": 19,      # 役員面接
    "オファー面談": None,
    "内定出し": 6,             # 内定者数
    "内定承諾": 5,             # 内定承諾数
    "入社": 5,
}

# 接頭辞 → (到達ノードindex, active)
# active=False は 不合格/辞退
STATUS_MAP = {
    "a": (1, False),   # 辞退（説明会には参加済とみなす）
    "b": (1, True),    # 説明選考会_選考中
    "c": (1, False),   # 説明選考会_不合格
    "d": (2, True),    # 説明選考会_合格
    "e": (2, True),    # 1次_調整中（1次未実施→説明会合格どまり）
    "f": (3, True),    # 1次_調整済
    "g": (3, False),   # 1次_不合格
    "k": (4, True),    # 1次_合格
    "l": (4, True),    # カジュアル_調整中（1次合格どまり）
    "m": (5, True),    # カジュアル_調整済み
    "n": (5, True),    # 2次_調整中（カジュ済どまり）
    "o": (6, True),    # 2次_調整済
    "p": (6, False),   # 2次_不合格
    "q": (6, True),    # 2次_合格
    "r": (6, True),    # 最終_調整中（2次どまり）
    "s": (7, True),    # 最終_調整済
    "t": (7, False),   # 最終_不合格
    "u": (7, True),    # 最終_合格
    "v": (7, True),    # オファー面談_調整中（最終どまり）
    "w": (8, True),    # オファー面談_調整済
    "x": (9, True),    # 内定出し
    "y": (10, True),   # 内定承諾
    "z": (10, True),   # 入社対応中（承諾済）
    "α": (11, True),   # 入社済
    "β": (1, True),    # インターンシップ参加予定
    "γ": (1, False),   # インターンシップ_不合格
}
FAIL_PREFIX = {"a", "c", "g", "p", "t", "γ"}  # 不合格・辞退


# ───────────────────────── 認証 / IO ─────────────────────────
def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def col_idx(headers, *needles):
    """ヘッダ名に needle を含む最初の列indexを返す。見つからなければ -1。"""
    for i, h in enumerate(headers):
        hs = str(h)
        if all(n in hs for n in needles):
            return i
    return -1


def prefix_of(status):
    """'d.説明選考会_合格' -> 'd' / 'α.入社済' -> 'α'。"""
    s = str(status).strip()
    if not s or "." not in s:
        return ""
    return s.split(".", 1)[0].strip()


def norm_rank(v):
    """全角S/A/B/C/D を半角化。"""
    if not v:
        return ""
    t = str(v).strip()
    z2h = {"Ｓ": "S", "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D"}
    return z2h.get(t, t.upper())


def parse_ts(v):
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(str(v).strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


# ───────────────────────── 集計（純粋関数） ─────────────────────────
def aggregate(prog_rows, prog_head, master_rows, today,
              flow_entry=None, email2flow=None, name2flow=None, flows=None):
    """進捗管理 + エントリーマスター から各種KPIを集計して dict で返す。"""
    flow_entry = flow_entry or {}
    email2flow = email2flow or {}
    name2flow = name2flow or {}
    flows = flows or ["代表面談", "説明会兼一次", "説明会", "エージェント"]
    ci_status = col_idx(prog_head, "ステータス")
    ci_ts = col_idx(prog_head, "タイムスタンプ")
    ci_seeker = col_idx(prog_head, "求職者評価")
    ci_company = col_idx(prog_head, "企業評価")
    ci_route = col_idx(prog_head, "経路")
    ci_univ = col_idx(prog_head, "大学群")
    ci_uniname = col_idx(prog_head, "大学名")
    ci_rank = col_idx(prog_head, "学生ランク")
    ci_email = col_idx(prog_head, "メールアドレス")
    ci_sei = col_idx(prog_head, "氏名（姓）")
    ci_mei = col_idx(prog_head, "氏名（名）")
    val_cols = [i for i, h in enumerate(prog_head)
                if ("価値観" in str(h) and "位" in str(h))]

    people = []
    for r in prog_rows:
        if ci_status >= len(r):
            status = ""
        else:
            status = r[ci_status]
        pf = prefix_of(status)
        if not pf and not (str(r[ci_ts]).strip() if ci_ts < len(r) else ""):
            continue  # 完全空行スキップ
        reached, active = STATUS_MAP.get(pf, (None, True))
        # ステータス未入力（最近のエントリー）は説明会前＝集計対象外（reached=None）
        get = lambda i: (r[i].strip() if i >= 0 and i < len(r) and r[i] else "")
        email = get(ci_email).lower()
        nm = (get(ci_sei) + get(ci_mei)).replace(" ", "").replace("　", "")
        flow = email2flow.get(email) or name2flow.get(nm) or "(不明)"
        people.append({
            "status": status, "prefix": pf,
            "reached": reached, "active": (active and pf not in FAIL_PREFIX),
            "ts": parse_ts(get(ci_ts)),
            "seeker": norm_rank(get(ci_seeker)),
            "company": norm_rank(get(ci_company)),
            "route": get(ci_route) or "(未設定)",
            "univ": get(ci_univ) or "(未設定)",
            "uniname": get(ci_uniname) or "(不明)",
            "rank": get(ci_rank) or "通常",
            "flow": flow,
            "values": [get(i) for i in val_cols if get(i)],
        })

    # --- エントリー母数（エントリーマスター） ---
    m_total = 0
    m_month = 0
    m_week = 0
    media_count = {}
    m_month_entry = {}   # YYYY/MM -> エントリー数
    m_week_entry = {}    # 月曜 %m/%d -> エントリー数
    m_uni_entry = {}     # 大学名 -> エントリー数
    ci_m_ts, ci_m_kikkake, ci_m_uni = 0, 1, 8  # A=ts, B=キッカケ, I=大学名（院）
    wk_start = today - dt.timedelta(days=today.weekday())
    for r in master_rows:
        ts = parse_ts(r[ci_m_ts]) if len(r) > ci_m_ts else None
        if ts is None:
            continue
        m_total += 1
        if ts.year == today.year and ts.month == today.month:
            m_month += 1
        if ts.date() >= wk_start.date():
            m_week += 1
        media = (r[ci_m_kikkake].strip() if len(r) > ci_m_kikkake and r[ci_m_kikkake] else "(不明)")
        media_count[media] = media_count.get(media, 0) + 1
        mk = ts.strftime("%Y/%m")
        m_month_entry[mk] = m_month_entry.get(mk, 0) + 1
        wkk = (ts - dt.timedelta(days=ts.weekday())).strftime("%m/%d")
        m_week_entry[wkk] = m_week_entry.get(wkk, 0) + 1
        uni = (r[ci_m_uni].strip() if len(r) > ci_m_uni and r[ci_m_uni] else "(不明)")
        m_uni_entry[uni] = m_uni_entry.get(uni, 0) + 1

    # --- ファネル到達数（ノード1..11は進捗管理ベース、0=母数） ---
    reach = [0] * len(NODES)
    reach[0] = m_total
    sel = [p for p in people if p["reached"] is not None]
    for p in sel:
        for n in range(1, p["reached"] + 1):
            reach[n] += 1

    # アクティブ（不合格/辞退除く現在地分布）
    active_people = [p for p in sel if p["active"]]
    active_total = len(active_people)
    active_dist = {}
    for p in active_people:
        node = NODES[p["reached"]] if p["reached"] else "—"
        active_dist[node] = active_dist.get(node, 0) + 1

    # 平均選考日数（最初のタイムスタンプ→today、選考中の母集団）
    lts = [(today - p["ts"]).days for p in sel if p["ts"]]
    avg_lt = round(sum(lts) / len(lts), 1) if lts else None

    # 内定/承諾
    offer = reach[NODES.index("内定出し")]
    accept = reach[NODES.index("内定承諾")]
    join = reach[NODES.index("入社")]

    # --- 経路別ファネル ---
    routes = {}
    for p in sel:
        routes.setdefault(p["route"], [0] * len(NODES))
        for n in range(1, p["reached"] + 1):
            routes[p["route"]][n] += 1
    routes = dict(sorted(routes.items(), key=lambda kv: -kv[1][1]))

    # --- 大学別（個別大学名・エントリー母数=master、ファネル=進捗結合） ---
    uni_reach = {}
    for p in sel:
        uni_reach.setdefault(p["uniname"], [0] * len(NODES))
        for n in range(1, p["reached"] + 1):
            uni_reach[p["uniname"]][n] += 1
    uni_detail = {}
    for uni, e in m_uni_entry.items():
        arr = list(uni_reach.get(uni, [0] * len(NODES)))
        arr[0] = e
        uni_detail[uni] = arr
    # 進捗にしか居ない大学名も拾う
    for uni, arr in uni_reach.items():
        if uni not in uni_detail:
            a = list(arr)
            uni_detail[uni] = a
    uni_detail = dict(sorted(uni_detail.items(), key=lambda kv: -kv[1][0])[:15])

    # --- 大学群別（到達配列・歩留計算用） ---
    univ_reach_arr = {}
    for p in sel:
        univ_reach_arr.setdefault(p["univ"], [0] * len(NODES))
        for n in range(1, p["reached"] + 1):
            univ_reach_arr[p["univ"]][n] += 1
    univ_reach_arr = dict(sorted(univ_reach_arr.items(), key=lambda kv: -kv[1][1]))

    univs = {}
    for p in sel:
        u = univs.setdefault(p["univ"],
                             {"e": 0, "exp": 0, "first": 0, "second": 0, "acc": 0})
        u["e"] += 1
        if p["reached"] >= 2:
            u["exp"] += 1
        if p["reached"] >= 3:
            u["first"] += 1
        if p["reached"] >= 6:
            u["second"] += 1
        if p["reached"] >= 10:
            u["acc"] += 1
    univs = dict(sorted(univs.items(), key=lambda kv: -kv[1]["e"]))

    # --- 企業評価ランク別 到達分布 ---
    ranks = {x: [0] * len(NODES) for x in ["S", "A", "B", "C", "D"]}
    for p in sel:
        c = p["company"]
        if c in ranks:
            for n in range(1, p["reached"] + 1):
                ranks[c][n] += 1

    # --- 価値観 × 到達相関（保有数 / 内定者保有 / 寄与率） ---
    # 価値観: 上位3位=「重視」、全体=10個いずれか保有、段階別保有(1次/2次/内定)
    val_top3, val_all, val_1st, val_2nd, val_off = {}, {}, {}, {}, {}
    for p in sel:
        for v in set(p["values"][:3]):
            val_top3[v] = val_top3.get(v, 0) + 1
        for v in set(p["values"]):
            val_all[v] = val_all.get(v, 0) + 1
            if p["reached"] >= 3:
                val_1st[v] = val_1st.get(v, 0) + 1
            if p["reached"] >= 6:
                val_2nd[v] = val_2nd.get(v, 0) + 1
            if p["reached"] >= 9:
                val_off[v] = val_off.get(v, 0) + 1
    # 表示順: 重視者数の多い順（全員全保有のため全体ではなく上位3で序列）
    top_vals = sorted(val_top3.items(), key=lambda kv: -kv[1])[:10]

    # --- 経路カテゴリ別(エージェント/スカウト) & 選考フロー別 ファネル ---
    # カテゴリ: エージェントflow=エージェント / それ以外のflow=スカウト
    cat_reach = {"エージェント": [0] * len(NODES), "スカウト": [0] * len(NODES)}
    flow_reach = {f: [0] * len(NODES) for f in flows}
    for p in sel:
        cat = "エージェント" if p["flow"] == "エージェント" else "スカウト"
        for n in range(1, p["reached"] + 1):
            cat_reach[cat][n] += 1
            if p["flow"] in flow_reach:
                flow_reach[p["flow"]][n] += 1
    # エントリー母数(node0)はflow母数から
    agent_e = flow_entry.get("エージェント", 0)
    scout_e = sum(v for k, v in flow_entry.items() if k != "エージェント")
    cat_reach["エージェント"][0] = agent_e
    cat_reach["スカウト"][0] = scout_e
    for f in flows:
        flow_reach[f][0] = flow_entry.get(f, 0)

    # --- 平均到達日数(各ステージ到達者の 応募→現在 経過日数の平均) ---
    avg_days = [None] * len(NODES)
    for n in range(1, len(NODES)):
        ds = [(today - p["ts"]).days for p in sel
              if p["ts"] and p["reached"] is not None and p["reached"] >= n]
        avg_days[n] = round(sum(ds) / len(ds), 1) if ds else None

    # --- 月次コホート（応募月別ファネル） ---
    months = {}
    for p in sel:
        if not p["ts"]:
            continue
        key = p["ts"].strftime("%Y/%m")
        months.setdefault(key, [0] * len(NODES))
        for n in range(1, p["reached"] + 1):
            months[key][n] += 1
    months = dict(sorted(months.items()))

    # --- 週次コホート（直近12週・月曜起算） ---
    weeks = {}
    for i in range(12):
        wk = wk_start - dt.timedelta(weeks=i)
        weeks[wk.strftime("%m/%d")] = [0] * len(NODES)
    for p in sel:
        if not p["ts"]:
            continue
        wk = p["ts"] - dt.timedelta(days=p["ts"].weekday())
        key = wk.strftime("%m/%d")
        if key in weeks:
            for n in range(1, p["reached"] + 1):
                weeks[key][n] += 1

    # --- ヨミ確度（企業評価×ステータスで簡易確度） ---
    yomi = {"S 確実": 0, "A 有力": 0, "B 可能性": 0, "C 様子見": 0}
    for p in active_people:
        c = p["company"]
        if p["reached"] >= 9:
            yomi["S 確実"] += 1
        elif c in ("S", "A") and p["reached"] >= 5:
            yomi["A 有力"] += 1
        elif c in ("A", "B"):
            yomi["B 可能性"] += 1
        else:
            yomi["C 様子見"] += 1

    # --- 見送り/辞退 理由内訳（理由列が無いため 不合格/辞退ステージ集計で代替） ---
    decline = {}
    label = {"a": "辞退", "c": "説明会_不合格", "g": "1次_不合格",
             "p": "2次_不合格", "t": "最終_不合格", "γ": "1day_不合格"}
    for p in sel:
        if p["prefix"] in FAIL_PREFIX:
            lb = label.get(p["prefix"], "その他")
            decline[lb] = decline.get(lb, 0) + 1
    decline = dict(sorted(decline.items(), key=lambda kv: -kv[1]))

    return {
        "reach": reach, "n_people": len(sel),
        "m_total": m_total, "m_month": m_month, "m_week": m_week,
        "media": dict(sorted(media_count.items(), key=lambda kv: -kv[1])),
        "active_total": active_total, "active_dist": active_dist,
        "avg_lt": avg_lt, "offer": offer, "accept": accept, "join": join,
        "routes": routes, "univs": univs, "univ_reach_arr": univ_reach_arr,
        "ranks": ranks,
        "val_top3": val_top3, "val_all": val_all, "val_1st": val_1st,
        "val_2nd": val_2nd, "val_off": val_off, "top_vals": top_vals,
        "months": months, "weeks": weeks, "yomi": yomi, "decline": decline,
        "cat_reach": cat_reach, "flow_reach": flow_reach,
        "flow_entry": flow_entry, "flows": flows, "avg_days": avg_days,
        "m_month_entry": m_month_entry, "m_week_entry": m_week_entry,
        "uni_detail": uni_detail,
        "elapsed_ratio": elapsed_ratio(today),
    }


def elapsed_ratio(today):
    """採用年度（〜2027/3末）の経過率。締切=2027-03-31, 起点=2026-04-01想定。"""
    start = dt.datetime(2026, 4, 1)
    end = dt.datetime(2027, 3, 31)
    total = (end - start).days
    done = max(0, (today - start).days)
    return min(1.0, done / total) if total else 0


def pace_signal(rate, elapsed):
    """達成率 ÷ 経過率 → (記号テキスト, 信号色)。"""
    if elapsed <= 0:
        return "—", None
    p = rate / elapsed
    if p >= 0.9:
        return f"順調 {p:.2f}", SIG_GREEN
    if p >= 0.6:
        return f"注意 {p:.2f}", SIG_AMBER
    return f"遅れ {p:.2f}", SIG_RED


def pct(n, d):
    return (n / d) if d else None


# ───────────────────────── レイアウト ─────────────────────────
class Grid:
    """値と書式リクエストを蓄積するレイアウトビルダー。"""

    def __init__(self, sheet_id, n_rows, n_cols):
        self.sid = sheet_id
        self.vals = [["" for _ in range(n_cols)] for _ in range(n_rows)]
        self.reqs = []  # 追加の formatting requests

    def put(self, r, c, v):
        self.vals[r][c] = "" if v is None else v

    def row(self, r, c, items):
        for i, v in enumerate(items):
            self.put(r, c + i, v)

    # --- 書式ヘルパ（GridRange生成） ---
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

    def border(self, r0, c0, r1, c1, style="SOLID", color=None, outer=True, inner=False):
        color = color or BOX_BORDER
        b = {"style": style, "color": color}
        req = {"updateBorders": {"range": self._rng(r0, c0, r1, c1)}}
        if outer:
            req["updateBorders"].update({"top": b, "bottom": b, "left": b, "right": b})
        if inner:
            ib = {"style": "SOLID", "color": GRID_BORDER}
            req["updateBorders"].update({"innerHorizontal": ib, "innerVertical": ib})
        self.reqs.append(req)

    def cell_bg(self, r, c, bg):
        self.reqs.append({"repeatCell": {
            "range": self._rng(r, c, r + 1, c + 1),
            "cell": {"userEnteredFormat": {"backgroundColor": bg}},
            "fields": "userEnteredFormat.backgroundColor",
        }})


def num(n):
    return n if isinstance(n, (int, float)) else (n or 0)


def pctstr(v):
    return "—" if v is None else f"{v*100:.0f}%"


def build_layout(sid, A, today):
    """14列のコンパクトレイアウト。A選考ファネルとB目標進捗は1表に統合。"""
    g = Grid(sid, N_ROWS, N_COLS)
    NS = NODES[1:]  # 説明会以降
    RC = 7          # 右表の開始列

    # 共通ヘルパ ----------------------------------------------------
    def sec(rr, title, c0=0, c1=None):
        g.put(rr, c0, title)
        g.fmt(rr, c0, rr + 1, (c1 or N_COLS), fg=RED_DK, bold=True, size=10)

    def table(rr, c0, header, rows, sig_col=None, sig_map=None):
        """ヘッダ+行を描画。sig_col列はsig_map[行index]の色で塗る。戻り=次の行。"""
        ncol = len(header)
        g.row(rr, c0, header)
        g.fmt(rr, c0, rr + 1, c0 + ncol, bg=HEAD_BG, fg=WHITE, bold=True,
              size=8, halign="CENTER", wrap="WRAP")
        for ri, row_vals in enumerate(rows):
            rrr = rr + 1 + ri
            g.row(rrr, c0, row_vals)
            bg = ZEBRA if ri % 2 else PAPER
            for ci in range(ncol):
                cell_bg = bg
                if sig_col is not None and ci == sig_col and sig_map:
                    cell_bg = sig_map.get(ri) or bg
                al = "LEFT" if ci == 0 else "CENTER"
                g.fmt(rrr, c0 + ci, rrr + 1, c0 + ci + 1, bg=cell_bg, halign=al,
                      size=8, bold=(ci == 0 or ci == 1))
        g.border(rr, c0, rr + 1 + len(rows), c0 + ncol, inner=True)
        return rr + 1 + len(rows)

    # ===== タイトル =====
    g.put(0, 0, "■ DOTZ 28卒 採用KPIサマリー")
    g.put(0, 9, f"更新 {today.strftime('%Y-%m-%d %H:%M')}")
    g.merge(0, 0, 1, 9)
    g.merge(0, 9, 1, N_COLS)
    g.fmt(0, 0, 1, 9, bg=HEAD_BG, fg=WHITE, bold=True, size=13, halign="LEFT")
    g.fmt(0, 9, 1, N_COLS, bg=HEAD_BG, fg={"red": 0.8, "green": 0.78, "blue": 0.76},
          size=9, halign="RIGHT")

    # ===== KPI（状況サマリー）9指標ストリップ ＋ 内定/承諾ハイライト箱 =====
    r = 2
    base = A["reach"][0]
    kpi = [
        ("総エントリー", f"{base}"),
        ("今月応募", f"{A['m_month']}"),
        ("今週応募", f"{A['m_week']}"),
        ("説明会参加", f"{A['reach'][1]}"),
        ("参加率", pctstr(pct(A['reach'][1], base))),
        ("アクティブ", f"{A['active_total']}"),
        ("内定承諾", f"{A['accept']}"),
        ("承諾率", pctstr(pct(A['accept'], A['offer']))),
        ("平均LT日", "—" if A['avg_lt'] is None else f"{A['avg_lt']}"),
    ]
    for i, (lab, val) in enumerate(kpi):  # cols 0..8
        g.put(r, i, lab)
        g.put(r + 1, i, val)
    g.fmt(r, 0, r + 1, 9, bg=HEAD_BG, fg=WHITE, bold=True, size=8, halign="CENTER",
          wrap="WRAP")
    g.fmt(r + 1, 0, r + 3, 9, bg=PALE_RED, fg=RED_DK, bold=True, size=13,
          halign="CENTER")
    g.merge(r + 1, 0, r + 3, 1)
    for i in range(1, 9):
        g.merge(r + 1, i, r + 3, i + 1)
    g.border(r, 0, r + 3, 9, color=RED, inner=True)
    # ハイライト箱: 内定 / 承諾（目標対比）
    for j, (lab, cur, goal) in enumerate([
            ("内定", A['offer'], GOAL['内定出し']),
            ("承諾", A['accept'], GOAL['内定承諾'])]):
        c0 = 9 + j * 3
        g.merge(r, c0, r + 1, c0 + 3)
        g.merge(r + 1, c0, r + 3, c0 + 3)
        g.put(r, c0, f"{lab}（目標{goal}）")
        g.put(r + 1, c0, f"{cur} / {goal}")
        g.fmt(r, c0, r + 1, c0 + 3, bg=RED, fg=WHITE, bold=True, size=8, halign="CENTER")
        g.fmt(r + 1, c0, r + 3, c0 + 3, bg=PALE_RED, fg=RED_DK, bold=True,
              size=17, halign="CENTER")
        g.border(r, c0, r + 3, c0 + 3, color=RED)

    # ===== 統合: 選考ファネル × 目標進捗（1表） =====
    r = 6
    sec(r, "▎選考ファネル × 目標進捗（到達/通過率/目標/達成率/ペース/着地）")
    r += 1
    er = A["elapsed_ratio"]
    full = ["エントリー"] + NS
    hdr = ["ステージ", "到達", "前段%", "累積%", "目標", "達成%", "ペース", "着地"]
    rows, sig_map = [], {}
    for i, name in enumerate(full):
        cnt = A["reach"][i]
        prev = A["reach"][i - 1] if i > 0 else None
        goal = GOAL.get(name)
        if goal:
            rate = pct(cnt, goal) or 0
            sig_txt, sig_bg = pace_signal(rate, er)
            landing = round(cnt / er) if er > 0 else cnt
            sig_map[i] = sig_bg
            gcells = [goal, pctstr(rate), sig_txt, landing]
        else:
            gcells = ["—", "—", "—", "—"]
        rows.append([name, cnt,
                     pctstr(pct(cnt, prev)) if prev else "—",
                     pctstr(pct(cnt, A["reach"][0])) if i > 0 else "100%"] + gcells)
    r = table(r, 0, hdr, rows, sig_col=6, sig_map=sig_map)
    g.put(r, 0, f"※経過率{er*100:.0f}%（〜27/3末）・ペース=達成率÷経過率・着地=実績÷経過率")
    g.fmt(r, 0, r + 1, N_COLS, fg=INK, italic=True, size=8)
    r += 2

    # ===== 詳細分析 =====
    g.put(r, 0, "■ 詳細分析")
    g.fmt(r, 0, r + 1, N_COLS, bg=HEAD_BG, fg=WHITE, bold=True, size=10, halign="LEFT")
    r += 2

    # 主要8段階: 説明/合格/1次/ｶｼﾞｭ/2次/最終/内定/承諾
    # 全12段階（node0=エントリー除く 1..11）を表示。横幅のため歩留まり率列は省略
    KEY = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    KEY_H = ["説明", "合格", "1次", "1次合", "ｶｼﾞｭ", "2次", "最終", "ｵﾌｧ", "内定", "承諾", "入社"]
    RYUU_M = []
    RYUU_P = []

    def ryuu(counts):
        return [pctstr(pct(counts[i], counts[i - 1])) for i in range(1, len(counts))]

    def two_up(left, right):
        (lt, lfn), (rt, rfn) = left, right
        sec(r, lt, 0, RC - 1)
        sec(r, rt, RC, N_COLS)
        return max(lfn(r + 1), rfn(r + 1))

    # 母数つき全幅ファネル表（数値→歩留を右側に）。items=[(label, reach_arr_or_None, entry)]
    def funnel_master(rr, label_h, items):
        rows = []
        for label, arr, entry in items:
            counts = [entry] + [(arr[k] if arr else 0) for k in KEY]
            rows.append([label] + counts)
        if not rows:
            rows = [["(なし)"] + [""] * (len(KEY) + 1)]
        return table(rr, 0, [label_h, "母数"] + KEY_H, rows)

    # 進捗ベース全幅ファネル表（説明会参加=母数相当）
    def funnel_prog(rr, c0, label_h, items):
        rows = []
        for label, arr in items:
            counts = [arr[k] for k in KEY]
            rows.append([label] + counts)
        if not rows:
            rows = [["(なし)"] + [""] * len(KEY)]
        return table(rr, c0, [label_h] + KEY_H, rows)

    # ===== 小表（2列ペア） =====
    # ⑤ 媒体別 ｜ ⑨ ヨミ確度
    def f_media(rr):
        tot = A["m_total"] or 1
        rows = [[m, c, pctstr(c / tot)] for m, c in A["media"].items()]
        return table(rr, 0, ["媒体", "応募", "構成比"], rows)

    def f_yomi(rr):
        rows = [[k, v] for k, v in A["yomi"].items()]
        return table(rr, RC, ["ヨミ確度", "人数"], rows)
    r = two_up(("⑤ 媒体別エントリー(母数=ｴﾝﾄﾘｰﾏｽﾀｰ)", f_media),
               ("⑨ ヨミ確度別(企業評価×ステータス)", f_yomi)) + 1

    # ⑩ 見送り/辞退 ｜ ⑪ アクティブ現在地
    def f_decline(rr):
        tot_d = sum(A["decline"].values()) or 1
        rows = [[k, v, pctstr(v / tot_d)] for k, v in A["decline"].items()]
        if not rows:
            rows = [["(なし)", "", ""]]
        return table(rr, 0, ["見送り/辞退", "件数", "比"], rows)

    def f_active(rr):
        rows = [[k, v] for k, v in sorted(
            A["active_dist"].items(),
            key=lambda kv: NODES.index(kv[0]) if kv[0] in NODES else 99)]
        if not rows:
            rows = [["(なし)", ""]]
        return table(rr, RC, ["現フェーズ", "ｱｸﾃｨﾌﾞ数"], rows)
    r = two_up(("⑩ 見送り・辞退 内訳", f_decline),
               ("⑪ アクティブ現在地分布", f_active)) + 1

    # ⑧ 価値観 × 到達段階（全体/重視/1次/2次/内定/寄与率）
    sec(r, "⑧ 価値観 × 到達段階（全10順位・段階別保有＋寄与率）")
    rows = []
    for v, t3 in A["top_vals"]:
        allc = A["val_all"].get(v, 0)
        off = A["val_off"].get(v, 0)
        rows.append([v, allc, t3, A["val_1st"].get(v, 0),
                     A["val_2nd"].get(v, 0), off, pctstr(pct(off, allc))])
    if not rows:
        rows = [["(なし)"] + [""] * 6]
    r = table(r + 1, 0, ["価値観", "全体保有", "重視(上位3)", "1次到達",
                         "2次到達", "内定者", "寄与率"], rows) + 1

    # ===== 全幅ファネル表（数値＋歩留・右側） =====
    # ④ 経路別（進捗の経路名）
    sec(r, "④ 経路別 ファネル＆歩留（進捗管理の経路／母数=説明会参加）")
    r = funnel_prog(r + 1, 0, "経路",
                    [(rt, rv) for rt, rv in A["routes"].items()]) + 1

    # ④b 経路カテゴリ別（エージェント/スカウト）＋平均到達日（分析サマリー準拠）
    sec(r, "④b 経路カテゴリ別 選考ファネル（総/エージェント/スカウト・平均到達日）")
    cat = A["cat_reach"]
    ag_e = cat["エージェント"][0] or 1
    sc_e = cat["スカウト"][0] or 1
    tot_e = (cat["エージェント"][0] + cat["スカウト"][0]) or 1
    rows = []
    for i, name in enumerate(full):
        tot = cat["エージェント"][i] + cat["スカウト"][i]
        ad = A["avg_days"][i] if i > 0 else 0
        rows.append([name, tot, pctstr(pct(tot, tot_e)),
                     "—" if ad is None else ad,
                     cat["エージェント"][i], pctstr(pct(cat["エージェント"][i], ag_e)),
                     cat["スカウト"][i], pctstr(pct(cat["スカウト"][i], sc_e))])
    r = table(r + 1, 0, ["ステージ", "総数", "総歩留", "平均到達日",
                         "Ag数", "Ag歩留", "ｽｶｳﾄ数", "ｽｶｳﾄ歩留"], rows) + 1

    # ④c 選考フロー別（エントリー元フォーム）＋歩留
    sec(r, "④c 選考フロー別 ファネル＆歩留（エントリー元フォーム別／母数=各フォーム）")
    r = funnel_master(r + 1, "選考フロー",
                      [(f, A["flow_reach"][f], A["flow_entry"].get(f, 0))
                       for f in A["flows"]]) + 1

    # ⑥ 大学群別 ＋歩留（進捗ベース）
    sec(r, "⑥ 大学群別 ファネル＆歩留（進捗管理／母数=説明会参加）")
    r = funnel_prog(r + 1, 0, "大学群",
                    [(u, uv) for u, uv in A["univ_reach_arr"].items()]) + 1

    # ⑦ 企業評価ランク別 ＋歩留（進捗ベース）
    sec(r, "⑦ 企業評価ランク別 ファネル＆歩留（進捗管理／母数=説明会参加）")
    r = funnel_prog(r + 1, 0, "評価",
                    [(rk, A["ranks"][rk]) for rk in ["S", "A", "B", "C", "D"]]) + 1

    # ② 月次KPI推移（母数=ｴﾝﾄﾘｰﾏｽﾀｰ・全段階＋歩留）
    sec(r, "② 月次KPI推移（母数=ｴﾝﾄﾘｰﾏｽﾀｰ／説明会以降=進捗管理・応募月別）")
    months_all = sorted(set(A["months"]) | set(A["m_month_entry"]))
    items = [(mk, A["months"].get(mk), A["m_month_entry"].get(mk, 0))
             for mk in months_all]
    r = funnel_master(r + 1, "応募月", items) + 1

    # ③ 週次KPI推移（直近12週・母数=ｴﾝﾄﾘｰﾏｽﾀｰ）
    sec(r, "③ 週次KPI推移（直近12週・月曜起算／母数=ｴﾝﾄﾘｰﾏｽﾀｰ）")
    items = [(wk, A["weeks"][wk], A["m_week_entry"].get(wk, 0))
             for wk in A["weeks"]]
    r = funnel_master(r + 1, "週(月)", items) + 1

    # ⑫ 大学別（個別大学名・エントリー降順／母数=ｴﾝﾄﾘｰﾏｽﾀｰ）
    sec(r, "⑫ 大学別 ファネル＆歩留（個別大学名・エントリー降順／母数=ｴﾝﾄﾘｰﾏｽﾀｰ）")
    items = [(uni, arr, arr[0]) for uni, arr in A["uni_detail"].items()]
    r = funnel_master(r + 1, "大学名", items) + 1

    return g, r


# ───────────────────────── 安全ゲート ─────────────────────────
def snapshot_tabs(svc):
    meta = svc.spreadsheets().get(
        spreadsheetId=SID,
        fields="sheets(properties(sheetId,title,index))").execute()
    return [(s["properties"]["sheetId"], s["properties"]["title"],
             s["properties"]["index"]) for s in meta["sheets"]]


def assert_existing_unchanged(before, after, new_title):
    """新規1タブ追加・既存のsheetId/title不変を検証。差分あれば例外。"""
    before_map = {sid: t for sid, t, _ in before}
    after_map = {sid: t for sid, t, _ in after}
    # 既存IDは全て残り、titleも不変
    for sid, title in before_map.items():
        if sid not in after_map:
            raise RuntimeError(f"既存タブが消失: {title} ({sid})")
        if after_map[sid] != title:
            raise RuntimeError(f"既存タブ名が変化: {title} -> {after_map[sid]}")
    new_ids = set(after_map) - set(before_map)
    if len(new_ids) != 1:
        raise RuntimeError(f"追加タブ数が1でない: {len(new_ids)}")
    nid = new_ids.pop()
    if after_map[nid] != new_title:
        raise RuntimeError(f"新規タブ名不一致: {after_map[nid]}")
    return nid


# ───────────────────────── メイン ─────────────────────────
def main():
    svc = get_service()
    today = dt.datetime.now(TZ).replace(tzinfo=None)

    # --- 安全スナップショット（前） ---
    before = snapshot_tabs(svc)
    print(f"[snapshot] 既存タブ数: {len(before)}")
    existing = {t: sid for sid, t, _ in before}

    # --- READ ソース ---
    ranges = [
        "'003_000_03採用進捗管理'!A10:CB400",
        "'エントリーマスター'!A2:Y1000",
        "'エントリー（スカウト：代表面談）'!A2:L300",
        "'エントリー（スカウト：説明会兼一次面接）'!A2:L300",
        "'エントリー（スカウト：説明会）'!A2:L300",
        "'エントリー（エージェント）'!A2:L300",
    ]
    vr = svc.spreadsheets().values().batchGet(
        spreadsheetId=SID, ranges=ranges).execute()["valueRanges"]
    prog_all = vr[0].get("values", [])
    master_rows = vr[1].get("values", [])
    prog_head = prog_all[0] if prog_all else []
    prog_rows = prog_all[1:]

    # 選考フロー（エントリー元4タブ）→ email/氏名 で進捗管理に結合
    FLOWS = ["代表面談", "説明会兼一次", "説明会", "エージェント"]
    flow_rows = {FLOWS[i]: vr[2 + i].get("values", []) for i in range(4)}
    flow_entry = {}
    email2flow, name2flow = {}, {}
    for flow, rws in flow_rows.items():
        cnt = 0
        for rw in rws:
            ts = rw[0].strip() if rw and rw[0] else ""
            if not ts:
                continue
            cnt += 1
            email = (rw[10].strip().lower() if len(rw) > 10 and rw[10] else "")
            name = ((rw[3] + rw[4]).replace(" ", "").replace("　", "")
                    if len(rw) > 4 and rw[3] else "")
            if email:
                email2flow.setdefault(email, flow)
            if name:
                name2flow.setdefault(name, flow)
        flow_entry[flow] = cnt
    print(f"[read] 進捗管理 {len(prog_rows)}行 / マスター {len(master_rows)}行 / "
          f"フロー母数 {flow_entry}")

    A = aggregate(prog_rows, prog_head, master_rows, today,
                  flow_entry, email2flow, name2flow, FLOWS)
    print(f"[agg] ファネル到達: {dict(zip(NODES, A['reach']))}")
    print(f"[agg] アクティブ {A['active_total']} / 内定 {A['offer']} / 承諾 {A['accept']}")

    # --- タブ準備（無ければ作成、在ればクリア） ---
    if KPI_TAB in existing:
        sid = existing[KPI_TAB]
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": [
            {"updateCells": {
                "range": {"sheetId": sid},
                "fields": "userEnteredValue,userEnteredFormat"}},
            {"unmergeCells": {"range": {"sheetId": sid}}},
        ]}).execute()
        print(f"[tab] 既存 {KPI_TAB} をクリア (id={sid})")
        is_new = False
    else:
        resp = svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": [
            {"addSheet": {"properties": {
                "title": KPI_TAB, "index": 0,
                "gridProperties": {"rowCount": N_ROWS, "columnCount": N_COLS,
                                   "hideGridlines": True}}}}
        ]}).execute()
        sid = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
        print(f"[tab] {KPI_TAB} を新規作成 (id={sid})")
        is_new = True

    # --- レイアウト生成 ---
    g, used_rows = build_layout(sid, A, today)

    # --- 値の書き込み ---
    svc.spreadsheets().values().update(
        spreadsheetId=SID, range=f"'{KPI_TAB}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": g.vals}).execute()

    # --- 列幅 + gridlines + 書式 ---
    layout_reqs = [
        {"updateSheetProperties": {
            "properties": {"sheetId": sid,
                           "gridProperties": {"hideGridlines": True}},
            "fields": "gridProperties.hideGridlines"}},
        # 全体の既定書式（白背景・行高さ）
        {"repeatCell": {
            "range": {"sheetId": sid},
            "cell": {"userEnteredFormat": {
                "backgroundColor": PAPER,
                "textFormat": {"fontFamily": FONT, "fontSize": 9}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
    ]
    # 列幅（コンパクト）: データ列=46px、ラベル列(0,7)=100px
    layout_reqs.append({"updateDimensionProperties": {
        "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0,
                  "endIndex": N_COLS},
        "properties": {"pixelSize": 46}, "fields": "pixelSize"}})
    for c in LABEL_COLS:
        layout_reqs.append({"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": c, "endIndex": c + 1},
            "properties": {"pixelSize": 100}, "fields": "pixelSize"}})

    svc.spreadsheets().batchUpdate(
        spreadsheetId=SID, body={"requests": layout_reqs}).execute()
    # build_layout が貯めた書式（重い場合は分割）
    reqs = g.reqs
    for i in range(0, len(reqs), 300):
        svc.spreadsheets().batchUpdate(
            spreadsheetId=SID, body={"requests": reqs[i:i + 300]}).execute()
    print(f"[fmt] 書式リクエスト {len(reqs)} 件適用")

    # --- 安全スナップショット（後） + 検証 ---
    after = snapshot_tabs(svc)
    nid = assert_existing_unchanged(before, after, KPI_TAB) if is_new else sid
    print(f"[verify] OK 既存タブ不変・新規タブ id={nid}")
    print(f"[done] gid={sid}")
    print(f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={sid}")


if __name__ == "__main__":
    main()
