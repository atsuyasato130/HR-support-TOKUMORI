#!/usr/bin/env python3
"""② 図解カタログ＝HTMLの図・グラフ50パターン（F01-F50・カテゴリ別）。
トンマナ: 温白地×墨#15171C×TOKUMORI赤#AF322C×中立グレー。数字=Lato・和文=Noto Sans JP(palt)。
各スライド=カテゴリ/番号/名前ヘッダ＋図デモ（採用サンプルデータ）。"""
import os
import math
import warnings

warnings.filterwarnings("ignore")
import html_to_slide as H

INK = "#15171C"; PAPER = "#FBFAF9"; RED = "#AF322C"; GRAY = "#8A8F98"
NEU = "#DCD9D4"; NEU2 = "#EDEBE7"; HL = "rgba(21,23,28,0.14)"
FONT = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900'
        '&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')
BASE = ('*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;background:%s;color:%s;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}.en{font-family:Lato,sans-serif;letter-spacing:.14em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}' % (PAPER, INK))

FIGS = []  # (num, category, name, inner_html)


def slide(num, cat, name, inner):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT + f'<style>{BASE}</style></head><body>'
            f'<div style="position:relative;width:1280px;height:720px;padding:48px 72px;">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div class="en" style="font-size:12px;color:{RED};font-weight:900;">F{num:02d}</div>'
            f'<div style="width:1px;height:12px;background:{HL};"></div>'
            f'<div class="en" style="font-size:11px;color:{GRAY};">{cat}</div></div>'
            f'<div class="jp" style="font-size:26px;font-weight:900;margin-top:10px;">{name}</div>'
            f'<div style="position:absolute;left:72px;top:170px;width:1136px;height:470px;">{inner}</div>'
            f'</div></body></html>')


def add(cat, name, inner):
    FIGS.append((len(FIGS) + 1, cat, name, inner))


# ---------- ヘルパー ----------
def hbar(label, pct, val, hi=False, h=30):
    c = RED if hi else NEU; lc = RED if hi else INK
    return (f'<div style="display:flex;align-items:center;margin-bottom:20px;">'
            f'<div class="jp" style="width:180px;font-size:15px;font-weight:700;color:{lc};">{label}</div>'
            f'<div style="flex:1;position:relative;height:{h}px;background:rgba(21,23,28,.045);">'
            f'<div style="position:absolute;left:0;top:0;height:{h}px;width:{pct}%;background:{c};"></div>'
            f'<div class="num" style="position:absolute;left:calc({pct}% + 12px);top:{h//2-11}px;font-size:16px;font-weight:700;color:{lc};">{val}</div>'
            f'</div></div>')


def vcol(label, hpx, val, hi=False, w=74):
    c = RED if hi else NEU
    return (f'<div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;">'
            f'<div class="num" style="font-size:15px;font-weight:700;color:{RED if hi else INK};margin-bottom:6px;">{val}</div>'
            f'<div style="width:{w}px;height:{hpx}px;background:{c};"></div>'
            f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:10px;">{label}</div></div>')


def donut(pct, size=210, stroke=26, color=RED, center=None, sub=""):
    deg = pct * 3.6
    ctr = center or f"{pct}%"
    return (f'<div style="position:relative;width:{size}px;height:{size}px;border-radius:50%;'
            f'background:conic-gradient({color} 0deg {deg}deg, {NEU2} {deg}deg 360deg);">'
            f'<div style="position:absolute;inset:{stroke}px;background:{PAPER};border-radius:50%;'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;">'
            f'<div class="num" style="font-size:{size//5}px;font-weight:900;">{ctr}</div>'
            f'<div class="jp" style="font-size:12px;color:{GRAY};">{sub}</div></div></div>')


def chip(txt, filled=False):
    return (f'<span class="jp" style="display:inline-block;padding:6px 14px;font-size:13px;font-weight:700;'
            f'background:{RED if filled else "transparent"};color:{"#fff" if filled else INK};'
            f'border:1.5px solid {RED if filled else NEU};margin-right:8px;">{txt}</span>')


ARROW = f'<div style="font-family:Lato;font-size:26px;color:{GRAY};margin:0 18px;">→</div>'


# ============ A. 棒・量 ============
add("Bars ／ 量の比較", "横棒＋1色ハイライト",
    '<div style="padding-top:40px;">' + hbar("300人以下", 92, "8.98倍", True) + hbar("1,000人以上", 13, "1.20倍") +
    hbar("5,000人以上", 4, "0.34倍") + '</div>')

add("Bars ／ 量の比較", "縦棒（年次推移）",
    '<div style="display:flex;gap:44px;height:360px;align-items:flex-end;padding:0 60px;">' +
    "".join(vcol(y, h, v, hi) for y, h, v, hi in
            [("2022", 90, "58", 0), ("2023", 140, "121", 0), ("2024", 200, "204", 0), ("2025", 260, "310", 0), ("2026", 320, "470", 1)]) + '</div>')

add("Bars ／ 量の比較", "グループ棒（2系列）",
    f'<div style="display:flex;gap:56px;height:340px;align-items:flex-end;padding:0 40px;">' +
    "".join(f'<div style="display:flex;align-items:flex-end;gap:8px;height:100%;">'
            f'<div style="display:flex;flex-direction:column;justify-content:flex-end;height:100%;align-items:center;">'
            f'<div style="width:52px;height:{a}px;background:{NEU};"></div><div class="jp" style="font-size:12px;color:{GRAY};margin-top:8px;">{l}<br>従来</div></div>'
            f'<div style="display:flex;flex-direction:column;justify-content:flex-end;height:100%;align-items:center;">'
            f'<div style="width:52px;height:{b}px;background:{RED};"></div><div class="jp" style="font-size:12px;color:{GRAY};margin-top:8px;"><br>当社</div></div></div>'
            for l, a, b in [("母集団", 90, 240), ("面談数", 110, 210), ("内定数", 70, 150), ("承諾数", 50, 130)]) + '</div>')

add("Bars ／ 量の比較", "積み上げ棒（構成比）",
    '<div style="padding-top:60px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:30px;">'
            f'<div class="jp" style="width:150px;font-size:15px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;display:flex;height:38px;">'
            f'<div style="width:{a}%;background:{RED};"></div><div style="width:{b}%;background:{NEU};"></div>'
            f'<div style="width:{c}%;background:{NEU2};"></div></div>'
            f'<div class="num" style="width:80px;text-align:right;font-weight:700;">{a}%</div></div>'
            for l, a, b, c in [("スカウト", 46, 34, 20), ("媒体", 28, 47, 25), ("リファラル", 12, 30, 58)]) +
    f'<div class="jp" style="font-size:12px;color:{GRAY};margin-top:6px;">■ 当社経由　<span style="color:{NEU};">■</span> 自社直接　<span style="color:{NEU2};">■</span> その他</div></div>')

