#!/usr/bin/env python3
"""概念図・説明図（データでない図解）のサンプル・ギャラリー。HTML/SVGで構造/関係/流れを図解できる実証。出力 /tmp/concept.html"""
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700;900&'
         'family=Shippori+Mincho+B1:wght@800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet"/>')

swot = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP">
<rect x="18" y="18" width="128" height="78" rx="8" fill="#F6ECEA" stroke="#AF322C"/><text x="30" y="42" font-size="14" font-weight="900" fill="#AF322C">S 強み</text><text x="30" y="66" font-size="11" fill="#1A1714">提案力・対人・伴走</text>
<rect x="154" y="18" width="128" height="78" rx="8" fill="#fff" stroke="#E6E3E1"/><text x="166" y="42" font-size="14" font-weight="900" fill="#1A1714">W 弱み</text><text x="166" y="66" font-size="11" fill="#7C736D">経験・知名度</text>
<rect x="18" y="104" width="128" height="78" rx="8" fill="#fff" stroke="#E6E3E1"/><text x="30" y="128" font-size="14" font-weight="900" fill="#1A1714">O 機会</text><text x="30" y="152" font-size="11" fill="#7C736D">早期化・市場拡大</text>
<rect x="154" y="104" width="128" height="78" rx="8" fill="#fff" stroke="#E6E3E1"/><text x="166" y="128" font-size="14" font-weight="900" fill="#1A1714">T 脅威</text><text x="166" y="152" font-size="11" fill="#7C736D">競合・AI代替</text></g></svg>"""

pyramid = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" font-weight="700" text-anchor="middle">
<polygon points="150,22 198,82 102,82" fill="#AF322C"/><text x="150" y="64" font-size="13" fill="#fff">ビジョン</text>
<polygon points="100,86 200,86 230,142 70,142" fill="#C0463F"/><text x="150" y="120" font-size="14" fill="#fff">戦略</text>
<polygon points="68,146 232,146 262,186 38,186" fill="#1A1714"/><text x="150" y="172" font-size="14" fill="#fff">日々の実行・習慣</text></g></svg>"""

relation = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" font-size="12" font-weight="700" text-anchor="middle">
<line x1="150" y1="100" x2="62" y2="46" stroke="#D9D2CE" stroke-width="2"/><line x1="150" y1="100" x2="238" y2="46" stroke="#D9D2CE" stroke-width="2"/>
<line x1="150" y1="100" x2="62" y2="158" stroke="#D9D2CE" stroke-width="2"/><line x1="150" y1="100" x2="238" y2="158" stroke="#D9D2CE" stroke-width="2"/>
<circle cx="150" cy="100" r="36" fill="#AF322C"/><text x="150" y="105" fill="#fff">求職者</text>
<circle cx="62" cy="46" r="27" fill="#1A1714"/><text x="62" y="51" fill="#fff" font-size="11">企業</text>
<circle cx="238" cy="46" r="27" fill="#1A1714"/><text x="238" y="51" fill="#fff" font-size="11">CA</text>
<circle cx="62" cy="158" r="27" fill="#fff" stroke="#C7BFB9"/><text x="62" y="163" fill="#1A1714" font-size="11">媒体</text>
<circle cx="238" cy="158" r="27" fill="#fff" stroke="#C7BFB9"/><text x="238" y="163" fill="#1A1714" font-size="11">学校</text></g></svg>"""

ba = """<svg viewBox="0 0 300 200"><defs><marker id="ar2" markerWidth="10" markerHeight="10" refX="3" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#AF322C"/></marker></defs><g font-family="Noto Sans JP" text-anchor="middle">
<rect x="16" y="52" width="112" height="96" rx="10" fill="#fff" stroke="#C7BFB9"/><text x="72" y="46" font-size="11" fill="#7C736D">Before</text><text x="72" y="98" font-size="14" font-weight="700" fill="#7C736D">なんとなく</text><text x="72" y="120" font-size="14" font-weight="700" fill="#7C736D">就職 → 早期離職</text>
<line x1="134" y1="100" x2="168" y2="100" stroke="#AF322C" stroke-width="4" marker-end="url(#ar2)"/>
<rect x="176" y="52" width="112" height="96" rx="10" fill="#F6ECEA" stroke="#AF322C"/><text x="232" y="46" font-size="11" fill="#AF322C">After</text><text x="232" y="98" font-size="14" font-weight="900" fill="#AF322C">納得して選び</text><text x="232" y="120" font-size="14" font-weight="900" fill="#AF322C">入社後に活躍</text></g></svg>"""

swim = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP">
<text x="6" y="60" font-size="11" font-weight="700" fill="#AF322C">CA</text>
<rect x="44" y="42" width="62" height="34" rx="6" fill="#AF322C"/><text x="75" y="63" font-size="11" fill="#fff" text-anchor="middle">面談</text>
<rect x="120" y="42" width="62" height="34" rx="6" fill="#AF322C"/><text x="151" y="63" font-size="11" fill="#fff" text-anchor="middle">推薦</text>
<rect x="196" y="42" width="78" height="34" rx="6" fill="#AF322C"/><text x="235" y="63" font-size="10" fill="#fff" text-anchor="middle">クロージング</text>
<text x="6" y="140" font-size="11" font-weight="700" fill="#1A1714">求職者</text>
<rect x="44" y="122" width="62" height="34" rx="6" fill="#fff" stroke="#C7BFB9"/><text x="75" y="143" font-size="11" text-anchor="middle">相談</text>
<rect x="120" y="122" width="62" height="34" rx="6" fill="#fff" stroke="#C7BFB9"/><text x="151" y="143" font-size="11" text-anchor="middle">選考</text>
<rect x="196" y="122" width="78" height="34" rx="6" fill="#fff" stroke="#C7BFB9"/><text x="235" y="143" font-size="11" text-anchor="middle">意思決定</text>
<g stroke="#D9D2CE" stroke-width="1.5"><line x1="75" y1="76" x2="75" y2="122"/><line x1="151" y1="76" x2="151" y2="122"/><line x1="235" y1="76" x2="235" y2="122"/></g></g></svg>"""

