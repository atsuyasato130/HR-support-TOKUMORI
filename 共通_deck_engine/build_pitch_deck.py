#!/usr/bin/env python3
"""ピッチ/概要資料の「デジタル・モダン版」＝dark canvas＋ゴシック＋等幅数値＋赤グロー。

最近のSaaS/スタートアップ・ピッチの空気。背景の赤グロー＋ドットグリッドはHTML画像（ハイブリッド）、
見出し・数値・本文はネイティブの編集可能テキスト。ダーク上はロゴ＝ワードマーク表記。
"""
import os
import json
import uuid
import math
import random
import warnings

warnings.filterwarnings("ignore")
from googleapiclient.discovery import build

import build_slides as bs
import html_to_slide as H
import figs_html as FH
from build_slides import IN, PW, PH, MX, CW

# ---- パレット（MODE=light 既定／dark も可） ----
MODE = os.environ.get("MODE", "light")
PAL = {
 "dark":  dict(BG="121110", PANEL="1C1A18", BORDER="302B27", TXT="F2EFEC", MUT="A39B94", FAINT="6E665F",
               ACC="E04B3C", CARD="1C1A18", CON="4A433C", NUM="7E766E",
               GLOW="rgba(224,75,60,0.22)", GLOW2="rgba(224,75,60,0.10)", DOT="rgba(255,255,255,0.05)"),
 "light": dict(BG="FCFBFA", PANEL="FFFFFF", BORDER="EAE5E1", TXT="1A1714", MUT="6B6B6B", FAINT="A8A099",
               ACC="AF322C", CARD="FFFFFF", CON="C7BFB9", NUM="A8A099",
               GLOW="rgba(175,50,44,0.08)", GLOW2="rgba(175,50,44,0.05)", DOT="rgba(26,23,20,0.045)"),
 # cool＝冷たいクリスプな地(画面っぽい)＋電光バーミリオン＋微かなクール青の対トーン（デュオトーン・グロー）
 "cool":  dict(BG="F6F8FB", PANEL="FFFFFF", BORDER="E3E7EE", TXT="151A22", MUT="586273", FAINT="98A1AF",
               ACC="EC3B29", CARD="FFFFFF", CON="C3CAD5", NUM="98A1AF",
               GLOW="rgba(236,59,41,0.10)", GLOW2="rgba(38,96,214,0.06)", DOT="rgba(21,26,34,0.05)"),
 # vivid＝純白＋明るい赤を強めのグローで（高コントラスト・クリーン）
 "vivid": dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="ECE9E6", TXT="121212", MUT="6B6B6B", FAINT="ABA39C",
               ACC="F23B27", CARD="FFFFFF", CON="CFC9C3", NUM="ABA39C",
               GLOW="rgba(242,59,39,0.13)", GLOW2="rgba(242,59,39,0.06)", DOT="rgba(20,20,20,0.045)"),
 # soft＝学生向け＝メディア「とくもり就活」globals.css 準拠（白＋クールグレー＋ブランド赤＋明朝見出し＝媒体と同じ世界観）
 "soft":  dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="E5E7EC", TXT="17181C", MUT="6A6E78", FAINT="A8ACB5",
               ACC="AF322C", CARD="FFFFFF", CON="C7CBD2", NUM="A8ACB5",
               GLOW="rgba(175,50,44,0.07)", GLOW2="rgba(226,87,74,0.06)", DOT="rgba(36,28,23,0.06)",
               HEAD="Shippori Mincho", BODY="Noto Sans JP", MONO="IBM Plex Mono"),
 # media＝赤×黒を大胆に。表紙/CTA=黒のダークヒーロー（白グリッド＋赤）、本文=白＋黒フッター＋ブランド赤
 "media": dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="E5E7EC", TXT="17181C", MUT="6A6E78", FAINT="A8ACB5",
               ACC="AF322C", CARD="FFFFFF", CON="C7CBD2", NUM="A8ACB5",
               GLOW="rgba(175,50,44,0.07)", GLOW2="rgba(226,87,74,0.06)", DOT="rgba(36,28,23,0.06)"),
 # shu＝白×ブランド赤の強いグラデ・ヒーロー（余白＝上品/ロゴ向き＋赤を強く）。ダーク文字
 "shu":   dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="EDE6E3", TXT="17181C", MUT="6A6E78", FAINT="B7AEA8",
               ACC="AF322C", CARD="FFFFFF", CON="CFC9C3", NUM="B7AEA8",
               GLOW="rgba(175,50,44,0.10)", GLOW2="rgba(175,50,44,0.06)", DOT="rgba(36,28,23,0.05)"),
 # aura＝elu風（超ミニマル白・大余白・極薄ゴースト大見出し）×TOKUMORI。記憶に残る一点＝単色赤の生成スワール
 "aura":  dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="ECEEF1", TXT="15171C", MUT="667085", FAINT="98A1AF",
               ACC="AF322C", CARD="FFFFFF", CON="C7CBD2", NUM="AEB3BC", GHOST="AEB3BC",
               GLOW="rgba(175,50,44,0.05)", GLOW2="rgba(175,50,44,0.03)", DOT="rgba(21,23,28,0.035)"),
 # ao＝とくもり採用代行ブランド（青）。白×ロイヤルブルー#3D5AE0の強グラデ・ヒーロー（余白＝上品/ロゴ向き）。赤は一切使わない
 "ao":    dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="E4E7EF", TXT="16181D", MUT="5C6373", FAINT="A6AEBE",
               ACC="3D5AE0", CARD="FFFFFF", CON="C3CAD5", NUM="A6AEBE",
               GLOW="rgba(61,90,224,0.10)", GLOW2="rgba(27,42,107,0.06)", DOT="rgba(22,24,29,0.05)"),
 # consult＝コンサル/think-cell型。白地・紺#1F3A5Cを構造色・institutionalフォント・フラット・高密度。グラデ/角丸/ピル/英語eyebrowは禁止（ANTI_AI_TELLS.md）
 "consult": dict(BG="FFFFFF", PANEL="F4F6F9", BORDER="D7DCE4", TXT="1A2230", MUT="5A6472", FAINT="9AA3B0",
                ACC="1F3A5C", CARD="FFFFFF", CON="9AA3B0", NUM="1F3A5C",
                GLOW="rgba(31,58,92,0.05)", GLOW2="rgba(31,58,92,0.03)", DOT="rgba(26,34,48,0.04)",
                HEAD="BIZ UDPGothic", BODY="Noto Sans JP", MONO="BIZ UDPGothic", WARM="B4532B"),
 # edit＝A案：エディトリアル特大タイポ（ライト）。白地・大余白・ブランド1色・巨大見出し/数字が主役。SpeakerDeck系
 "edit": dict(BG="FBFAF8", PANEL="F3F1ED", BORDER="E5E2DC", TXT="14161A", MUT="6B6F78", FAINT="A9A49C",
              ACC="3D5AE0", CARD="FFFFFF", CON="C9C4BC", NUM="A9A49C",
              GLOW="rgba(0,0,0,0)", GLOW2="rgba(0,0,0,0)", DOT="rgba(0,0,0,0)",
              HEAD="Zen Kaku Gothic New", BODY="Zen Kaku Gothic New", MONO="Lato"),
 # block＝B案：色面ブロック/Canva系（ライト）。ブランド色ベタ面と白の対比・反転特大タイポ・器アーチ・大胆
 "block": dict(BG="FFFFFF", PANEL="F3F1ED", BORDER="E5E2DC", TXT="14161A", MUT="6B6F78", FAINT="A9A49C",
               ACC="3D5AE0", CARD="FFFFFF", CON="C9C4BC", NUM="A9A49C",
               GLOW="rgba(0,0,0,0)", GLOW2="rgba(0,0,0,0)", DOT="rgba(0,0,0,0)",
               HEAD="Zen Kaku Gothic New", BODY="Zen Kaku Gothic New", MONO="Lato"),
 # modern＝採用ハイブリッド：A(エディトリアル白地)を基本＋B(色面ブロック)を表紙/章扉/KPIに。赤#af322c主・青#3D5AE0従
 "modern": dict(BG="FBFAF8", PANEL="F3F1ED", BORDER="E5E2DC", TXT="14161A", MUT="6B6F78", FAINT="A9A49C",
                ACC="AF322C", ACC2="3D5AE0", CARD="FFFFFF", CON="C9C4BC", NUM="A9A49C",
                GLOW="rgba(0,0,0,0)", GLOW2="rgba(0,0,0,0)", DOT="rgba(0,0,0,0)",
                HEAD="Zen Kaku Gothic New", BODY="Zen Kaku Gothic New", MONO="Lato"),
 # simple＝【2026-07-03確定・本番標準】極限シンプル：白・装飾ゼロ・palt・Noto Sans JP+Lato数字・赤は要所のみ。
 # テキストは全てネイティブ（編集可）・図のみHTMLハイブリッド（図解カタログF01-F80基準）
 "simple": dict(BG="FFFFFF", PANEL="FFFFFF", BORDER="E8E6E2", TXT="15171C", MUT="8A8F98", FAINT="B9BDC4",
                ACC="AF322C", CARD="FFFFFF", CON="C9C6C0", NUM="8A8F98",
                GLOW="rgba(0,0,0,0)", GLOW2="rgba(0,0,0,0)", DOT="rgba(0,0,0,0)",
                HEAD="Noto Sans JP", BODY="Noto Sans JP", MONO="Lato"),
}[MODE if MODE in ("dark", "light", "cool", "vivid", "soft", "media", "shu", "aura", "ao", "consult", "edit", "block", "modern", "simple") else "light"]
BG = PAL["BG"]; PANEL = PAL["PANEL"]; BORDER = PAL["BORDER"]; TXT = PAL["TXT"]
MUT = PAL["MUT"]; FAINT = PAL["FAINT"]; ACC = PAL["ACC"]
# BRAND＝ブランド色の切替（blue=とくもり採用代行 / red=TOKUMORI公式#af322c）。ACCを上書き
BRAND = os.environ.get("BRAND")
if BRAND == "red":
    ACC = "AF322C"
elif BRAND == "blue":
    ACC = "3D5AE0"
