#!/usr/bin/env python3
"""業界マップ（HTML版・高クラフト v2）をデータから一発生成。

設計4軸: Purpose=業界全体像の高級リファレンス / Tone=日経×官公庁コンサル×編集デザイン誌 /
Constraints=単一HTML・1280x720・CSS only・Google Fonts / Differentiation=下部ディープインク帯の
明朝KEY TAKEAWAY＋カテゴリ番号バッジ＋内定難易度ドット＋staggered reveal。
HTML/CSSのレイアウトエンジンで自動整列＝文字は原理的に被らない。出力=/tmp/industry_map.html
"""
import json
import os

BASE = "/Users/atsuyasato/Claude AI"
IND = json.load(open(os.path.join(BASE, "data_ca_training.json"), encoding="utf-8"))["INDUSTRIES"]
MKT = json.load(open(os.path.join(BASE, "data_industry_market.json"), encoding="utf-8"))["MARKET"]
OUT = json.load(open(os.path.join(BASE, "data_industry_outlook.json"), encoding="utf-8"))["OUTLOOK"]

NAME_SHORT = {
    "その他金融（カード/リース/フィンテック）": "その他金融", "保険（生保・損保）": "保険",
    "医療・介護・教育サービス": "医療・介護・教育", "鉄道・運輸（旅客）": "鉄道・運輸",
    "旅行・ホテル・レジャー": "旅行・ホテル", "電力・ガス・エネルギー": "電力・ガス",
    "SIer・システム開発": "SIer・開発", "SaaS・スタートアップ": "SaaS・新興",
    "電機・電子・精密": "電機・精密", "医薬品・医療機器": "医薬・医療機器", "機械・重工・プラント": "機械・重工",
    "その他メーカー（化粧品・日用品）": "その他メーカー", "百貨店・スーパー・コンビニ": "百貨店・小売",
    "外食・フードサービス": "外食・フード", "陸運・倉庫・3PL": "陸運・倉庫",
    "不動産（デベロッパー）": "不動産デベ", "住宅・ハウスメーカー": "住宅・ハウス",
    "公務員・公的機関": "公務員・公的",
}
COMP_SHORT = {"SES・客先常駐": "中小SES多数", "公務員・公的機関": "各府省庁・自治体"}
# 番号バッジ付きのカテゴリ順（左→右の列に積む）
COLMAP = [["商社", "金融"], ["サービス"], ["IT", "小売"], ["メーカー"],
          ["広告マスコミ", "物流・運輸"], ["不動産・建設", "官公庁"]]
CAT_NO = {"商社": "01", "サービス": "02", "金融": "03", "IT": "04", "メーカー": "05", "小売": "06",
          "広告マスコミ": "07", "物流・運輸": "08", "不動産・建設": "09", "官公庁": "10"}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def pop_class(p):
    return "pop-hi" if p == "高" else ("pop-lo" if p in ("低", "低〜中") else "pop-mid")


def growth(g):
    return ("▲", "g-up") if g == "拡大" else (("▼", "g-dn") if g == "縮小" else ("▬", "g-flat"))


def diff_dots(s):
    n = 3 if "最難関" in s else (2 if "難関" in s else 1)
    return '<span class="dots" title="内定難易度">%s%s</span>' % (
        '<i class="on"></i>' * n, '<i></i>' * (3 - n))


