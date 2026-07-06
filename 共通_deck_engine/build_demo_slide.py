#!/usr/bin/env python3
"""新卒研修スライドのデモ（A1/A3 事業理解）をHTMLで高品質生成。

brand.py のトークンを使い、コンサル級のプロセス図1枚を作る。
出力 /tmp/demo_slide.html → html_to_slide.py で Google Slides に画像挿入（ハイブリッド）。
"""
import os
import brand as B

STAGES = [
    ("01", "入口", "母集団形成", ["新卒メディア・スカウト", "学校/紹介ルート", "説明会・送客"]),
    ("02", "中核", "面談・マッチング", ["キャリア面談・課題整理", "求人マッチング・推薦", "選考支援・対策"]),
    ("03", "出口", "内定者フォロー", ["内定承諾の意思決定支援", "入社前フォロー", "入社後の定着支援"]),
]

html = """<!DOCTYPE html>
<html lang="ja"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>事業理解デモ｜Tokumori</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Shippori+Mincho+B1:wght@600;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
  :root{--red:#%(RED)s;--redd:#%(REDD)s;--ink:#%(INK)s;--sub:#%(SUB)s;--rule:#%(RULE)s;--panel:#%(PANEL)s;
    --lred:#%(LRED)s;--paper:#%(PAPER)s;--dark:#%(INKDK)s;--faint:#%(FAINT2)s;}
  *{box-sizing:border-box;}
  html,body{margin:0;background:#fff;font-family:"%(BODY)s",sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased;}
  .stage{min-height:100vh;display:grid;place-items:center;}
  .board{width:1280px;height:720px;background:var(--paper);position:relative;display:flex;flex-direction:column;overflow:hidden;}
  .board::before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:var(--red);}
  .hd{padding:34px 52px 0;}
  .kick{font-family:"%(MONO)s",monospace;color:var(--red);font-weight:600;font-size:13px;letter-spacing:.14em;}
  .title{font-family:"%(DISP)s",serif;font-weight:800;font-size:33px;line-height:1.14;margin:7px 0 4px;letter-spacing:.01em;}
  .title b{color:var(--red);}
  .sub{color:var(--sub);font-size:14px;}
  .rule{height:2px;width:64px;background:var(--red);margin:13px 52px 0;}
  .flow{flex:1;display:flex;flex-direction:column;justify-content:center;gap:18px;padding:8px 52px 0;}
  .stages{display:grid;grid-template-columns:1fr 28px 1fr 28px 1fr;align-items:stretch;}
  .arr{display:grid;place-items:center;color:var(--red);font-size:26px;font-weight:700;}
  .card{background:#fff;border:1px solid var(--rule);border-radius:12px;padding:18px 20px;box-shadow:0 6px 20px rgba(20,16,12,.05);display:flex;flex-direction:column;gap:9px;}
  .card.core{border-color:var(--red);box-shadow:0 10px 26px rgba(175,50,44,.13);}
  .ctop{display:flex;align-items:center;gap:9px;}
  .no{font-family:"%(MONO)s",monospace;font-size:11px;font-weight:600;color:#fff;background:var(--ink);border-radius:5px;padding:2px 7px;}
  .card.core .no{background:var(--red);}
  .stg{font-family:"%(MONO)s",monospace;font-size:11px;color:var(--sub);letter-spacing:.1em;}
  .cname{font-weight:900;font-size:19px;line-height:1.1;}
  .card.core .cname{color:var(--red);}
  .li{display:flex;gap:8px;align-items:flex-start;font-size:13px;line-height:1.45;}
  .li::before{content:"";width:6px;height:6px;border-radius:99px;background:var(--red);margin-top:7px;flex:none;}
  .base{display:flex;align-items:center;gap:16px;background:var(--ink);color:#fff;border-radius:12px;padding:14px 22px;}
  .base .blab{font-family:"%(DISP)s",serif;font-weight:800;font-size:16px;flex:none;}
  .base .bitems{display:flex;gap:10px;flex-wrap:wrap;}
  .chipb{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:5px 13px;font-size:12.5px;font-weight:500;}
  .rev{position:absolute;top:34px;right:52px;text-align:right;}
  .rev .rl{font-family:"%(MONO)s",monospace;font-size:10px;color:var(--faint);letter-spacing:.08em;}
  .rev .rv{font-family:"%(DISP)s",serif;font-weight:800;font-size:15px;color:var(--red);margin-top:2px;}
  .foot{background:var(--dark);padding:13px 52px;display:flex;align-items:center;gap:18px;}
  .foot .lab{font-family:"%(MONO)s",monospace;color:#E9B7B2;font-weight:600;font-size:11px;letter-spacing:.1em;flex:none;}
  .foot .txt{font-family:"%(DISP)s",serif;font-weight:600;color:#F4F0EE;font-size:14.5px;line-height:1.5;}
  .foot .txt b{color:#fff;}
  .src{position:absolute;bottom:3px;left:52px;font-family:"%(MONO)s",monospace;font-size:8px;color:rgba(255,255,255,.5);}
</style></head>
<body class="exp">
<div class="stage"><div class="board">
  <div class="hd">
    <div class="kick">A1・A3 ・ 事業理解</div>
    <div class="title">TOKUMORIの新卒紹介は <b>「入口 → 中核 → 出口」</b> を “データ基盤” が支える</div>
    <div class="sub">求職者一人ひとりの意思決定に伴走し、内定承諾＝成果で収益化するビジネスモデル</div>
    <div class="rev"><div class="rl">REVENUE MODEL</div><div class="rv">内定承諾で課金（成果報酬）</div></div>
  </div>
  <div class="rule"></div>
  <div class="flow">
    <div class="stages">__STAGES__</div>
    <div class="base">
      <div class="blab">基盤</div>
      <div class="bitems"><span class="chipb">データ / Salesforce</span><span class="chipb">AI活用（面談準備・紹介文・リサーチ）</span><span class="chipb">業界・職種知識</span></div>
    </div>
  </div>
  <div class="foot">
    <div class="lab">KEY TAKEAWAY</div>
    <div class="txt">売上は<b>「内定承諾」</b>で発生＝<b>中核（面談・マッチング）の質</b>が事業の生命線。基盤（SF/AI/業界知識）が全工程の生産性を決める。</div>
  </div>
  <div class="src">出典：Tokumori事業モデル（新卒紹介＝内定承諾課金）／社内研修 A1・A3。配布前に最新の数値・条件を要確認。</div>
</div></div>
</body></html>
""" % vars(B)

cards = []
for no, stg, name, items in STAGES:
    lis = "".join('<div class="li">%s</div>' % it for it in items)
    core = " core" if stg == "中核" else ""
    cards.append('<div class="card%s"><div class="ctop"><span class="no">%s</span><span class="stg">%s</span></div>'
                 '<div class="cname">%s</div>%s</div>' % (core, no, stg, name, lis))
flow = cards[0] + '<div class="arr">›</div>' + cards[1] + '<div class="arr">›</div>' + cards[2]
html = html.replace("__STAGES__", flow)

open("/tmp/demo_slide.html", "w", encoding="utf-8").write(html)
print("wrote /tmp/demo_slide.html | bytes:", len(html))
