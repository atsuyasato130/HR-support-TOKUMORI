#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOTZ 28卒 採用 週次レポート（Slack・経営報告粒度）のテキストを生成する。

- 本番SS(production)の生データを直接集計（build_dotz_kpi.aggregate 流用）。
- 既定では送信せずテキストを標準出力にプレビューする（--send 指定時のみ送信想定）。
  ※実際の Slack 送信は GAS 側（本番）で行う。本スクリプトは確認用。
- 経営向けに「対目標達成率 / ファネル通過率＋ボトルネック / 着地ペース /
  経路別の質 / 選考中の現況 / 要対応」を含める。

正本: ~/Claude AI/build_dotz_weekly_slack.py
"""

import json
import os
import datetime as dt

from build_dotz_monthly_doc import get_services, load_aggregate
from build_dotz_kpi import NODES, GOAL, TZ

SNAP_FILE = os.path.expanduser("~/Claude AI/.dotz_weekly_snapshot.json")


def _idx(reach, name):
    return reach[NODES.index(name)]


def _rate(n, d):
    return (n / d) if d else None


def _rstr(n, d):
    r = _rate(n, d)
    return f"{r * 100:.0f}%" if r is not None else "—"


def _load_snap():
    """前回レポート時点の各段階累計（スナップショット）を読む。無ければ None。"""
    try:
        with open(SNAP_FILE, encoding="utf-8") as f:
            return json.load(f).get("reach")
    except (OSError, ValueError):
        return None


def _save_snap(reach, today):
    try:
        with open(SNAP_FILE, "w", encoding="utf-8") as f:
            json.dump({"date": today.strftime("%Y/%m/%d"), "reach": reach}, f)
    except OSError as e:
        print("snapshot保存失敗:", e)


def build_weekly_text(agg, today, prev_reach=None):
    reach = agg["reach"]
    el = agg["elapsed_ratio"]
    mwe = agg["m_week_entry"]
    wk_start = today - dt.timedelta(days=today.weekday())
    this_key = wk_start.strftime("%m/%d")
    last_key = (wk_start - dt.timedelta(days=7)).strftime("%m/%d")
    this_new = mwe.get(this_key, 0)
    last_new = mwe.get(last_key, 0)
    dw = this_new - last_new

    g_entry = GOAL.get("エントリー") or 0
    g_acc = GOAL.get("内定承諾") or 0
    wd = ["月", "火", "水", "木", "金", "土", "日"][today.weekday()]

    # 主要ファネル段階（通過率算出用）
    chain = ["エントリー", "説明選考会参加", "1次面接", "2次面接",
             "最終(役員)面接", "内定承諾"]
    # ボトルネック（前段比が最低の隣接遷移）
    worst = None
    for i in range(1, len(chain)):
        cur_n, prev_n = _idx(reach, chain[i]), _idx(reach, chain[i - 1])
        if prev_n < 3:  # 母数が薄い後段（0%誤判定）は除外
            continue
        r = cur_n / prev_n
        if worst is None or r < worst[2]:
            worst = (chain[i - 1], chain[i], r)

    L = []
    L.append(f"*DOTZ 28卒 採用週次レポート* ({today.strftime('%-m月%-d日')}({wd}))")
    L.append("")

    # TL;DR サマリー（最初の1行で全体把握）
    acc_fc = round(agg["accept"] / el) if el > 0 else 0
    bn = f"{worst[0]}→{worst[1]} {worst[2] * 100:.0f}%" if worst else "—"
    L.append(f"*＜今週サマリー＞* 新規 {mwe.get(this_key, 0)}件 ／ "
             f"累計 {reach[0]}/{g_entry}（{_rstr(reach[0], g_entry)}）／ "
             f"承諾着地 約{acc_fc}名(目標{g_acc}) ／ 最大BN {bn}")
    L.append("")

    # 今週のサマリー
    L.append("*■ 今週のサマリー*")
    L.append(f"新規エントリー: *{this_new}件*（前週比 {'+' if dw >= 0 else ''}{dw}件）"
             f"  /  今月累計: {agg['m_month']}件")
    ent_ach = _rstr(reach[0], g_entry)
    L.append(f"累計エントリー: {reach[0]}件 / 目標 {g_entry}（達成率 {ent_ach}）")
    L.append("")

    # 今週のファネル増加（前回レポート比・スナップショット差分）
    L.append("*■ 今週のファネル増加（前回比）*")
    inc_stages = ["説明選考会参加", "1次面接", "カジュアル面談", "2次面接",
                  "最終(役員)面接", "内定出し", "内定承諾"]
    lbl = {"説明選考会参加": "説明会", "1次面接": "1次", "カジュアル面談": "ｶｼﾞｭ",
           "2次面接": "2次", "最終(役員)面接": "最終", "内定出し": "内定",
           "内定承諾": "承諾"}
    if prev_reach:
        parts = []
        for name in inc_stages:
            i = NODES.index(name)
            d = reach[i] - (prev_reach[i] if i < len(prev_reach) else 0)
            parts.append(f"{lbl[name]} {'+' if d >= 0 else ''}{d}")
        L.append(" / ".join(parts))
    else:
        L.append("（初回のため基準値を記録。次回レポートから各段階の増加を表示します）")
    L.append("")

    # 選考ファネル＆通過率＋ボトルネック
    L.append("*■ 選考ファネル＆通過率*")
    e0 = reach[0]
    s = _idx(reach, "説明選考会参加")
    f1 = _idx(reach, "1次面接")
    f2 = _idx(reach, "2次面接")
    fin = _idx(reach, "最終(役員)面接")
    acc = agg["accept"]
    L.append(f"Entry *{e0}* → 説明会 {s} → 1次 {f1} → 2次 {f2} → 最終 {fin} → 承諾 {acc}")
    L.append(f"通過率: 説明会 {_rstr(s, e0)}  /  説明会→1次 {_rstr(f1, s)}  /  "
             f"1次→2次 {_rstr(f2, f1)}")
    if worst:
        L.append(f"[要注意] 最大ボトルネック: {worst[0]}→{worst[1]} 通過率 "
                 f"{worst[2] * 100:.0f}%")
    L.append("")

    # 着地予想（主要段階・年度末・線形）
    L.append("*■ 着地予想（年度末・線形参考）*")
    if el > 0:
        short = {"説明選考会参加": "説明会参加", "1次面接": "1次", "2次面接": "2次",
                 "内定出し": "内定", "内定承諾": "承諾"}
        for name in ["説明選考会参加", "1次面接", "2次面接", "内定出し", "内定承諾"]:
            n = _idx(reach, name)
            fcn = round(n / el)
            g = GOAL.get(name)
            gtxt = f" / 目標 {g}（{_rstr(fcn, g)}）" if g else ""
            L.append(f"{short[name]}: 現 {n} → 予測 約{fcn}{gtxt}")
    L.append("")

    # 経路別の質（CVR）
    L.append("*■ 経路別の質（説明会→1次 通過率）*")
    cnt = 0
    for route, arr in list(agg["routes"].items()):
        rs = arr[NODES.index("説明選考会参加")]
        r1 = arr[NODES.index("1次面接")]
        if rs <= 0:
            continue
        L.append(f"・{route}: 説明会 {rs} → 1次 {r1}（{_rstr(r1, rs)}）")
        cnt += 1
        if cnt >= 4:
            break
    if cnt == 0:
        L.append("・（説明会到達データ蓄積中）")
    L.append("")

    # 選考中の現況
    L.append("*■ 選考中の現況（アクティブ）*")
    dist = agg["active_dist"]
    order = ["説明選考会参加", "説明選考会合格", "1次面接", "1次合格",
             "カジュアル面談", "2次面接", "最終(役員)面接", "内定出し"]
    parts = [f"{n} {dist[n]}" for n in order if dist.get(n)]
    L.append(f"アクティブ計: *{agg['active_total']}名*"
             + ("（" + " / ".join(parts) + "）" if parts else ""))
    L.append(f"平均選考日数: {agg['avg_lt'] if agg['avg_lt'] else '—'}日")
    L.append("")

    # 要対応
    L.append("*■ 今週の要対応*")
    todos = []
    if worst:
        todos.append(f"{worst[0]}→{worst[1]} の通過率改善（面談調整・歩留り対策）")
    if agg["active_total"] > 0:
        todos.append(f"選考中 {agg['active_total']}名の次アクション設定（停滞防止）")
    if not todos:
        todos.append("特記事項なし")
    for t in todos:
        L.append(f"・{t}")
    L.append("")
    L.append("※詳細は採用管理シートを確認ください")

    return "\n".join(L)


def main():
    sheets, _, _ = get_services()
    today = dt.datetime.now(TZ).replace(tzinfo=None)
    agg = load_aggregate(sheets, today)
    prev_reach = _load_snap()
    text = build_weekly_text(agg, today, prev_reach)
    _save_snap(agg["reach"], today)
    print("=" * 60)
    print("週次Slackプレビュー（経営報告粒度・本番データ・送信なし）")
    print("=" * 60)
    print(text)
    print("=" * 60)


if __name__ == "__main__":
    main()