add("Bars ／ 量の比較", "発散棒（増減±）",
    '<div style="padding-top:40px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:22px;">'
            f'<div class="jp" style="width:170px;font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;position:relative;height:30px;">'
            f'<div style="position:absolute;left:50%;top:0;width:1.5px;height:30px;background:{INK};opacity:.25;"></div>'
            f'<div style="position:absolute;{"left:50%" if v>0 else f"right:50%"};top:0;height:30px;width:{abs(v)}%;background:{RED if v>0 else NEU};"></div>'
            f'<div class="num" style="position:absolute;{"left" if v>0 else "right"}:calc(50% + {abs(v)}% + 10px);top:4px;font-size:15px;font-weight:700;color:{RED if v>0 else GRAY};">{"+" if v>0 else ""}{v}%</div>'
            f'</div></div>'
            for l, v in [("エントリー", 38), ("説明会参加", 24), ("辞退率", -17), ("採用工数", -32)]) + '</div>')

add("Bars ／ 量の比較", "ブレット（目標vs実績）",
    '<div style="padding-top:56px;">' +
    "".join(f'<div style="margin-bottom:40px;"><div style="display:flex;justify-content:space-between;">'
            f'<div class="jp" style="font-size:15px;font-weight:700;">{l}</div>'
            f'<div class="num" style="font-size:15px;font-weight:700;color:{RED};">{v} <span style="color:{GRAY};font-weight:400;">/ 目標 {t}</span></div></div>'
            f'<div style="position:relative;height:20px;background:{NEU2};margin-top:10px;">'
            f'<div style="position:absolute;left:0;top:0;height:20px;width:{p}%;background:{RED};"></div>'
            f'<div style="position:absolute;left:{g}%;top:-5px;width:2.5px;height:30px;background:{INK};"></div></div></div>'
            for l, v, t, p, g in [("母集団形成", "742名", "600名", 92, 74), ("内定承諾", "12名", "15名", 62, 78)]) + '</div>')

add("Bars ／ 量の比較", "達成率プログレス一覧",
    '<div style="padding-top:36px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:26px;">'
            f'<div class="jp" style="width:200px;font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;height:10px;background:{NEU2};border-radius:5px;position:relative;">'
            f'<div style="position:absolute;left:0;top:0;height:10px;width:{p}%;background:{RED if p>=100 else INK};border-radius:5px;"></div></div>'
            f'<div class="num" style="width:90px;text-align:right;font-size:16px;font-weight:900;color:{RED if p>=100 else INK};">{p}%</div></div>'
            for l, p in [("スカウト送信", 118), ("カジュアル面談", 104), ("一次面接", 87), ("最終面接", 72), ("内定承諾", 61)]) + '</div>')

add("Bars ／ 量の比較", "ランキング棒＋前年差",
    '<div style="padding-top:30px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:19px;">'
            f'<div class="num" style="width:44px;font-size:19px;font-weight:900;color:{RED if i==0 else GRAY};">{i+1}</div>'
            f'<div class="jp" style="width:200px;font-size:14.5px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;position:relative;height:26px;background:rgba(21,23,28,.045);">'
            f'<div style="position:absolute;left:0;top:0;height:26px;width:{p}%;background:{RED if i==0 else NEU};"></div></div>'
            f'<div class="num" style="width:120px;text-align:right;font-size:14px;color:{GRAY};">{d}</div></div>'
            for i, (l, p, d) in enumerate([("求人検索エンジン", 88, "+12pt"), ("ダイレクトスカウト", 71, "+8pt"),
                                           ("人材紹介", 52, "−4pt"), ("リファラル", 34, "+6pt"), ("SNS採用", 22, "+9pt")])) + '</div>')

add("Bars ／ 量の比較", "ウォーターフォール（差分の橋）",
    f'<div style="display:flex;align-items:flex-end;height:340px;gap:34px;padding:0 60px;">'
    f'<div style="display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;">'
    f'<div class="num" style="font-weight:900;margin-bottom:6px;">1,410</div><div style="width:120px;height:282px;background:{INK};"></div>'
    f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:10px;">現状コスト</div></div>'
    f'<div style="display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;">'
    f'<div style="height:51px;"></div><div class="num" style="font-weight:900;color:{RED};margin-bottom:6px;">−255</div>'
    f'<div style="width:120px;height:51px;background:{RED};"></div><div style="height:180px;"></div>'
    f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:-24px;">置き換え削減</div></div>'
    f'<div style="display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;">'
    f'<div class="num" style="font-weight:900;margin-bottom:6px;">1,155</div><div style="width:120px;height:231px;background:{NEU};"></div>'
    f'<div class="jp" style="font-size:13px;color:{GRAY};margin-top:10px;">導入後</div></div>'
    f'<div class="jp" style="align-self:center;margin-left:30px;font-size:14px;color:{GRAY};line-height:2;">単位=万円/年<br>削減率 <span class="num" style="color:{RED};font-weight:900;font-size:22px;">−18%</span></div></div>')

# ============ B. 線・推移 ============
def line_svg(points, w=1000, hh=300, color=RED, dot_last=True, fill=False):
    xs = [60 + i * (w - 120) / (len(points) - 1) for i in range(len(points))]
    ys = [hh - 40 - p * (hh - 90) / 100 for p in points]
    pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in zip(xs, ys))
    fillp = f'<polygon points="{xs[0]:.0f},{hh-40} {pts} {xs[-1]:.0f},{hh-40}" fill="rgba(175,50,44,.08)"/>' if fill else ""
    dot = f'<circle cx="{xs[-1]:.0f}" cy="{ys[-1]:.0f}" r="7" fill="{color}"/>' if dot_last else ""
    base = f'<line x1="40" y1="{hh-40}" x2="{w-40}" y2="{hh-40}" stroke="{INK}" stroke-opacity=".2"/>'
    return f'<svg width="{w}" height="{hh}">{base}{fillp}<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3.5"/>{dot}</svg>'


add("Lines ／ 推移", "折れ線（終点強調）",
    f'<div style="padding-top:30px;">{line_svg([12,20,34,42,58,66,84])}'
    f'<div style="display:flex;justify-content:space-between;width:1000px;padding:0 42px;" class="num">' +
    "".join(f'<div style="font-size:13px;color:{GRAY};">{m}</div>' for m in ["1月", "2月", "3月", "4月", "5月", "6月", "7月"]) +
    f'</div><div class="jp" style="margin-top:16px;font-size:15px;font-weight:700;">エントリー数は7ヶ月で <span class="num" style="color:{RED};font-size:20px;font-weight:900;">7.0倍</span></div></div>')

add("Lines ／ 推移", "エリアチャート（面）",
    f'<div style="padding-top:30px;">{line_svg([18,26,30,44,52,68,90], fill=True)}'
    f'<div class="jp" style="margin-top:16px;font-size:14px;color:{GRAY};">累計内定承諾数の推移（2026年上期）</div></div>')

add("Lines ／ 推移", "スロープチャート（2時点）",
    f'<div style="display:flex;gap:120px;padding:40px 80px;">' +
    "".join(f'<svg width="240" height="300">'
            f'<line x1="40" y1="{260-a*2}" x2="200" y2="{260-b*2}" stroke="{RED if hi else NEU}" stroke-width="{4 if hi else 3}"/>'
            f'<circle cx="40" cy="{260-a*2}" r="6" fill="{RED if hi else NEU}"/><circle cx="200" cy="{260-b*2}" r="6" fill="{RED if hi else NEU}"/>'
            f'<text x="40" y="{250-a*2}" font-family="Lato" font-size="15" font-weight="700" fill="{INK}" text-anchor="middle">{a}%</text>'
            f'<text x="200" y="{250-b*2}" font-family="Lato" font-size="17" font-weight="900" fill="{RED if hi else INK}" text-anchor="middle">{b}%</text>'
            f'<text x="120" y="292" font-size="14" fill="{GRAY}" text-anchor="middle" font-family="Noto Sans JP">{l}</text></svg>'
            for l, a, b, hi in [("書類通過率", 34, 61, 1), ("面接設定率", 48, 72, 0), ("内定承諾率", 45, 83, 1)]) + '</div>')