def main():
    by_cat = {}
    for i, ind in enumerate(IND):
        by_cat.setdefault(ind[1], []).append(i)

    cols = []
    for ci, cats in enumerate(COLMAP):
        clusters = []
        for cat in cats:
            chips = []
            for idx in by_cat.get(cat, []):
                ind = IND[idx]
                name = NAME_SHORT.get(ind[0], ind[0])
                comp = COMP_SHORT.get(ind[0], ind[4].split("、")[0].split("/")[0].split("（")[0])
                pop = ind[8] if len(ind) > 8 else "中"
                g = MKT[idx].get("成長ランク", "横ばい") if idx < len(MKT) else "横ばい"
                diff = OUT[idx].get("内定難易度", "") if idx < len(OUT) else ""
                gl, gc = growth(g)
                chips.append(
                    '<div class="chip">'
                    '<div class="r1"><span class="nm {pc}">{nm}</span><span class="arr {gc}">{gl}</span></div>'
                    '<div class="r2"><span class="cp">{cp}</span>{dd}</div></div>'.format(
                        pc=pop_class(pop), nm=esc(name), gc=gc, gl=gl, cp=esc(comp), dd=diff_dots(diff)))
            clusters.append(
                '<div class="cluster"><div class="chead"><span class="no">{no}</span>'
                '<span class="cname">{cat}</span></div>{chips}</div>'.format(
                    no=CAT_NO.get(cat, ""), cat=esc(cat), chips="".join(chips)))
        cols.append('<div class="col" style="--d:{d}ms">{c}</div>'.format(d=ci * 70, c="".join(clusters)))

    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>業界マップ｜Tokumori</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Shippori+Mincho+B1:wght@600;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet" />
