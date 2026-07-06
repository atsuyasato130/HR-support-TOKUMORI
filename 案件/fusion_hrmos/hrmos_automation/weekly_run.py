#!/usr/bin/env python3
"""週次ランナー（毎週水 10:30 想定）：
1) レポート出力タブ（月次＋週次・グラフ）を再生成
2) 週次レポートを Slack(Block Kit＋QuickChart) に配信
期間=前週木〜当週水。判定の色バー・職種別/媒体グラフつき。
ログは stdout。launchd/cron から呼び出す想定。"""
import os
import sys
import json
import datetime as dt
import urllib.request
from collections import Counter, defaultdict

sys.path.insert(0, os.path.expanduser("~/Claude AI"))
from dotenv import load_dotenv                       # noqa: E402
from slack_sdk import WebClient                       # noqa: E402
import build_hrmos_report                             # noqa: E402
from build_hrmos_funnel_v2 import (                   # noqa: E402
    SID, TZ, get_service, load_records, funnel_counts, pct, short, inw, FLOW, arrow,
)

CONFIG = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
CHANNEL = "C0A59L3LU12"
GREEN, AMBER, RED = "#2E7D32", "#F59E0B", "#D32F2F"
PALETTE = ["#AF322C", "#4E79A7", "#E8A33D", "#59A14F", "#76B7B2", "#B07AA1", "#9C755F", "#BAB0AC"]


def qc_short(cfg, w, h):
    payload = json.dumps({"chart": cfg, "width": w, "height": h, "backgroundColor": "white"},
                         ensure_ascii=False).encode()
    req = urllib.request.Request("https://quickchart.io/chart/create", data=payload,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["url"]


def post_weekly_slack():
    svc = get_service()
    recs = load_records(svc)
    analysis = [r for r in recs if not r["excluded"]]
    today = dt.datetime.now(TZ).date()
    last_wed = today - dt.timedelta(days=(today.weekday() - 2) % 7)
    this_w = (last_wed - dt.timedelta(days=6), last_wed)
    prev_w = (last_wed - dt.timedelta(days=13), last_wed - dt.timedelta(days=7))

    def cohort(a, b):
        return [r for r in analysis if inw(r["app"], a, b)]

    sub = cohort(*this_w)
    app_tw, app_pw = len(sub), len(cohort(*prev_w))
    new_w = [sum(1 for r in analysis if inw(r["steps"][i], *this_w)) for i in range(5)]
    offer_w = sum(1 for r in analysis if inw(r["offer"], *this_w))

    def closed(r):
        return any((r["accept"], r["join"], r["decline"], r["fail"]))

    def stage(r):
        if r["offer"]:
            return "内定"
        for i in range(4, -1, -1):
            if r["steps"][i]:
                return FLOW[i + 1]
        return "エントリー"
    active_by = Counter(stage(r) for r in analysis if not closed(r))
    n_active = sum(active_by.values())

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
        judge, color = "順調", GREEN
    elif app_tw == 0 or ratio < 0.7:
        judge, color = "要警戒", RED
    else:
        judge, color = "要注意", AMBER

    # QuickChart（職種別 横棒・媒体割合 円）
    bar_items = [(k, sum(v.values())) for k, v in jobs_w]
    bar_cfg = {"type": "horizontalBar", "data": {"labels": [k for k, _ in bar_items],
               "datasets": [{"data": [v for _, v in bar_items], "backgroundColor": "#4E79A7"}]},
               "options": {"title": {"display": True, "text": f"職種別 応募内訳（今週・計{app_tw}名）", "fontSize": 16},
                           "legend": {"display": False},
                           "plugins": {"datalabels": {"anchor": "end", "align": "right", "color": "#333"}},
                           "scales": {"xAxes": [{"ticks": {"beginAtZero": True, "precision": 0}}]}}}
    pie_cfg = {"type": "doughnut", "data": {"labels": [f"{k} {n}件" for k, n in media_w],
               "datasets": [{"data": [n for _, n in media_w], "backgroundColor": PALETTE[:len(media_w)]}]},
               "options": {"title": {"display": True, "text": "媒体（細かい経路）割合（今週）", "fontSize": 15},
                           "legend": {"position": "right"}}}
    bar_url = qc_short(bar_cfg, 720, 380) if bar_items else None
    pie_url = qc_short(pie_cfg, 680, 420) if media_w else None

    def fnum(x, p):
        return f"{x}（{arrow(x, p)}）"
    pos_lines = "\n".join(f"• {k}：{sum(v.values())}（" + "・".join(f"{s}{n}" for s, n in v.most_common()) + "）"
                          for k, v in jobs_w) or "（今週応募なし）"
    rank_lines = "\n".join(f"{i}. {k}　{n}件" for i, (k, n) in enumerate(media_w, 1)) or "（今週なし）"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "FUSION 中途採用｜週次レポート"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"対象期間：{this_w[0]:%Y/%m/%d}(木) 〜 {this_w[1]:%m/%d}(水)　｜　毎週水 10:30"}]},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*判定：{judge}*　今週応募 {app_tw}件（{arrow(app_tw, app_pw)}）／主経路 {top_src[0]} {top_src[1]}件／中心職種 {top_pos}"}},
        {"type": "divider"},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*今週の応募*\n{fnum(app_tw, app_pw)}"},
            {"type": "mrkdwn", "text": f"*進行中パイプライン*\n計 {n_active}名"},
            {"type": "mrkdwn", "text": f"*今週カジュ面談*\n{fnum(new_w[0], 0)}"},
            {"type": "mrkdwn", "text": f"*今週内定*\n{offer_w}"}]},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*職種別 応募内訳（今週）*\n{pos_lines}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"*新規流入 媒体・エージェント別（今週）*\n{rank_lines}"}},
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"*所感（AI下書き）*\n先週（{app_pw}件）→今週{app_tw}件。{top_src[0]}経由が牽引。"
                 "1次以降の歩留まり改善（選考基準の明確化・採用広報資料）が次の打ち手。"}},
        {"type": "context", "elements": [{"type": "mrkdwn", "text": "詳細 ▸ スプレッドシート「レポート出力」タブ"}]},
    ]
    if bar_url:
        blocks.insert(7, {"type": "image", "image_url": bar_url, "alt_text": "職種別応募"})
    if pie_url:
        blocks.append({"type": "image", "image_url": pie_url, "alt_text": "媒体割合"})

    load_dotenv(f"{CONFIG}/.env")
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise SystemExit("SLACK_BOT_TOKEN 未設定")
    res = WebClient(token=token).chat_postMessage(
        channel=CHANNEL, text=f"FUSION 中途採用｜週次レポート（判定：{judge}）",
        attachments=[{"color": color, "blocks": blocks}])
    print(f"[weekly_run] Slack送信 ts={res['ts']} 判定={judge} 応募={app_tw}(前週{app_pw})")


if __name__ == "__main__":
    print(f"[weekly_run] start {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    build_hrmos_report.main()      # レポート出力タブ更新
    post_weekly_slack()            # Slack配信
    print("[weekly_run] done")
