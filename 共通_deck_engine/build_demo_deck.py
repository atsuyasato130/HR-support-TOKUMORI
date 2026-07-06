#!/usr/bin/env python3
"""新卒研修『事業理解』資料（4枚）をHTMLで高品質生成（被り対策済み）。

brand.py トークン共有。各スライドを /tmp/deck_NN.html に書き出し→html_to_slide.insert_many で
1つのGoogle Slidesに画像束ね。被り対策＝ヘッダをflex(見出し枠 flex:1 ＋ 右メタ flex:none)で分離。
"""
import os
import brand as B

CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com"/><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900&family=Shippori+Mincho+B1:wght@600;800&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root{--red:#%(RED)s;--redd:#%(REDD)s;--ink:#%(INK)s;--sub:#%(SUB)s;--rule:#%(RULE)s;--panel:#%(PANEL)s;
  --lred:#%(LRED)s;--paper:#%(PAPER)s;--dark:#%(INKDK)s;--faint:#%(FAINT2)s;}
*{box-sizing:border-box;margin:0;}
html,body{background:#fff;font-family:"%(BODY)s",sans-serif;color:var(--ink);-webkit-font-smoothing:antialiased;}
.stage{min-height:100vh;display:grid;place-items:center;}
.board{width:1280px;height:720px;background:var(--paper);position:relative;display:flex;flex-direction:column;overflow:hidden;}
.board::before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:var(--red);z-index:2;}
/* header: 被り防止＝見出し枠とメタ枠をflexで分離 */
.hd{padding:32px 52px 0;display:flex;justify-content:space-between;align-items:flex-start;gap:28px;}
.hd .lead{flex:1;min-width:0;}
.hd .meta{flex:none;text-align:right;max-width:280px;}
.kick{font-family:"%(MONO)s",monospace;color:var(--red);font-weight:600;font-size:13px;letter-spacing:.14em;}
.title{font-family:"%(DISP)s",serif;font-weight:800;font-size:31px;line-height:1.16;margin:7px 0 4px;letter-spacing:.01em;text-wrap:pretty;}
.title b{color:var(--red);}
.sub{color:var(--sub);font-size:13.5px;}
.badge .rl{font-family:"%(MONO)s",monospace;font-size:10px;color:var(--faint);letter-spacing:.08em;}
.badge .rv{font-family:"%(DISP)s",serif;font-weight:800;font-size:14px;color:var(--red);margin-top:2px;line-height:1.3;}
.rule{height:2px;width:64px;background:var(--red);margin:13px 52px 0;}
.body{flex:1;display:flex;flex-direction:column;justify-content:center;padding:6px 52px 0;min-height:0;}
.foot{background:var(--dark);padding:13px 52px;display:flex;align-items:center;gap:18px;}
.foot .lab{font-family:"%(MONO)s",monospace;color:#E9B7B2;font-weight:600;font-size:11px;letter-spacing:.1em;flex:none;}
.foot .txt{font-family:"%(DISP)s",serif;font-weight:600;color:#F4F0EE;font-size:14px;line-height:1.5;}
.foot .txt b{color:#fff;}
.src{position:absolute;bottom:3px;left:52px;font-family:"%(MONO)s",monospace;font-size:8px;color:rgba(255,255,255,.5);}
/* cover(dark) */
.cover{background:var(--dark);color:#fff;justify-content:center;padding:0 70px;}
.cover .rail{position:absolute;left:0;top:0;bottom:0;width:12px;background:var(--red);}
.cover .ck{font-family:"%(MONO)s",monospace;color:#E9B7B2;font-weight:600;font-size:13px;letter-spacing:.16em;}
.cover h1{font-family:"%(DISP)s",serif;font-weight:800;font-size:62px;letter-spacing:.02em;margin:10px 0 6px;}
.cover .cs{font-size:18px;color:#D9D2CE;}
.cover .cm{position:absolute;bottom:46px;left:70px;font-family:"%(MONO)s",monospace;font-size:12px;color:#A99F99;letter-spacing:.06em;}
/* process flow */
.stages{display:grid;grid-template-columns:1fr 26px 1fr 26px 1fr;align-items:stretch;}
.arr{display:grid;place-items:center;color:var(--red);font-size:24px;font-weight:700;}
.card{background:#fff;border:1px solid var(--rule);border-radius:12px;padding:16px 18px;box-shadow:0 6px 18px rgba(20,16,12,.05);display:flex;flex-direction:column;gap:8px;}
.card.core{border-color:var(--red);box-shadow:0 10px 24px rgba(175,50,44,.13);}
.ctop{display:flex;align-items:center;gap:8px;}
.no{font-family:"%(MONO)s",monospace;font-size:11px;font-weight:600;color:#fff;background:var(--ink);border-radius:5px;padding:2px 7px;}
.card.core .no{background:var(--red);}
.stg{font-family:"%(MONO)s",monospace;font-size:11px;color:var(--sub);letter-spacing:.1em;}
.cname{font-weight:900;font-size:18px;line-height:1.1;}
.card.core .cname{color:var(--red);}
.li{display:flex;gap:8px;align-items:flex-start;font-size:12.5px;line-height:1.4;}
.li::before{content:"";width:5px;height:5px;border-radius:99px;background:var(--red);margin-top:7px;flex:none;}
.base{display:flex;align-items:center;gap:14px;background:var(--ink);color:#fff;border-radius:12px;padding:13px 20px;margin-top:16px;}
.base .bl{font-family:"%(DISP)s",serif;font-weight:800;font-size:15px;flex:none;}
.chipb{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:999px;padding:5px 12px;font-size:12px;}
.bset{display:flex;gap:9px;flex-wrap:wrap;}
/* stat cards */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
.stat{background:var(--panel);border:1px solid var(--rule);border-radius:12px;padding:20px 16px;text-align:center;position:relative;overflow:hidden;}
.stat::before{content:"";position:absolute;top:0;left:0;right:0;height:5px;background:var(--red);}
.stat .big{font-family:"%(DISP)s",serif;font-weight:800;font-size:40px;color:var(--red);line-height:1;margin-top:6px;}
.stat .lb{font-weight:700;font-size:13px;margin-top:10px;}
.stat .sc{font-family:"%(MONO)s",monospace;font-size:9px;color:var(--sub);margin-top:5px;}
/* takeaways */
.tk{display:flex;flex-direction:column;gap:14px;}
.tkrow{display:flex;gap:14px;align-items:flex-start;}
.tkno{font-family:"%(DISP)s",serif;font-weight:800;font-size:26px;color:var(--red);flex:none;width:42px;line-height:1.1;}
.tktx{font-size:17px;line-height:1.5;}
.tktx b{color:var(--red);}
</style>
""" % vars(B)


def doc(body):
    return "<!DOCTYPE html><html lang=\"ja\"><head><meta charset=\"utf-8\"/>" + CSS + \
        "</head><body class=\"exp\"><div class=\"stage\">" + body + "</div></body></html>"


def header(kick, title, sub, badge_l=None, badge_v=None):
    meta = ""
    if badge_v:
        meta = '<div class="meta badge"><div class="rl">%s</div><div class="rv">%s</div></div>' % (badge_l or "", badge_v)
    return ('<div class="hd"><div class="lead"><div class="kick">%s</div><div class="title">%s</div>'
            '<div class="sub">%s</div></div>%s</div><div class="rule"></div>' % (kick, title, sub, meta))


def foot(txt, src):
    return ('<div class="foot"><div class="lab">KEY TAKEAWAY</div><div class="txt">%s</div></div>'
            '<div class="src">%s</div>' % (txt, src))


SRC = "出典：Tokumori事業モデル／社内研修 A1・A3。労働市場の数値は厚労省・Gallup・国税庁・日本生産性本部（概観）。配布前に最新値を要確認。"


def s_cover():
    b = ('<div class="board cover"><div class="rail"></div>'
         '<div class="ck">TOKUMORI 新卒研修 ・ ONBOARDING</div>'
         '<h1>事業理解</h1>'
         '<div class="cs">TOKUMORIの新卒紹介ビジネスを“3分で”説明できる</div>'
         '<div class="cm">Module A1・A3 ／ 自社・マインド ／ 所要 約1.5時間</div></div>')
    return doc(b)


def s_overview():
    stages = [("01", "入口", "母集団形成", ["新卒メディア・スカウト", "学校/紹介ルート", "説明会・送客"]),
              ("02", "中核", "面談・マッチング", ["キャリア面談・課題整理", "求人マッチング・推薦", "選考支援・対策"]),
              ("03", "出口", "内定者フォロー", ["内定承諾の意思決定支援", "入社前フォロー", "入社後の定着支援"])]
    cards = []
    for no, stg, name, items in stages:
        lis = "".join('<div class="li">%s</div>' % it for it in items)
        core = " core" if stg == "中核" else ""
        cards.append('<div class="card%s"><div class="ctop"><span class="no">%s</span><span class="stg">%s</span></div>'
                     '<div class="cname">%s</div>%s</div>' % (core, no, stg, name, lis))
    flow = cards[0] + '<div class="arr">›</div>' + cards[1] + '<div class="arr">›</div>' + cards[2]
    body = ('<div class="board">' +
            header("A1・A3 ・ 事業理解",
                   'TOKUMORIの新卒紹介は <b>「入口 → 中核 → 出口」</b> を “データ基盤” が支える',
                   "求職者一人ひとりの意思決定に伴走し、内定承諾＝成果で収益化する",
                   "REVENUE MODEL", "内定承諾で課金<br/>（成果報酬）") +
            '<div class="body"><div class="stages">' + flow + '</div>'
            '<div class="base"><div class="bl">基盤</div><div class="bset">'
            '<span class="chipb">データ / Salesforce</span><span class="chipb">AI活用（面談準備・紹介文・リサーチ）</span>'
            '<span class="chipb">業界・職種知識</span></div></div></div>' +
            foot('売上は<b>「内定承諾」</b>で発生＝<b>中核（面談・マッチング）の質</b>が事業の生命線。基盤が全工程の生産性を決める。', SRC) +
            '</div>')
    return doc(body)


def s_market():
    stats = [("33.8%", "新卒3年以内の離職率", "厚労省（大卒・近年）"),
             ("6%", "仕事に熱意ある社員", "Gallup・世界最低水準"),
             ("460万円", "平均給与（年）", "国税庁 民間給与実態"),
             ("28位", "時間当たり労働生産性", "OECD・日本生産性本部")]
    cells = "".join('<div class="stat"><div class="big">%s</div><div class="lb">%s</div><div class="sc">%s</div></div>' % s for s in stats)
    body = ('<div class="board">' +
            header("A1 ・ 社会人マインド／事業理解",
                   '働く現実は厳しい — <b>だからこそ“納得して働ける一社”に導くCAの価値</b>がある',
                   "労働市場のマクロを直視する（出典付き）") +
            '<div class="body"><div class="stats">' + cells + '</div></div>' +
            foot('“なんとなく就職→早期離職”が多い社会。<b>適性と納得で選べるよう伴走する</b>のがCAの仕事の意味。', SRC) +
            '</div>')
    return doc(body)


def s_summary():
    rows = [("01", 'TOKUMORIの新卒紹介は <b>入口→中核→出口</b> の一気通貫。'),
            ("02", '売上は <b>内定承諾（成果報酬）</b>＝<b>中核（面談・マッチング）の質</b>が生命線。'),
            ("03", '全工程の生産性は <b>基盤（Salesforce・AI・業界知識）</b> が決める。'),
            ("04", '本当のゴールは <b>求職者が入社後に活躍し“ありたい自分”でいられること</b>。')]
    tk = "".join('<div class="tkrow"><div class="tkno">%s</div><div class="tktx">%s</div></div>' % r for r in rows)
    body = ('<div class="board">' +
            header("A1・A3 ・ まとめ", 'まとめ：<b>内定承諾の質＝中核</b>、それを<b>基盤</b>が支える', "事業を自分の言葉で3分プレゼンできる状態に") +
            '<div class="body"><div class="tk">' + tk + '</div></div>' +
            foot('“右から左に流すだけ”ではない。<b>人生の岐路に伴走し、成果（承諾）と定着で価値を出す</b>事業。', SRC) +
            '</div>')
    return doc(body)


def main():
    slides = [s_cover(), s_overview(), s_market(), s_summary()]
    paths = []
    for i, h in enumerate(slides, 1):
        p = "/tmp/deck_%02d.html" % i
        open(p, "w", encoding="utf-8").write(h)
        paths.append(p)
    print("\n".join(paths))


if __name__ == "__main__":
    main()
