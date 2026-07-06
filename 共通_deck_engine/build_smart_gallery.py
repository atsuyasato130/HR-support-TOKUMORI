#!/usr/bin/env python3
"""“スマートな図解”洗練版ギャラリー。引き算の美学：余白・1アクセント・細線・洗練タイポ。出力 /tmp/smart.html"""
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&'
         'family=Shippori+Mincho+B1:wght@800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet"/>')

donut = """<svg viewBox="0 0 300 200"><g transform="translate(108,100)">
<circle r="64" fill="none" stroke="#EFEBE8" stroke-width="11"/>
<circle r="64" fill="none" stroke="#AF322C" stroke-width="11" stroke-linecap="round" stroke-dasharray="181 221" transform="rotate(-90)"/>
<text y="-1" text-anchor="middle" font-size="31" font-weight="800" font-family="Shippori Mincho B1" fill="#1A1714">45%</text>
<text y="20" text-anchor="middle" font-size="10" letter-spacing="2" fill="#9A938E" font-family="IBM Plex Mono">CORE</text></g>
<g font-family="IBM Plex Mono" font-size="11" fill="#7C736D"><text x="206" y="86">中核　45</text><text x="206" y="110">入口　30</text><text x="206" y="134">出口　25</text>
<rect x="186" y="78" width="3" height="10" fill="#AF322C"/><rect x="186" y="102" width="3" height="10" fill="#1A1714"/><rect x="186" y="126" width="3" height="10" fill="#D9D2CE"/></g></svg>"""

funnel = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP">
<rect x="30" y="36" width="200" height="20" rx="3" fill="#EFE7E4"/><text x="38" y="51" font-size="11" fill="#1A1714">認知</text><text x="270" y="51" font-size="11" font-family="IBM Plex Mono" fill="#9A938E" text-anchor="end">100</text>
<rect x="30" y="74" width="150" height="20" rx="3" fill="#E4D2CE"/><text x="38" y="89" font-size="11" fill="#1A1714">応募</text><text x="270" y="89" font-size="11" font-family="IBM Plex Mono" fill="#9A938E" text-anchor="end">42</text>
<rect x="30" y="112" width="92" height="20" rx="3" fill="#D2A8A2"/><text x="38" y="127" font-size="11" fill="#1A1714">面談</text><text x="270" y="127" font-size="11" font-family="IBM Plex Mono" fill="#9A938E" text-anchor="end">18</text>
<rect x="30" y="150" width="44" height="20" rx="3" fill="#AF322C"/><text x="38" y="165" font-size="11" fill="#fff">承諾</text><text x="270" y="165" font-size="12" font-family="IBM Plex Mono" fill="#AF322C" text-anchor="end" font-weight="500">6</text></g></svg>"""

area = """<svg viewBox="0 0 300 200">
<path d="M30,150 C90,120 130,70 180,60 C220,52 250,40 275,36 L275,170 L30,170 Z" fill="#AF322C" opacity="0.06"/>
<path d="M30,150 C90,120 130,70 180,60 C220,52 250,40 275,36" fill="none" stroke="#AF322C" stroke-width="2.5" stroke-linecap="round"/>
<line x1="30" y1="170" x2="280" y2="170" stroke="#EFEBE8" stroke-width="1.5"/>
<circle cx="275" cy="36" r="4" fill="#AF322C"/><text x="272" y="28" font-size="12" font-family="IBM Plex Mono" fill="#AF322C" text-anchor="end" font-weight="500">+38%</text>
<g font-family="IBM Plex Mono" font-size="10" fill="#9A938E"><text x="30" y="186">Q1</text><text x="152" y="186" text-anchor="middle">Q3</text><text x="280" y="186" text-anchor="end">Q4</text></g></svg>"""

quad = """<svg viewBox="0 0 300 200">
<line x1="50" y1="28" x2="50" y2="172" stroke="#EFEBE8" stroke-width="1.5"/><line x1="50" y1="172" x2="280" y2="172" stroke="#EFEBE8" stroke-width="1.5"/>
<line x1="165" y1="28" x2="165" y2="172" stroke="#F4F1EF" stroke-width="1"/><line x1="50" y1="100" x2="280" y2="100" stroke="#F4F1EF" stroke-width="1"/>
<circle cx="100" cy="70" r="6" fill="#D9D2CE"/><circle cx="225" cy="140" r="6" fill="#D9D2CE"/><circle cx="105" cy="135" r="5" fill="#E0DAD6"/>
<circle cx="222" cy="58" r="9" fill="#fff" stroke="#AF322C" stroke-width="2.5"/><circle cx="222" cy="58" r="3.5" fill="#AF322C"/><text x="222" y="40" text-anchor="middle" font-size="11" font-family="IBM Plex Mono" fill="#AF322C">注力</text>
<g font-family="IBM Plex Mono" font-size="9" fill="#9A938E"><text x="46" y="32" text-anchor="end">高</text><text x="276" y="188" text-anchor="end">緊急度 →</text><text x="40" y="100" text-anchor="middle" transform="rotate(-90 40 100)">重要度 →</text></g></svg>"""

steps = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" text-anchor="middle">
<line x1="62" y1="92" x2="238" y2="92" stroke="#E6E3E1" stroke-width="2"/>
<circle cx="62" cy="92" r="17" fill="#fff" stroke="#1A1714" stroke-width="1.5"/><text x="62" y="97" font-size="12" font-family="IBM Plex Mono" fill="#1A1714">01</text><text x="62" y="132" font-size="11" fill="#7C736D">入口</text>
<circle cx="150" cy="92" r="20" fill="#AF322C"/><text x="150" y="97" font-size="13" font-family="IBM Plex Mono" fill="#fff">02</text><text x="150" y="135" font-size="11" font-weight="700" fill="#AF322C">中核</text>
<circle cx="238" cy="92" r="17" fill="#fff" stroke="#1A1714" stroke-width="1.5"/><text x="238" y="97" font-size="12" font-family="IBM Plex Mono" fill="#1A1714">03</text><text x="238" y="132" font-size="11" fill="#7C736D">出口</text></g></svg>"""

