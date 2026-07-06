#!/usr/bin/env python3
"""デザインサンプル v1（FB用）＝スライド全面をHTMLで設計して画像化。
表紙3案＋章扉＋KPI＋データ＋ステートメント＋締め の8枚を1つのGoogleスライドに。
狙い: LayerX/SmartHR級の「スマート・かっこいい」。チャコール×ブランド赤×精密グリッド。器は細線アークに抽象化。"""
import os
import warnings

warnings.filterwarnings("ignore")

import html_to_slide as H

INK = "#15171C"       # チャコール（ほぼ黒・純黒でない）
PAPER = "#FBFAF9"     # 温白
RED = "#AF322C"       # TOKUMORI公式
GRAY = "#8A8F98"
HAIR_D = "rgba(255,255,255,0.14)"   # ダーク上のヘアライン
HAIR_L = "rgba(21,23,28,0.14)"      # ライト上のヘアライン

FONT = ('<link href="https://fonts.googleapis.com/css2?'
        'family=Noto+Sans+JP:wght@400;500;700;900&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')

BASE = ('*{margin:0;padding:0;box-sizing:border-box;}'
        'html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}'
        '.en{font-family:Lato,sans-serif;letter-spacing:.16em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}')


def arc(size, stroke, color, opacity=1.0, flip=False):
    # 器の抽象化＝半円の細線アーク（CSS円をoverflowで半分見せる）。flip=False:ドーム（上に凸）/ True:椀（下に凸）
    shift = 0 if not flip else -size // 2
    return (f'<div style="width:{size}px;height:{size//2}px;overflow:hidden;opacity:{opacity};">'
            f'<div style="width:{size-2*stroke}px;height:{size-2*stroke}px;border:{stroke}px solid {color};'
            f'border-radius:50%;margin-top:{shift}px;"></div></div>')


def page(body, dark=False):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT +
            f'<style>{BASE}body{{background:{INK if dark else PAPER};color:{"#FFFFFF" if dark else INK};}}</style>'
            '</head><body>' + body + '</body></html>')


# ---------- S1 表紙A: Charcoal Precision（ダーク・精密） ----------
cover_a = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    </div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal</div>
  </div>
  <div style="position:absolute;left:72px;top:200px;width:900px;">
    <div class="en" style="font-size:12px;color:{RED};font-weight:700;margin-bottom:26px;">Tokumori RPO — 2026</div>
    <div class="jp" style="font-size:64px;font-weight:900;line-height:1.24;letter-spacing:.01em;">採用を、<br>勝てる構造に。</div>
    <div style="width:44px;height:3px;background:{RED};margin:34px 0 22px;"></div>
    <div class="jp" style="font-size:16px;color:#B9BDC4;line-height:1.9;">母集団形成から定着まで——データと学術で、候補者に選ばれる採用へ。</div>
  </div>
  <div style="position:absolute;right:-140px;top:150px;">{arc(460, 1.5, RED, 0.85)}</div>
  <div style="position:absolute;right:-100px;top:190px;">{arc(380, 1.0, "#FFFFFF", 0.18)}</div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_D};padding-top:18px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Chuto Saiyo RPO</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Confidential</div>
  </div>
</div>''', dark=True)

# ---------- S2 表紙B: Swiss White（白・エッジ赤・グリッド） ----------
cover_b = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px 48px 96px;">
  <div style="position:absolute;left:0;top:0;width:8px;height:720px;background:{RED};"></div>
  <div style="position:absolute;left:426px;top:0;width:1px;height:720px;background:{HAIR_L};"></div>
  <div style="position:absolute;left:780px;top:0;width:1px;height:720px;background:{HAIR_L};"></div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal — 2026</div>
  </div>
  <div style="position:absolute;left:96px;top:212px;width:1000px;">
    <div class="jp" style="font-size:70px;font-weight:900;line-height:1.22;letter-spacing:.01em;">採用を、<br>勝てる構造に。</div>
    <div class="jp" style="font-size:16px;color:#5F6570;line-height:1.9;margin-top:34px;">母集団形成から定着まで——データと学術で、候補者に選ばれる採用へ。</div>
  </div>
  <div style="position:absolute;left:96px;right:72px;bottom:48px;display:flex;justify-content:space-between;border-top:1px solid {HAIR_L};padding-top:18px;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI ｜ 中途採用RPO ご提案</div>
    <div class="en" style="font-size:11px;color:{RED};font-weight:700;">Win by Structure</div>
  </div>
</div>''')

