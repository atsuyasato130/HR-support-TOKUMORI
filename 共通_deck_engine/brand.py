#!/usr/bin/env python3
"""Tokumori デザイントークンの“正本”（単一ソース）。

build_slides.py（ネイティブGoogle Slides）と build_infographic_html.py（HTML図解）が
両方ともここを参照することで、ネイティブ／HTML画像が混在しても見た目が一貫する。
色・フォントを変えるときはここだけ直せば両方に反映される。
"""

# ---- カラー（HEX・#なし） ----
RED = "AF322C"      # アクセント（唯一の主役色）
REDD = "7A211C"     # 深い赤（補助）
INK = "1A1714"      # 本文（温かい近黒・純黒は使わない）
INKDK = "23201E"    # ヒーロー/章扉/暗バーの地色（ディープ・ウォームインク）
SUB = "6B6B6B"      # 補足テキスト
WHITE = "FFFFFF"
LRED = "F6ECEA"     # 赤の極薄（callout背景）
LGREEN = "F2F1F0"   # ok系の薄背景
PANEL = "FAF8F7"    # 微パネル
FAINT = "EEEAE8"    # ゴースト数字
RULE = "E6E3E1"     # 細罫
GREEN = "000000"    # ok系アクセント（黒で締める）
LINKC = "1155CC"    # リンク
ROSE = "C9938F"     # 暗地上のローズ
ONDARK = "C9C2BD"   # 暗地上の淡文字
# 機能色（成長など。意味づけ限定）
UP = "1E7A4E"       # 拡大
FLAT = "A49C96"     # 横ばい
DN = "B0742A"       # 縮小
# HTML専用の中立色（紙・ヘアライン）
PAPER = "FDFCFB"
HAIR = "EFEBE8"
FAINT2 = "A9A09A"

# ---- フォント（Google Fonts・Slides/HTML共通） ----
DISP = "Shippori Mincho B1"   # 明朝＝ヒーロー見出し・章番号（editorial高級感）
HEAD = "Zen Kaku Gothic New"  # コンテンツ見出し
BODY = "Noto Sans JP"         # 本文（可読性）
MONO = "IBM Plex Mono"        # ラベル・数値・フッター
