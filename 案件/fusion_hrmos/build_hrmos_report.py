#!/usr/bin/env python3
"""FUSION 中途「レポート出力」タブ再構成（左=月次・詳細／右=週次・ワイド）。

- 月次：過去GAS設計(_reportMonthlySection_)を踏襲し情報量を最大化
  （当月サマリ＋前月比／ファネル歩留まり／職種別実績／経路別CVR・必要エントリー／所感）。
- 週次：列幅を広く使い、判定/フルファネル(今週・前週・前週比)/職種別内訳/ファネル(新規・進行中)/
  媒体・エージェント別ランキング/所感＋ネイティブチャート（職種別 横棒・媒体割合 円）。
- 配色・helperは build_hrmos_funnel_v2 と共通。既存タブ非破壊・冪等。
⚠ レポート出力はGAS自動生成タブ。clasp認証切れのため、GASの旧トリガーはApps Script側で
  停止が必要（停止しないと月曜に旧フォーマットへ戻る）。
正本: ~/Claude AI/build_hrmos_report.py
"""
import datetime as dt
from collections import Counter, defaultdict

from build_hrmos_funnel_v2 import (
    SID, TZ, get_service, load_records, funnel_counts, pct, short, inw, FLOW,
    Grid, section, table, chart_req, arrow,
    TITLE_BG, HEAD_BG, SUBBAND, INK, SUBINK, WHITE, ZEBRA, BORDER, GOOD, WARN, BAD, PAPER, FONT,
)

REPORT_TAB = "レポート出力"
NC = 26               # ワイドレイアウト
N_ROWS = 140
TODAY = dt.datetime.now(TZ).date()
MCOLS = (0, 11)       # 月次ブロック列範囲
WCOLS = (13, 25)      # 週次ブロック列範囲


def pie_req(sid, title, ar, ac, hdr, ndata, dom_col, val_col, w=460, h=300):
    def rng(col):
        return {"sheetId": sid, "startRowIndex": hdr + 1, "endRowIndex": hdr + 1 + ndata,
                "startColumnIndex": col, "endColumnIndex": col + 1}
    return {"addChart": {"chart": {"spec": {"title": title, "pieChart": {
        "legendPosition": "RIGHT_LEGEND",
        "domain": {"sourceRange": {"sources": [rng(dom_col)]}},
        "series": {"sourceRange": {"sources": [rng(val_col)]}}}},
        "position": {"overlayPosition": {"anchorCell": {"sheetId": sid, "rowIndex": ar, "columnIndex": ac},
                     "widthPixels": w, "heightPixels": h}}}}}


def note(g, r, c0, c1, text, nrows=3):
    g.put(r, c0, text)
    g.merge(r, c0, r + nrows, c1 + 1)
    g.fmt(r, c0, r + nrows, c1 + 1, fg=INK, size=9, wrap="WRAP", valign="TOP")
    g.border(r, c0, r + nrows, c1 + 1, color=BORDER)
    return r + nrows


