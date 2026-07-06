#!/usr/bin/env python3
"""① 背景カタログ＝表紙8案（C1-C8）＋本文ページ6案（B1-B6）。フルHTMLモック（サンプル文字入り）。
スマート・かっこいい系（チャコール#15171C×温白#FBFAF9×TOKUMORI赤#AF322C）。器は細線アークに抽象化。"""
import os
import warnings

warnings.filterwarnings("ignore")
import html_to_slide as H

INK = "#15171C"; PAPER = "#FBFAF9"; RED = "#AF322C"; GRAY = "#8A8F98"
HD = "rgba(255,255,255,0.14)"; HL = "rgba(21,23,28,0.14)"
FONT = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700;900'
        '&family=Lato:wght@400;700;900&display=swap" rel="stylesheet"/>')
BASE = ('*{margin:0;padding:0;box-sizing:border-box;}html,body{width:1280px;height:720px;overflow:hidden;}'
        'body{font-family:"Noto Sans JP",sans-serif;-webkit-font-smoothing:antialiased;}'
        '.jp{font-feature-settings:"palt";}'
        '.en{font-family:Lato,sans-serif;letter-spacing:.16em;text-transform:uppercase;}'
        '.num{font-family:Lato,sans-serif;}')


def arc(size, stroke, color, opacity=1.0, flip=False):
    shift = 0 if not flip else -size // 2
    return (f'<div style="width:{size}px;height:{size//2}px;overflow:hidden;opacity:{opacity};">'
            f'<div style="width:{size-2*stroke}px;height:{size-2*stroke}px;border:{stroke}px solid {color};'
            f'border-radius:50%;margin-top:{shift}px;"></div></div>')


def page(body, dark=False, bg=None):
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONT +
            f'<style>{BASE}body{{background:{bg or (INK if dark else PAPER)};color:{"#FFFFFF" if dark else INK};}}</style>'
            '</head><body>' + body + '</body></html>')


def tag(label):  # カタログ用の識別タグ（右下小）
    return (f'<div class="en" style="position:absolute;right:16px;bottom:12px;font-size:10px;'
            f'color:{RED};font-weight:700;background:rgba(175,50,44,.08);padding:4px 10px;">{label}</div>')


TITLE = "採用を、勝てる構造に。"
SUB = "母集団形成から定着まで——データと学術で、候補者に選ばれる採用へ。"
HKICK = "Market Shift ／ 採用市場"
HTITLE = "中小の採用難易度は、大企業の約26倍"

# ============ 表紙 8案 ============
covers = {}

covers["C1 Charcoal Precision"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;"><div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div></div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal</div></div>
  <div style="position:absolute;left:72px;top:200px;width:900px;">
    <div class="en" style="font-size:12px;color:{RED};font-weight:700;margin-bottom:26px;">Tokumori RPO — 2026</div>
    <div class="jp" style="font-size:64px;font-weight:900;line-height:1.24;">採用を、<br>勝てる構造に。</div>
    <div style="width:44px;height:3px;background:{RED};margin:34px 0 22px;"></div>
    <div class="jp" style="font-size:16px;color:#B9BDC4;line-height:1.9;">{SUB}</div></div>
  <div style="position:absolute;right:-140px;top:150px;">{arc(460,2,RED,.85)}</div>
  <div style="position:absolute;right:-100px;top:190px;">{arc(380,1,"#FFFFFF",.18)}</div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HD};padding-top:18px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div><div class="en" style="font-size:11px;color:{GRAY};">Confidential</div></div>
  {tag("C1")}
</div>''', dark=True)

covers["C2 Swiss White"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px 48px 96px;">
  <div style="position:absolute;left:0;top:0;width:8px;height:720px;background:{RED};"></div>
  <div style="position:absolute;left:426px;top:0;width:1px;height:720px;background:{HL};"></div>
  <div style="position:absolute;left:780px;top:0;width:1px;height:720px;background:{HL};"></div>
  <div style="display:flex;justify-content:space-between;"><div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal — 2026</div></div>
  <div style="position:absolute;left:96px;top:212px;width:1000px;">
    <div class="jp" style="font-size:70px;font-weight:900;line-height:1.22;">採用を、<br>勝てる構造に。</div>
    <div class="jp" style="font-size:16px;color:#5F6570;line-height:1.9;margin-top:34px;">{SUB}</div></div>
  <div style="position:absolute;left:96px;right:72px;bottom:48px;display:flex;justify-content:space-between;border-top:1px solid {HL};padding-top:18px;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI ｜ 中途採用RPO ご提案</div>
    <div class="en" style="font-size:11px;color:{RED};font-weight:700;">Win by Structure</div></div>
  {tag("C2")}
</div>''')