add("Lines ／ 推移", "スパークライン行（KPI×ミニ推移）",
    '<div style="padding-top:26px;">' +
    "".join(f'<div style="display:flex;align-items:center;border-bottom:1px solid {HL};padding:18px 0;">'
            f'<div class="jp" style="width:230px;font-size:15px;font-weight:700;">{l}</div>'
            f'<div>{line_svg(pts, w=420, hh=64, color=(RED if hi else "#9AA0A8"), dot_last=True)}</div>'
            f'<div class="num" style="flex:1;text-align:right;font-size:24px;font-weight:900;color:{RED if hi else INK};">{v}</div></div>'
            for l, pts, v, hi in [("エントリー", [20, 35, 30, 55, 80], "742", 1), ("面談実施", [30, 32, 45, 50, 62], "218", 0), ("内定承諾", [10, 22, 30, 44, 70], "12", 1)]) + '</div>')

add("Lines ／ 推移", "メッコ風（構成×規模）",
    f'<div style="display:flex;height:330px;padding-top:30px;gap:4px;">' +
    "".join(f'<div style="width:{w}px;display:flex;flex-direction:column;gap:4px;">'
            + "".join(f'<div style="height:{h}%;background:{c};display:flex;align-items:center;justify-content:center;">'
                      f'<span class="num" style="font-size:13px;font-weight:700;color:{"#fff" if c in (RED, INK) else INK};">{p}</span></div>'
                      for h, c, p in segs) +
            f'<div class="jp" style="text-align:center;font-size:13px;color:{GRAY};padding-top:6px;">{l}<br><span class="num">{tot}</span></div></div>'
            for l, w, tot, segs in [
                ("スカウト", 420, "46%", [(58, RED, "58%"), (30, NEU, "30%"), (12, NEU2, "12%")]),
                ("媒体", 300, "33%", [(34, RED, "34%"), (44, NEU, "44%"), (22, NEU2, "22%")]),
                ("紹介", 190, "21%", [(22, RED, "22%"), (38, NEU, "38%"), (40, NEU2, "40%")])]) + '</div>')

# ============ C. 円・割合 ============
add("Circles ／ 割合", "ドーナツ（中央数値）",
    f'<div style="display:flex;align-items:center;gap:80px;padding:20px 60px;">{donut(83, 260, 32, RED, "83%", "内定承諾率")}'
    f'<div class="jp" style="font-size:15px;line-height:2.2;color:#3A3F47;">事例D（広告・中途）<br>CX設計＋クロージング強化により<br>承諾率 <b class="num" style="color:{RED};font-size:19px;">83%</b>（業界平均 45%）</div></div>')

add("Circles ／ 割合", "半円ゲージ",
    f'<div style="display:flex;justify-content:center;padding-top:50px;">'
    f'<div style="position:relative;width:420px;height:210px;overflow:hidden;">'
    f'<div style="width:420px;height:420px;border-radius:50%;background:conic-gradient(from 270deg, {RED} 0deg 122deg, {NEU2} 122deg 180deg, transparent 180deg 360deg);"></div>'
    f'<div style="position:absolute;left:60px;top:60px;width:300px;height:300px;border-radius:50%;background:{PAPER};"></div>'
    f'<div style="position:absolute;left:0;right:0;top:120px;text-align:center;"><span class="num" style="font-size:64px;font-weight:900;">68<span style="font-size:30px;">%</span></span>'
    f'<div class="jp" style="font-size:13px;color:{GRAY};">目標達成率（上期）</div></div></div></div>')

add("Circles ／ 割合", "ラジアル進捗×3",
    f'<div style="display:flex;gap:90px;justify-content:center;padding-top:40px;">' +
    "".join(f'<div style="text-align:center;">{donut(p, 190, 20, RED if hi else INK, f"{p}%", l)}</div>'
            for p, l, hi in [(92, "母集団目標", 1), (74, "面談設定", 0), (61, "承諾", 0)]) + '</div>')

add("Circles ／ 割合", "円面積バブル比較",
    f'<div style="display:flex;align-items:flex-end;gap:70px;justify-content:center;padding-top:60px;">' +
    "".join(f'<div style="text-align:center;"><div style="width:{d}px;height:{d}px;border-radius:50%;background:{c};'
            f'display:flex;align-items:center;justify-content:center;margin:0 auto;">'
            f'<span class="num" style="font-size:{d//5}px;font-weight:900;color:{tc};">{v}</span></div>'
            f'<div class="jp" style="font-size:14px;color:{GRAY};margin-top:14px;">{l}</div></div>'
            for d, c, tc, v, l in [(120, NEU2, INK, "58", "導入前"), (200, NEU, INK, "204", "6ヶ月"), (300, RED, "#fff", "742", "12ヶ月")]) + '</div>')

add("Circles ／ 割合", "ワッフル（100マス）",
    f'<div style="display:flex;align-items:center;gap:80px;padding:16px 40px;">'
    f'<div style="display:grid;grid-template-columns:repeat(10,30px);grid-gap:6px;">' +
    "".join(f'<div style="width:30px;height:30px;background:{RED if i < 47 else NEU2};"></div>' for i in range(100)) +
    f'</div><div class="jp" style="font-size:16px;line-height:2.1;">早期離職の <b class="num" style="font-size:30px;color:{RED};">47%</b> は<br>入社6ヶ月以内に発生。<br><span style="color:{GRAY};font-size:13.5px;">出典: en調査 2026</span></div></div>')

# ============ D. 数値・KPI ============
add("Numbers ／ KPI", "KPIカード×4",
    f'<div style="display:flex;gap:24px;padding-top:50px;">' +
    "".join(f'<div style="flex:1;border-top:3px solid {RED if hi else NEU};padding:22px 4px 0;">'
            f'<div class="jp" style="font-size:13.5px;color:{GRAY};font-weight:700;">{l}</div>'
            f'<div class="num jp" style="font-size:52px;font-weight:900;margin-top:10px;color:{RED if hi else INK};">{v}</div>'
            f'<div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:8px;">{n}</div></div>'
            for l, v, n, hi in [("母集団形成", "29倍", "最大・事例値", 1), ("内定承諾率", "+38%", "改善・方向値", 0),
                                ("人事工数", "−89%", "削減", 0), ("採用期間", "−40%", "短縮", 0)]) + '</div>')