<style>
  :root{
    --red:#AF322C; --redd:#7A211C; --ink:#1A1714; --sub:#7C736D; --faint:#A9A09A;
    --rule:#E7E3E0; --hair:#EFEBE8; --panel:#FBF9F8; --lred:#F7ECEA; --paper:#FDFCFB;
    --dark:#211C1A; --up:#1E7A4E; --flat:#A49C96; --dn:#B0742A;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;background:#E7E4E1;font-family:"Noto Sans JP",sans-serif;color:var(--ink);
    -webkit-font-smoothing:antialiased;}
  .stage{min-height:100vh;display:grid;place-items:center;padding:24px;}
  .board{width:1280px;height:720px;background:var(--paper);position:relative;display:flex;flex-direction:column;
    border-radius:8px;box-shadow:0 18px 60px rgba(20,16,12,.18);overflow:hidden;}
  .board::before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:var(--red);}
  .hd{padding:30px 44px 0;display:flex;justify-content:space-between;align-items:flex-start;}
  .kick{font-family:"IBM Plex Mono",monospace;color:var(--red);font-weight:600;font-size:12px;letter-spacing:.14em;}
  .title{font-family:"Shippori Mincho B1",serif;font-weight:800;font-size:36px;line-height:1.08;margin:6px 0 3px;letter-spacing:.01em;}
  .sub{color:var(--sub);font-size:13.5px;}
  .meta{text-align:right;font-family:"IBM Plex Mono",monospace;color:var(--faint);font-size:10.5px;line-height:1.7;letter-spacing:.06em;}
  .legend{margin-top:8px;display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--sub);align-items:flex-end;}
  .legend .row{display:flex;gap:7px;align-items:center;}
  .legend b{color:var(--ink);}
  .dot{width:9px;height:9px;border-radius:99px;display:inline-block;}
  .rule{height:2px;background:var(--red);width:60px;margin:12px 44px 0;}
  .map{flex:1;display:grid;grid-template-columns:repeat(6,1fr);gap:0;padding:14px 44px 8px;min-height:0;}
  .col{display:flex;flex-direction:column;gap:13px;min-height:0;padding:0 13px;border-right:1px solid var(--hair);
    animation:rise .6s both;animation-delay:var(--d);}
  .col:first-child{padding-left:0;} .col:last-child{padding-right:0;border-right:none;}
  @keyframes rise{from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:none;}}
  @media (prefers-reduced-motion:reduce){.col{animation:none;}}
  .cluster{display:flex;flex-direction:column;gap:4px;}
  .chead{display:flex;align-items:center;gap:6px;border-bottom:1.5px solid var(--ink);padding-bottom:3px;margin-bottom:1px;}
  .chead .no{font-family:"IBM Plex Mono",monospace;font-size:9px;font-weight:600;color:#fff;background:var(--red);
    border-radius:3px;padding:1px 4px;letter-spacing:.02em;}
  .chead .cname{font-weight:700;font-size:12.5px;color:var(--ink);}
  .chip{padding:1px 0 4px;border-bottom:1px solid var(--hair);}
  .chip:last-child{border-bottom:none;}
  .r1{display:flex;justify-content:space-between;align-items:baseline;gap:5px;}
  .nm{font-weight:700;font-size:12.5px;line-height:1.2;text-wrap:pretty;}
  .nm.pop-hi{color:var(--red);} .nm.pop-mid{color:var(--ink);} .nm.pop-lo{color:var(--faint);font-weight:500;}
  .arr{font-size:11px;font-weight:700;flex:none;}
  .arr.g-up{color:var(--up);} .arr.g-flat{color:var(--flat);} .arr.g-dn{color:var(--dn);}
  .r2{display:flex;justify-content:space-between;align-items:center;gap:6px;margin-top:1px;}
  .cp{font-family:"IBM Plex Mono",monospace;font-size:9px;color:var(--faint);white-space:nowrap;overflow:hidden;
    text-overflow:ellipsis;}
  .dots{display:inline-flex;gap:2px;flex:none;}
  .dots i{width:5px;height:5px;border-radius:99px;background:#E0DAD6;display:inline-block;}
  .dots i.on{background:var(--redd);}
  .foot{background:var(--dark);padding:13px 44px;display:flex;align-items:center;gap:18px;}
  .foot .lab{font-family:"IBM Plex Mono",monospace;color:#E9B7B2;font-weight:600;font-size:11px;letter-spacing:.1em;flex:none;}
  .foot .txt{font-family:"Shippori Mincho B1",serif;font-weight:600;color:#F4F0EE;font-size:14px;line-height:1.55;}
  .foot .txt b{color:#fff;}
  .src{position:absolute;bottom:4px;left:44px;font-family:"IBM Plex Mono",monospace;font-size:8px;color:rgba(255,255,255,.55);}
  /* 画像書き出し用(フルブリード)：EXPORT=1 で body.exp */
  .exp .stage{padding:0;background:#fff;}
  .exp .board{border-radius:0;box-shadow:none;}
</style>
</head>
<body class="__BODYCLS__">
<div class="stage">
  <div class="board" data-screen-label="業界マップ">
    <div class="hd">
      <div>
        <div class="kick">INDUSTRY MAP ・ 業界理解</div>
        <div class="title">人気と成長性は一致しない ― 業界は“2軸”で見る</div>
        <div class="sub">日本の主要36業界マップ ／ 10カテゴリ・人気度 × 成長性</div>
      </div>
      <div>
        <div class="meta">36 INDUSTRIES ／ 10 CATEGORIES<br/>AS OF 2025 ・ TOKUMORI</div>
        <div class="legend">
          <div class="row">人気 <span class="dot" style="background:var(--red)"></span><b>高</b><span class="dot" style="background:var(--ink)"></span>中<span class="dot" style="background:var(--faint)"></span>低</div>
          <div class="row">成長 <span class="arr g-up">▲</span>拡大 <span class="arr g-flat">▬</span>横ばい <span class="arr g-dn">▼</span>縮小</div>
          <div class="row">難易度 <span class="dots"><i class="on"></i><i class="on"></i><i class="on"></i></span>高 〜 <span class="dots"><i class="on"></i><i></i><i></i></span>低</div>
        </div>
      </div>
    </div>
    <div class="rule"></div>
    <div class="map">__COLS__</div>
    <div class="foot">
      <div class="lab">KEY TAKEAWAY</div>
      <div class="txt">拡大業界（IT・金融・先端メーカー・エンタメ）と横ばい/縮小（マスコミ・住宅）に二極化。<b>“人気＝成長”ではない</b>。志望は人気でなく<b>“成長性 × 自分の適性”</b>で選ぶ。</div>
    </div>
    <div class="src">出典：data_ca_training／industry_market／outlook（矢野経済研究所・経産省・各社IR 等, 2023-2025）。人気度・難易度=就活の概観。配布前に最新値を要確認。</div>
  </div>
</div>
</body>
</html>
""".replace("__COLS__", "".join(cols)).replace("__BODYCLS__", "exp" if os.environ.get("EXPORT") else "")

    out = "/tmp/industry_map.html"
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, "| bytes:", len(html), "| industries:", len(IND))


if __name__ == "__main__":
    main()
