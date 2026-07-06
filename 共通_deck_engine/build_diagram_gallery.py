#!/usr/bin/env python3
"""作れる図タイプのサンプル・ギャラリー（ブランド統一）。HTML/SVGで多彩な図を一発描画できることの実証。
出力 /tmp/gallery.html。"""
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700;900&'
         'family=Shippori+Mincho+B1:wght@800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet"/>')
RED = "#AF322C"; INK = "#1A1714"; SUB = "#7C736D"; GRY = "#C7BFB9"; LRED = "#F6ECEA"

# --- 各図(SVG/HTML inner) ---
donut = """<svg viewBox="0 0 300 200"><g transform="translate(95,100)">
<circle r="62" fill="none" stroke="#EFEBE8" stroke-width="34"/>
<circle r="62" fill="none" stroke="%s" stroke-width="34" stroke-dasharray="175 215" transform="rotate(-90)"/>
<circle r="62" fill="none" stroke="%s" stroke-width="34" stroke-dasharray="117 273" stroke-dashoffset="-175" transform="rotate(-90)"/>
<circle r="62" fill="none" stroke="%s" stroke-width="34" stroke-dasharray="98 292" stroke-dashoffset="-292" transform="rotate(-90)"/>
<text y="7" text-anchor="middle" font-size="22" font-weight="900" fill="%s">45%%</text></g>
<g font-size="13" font-family="Noto Sans JP"><rect x="190" y="56" width="13" height="13" rx="3" fill="%s"/><text x="209" y="67">中核 45%%</text>
<rect x="190" y="86" width="13" height="13" rx="3" fill="%s"/><text x="209" y="97">入口 30%%</text>
<rect x="190" y="116" width="13" height="13" rx="3" fill="#D9D2CE"/><text x="209" y="127" fill="%s">出口 25%%</text></g></svg>""" % (RED, INK, GRY, RED, RED, INK, SUB)

matrix = """<svg viewBox="0 0 300 200">
<line x1="40" y1="20" x2="40" y2="175" stroke="#D9D2CE" stroke-width="2"/><line x1="40" y1="175" x2="280" y2="175" stroke="#D9D2CE" stroke-width="2"/>
<line x1="160" y1="20" x2="160" y2="175" stroke="#EFEBE8" stroke-width="1.5"/><line x1="40" y1="97" x2="280" y2="97" stroke="#EFEBE8" stroke-width="1.5"/>
<circle cx="220" cy="55" r="12" fill="%s"/><text x="220" y="38" text-anchor="middle" font-size="12" font-weight="700" fill="%s">最優先</text>
<circle cx="100" cy="60" r="9" fill="#C7BFB9"/><circle cx="225" cy="135" r="9" fill="#C7BFB9"/><circle cx="95" cy="140" r="8" fill="#E0DAD6"/>
<text x="34" y="30" text-anchor="end" font-size="11" fill="%s">高</text><text x="34" y="172" text-anchor="end" font-size="11" fill="%s">低</text>
<text x="150" y="195" text-anchor="middle" font-size="12" fill="%s">緊急度 →</text>
<text x="20" y="100" text-anchor="middle" font-size="12" fill="%s" transform="rotate(-90 20 100)">重要度 →</text></svg>""" % (RED, RED, SUB, SUB, SUB, SUB)

funnel = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP">
<polygon points="40,28 260,28 232,58 68,58" fill="%s"/><text x="150" y="48" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">認知 100%%</text>
<polygon points="70,64 230,64 205,94 95,94" fill="#C0463F"/><text x="150" y="84" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">応募 42%%</text>
<polygon points="97,100 203,100 180,130 120,130" fill="#D08079"/><text x="150" y="120" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">面談 18%%</text>
<polygon points="122,136 178,136 160,168 140,168" fill="#1A1714"/><text x="150" y="156" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">承諾 6%%</text></g></svg>""" % (RED,)