add("Numbers ／ KPI", "巨大数字＋トレンド",
    f'<div style="display:flex;align-items:baseline;gap:40px;padding-top:60px;">'
    f'<div class="num jp" style="font-size:190px;font-weight:900;letter-spacing:-.02em;line-height:1;">742<span style="font-size:60px;">名</span></div>'
    f'<div><div class="num" style="font-size:34px;font-weight:900;color:{RED};">↑ +1,170%</div>'
    f'<div class="jp" style="font-size:15px;color:{GRAY};margin-top:10px;">エントリー数（事例A・年間）<br>58名 → 742名</div></div></div>')

add("Numbers ／ KPI", "数値グリッド 2×3",
    f'<div style="display:grid;grid-template-columns:repeat(3,1fr);grid-gap:1px;background:{HL};margin-top:30px;">' +
    "".join(f'<div style="background:{PAPER};padding:34px 30px;">'
            f'<div class="jp" style="font-size:13px;color:{GRAY};font-weight:700;">{l}</div>'
            f'<div class="num jp" style="font-size:44px;font-weight:900;margin-top:8px;color:{RED if hi else INK};">{v}</div></div>'
            for l, v, hi in [("取引社数", "300社", 0), ("SNSリーチ", "25万人", 0), ("連続増収", "5期", 0),
                             ("スカウト返信率", "2.4倍", 1), ("平均TTH", "40日", 0), ("継続率", "94%", 0)]) + '</div>')

add("Numbers ／ KPI", "Before → After",
    f'<div style="display:flex;align-items:center;justify-content:center;gap:20px;padding-top:80px;">'
    f'<div style="text-align:center;"><div class="jp en" style="font-size:12px;color:{GRAY};">Before</div>'
    f'<div class="num jp" style="font-size:80px;font-weight:900;color:{GRAY};">45<span style="font-size:36px;">%</span></div></div>'
    f'<svg width="140" height="40"><line x1="0" y1="20" x2="120" y2="20" stroke="{RED}" stroke-width="3"/><path d="M120,10 L140,20 L120,30 Z" fill="{RED}"/></svg>'
    f'<div style="text-align:center;"><div class="jp en" style="font-size:12px;color:{RED};font-weight:700;">After</div>'
    f'<div class="num jp" style="font-size:120px;font-weight:900;color:{RED};line-height:1;">83<span style="font-size:50px;">%</span></div></div>'
    f'<div class="jp" style="margin-left:40px;font-size:15px;color:{GRAY};">内定承諾率<br>（事例D・n=6）</div></div>')

add("Numbers ／ KPI", "カウンター行（単位混在）",
    f'<div style="display:flex;justify-content:space-between;padding:70px 30px 0;">' +
    "".join(f'<div style="text-align:center;"><div class="num jp" style="font-size:58px;font-weight:900;">{v}<span style="font-size:24px;color:{GRAY};">{u}</span></div>'
            f'<div class="jp" style="font-size:13.5px;color:{GRAY};margin-top:10px;">{l}</div></div>' +
            (f'<div style="width:1px;background:{HL};"></div>' if i < 3 else "")
            for i, (v, u, l) in enumerate([("6", "期目", "設立からの成長"), ("300", "社", "累計取引"), ("94", "%", "契約継続率"), ("40", "日", "平均採用期間")])) + '</div>')

add("Numbers ／ KPI", "2社比較スタット",
    f'<div style="display:flex;gap:1px;background:{HL};margin-top:40px;">'
    f'<div style="flex:1;background:{PAPER};padding:40px;"><div class="jp" style="font-size:15px;font-weight:700;color:{GRAY};">一般的なRPO</div>' +
    "".join(f'<div style="display:flex;justify-content:space-between;border-bottom:1px solid {HL};padding:16px 0;">'
            f'<span class="jp" style="font-size:14px;color:{GRAY};">{l}</span><span class="num" style="font-weight:700;color:{GRAY};">{v}</span></div>'
            for l, v in [("戦略設計", "×"), ("学術的根拠", "×"), ("実働時間", "100h")]) +
    f'</div><div style="flex:1;background:{INK};padding:40px;color:#fff;"><div class="jp" style="font-size:15px;font-weight:700;color:{RED.replace("#AF","#E5")};">とくもり採用代行</div>' +
    "".join(f'<div style="display:flex;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.15);padding:16px 0;">'
            f'<span class="jp" style="font-size:14px;color:#B9BDC4;">{l}</span><span class="num jp" style="font-weight:900;">{v}</span></div>'
            for l, v in [("戦略設計", "◎ 学術×データ"), ("学術的根拠", "◎ 全施策"), ("実働時間", "100h+設計")]) + '</div></div>')

# ============ E. フロー・プロセス ============
add("Flow ／ 工程", "番号ステップ（5段）",
    f'<div style="display:flex;align-items:flex-start;justify-content:space-between;padding:70px 10px 0;">' +
    "".join((f'<div style="text-align:center;width:180px;">'
             f'<div class="num" style="width:58px;height:58px;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;'
             f'font-size:20px;font-weight:900;{"background:"+RED+";color:#fff;" if hi else "border:2px solid "+NEU+";color:"+INK+";"}">{i+1:02d}</div>'
             f'<div class="jp" style="font-size:15px;font-weight:700;margin-top:14px;">{t}</div>'
             f'<div class="jp" style="font-size:12.5px;color:{GRAY};margin-top:6px;">{d}</div></div>') +
            (f'<svg width="46" height="58"><line x1="4" y1="29" x2="38" y2="29" stroke="{NEU}" stroke-width="2"/><path d="M38,23 L46,29 L38,35 Z" fill="{NEU}"/></svg>' if i < 4 else "")
            for i, (t, d, hi) in enumerate([("ヒアリング", "当日", 0), ("要件整理", "次回", 0), ("ご契約", "最短1週", 0), ("Kick Off", "2週間", 0), ("活動開始", "全ファネル", 1)])) + '</div>')

add("Flow ／ 工程", "ファネル（採用）",
    '<div style="padding-top:30px;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:10px;">'
            f'<div style="width:{w}%;height:52px;background:{RED if hi else c};margin:0 auto;display:flex;align-items:center;justify-content:center;">'
            f'<span class="jp" style="color:{"#fff" if hi or c==INK else INK};font-size:14.5px;font-weight:700;">{l}　<span class="num">{v}</span></span></div></div>'
            for l, v, w, c, hi in [("エントリー", "742", 96, NEU2, 0), ("書類通過", "421", 74, NEU, 0), ("一次面接", "218", 55, NEU, 0),
                                   ("最終面接", "64", 36, INK, 0), ("内定承諾", "12", 22, "", 1)]) + '</div>')

add("Flow ／ 工程", "パイプライン（横帯）",
    f'<div style="display:flex;height:120px;margin-top:90px;">' +
    "".join(f'<div style="flex:{f};background:{c};clip-path:polygon(0 0,calc(100% - 26px) 0,100% 50%,calc(100% - 26px) 100%,0 100%,26px 50%);'
            f'display:flex;flex-direction:column;align-items:center;justify-content:center;margin-right:-18px;">'
            f'<span class="jp" style="font-size:14.5px;font-weight:700;color:{"#fff" if c in (INK, RED) else INK};">{l}</span>'
            f'<span class="num" style="font-size:12.5px;color:{"rgba(255,255,255,.7)" if c in (INK, RED) else GRAY};">{d}</span></div>'
            for l, d, f, c in [("戦略設計", "W1-2", 1, NEU2), ("媒体・スカウト", "W3-6", 1.2, NEU), ("選考運用", "W7-10", 1.2, INK), ("クロージング", "W11-12", 1, RED)]) + '</div>')