covers["C3 Ink Panel"] = page(f'''
<div style="position:relative;width:1280px;height:720px;background:{PAPER};">
  <div style="position:absolute;left:0;top:0;width:512px;height:720px;background:{INK};padding:56px 48px;">
    <div style="display:flex;align-items:center;gap:12px;"><div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;color:#fff;">とくもり採用代行</div></div>
    <div class="jp" style="position:absolute;left:48px;top:236px;font-size:52px;font-weight:900;line-height:1.3;color:#fff;">採用を、<br>勝てる<br>構造に。</div>
    <div class="en" style="position:absolute;left:48px;bottom:52px;font-size:11px;color:{GRAY};">Recruitment Proposal</div></div>
  <div style="position:absolute;left:512px;top:0;right:0;height:720px;padding:56px 64px;color:{INK};">
    <div class="en" style="text-align:right;font-size:11px;color:{GRAY};">2026 — Chuto Saiyo RPO</div>
    <div style="position:absolute;left:64px;top:200px;">{arc(300,2,RED)}</div>
    <div class="jp" style="position:absolute;left:64px;top:420px;width:600px;font-size:16px;color:#3A3F47;line-height:2;">母集団形成から定着まで。<br>データと学術で、候補者に選ばれる採用へ。</div>
    <div style="position:absolute;left:64px;right:64px;bottom:48px;border-top:1px solid {HL};padding-top:16px;display:flex;justify-content:space-between;">
      <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div><div class="en" style="font-size:11px;color:{GRAY};">Confidential</div></div></div>
  {tag("C3")}
</div>''', bg=PAPER)