cycle = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" font-size="12" font-weight="700">
<defs><marker id="ar" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="%s"/></marker></defs>
<path d="M150,40 A60,60 0 0 1 210,100" fill="none" stroke="%s" stroke-width="3" marker-end="url(#ar)"/>
<path d="M210,100 A60,60 0 0 1 150,160" fill="none" stroke="%s" stroke-width="3" marker-end="url(#ar)"/>
<path d="M150,160 A60,60 0 0 1 90,100" fill="none" stroke="%s" stroke-width="3" marker-end="url(#ar)"/>
<path d="M90,100 A60,60 0 0 1 150,40" fill="none" stroke="%s" stroke-width="3" marker-end="url(#ar)"/>
<circle cx="150" cy="40" r="22" fill="%s"/><text x="150" y="44" text-anchor="middle" fill="#fff">計画</text>
<circle cx="210" cy="100" r="22" fill="%s"/><text x="210" y="104" text-anchor="middle" fill="#fff">実行</text>
<circle cx="150" cy="160" r="22" fill="%s"/><text x="150" y="164" text-anchor="middle" fill="#fff">評価</text>
<circle cx="90" cy="100" r="22" fill="%s"/><text x="90" y="104" text-anchor="middle" fill="#fff">改善</text></g></svg>""" % (RED, GRY, GRY, GRY, GRY, RED, INK, RED, INK)

radar = """<svg viewBox="0 0 300 200"><g transform="translate(150,105)">
<polygon points="0,-78 74,-24 46,63 -46,63 -74,-24" fill="none" stroke="#EFEBE8" stroke-width="1.5"/>
<polygon points="0,-52 49,-16 30,42 -30,42 -49,-16" fill="none" stroke="#EFEBE8" stroke-width="1.5"/>
<polygon points="0,-66 56,-8 38,55 -20,38 -40,-30" fill="%s33" stroke="%s" stroke-width="2.5"/>
<g font-size="11" fill="%s" font-family="Noto Sans JP"><text x="0" y="-84" text-anchor="middle">主体性</text><text x="86" y="-22">対人力</text>
<text x="52" y="78">実行力</text><text x="-52" y="78" text-anchor="end">学習力</text><text x="-86" y="-22" text-anchor="end">分析力</text></g></g></svg>""" % (RED, RED, SUB)

hbar = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" font-size="12">
<text x="8" y="42">面談数</text><rect x="80" y="30" width="190" height="16" rx="3" fill="%s"/><text x="276" y="43" text-anchor="end" font-size="11" fill="#fff" font-weight="700">120</text>
<text x="8" y="80">紹介数</text><rect x="80" y="68" width="120" height="16" rx="3" fill="#C0463F"/><text x="206" y="81" font-size="11" fill="%s">68</text>
<text x="8" y="118">面接</text><rect x="80" y="106" width="70" height="16" rx="3" fill="#D08079"/><text x="156" y="119" font-size="11" fill="%s">31</text>
<text x="8" y="156">承諾</text><rect x="80" y="144" width="26" height="16" rx="3" fill="%s"/><text x="112" y="157" font-size="11" fill="%s">9</text></g></svg>""" % (RED, SUB, SUB, INK, SUB)

CARDS = [("円・ドーナツ", "構成比", donut), ("2×2マトリクス", "優先度・ポジショニング", matrix),
         ("ファネル", "選考・採用フロー", funnel), ("サイクル", "PDCA・反復", cycle),
         ("レーダー", "スキル・多軸評価", radar), ("横棒ランキング", "比較・推移", hbar)]

cards_html = "".join(
    '<div class="card"><div class="ct"><span class="cn">%s</span><span class="cd">%s</span></div><div class="fig">%s</div></div>' % (n, d, s)
    for n, d, s in CARDS)

html = """<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"/>%s
<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;background:#fff;font-family:"Noto Sans JP",sans-serif;color:%s;}
.wrap{padding:34px 44px 40px;}
.h{font-family:"IBM Plex Mono",monospace;color:%s;font-weight:600;font-size:13px;letter-spacing:.14em;}
.t{font-family:"Shippori Mincho B1",serif;font-weight:800;font-size:30px;margin:6px 0 2px;}
.s{color:%s;font-size:14px;margin-bottom:20px;}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}
.card{border:1px solid #E6E3E1;border-radius:14px;padding:14px 16px;box-shadow:0 6px 18px rgba(20,16,12,.05);}
.ct{display:flex;align-items:baseline;gap:8px;border-bottom:1.5px solid %s;padding-bottom:5px;margin-bottom:4px;}
.cn{font-weight:900;font-size:15px;}.cd{font-size:11px;color:%s;}
.fig{height:200px;}.fig svg{width:100%%;height:100%%;}
</style></head><body><div class="wrap">
<div class="h">DIAGRAM LIBRARY ・ 作れる図タイプ</div>
<div class="t">データを渡せば、いろんな“図”を一発で</div>
<div class="s">ブランド統一（赤＋明朝＋等幅）。すべてHTML/SVG＝被りゼロ・編集はコード/データ側。これは一例で他にもピラミッド・タイムライン・ガント・相関図・ベン図 等も可。</div>
<div class="grid">%s</div></div></body></html>""" % (FONTS, INK, RED, SUB, RED, SUB, cards_html)

open("/tmp/gallery.html", "w", encoding="utf-8").write(html)
print("wrote /tmp/gallery.html | bytes:", len(html))
