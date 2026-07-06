#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTZ 28卒採用 月次レポート（Google ドキュメント）を生成する。

- 本番SS(production)の生データを直接集計（数式タブ非依存）。
  集計コアは build_dotz_kpi.aggregate を流用する。
- fusion(中途RPO)の月次Doc(buildMonthlyDocEditable_)と同水準の構成:
  KPIヒーロー(当月/前月比) → 担当者コメント(編集可・ルールベース) →
  選考ファネル(対目標・ペース) → 月次トレンド → 媒体別 → 大学群別 →
  経路カテゴリ別 → 価値観TOP3。グラフは QuickChart 画像。Gemini非依存。
- 生成後リンク共有(編集可)を付与し、Doc URL を出力する。

正本: ~/Claude AI/build_dotz_monthly_doc.py
"""

import json
import logging
import urllib.parse
import urllib.request
import datetime as dt

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build as gbuild

from build_dotz_kpi import (
    SID,
    TOKEN,
    TZ,
    NODES,
    GOAL,
    aggregate,
    parse_ts,
    pct,
    elapsed_ratio,
    col_idx,
    norm_rank,
    prefix_of,
    STATUS_MAP,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ブランド配色（Tokumori: 深い赤 + 黒）
RED = "#AF322C"
RED_DK = "#7E1C18"
INK = "#292929"
GRAY = "#8A8A8A"
PALE = "#F5EAE9"
QC_PALETTE = [RED, "#404040", "#9B9B9B", "#C98B87", "#5E5E5E", "#D8C2C0"]

# ファネルで主役にする段階（母数が小さい中間を圧縮）
FUNNEL_VIEW = [
    "エントリー",
    "説明選考会参加",
    "1次面接",
    "カジュアル面談",
    "2次面接",
    "最終(役員)面接",
    "内定出し",
    "内定承諾",
]


# ───────────────────────── 認証 / サービス ─────────────────────────
def get_services():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    sheets = gbuild("sheets", "v4", credentials=creds)
    docs = gbuild("docs", "v1", credentials=creds)
    drive = gbuild("drive", "v3", credentials=creds)
    return sheets, docs, drive


# ───────────────────────── データ取得（build_dotz_kpi.main と同じ） ──────
def load_aggregate(sheets, today):
    ranges = [
        "'003_000_03採用進捗管理'!A10:CB400",
        "'エントリーマスター'!A2:Y1000",
        "'エントリー（スカウト：代表面談）'!A2:L300",
        "'エントリー（スカウト：説明会兼一次面接）'!A2:L300",
        "'エントリー（スカウト：説明会）'!A2:L300",
        "'エントリー（エージェント）'!A2:L300",
    ]
    vr = sheets.spreadsheets().values().batchGet(
        spreadsheetId=SID, ranges=ranges).execute()["valueRanges"]
    prog_all = vr[0].get("values", [])
    master_rows = vr[1].get("values", [])
    prog_head = prog_all[0] if prog_all else []
    prog_rows = prog_all[1:]

    flows = ["代表面談", "説明会兼一次", "説明会", "エージェント"]
    flow_rows = {flows[i]: vr[2 + i].get("values", []) for i in range(4)}
    flow_entry, email2flow, name2flow = {}, {}, {}
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

    agg = aggregate(prog_rows, prog_head, master_rows, today,
                    flow_entry, email2flow, name2flow, flows)

    # 求職者評価ランク別の到達分布（agg["ranks"] は企業評価。求職者評価を追加）
    ci_status = col_idx(prog_head, "ステータス")
    ci_seeker = col_idx(prog_head, "求職者評価")
    seeker_ranks = {x: [0] * len(NODES) for x in ["S", "A", "B", "C", "D"]}
    for r in prog_rows:
        status = r[ci_status] if 0 <= ci_status < len(r) else ""
        reached, _ = STATUS_MAP.get(prefix_of(status), (None, True))
        if reached is None:
            continue
        sk = norm_rank(r[ci_seeker]) if 0 <= ci_seeker < len(r) and r[ci_seeker] else ""
        if sk in seeker_ranks:
            for n in range(1, reached + 1):
                seeker_ranks[sk][n] += 1
    agg["seeker_ranks"] = seeker_ranks
    return agg


# ───────────────────────── QuickChart ─────────────────────────
def qc_url(config, width=520, height=300):
    """QuickChart short URL を生成（config が長くてもURL長制限を回避）。"""
    payload = json.dumps({
        "chart": config,
        "width": width,
        "height": height,
        "backgroundColor": "white",
        "devicePixelRatio": 2,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://quickchart.io/chart/create",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode("utf-8"))
        if body.get("success") and body.get("url"):
            return body["url"]
        logger.error("QuickChart 応答に url 無し: %s", body)
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        logger.error("QuickChart 生成失敗: %s", e)
    return None


def _no_legend(extra=None):
    base = {"legend": {"display": False}}
    if extra:
        base.update(extra)
    return base


def chart_funnel(reach):
    labels = [n for n in FUNNEL_VIEW]
    data = [reach[NODES.index(n)] for n in FUNNEL_VIEW]
    return {
        "type": "horizontalBar",
        "data": {"labels": labels,
                 "datasets": [{"data": data, "backgroundColor": RED}]},
        "options": {"legend": {"display": False},
                    "scales": {"xAxes": [{"ticks": {"beginAtZero": True}}]}},
    }


def chart_trend(month_entry):
    """月別エントリー実数（非コホート）。応募日ベースの確定値。"""
    keys = sorted(month_entry.keys())
    entry = [month_entry[k] for k in keys]
    return {
        "type": "bar",
        "data": {"labels": keys,
                 "datasets": [{"label": "月別エントリー（実数）", "data": entry,
                               "backgroundColor": RED}]},
        "options": {"legend": {"display": False}},
    }


def chart_doughnut(counts):
    items = list(counts.items())[:6]
    return {
        "type": "doughnut",
        "data": {
            "labels": [k for k, _ in items],
            "datasets": [{"data": [v for _, v in items],
                          "backgroundColor": QC_PALETTE}],
        },
        "options": {"legend": {"position": "right"}},
    }


def chart_univ(univs):
    items = list(univs.items())[:6]
    labels = [k for k, _ in items]
    return {
        "type": "horizontalBar",
        "data": {"labels": labels,
                 "datasets": [{"data": [v["e"] for _, v in items],
                               "backgroundColor": "#404040"}]},
        "options": {"legend": {"display": False}},
    }


def chart_values(top_vals):
    items = top_vals[:8]
    return {
        "type": "horizontalBar",
        "data": {"labels": [k for k, _ in items],
                 "datasets": [{"data": [v for _, v in items],
                               "backgroundColor": RED}]},
        "options": {"legend": {"display": False}},
    }


# ───────────────────────── ルールベース所感 ─────────────────────────
def rule_insight(agg, ym_label):
    lines = []
    reach = agg["reach"]
    # ボトルネック（前段比が最も低い段階）
    worst = None
    for i in range(1, len(FUNNEL_VIEW)):
        cur = reach[NODES.index(FUNNEL_VIEW[i])]
        prev = reach[NODES.index(FUNNEL_VIEW[i - 1])]
        if prev <= 0:
            continue
        rate = cur / prev
        if worst is None or rate < worst[2]:
            worst = (FUNNEL_VIEW[i - 1], FUNNEL_VIEW[i], rate)
    if worst:
        lines.append(
            f"・最大のボトルネックは「{worst[0]}→{worst[1]}」で通過率 "
            f"{worst[2] * 100:.0f}%。ここの改善が次の打ち手の優先度トップ。")
    # 着地ペース（承諾の達成率 ÷ 経過率）
    el = agg["elapsed_ratio"]
    acc_goal = GOAL.get("内定承諾") or 0
    if acc_goal and el > 0:
        rate = agg["accept"] / acc_goal
        landing = (rate / el) if el else 0
        verdict = "順調" if landing >= 0.9 else ("注意" if landing >= 0.6 else "遅れ")
        lines.append(
            f"・内定承諾は {agg['accept']}/{acc_goal}（目標比 {rate * 100:.0f}%）。"
            f"年度経過率 {el * 100:.0f}% に対し着地ペースは {landing:.2f}＝{verdict}。")
    # 媒体トップ
    if agg["media"]:
        mk, mv = list(agg["media"].items())[0]
        lines.append(
            f"・流入は「{mk}」が最多（{mv}件 / 全{agg['m_total']}件）。"
            "費用対効果の観点で配分継続の妥当性を確認。")
    # 大学群トップ
    if agg["univs"]:
        uk, uv = list(agg["univs"].items())[0]
        lines.append(f"・大学群は「{uk}」が中心（進捗 {uv['e']}名）。")
    if not lines:
        lines.append("・データ蓄積中。次月以降に通過率・着地の傾向を評価する。")
    return lines


def landing(n, el):
    """実績 ÷ 年度経過率＝線形の年度末着地予測。"""
    return round(n / el) if el and el > 0 else None


def exec_summary(agg, cur, cur_entry, prev_entry):
    """経営向けエグゼクティブサマリー（要点3-5行）。"""
    reach = agg["reach"]
    el = agg["elapsed_ratio"]
    idx = lambda name: reach[NODES.index(name)]
    g_entry = GOAL.get("エントリー") or 0
    g_acc = GOAL.get("内定承諾") or 0
    lines = []
    d = cur_entry - prev_entry
    ent_ach = f"{reach[0] / g_entry * 100:.0f}%" if g_entry else "—"
    lines.append(
        f"・当月（{cur}）エントリー {cur_entry}件（前月比 {'+' if d >= 0 else ''}{d}）。"
        f"累計 {reach[0]}件 ／ 目標 {g_entry}（達成率 {ent_ach}）。")
    lines.append(
        f"・選考進捗：説明会参加 {idx('説明選考会参加')} → 1次 {idx('1次面接')} → "
        f"2次 {idx('2次面接')} → 内定 {agg['offer']} → 承諾 {agg['accept']}"
        f"（選考中アクティブ {agg['active_total']}名 ／ 平均選考日数 "
        f"{agg['avg_lt'] if agg['avg_lt'] else '—'}日）。")
    worst = None
    for i in range(1, len(FUNNEL_VIEW)):
        cur_n, prev_n = idx(FUNNEL_VIEW[i]), idx(FUNNEL_VIEW[i - 1])
        if prev_n <= 0:
            continue
        rate = cur_n / prev_n
        if worst is None or rate < worst[2]:
            worst = (FUNNEL_VIEW[i - 1], FUNNEL_VIEW[i], rate)
    if worst:
        lines.append(
            f"・最大のボトルネックは「{worst[0]}→{worst[1]}」通過率 "
            f"{worst[2] * 100:.0f}%。次の打ち手の優先度トップ。")
    if g_acc and el > 0:
        fc = landing(agg["accept"], el)
        verdict = "目標到達ペース" if fc >= g_acc else "目標未達ペース"
        lines.append(
            f"・現ペースの年度末着地（線形・参考）：内定承諾 約{fc}名 ／ 目標 "
            f"{g_acc}名＝{verdict}。")
    return lines


# ───────────────────────── Doc 構築ヘルパ ─────────────────────────
class DocBuilder:
    """endOfSegmentLocation で末尾追記し、index計算を回避する。"""

    def __init__(self, docs, doc_id):
        self.docs = docs
        self.doc_id = doc_id

    def _batch(self, requests):
        if requests:
            self.docs.documents().batchUpdate(
                documentId=self.doc_id, body={"requests": requests}).execute()

    def _end(self):
        d = self.docs.documents().get(documentId=self.doc_id).execute()
        return d["body"]["content"][-1]["endIndex"] - 1

    def heading(self, text, level=1):
        start = self._end()
        style = {1: "HEADING_1", 2: "HEADING_2"}.get(level, "HEADING_2")
        self._batch([
            {"insertText": {"endOfSegmentLocation": {}, "text": text + "\n"}},
            {"updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": start + len(text) + 1},
                "paragraphStyle": {"namedStyleType": style},
                "fields": "namedStyleType"}},
        ])

    def para(self, text, bold=False, size=10.5, color=None):
        start = self._end()
        reqs = [{"insertText": {"endOfSegmentLocation": {}, "text": text + "\n"}}]
        if text:
            ts = {"bold": bold, "fontSize": {"magnitude": size, "unit": "PT"}}
            fields = "bold,fontSize"
            if color:
                ts["foregroundColor"] = {"color": {"rgbColor": _hex(color)}}
                fields += ",foregroundColor"
            reqs.append({"updateTextStyle": {
                "range": {"startIndex": start, "endIndex": start + len(text)},
                "textStyle": ts, "fields": fields}})
        self._batch(reqs)

    def image(self, url, width=520, height=300):
        if not url:
            self.para("（グラフ生成に失敗しました）", color=GRAY)
            return
        # Docs が fetch する前に QuickChart 側のレンダーを温める（短縮URLの遅延対策）
        for _ in range(3):
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    r.read(1)
                break
            except (urllib.error.URLError, TimeoutError) as e:
                logger.error("画像 warm-up 失敗(retry): %s", e)
        try:
            self._batch([
                {"insertInlineImage": {
                    "endOfSegmentLocation": {},
                    "uri": url,
                    "objectSize": {
                        "width": {"magnitude": width, "unit": "PT"},
                        "height": {"magnitude": height, "unit": "PT"}}}},
                {"insertText": {"endOfSegmentLocation": {}, "text": "\n"}},
            ])
        except Exception as e:  # noqa: BLE001  画像1枚の失敗で全体を止めない
            logger.error("画像挿入失敗（テキストで代替）: %s", e)
            self.para("（グラフ挿入に失敗しました）", color=GRAY)

    def table(self, header, rows):
        """ヘッダ＋データ行の表を末尾に追加する。"""
        ncols = len(header)
        nrows = len(rows) + 1
        self._batch([{"insertTable": {
            "endOfSegmentLocation": {}, "rows": nrows, "columns": ncols}}])
        # 挿入した表の各セル開始indexを取得 → 逆順で流し込む
        d = self.docs.documents().get(documentId=self.doc_id).execute()
        table_el = None
        for el in reversed(d["body"]["content"]):
            if "table" in el:
                table_el = el["table"]
                break
        cells = []  # (start_index, text, is_header)
        grid = [header] + rows
        for ri, trow in enumerate(table_el["tableRows"]):
            for ci, cell in enumerate(trow["tableCells"]):
                si = cell["content"][0]["startIndex"]
                txt = str(grid[ri][ci]) if ci < len(grid[ri]) else ""
                cells.append((si, txt, ri == 0))
        reqs = []
        for si, txt, is_head in sorted(cells, key=lambda x: -x[0]):
            if txt:
                reqs.append({"insertText": {
                    "location": {"index": si}, "text": txt}})
        self._batch(reqs)
        # ヘッダ行の書式（背景赤・白文字・太字）
        d = self.docs.documents().get(documentId=self.doc_id).execute()
        for el in reversed(d["body"]["content"]):
            if "table" in el:
                table_el = el["table"]
                break
        style_reqs = []
        head_row = table_el["tableRows"][0]
        for cell in head_row["tableCells"]:
            c0 = cell["content"][0]["startIndex"]
            c1 = cell["content"][-1]["endIndex"]
            style_reqs.append({"updateTextStyle": {
                "range": {"startIndex": c0, "endIndex": max(c0, c1 - 1)},
                "textStyle": {"bold": True,
                              "foregroundColor": {"color": {"rgbColor": _hex("#FFFFFF")}}},
                "fields": "bold,foregroundColor"}})
        # ヘッダセル背景
        ts = table_el["tableRows"][0]["tableCells"]
        tbl_start = None
        for el in reversed(d["body"]["content"]):
            if "table" in el:
                tbl_start = el["startIndex"]
                break
        style_reqs.append({"updateTableCellStyle": {
            "tableRange": {
                "tableCellLocation": {
                    "tableStartLocation": {"index": tbl_start},
                    "rowIndex": 0, "columnIndex": 0},
                "rowSpan": 1, "columnSpan": ncols},
            "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": _hex(RED)}}},
            "fields": "backgroundColor"}})
        self._batch(style_reqs)


def _hex(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255,
            "green": int(h[2:4], 16) / 255,
            "blue": int(h[4:6], 16) / 255}


# ───────────────────────── メイン ─────────────────────────
def build(period_ym=None, preview=True):
    sheets, docs, drive = get_services()
    today = dt.datetime.now(TZ).replace(tzinfo=None)
    agg = load_aggregate(sheets, today)

    # 対象月（既定=当月）。前月比のため前月キーも算出。
    cur = period_ym or today.strftime("%Y/%m")
    y, m = int(cur[:4]), int(cur[5:7])
    prev = f"{y - 1}/12" if m == 1 else f"{y}/{m:02d}"
    prev = (dt.date(y, m, 1) - dt.timedelta(days=1)).strftime("%Y/%m")
    me = agg["m_month_entry"]
    cur_entry = me.get(cur, 0)
    prev_entry = me.get(prev, 0)
    delta = cur_entry - prev_entry
    delta_s = f"（前月比 {'+' if delta >= 0 else ''}{delta}）"

    reach = agg["reach"]
    title = f"DOTZ 28卒 採用 月次レポート {cur}"

    doc = docs.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    b = DocBuilder(docs, doc_id)

    b.heading(title, 1)
    b.para(f"作成日: {today.strftime('%Y/%m/%d')}　／　対象: {cur}（応募月ベース）",
           color=GRAY, size=9)
    el = agg["elapsed_ratio"]

    # 0) エグゼクティブサマリー（経営向け要点）
    b.heading("エグゼクティブサマリー", 2)
    for line in exec_summary(agg, cur, cur_entry, prev_entry):
        b.para(line, size=10.5)

    # 0b) 対目標サマリー（全選考段階・着地予測）
    b.heading("対目標サマリー（全選考段階・着地予測）", 2)
    tgt_rows = []
    tgt_stages = ["エントリー", "説明選考会参加", "説明選考会合格", "1次面接",
                  "1次合格", "カジュアル面談", "2次面接", "最終(役員)面接",
                  "内定出し", "内定承諾"]
    for name in tgt_stages:
        n = reach[NODES.index(name)]
        prev_i = NODES.index(name) - 1
        prev_n = reach[prev_i] if prev_i >= 0 else None
        step = f"{n / prev_n * 100:.0f}%" if prev_n else "—"
        goal = GOAL.get(name)
        ach = f"{n / goal * 100:.0f}%" if goal else "—"
        fc = landing(n, el)
        tgt_rows.append([name, n, step, goal or "—", ach,
                         fc if fc is not None else "—"])
    b.table(["選考段階", "実績", "前段比", "目標", "達成率", "着地予測*"], tgt_rows)
    b.para("*着地予測＝実績 ÷ 年度経過率（線形仮定）。採用の季節性は考慮しない参考値。",
           color=GRAY, size=8.5)

    # 1) KPIヒーロー（当月の動き + 全体の現況）
    b.heading("KPI サマリー", 2)
    setsu = reach[NODES.index("説明選考会参加")]
    acc_rate = pct(agg["accept"], reach[0])
    b.table(
        ["指標", "値", "補足"],
        [
            [f"{cur} エントリー", f"{cur_entry} 件", delta_s],
            ["累計エントリー（母数）", f"{reach[0]} 件", ""],
            ["説明選考会 参加", f"{setsu} 件",
             f"参加率 {pct(setsu, reach[0]) * 100:.0f}%" if reach[0] else ""],
            ["1次面接 到達", f"{reach[NODES.index('1次面接')]} 件", ""],
            ["2次面接 到達", f"{reach[NODES.index('2次面接')]} 件", ""],
            ["内定出し", f"{agg['offer']} 件", f"目標 {GOAL.get('内定出し')}"],
            ["内定承諾", f"{agg['accept']} 件", f"目標 {GOAL.get('内定承諾')}"],
            ["承諾率", f"{acc_rate * 100:.1f}%" if acc_rate else "—", "対累計エントリー"],
            ["アクティブ（選考中）", f"{agg['active_total']} 名", ""],
            ["平均選考日数", f"{agg['avg_lt']} 日" if agg['avg_lt'] else "—", ""],
        ])

    # 2) 担当者コメント（編集可・ルールベース下書き）
    b.heading("担当者コメント（編集してください）", 2)
    for line in rule_insight(agg, cur):
        b.para(line, size=10.5)
    b.para("◇ 総評：", bold=True)
    b.para("（ここに今月の総評・次月の打ち手を記入）", color=GRAY)

    # 3) 選考ファネル（対目標・ペース）
    b.heading("選考ファネル（累計到達・対目標）", 2)
    b.image(qc_url(chart_funnel(reach), 520, 320), 380, 234)
    el = agg["elapsed_ratio"]
    frows = []
    for i, name in enumerate(FUNNEL_VIEW):
        idx = NODES.index(name)
        cur_n = reach[idx]
        prev_n = reach[NODES.index(FUNNEL_VIEW[i - 1])] if i > 0 else None
        step = f"{cur_n / prev_n * 100:.0f}%" if prev_n else "—"
        cum = f"{pct(cur_n, reach[0]) * 100:.0f}%" if reach[0] else "—"
        goal = GOAL.get(name)
        ach = f"{cur_n / goal * 100:.0f}%" if goal else "—"
        pace = "—"
        if goal and el > 0:
            p = (cur_n / goal) / el
            pace = ("順調" if p >= 0.9 else "注意" if p >= 0.6 else "遅れ") + f" {p:.2f}"
        frows.append([name, cur_n, step, cum, goal or "—", ach, pace])
    b.table(["段階", "到達", "前段比", "累計比", "目標", "達成率", "ペース"], frows)

    # 3b) 経路別の質（通過率）
    b.heading("経路別の質（通過率）", 2)
    q_rows = []
    for route, arr in list(agg["routes"].items())[:6]:
        setsu = arr[NODES.index("説明選考会参加")]
        f1 = arr[NODES.index("1次面接")]
        f2 = arr[NODES.index("2次面接")]
        acc = arr[NODES.index("内定承諾")]
        cvr = f"{f1 / setsu * 100:.0f}%" if setsu else "—"
        q_rows.append([route, setsu, f1, f2, acc, cvr])
    b.table(["経路", "説明会", "1次", "2次", "承諾", "説明会→1次"], q_rows)

    # 3c) 選考評価の分布（企業評価・求職者評価のランク別人数×到達段階）
    b.heading("選考評価の分布（評価ランク別の人数と到達段階）", 2)

    def _eval_rows(ranks):
        rows = []
        for rk in ["S", "A", "B", "C", "D"]:
            arr = ranks.get(rk, [0] * len(NODES))
            rows.append([rk,
                         arr[NODES.index("説明選考会参加")],
                         arr[NODES.index("1次面接")],
                         arr[NODES.index("2次面接")],
                         arr[NODES.index("内定出し")],
                         arr[NODES.index("内定承諾")]])
        return rows

    b.para("企業評価（当社が応募者をどう評価したか）", bold=True, size=10)
    b.table(["企業評価", "人数", "1次到達", "2次到達", "内定", "承諾"],
            _eval_rows(agg["ranks"]))
    b.para("求職者評価（応募者の当社への評価＝相性）", bold=True, size=10)
    b.table(["求職者評価", "人数", "1次到達", "2次到達", "内定", "承諾"],
            _eval_rows(agg["seeker_ranks"]))

    # 4) 月次トレンド（エントリー実数・非コホート）
    b.heading("月次トレンド（月別エントリー実数）", 2)
    b.image(qc_url(chart_trend(me), 520, 250), 380, 183)
    b.para("※応募日ベースの月別実数。説明会以降の段階別 月末累計は、本番運用で"
           "毎月スナップショットを蓄積し翌月以降に推移表示します（到達日列が無いため）。",
           color=GRAY, size=8.5)

    # 4b) 週次推移（直近6週・勢い）
    b.heading("週次推移（直近6週・月曜起算）", 2)
    weeks = agg["weeks"]
    mwe = agg["m_week_entry"]
    wk_keys = sorted(weeks.keys(),
                     key=lambda k: (int(k[:2]), int(k[3:])))[-6:]
    w_rows = []
    for k in wk_keys:
        arr = weeks.get(k, [0] * len(NODES))
        w_rows.append([k + " 週", mwe.get(k, 0),
                       arr[NODES.index("説明選考会参加")],
                       arr[NODES.index("1次面接")]])
    b.table(["週", "エントリー", "説明会", "1次"], w_rows)

    # 5) 媒体別
    b.heading("媒体別 エントリー", 2)
    b.image(qc_url(chart_doughnut(agg["media"]), 440, 300), 320, 218)
    b.table(["媒体", "エントリー"],
            [[k, v] for k, v in list(agg["media"].items())[:8]])

    # 6) 大学群別
    b.heading("大学群別", 2)
    b.image(qc_url(chart_univ(agg["univs"]), 520, 300), 380, 219)
    urows = []
    for k, v in list(agg["univs"].items())[:8]:
        urows.append([k, v["e"], v["exp"], v["first"], v["second"], v["acc"]])
    b.table(["大学群", "進捗", "説明会", "1次", "2次", "承諾"], urows)

    # 7) 経路カテゴリ別（エージェント / スカウト）
    b.heading("経路カテゴリ別 ファネル", 2)
    cr = agg["cat_reach"]
    crows = []
    for cat in ["エージェント", "スカウト"]:
        arr = cr.get(cat, [0] * len(NODES))
        crows.append([cat, arr[0], arr[NODES.index("説明選考会参加")],
                      arr[NODES.index("1次面接")], arr[NODES.index("2次面接")],
                      arr[NODES.index("内定承諾")]])
    b.table(["カテゴリ", "エントリー", "説明会", "1次", "2次", "承諾"], crows)

    # 8) 価値観TOP3
    b.heading("重視価値観 TOP（応募者の上位3位集計）", 2)
    if agg["top_vals"]:
        b.image(qc_url(chart_values(agg["top_vals"]), 520, 300), 380, 219)
    else:
        b.para("価値観データなし。", color=GRAY)

    b.para("")
    b.para("※本レポートは本番データ（応募月ベース）から自動集計。"
           "担当者コメント欄は編集可。", color=GRAY, size=9)

    # リンク共有（プレビューは閲覧のみ／本番GAS版で編集権限に切替）
    share_role = "reader" if preview else "writer"
    try:
        drive.permissions().create(
            fileId=doc_id,
            body={"type": "anyone", "role": share_role},
            fields="id").execute()
    except Exception as e:  # noqa: BLE001  共有失敗は致命的でない
        logger.error("リンク共有設定に失敗: %s", e)

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    logger.info("[done] %s", title)
    logger.info("[agg] reach=%s", dict(zip(NODES, reach)))
    logger.info("[url] %s", url)
    return url


if __name__ == "__main__":
    import sys
    ym = sys.argv[1] if len(sys.argv) > 1 else None
    build(ym)