# ---------- S3 表紙C: Ink Panel（左チャコールパネル・右白・アーク跨ぎ） ----------
cover_c = page(f'''
<div style="position:relative;width:1280px;height:720px;">
  <div style="position:absolute;left:0;top:0;width:512px;height:720px;background:{INK};padding:56px 48px;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;color:#fff;">とくもり採用代行</div>
    </div>
    <div class="jp" style="position:absolute;left:48px;top:236px;width:420px;font-size:52px;font-weight:900;line-height:1.3;color:#fff;letter-spacing:.01em;">採用を、<br>勝てる<br>構造に。</div>
    <div class="en" style="position:absolute;left:48px;bottom:52px;font-size:11px;color:{GRAY};">Recruitment Proposal</div>
  </div>
  <div style="position:absolute;left:512px;top:0;right:0;height:720px;padding:56px 64px;">
    <div class="en" style="text-align:right;font-size:11px;color:{GRAY};">2026 — Chuto Saiyo RPO</div>
    <div style="position:absolute;left:64px;top:210px;">{arc(300, 2, RED, 1.0)}</div>
    <div class="jp" style="position:absolute;left:64px;top:420px;width:600px;font-size:16px;color:#3A3F47;line-height:2.0;">母集団形成から定着まで。<br>データと学術で、候補者に選ばれる採用へ。</div>
    <div style="position:absolute;left:64px;right:64px;bottom:48px;border-top:1px solid {HAIR_L};padding-top:16px;display:flex;justify-content:space-between;">
      <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div>
      <div class="en" style="font-size:11px;color:{GRAY};">Confidential</div>
    </div>
  </div>
</div>''')

# ---------- S4 章扉: ゴースト番号 ----------
section = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div class="num" style="position:absolute;right:40px;top:-60px;font-size:400px;font-weight:900;color:transparent;-webkit-text-stroke:1.5px rgba(21,23,28,.14);line-height:1;">01</div>
  <div style="position:absolute;left:72px;top:250px;">
    <div class="en" style="font-size:12px;color:{RED};font-weight:700;margin-bottom:24px;">Market Shift ／ 採用市場</div>
    <div class="jp" style="font-size:46px;font-weight:900;letter-spacing:.01em;">採用環境の、構造変化</div>
    <div style="width:44px;height:3px;background:{RED};margin:30px 0 22px;"></div>
    <div class="jp" style="font-size:16px;color:#5F6570;line-height:1.9;">大企業優位・売り手市場・地方採用難——市場はもう元に戻らない。</div>
  </div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_L};padding-top:16px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">とくもり採用代行 ｜ 中途採用RPO</div>
    <div class="num" style="font-size:12px;color:{GRAY};">04</div>
  </div>
</div>''')

# ---------- S5 KPI: 巨大数字 ----------
bignum = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div class="en" style="font-size:12px;color:{RED};font-weight:700;">Impact ／ 提供価値</div>
  <div style="position:absolute;left:66px;top:130px;display:flex;align-items:baseline;">
    <div class="num jp" style="font-size:280px;font-weight:900;letter-spacing:-0.02em;line-height:1;">29</div>
    <div class="num" style="font-size:120px;font-weight:900;color:{RED};line-height:1;">×</div>
  </div>
  <div style="position:absolute;right:-120px;top:260px;">{arc(360, 1.2, INK, 0.14)}</div>
  <div style="position:absolute;left:72px;top:490px;">
    <div class="jp" style="font-size:24px;font-weight:700;">母集団形成、最大29倍</div>
    <div class="jp" style="font-size:15px;color:#5F6570;margin-top:14px;line-height:1.8;">既存比・事例値（+800〜2,600%）。方向値であり成果保証ではありません。</div>
  </div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_L};padding-top:14px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:11px;color:{GRAY};">出典: 自社実績・モデルケースに基づく方向値</div>
    <div class="num" style="font-size:12px;color:{GRAY};">05</div>
  </div>
</div>''')

