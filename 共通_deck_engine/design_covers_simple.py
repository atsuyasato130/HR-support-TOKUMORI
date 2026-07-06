#!/usr/bin/env python3
"""表紙v2＝極限シンプル4案（S1-S4）＋同思想の章扉・本文2案。装飾ゼロ・白・タイポと余白のみ。
（LayerX/メルカリの実物デッキ流。ANTI_AI_TELLS 2026-07-03確定方針）"""
import os
import warnings

warnings.filterwarnings("ignore")
import html_to_slide as H

INK = "#15171C"; PAPER = "#FFFFFF"; RED = "#AF322C"; GRAY = "#8A8F98"
HL = "rgba(21,23,28,0.12)"
FONT = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900'
        '&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')
BASE = ('*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;background:%s;color:%s;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}.en{font-family:Lato,sans-serif;letter-spacing:.14em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}' % (PAPER, INK))


def page(body):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT +
            f'<style>{BASE}</style></head><body>' + body + '</body></html>')


def tag(label):
    return (f'<div class="en" style="position:absolute;right:16px;bottom:12px;font-size:10px;'
            f'color:{RED};font-weight:700;background:rgba(175,50,44,.07);padding:4px 10px;">{label}</div>')


# ロゴ（ワードマーク＝文字とご飯マークの簡易再現。実運用は image2.png を native 配置）
def logo(size=15):
    return (f'<span style="display:inline-flex;align-items:center;gap:9px;">'
            f'<span style="position:relative;width:{size+2}px;height:{size+2}px;display:inline-block;">'
            f'<span style="position:absolute;inset:0;border-radius:50%;background:{INK};"></span>'
            f'<span style="position:absolute;left:0;right:0;bottom:0;height:45%;border-radius:0 0 {size}px {size}px;background:{RED};"></span>'
            f'<span style="position:absolute;left:0;right:0;top:45%;height:12%;background:#fff;"></span></span>'
            f'<span class="jp" style="font-size:{size}px;font-weight:900;letter-spacing:.02em;">とくもり採用代行</span></span>')


S = {}

# S1: LayerX流＝左上ロゴ・左寄せ特大タイトル・下部に社名と日付（それ以外なにもない）
S["S1 左寄せ（LayerX流）"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:64px 84px;">
  {logo(16)}
  <div style="position:absolute;left:84px;top:284px;">
    <div class="jp" style="font-size:58px;font-weight:900;line-height:1.4;letter-spacing:.01em;">採用を、勝てる構造に。</div>
    <div class="jp" style="font-size:17px;color:{GRAY};margin-top:26px;font-weight:500;">中途採用RPO ご提案</div>
  </div>
  <div class="jp" style="position:absolute;left:84px;bottom:60px;font-size:13px;color:{GRAY};">株式会社TOKUMORI　2026.07</div>
  {tag("S1")}
</div>''')

# S2: メルカリ流＝中央揃え・ロゴ上・タイトル中央・最下部メタ
S["S2 中央揃え（メルカリ流）"] = page(f'''
<div style="position:relative;width:1280px;height:720px;">
  <div style="position:absolute;left:0;right:0;top:170px;text-align:center;">
    <div style="display:flex;justify-content:center;">{logo(15)}</div>
    <div class="jp" style="font-size:54px;font-weight:900;margin-top:64px;letter-spacing:.01em;">採用を、勝てる構造に。</div>
    <div class="jp" style="font-size:16px;color:{GRAY};margin-top:24px;">中途採用RPO ご提案</div>
  </div>
  <div class="jp" style="position:absolute;left:0;right:0;bottom:56px;text-align:center;font-size:12.5px;color:{GRAY};">株式会社TOKUMORI</div>
  {tag("S2")}
</div>''')

# S3: タイトル純度100%＝ページのほぼ全てが余白。ロゴすら最小
S["S3 余白特化（純度100%）"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:64px 84px;">
  <div style="position:absolute;left:84px;top:330px;">
    <div class="jp" style="font-size:44px;font-weight:900;letter-spacing:.02em;">採用を、勝てる構造に。</div>
  </div>
  <div style="position:absolute;left:84px;bottom:60px;">{logo(13)}</div>
  <div class="jp en" style="position:absolute;right:84px;bottom:60px;font-size:11px;color:{GRAY};">Chuto RPO — 2026</div>
  {tag("S3")}
</div>''')

# S4: S1の赤ワンポイント版＝タイトル頭に小さな赤■だけ（唯一の色）
S["S4 赤ワンポイント"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:64px 84px;">
  {logo(16)}
  <div style="position:absolute;left:84px;top:264px;">
    <div style="width:15px;height:15px;background:{RED};margin-bottom:36px;"></div>
    <div class="jp" style="font-size:58px;font-weight:900;line-height:1.4;letter-spacing:.01em;">採用を、勝てる構造に。</div>
    <div class="jp" style="font-size:17px;color:{GRAY};margin-top:26px;font-weight:500;">中途採用RPO ご提案</div>
  </div>
  <div class="jp" style="position:absolute;left:84px;bottom:60px;font-size:13px;color:{GRAY};">株式会社TOKUMORI　2026.07</div>
  {tag("S4")}
</div>''')

# 章扉（同思想）＝白・小さな番号・タイトルだけ
S["S5 章扉（極限シンプル）"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:64px 84px;">
  <div style="position:absolute;left:84px;top:296px;">
    <div class="num" style="font-size:15px;font-weight:900;color:{RED};">01</div>
    <div class="jp" style="font-size:42px;font-weight:900;margin-top:20px;">採用市場の、構造変化</div>
    <div class="jp" style="font-size:15px;color:{GRAY};margin-top:18px;">大企業優位・売り手市場——市場はもう元に戻らない。</div>
  </div>
  {tag("S5")}
</div>''')

# 本文（同思想）＝ヘッダは小kicker＋見出しのみ・罫線なし・フッタは頁番号のみ
S["S6 本文（極限シンプル）"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:60px 84px;">
  <div class="jp" style="font-size:13px;color:{RED};font-weight:700;">採用市場</div>
  <div class="jp" style="font-size:30px;font-weight:900;margin-top:12px;">中小の採用難易度は、大企業の約26倍</div>
  <div style="margin-top:56px;width:1112px;height:310px;border:1px dashed {HL.replace("0.12","0.35")};display:flex;align-items:center;justify-content:center;color:{GRAY};" class="jp">（本文・図表エリア＝図解カタログの図が入る）</div>
  <div class="jp" style="position:absolute;left:84px;bottom:44px;font-size:11px;color:{GRAY};">出典: リクルートワークス研究所 第42回(26卒)</div>
  <div class="num" style="position:absolute;right:84px;bottom:44px;font-size:12px;color:{GRAY};">06</div>
  {tag("S6")}
</div>''')


def main():
    paths = []
    for name, html in S.items():
        p = "/tmp/simplecov_%s.html" % name.split(" ")[0]
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ 表紙v2 極限シンプル（S1-S6）",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("SIMPLE COVERS:", url)


if __name__ == "__main__":
    main()
