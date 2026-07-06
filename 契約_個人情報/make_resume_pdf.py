"""履歴書PDF生成（A4 1枚・JIS規格準拠）"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
# 太字相当はGothicW5、レギュラーはMin(明朝)を使うと履歴書らしくなるが、
# ここでは「Hira=ゴシック」「HiraB=ゴシック太」の役割で W5 を共用、
# 本文はそのまま W5、見出し系も W5 + サイズで強調
FONT_REG = "HeiseiKakuGo-W5"
FONT_BOLD = "HeiseiKakuGo-W5"

# テンプレ内の参照名を維持するため、registerFontの別名としても登録
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("HeiseiKakuGo-W5", normal="HeiseiKakuGo-W5", bold="HeiseiKakuGo-W5")

OUTPUT = "/Users/atsuyasato130/Claude AI/履歴書_大坪寧夏.pdf"

# ---- 履歴書データ ----
DATA = {
    "date": "2026年5月12日現在",
    "kana": "おおつぼ　ねな",
    "name": "大坪　寧夏",
    "birth": "2004年10月7日生（満21歳）",
    "gender": "女",
    "addr_kana": "みやぎけんせんだいしあおばくいつつばし2ちょうめ8-14 レジディアせんだいいつつばしぷれいす507",
    "addr_zip": "〒980-0022",
    "addr": "宮城県仙台市青葉区五橋2丁目8-14 レジディア仙台五橋プレイス507号室",
    "tel": "080-9630-7001",
    "addr2_kana": "いわてけんもりおかしかわめちょう22-18",
    "addr2_zip": "〒020-0811",
    "addr2": "岩手県盛岡市川目町22-18（実家）",
    "tel2": "019-651-7742",
    "history": [
        ("",     "",  "学歴"),
        ("2020", "4", "盛岡大学附属高等学校 入学"),
        ("2023", "3", "盛岡大学附属高等学校 卒業"),
        ("2023", "4", "東北学院大学 文学部 英文学科 入学"),
        ("2027", "3", "東北学院大学 文学部 英文学科 卒業見込み"),
        ("",     "",  "以上"),
    ],
    "pr": (
        "私は、1人でも多くの人が幸せでいて欲しいと思っています。仕事はその人の人生を決める大きな決断であり、"
        "幸せに直結すると考えるため、その大事な決断をサポートする存在は非常に重要です。お客様の強みを最大限に発揮し、"
        "幸せな人生を歩むお手伝いをしたいと考えています。"
        "器械体操・バトントワリング・ダンス・チアリーディングと多くの競技を経験する中で共通していたのは、"
        "「常に目標を持ち、達成のために努力し続け、本気で生きてきた」ということです。"
        "このこれまでの生き方と御社の企業理念が一致し、自分自身もさらに成長したいと考え貴社を志望しました。"
        "私にとっての幸せは「自分にしか出来ないことを発揮できている時」です。一対一で自分の力が試される環境で、"
        "「相談してよかった」と思っていただけるCAを目指すことが私自身の幸せにも繋がると考えています。"
        "貴社はスポーツをしてきた学生に向けた就活支援も充実しており、スポーツ経験者だからこそ出来るアドバイスや、"
        "納得のいく会社選びの手助けに尽力していきたいです。"
    ),
    "wish": "貴社規定に従います。",
}

# ---- レイアウト ----
PAGE_W, PAGE_H = A4
MARGIN_L = 14 * mm
MARGIN_R = 14 * mm
MARGIN_T = 12 * mm
MARGIN_B = 12 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


def draw_resume():
    c = canvas.Canvas(OUTPUT, pagesize=A4)
    c.setLineWidth(0.5)

    # --- タイトル & 日付 ---
    c.setFont(FONT_BOLD, 22)
    c.drawString(MARGIN_L, PAGE_H - MARGIN_T - 6 * mm, "履　歴　書")
    c.setFont(FONT_REG, 9)
    c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T - 4 * mm, DATA["date"])

    y = PAGE_H - MARGIN_T - 12 * mm  # ヘッダ下

    # ===== 基本情報ブロック =====
    photo_w = 28 * mm
    photo_h = 36 * mm
    info_w = CONTENT_W - photo_w - 2 * mm
    info_x = MARGIN_L
    photo_x = MARGIN_L + info_w + 2 * mm
    info_top = y
    info_bottom = info_top - photo_h

    # 写真枠
    c.rect(photo_x, info_bottom, photo_w, photo_h)
    c.setFont(FONT_REG, 7)
    c.drawCentredString(photo_x + photo_w / 2, info_bottom + photo_h / 2 + 4, "写真貼付")
    c.drawCentredString(photo_x + photo_w / 2, info_bottom + photo_h / 2 - 6, "縦40×横30mm")

    # 情報グリッド
    # 行構成: ふりがな / 氏名 / 生年月日・性別
    info_x2 = info_x
    row_h = photo_h / 3  # 12mm相当
    label_w = 18 * mm

    def cell(x, y, w, h, label, value, value_font=FONT_REG, value_size=11, label_size=7):
        c.rect(x, y - h, w, h)
        # ラベル
        c.setFont(FONT_REG, label_size)
        c.drawString(x + 1.5 * mm, y - 3.2 * mm, label)
        # 値
        c.setFont(value_font, value_size)
        c.drawString(x + 1.5 * mm, y - h + 3 * mm, value)

    # 1行目: ふりがな
    cell(info_x2, info_top, info_w, row_h, "ふりがな", DATA["kana"], value_size=10)
    # 2行目: 氏名
    cell(info_x2, info_top - row_h, info_w, row_h, "氏　名", DATA["name"], value_font=FONT_BOLD, value_size=15)
    # 3行目: 生年月日 / 性別
    bd_w = info_w * 0.72
    cell(info_x2, info_top - row_h * 2, bd_w, row_h, "生年月日", DATA["birth"], value_size=10)
    cell(info_x2 + bd_w, info_top - row_h * 2, info_w - bd_w, row_h, "性別", DATA["gender"], value_size=11)

    y = info_bottom - 1 * mm

    # ===== 現住所 / 連絡先 =====
    # ふりがな段(高さkana_h) + 住所段(高さaddr_main_h) の縦2段構成
    kana_h = 6 * mm
    addr_main_h = 12 * mm
    addr_h = kana_h + addr_main_h
    tel_w = 38 * mm
    addr_w = CONTENT_W - tel_w

    def addr_block(y_top, label_addr, zip_str, kana_str, addr_str, tel_str):
        # ふりがな枠
        c.rect(MARGIN_L, y_top - kana_h, addr_w, kana_h)
        c.setFont(FONT_REG, 6.5)
        c.drawString(MARGIN_L + 1.5 * mm, y_top - 3 * mm, "ふりがな")
        c.setFont(FONT_REG, 7.5)
        c.drawString(MARGIN_L + 12 * mm, y_top - 3.8 * mm, kana_str)
        # 電話枠（ふりがな段と同じ高さ）
        c.rect(MARGIN_L + addr_w, y_top - kana_h, tel_w, kana_h)
        c.setFont(FONT_REG, 6.5)
        c.drawString(MARGIN_L + addr_w + 1.5 * mm, y_top - 3 * mm, "電話")
        c.setFont(FONT_REG, 9.5)
        c.drawString(MARGIN_L + addr_w + 9 * mm, y_top - 4.2 * mm, tel_str)
        # 住所枠
        y_addr = y_top - kana_h
        c.rect(MARGIN_L, y_addr - addr_main_h, addr_w, addr_main_h)
        c.setFont(FONT_REG, 6.5)
        c.drawString(MARGIN_L + 1.5 * mm, y_addr - 3 * mm, f"{label_addr}　{zip_str}")
        c.setFont(FONT_REG, 10)
        c.drawString(MARGIN_L + 1.5 * mm, y_addr - addr_main_h + 3 * mm, addr_str)
        # E-mail枠
        c.rect(MARGIN_L + addr_w, y_addr - addr_main_h, tel_w, addr_main_h)
        c.setFont(FONT_REG, 6.5)
        c.drawString(MARGIN_L + addr_w + 1.5 * mm, y_addr - 3 * mm, "E-mail")

    addr_block(y, "現住所", DATA["addr_zip"], DATA["addr_kana"], DATA["addr"], DATA["tel"])
    y -= addr_h + 0.5 * mm
    addr_block(y, "連絡先", DATA["addr2_zip"], DATA["addr2_kana"], DATA["addr2"], DATA["tel2"])
    y -= addr_h + 2 * mm

    # ===== 学歴・職歴 =====
    hist_header_h = 5.5 * mm
    hist_row_h = 5.2 * mm
    yr_w = 12 * mm
    mo_w = 10 * mm
    desc_w = CONTENT_W - yr_w - mo_w

    # ヘッダ
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - hist_header_h, CONTENT_W, hist_header_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawCentredString(MARGIN_L + yr_w / 2, y - hist_header_h + 1.5 * mm, "年")
    c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - hist_header_h + 1.5 * mm, "月")
    c.drawCentredString(MARGIN_L + yr_w + mo_w + desc_w / 2, y - hist_header_h + 1.5 * mm,
                        "学　歴 ・ 職　歴（各別にまとめて書く）")
    y -= hist_header_h

    rows = DATA["history"]
    # 行数を10にして余白を確保（中央寄せ風）
    total_rows = 8
    for i in range(total_rows):
        c.rect(MARGIN_L, y - hist_row_h, yr_w, hist_row_h)
        c.rect(MARGIN_L + yr_w, y - hist_row_h, mo_w, hist_row_h)
        c.rect(MARGIN_L + yr_w + mo_w, y - hist_row_h, desc_w, hist_row_h)
        if i < len(rows):
            yr, mo, desc = rows[i]
            c.setFont(FONT_REG, 10)
            c.drawCentredString(MARGIN_L + yr_w / 2, y - hist_row_h + 1.6 * mm, yr)
            c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - hist_row_h + 1.6 * mm, mo)
            if desc == "学歴":
                c.setFont(FONT_BOLD, 10)
                c.drawCentredString(MARGIN_L + yr_w + mo_w + desc_w / 2,
                                    y - hist_row_h + 1.6 * mm, desc)
            elif desc == "以上":
                c.setFont(FONT_REG, 10)
                c.drawRightString(MARGIN_L + yr_w + mo_w + desc_w - 3 * mm,
                                  y - hist_row_h + 1.6 * mm, desc)
            else:
                c.setFont(FONT_REG, 10)
                c.drawString(MARGIN_L + yr_w + mo_w + 3 * mm,
                             y - hist_row_h + 1.6 * mm, desc)
        y -= hist_row_h

    y -= 2 * mm

    # ===== 志望動機・自己PR =====
    pr_label_h = 5.5 * mm
    pr_body_h = 56 * mm
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - pr_label_h, CONTENT_W, pr_label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawString(MARGIN_L + 2 * mm, y - pr_label_h + 1.5 * mm,
                 "志望の動機、特技、好きな学科、アピールポイントなど")
    y -= pr_label_h
    c.rect(MARGIN_L, y - pr_body_h, CONTENT_W, pr_body_h)
    # 本文を流し込み
    draw_paragraph(c, DATA["pr"], MARGIN_L + 3 * mm, y - 4 * mm,
                   CONTENT_W - 6 * mm, font=FONT_REG, size=9.2, leading=13.5)
    y -= pr_body_h + 1.5 * mm

    # ===== 本人希望記入欄 =====
    wish_label_h = 5 * mm
    wish_body_h = 12 * mm
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - wish_label_h, CONTENT_W, wish_label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 8.5)
    c.drawString(MARGIN_L + 2 * mm, y - wish_label_h + 1.3 * mm,
                 "本人希望記入欄（特に給料・職種・勤務時間・勤務地・その他についての希望などがあれば記入）")
    y -= wish_label_h
    c.rect(MARGIN_L, y - wish_body_h, CONTENT_W, wish_body_h)
    c.setFont(FONT_REG, 10)
    c.drawString(MARGIN_L + 3 * mm, y - 5 * mm, DATA["wish"])

    c.showPage()
    c.save()
    print(f"✅ 生成完了: {OUTPUT}")


def draw_paragraph(c, text, x, y, w, font=FONT_REG, size=10, leading=14):
    """簡易折り返し（CJK向け：文字単位で幅計算）"""
    c.setFont(font, size)
    line = ""
    cur_y = y
    for ch in text:
        test = line + ch
        if pdfmetrics.stringWidth(test, font, size) > w:
            c.drawString(x, cur_y, line)
            cur_y -= leading
            line = ch
        else:
            line = test
    if line:
        c.drawString(x, cur_y, line)


if __name__ == "__main__":
    draw_resume()