add("Flow ／ 工程", "タイムライン（マイルストーン）",
    f'<div style="position:relative;padding-top:120px;">'
    f'<div style="position:absolute;left:20px;right:20px;top:150px;height:2px;background:{NEU};"></div>' +
    "".join(f'<div style="position:absolute;left:{x}px;top:120px;text-align:center;width:170px;margin-left:-85px;">'
            f'<div class="num" style="font-size:13px;color:{RED if hi else GRAY};font-weight:700;">{d}</div>'
            f'<div style="width:{16 if hi else 12}px;height:{16 if hi else 12}px;border-radius:50%;background:{RED if hi else PAPER};'
            f'border:2.5px solid {RED if hi else NEU};margin:12px auto;"></div>'
            f'<div class="jp" style="font-size:14px;font-weight:700;">{l}</div></div>'
            for x, d, l, hi in [(110, "7月", "契約・KO", 0), (390, "8月", "母集団稼働", 0), (670, "10月", "選考ピーク", 0), (950, "12月", "承諾12名", 1)]) + '</div>')

add("Flow ／ 工程", "ガント（期間バー）",
    '<div style="padding-top:44px;">' +
    f'<div style="display:flex;margin-bottom:14px;padding-left:190px;" class="num">' +
    "".join(f'<div style="flex:1;font-size:12px;color:{GRAY};text-align:center;">{m}月</div>' for m in range(7, 13)) + '</div>' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:18px;">'
            f'<div class="jp" style="width:190px;font-size:14px;font-weight:700;">{l}</div>'
            f'<div style="flex:1;position:relative;height:26px;background:rgba(21,23,28,.04);">'
            f'<div style="position:absolute;left:{s}%;width:{w}%;top:0;height:26px;background:{RED if hi else NEU};"></div></div></div>'
            for l, s, w, hi in [("戦略・要件設計", 0, 18, 0), ("スカウト運用", 12, 55, 1), ("説明会・選考", 30, 48, 0), ("クロージング", 65, 30, 0), ("型化・引き継ぎ", 82, 18, 0)]) + '</div>')

add("Flow ／ 工程", "サイクル（PDCA環）",
    f'<div style="position:relative;width:420px;height:420px;margin:8px auto 0;">'
    f'<div style="position:absolute;inset:60px;border:2px dashed {NEU};border-radius:50%;"></div>' +
    "".join(f'<div style="position:absolute;{pos};width:150px;text-align:center;">'
            f'<div style="width:74px;height:74px;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;'
            f'{"background:"+RED+";color:#fff;" if hi else "background:"+PAPER+";border:2px solid "+NEU+";"}" class="en"><b>{t}</b></div>'
            f'<div class="jp" style="font-size:13px;font-weight:700;margin-top:8px;">{l}</div></div>'
            for t, l, pos, hi in [("Plan", "週次で仮説", "left:135px;top:-6px", 0), ("Do", "実働代行", "right:-40px;top:150px", 0),
                                  ("Check", "数値レビュー", "left:135px;bottom:-6px", 0), ("Act", "翌週に反映", "left:-40px;top:150px", 1)]) + '</div>')

add("Flow ／ 工程", "スイムレーン（役割×工程）",
    f'<div style="margin-top:34px;border:1px solid {HL};">' +
    "".join(f'<div style="display:flex;border-bottom:1px solid {HL};">'
            f'<div class="jp" style="width:150px;padding:20px;font-size:13.5px;font-weight:900;background:rgba(21,23,28,.03);">{r}</div>' +
            "".join(f'<div style="flex:1;padding:20px 12px;border-left:1px solid {HL};">' +
                    (f'<div class="jp" style="background:{RED if hi else NEU2};color:{"#fff" if hi else INK};font-size:12.5px;font-weight:700;padding:8px 10px;text-align:center;">{c}</div>' if c else "") + '</div>'
                    for c, hi in cells) + '</div>'
            for r, cells in [("とくもり", [("戦略設計", 1), ("スカウト実働", 0), ("日程調整", 0), ("週次レポート", 0)]),
                             ("貴社 人事", [("要件FB", 0), ("", 0), ("面接実施", 0), ("合否判断", 1)]),
                             ("現場", [("", 0), ("カジュアル面談", 0), ("", 0), ("最終面接", 0)])]) + '</div>')

# ============ F. 構造 ============
add("Structure ／ 構造", "ピラミッド（3層）",
    f'<div style="padding-top:26px;text-align:center;">' +
    "".join(f'<div style="width:{w}px;margin:0 auto 8px;background:{c};color:{tc};padding:20px 0;'
            f'clip-path:polygon({cp});"><div class="jp" style="font-size:15.5px;font-weight:900;">{l}</div>'
            f'<div class="jp" style="font-size:12.5px;opacity:.75;">{d}</div></div>'
            for w, c, tc, l, d, cp in [
                (360, RED, "#fff", "市場層", "規模・地域の採用力格差", "18% 0,82% 0,100% 100%,0 100%"),
                (620, NEU, INK, "組織層", "採用×育成×評価の連動", "10% 0,90% 0,100% 100%,0 100%"),
                (880, NEU2, INK, "手法層", "選考の科学的妥当性", "6% 0,94% 0,100% 100%,0 100%")]) + '</div>')

add("Structure ／ 構造", "2×2マトリクス（プロット）",
    f'<div style="position:relative;width:560px;height:400px;margin:20px auto 0;">'
    f'<div style="position:absolute;left:50%;top:0;width:1.5px;height:100%;background:{NEU};"></div>'
    f'<div style="position:absolute;left:0;top:50%;width:100%;height:1.5px;background:{NEU};"></div>'
    f'<div class="jp" style="position:absolute;left:50%;top:-28px;transform:translateX(-50%);font-size:12.5px;color:{GRAY};">戦略性 高</div>'
    f'<div class="jp" style="position:absolute;left:50%;bottom:-28px;transform:translateX(-50%);font-size:12.5px;color:{GRAY};">戦略性 低</div>'
    f'<div class="jp" style="position:absolute;left:-56px;top:50%;font-size:12.5px;color:{GRAY};">実働 弱</div>'
    f'<div class="jp" style="position:absolute;right:-56px;top:50%;font-size:12.5px;color:{GRAY};">実働 強</div>' +
    "".join(f'<div style="position:absolute;left:{x}px;top:{y}px;text-align:center;transform:translate(-50%,-50%);">'
            f'<div style="width:{26 if hi else 18}px;height:{26 if hi else 18}px;border-radius:50%;background:{RED if hi else NEU};margin:0 auto;"></div>'
            f'<div class="jp" style="font-size:13px;font-weight:{900 if hi else 400};margin-top:6px;color:{RED if hi else GRAY};">{l}</div></div>'
            for l, x, y, hi in [("コンサル", 150, 90, 0), ("派遣", 360, 300, 0), ("一般RPO", 420, 220, 0), ("とくもり", 470, 70, 1)]) + '</div>')