def main():
    svc = get_service()
    recs = load_records(svc)
    analysis = [r for r in recs if not r["excluded"]]

    last_wed = TODAY - dt.timedelta(days=(TODAY.weekday() - 2) % 7)
    this_w = (last_wed - dt.timedelta(days=6), last_wed)
    prev_w = (last_wed - dt.timedelta(days=13), last_wed - dt.timedelta(days=7))
    cur_month = (dt.date(TODAY.year, TODAY.month, 1), TODAY)
    pm_last = cur_month[0] - dt.timedelta(days=1)
    prev_month = (dt.date(pm_last.year, pm_last.month, 1), pm_last)

    def cohort(a, b):
        return [r for r in analysis if inw(r["app"], a, b)]

    def flow_counts(a, b):
        c = [0] * 8
        c[0] = sum(1 for r in analysis if inw(r["app"], a, b))
        for i in range(5):
            c[i + 1] = sum(1 for r in analysis if inw(r["steps"][i], a, b))
        c[6] = sum(1 for r in analysis if inw(r["offer"], a, b))
        c[7] = sum(1 for r in analysis if inw(r["accept"], a, b))
        return c

    def _stage(r):
        if r["offer"]:
            return "内定"
        for i in range(4, -1, -1):
            if r["steps"][i]:
                return FLOW[i + 1]
        return "エントリー"
    active_by = Counter(_stage(r) for r in analysis if not (r["accept"] or r["join"] or r["decline"] or r["fail"]))
    n_active = sum(active_by.values())

    # ===== 月次データ（当月コホート＋前月比） =====
    a_month, a_pmonth = cohort(*cur_month), cohort(*prev_month)
    fm, fpm = funnel_counts(a_month), funnel_counts(a_pmonth)
    f_all = funnel_counts(analysis)
    by_pos_m = defaultdict(list)
    for r in a_month:
        by_pos_m[r["pos"]].append(r)
    jobs_m = sorted(((k, funnel_counts(v)) for k, v in by_pos_m.items()), key=lambda kv: -kv[1][0])
    by_src_all = defaultdict(list)
    for r in analysis:
        by_src_all[r["src"]].append(r)
    routes = sorted(((short(k), funnel_counts(v)) for k, v in by_src_all.items()), key=lambda kv: -kv[1][0])

    # ===== 週次データ =====
    sub = cohort(*this_w)
    fw_week, fw_prev = flow_counts(*this_w), flow_counts(*prev_w)
    app_tw, app_pw = fw_week[0], fw_prev[0]
    offer_w = fw_week[6]

    def status(r):
        if r["fail"]:
            return "不合格"
        if r["steps"][0]:
            return "面談調整〜済"
        return "書類選考中"
    posg = defaultdict(Counter)
    for r in sub:
        posg[r["pos"]][status(r)] += 1
    jobs_w = sorted(posg.items(), key=lambda kv: -sum(kv[1].values()))
    srcg = Counter(short(r["src"]) for r in sub)
    media_w = srcg.most_common()
    top_src = media_w[0] if media_w else ("—", 0)
    top_pos = "・".join(k for k, _ in jobs_w[:2]) if jobs_w else "—"

    ratio = (app_tw / app_pw) if app_pw else (2 if app_tw else 1)
    if app_tw >= 5 and ratio >= 1.1:
        judge, jbg = "順調", GOOD
    elif app_tw == 0 or ratio < 0.7:
        judge, jbg = "要警戒", BAD
    else:
        judge, jbg = "要注意", WARN
    judge_line = (f"判定：{judge}　｜　今週応募 {app_tw}件（{arrow(app_tw, app_pw)}）　｜　"
                  f"主経路 {top_src[0]} {top_src[1]}件　｜　中心職種 {top_pos}")
    insight_w = (f"先週（{app_pw}件）→今週{app_tw}件（{arrow(app_tw, app_pw)}）。"
                 f"{top_src[0]}経由が{top_src[1]}件で母集団を牽引。職種は{top_pos}が中心。"
                 "1次以降の通過・歩留まりは引き続き課題のため、選考基準の明確化と採用広報資料の拡充が次の打ち手。"
                 "（AI下書き・本実装はGeminiで前週内容を踏まえ自動生成）")
    insight_m = (f"当月応募{fm[0]}件（前月{fpm[0]}件）・内定{fm[6]}件（内定率{pct(fm[6], fm[0])}）。"
                 f"主要経路は{routes[0][0] if routes else '—'}。全期間の最大ボトルネックはカジュアル面談→1次。"
                 "母集団は回復基調。歩留まり改善（特に面談→選考本番）と高効率経路への配分が重点。（AI下書き）")

    # ===== タブ取得・クリア（チャート含む） =====
    meta = svc.spreadsheets().get(spreadsheetId=SID,
            fields="sheets(properties(sheetId,title),charts(chartId))").execute()["sheets"]
    before = {s["properties"]["sheetId"]: s["properties"]["title"] for s in meta}
    sid = next((s["properties"]["sheetId"] for s in meta if s["properties"]["title"] == REPORT_TAB), None)
    if sid is None:
        raise RuntimeError("レポート出力 タブが見つかりません")
    del_reqs = [{"unmergeCells": {"range": {"sheetId": sid}}},
                {"updateCells": {"range": {"sheetId": sid}, "fields": "userEnteredValue,userEnteredFormat"}}]
    for s in meta:
        if s["properties"]["sheetId"] == sid:
            for ch in s.get("charts", []):
                del_reqs.append({"deleteEmbeddedObject": {"objectId": ch["chartId"]}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": del_reqs}).execute()
    print(f"[tab] {REPORT_TAB} をクリア (id={sid})")

    # ===== レイアウト =====
    g = Grid(sid, N_ROWS, NC)
    g.put(0, 0, "FUSION 中途採用　レポート（月次・週次）")
    g.merge(0, 0, 1, NC)
    g.fmt(0, 0, 1, NC, bg=TITLE_BG, fg=WHITE, bold=True, size=15, halign="LEFT")
    g.rowh(0, 40)
    g.put(1, 0, f"最終更新: {dt.datetime.now(TZ):%Y/%m/%d %H:%M}　｜　週次=直近 木〜水"
                f"（{this_w[0].month}/{this_w[0].day}〜{this_w[1].month}/{this_w[1].day}）／月次=当月　｜　配信: 毎週水 10:30")
    g.merge(1, 0, 2, NC)
    g.fmt(1, 0, 2, NC, bg=SUBBAND, fg=SUBINK, size=9, halign="LEFT")
    g.rowh(1, 20)

    # ---------- 左：月次（詳細） ----------
    mc0, mc1 = MCOLS
    L = section(g, 3, mc0, mc1, "■ 月次レポート（当月・経営向け／前月比つき）")
    L = table(g, L, mc0, ["月次サマリ", "当月", "前月", "前月比"],
              [[FLOW[i], fm[i], fpm[i], (f"+{fm[i]-fpm[i]}" if fm[i] >= fpm[i] else str(fm[i]-fpm[i]))]
               for i in range(8)] + [["内定率", pct(fm[6], fm[0]), pct(fpm[6], fpm[0]), ""]],
              aligns=["LEFT", "CENTER", "CENTER", "CENTER"]) + 1
    L = section(g, L, mc0, mc1, "▎ファネル歩留まり（当月・全体）")
    fr = []
    for i, lbl in enumerate(FLOW):
        prevp = "—" if i == 0 else pct(fm[i], fm[i - 1])
        cump = "100%" if i == 0 else pct(fm[i], fm[0])
        drop = 0 if i == 0 else max(0, fm[i - 1] - fm[i])
        fr.append([lbl, fm[i], prevp, cump, drop])
    mfunnel_hdr = L
    L = table(g, L, mc0, ["ステージ", "到達", "前段率", "累積率", "離脱"], fr,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]) + 1
    L = section(g, L, mc0, mc1, "▎雇用区分別（当月・正社員/業務委託）")
    erows = []
    for lab in ["正社員", "業務委託"]:
        cc = funnel_counts([x for x in a_month if x["koyou"] == lab])
        erows.append([f"{lab}（{cc[0]}名）", cc[0], cc[1], cc[6], pct(cc[6], cc[0])])
    L = table(g, L, mc0, ["区分", "応募", "カジュ面談", "内定", "内定率"], erows,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER"]) + 1
    L = section(g, L, mc0, mc1, "▎職種別 実績（当月）")
    jh = ["選考ポジション"] + FLOW
    jrows = [[k] + cc for k, cc in jobs_m] or [["（当月応募なし）"] + [0] * 8]
    mjob_hdr = L
    L = table(g, L, mc0, jh, jrows, aligns=["LEFT"] + ["CENTER"] * 8) + 1
    L = section(g, L, mc0, mc1, "▎経路別 CVR・必要エントリー数（全期間累計）")
    rr = []
    for nm, cc in routes:
        need_o = round(cc[0] / cc[6], 1) if cc[6] else "—"
        need_a = round(cc[0] / cc[7], 1) if cc[7] else "—"
        rr.append([nm, cc[0], cc[6], cc[7], pct(cc[6], cc[0]), need_o, need_a])
    L = table(g, L, mc0, ["経路", "応募", "内定", "承諾", "内定率", "内定1名/必要", "承諾1名/必要"], rr,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER"]) + 1
    L = section(g, L, mc0, mc1, "▎所感（月次・AI下書き）")
    L = note(g, L, mc0, mc1, insight_m, 3) + 1

    # ---------- 右：週次（ワイド・詳細） ----------
    wc0, wc1 = WCOLS
    W = section(g, 3, wc0, wc1, "■ 週次レポート（直近 木〜水・Slack配信と同内容）")
    g.put(W, wc0, judge_line); g.merge(W, wc0, W + 2, wc1 + 1)
    g.fmt(W, wc0, W + 2, wc1 + 1, bg=jbg, fg=INK, bold=True, size=11, halign="LEFT", wrap="WRAP")
    g.border(W, wc0, W + 2, wc1 + 1, color=BORDER)
    g.rowh(W, 22)
    W += 3
    W = section(g, W, wc0, wc1, "▎サマリー（フルファネル：今週／前週／前週比）")
    diff = [fw_week[i] - fw_prev[i] for i in range(8)]
    W = table(g, W, wc0, ["期間 / 状態"] + FLOW + ["内定率"], [
        [f"今週({this_w[0].month}/{this_w[0].day}〜{this_w[1].month}/{this_w[1].day})"] + fw_week + [pct(fw_week[6], fw_week[0])],
        ["前週"] + fw_prev + [pct(fw_prev[6], fw_prev[0])],
        ["前週比"] + [(f"+{d}" if d > 0 else str(d)) for d in diff] + [""],
    ], aligns=["LEFT"] + ["CENTER"] * 9) + 1
    W = section(g, W, wc0, wc1, "▎職種別 応募内訳（今週・選考状況つき）")
    job_hdr = W
    job_rows = [[k, sum(v.values()), "・".join(f"{s}{n}" for s, n in v.most_common())] for k, v in jobs_w] \
        or [["（今週応募なし）", 0, "—"]]
    W = table(g, W, wc0, ["選考ポジション", "件数", "選考状況"], job_rows, aligns=["LEFT", "CENTER", "LEFT"]) + 1
    W = section(g, W, wc0, wc1, "▎ファネル（新規＝今週／前週／進行中＝累計在庫）")
    fw_rows = [["エントリー(応募)", fw_week[0], fw_prev[0], active_by.get("エントリー", 0)]]
    for i, lbl in enumerate(["カジュアル面談", "1次", "2次", "最終", "会食"]):
        fw_rows.append([lbl, fw_week[i + 1], fw_prev[i + 1], active_by.get(lbl, 0)])
    fw_rows.append(["内定", fw_week[6], fw_prev[6], active_by.get("内定", 0)])
    W = table(g, W, wc0, ["ステージ", "今週新規", "前週", "進行中"], fw_rows,
              aligns=["LEFT", "CENTER", "CENTER", "CENTER"]) + 1
    W = section(g, W, wc0, wc1, "▎新規流入 媒体・エージェント別（今週）")
    media_hdr = W
    tot = sum(n for _, n in media_w) or 1
    mw_rows = [[k, n, pct(n, tot)] for k, n in media_w] or [["（今週なし）", 0, "—"]]
    W = table(g, W, wc0, ["経路（媒体・エージェント名）", "件数", "構成比"], mw_rows,
              aligns=["LEFT", "CENTER", "CENTER"]) + 1
    W = section(g, W, wc0, wc1, "▎所感（週次・AI下書き）")
    W = note(g, W, wc0, wc1, insight_w, 3) + 1

    # ---------- グラフ（下部・週次＋月次） ----------
    chart_r = max(L, W) + 1
    g.put(chart_r - 1, 0, "■ 週次グラフ（職種別 横棒／媒体割合 円）")
    g.merge(chart_r - 1, 0, chart_r, NC)
    g.fmt(chart_r - 1, 0, chart_r, NC, bg=SUBBAND, fg=INK, bold=True, size=10, halign="LEFT")
    monthly_chart_r = chart_r + 18
    g.put(monthly_chart_r - 1, 0, "■ 月次グラフ（ファネル到達数／職種別 応募数）")
    g.merge(monthly_chart_r - 1, 0, monthly_chart_r, NC)
    g.fmt(monthly_chart_r - 1, 0, monthly_chart_r, NC, bg=SUBBAND, fg=INK, bold=True, size=10, halign="LEFT")

    # ===== 書込 =====
    svc.spreadsheets().values().update(spreadsheetId=SID, range=f"'{REPORT_TAB}'!A1",
            valueInputOption="USER_ENTERED", body={"values": g.vals}).execute()
    layout = [
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"hideGridlines": True}},
         "fields": "gridProperties.hideGridlines"}},
        {"repeatCell": {"range": {"sheetId": sid}, "cell": {"userEnteredFormat": {"backgroundColor": PAPER,
         "textFormat": {"fontFamily": FONT, "fontSize": 9}}}, "fields": "userEnteredFormat(backgroundColor,textFormat)"}},
        {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 2}},
         "fields": "gridProperties.frozenRowCount"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": NC},
         "properties": {"pixelSize": 78}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
         "properties": {"pixelSize": 150}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 12, "endIndex": 13},
         "properties": {"pixelSize": 24}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 13, "endIndex": 14},
         "properties": {"pixelSize": 230}, "fields": "pixelSize"}},
    ]
    for rr_, px in g.row_h.items():
        layout.append({"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS",
         "startIndex": rr_, "endIndex": rr_ + 1}, "properties": {"pixelSize": px}, "fields": "pixelSize"}})
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": layout}).execute()
    for i in range(0, len(g.reqs), 300):
        svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": g.reqs[i:i + 300]}).execute()
    print(f"[fmt] 書式 {len(g.reqs)} 件")

    charts = [
        chart_req(sid, "職種別 応募内訳（今週）", "BAR", chart_r, 0, job_hdr, len(job_rows), wc0, [wc0 + 1], w=620, h=320),
        pie_req(sid, "媒体（細かい経路）割合（今週）", chart_r, 11, media_hdr, len(mw_rows), wc0, wc0 + 1, w=480, h=320),
        chart_req(sid, "ファネル到達数（当月）", "BAR", monthly_chart_r, 0, mfunnel_hdr, len(fr), 0, [1], w=560, h=320),
        chart_req(sid, "職種別 応募数（当月）", "BAR", monthly_chart_r, 13, mjob_hdr, len(jrows), 0, [1], w=560, h=320),
    ]
    svc.spreadsheets().batchUpdate(spreadsheetId=SID, body={"requests": charts}).execute()
    print("[chart] 横棒(職種別)＋円(媒体)を生成")

    after = svc.spreadsheets().get(spreadsheetId=SID, fields="sheets(properties(sheetId,title))").execute()["sheets"]
    if len(after) != len(before):
        raise RuntimeError("タブ数が変化")
    print(f"[safe] 既存タブ不変（{len(before)}→{len(after)}）")
    print(f"[done] gid={sid}  判定={judge} 今週応募={app_tw}(前週{app_pw}) 当月={fm[0]}(前月{fpm[0]}) 経路数={len(routes)}")
    print(f"https://docs.google.com/spreadsheets/d/{SID}/edit#gid={sid}")


if __name__ == "__main__":
    main()