PAL["ACC"] = ACC
# フォントは用途別に変えてOK（ユーザー許可）。既定=IBM Plex（統一・デジタル）、PALにHEAD/BODY/MONO指定で上書き
HEAD = PAL.get("HEAD", "IBM Plex Sans JP")
BODY = PAL.get("BODY", "IBM Plex Sans JP")
MONO = PAL.get("MONO", "IBM Plex Mono")
IMG_URL = "https://drive.google.com/uc?export=download&id=%s"
LOGO = os.environ.get("LOGO")  # ロゴPNGパス（指定時：全スライド左上のワードマークを画像ロゴに差し替え）
LOGO_URL = None                # main() でDriveにアップ後に設定（wordmark から参照）


def font_link(*families):
    # Google Fonts の <link>（HTMLハイブリッド図で用途別フォントを読み込む）
    seen = []
    for f in families:
        if f not in seen:
            seen.append(f)
    q = "&".join("family=" + f.replace(" ", "+") + ":wght@400;500;700" for f in seen)
    return '<link href="https://fonts.googleapis.com/css2?' + q + '&display=swap" rel="stylesheet"/>'

# MODE=soft ＝ メディアのソフト・フューチャー背景を全スライドに敷く（=背景で“強さ”）
BGALL = (MODE == "soft")
# MODE=media ＝ 赤主体のグラデーション・ヒーロー（表紙/CTA）＋本文に深赤フッターバー
HERO_DARK = (MODE == "media")
SHU = (MODE == "shu")     # 朱×白の明るいグラデ・ヒーロー（ダーク文字・余白・ロゴ向き）
AO = (MODE == "ao")       # とくもり採用代行（青）：白×ロイヤルブルーの強グラデ・ヒーロー（ダーク文字・余白・ロゴ向き）
AURA = (MODE == "aura")   # elu風：超ミニマル白＋大余白＋極薄ゴースト大見出し＋単色赤スワール
AIRY = AURA               # 余白を増やし見出しを軽量化する（elu風の“呼吸”）
CONSULT = (MODE == "consult")  # コンサル/think-cell型：紺・フラット・高密度・出典脚注・アクションタイトル
EDIT = (MODE == "edit")        # A案：エディトリアル特大タイポ（ライト・大余白・ブランド1色）
BLOCK = (MODE == "block")      # B案：色面ブロック/Canva系（ライト・反転特大タイポ・器アーチ）
HYBRID = (MODE == "modern")    # 採用ハイブリッド：A基本＋B(表紙/章扉/KPI)。赤主・青従
SIMPLE = (MODE == "simple")    # 【本番標準】極限シンプル：白・装飾ゼロ・全テキスト編集可・図のみHTML
MODERN = EDIT or BLOCK or HYBRID or SIMPLE
HBLOCK = BLOCK or HYBRID       # 表紙/章扉/KPIヒーローを色面ブロックで出す
ACC2 = PAL.get("ACC2", ACC)    # 副アクセント（modern=青）。BRANDと独立
if BRAND == "red":
    ACC2 = "3D5AE0"
elif BRAND == "blue":
    ACC2 = "AF322C"
RND = (not CONSULT)            # 角丸の可否（consultはフラット＝角丸なし）
WARM = PAL.get("WARM", ACC)    # 稀少な暖色アクセント（"効く1数字"のみ・consult用）
HERO_BG = "8F231F"        # ヒーロー下地（グラデの濃い側＝深い赤）
HERO_TXT = "FFFFFF"       # 赤地の上の見出し（白）
HERO_SUB = "F4DCD8"       # 赤地の上のサブ（明るいローズ）
HERO_META = "E6C4BF"      # 赤地の上のメタ（淡い）
FOOT_RED = "8F231F"       # フッターバー＝深い赤（黒すぎ回避・赤主体）
# 統一ヘッダー位置（全コンテンツ・スライド共通＝タイトルの高さ/サイズを必ず揃える）
KICK_Y = int(0.98*IN); TITLE_Y = int(1.26*IN); RULE_Y = int(1.88*IN); TITLE_SIZE = 26
# 本文バンド：罫のすぐ下から始め、やや上寄りに中央化（隙間を詰める＝本題を少し上に）
# consult＝ロゴ無し・ヘッダを上げるので本文帯も上に拡張（1.64"開始）／simple＝1.9"開始
BODY_TOP = int((2.4 if MODE in ("edit", "block", "modern") else (1.64 if MODE == "consult" else (1.9 if MODE == "simple" else 2.0)))*IN); BODY_BOT = int(4.92*IN)
def ctop(h): return BODY_TOP + max(0, int((BODY_BOT - BODY_TOP - h) * 0.28))


def glow_bg_html():
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;}'
            '.c{width:1280px;height:720px;background:'
            'radial-gradient(58%% 60%% at 82%% 88%%, %s, rgba(0,0,0,0) 70%%),'
            'radial-gradient(46%% 50%% at 12%% 6%%, %s, rgba(0,0,0,0) 70%%),'
            '#%s;}'
            '.g{width:1280px;height:720px;'
            'background-image:radial-gradient(circle, %s 1px, transparent 1.4px);'
            'background-size:36px 36px;}'
            '</style></head><body><div class="c"><div class="g"></div></div></body></html>'
            % (PAL["GLOW"], PAL["GLOW2"], PAL["BG"], PAL["DOT"]))


def softfv_bg_html():
    # メディア globals.css `.softfv` を忠実移植：赤/emberのラジアルブロブ＋放射マスクのドット＋漂う光ブロブ
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;}'
            '.c{position:relative;width:1280px;height:720px;overflow:hidden;background:'
            'radial-gradient(125% 90% at 100% -10%, rgba(175,50,44,0.07), transparent 55%),'
            'radial-gradient(80% 60% at -10% 110%, rgba(226,87,74,0.06), transparent 55%),'
            '#ffffff;}'
            '.c::before{content:"";position:absolute;inset:0;'
            'background-image:radial-gradient(rgba(36,28,23,0.06) 1px, transparent 1px);'
            'background-size:22px 22px;'
            '-webkit-mask-image:radial-gradient(ellipse 70% 60% at 50% 35%, #000 30%, transparent 75%);'
            'mask-image:radial-gradient(ellipse 70% 60% at 50% 35%, #000 30%, transparent 75%);}'
            '.c::after{content:"";position:absolute;width:40rem;height:40rem;right:-8rem;top:-14rem;'
            'border-radius:9999px;background:radial-gradient(circle, rgba(226,87,74,0.18), transparent 62%);'
            'filter:blur(44px);}'
            '</style></head><body><div class="c"></div></body></html>')


def shu_bg_html():
    # 朱×白の明るいグラデ：右下から朱の温かいブルームが立ち上がり、見出しのある左上は白へ抜ける＝余白・上品
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;}'
            '.c{position:relative;width:1280px;height:720px;overflow:hidden;background:'
            'radial-gradient(124% 140% at 110% 118%, rgba(175,50,44,0.95), transparent 66%),'   # ブランド赤の強ブルーム（右下・主役）
            'radial-gradient(88% 98% at 104% 40%, rgba(175,50,44,0.45), transparent 60%),'        # 右側へ押し上げ（赤を広く）
            'radial-gradient(58% 70% at -4% -12%, rgba(175,50,44,0.10), transparent 56%),'         # 淡い左上（見出し帯は明るく残す）
            '#ffffff;}'
            '.c::before{content:"";position:absolute;inset:0;'
            'background-image:radial-gradient(rgba(255,255,255,0.10) 1px, transparent 1px);background-size:24px 24px;'
            '-webkit-mask-image:radial-gradient(ellipse 80% 70% at 70% 75%, #000 30%, transparent 80%);'
            'mask-image:radial-gradient(ellipse 80% 70% at 70% 75%, #000 30%, transparent 80%);}'
            '</style></head><body><div class="c"></div></body></html>')


def ao_bg_html():
    # 白×ロイヤルブルーの明るいグラデ：右下から青の温かいブルームが立ち上がり、見出しのある左上は白へ抜ける＝余白・上品・ロゴ向き
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;}'
            '.c{position:relative;width:1280px;height:720px;overflow:hidden;background:'
            'radial-gradient(124% 140% at 110% 118%, rgba(61,90,224,0.92), transparent 66%),'   # ロイヤルブルーの強ブルーム（右下・主役）
            'radial-gradient(88% 98% at 104% 40%, rgba(40,58,150,0.46), transparent 60%),'        # 右側へ押し上げ（深紺で奥行き）
            'radial-gradient(58% 70% at -4% -12%, rgba(61,90,224,0.08), transparent 56%),'         # 淡い左上（見出し帯は明るく残す）
            '#ffffff;}'
            '.c::before{content:"";position:absolute;inset:0;'
            'background-image:radial-gradient(rgba(255,255,255,0.10) 1px, transparent 1px);background-size:24px 24px;'
            '-webkit-mask-image:radial-gradient(ellipse 80% 70% at 70% 75%, #000 30%, transparent 80%);'
            'mask-image:radial-gradient(ellipse 80% 70% at 70% 75%, #000 30%, transparent 80%);}'
            '</style></head><body><div class="c"></div></body></html>')


def herogrid_bg_html():
    # 赤主体のグラデーション・ヒーロー：深い赤→明るい赤の斜めグラデ＋温かいember光＋白の細グリッド（上にフェード）
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;}'
            '.c{position:relative;width:1280px;height:720px;overflow:hidden;background:'
            'radial-gradient(75% 95% at 82% 118%, rgba(245,128,98,0.42), transparent 58%),'   # 温かいember光（右下）
            'radial-gradient(60% 70% at 6% -12%, rgba(120,28,22,0.55), transparent 60%),'      # 深い赤の影（左上）
            'linear-gradient(122deg, #6E1C17 0%, #97271F 46%, #B83A30 100%);}'                 # 深→明の赤グラデ
            '.g{position:absolute;inset:0;'
            'background-image:linear-gradient(rgba(255,255,255,0.07) 1px, transparent 1px),'
            'linear-gradient(90deg, rgba(255,255,255,0.07) 1px, transparent 1px);'
            'background-size:46px 46px;'
            '-webkit-mask-image:radial-gradient(ellipse 90% 80% at 50% 0%, #000 35%, transparent 82%);'
            'mask-image:radial-gradient(ellipse 90% 80% at 50% 0%, #000 35%, transparent 82%);}'
            '</style></head><body><div class="c"><div class="g"></div></div></body></html>')