add("Structure ／ 構造", "ベン図（2円）",
    f'<div style="position:relative;width:700px;height:380px;margin:30px auto 0;">'
    f'<div style="position:absolute;left:60px;top:30px;width:320px;height:320px;border-radius:50%;background:rgba(21,23,28,.07);"></div>'
    f'<div style="position:absolute;right:60px;top:30px;width:320px;height:320px;border-radius:50%;background:rgba(175,50,44,.10);border:1.5px solid rgba(175,50,44,.4);"></div>'
    f'<div class="jp" style="position:absolute;left:110px;top:170px;font-size:15px;font-weight:700;text-align:center;">採用の実務力<br><span style="font-size:12.5px;color:{GRAY};font-weight:400;">RPO会社</span></div>'
    f'<div class="jp" style="position:absolute;right:100px;top:170px;font-size:15px;font-weight:700;text-align:center;">学術・データ<br><span style="font-size:12.5px;color:{GRAY};font-weight:400;">コンサル</span></div>'
    f'<div class="jp" style="position:absolute;left:50%;top:160px;transform:translateX(-50%);text-align:center;background:{RED};color:#fff;padding:14px 18px;font-size:14px;font-weight:900;">両立＝<br>とくもり</div></div>')

add("Structure ／ 構造", "レイヤースタック",
    '<div style="padding-top:30px;width:760px;margin:0 auto;">' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:10px;">'
            f'<div style="flex:1;background:{c};color:{tc};padding:22px 28px;" class="jp">'
            f'<b style="font-size:15.5px;">{l}</b>　<span style="font-size:13px;opacity:.75;">{d}</span></div>'
            f'<div class="en" style="width:90px;text-align:right;font-size:11px;color:{GRAY};">{t}</div></div>'
            for l, d, c, tc, t in [("型化・自走", "FMT・引き継ぎ", RED, "#fff", "Layer 4"),
                                   ("効率化", "AI・自動化", INK, "#fff", "Layer 3"),
                                   ("実働", "スカウト〜面談", NEU, INK, "Layer 2"),
                                   ("戦略", "設計・KPI", NEU2, INK, "Layer 1")]) + '</div>')

add("Structure ／ 構造", "オニオン（同心円）",
    f'<div style="position:relative;width:430px;height:430px;margin:4px auto 0;">' +
    "".join(f'<div style="position:absolute;inset:{i};border-radius:50%;background:{c};border:1px solid {HL};"></div>'
            for i, c in [("0px", NEU2), ("62px", NEU), ("124px", "#fff")]) +
    f'<div style="position:absolute;inset:186px;border-radius:50%;background:{RED};display:flex;align-items:center;justify-content:center;">'
    f'<span class="jp" style="color:#fff;font-size:13px;font-weight:900;text-align:center;">候補者<br>体験</span></div>'
    f'<div class="jp" style="position:absolute;left:50%;top:30px;transform:translateX(-50%);font-size:13px;font-weight:700;color:{GRAY};">市場・ブランド</div>'
    f'<div class="jp" style="position:absolute;left:50%;top:92px;transform:translateX(-50%);font-size:13px;font-weight:700;">選考プロセス</div>'
    f'<div class="jp" style="position:absolute;left:50%;top:152px;transform:translateX(-50%);font-size:13px;font-weight:700;">面接・面談</div></div>')

add("Structure ／ 構造", "ツリー（分解）",
    f'<div style="display:flex;align-items:center;gap:50px;padding:40px 40px 0;">'
    f'<div style="background:{INK};color:#fff;padding:26px 30px;" class="jp"><b style="font-size:17px;">採用成功</b><br><span style="font-size:12.5px;color:#B9BDC4;">承諾数=12名</span></div>'
    f'<svg width="60" height="300"><path d="M0,150 C30,150 30,40 60,40 M0,150 C30,150 30,150 60,150 M0,150 C30,150 30,260 60,260" stroke="{NEU}" stroke-width="2" fill="none"/></svg>'
    f'<div style="display:flex;flex-direction:column;gap:26px;">' +
    "".join(f'<div style="border-left:3px solid {RED if hi else NEU};padding:12px 22px;background:rgba(21,23,28,.03);" class="jp">'
            f'<b style="font-size:15px;">{l}</b>　<span class="num" style="color:{RED if hi else GRAY};font-weight:700;">{v}</span>'
            f'<div style="font-size:12.5px;color:{GRAY};margin-top:4px;">{d}</div></div>'
            for l, v, d, hi in [("母集団", "×29", "スカウト・媒体・リファラル", 1), ("転換率", "+61%", "構造化面接・CX設計", 0), ("承諾率", "83%", "C.L.O.S.E.クロージング", 0)]) + '</div></div>')

add("Structure ／ 構造", "組織図ライト",
    f'<div style="text-align:center;padding-top:24px;">'
    f'<div style="display:inline-block;background:{INK};color:#fff;padding:16px 34px;" class="jp"><b>専任PM</b><span style="font-size:12px;color:#B9BDC4;">　週次で貴社と直結</span></div>'
    f'<svg width="700" height="46"><path d="M350,0 L350,20 M350,20 L60,20 L60,46 M350,20 L350,46 M350,20 L640,20 L640,46" stroke="{NEU}" stroke-width="2" fill="none"/></svg>'
    f'<div style="display:flex;justify-content:center;gap:120px;">' +
    "".join(f'<div style="border:1.5px solid {RED if hi else NEU};padding:16px 26px;background:{PAPER};" class="jp">'
            f'<b style="font-size:14.5px;color:{RED if hi else INK};">{l}</b><div style="font-size:12px;color:{GRAY};margin-top:4px;">{d}</div></div>'
            for l, d, hi in [("スカウトチーム", "配信・返信対応", 0), ("選考オペレーション", "日程・進行管理", 0), ("クロージング", "承諾・辞退防止", 1)]) + '</div></div>')

# ============ G. 比較 ============
add("Compare ／ 比較", "Before/Afterパネル",
    f'<div style="display:flex;gap:26px;padding-top:40px;">'
    f'<div style="flex:1;border:1px solid {HL};padding:34px;">'
    f'<div class="en" style="font-size:11px;color:{GRAY};font-weight:700;">Before</div>'
    f'<div class="jp" style="font-size:19px;font-weight:900;margin-top:12px;color:#4A4F57;">エージェント任せの「待ち」採用</div>'
    f'<div class="jp" style="font-size:14px;color:{GRAY};margin-top:12px;line-height:1.9;">紹介料は年700万円。それでも年4名が限界で、担当は疲弊。</div></div>'
    f'<div style="align-self:center;" class="num"><svg width="54" height="34"><line x1="0" y1="17" x2="38" y2="17" stroke="{RED}" stroke-width="3"/><path d="M38,8 L54,17 L38,26 Z" fill="{RED}"/></svg></div>'
    f'<div style="flex:1;background:{INK};padding:34px;color:#fff;">'
    f'<div class="en" style="font-size:11px;color:{RED.replace("#AF","#E5")};font-weight:700;">After</div>'
    f'<div class="jp" style="font-size:19px;font-weight:900;margin-top:12px;">構造で勝つ「攻め」の採用</div>'
    f'<div class="jp" style="font-size:14px;color:#B9BDC4;margin-top:12px;line-height:1.9;">母集団を自社資産化。コスト−18%で採用数+25%。</div></div></div>')