timeline = """<svg viewBox="0 0 300 200"><g font-family="Noto Sans JP" text-anchor="middle">
<line x1="34" y1="100" x2="278" y2="100" stroke="#D9D2CE" stroke-width="3"/>
<circle cx="50" cy="100" r="10" fill="#AF322C"/><text x="50" y="74" font-size="12" font-weight="700">Stage1</text><text x="50" y="128" font-size="10" fill="#7C736D">基礎・3週</text>
<circle cx="125" cy="100" r="10" fill="#AF322C"/><text x="125" y="74" font-size="12" font-weight="700">Stage2</text><text x="125" y="128" font-size="10" fill="#7C736D">応用</text>
<circle cx="200" cy="100" r="10" fill="#AF322C"/><text x="200" y="74" font-size="12" font-weight="700">Stage3</text><text x="200" y="128" font-size="10" fill="#7C736D">実践</text>
<circle cx="262" cy="100" r="11" fill="#1A1714"/><text x="262" y="74" font-size="12" font-weight="700" fill="#1A1714">独り立ち</text><text x="262" y="128" font-size="10" fill="#7C736D">半年</text></g></svg>"""

CARDS = [("SWOT・フレームワーク", "強み/弱み/機会/脅威", swot), ("ピラミッド・階層", "構造・優先順位", pyramid),
         ("相関図", "関係・エコシステム", relation), ("対比 Before→After", "課題 → 解決", ba),
         ("スイムレーン", "役割 × 工程フロー", swim), ("タイムライン", "フェーズ・ロードマップ", timeline)]
cards = "".join(f'<div class="card"><div class="ct"><span class="cn">{n}</span><span class="cd">{d}</span></div><div class="fig">{s}</div></div>' for n, d, s in CARDS)

html = f"""<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"/>{FONTS}
<style>*{{margin:0;box-sizing:border-box;}}html,body{{width:1280px;background:#fff;font-family:"Noto Sans JP",sans-serif;color:#1A1714;}}
.wrap{{padding:34px 44px 40px;}}
.h{{font-family:"IBM Plex Mono",monospace;color:#AF322C;font-weight:600;font-size:13px;letter-spacing:.14em;}}
.t{{font-family:"Shippori Mincho B1",serif;font-weight:800;font-size:29px;margin:6px 0 2px;}}
.s{{color:#7C736D;font-size:14px;margin-bottom:20px;}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;}}
.card{{border:1px solid #E6E3E1;border-radius:14px;padding:14px 16px;box-shadow:0 6px 18px rgba(20,16,12,.05);}}
.ct{{display:flex;align-items:baseline;gap:8px;border-bottom:1.5px solid #AF322C;padding-bottom:5px;margin-bottom:4px;}}
.cn{{font-weight:900;font-size:15px;}}.cd{{font-size:11px;color:#7C736D;}}
.fig{{height:200px;}}.fig svg{{width:100%;height:100%;}}
</style></head><body><div class="wrap">
<div class="h">DIAGRAM LIBRARY ・ 概念図・説明図（データでない図解）</div>
<div class="t">数字がなくても、“概念・関係・流れ”を図解できる</div>
<div class="s">フレームワーク／階層／相関／対比／プロセス／時系列 など。すべてHTML/SVG・ブランド統一・文字はネイティブ編集可（ハイブリッド）。他に MECE/ロジックツリー・氷山モデル・ベン図・ガント なども可。</div>
<div class="grid">{cards}</div></div></body></html>"""

open("/tmp/concept.html", "w", encoding="utf-8").write(html)
print("wrote /tmp/concept.html | bytes:", len(html))