# ---------- S6 データ: 横棒（精密） ----------
def bar_row(label, w, val, hi=False):
    color = RED if hi else "#D9D6D2"
    lab_c = RED if hi else INK
    return (f'<div style="display:flex;align-items:center;margin-bottom:26px;">'
            f'<div class="jp" style="width:190px;font-size:16px;font-weight:700;color:{lab_c};">{label}</div>'
            f'<div style="flex:1;position:relative;height:34px;background:rgba(21,23,28,.05);">'
            f'<div style="position:absolute;left:0;top:0;height:34px;width:{w}%;background:{color};"></div>'
            f'<div class="num" style="position:absolute;left:calc({w}% + 14px);top:5px;font-size:17px;font-weight:700;color:{lab_c};">{val}</div>'
            f'</div></div>')

chart = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div class="en" style="font-size:12px;color:{RED};font-weight:700;">Market Shift ／ 採用市場</div>
  <div class="jp" style="font-size:32px;font-weight:900;margin-top:16px;letter-spacing:.01em;">中小の採用難易度は、大企業の約26倍</div>
  <div style="margin-top:64px;width:1060px;">
    {bar_row("300人以下", 92, "8.98倍", True)}
    {bar_row("1,000人以上", 13, "1.20倍")}
    {bar_row("5,000人以上", 4, "0.34倍")}
  </div>
  <div class="jp" style="margin-top:40px;font-size:15px;font-weight:700;">
    <span style="border-bottom:3px solid {RED};padding-bottom:3px;">スカウト反応率も 16.8% → 6.7% へ半減。「待ち」の採用は通用しない。</span>
  </div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_L};padding-top:14px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:11px;color:{GRAY};">出典: リクルートワークス研究所 第42回(26卒) ／ マルゴト社2025。大卒有効求人倍率。</div>
    <div class="num" style="font-size:12px;color:{GRAY};">06</div>
  </div>
</div>''')

# ---------- S7 ステートメント（ダーク・下線強調） ----------
statement = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div class="en" style="font-size:12px;color:{RED};font-weight:700;">Method ／ CX × EVP</div>
  <div class="jp" style="position:absolute;left:72px;top:250px;width:1100px;font-size:50px;font-weight:900;line-height:1.6;letter-spacing:.01em;">
    体験と理由が、<br><span style="border-bottom:5px solid {RED};padding-bottom:6px;">承諾率を動かす。</span>
  </div>
  <div class="jp" style="position:absolute;left:72px;top:520px;font-size:16px;color:#B9BDC4;line-height:1.9;">
    候補者体験(CX)と働く理由(EVP)の設計で、内定承諾率 +25〜38%（方向値）。
  </div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_D};padding-top:14px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">とくもり採用代行 ｜ 中途採用RPO</div>
    <div class="num" style="font-size:12px;color:{GRAY};">07</div>
  </div>
</div>''', dark=True)

# ---------- S8 締め（ダーク・アーク） ----------
closing = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:10px;height:10px;background:{RED};"></div>
    <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
  </div>
  <div class="jp" style="position:absolute;left:72px;top:240px;font-size:54px;font-weight:900;letter-spacing:.01em;">採用を、勝てる構造に。<span style="color:{RED};">一緒に。</span></div>
  <div class="jp" style="position:absolute;left:72px;top:390px;font-size:16px;color:#B9BDC4;line-height:2.1;">
    まずは現状のKPIと課題を、30分でヒアリングします。<br>最短1週間でKick Off、6ヶ月で採用の仕組みを構築します。
  </div>
  <div style="position:absolute;right:-140px;bottom:-40px;">{arc(430, 1.5, RED, 0.85, flip=True)}</div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HAIR_D};padding-top:16px;display:flex;justify-content:space-between;">
    <div class="en" style="font-size:12px;color:#fff;"><span style="color:{RED};font-weight:900;">Contact</span>&nbsp;&nbsp;atsuya_sato@tokumori.co.jp</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Tokumori, Inc.</div>
  </div>
</div>''', dark=True)


def main():
    slides = [("cover_a", cover_a), ("cover_b", cover_b), ("cover_c", cover_c),
              ("section", section), ("bignum", bignum), ("chart", chart),
              ("statement", statement), ("closing", closing)]
    paths = []
    for name, html in slides:
        p = "/tmp/ds1_%s.html" % name
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ デザインサンプル v1（FB用）",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("SAMPLE:", url)


if __name__ == "__main__":
    main()