add("Compare ／ 比較", "VS表（2社正対）",
    f'<div style="margin-top:30px;border:1px solid {HL};">'
    f'<div style="display:flex;background:rgba(21,23,28,.03);border-bottom:1px solid {HL};">'
    f'<div style="width:240px;padding:16px 22px;"></div>'
    f'<div class="jp" style="flex:1;padding:16px;text-align:center;font-weight:700;color:{GRAY};">一般的なRPO</div>'
    f'<div class="jp" style="flex:1;padding:16px;text-align:center;font-weight:900;background:{RED};color:#fff;">とくもり採用代行</div></div>' +
    "".join(f'<div style="display:flex;border-bottom:1px solid {HL};">'
            f'<div class="jp" style="width:240px;padding:15px 22px;font-size:14px;font-weight:700;">{l}</div>'
            f'<div class="jp" style="flex:1;padding:15px;text-align:center;font-size:14px;color:{GRAY};">{a}</div>'
            f'<div class="jp" style="flex:1;padding:15px;text-align:center;font-size:14px;font-weight:700;background:rgba(175,50,44,.05);">{b}</div></div>'
            for l, a, b in [("戦略設計", "△ 別料金", "◎ 標準内"), ("学術的根拠", "×", "◎ Sackett等に準拠"),
                            ("実働範囲", "○ 事務中心", "◎ スカウト〜面談"), ("型化・引き継ぎ", "×", "◎ FMT納品")]) + '</div>')

add("Compare ／ 比較", "ハービーボール表",
    f'<div style="margin-top:36px;">' +
    "".join(f'<div style="display:flex;align-items:center;border-bottom:1px solid {HL};padding:17px 0;">'
            f'<div class="jp" style="width:280px;font-size:14.5px;font-weight:700;">{l}</div>' +
            "".join(f'<div style="flex:1;display:flex;justify-content:center;">'
                    f'<div style="width:26px;height:26px;border-radius:50%;border:2px solid {RED if v==4 else NEU};'
                    f'background:conic-gradient({RED if v>=3 else "#9AA0A8"} 0deg {v*90}deg, transparent {v*90}deg 360deg);"></div></div>'
                    for v in row) + '</div>'
            for l, row in [("戦略設計", [1, 2, 4]), ("実働カバレッジ", [2, 3, 4]), ("データ・学術性", [1, 1, 4]), ("価格柔軟性", [3, 2, 3])]) +
    f'<div style="display:flex;padding-top:14px;"><div style="width:280px;"></div>' +
    "".join(f'<div class="jp" style="flex:1;text-align:center;font-size:13px;color:{GRAY};font-weight:700;">{n}</div>' for n in ["派遣", "一般RPO", "とくもり"]) + '</div></div>')

add("Compare ／ 比較", "プライシング3枚",
    f'<div style="display:flex;gap:24px;padding-top:26px;">' +
    "".join(f'<div style="flex:1;border:{"2px solid "+RED if rec else "1px solid "+HL};padding:30px;position:relative;background:{PAPER};">'
            + (f'<div class="jp" style="position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:{RED};color:#fff;font-size:12px;font-weight:900;padding:4px 16px;">おすすめ</div>' if rec else "")
            + f'<div class="jp" style="font-size:16px;font-weight:900;">{n}</div>'
            f'<div style="margin-top:14px;"><span class="num" style="font-size:44px;font-weight:900;color:{RED if rec else INK};">{p}</span>'
            f'<span class="jp" style="font-size:14px;color:{GRAY};">万円/月</span></div>'
            f'<div style="border-top:1px solid {HL};margin-top:18px;padding-top:16px;">' +
            "".join(f'<div class="jp" style="font-size:13.5px;padding:5px 0;color:#3A3F47;">・{f}</div>' for f in fs) + '</div></div>'
            for n, p, rec, fs in [("ライト", "20", 0, ["実働代行のみ", "月50h", "予算優先"]),
                                  ("ベーシック", "35", 1, ["実行主体+戦略伴走", "月100h", "週次レポート"]),
                                  ("プレミアム", "80", 0, ["戦略×実働×AI全込", "フル稼働", "採用チーム化"])]) + '</div>')

add("Compare ／ 比較", "◎○×チェック表",
    f'<div style="margin-top:30px;border-top:2px solid {INK};">' +
    "".join(f'<div style="display:flex;align-items:center;border-bottom:1px solid {HL};">'
            f'<div class="jp" style="width:300px;padding:16px 8px;font-size:14.5px;font-weight:700;">{l}</div>' +
            "".join(f'<div class="num jp" style="flex:1;text-align:center;padding:14px 0;font-size:{20 if v=="◎" else 16}px;font-weight:900;'
                    f'color:{RED if v=="◎" else (INK if v=="○" else NEU)};">{v}</div>' for v in row) + '</div>'
            for l, row in [("媒体運用", ["◎", "○", "×"]), ("スカウト代行", ["◎", "○", "×"]), ("面接設計", ["◎", "×", "○"]), ("定着支援", ["○", "×", "×"])]) +
    f'<div style="display:flex;padding-top:12px;"><div style="width:300px;"></div>' +
    "".join(f'<div class="jp" style="flex:1;text-align:center;font-size:13px;color:{GRAY};font-weight:700;">{n}</div>' for n in ["とくもり", "RPO他社", "コンサル"]) + '</div></div>')

add("Compare ／ 比較", "メリット/デメリット",
    f'<div style="display:flex;gap:1px;background:{HL};margin-top:36px;">'
    f'<div style="flex:1;background:{PAPER};padding:34px;">'
    f'<div class="jp" style="font-size:15px;font-weight:900;color:{RED};border-bottom:2px solid {RED};padding-bottom:10px;">内製化のメリット</div>' +
    "".join(f'<div class="jp" style="font-size:14px;padding:12px 0;border-bottom:1px solid {HL};color:#3A3F47;">＋ {t}</div>'
            for t in ["ノウハウが社内に蓄積", "候補者との距離が近い", "長期では固定費化できる"]) +
    f'</div><div style="flex:1;background:{PAPER};padding:34px;">'
    f'<div class="jp" style="font-size:15px;font-weight:900;color:{GRAY};border-bottom:2px solid {NEU};padding-bottom:10px;">内製化のデメリット</div>' +
    "".join(f'<div class="jp" style="font-size:14px;padding:12px 0;border-bottom:1px solid {HL};color:{GRAY};">− {t}</div>'
            for t in ["立ち上げに12ヶ月以上", "採用のプロ人材が必要", "工数が経営を圧迫"]) + '</div></div>')