def aura_swirl_svg(size=820, seed=11):
    # ギヨシェ・ロゼッタ（スピログラフ＝ハイポトロコイドの花/リング）を少しずつ回転して重ね、花弁を細線の帯に。
    # 中央に穴。色＝赤を主役にしたオーロラ調の縦グラデ（金→琥珀→珊瑚→★ブランド赤→臙脂→薔薇）。控えめ・淡く。
    cx = cy = size / 2.0
    R, r, d = 13, 8, 9
    rev = r // math.gcd(R, r)
    rad = size * 0.46; sc = rad / (abs(R - r) + d)

    def hpath(rot):
        pts = []
        steps = rev * 240
        for i in range(steps + 1):
            t = i / steps * 2 * math.pi * rev
            x = (R - r) * math.cos(t) + d * math.cos((R - r) / r * t)
            y = (R - r) * math.sin(t) - d * math.sin((R - r) / r * t)
            xr = x * math.cos(rot) - y * math.sin(rot); yr = x * math.sin(rot) + y * math.cos(rot)
            pts.append(f"{cx + xr * sc:.1f},{cy + yr * sc:.1f}")
        return "M" + " L".join(pts)

    K = 14
    paths = "".join(
        f'<path d="{hpath((j - (K - 1) / 2.0) * 0.024)}" fill="none" stroke="url(#ag)" '
        f'stroke-width="0.65" opacity="0.5"/>' for j in range(K))
    stops = "".join('<stop offset="%s" stop-color="#%s"/>' % s for s in
                    [("0%", "E8B24A"), ("20%", "E0894A"), ("40%", "D2553A"),
                     ("58%", "AF322C"), ("76%", "8E2741"), ("100%", "B0467E")])
    inner = (
        '<defs>'
        f'<linearGradient id="ag" x1="0%" y1="0%" x2="100%" y2="100%">{stops}</linearGradient>'
        '<filter id="agl" x="-25%" y="-25%" width="150%" height="150%"><feGaussianBlur stdDeviation="5"/></filter>'
        f'<g id="ar">{paths}</g>'
        '</defs>'
        '<use href="#ar" filter="url(#agl)" opacity="0.4"/>'   # 柔らかい発光
        '<use href="#ar"/>'                                    # シャープな帯
    )
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{inner}</svg>'


def aura_bg_html():
    # elu風：白＋右に“魂っぽい”発光多色オーラ＋極淡い多色グロー（cover/CTAの下地。本文は白＝大余白）
    # データ会社感：右下コーナーから断ち切れでロゼッタを覗かせ、暖色グロー（右下）＋淡い対角グロー（左上）に溶かす。
    # さらに薄いプロット・ドットグリッド（右下に寄せてフェード）で“精緻・データ”の質感。全体は白＝大余白。
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>'
            '*{margin:0;}html,body{width:1280px;height:720px;background:#FFFFFF;}'
            '.c{position:relative;width:1280px;height:720px;overflow:hidden;background:'
            'radial-gradient(50% 58% at 96% 96%, rgba(224,122,78,0.13), transparent 60%),'    # 右下＝主役の暖色グロー
            'radial-gradient(32% 40% at 92% 80%, rgba(175,50,44,0.08), transparent 66%),'      # 右下に赤を重ねる
            'radial-gradient(42% 48% at 4% 4%, rgba(201,78,110,0.05), transparent 62%),'        # 左上＝対角の淡いグロー（融合）
            '#FFFFFF;}'
            '.g{position:absolute;inset:0;'
            'background-image:radial-gradient(circle, rgba(21,23,28,0.05) 1px, transparent 1.5px);'
            'background-size:34px 34px;'
            '-webkit-mask-image:radial-gradient(ellipse 78% 78% at 90% 88%, #000 0%, transparent 62%);'
            'mask-image:radial-gradient(ellipse 78% 78% at 90% 88%, #000 0%, transparent 62%);}'
            '.s{position:absolute;right:-228px;bottom:-228px;opacity:0.82;}'
            '</style></head><body><div class="c"><div class="g"></div>'
            '<div class="s">' + aura_swirl_svg() + '</div></div></body></html>')


def flow_fig_html(steps, accent=2):
    n = len(steps)
    cards = ""
    for i, (num, title, desc) in enumerate(steps):
        x = 40 + i * 305
        acc = (i == accent)
        fillc = "#" + PAL["CARD"]
        bd = "#" + ACC if acc else "#" + BORDER
        nc = "#" + ACC if acc else "#" + PAL["NUM"]; tc = "#" + TXT; dc = "#" + MUT
        cards += (
            f'<g transform="translate({x},44)">'
            f'<rect x="0" y="0" width="270" height="200" rx="16" fill="{fillc}" stroke="{bd}" stroke-width="{1.6 if acc else 1}"/>'
            f'<text x="22" y="56" font-family="{MONO}" font-size="22" font-weight="500" fill="{nc}">{num}</text>'
            f'<line x1="22" y1="72" x2="50" y2="72" stroke="{nc}" stroke-width="2"/>'
            f'<text x="22" y="112" font-family="{HEAD}" font-size="21" font-weight="700" fill="{tc}">{title}</text>'
            f'<text x="22" y="150" font-family="{BODY}" font-size="13.5" fill="{dc}"><tspan x="22" dy="0">{desc[:13]}</tspan><tspan x="22" dy="22">{desc[13:]}</tspan></text>'
            f'</g>')
        if i < n - 1:
            ax = 40 + i * 305 + 270
            cards += f'<line x1="{ax+4}" y1="144" x2="{ax+27}" y2="144" stroke="#{PAL["CON"]}" stroke-width="1.5" marker-end="url(#pa)"/>'
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + font_link(HEAD, BODY, MONO) +
            '<style>*{margin:0;}html,body{width:1280px;height:300px;background:#' + PAL["BG"] + ';}svg{display:block;}</style>'
            '</head><body><svg width="1280" height="300" viewBox="0 0 1280 300">'
            '<defs><marker id="pa" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto">'
            '<path d="M0,0 L9,4.5 L0,9 Z" fill="#' + PAL["CON"] + '"/></marker></defs>' + cards + '</svg></body></html>')


def twolist_maxlen(cols):
    return max([len(str(it)) for c in cols for it in c.get("items", [])] + [1])


def twolist_fig_html(cols, accent=None):
    # HTMLでデザインした2カラム対比図（見出し＝アクセント下線／項目＝角丸ドット＋折返しテキスト）。
    # 最長項目の文字数に応じて本文サイズを可変（状況に応じてサイズを変える＝不自然な2行崩れを防ぐ）。
    acc = "#" + (accent or ACC)
    ml = twolist_maxlen(cols)
    fs = 25 if ml <= 12 else (23 if ml <= 18 else (21 if ml <= 24 else (19 if ml <= 30 else 17)))
    mb = 26 if fs >= 21 else 20
    colhtml = ""
    for c in cols:
        lis = "".join('<li><span class="b"></span><span class="t">%s</span></li>' % it for it in c.get("items", []))
        colhtml += '<div class="col"><div class="h">%s</div><ul>%s</ul></div>' % (c.get("title", ""), lis)
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + font_link(HEAD, BODY) +
            '<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;background:#%s;}'
            '.wrap{display:flex;gap:64px;padding:8px 6px;}.col{flex:1;min-width:0;}'
            '.h{font-family:%s;font-weight:700;font-size:29px;color:#%s;padding-bottom:14px;'
            'border-bottom:3px solid %s;margin-bottom:30px;}'
            'ul{list-style:none;}li{display:flex;align-items:flex-start;gap:16px;margin-bottom:%dpx;}'
            '.b{flex:0 0 auto;width:11px;height:11px;border-radius:3px;background:%s;margin-top:%dpx;}'
            '.t{font-family:%s;font-size:%dpx;line-height:1.55;color:#%s;}'
            '</style></head><body><div class="wrap">%s</div></body></html>'
            % (BG, HEAD, TXT, acc, mb, acc, int(fs*0.42), BODY, fs, TXT, colhtml))


# ---- ダーク用ネイティブ部品 ----
def wordmark(dk, sid):
    if LOGO_URL:  # 公式ロゴ画像を左上に配置（アスペクト 774:148 を維持）
        lh = int(0.27*IN); lw = int(lh*774/148)
        bgimg(dk, sid, LOGO_URL, w=lw, h=lh, x=MX, y=int(0.36*IN))
        return
    dk.rect(sid, MX, int(0.46*IN), int(0.12*IN), int(0.12*IN), fill=ACC, shape="ELLIPSE")
    dk.text(sid, MX+int(0.26*IN), int(0.36*IN), int(3*IN), int(0.3*IN),
            [("TOKUMORI", {"size": 11, "color": TXT, "bold": True, "font": MONO})], valign="MIDDLE")