covers["C4 Deep Red Field"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;background:linear-gradient(160deg,#9E2D27 0%,{RED} 55%,#B94038 100%);color:#fff;">
  <div style="display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    <div class="en" style="font-size:11px;color:rgba(255,255,255,.7);">Recruitment Proposal</div></div>
  <div style="position:absolute;right:-160px;top:120px;">{arc(520,1.5,"#FFFFFF",.35)}</div>
  <div style="position:absolute;left:72px;top:220px;">
    <div class="en" style="font-size:12px;color:rgba(255,255,255,.75);font-weight:700;margin-bottom:26px;">Tokumori RPO — 2026</div>
    <div class="jp" style="font-size:64px;font-weight:900;line-height:1.24;">採用を、<br>勝てる構造に。</div>
    <div style="width:44px;height:3px;background:#fff;margin:32px 0 20px;"></div>
    <div class="jp" style="font-size:16px;color:rgba(255,255,255,.85);line-height:1.9;">{SUB}</div></div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid rgba(255,255,255,.25);padding-top:18px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:rgba(255,255,255,.7);">株式会社TOKUMORI</div>
    <div class="en" style="font-size:11px;color:rgba(255,255,255,.7);">Confidential</div></div>
  {tag("C4")}
</div>''', bg=RED)

covers["C5 Grid Paper"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;
  background-image:linear-gradient({HL} 1px,transparent 1px),linear-gradient(90deg,{HL} 1px,transparent 1px);
  background-size:80px 80px;background-position:36px 28px;">
  <div style="position:absolute;left:36px;top:28px;width:15px;height:15px;">
    <div style="position:absolute;left:7px;top:0;width:1.5px;height:15px;background:{RED};"></div>
    <div style="position:absolute;left:0;top:7px;width:15px;height:1.5px;background:{RED};"></div></div>
  <div style="display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal — 2026</div></div>
  <div style="position:absolute;left:72px;top:230px;">
    <div class="jp" style="font-size:66px;font-weight:900;line-height:1.24;">採用を、<br>勝てる構造に。</div>
    <div class="jp" style="font-size:16px;color:#5F6570;line-height:1.9;margin-top:30px;">{SUB}</div></div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;display:flex;justify-content:space-between;border-top:1px solid {HL};padding-top:18px;background:{PAPER};">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div>
    <div class="en" style="font-size:11px;color:{RED};font-weight:700;">Win by Structure</div></div>
  {tag("C5")}
</div>''')

covers["C6 Diagonal Cut"] = page(f'''
<div style="position:relative;width:1280px;height:720px;">
  <div style="position:absolute;inset:0;background:{PAPER};"></div>
  <div style="position:absolute;right:0;top:0;width:560px;height:720px;background:{INK};clip-path:polygon(230px 0,100% 0,100% 100%,0 100%);"></div>
  <div style="position:absolute;right:64px;bottom:220px;">{arc(300,2,RED,.9,True)}</div>
  <div style="position:relative;padding:56px 72px;color:{INK};">
    <div style="display:flex;align-items:center;gap:12px;"><div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div></div></div>
  <div style="position:absolute;left:72px;top:230px;width:640px;color:{INK};">
    <div class="en" style="font-size:12px;color:{RED};font-weight:700;margin-bottom:24px;">Tokumori RPO — 2026</div>
    <div class="jp" style="font-size:62px;font-weight:900;line-height:1.26;">採用を、<br>勝てる構造に。</div>
    <div class="jp" style="font-size:15.5px;color:#5F6570;line-height:1.9;margin-top:28px;width:560px;">{SUB}</div></div>
  <div class="en" style="position:absolute;right:72px;top:64px;font-size:11px;color:{GRAY};">Recruitment Proposal</div>
  <div style="position:absolute;left:72px;bottom:48px;color:{GRAY};" class="jp"><span style="font-size:12px;">株式会社TOKUMORI ｜ 2026</span></div>
  {tag("C6")}
</div>''', bg=PAPER)

covers["C7 Ink Dot Matrix"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;
  background:radial-gradient(circle at 85% 30%, #1D2027 0%, {INK} 55%);">
  <div style="position:absolute;right:56px;top:56px;width:420px;height:300px;
    background-image:radial-gradient(rgba(255,255,255,.22) 1.5px,transparent 1.5px);background-size:26px 26px;
    -webkit-mask-image:radial-gradient(ellipse 90% 90% at 70% 30%,#000 30%,transparent 75%);"></div>
  <div style="display:flex;justify-content:space-between;align-items:center;">
    <div style="display:flex;align-items:center;gap:12px;"><div style="width:10px;height:10px;background:{RED};"></div>
      <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div></div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal</div></div>
  <div style="position:absolute;left:72px;top:250px;">
    <div class="jp" style="font-size:62px;font-weight:900;line-height:1.26;">採用を、勝てる構造に。</div>
    <div style="display:flex;align-items:center;gap:18px;margin-top:30px;">
      <div style="width:44px;height:3px;background:{RED};"></div>
      <div class="jp" style="font-size:16px;color:#B9BDC4;">{SUB}</div></div></div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;border-top:1px solid {HD};padding-top:18px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Confidential</div></div>
  {tag("C7")}
</div>''', dark=True)

covers["C8 Grand Arc"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div style="position:absolute;left:-200px;bottom:-560px;">{arc(1680,2,RED,.55)}</div>
  <div style="position:absolute;left:-120px;bottom:-500px;">{arc(1520,1,INK,.12)}</div>
  <div style="display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:15px;font-weight:700;">とくもり採用代行</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Recruitment Proposal — 2026</div></div>
  <div style="position:absolute;left:0;right:0;top:250px;text-align:center;">
    <div class="en" style="font-size:12px;color:{RED};font-weight:700;margin-bottom:26px;">Tokumori RPO</div>
    <div class="jp" style="font-size:64px;font-weight:900;line-height:1.24;">採用を、勝てる構造に。</div>
    <div class="jp" style="font-size:16px;color:#5F6570;margin-top:26px;">{SUB}</div></div>
  <div style="position:absolute;left:72px;right:72px;bottom:48px;display:flex;justify-content:space-between;">
    <div class="jp" style="font-size:12px;color:{GRAY};">株式会社TOKUMORI</div>
    <div class="en" style="font-size:11px;color:{GRAY};">Confidential</div></div>
  {tag("C8")}
</div>''')

# ============ 本文ページ 6案（サンプル本文＝見出し＋ダミー図版スペース） ============
bodies = {}
PLACE = (f'<div style="margin-top:46px;width:1136px;height:300px;border:1px dashed {HL.replace("0.14","0.35")};'
         f'display:flex;align-items:center;justify-content:center;color:{GRAY};" class="jp">（本文・図表エリア）</div>')


def body_head(kick=HKICK, title=HTITLE, ink=INK, red=RED, gray_line=HL):
    return (f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<div style="width:22px;height:3px;background:{red};"></div>'
            f'<div class="en" style="font-size:11.5px;color:{red};font-weight:700;">{kick}</div></div>'
            f'<div class="jp" style="font-size:33px;font-weight:900;margin-top:16px;color:{ink};">{title}</div>')


def body_foot(dark=False):
    line = HD if dark else HL
    return (f'<div style="position:absolute;left:72px;right:72px;bottom:44px;border-top:1px solid {line};'
            f'padding-top:14px;display:flex;justify-content:space-between;">'
            f'<div class="jp" style="font-size:11px;color:{GRAY};">出典: リクルートワークス研究所 第42回(26卒) ／ マルゴト社2025</div>'
            f'<div class="num" style="font-size:12px;color:{GRAY};">06</div></div>')


bodies["B1 Plain Editorial"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  {body_head()}{PLACE}{body_foot()}{tag("B1")}
</div>''')

bodies["B2 Side Rail"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px 56px 96px;">
  <div style="position:absolute;left:0;top:0;width:6px;height:720px;background:{RED};"></div>
  <div style="position:absolute;left:6px;top:0;width:1px;height:720px;background:{HL};"></div>
  {body_head()}{PLACE}{body_foot()}{tag("B2")}
</div>''')

bodies["B3 Column Hairlines"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div style="position:absolute;left:436px;top:0;width:1px;height:720px;background:{HL};"></div>
  <div style="position:absolute;left:800px;top:0;width:1px;height:720px;background:{HL};"></div>
  {body_head()}{PLACE}{body_foot()}{tag("B3")}
</div>''')

bodies["B4 Footer Band"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  {body_head()}{PLACE}
  <div style="position:absolute;left:0;right:0;bottom:0;height:52px;background:{INK};display:flex;align-items:center;justify-content:space-between;padding:0 72px;">
    <div class="jp" style="font-size:11px;color:#9BA1AB;">出典: リクルートワークス研究所 第42回(26卒) ／ マルゴト社2025</div>
    <div class="en" style="font-size:11px;color:#9BA1AB;">Tokumori RPO — <span style="color:#fff;">06</span></div></div>
  {tag("B4")}
</div>''')

bodies["B5 Ghost Number"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  <div class="num" style="position:absolute;right:20px;top:-70px;font-size:330px;font-weight:900;color:transparent;
    -webkit-text-stroke:1.5px rgba(21,23,28,.10);line-height:1;">01</div>
  {body_head()}{PLACE}{body_foot()}{tag("B5")}
</div>''')

bodies["B6 Dark Content"] = page(f'''
<div style="position:relative;width:1280px;height:720px;padding:56px 72px;">
  {body_head(ink="#FFFFFF")}
  <div style="margin-top:46px;width:1136px;height:300px;border:1px dashed rgba(255,255,255,.3);display:flex;align-items:center;justify-content:center;color:{GRAY};" class="jp">（本文・図表エリア）</div>
  {body_foot(dark=True)}{tag("B6")}
</div>''', dark=True)


def main():
    slides = list(covers.items()) + list(bodies.items())
    paths = []
    for name, html in slides:
        p = "/tmp/bgcat_%s.html" % name.split(" ")[0]
        open(p, "w", encoding="utf-8").write(html)
        paths.append(p)
    pid, url = H.insert_many(paths, title="TOKUMORI ｜ ① 背景カタログ（表紙8＋本文6）",
                             slide_id=os.environ.get("SLIDE_ID"), dpi=3)
    print("BG CATALOG:", url)


if __name__ == "__main__":
    main()