# ============ H. 関係 ============
add("Relation ／ 関係", "ハブ&スポーク",
    f'<div style="position:relative;width:640px;height:420px;margin:10px auto 0;">'
    f'<svg width="640" height="420" style="position:absolute;">' +
    "".join(f'<line x1="320" y1="210" x2="{x}" y2="{y}" stroke="{NEU}" stroke-width="1.5"/>' for x, y in [(110, 80), (530, 80), (80, 320), (560, 320), (320, 30)]) +
    f'</svg><div style="position:absolute;left:245px;top:150px;width:150px;height:120px;background:{RED};display:flex;align-items:center;justify-content:center;">'
    f'<span class="jp" style="color:#fff;font-weight:900;font-size:16px;text-align:center;">専任PM<br><span style="font-size:11.5px;font-weight:400;">単一窓口</span></span></div>' +
    "".join(f'<div style="position:absolute;left:{x-70}px;top:{y-26}px;width:140px;border:1.5px solid {NEU};background:{PAPER};padding:10px;text-align:center;" class="jp">'
            f'<b style="font-size:13.5px;">{l}</b></div>' for x, y, l in [(110, 80, "媒体各社"), (530, 80, "スカウト運用"), (80, 320, "エージェント"), (560, 320, "面接官"), (320, 30, "貴社 人事")]) + '</div>')

add("Relation ／ 関係", "二面プラットフォーム",
    f'<div style="display:flex;align-items:center;gap:0;padding:70px 20px 0;">'
    f'<div style="flex:1;text-align:right;padding-right:30px;">' +
    "".join(f'<div class="jp" style="display:inline-block;clear:both;border:1.5px solid {NEU};padding:10px 18px;margin:6px 0;font-size:13.5px;font-weight:700;">{t}</div><br>' for t in ["求職者", "転職潜在層", "学生"]) +
    f'</div><svg width="90" height="120"><path d="M6,60 L84,60" stroke="{GRAY}" stroke-width="2"/><path d="M76,52 L90,60 L76,68Z" fill="{GRAY}"/><path d="M14,52 L0,60 L14,68Z" fill="{GRAY}"/></svg>'
    f'<div style="width:250px;background:{INK};color:#fff;text-align:center;padding:38px 20px;">'
    f'<div class="jp" style="font-weight:900;font-size:17px;">とくもり<br>採用プラットフォーム</div>'
    f'<div class="jp" style="font-size:12px;color:#B9BDC4;margin-top:8px;">25万人リーチ × 選考設計</div></div>'
    f'<svg width="90" height="120"><path d="M6,60 L84,60" stroke="{GRAY}" stroke-width="2"/><path d="M76,52 L90,60 L76,68Z" fill="{GRAY}"/><path d="M14,52 L0,60 L14,68Z" fill="{GRAY}"/></svg>'
    f'<div style="flex:1;padding-left:30px;">' +
    "".join(f'<div class="jp" style="display:inline-block;clear:both;border:1.5px solid {RED};color:{RED};padding:10px 18px;margin:6px 0;font-size:13.5px;font-weight:700;">{t}</div><br>' for t in ["貴社（採用企業）", "300社の取引先"]) + '</div></div>')

add("Relation ／ 関係", "収束（多→1）",
    f'<div style="display:flex;align-items:center;padding:50px 40px 0;">'
    f'<div style="display:flex;flex-direction:column;gap:16px;">' +
    "".join(f'<div class="jp" style="border:1.5px solid {NEU};padding:12px 22px;font-size:14px;font-weight:700;background:{PAPER};">{t}</div>'
            for t in ["ダイレクトスカウト", "求人媒体 5社", "リファラル設計", "SNS・オウンド"]) +
    f'</div><svg width="180" height="300"><path d="M10,40 C90,40 90,150 170,150 M10,115 C90,115 90,150 170,150 M10,185 C90,185 90,150 170,150 M10,260 C90,260 90,150 170,150" stroke="{NEU}" stroke-width="2" fill="none"/><path d="M162,142 L178,150 L162,158Z" fill="{RED}"/></svg>'
    f'<div style="background:{RED};color:#fff;padding:44px 40px;text-align:center;">'
    f'<div class="num" style="font-size:52px;font-weight:900;">742<span style="font-size:22px;">名</span></div>'
    f'<div class="jp" style="font-size:13.5px;margin-top:6px;">統合母集団<br>（単一パイプライン管理）</div></div></div>')

# ============ I. 表 ============
add("Table ／ 表", "クリーン表（ハイライト行）",
    f'<div style="margin-top:26px;border-top:2px solid {INK};">'
    f'<div style="display:flex;border-bottom:1.5px solid {INK};" class="jp">' +
    "".join(f'<div style="flex:{f};padding:14px 10px;font-size:13px;font-weight:900;color:{GRAY};">{h}</div>'
            for h, f in [("フェーズ", 2), ("主要KPI", 2), ("担当", 1.4), ("頻度", 1), ("状態", 1)]) + '</div>' +
    "".join(f'<div style="display:flex;border-bottom:1px solid {HL};{"background:rgba(175,50,44,.05);" if hi else ""}" class="jp">'
            f'<div style="flex:2;padding:15px 10px;font-size:14px;font-weight:700;">{a}</div>'
            f'<div style="flex:2;padding:15px 10px;font-size:14px;color:#3A3F47;">{b}</div>'
            f'<div style="flex:1.4;padding:15px 10px;font-size:14px;color:{GRAY};">{c}</div>'
            f'<div style="flex:1;padding:15px 10px;font-size:14px;color:{GRAY};">{d}</div>'
            f'<div class="num jp" style="flex:1;padding:15px 10px;font-size:13px;font-weight:900;color:{RED if hi else GRAY};">{e}</div></div>'
            for a, b, c, d, e, hi in [("母集団形成", "エントリー数", "とくもり", "日次", "▲ 進行中", 1),
                                      ("書類・日程", "通過率/設定率", "とくもり", "日次", "順調", 0),
                                      ("面接", "評価一致率", "貴社+支援", "週次", "順調", 0),
                                      ("クロージング", "承諾率", "共同", "週次", "順調", 0)]) + '</div>')

add("Table ／ 表", "ヒートマップ表",
    f'<div style="margin-top:30px;">'
    f'<div style="display:flex;padding-left:190px;" class="jp">' +
    "".join(f'<div style="flex:1;text-align:center;font-size:13px;color:{GRAY};font-weight:700;padding-bottom:10px;">{m}</div>' for m in ["4月", "5月", "6月", "7月", "8月", "9月"]) + '</div>' +
    "".join(f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'<div class="jp" style="width:190px;font-size:14px;font-weight:700;">{l}</div>' +
            "".join(f'<div style="flex:1;margin:0 3px;height:54px;background:rgba(175,50,44,{v});display:flex;align-items:center;justify-content:center;">'
                    f'<span class="num" style="font-size:14px;font-weight:700;color:{"#fff" if v>=.55 else INK};">{int(v*100)}</span></div>' for v in row) + '</div>'
            for l, row in [("スカウト返信率", [.15, .25, .3, .45, .6, .75]), ("面談設定率", [.2, .3, .45, .5, .65, .8]), ("承諾率", [.1, .2, .35, .5, .7, .95])]) +
    f'<div class="jp" style="font-size:12px;color:{GRAY};margin-top:10px;">数値=指数（開始月比・100=最大）。色が濃いほど改善。</div></div>')

def main():
    paths = []
    for num, cat, name, inner in FIGS:
        html = slide(num, cat, name, inner)
        p = "/tmp/figcat_%02d.html" % num
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    print("figs:", len(paths))
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ ② 図解カタログ50",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("FIG CATALOG:", url)


if __name__ == "__main__":
    main()