def head(dk, sid, kick, title):
    # 統一ヘッダー：ワードマーク＋kicker＋タイトル(固定サイズ＝全スライド共通・fitで縮めない)＋細罫
    if not (CONSULT or SIMPLE):  # consult/simpleは本文ページのロゴを廃し、ヘッダを上に詰める
        wordmark(dk, sid)
    if SIMPLE:
        # 極限シンプル：赤kicker（和文13pt）＋見出し27pt。罫線・tick・ロゴなし（H01-H12基準）
        dk.text(sid, MX, int(0.5*IN), CW, int(0.26*IN),
                [(kick, {"size": 12.5, "color": ACC, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(0.84*IN), CW, int(0.84*IN),
                [(title, {"size": 27, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(27, 17))
        return
    if MODERN:
        # モダン（エディトリアル）ヘッダ：赤の小kicker＋大きめ見出し（罫/tickは置かず＝タイポ階層で見せる）。
        # kickerの左に短い赤tickをインラインで（2行見出しと衝突しない）。
        dk.rect(sid, MX, int(1.06*IN), int(0.24*IN), int(0.045*IN), fill=ACC)
        dk.text(sid, MX+int(0.34*IN), int(0.98*IN), CW-int(0.34*IN), int(0.26*IN),
                [(kick, {"size": 10.5, "color": ACC, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(1.34*IN), CW, int(0.9*IN),
                [(title, {"size": 24, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(24, 15))
        return
    if CONSULT:
        # コンサル型：ロゴ無しでヘッダを上に詰める。章番号eyebrid（紺・小tick付）＋アクションタイトル＋紺の細罫
        dk.rect(sid, MX, int(0.56*IN), int(0.22*IN), int(0.045*IN), fill=ACC)
        dk.text(sid, MX+int(0.32*IN), int(0.48*IN), CW-int(0.32*IN), int(0.24*IN),
                [(kick, {"size": 10, "color": ACC, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(0.82*IN), CW, int(0.66*IN),
                [(title, {"size": 22, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(22, 15))
        dk.rect(sid, MX, int(1.52*IN), CW, 19050, fill=ACC)
        return
    dk.text(sid, MX, KICK_Y, CW, int(0.24*IN),
            [(kick, {"size": 9.5, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX, TITLE_Y, CW, int(0.5*IN),
            [(title, {"size": TITLE_SIZE, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.rect(sid, MX, RULE_Y, CW, 9525, fill=BORDER)


def foot_d(dk, sid, tag, page):
    if MODERN:  # モダンは装飾を抑え、ページ番号のみ（罫やブランドバーを置かない）
        dk.text(sid, PW-MX-int(1.2*IN), PH-int(0.5*IN), int(1.2*IN), int(0.3*IN),
                [("%02d" % page, {"size": 9, "color": FAINT, "font": MONO})], align="END", valign="MIDDLE")
        return
    if HERO_DARK:  # 深い赤のフッターバー（全幅）＝赤主体で全スライドに赤を通す
        by = PH-int(0.44*IN)
        dk.rect(sid, 0, by, PW, int(0.44*IN), fill=FOOT_RED)
        dk.text(sid, MX, by, CW-int(1*IN), int(0.44*IN),
                [("TOKUMORI", {"size": 8.5, "color": "FFFFFF", "bold": True, "font": MONO}),
                 ("  "+tag, {"size": 8, "color": "E7C9C5", "font": MONO})], valign="MIDDLE")
        dk.text(sid, PW-MX-int(1.2*IN), by, int(1.2*IN), int(0.44*IN),
                [("%02d" % page, {"size": 8, "color": "E7C9C5", "font": MONO})], align="END", valign="MIDDLE")
        return
    dk.rect(sid, MX, PH-int(0.5*IN), CW, 9525, fill=BORDER)
    dk.text(sid, MX, PH-int(0.44*IN), CW-int(1*IN), int(0.3*IN),
            [("TOKUMORI", {"size": 8.5, "color": ACC, "bold": True, "font": MONO}),
             ("  "+tag, {"size": 8, "color": MUT, "font": MONO})], valign="MIDDLE")
    dk.text(sid, PW-MX-int(1.2*IN), PH-int(0.44*IN), int(1.2*IN), int(0.3*IN),
            [("%02d" % page, {"size": 8, "color": MUT, "font": MONO})], align="END", valign="MIDDLE")


def pill(dk, sid, x, y, w, text):
    dk.rect(sid, x, y, w, int(0.34*IN), line=ACC, lw=1.0, round=RND)
    dk.text(sid, x, y, w, int(0.34*IN), [(text, {"size": 9.5, "color": ACC, "bold": True, "font": MONO})],
            align="CENTER", valign="MIDDLE")


def callout_d(dk, sid, body, y=int(3.98*IN)):
    h = int(0.8*IN)
    if CONSULT:
        # 結論（So-What）：ラベルは置かず、左に紺の細バー＋太字の結論のみ（テンプレ/AI感を消す）
        hh = int(0.6*IN)
        dk.rect(sid, MX, y+int(0.02*IN), int(0.05*IN), hh-int(0.04*IN), fill=ACC)
        dk.text(sid, MX+int(0.26*IN), y, CW-int(0.26*IN), hh,
                [(body, {"size": 14, "color": TXT, "bold": True, "font": BODY})], valign="MIDDLE", fit=(14, 10))
        return
    dk.rect(sid, MX, y+int(0.03*IN), int(0.026*IN), h-int(0.06*IN), fill=ACC)
    dk.text(sid, MX+int(0.26*IN), y, CW-int(0.3*IN), int(0.24*IN),
            [("要点", {"size": 9, "color": MUT, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX+int(0.26*IN), y+int(0.25*IN), CW-int(0.34*IN), h-int(0.25*IN),
            [(body, {"size": 13.5, "color": TXT, "font": BODY})], valign="TOP", fit=(13.5, 10))


# ---------- コンテンツ・スペック（テーマ=MODE × 内容=SPEC で量産。env SPEC=path.json で内容差し替え） ----------
DEFAULT_SPEC = {
    "title_doc": "TOKUMORI ｜ サービス概要",
    "tag": "SERVICE OVERVIEW",
    "cover": {"kicker": "SERVICE OVERVIEW ・ 2026", "title": "採用を、データで強くする。",
              "subtitle": "母集団形成から定着まで——人とデータで伴走するHRパートナー。", "org": "株式会社TOKUMORI"},
    "slides": [
        {"type": "bullets", "kicker": "ISSUE ・ 採用の現場", "title": "“採れない・続かない”は構造の問題",
         "items": ["母集団形成が難しく、要件に合う候補者に出会えない", "選考が属人化し、どこで落ちているかが見えない",
                   "面接官・人事の工数が逼迫し、対応スピードが落ちる", "入社後のミスマッチで早期離職が起きる"]},
        {"type": "stats", "kicker": "DATA ・ 労働市場の前提", "title": "数字が示す、採用の難度",
         "stats": [["33.8%", "大卒3年以内離職率", "厚労省 2024"], ["1.2x", "新卒求人倍率の高止まり", "リクルートWS 2025"],
                   ["55.2%", "企業のAI業務利用率(日本)", "総務省 2025"]],
         "note": "出典は各調査の公表値。数値は編集してご利用いただけます。"},
        {"type": "cards", "kicker": "VALUE ・ 提供価値", "title": "3つの強みで、採用を前に進める",
         "cards": [["RPO伴走", "END-TO-END", "要件定義から母集団形成・面談・クロージングまで実働で伴走。"],
                   ["データ基盤", "ANALYTICS", "Salesforce／スプレッドシートで歩留まり・KPIを可視化。"],
                   ["AI活用", "AUTOMATION", "候補者リサーチ・紹介文・レポート作成をAIで自動化。"]]},
        {"type": "flow", "kicker": "FLOW ・ サービス全体像", "title": "母集団形成から定着まで、一気通貫", "accent": 2,
         "steps": [["01", "母集団形成", "媒体・スカウト・リファラルを設計し候補者を集める"], ["02", "選考設計", "要件定義から面接フローまでKPIで可視化"],
                   ["03", "面談・クロージング", "キャリアに伴走し、納得した意思決定を支援"], ["04", "定着・活躍支援", "入社後フォローで早期離職を防ぎ戦力化"]],
         "point": "中核は“面談・クロージング”。候補者の納得を引き出すことが、定着と活躍の起点になる。"},
    ],
    "cta": {"kicker": "LET'S WORK TOGETHER", "title": "採用の“仕組み化”を、一緒に。",
            "points": ["まずは現状のKPIと課題を30分でヒアリングします", "母集団〜定着まで、必要な範囲だけ伴走可能です", "データ基盤・AI活用の導入支援も承ります"],
            "contact": "atsuya_sato@tokumori.co.jp"},
}


def bgimg(dk, sid, url, w=PW, h=PH, x=0, y=0):
    dk.reqs.append({"createImage": {"objectId": dk._id("im"), "url": url,
        "elementProperties": {"pageObjectId": sid,
            "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"}}}})


def render_cover(dk, spec, glow_url, hero_url):
    cv = spec.get("cover", {}); org = cv.get("org", "")
    if SIMPLE:
        # 極限シンプル表紙（S1確定形）：ロゴ左上・特大タイトル左寄せ・サブ・下部社名。装飾ゼロ・全文字編集可
        sid = dk.slide(bg=BG)
        wordmark(dk, sid)
        dk.text(sid, MX, int(2.32*IN), int(8.8*IN), int(0.95*IN),
                [(cv.get("title", ""), {"size": 44, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(44, 28))
        dk.text(sid, MX, int(3.38*IN), int(8*IN), int(0.4*IN),
                [(cv.get("subtitle", cv.get("kicker", "")), {"size": 15, "color": MUT, "font": BODY})], valign="TOP", fit=(15, 12))
        dk.text(sid, MX, PH-int(0.66*IN), CW, int(0.3*IN),
                [(org, {"size": 12, "color": MUT, "font": BODY})], valign="MIDDLE")
        return
    doc = (spec.get("tag", "") + " ご提案").strip()
    if EDIT:
        # A案 表紙：白地・大余白・特大タイトル・アクセントtick・器モチーフ（右上に淡く）
        sid = dk.slide(bg=BG)
        dk.text(sid, MX, int(0.55*IN), int(5*IN), int(0.3*IN),
                [("とくもり採用代行", {"size": 12, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, PW-MX-int(3.6*IN), int(0.55*IN), int(3.6*IN), int(0.3*IN),
                [(doc, {"size": 10, "color": MUT, "font": MONO})], align="END", valign="MIDDLE")
        bowl(dk, sid, PW-int(1.15*IN), int(1.35*IN), int(1.7*IN), ACC)
        dk.text(sid, MX, int(2.0*IN), int(8.7*IN), int(1.7*IN),
                [(cv.get("title", ""), {"size": 46, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(46, 30))
        dk.rect(sid, MX, int(3.9*IN), int(0.72*IN), int(0.05*IN), fill=ACC)
        dk.text(sid, MX, int(4.14*IN), int(8*IN), int(0.55*IN),
                [(cv.get("subtitle", ""), {"size": 15, "color": MUT, "font": BODY})], valign="TOP", fit=(15, 12))
        dk.text(sid, MX, PH-int(0.6*IN), CW, int(0.3*IN),
                [(org, {"size": 10, "color": FAINT, "font": MONO})], valign="MIDDLE")
        return
    if HBLOCK:
        # B案/ハイブリッド 表紙：左=ブランド色ベタ面に反転特大タイトル／右=白に器モチーフ＋サブ
        sid = dk.slide(bg=BG)
        pw = int(4.95*IN)
        dk.rect(sid, 0, 0, pw, PH, fill=ACC)
        dk.text(sid, MX, int(0.55*IN), pw-int(0.7*IN), int(0.3*IN),
                [("とくもり採用代行", {"size": 12, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(1.86*IN), pw-int(0.55*IN), int(2.7*IN),
                [(cv.get("title", ""), {"size": 34, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="TOP", fit=(34, 22))
        dk.text(sid, MX, PH-int(0.6*IN), pw-int(0.6*IN), int(0.3*IN),
                [(doc, {"size": 10, "color": "E7E4F2", "font": MONO})], valign="MIDDLE")
        dk.text(sid, pw+int(0.5*IN), int(1.95*IN), PW-pw-int(0.9*IN), int(1.4*IN),
                [(cv.get("subtitle", ""), {"size": 15, "color": TXT, "font": BODY})], valign="TOP")
        bowl(dk, sid, PW-int(1.55*IN), int(3.15*IN), int(2.4*IN), ACC)
        dk.text(sid, pw+int(0.5*IN), PH-int(0.6*IN), PW-pw-int(0.9*IN), int(0.3*IN),
                [(org, {"size": 10, "color": FAINT, "font": MONO})], valign="MIDDLE")
        return
    if CONSULT:
        # コンサル提案書 表紙 v2：左=紺パネルに大見出し／右=白地に器モチーフ＋サブ＋文書情報（非対称・上質）
        sid = dk.slide(bg="FFFFFF")
        pw = int(5.7*IN); steel = "AEC0D6"; steel2 = "8B9CB0"
        dk.rect(sid, 0, 0, pw, PH, fill=ACC)                        # 左 紺パネル（フルブリード）
        dk.text(sid, MX, int(0.6*IN), int(4.4*IN), int(0.3*IN),
                [("とくもり採用代行", {"size": 13, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(2.18*IN), pw-int(0.85*IN), int(0.28*IN),
                [(cv.get("kicker", ""), {"size": 11, "color": steel, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.rect(sid, MX, int(2.62*IN), int(0.56*IN), int(0.042*IN), fill="FFFFFF")   # accent tick
        dk.text(sid, MX, int(2.82*IN), pw-int(0.8*IN), int(1.7*IN),
                [(cv.get("title", ""), {"size": 39, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="TOP", fit=(39, 24))
        rcx = pw + (PW - pw)//2                                     # 右 白エリアの中心
        bowl(dk, sid, rcx, int(1.4*IN), int(2.3*IN), ACC, "FFFFFF")  # 器モチーフ（紺半円）
        dk.text(sid, pw+int(0.42*IN), int(3.3*IN), PW-pw-int(0.82*IN), int(1.1*IN),
                [(cv.get("subtitle", ""), {"size": 14, "color": TXT, "font": BODY})], valign="TOP", fit=(14, 11))
        dk.rect(sid, pw+int(0.42*IN), PH-int(0.88*IN), PW-pw-int(0.82*IN), 9525, fill=BORDER)
        meta = cv.get("meta") or (org + "　｜　CONFIDENTIAL")
        dk.text(sid, pw+int(0.42*IN), PH-int(0.72*IN), PW-pw-int(0.82*IN), int(0.4*IN),
                [(meta, {"size": 9.5, "color": steel2, "font": BODY})], valign="MIDDLE", fit=(9.5, 8))
        return
    if HERO_DARK:
        sid = dk.slide(bg=HERO_BG); bgimg(dk, sid, hero_url)
        dk.rect(sid, MX, int(0.46*IN), int(0.12*IN), int(0.12*IN), fill="FFFFFF", shape="ELLIPSE")
        dk.text(sid, MX+int(0.26*IN), int(0.36*IN), int(3*IN), int(0.3*IN), [("TOKUMORI", {"size": 11, "color": HERO_TXT, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(1.55*IN), CW, int(0.26*IN), [(cv.get("kicker", ""), {"size": 10, "color": HERO_TXT, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(1.98*IN), CW, int(0.92*IN), [(cv.get("title", ""), {"size": 40, "color": HERO_TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.rect(sid, MX, int(3.18*IN), int(1.1*IN), int(0.055*IN), fill="FFFFFF")
        dk.text(sid, MX, int(3.46*IN), CW, int(0.5*IN), [(cv.get("subtitle", ""), {"size": 15, "color": HERO_SUB, "font": BODY})])
        dk.text(sid, MX, PH-int(0.62*IN), CW, int(0.3*IN), [(org, {"size": 10, "color": HERO_META, "font": MONO})], valign="MIDDLE")
    elif AURA:
        # elu風：白＋右に“魂”の発光オーラ、左に力強い濃い大見出し＋赤eyebrow＋細赤罫＋mono meta（大余白）
        sid = dk.slide(bg=BG); bgimg(dk, sid, glow_url); wordmark(dk, sid)
        dk.text(sid, MX, int(1.78*IN), int(6.4*IN), int(0.26*IN), [(cv.get("kicker", ""), {"size": 10, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(2.22*IN), int(6.7*IN), int(1.7*IN), [(cv.get("title", ""), {"size": 48, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(48, 28))
        dk.rect(sid, MX, int(4.02*IN), int(0.86*IN), int(0.045*IN), fill=ACC)
        dk.text(sid, MX, int(4.26*IN), int(6.2*IN), int(0.6*IN), [(cv.get("subtitle", ""), {"size": 14, "color": MUT, "font": BODY})], valign="TOP")
        dk.text(sid, MX, PH-int(0.66*IN), CW, int(0.3*IN), [(org, {"size": 10, "color": FAINT, "font": MONO})], valign="MIDDLE")
    else:
        sid = dk.slide(bg=BG); bgimg(dk, sid, glow_url); wordmark(dk, sid)
        dk.text(sid, MX, int(1.55*IN), CW, int(0.26*IN), [(cv.get("kicker", ""), {"size": 10, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(1.98*IN), CW, int(0.9*IN), [(cv.get("title", ""), {"size": 38, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.rect(sid, MX, int(3.12*IN), int(1.0*IN), int(0.05*IN), fill=ACC)
        dk.text(sid, MX, int(3.4*IN), CW, int(0.5*IN), [(cv.get("subtitle", ""), {"size": 15, "color": MUT, "font": BODY})])
        dk.text(sid, MX, PH-int(0.66*IN), CW, int(0.3*IN), [(org, {"size": 10, "color": FAINT, "font": MONO})], valign="MIDDLE")


def s_bullets(dk, s, tag, glow_url):
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    items = s.get("items", []); row = int(0.5*IN); y = ctop(row*max(1, len(items)))
    for it in items:
        dk.rect(sid, MX+int(0.02*IN), y+int(0.13*IN), int(0.1*IN), int(0.1*IN), fill=ACC)
        dk.text(sid, MX+int(0.32*IN), y, CW-int(0.32*IN), row, [(it, {"size": 14, "color": TXT, "font": BODY})], valign="MIDDLE")
        y += row
    foot_d(dk, sid, tag, dk.page)


def s_stats(dk, s, tag, glow_url):
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    stats = s.get("stats", []); n = max(1, len(stats))
    gap = int(0.24*IN); cw = (CW-gap*(n-1))//n; sh = int(1.7*IN); sy = ctop(sh); x = MX
    for row3 in stats:
        big, lab, src = (list(row3) + ["", "", ""])[:3]
        dk.rect(sid, x, sy, cw, sh, fill=PANEL, line=BORDER, lw=1, round=RND)
        dk.rect(sid, x+int(0.26*IN), sy+int(0.28*IN), int(0.34*IN), 12700, fill=ACC)
        # consult: 数字は字幅の狭い Noto Sans JP（BIZ UDは幅広で4桁が折返すため）＋やや小さめ＝確実に1行
        bigfont, bigsz, bigfit = (BODY, 33, (33, 16)) if CONSULT else (MONO, 38, (38, 22))
        dk.text(sid, x+int(0.24*IN), sy+int(0.42*IN), cw-int(0.36*IN), int(0.7*IN), [(big, {"size": bigsz, "color": TXT, "bold": True, "font": bigfont})], valign="MIDDLE", fit=bigfit)
        dk.text(sid, x+int(0.28*IN), sy+int(1.16*IN), cw-int(0.5*IN), int(0.32*IN), [(lab, {"size": 12, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(12, 9))
        if src:  # 空文字だと Slides API が「has no text」で落ちるため非空のみ描画
            dk.text(sid, x+int(0.28*IN), sy+int(1.44*IN), cw-int(0.5*IN), int(0.24*IN), [(src, {"size": 9, "color": MUT, "font": MONO})], valign="MIDDLE")
        x += cw+gap
    if s.get("note"):
        dk.text(sid, MX, sy+sh+int(0.2*IN), CW, int(0.3*IN), [(s["note"], {"size": 10, "color": MUT, "font": BODY})], valign="MIDDLE")
    foot_d(dk, sid, tag, dk.page)


def s_cards(dk, s, tag, glow_url):
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    cards = s.get("cards", []); n = max(1, len(cards))
    gap = int(0.24*IN); cw = (CW-gap*(n-1))//n; ch = int(2.38*IN); cy = ctop(ch); x = MX; pad = int(0.26*IN)
    for c in cards:
        title, tagl, desc = (list(c) + ["", "", ""])[:3]
        dk.rect(sid, x, cy, cw, ch, fill=PANEL, line=BORDER, lw=1, round=RND)
        pill(dk, sid, x+pad, cy+int(0.24*IN), int(1.5*IN), tagl)
        dk.text(sid, x+pad, cy+int(0.74*IN), cw-pad-int(0.24*IN), int(0.5*IN), [(title, {"size": 19, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(19, 13))
        dk.text(sid, x+pad, cy+int(1.28*IN), cw-pad-int(0.24*IN), ch-int(1.42*IN), [(desc, {"size": 11, "color": MUT, "font": BODY})], valign="TOP", spacing=126, fit=(11, 9))
        x += cw+gap
    if s.get("note"):
        dk.text(sid, MX, PH-int(0.72*IN), CW, int(0.22*IN),
                [(s["note"], {"size": 8.5, "color": MUT, "font": BODY})], valign="MIDDLE", fit=(8.5, 7))
    foot_d(dk, sid, tag, dk.page)


def s_flow(dk, s, tag, glow_url):
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    imgH = CW*300//1280; coh = int(0.8*IN); g = int(0.16*IN); fy = ctop(imgH+g+coh)
    if s.get("_url"):
        bgimg(dk, sid, s["_url"], w=CW, h=imgH, x=MX, y=fy)
    if s.get("point"):
        callout_d(dk, sid, s["point"], y=fy+imgH+g)
    foot_d(dk, sid, tag, dk.page)


def render_cta(dk, spec, glow_url, hero_url):
    ct = spec.get("cta", {})
    if MODERN:
        # モダン クロージング：block/hybrid=ブランド色ベタに白／edit=白地にアクセント。特大タイトル＋要点＋連絡先
        dark = HBLOCK
        sid = dk.slide(bg=(ACC if dark else BG))
        tcol = "FFFFFF" if dark else TXT
        acc = "FFFFFF" if dark else ACC
        sub = "EDECF4" if dark else MUT
        dk.text(sid, MX, int(0.6*IN), int(6*IN), int(0.3*IN),
                [("とくもり採用代行", {"size": 12, "color": tcol, "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(1.7*IN), int(8.7*IN), int(1.6*IN),
                [(ct.get("title", ""), {"size": 34, "color": tcol, "bold": True, "font": HEAD})], valign="TOP", fit=(34, 22))
        dk.rect(sid, MX, int(3.5*IN), int(0.72*IN), int(0.05*IN), fill=acc)
        y = int(3.8*IN)
        for ln in ct.get("points", []):
            dk.text(sid, MX, y, int(8.4*IN), int(0.4*IN), [(ln, {"size": 14, "color": sub, "font": BODY})], valign="MIDDLE", fit=(14, 11))
            y += int(0.44*IN)
        dk.text(sid, MX, PH-int(0.62*IN), CW, int(0.3*IN),
                [("CONTACT   ", {"size": 10, "color": acc, "bold": True, "font": MONO}), (ct.get("contact", ""), {"size": 11, "color": tcol, "font": MONO})], valign="MIDDLE")
        if BLOCK:
            bowl(dk, sid, PW-int(1.5*IN), int(1.6*IN), int(2.0*IN), "FFFFFF", ACC)
        return
    if CONSULT:
        # コンサル型クロージング：紺ベタ＋白の結論タイトル＋要点＋連絡先（表紙とブックエンド）
        sid = dk.slide(bg=ACC)
        dk.text(sid, MX, int(0.52*IN), int(6*IN), int(0.3*IN),
                [("とくもり採用代行", {"size": 12.5, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(1.7*IN), CW, int(0.26*IN),
                [(ct.get("kicker", ""), {"size": 11, "color": "AEC0D6", "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(2.12*IN), int(8.6*IN), int(1.0*IN),
                [(ct.get("title", ""), {"size": 34, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="TOP", fit=(34, 22))
        y = int(3.4*IN)
        for ln in ct.get("points", []):
            dk.rect(sid, MX+int(0.02*IN), y+int(0.13*IN), int(0.1*IN), int(0.1*IN), fill="FFFFFF")
            dk.text(sid, MX+int(0.32*IN), y, CW-int(0.32*IN), int(0.4*IN),
                    [(ln, {"size": 13.5, "color": "D6DEE8", "font": BODY})], valign="MIDDLE")
            y += int(0.44*IN)
        dk.text(sid, MX, PH-int(0.62*IN), CW, int(0.3*IN),
                [("CONTACT  ", {"size": 10, "color": "AEC0D6", "bold": True, "font": HEAD}),
                 (ct.get("contact", ""), {"size": 11, "color": "FFFFFF", "font": BODY})], valign="MIDDLE")
        return
    tcol = HERO_TXT if HERO_DARK else TXT; kcol = HERO_TXT if HERO_DARK else ACC; lcol = HERO_SUB if HERO_DARK else TXT
    if HERO_DARK:
        sid = dk.slide(bg=HERO_BG); bgimg(dk, sid, hero_url)
        dk.rect(sid, MX, int(0.46*IN), int(0.12*IN), int(0.12*IN), fill="FFFFFF", shape="ELLIPSE")
        dk.text(sid, MX+int(0.26*IN), int(0.36*IN), int(3*IN), int(0.3*IN), [("TOKUMORI", {"size": 11, "color": HERO_TXT, "bold": True, "font": MONO})], valign="MIDDLE")
    else:
        sid = dk.slide(bg=BG); bgimg(dk, sid, glow_url); wordmark(dk, sid)
    dk.text(sid, MX, int(1.55*IN), CW, int(0.26*IN), [(ct.get("kicker", "LET'S WORK TOGETHER"), {"size": 10, "color": kcol, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX, int(1.98*IN), CW, int(0.9*IN), [(ct.get("title", ""), {"size": 38, "color": tcol, "bold": True, "font": HEAD})], valign="MIDDLE")
    y = int(3.1*IN)
    for ln in ct.get("points", []):
        dk.rect(sid, MX+int(0.02*IN), y+int(0.13*IN), int(0.1*IN), int(0.1*IN), fill=("FFFFFF" if HERO_DARK else ACC))
        dk.text(sid, MX+int(0.32*IN), y, CW-int(0.32*IN), int(0.4*IN), [(ln, {"size": 13.5, "color": lcol, "font": BODY})], valign="MIDDLE")
        y += int(0.46*IN)
    contact = ct.get("contact", "")
    if HERO_DARK:
        dk.rect(sid, MX, int(4.6*IN), int(5.7*IN), int(0.52*IN), fill="FFFFFF", round=RND)
        dk.text(sid, MX+int(0.28*IN), int(4.6*IN), int(5.4*IN), int(0.52*IN), [("CONTACT  ", {"size": 10, "color": ACC, "bold": True, "font": MONO}), (contact, {"size": 11, "color": "17181C", "font": MONO})], valign="MIDDLE")
    else:
        dk.rect(sid, MX, int(4.6*IN), int(5.6*IN), int(0.5*IN), line=BORDER, lw=1, round=RND)
        dk.text(sid, MX+int(0.26*IN), int(4.6*IN), int(5.3*IN), int(0.5*IN), [("CONTACT  ", {"size": 10, "color": ACC, "bold": True, "font": MONO}), (contact, {"size": 11, "color": TXT, "font": MONO})], valign="MIDDLE")


def fig_tokens():
    # figs_html 用のテーマトークン（アクセント=現MODEのACC・グレー3段は中立のまま）
    return {"RED": ACC, "INK": TXT, "SUB": MUT, "PANEL": PANEL, "FAINT": FAINT,
            "RULE": BORDER, "BORDER": BORDER, "LRED": "ECEFFC", "CON": PAL["CON"],
            "HEAD": HEAD, "BODY": BODY, "MONO": MONO, "BG": BG}


# fig 名 → (figs_html 関数, data から位置引数として渡すキー順)
FIG_DISPATCH = {
    "bar":          (FH.bar_html,          ["items"]),
    "funnel":       (FH.funnel_html,       ["data"]),
    "pyramid":      (FH.pyramid_html,      ["levels"]),
    "before_after": (FH.before_after_html, ["before", "after"]),
    "formula":      (FH.formula_html,      ["equation", "parts"]),
    "process":      (FH.process_html,      ["steps"]),
    "gridmatrix":   (FH.gridmatrix_html,   ["cols", "rows", "cells"]),
    "timeline":     (FH.timeline_html,     ["phases"]),
    "ladder":       (FH.ladder_html,       ["steps"]),
    "cycle":        (FH.cycle_html,        ["nodes"]),
    "waterfall":    (FH.waterfall_html,    ["items"]),
}


def fig_html_for(s):
    fn, keys = FIG_DISPATCH[s["fig"]]
    d = s.get("data", {})
    args = [d[k] for k in keys]
    kw = {"H": s["H"]} if s.get("H") else {}
    return fn(*args, fig_tokens(), **kw)


def s_fig(dk, s, tag, glow_url):
    # 図解（HTMLハイブリッド）スライド：統一ヘッダ＋本文帯に高精細図＋任意の要点/出典
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    Hh = s.get("H") or 410
    has_point = bool(s.get("point")); has_note = bool(s.get("note"))
    if MODERN:
        # モダン：要点はボックスにせず"太字1行"。図→要点→出典を上から積み、重なりを防ぐ
        reserve = (int(0.5*IN) if has_point else 0) + (int(0.34*IN) if has_note else 0)
        maxh = (BODY_BOT - BODY_TOP) - reserve
        imgH = min(CW*Hh//1280, maxh); imgW = imgH*1280//Hh
        fx = MX + (CW - imgW)//2; fy = BODY_TOP
        if s.get("_url"):
            bgimg(dk, sid, s["_url"], w=imgW, h=imgH, x=fx, y=fy)
        yb = fy + imgH + int(0.14*IN)
        if has_point:
            dk.rect(sid, MX, yb+int(0.06*IN), int(0.24*IN), int(0.045*IN), fill=ACC)
            dk.text(sid, MX+int(0.34*IN), yb-int(0.02*IN), CW-int(0.34*IN), int(0.42*IN),
                    [(s["point"], {"size": 13.5, "color": TXT, "bold": True, "font": BODY})], valign="TOP", fit=(13.5, 10))
        if has_note:
            dk.text(sid, MX, PH-int(0.52*IN), int(8.2*IN), int(0.24*IN),
                    [(s["note"], {"size": 8.5, "color": FAINT, "font": BODY})], valign="MIDDLE", fit=(8.5, 7))
        foot_d(dk, sid, tag, dk.page)
        return
    maxh = int((2.0 if has_point else (2.58 if has_note else 2.92)) * IN)
    imgH = min(CW*Hh//1280, maxh); imgW = imgH*1280//Hh
    fx = MX + (CW - imgW)//2
    coh = int(0.8*IN); g = int(0.16*IN)
    fy = ctop(imgH + (g + coh if has_point else 0))
    if s.get("_url"):
        bgimg(dk, sid, s["_url"], w=imgW, h=imgH, x=fx, y=fy)
    if has_point:
        callout_d(dk, sid, s["point"], y=fy+imgH+g)
    if has_note:
        dk.text(sid, MX, PH-int(0.72*IN), CW, int(0.22*IN),
                [(s["note"], {"size": 8.5, "color": MUT, "font": BODY})], valign="MIDDLE", fit=(8.5, 7))
    foot_d(dk, sid, tag, dk.page)


def s_section(dk, s, tag, glow_url):
    if SIMPLE:
        # 極限シンプル章扉（S5確定形）：白・赤番号・タイトル・サブのみ
        sid = dk.slide(bg=BG)
        if s.get("num"):
            nn = "0" + str(s["num"]) if len(str(s["num"])) == 1 else str(s["num"])
            dk.text(sid, MX, int(2.28*IN), int(2*IN), int(0.3*IN),
                    [(nn, {"size": 15, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(2.62*IN), int(8.8*IN), int(0.8*IN),
                [(s.get("title", ""), {"size": 34, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(34, 22))
        if s.get("subtitle"):
            dk.text(sid, MX, int(3.52*IN), int(8.4*IN), int(0.5*IN),
                    [(s["subtitle"], {"size": 14.5, "color": MUT, "font": BODY})], valign="TOP", fit=(14.5, 11))
        return
    if MODERN and not HBLOCK:
        # メルカリ型 明るい章扉：白地＋大きな赤の章番号＋濃い大見出し＋赤の細罫＋器モチーフ（右下・淡赤）
        sid = dk.slide(bg=BG)
        if s.get("num"):
            nn = "0" + str(s["num"]) if len(str(s["num"])) == 1 else str(s["num"])
            dk.text(sid, MX, int(1.42*IN), int(3*IN), int(0.9*IN),
                    [(nn, {"size": 60, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(2.5*IN), int(8.6*IN), int(1.0*IN),
                [(s.get("title", ""), {"size": 34, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(34, 22))
        dk.rect(sid, MX, int(3.62*IN), int(0.72*IN), int(0.05*IN), fill=ACC)
        if s.get("subtitle"):
            dk.text(sid, MX, int(3.86*IN), int(8.2*IN), int(0.8*IN),
                    [(s["subtitle"], {"size": 15, "color": MUT, "font": BODY})], valign="TOP", fit=(15, 12))
        bowl(dk, sid, PW-int(1.15*IN), PH-int(1.5*IN), int(2.2*IN), ACC, BG)
        return
    if HBLOCK:
        # モダン章扉：ブランド色ベタ＋白の大章番号・章タイトル＋器モチーフ（右下にブリード）
        sid = dk.slide(bg=ACC)
        if s.get("num"):
            nn = "0" + str(s["num"]) if len(str(s["num"])) == 1 else str(s["num"])
            dk.text(sid, MX, int(1.5*IN), int(3*IN), int(0.5*IN),
                    [(nn, {"size": 20, "color": "FFFFFF", "bold": True, "font": MONO})], valign="MIDDLE")
        dk.text(sid, MX, int(2.05*IN), int(8.4*IN), int(1.3*IN),
                [(s.get("title", ""), {"size": 34, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="MIDDLE", fit=(34, 22))
        dk.rect(sid, MX, int(3.5*IN), int(0.72*IN), int(0.05*IN), fill="FFFFFF")
        if s.get("subtitle"):
            dk.text(sid, MX, int(3.78*IN), int(7.6*IN), int(0.8*IN),
                    [(s["subtitle"], {"size": 15, "color": "EDE6E6", "font": BODY})], valign="TOP", fit=(15, 12))
        bowl(dk, sid, PW-int(1.3*IN), PH-int(1.7*IN), int(2.6*IN), "FFFFFF", ACC)
        return
    if CONSULT:
        # コンサル型 章扉：紺ベタ＋白の章番号・章タイトル・一行サマリー（フラット）
        sid = dk.slide(bg=ACC)
        if s.get("num"):
            dk.text(sid, MX, int(1.5*IN), CW, int(0.4*IN),
                    [("0" + s["num"] if len(str(s["num"])) == 1 else s["num"],
                      {"size": 15, "color": "AEC0D6", "bold": True, "font": HEAD})], valign="MIDDLE")
        dk.text(sid, MX, int(2.0*IN), int(8.6*IN), int(1.1*IN),
                [(s.get("title", ""), {"size": 34, "color": "FFFFFF", "bold": True, "font": HEAD})], valign="MIDDLE", fit=(34, 22))
        dk.rect(sid, MX, int(3.2*IN), int(1.0*IN), int(0.05*IN), fill="FFFFFF")
        if s.get("subtitle"):
            dk.text(sid, MX, int(3.46*IN), int(8.2*IN), int(0.7*IN),
                    [(s["subtitle"], {"size": 14.5, "color": "C7D2DF", "font": BODY})], valign="TOP")
        return
    # 章扉（ヒーロー扱い）：MODEのグラデ地＋ロゴ＋章番号＋章タイトル＋一行サマリー
    sid = dk.slide(bg=BG); bgimg(dk, sid, glow_url); wordmark(dk, sid)
    if s.get("num"):
        dk.text(sid, MX, int(1.42*IN), CW, int(0.4*IN),
                [(s["num"], {"size": 17, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX, int(1.96*IN), CW, int(1.0*IN),
            [(s.get("title", ""), {"size": 36, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.rect(sid, MX, int(3.16*IN), int(1.0*IN), int(0.05*IN), fill=ACC)
    if s.get("subtitle"):
        dk.text(sid, MX, int(3.46*IN), int(7.4*IN), int(0.7*IN),
                [(s["subtitle"], {"size": 15, "color": MUT, "font": BODY})], valign="TOP")


def flat_bg_html():
    # consult＝装飾なしの純白地（グラデ/グロー/ドット禁止）
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/><style>*{margin:0;}'
            'html,body{width:1280px;height:720px;background:#FFFFFF;}</style></head><body></body></html>')


def s_split(dk, s, tag, glow_url):
    # 高密度・左右2ゾーン：左=ロジック枠（小見出し＋箇条）／右=エビデンス（図 or 箇条）＋示唆バンド＋出典
    sid = dk.slide(bg=BG)
    if BGALL: bgimg(dk, sid, glow_url)
    head(dk, sid, s.get("kicker", ""), s.get("title", ""))
    has_point = bool(s.get("point")); has_note = bool(s.get("note"))
    if s.get("_twourl"):
        # テキスト×テキストは HTMLでデザインした2カラム図（可変フォント・折返し）に置換
        bt = BODY_TOP
        reserve = (int(0.7*IN) if has_point else 0) + (int(0.3*IN) if has_note else 0)
        bb = BODY_BOT - reserve
        Hh = s.get("_twoH") or 430
        imgH = min(CW*Hh//1280, bb-bt); imgW = imgH*1280//Hh
        bgimg(dk, sid, s["_twourl"], w=imgW, h=imgH, x=MX+(CW-imgW)//2, y=bt)
        if has_point:
            callout_d(dk, sid, s["point"], y=bb+int(0.1*IN))
        if has_note:
            dk.text(sid, MX, PH-int(0.5*IN), int(8.2*IN), int(0.24*IN),
                    [(s["note"], {"size": 8.5, "color": MUT, "font": BODY})], valign="MIDDLE", fit=(8.5, 7))
        foot_d(dk, sid, tag, dk.page)
        return
    band_top = BODY_TOP
    band_bot = BODY_BOT - (int(0.96*IN) if has_point else 0)
    bh = band_bot - band_top
    gap = int(0.28*IN); lw = int((CW - gap) * 0.42); rw = CW - gap - lw
    lx = MX; rx = MX + lw + gap; pad = int(0.22*IN)
    left = s.get("left", {})
    dk.rect(sid, lx, band_top, lw, bh, fill=PANEL, line=BORDER, lw=1, round=RND)
    dk.text(sid, lx+pad, band_top+int(0.16*IN), lw-2*pad, int(0.3*IN),
            [(left.get("title", ""), {"size": 13, "color": ACC, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.rect(sid, lx+pad, band_top+int(0.54*IN), lw-2*pad, 9525, fill=BORDER)
    litems = left.get("items", []); lbtop = band_top+int(0.66*IN)
    lrow = (band_bot - lbtop - int(0.06*IN)) // max(1, len(litems))  # 利用可能高さを等分＝食い込み防止
    y = lbtop
    for it in litems:
        dk.rect(sid, lx+pad, y+int(0.1*IN), int(0.07*IN), int(0.07*IN), fill=ACC)
        dk.text(sid, lx+pad+int(0.18*IN), y, lw-2*pad-int(0.18*IN), lrow,
                [(it, {"size": 11.5, "color": TXT, "font": BODY})], valign="MIDDLE", fit=(11.5, 8), spacing=112)
        y += lrow
    if s.get("_url"):
        Hh = s.get("H") or 410
        imgH = min(rw*Hh//1280, bh); imgW = imgH*1280//Hh
        bgimg(dk, sid, s["_url"], w=min(imgW, rw), h=imgH,
              x=rx+max(0, (rw-imgW)//2), y=band_top+max(0, (bh-imgH)//2))
    else:
        right = s.get("right", {})
        dk.text(sid, rx, band_top+int(0.16*IN), rw, int(0.3*IN),
                [(right.get("title", ""), {"size": 13, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE")
        ritems = right.get("items", []); rbtop = band_top+int(0.66*IN)
        rrow = (band_bot - rbtop - int(0.06*IN)) // max(1, len(ritems))
        y = rbtop
        for it in ritems:
            dk.rect(sid, rx, y+int(0.1*IN), int(0.07*IN), int(0.07*IN), fill=ACC)
            dk.text(sid, rx+int(0.18*IN), y, rw-int(0.18*IN), rrow,
                    [(it, {"size": 12, "color": TXT, "font": BODY})], valign="MIDDLE", fit=(12, 9), spacing=118)
            y += rrow
    if has_point:
        callout_d(dk, sid, s["point"], y=band_bot+int(0.16*IN))
    if has_note:
        dk.text(sid, MX, PH-int(0.72*IN), CW, int(0.22*IN),
                [(s["note"], {"size": 8.5, "color": MUT, "font": BODY})], valign="MIDDLE", fit=(8.5, 7))
    foot_d(dk, sid, tag, dk.page)


def bowl(dk, sid, cx, top, d, color, bgc=None):
    # とくもり「ごはん茶碗」モチーフ＝下半分の半円（ドーム状）。装飾のアクセント図形。
    bgc = bgc or BG
    dk.rect(sid, cx-d//2, top, d, d, fill=color, shape="ELLIPSE")
    dk.rect(sid, cx-d//2-1270, top-1270, d+2540, d//2+1270, fill=bgc)  # 上半分をbg色でマスク→下の半円


def modern_foot(dk, sid, tag, page, dark=False):
    col = "FFFFFF" if dark else FAINT
    dk.text(sid, PW-MX-int(1.2*IN), PH-int(0.5*IN), int(1.2*IN), int(0.3*IN),
            [("%02d" % page, {"size": 9, "color": col, "font": MONO})], align="END", valign="MIDDLE")


def modern_note(dk, sid, note, dark=False):
    if not note:
        return
    dk.text(sid, MX, PH-int(0.52*IN), int(8*IN), int(0.24*IN),
            [(note, {"size": 8.5, "color": ("D9D6E2" if dark else FAINT), "font": BODY})], valign="MIDDLE", fit=(8.5, 7))


def s_bignum(dk, s, tag, glow_url):
    # 巨大数字を主役に（SpeakerDeck系）。block/hybrid=ブランド色ベタ面に白の特大数字／edit=白地にアクセント特大数字
    dark = HBLOCK
    sid = dk.slide(bg=(ACC if dark else BG))
    tcol = "FFFFFF" if dark else TXT
    ncol = "FFFFFF" if dark else ACC
    kcol = "EAE8F4" if dark else ACC
    subcol = "EDECF4" if dark else MUT
    dk.text(sid, MX, int(0.62*IN), int(7*IN), int(0.3*IN),
            [(s.get("kicker", ""), {"size": 11, "color": kcol, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.text(sid, MX-int(0.06*IN), int(1.35*IN), int(9*IN), int(2.7*IN),
            [(s.get("num", ""), {"size": 112, "color": ncol, "bold": True, "font": MONO})], valign="MIDDLE", fit=(112, 46))
    dk.text(sid, MX, int(4.02*IN), int(8.6*IN), int(0.5*IN),
            [(s.get("label", ""), {"size": 18, "color": tcol, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(18, 12))
    if s.get("context"):
        dk.text(sid, MX, int(4.54*IN), int(8.4*IN), int(0.44*IN),
                [(s["context"], {"size": 13, "color": subcol, "font": BODY})], valign="TOP", fit=(13, 10))
    modern_note(dk, sid, s.get("note"), dark)
    modern_foot(dk, sid, tag, dk.page, dark)


def s_statement(dk, s, tag, glow_url):
    # 特大ステートメント（1スライド1メッセージ）。edit=白地／block=ブランド色ベタ面に白文字
    dark = BLOCK
    sid = dk.slide(bg=(ACC if dark else BG))
    tcol = "FFFFFF" if dark else TXT
    acc = "FFFFFF" if dark else ACC
    kcol = "EAE8F4" if dark else ACC
    dk.text(sid, MX, int(0.62*IN), int(7*IN), int(0.3*IN),
            [(s.get("kicker", ""), {"size": 11, "color": kcol, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.text(sid, MX, int(1.7*IN), int(8.7*IN), int(2.6*IN),
            [(s.get("title", ""), {"size": 34, "color": tcol, "bold": True, "font": HEAD})], valign="TOP", fit=(34, 22))
    dk.rect(sid, MX, int(4.35*IN), int(0.72*IN), int(0.05*IN), fill=acc)
    if s.get("subtitle"):
        dk.text(sid, MX, int(4.62*IN), int(8.2*IN), int(0.8*IN),
                [(s["subtitle"], {"size": 15, "color": ("EDECF4" if dark else MUT), "font": BODY})], valign="TOP", fit=(15, 12))
    if BLOCK:
        bowl(dk, sid, PW-int(1.5*IN), int(4.7*IN), int(2.0*IN), "FFFFFF", ACC)
    modern_foot(dk, sid, tag, dk.page, dark)


def s_points(dk, s, tag, glow_url):
    # 見出し＋大きな連番の並列ポイント（余白・非対称・囲みなし）。edit/block共通（白地）
    sid = dk.slide(bg=BG)
    dk.text(sid, MX, int(0.66*IN), int(7*IN), int(0.3*IN),
            [(s.get("kicker", ""), {"size": 11, "color": ACC, "bold": True, "font": HEAD})], valign="MIDDLE")
    dk.text(sid, MX, int(1.06*IN), CW, int(0.9*IN),
            [(s.get("title", ""), {"size": 25, "color": TXT, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(25, 17))
    items = s.get("items", []); n = max(1, len(items)); g = int(0.5*IN)
    colw = (CW - g*(n-1))//n; x = MX; y = int(2.55*IN)
    for it in items:
        num, ti, de = (list(it) + ["", "", ""])[:3]
        dk.text(sid, x, y, colw, int(0.86*IN), [(num, {"size": 33, "color": ACC, "bold": True, "font": MONO})], valign="MIDDLE")
        dk.rect(sid, x, y+int(1.0*IN), int(0.46*IN), int(0.04*IN), fill=ACC)
        dk.text(sid, x, y+int(1.2*IN), colw, int(0.5*IN), [(ti, {"size": 16, "color": TXT, "bold": True, "font": HEAD})], valign="TOP", fit=(16, 12))
        dk.text(sid, x, y+int(1.72*IN), colw, int(1.3*IN), [(de, {"size": 12.5, "color": MUT, "font": BODY})], valign="TOP", fit=(12.5, 10), spacing=128)
        x += colw + g
    modern_note(dk, sid, s.get("note"))
    modern_foot(dk, sid, tag, dk.page)


SLIDE_TYPES = {"bullets": s_bullets, "stats": s_stats, "cards": s_cards, "flow": s_flow,
               "fig": s_fig, "section": s_section, "split": s_split,
               "bignum": s_bignum, "statement": s_statement, "points": s_points}


def main():
    c = H.creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)
    spec = json.load(open(os.environ["SPEC"], encoding="utf-8")) if os.environ.get("SPEC") else DEFAULT_SPEC
    tag = spec.get("tag", "SERVICE OVERVIEW")

    # ロゴ（指定時）：Driveへアップし全スライドのワードマークを画像ロゴに差し替え
    global LOGO_URL
    if LOGO:
        LOGO_URL = IMG_URL % H.upload_drive(dr, LOGO)

    # 背景画像（テーマ別・DPI3）。soft=メディアsoftfv / media=赤グラデ・黒ヒーロー / shu=白×赤強グラデ / ao=白×青強グラデ
    atmo_html = flat_bg_html() if (CONSULT or MODERN) else (aura_bg_html() if AURA else (ao_bg_html() if AO else (shu_bg_html() if SHU else (softfv_bg_html() if BGALL else glow_bg_html()))))
    glow_url = IMG_URL % H.upload_drive(dr, H.render_png_fromstr(atmo_html, 1280, 720, 3))
    hero_url = (IMG_URL % H.upload_drive(dr, H.render_png_fromstr(herogrid_bg_html(), 1280, 720, 3))) if HERO_DARK else glow_url
    # フロー/図はスライド分、HTMLハイブリッドをDPI4でレンダリング（荒さ回避）
    for s in spec.get("slides", []):
        if s.get("type") == "flow":
            steps = [tuple(t) for t in s.get("steps", [])]
            s["_url"] = IMG_URL % H.upload_drive(dr, H.render_png_fromstr(flow_fig_html(steps, s.get("accent", 2)), 1280, 300, 4))
        elif s.get("type") == "fig" or (s.get("type") == "split" and s.get("fig")):
            Hh = s.get("H") or 410
            s["_url"] = IMG_URL % H.upload_drive(dr, H.render_png_fromstr(fig_html_for(s), 1280, Hh, 4))
        elif s.get("type") == "split" and s.get("right") and not s.get("fig"):
            # text-text split → HTMLでデザインした2カラム図（可変フォント）
            cols = [s.get("left", {}), s.get("right", {})]
            ml = twolist_maxlen(cols)
            maxit = max(len(cols[0].get("items", [])), len(cols[1].get("items", [])), 1)
            fs = 25 if ml <= 12 else (23 if ml <= 18 else (21 if ml <= 24 else (19 if ml <= 30 else 17)))
            Hh = min(480, 110 + maxit*int(fs*3.4))
            s["_twoH"] = Hh
            s["_twourl"] = IMG_URL % H.upload_drive(dr, H.render_png_fromstr(twolist_fig_html(cols), 1280, Hh, 4))

    reuse = os.environ.get("PITCH_ID")
    if reuse:
        pid = reuse; cur = slides.presentations().get(presentationId=pid).execute()
        delr = [{"deleteObject": {"objectId": z["objectId"]}} for z in cur.get("slides", [])]
    else:
        pres = slides.presentations().create(body={"title": "%s（%s）" % (spec.get("title_doc", "TOKUMORI ｜ 資料"), MODE)}).execute()
        pid = pres["presentationId"]
        delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]
    dk = bs.Deck(total=len(spec.get("slides", [])) + 2, nonce="pt" + uuid.uuid4().hex[:4])

    render_cover(dk, spec, glow_url, hero_url)
    for s in spec.get("slides", []):
        fn = SLIDE_TYPES.get(s.get("type"))
        if fn:
            fn(dk, s, tag, glow_url)
    render_cta(dk, spec, glow_url, hero_url)

    bs.safe_bu(slides, pid, delr+dk.reqs)
    for b in [{"type": "user", "role": "writer", "emailAddress": "0130atsuya@gmail.com"},
              {"type": "user", "role": "writer", "emailAddress": "atsuya_sato@tokumori.co.jp"},
              {"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}]:
        try:
            dr.permissions().create(fileId=pid, body=b, sendNotificationEmail=False, fields="id").execute()
        except Exception as e:
            print("share note:", str(e)[:60])
    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("PITCH(digital/dark):", url, "/", dk.page, "pages")
    return pid, url


if __name__ == "__main__":
    main()