ba = """<svg viewBox="0 0 300 200"><defs><marker id="ba_ar" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#AF322C"/></marker></defs><g font-family="Noto Sans JP" text-anchor="middle">
<rect x="20" y="58" width="104" height="84" rx="10" fill="#FBFAF9" stroke="#E6E3E1"/>
<text x="72" y="48" font-size="10" letter-spacing="2" font-family="IBM Plex Mono" fill="#B3ABA5">BEFORE</text>
<text x="72" y="98" font-size="13" fill="#A49C96">なんとなく</text><text x="72" y="119" font-size="13" fill="#A49C96">就職する</text>
<line x1="132" y1="100" x2="166" y2="100" stroke="#AF322C" stroke-width="2" marker-end="url(#ba_ar)"/>
<rect x="176" y="58" width="104" height="84" rx="10" fill="#fff" stroke="#AF322C" stroke-width="1.5"/>
<text x="228" y="48" font-size="10" letter-spacing="2" font-family="IBM Plex Mono" fill="#AF322C">AFTER</text>
<text x="228" y="98" font-size="13" font-weight="700" fill="#1A1714">納得して選び</text><text x="228" y="119" font-size="13" font-weight="700" fill="#AF322C">活躍する</text></g></svg>"""

kpi = """<svg viewBox="0 0 300 200"><g font-family="Shippori Mincho B1" text-anchor="middle">
<text x="56" y="90" font-size="33" font-weight="800" fill="#AF322C">33.8%</text><rect x="28" y="103" width="56" height="2.5" fill="#AF322C"/><text x="56" y="126" font-size="11" font-family="Noto Sans JP" fill="#1A1714">3年離職率</text><text x="56" y="143" font-size="9" font-family="IBM Plex Mono" fill="#9A938E">厚労省</text>
<line x1="118" y1="62" x2="118" y2="128" stroke="#EFEBE8" stroke-width="1"/>
<text x="160" y="90" font-size="33" font-weight="800" fill="#1A1714">6%</text><rect x="140" y="103" width="40" height="2.5" fill="#D9D2CE"/><text x="160" y="126" font-size="11" font-family="Noto Sans JP" fill="#1A1714">熱意ある社員</text><text x="160" y="143" font-size="9" font-family="IBM Plex Mono" fill="#9A938E">Gallup</text>
<line x1="212" y1="62" x2="212" y2="128" stroke="#EFEBE8" stroke-width="1"/>
<text x="254" y="90" font-size="33" font-weight="800" fill="#1A1714">28位</text><rect x="230" y="103" width="48" height="2.5" fill="#D9D2CE"/><text x="254" y="126" font-size="11" font-family="Noto Sans JP" fill="#1A1714">労働生産性</text><text x="254" y="143" font-size="9" font-family="IBM Plex Mono" fill="#9A938E">OECD</text></g></svg>"""

CARDS = [("ドーナツ", "構成比", donut), ("ファネル", "選考フロー", funnel), ("Before → After", "課題 → 解決", ba),
         ("2×2マトリクス", "ポジショニング", quad), ("エリア／推移", "トレンド", area), ("KPIスタッツ", "主要指標", kpi)]
cards = "".join(f'<div class="card"><div class="ct"><span class="cn">{n}</span><span class="cd">{d}</span></div><div class="fig">{s}</div></div>' for n, d, s in CARDS)

html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"/>{FONTS}
<style>*{{margin:0;box-sizing:border-box;}}html,body{{width:1280px;background:#fff;font-family:"Noto Sans JP",sans-serif;color:#1A1714;}}
.wrap{{padding:36px 48px 44px;}}
.h{{font-family:"IBM Plex Mono",monospace;color:#AF322C;font-weight:500;font-size:12px;letter-spacing:.18em;}}
.t{{font-family:"Shippori Mincho B1",serif;font-weight:800;font-size:30px;margin:8px 0 3px;letter-spacing:.01em;}}
.s{{color:#9A938E;font-size:13px;margin-bottom:24px;}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px;}}
.card{{border:1px solid #F0ECE9;border-radius:16px;padding:16px 18px;}}
.ct{{display:flex;align-items:baseline;gap:9px;margin-bottom:6px;}}
.cn{{font-weight:700;font-size:14px;}}.cd{{font-size:10px;color:#B3ABA5;font-family:"IBM Plex Mono",monospace;letter-spacing:.06em;}}
.fig{{height:200px;}}.fig svg{{width:100%;height:100%;}}
</style></head><body><div class="wrap">
<div class="h">SMART DIAGRAMS ・ 洗練版</div>
<div class="t">引き算の美学 — 余白・1アクセント・細い線</div>
<div class="s">赤は1図につき主役1箇所のみ。塗りを減らし、線を細く、数値は等幅で。データインク比を上げた“スマートな”図解。</div>
<div class="grid">{cards}</div></div></body></html>"""
open("/tmp/smart.html", "w", encoding="utf-8").write(html)
print("wrote /tmp/smart.html | bytes:", len(html))
