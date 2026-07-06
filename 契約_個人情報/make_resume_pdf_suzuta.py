"""履歴書PDF生成（鈴田克志さん用・A4 1枚・JIS規格準拠）"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import registerFontFamily

pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiMin-W3"))
FONT_REG = "HeiseiKakuGo-W5"
FONT_BOLD = "HeiseiKakuGo-W5"
registerFontFamily("HeiseiKakuGo-W5", normal="HeiseiKakuGo-W5", bold="HeiseiKakuGo-W5")

OUTPUT = "/Users/atsuyasato130/Claude AI/履歴書_鈴田克志.pdf"
PHOTO_PATH = "/Users/atsuyasato130/Claude AI/suzuta_photo_p0_0.png"

DATA = {
    "date": "2026年5月19日現在",
    "kana": "すずた　かつし",
    "name": "鈴田　克志",
    "birth": "2003年9月8日生（満22歳）",
    "gender": "男",
    "nationality": "日本",
    "addr_kana": "ひょうごけんひめじししろみだい3ちょうめ8-19",
    "addr_zip": "〒670-0803",
    "addr": "兵庫県姫路市城見台3丁目8-19",
    "tel": "080-3807-7105",
    "email": "kasshi0908@gmail.com",
    "history": [
        ("",     "",  "学歴"),
        ("2019", "4", "兵庫県立姫路西高等学校 普通科 入学"),
        ("2022", "3", "兵庫県立姫路西高等学校 普通科 卒業"),
        ("2022", "4", "龍谷大学 経営学部 経営学科 入学"),
        ("2023", "4", "University of Calgary ESL 入学"),
        ("2024", "4", "University of Calgary ESL 修了"),
        ("2025", "2", "東呉大学 経営学部 交換留学 入学"),
        ("2026", "1", "東呉大学 経営学部 交換留学 修了"),
        ("2027", "3", "龍谷大学 経営学部 経営学科 卒業見込み"),
        ("",     "",  "職歴"),
        ("2025", "3", "株式会社TOKUMORI 営業職 入社"),
        ("",     "",  "現在に至る"),
        ("",     "",  "以上"),
    ],
    "licenses": [
        ("2022", "11", "普通自動車第一種運転免許 取得"),
        ("2024", "4",  "IELTS Academic 5.5 取得"),
    ],
    "pr": (
        "私の強みは、走りながら考え行動を改善し続けることで、組織の成果を最大化できる点である。"
        "長期インターンでは学生集客を担う部署のマネージャーを務めたが、成果が出ず降格を経験した。"
        "原因を分析すると、私はもともと考えることが好きで施策を深く検討できる一方で、行動量が不足し"
        "現場の実態を十分に把握できていなかった。そこで「走りながら考える」ことを意識し、自ら現場に入り"
        "メンバーへのヒアリングや業務観察を通じて課題を整理した。その上で各メンバーの強みを活かした"
        "役割分担を再設計し、新たなユニットの立ち上げや進捗共有の仕組みを整えた結果、組織の成果を向上させ"
        "マネージャーに復帰し、部署全体で目標を達成することができた。また台湾留学では、多国籍メンバーとの"
        "協働を通じて異なる価値観を調整しながら成果を出す力を培った。これらの経験から、多様な強みや"
        "価値観をつなぎ、課題解決を通じて新たな価値を生み出すことにやりがいを感じている。貴社においても、"
        "関係者を巻き込みながら価値創出に貢献したい。"
    ),
    "commute": "―",
    "dependents": "0人",
    "spouse": "無",
    "spouse_support": "無",
    "wish": "貴社規定に従います。",
}

PAGE_W, PAGE_H = A4
MARGIN_L = 14 * mm
MARGIN_R = 14 * mm
MARGIN_T = 12 * mm
MARGIN_B = 12 * mm
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R


def draw_paragraph(c, text, x, y, w, font=FONT_REG, size=10, leading=14):
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


def labeled_cell(c, x, y_top, w, h, label, value,
                 label_size=7, value_font=FONT_REG, value_size=10,
                 value_align="left", value_centered_v=False):
    """ラベル付きセル: ラベルを左上、値を下半分に描画"""
    c.rect(x, y_top - h, w, h)
    c.setFont(FONT_REG, label_size)
    c.drawString(x + 1.5 * mm, y_top - 3.0 * mm, label)
    c.setFont(value_font, value_size)
    if value_centered_v:
        y_val = y_top - h / 2 - value_size * 0.35
    else:
        y_val = y_top - h + 2.8 * mm
    if value_align == "center":
        c.drawCentredString(x + w / 2, y_val, value)
    elif value_align == "right":
        c.drawRightString(x + w - 1.5 * mm, y_val, value)
    else:
        c.drawString(x + 1.5 * mm, y_val, value)


def draw_resume():
    c = canvas.Canvas(OUTPUT, pagesize=A4)
    c.setLineWidth(0.5)

    c.setFont(FONT_BOLD, 22)
    c.drawString(MARGIN_L, PAGE_H - MARGIN_T - 6 * mm, "履　歴　書")
    c.setFont(FONT_REG, 9)
    c.drawRightString(PAGE_W - MARGIN_R, PAGE_H - MARGIN_T - 4 * mm, DATA["date"])

    y = PAGE_H - MARGIN_T - 12 * mm

    # ===== 基本情報ブロック =====
    photo_w = 30 * mm
    photo_h = 40 * mm
    info_w = CONTENT_W - photo_w - 2 * mm
    info_x = MARGIN_L
    photo_x = MARGIN_L + info_w + 2 * mm
    info_top = y
    info_bottom = info_top - photo_h

    # 写真枠 + 画像
    c.rect(photo_x, info_bottom, photo_w, photo_h)
    try:
        c.drawImage(ImageReader(PHOTO_PATH),
                    photo_x + 0.5 * mm, info_bottom + 0.5 * mm,
                    width=photo_w - 1 * mm, height=photo_h - 1 * mm,
                    preserveAspectRatio=True, anchor="c", mask="auto")
    except Exception as e:
        c.setFont(FONT_REG, 7)
        c.drawCentredString(photo_x + photo_w / 2, info_bottom + photo_h / 2, "写真貼付")

    row_h = photo_h / 3

    labeled_cell(c, info_x, info_top, info_w, row_h, "ふりがな", DATA["kana"], value_size=10)
    labeled_cell(c, info_x, info_top - row_h, info_w, row_h, "氏　名", DATA["name"],
                 value_font=FONT_BOLD, value_size=15)
    bd_w = info_w * 0.58
    gd_w = info_w * 0.18
    nt_w = info_w - bd_w - gd_w
    labeled_cell(c, info_x, info_top - row_h * 2, bd_w, row_h,
                 "生年月日", DATA["birth"], value_size=10)
    labeled_cell(c, info_x + bd_w, info_top - row_h * 2, gd_w, row_h,
                 "性別", DATA["gender"], value_size=11, value_align="center", value_centered_v=True)
    labeled_cell(c, info_x + bd_w + gd_w, info_top - row_h * 2, nt_w, row_h,
                 "国籍", DATA["nationality"], value_size=10, value_align="center", value_centered_v=True)

    y = info_bottom - 2 * mm

    # ===== 現住所 =====
    kana_h = 6 * mm
    addr_main_h = 12 * mm
    addr_h = kana_h + addr_main_h
    tel_w = 50 * mm
    addr_w = CONTENT_W - tel_w

    # ふりがな枠
    c.rect(MARGIN_L, y - kana_h, addr_w, kana_h)
    c.setFont(FONT_REG, 6.5)
    c.drawString(MARGIN_L + 1.5 * mm, y - 3 * mm, "ふりがな")
    c.setFont(FONT_REG, 8)
    c.drawString(MARGIN_L + 13 * mm, y - 4.0 * mm, DATA["addr_kana"])
    # 電話枠
    c.rect(MARGIN_L + addr_w, y - kana_h, tel_w, kana_h)
    c.setFont(FONT_REG, 6.5)
    c.drawString(MARGIN_L + addr_w + 1.5 * mm, y - 3 * mm, "電話")
    c.setFont(FONT_REG, 10)
    c.drawString(MARGIN_L + addr_w + 9 * mm, y - 4.3 * mm, DATA["tel"])

    # 住所枠
    y_addr = y - kana_h
    c.rect(MARGIN_L, y_addr - addr_main_h, addr_w, addr_main_h)
    c.setFont(FONT_REG, 6.5)
    c.drawString(MARGIN_L + 1.5 * mm, y_addr - 3 * mm, f"現住所　{DATA['addr_zip']}")
    c.setFont(FONT_REG, 11)
    c.drawString(MARGIN_L + 3 * mm, y_addr - addr_main_h + 4 * mm, DATA["addr"])
    # E-mail枠
    c.rect(MARGIN_L + addr_w, y_addr - addr_main_h, tel_w, addr_main_h)
    c.setFont(FONT_REG, 6.5)
    c.drawString(MARGIN_L + addr_w + 1.5 * mm, y_addr - 3 * mm, "E-mail")
    c.setFont(FONT_REG, 9)
    c.drawString(MARGIN_L + addr_w + 2 * mm, y_addr - addr_main_h + 4 * mm, DATA["email"])

    y -= addr_h + 2 * mm

    # ===== 学歴・職歴 =====
    hist_header_h = 5.5 * mm
    hist_row_h = 4.8 * mm
    yr_w = 12 * mm
    mo_w = 10 * mm
    desc_w = CONTENT_W - yr_w - mo_w

    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - hist_header_h, CONTENT_W, hist_header_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawCentredString(MARGIN_L + yr_w / 2, y - hist_header_h + 1.7 * mm, "年")
    c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - hist_header_h + 1.7 * mm, "月")
    c.drawCentredString(MARGIN_L + yr_w + mo_w + desc_w / 2, y - hist_header_h + 1.7 * mm,
                        "学　歴 ・ 職　歴（各別にまとめて書く）")
    y -= hist_header_h

    rows = DATA["history"]
    total_rows = 14
    for i in range(total_rows):
        c.rect(MARGIN_L, y - hist_row_h, yr_w, hist_row_h)
        c.rect(MARGIN_L + yr_w, y - hist_row_h, mo_w, hist_row_h)
        c.rect(MARGIN_L + yr_w + mo_w, y - hist_row_h, desc_w, hist_row_h)
        if i < len(rows):
            yr, mo, desc = rows[i]
            c.setFont(FONT_REG, 9.5)
            c.drawCentredString(MARGIN_L + yr_w / 2, y - hist_row_h + 1.5 * mm, yr)
            c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - hist_row_h + 1.5 * mm, mo)
            if desc in ("学歴", "職歴"):
                c.setFont(FONT_BOLD, 10)
                c.drawCentredString(MARGIN_L + yr_w + mo_w + desc_w / 2,
                                    y - hist_row_h + 1.5 * mm, desc)
            elif desc in ("以上", "現在に至る"):
                c.setFont(FONT_REG, 9.5)
                c.drawRightString(MARGIN_L + yr_w + mo_w + desc_w - 4 * mm,
                                  y - hist_row_h + 1.5 * mm, desc)
            else:
                c.setFont(FONT_REG, 9.5)
                c.drawString(MARGIN_L + yr_w + mo_w + 3 * mm,
                             y - hist_row_h + 1.5 * mm, desc)
        y -= hist_row_h

    y -= 2 * mm

    # ===== 免許・資格 =====
    lic_header_h = 5.5 * mm
    lic_row_h = 4.8 * mm
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - lic_header_h, CONTENT_W, lic_header_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawCentredString(MARGIN_L + yr_w / 2, y - lic_header_h + 1.7 * mm, "年")
    c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - lic_header_h + 1.7 * mm, "月")
    c.drawCentredString(MARGIN_L + yr_w + mo_w + desc_w / 2, y - lic_header_h + 1.7 * mm,
                        "免　許 ・ 資　格")
    y -= lic_header_h

    lic_total = 3
    for i in range(lic_total):
        c.rect(MARGIN_L, y - lic_row_h, yr_w, lic_row_h)
        c.rect(MARGIN_L + yr_w, y - lic_row_h, mo_w, lic_row_h)
        c.rect(MARGIN_L + yr_w + mo_w, y - lic_row_h, desc_w, lic_row_h)
        if i < len(DATA["licenses"]):
            yr, mo, desc = DATA["licenses"][i]
            c.setFont(FONT_REG, 9.5)
            c.drawCentredString(MARGIN_L + yr_w / 2, y - lic_row_h + 1.5 * mm, yr)
            c.drawCentredString(MARGIN_L + yr_w + mo_w / 2, y - lic_row_h + 1.5 * mm, mo)
            c.drawString(MARGIN_L + yr_w + mo_w + 3 * mm,
                         y - lic_row_h + 1.5 * mm, desc)
        elif i == len(DATA["licenses"]):
            c.setFont(FONT_REG, 9.5)
            c.drawRightString(MARGIN_L + yr_w + mo_w + desc_w - 4 * mm,
                              y - lic_row_h + 1.5 * mm, "以上")
        y -= lic_row_h

    y -= 2 * mm

    # ===== 志望動機（左）/ 副情報（右）=====
    side_w = 48 * mm
    pr_w = CONTENT_W - side_w
    block_h = 60 * mm
    label_h = 5.5 * mm

    # --- 左: 志望動機ラベル + 本文 ---
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - label_h, pr_w, label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawString(MARGIN_L + 2 * mm, y - label_h + 1.7 * mm,
                 "志望の動機、特技、アピールポイントなど")
    c.rect(MARGIN_L, y - block_h, pr_w, block_h - label_h)
    # 注意: 上のlabel枠とbody枠の上端を一致させる
    body_top = y - label_h
    body_h = block_h - label_h
    c.rect(MARGIN_L, body_top - body_h, pr_w, body_h)
    draw_paragraph(c, DATA["pr"], MARGIN_L + 3 * mm, body_top - 4 * mm,
                   pr_w - 6 * mm, font=FONT_REG, size=9.0, leading=12.6)

    # --- 右: 通勤時間 / 扶養家族 / 配偶者・扶養義務 ---
    sx = MARGIN_L + pr_w
    # 3区画に均等分割
    sub_h = block_h / 3

    # 区画1: 通勤時間
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(sx, y - label_h, side_w, label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 9)
    c.drawString(sx + 2 * mm, y - label_h + 1.7 * mm, "通勤時間")
    c.rect(sx, y - sub_h, side_w, sub_h - label_h)
    c.setFont(FONT_REG, 10)
    c.drawString(sx + 3 * mm, y - sub_h + 3 * mm, f"約　{DATA['commute']}")

    # 区画2: 扶養家族（配偶者を除く）
    y2 = y - sub_h
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(sx, y2 - label_h, side_w, label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 8.5)
    c.drawString(sx + 2 * mm, y2 - label_h + 1.7 * mm, "扶養家族（配偶者を除く）")
    c.rect(sx, y2 - sub_h, side_w, sub_h - label_h)
    c.setFont(FONT_REG, 10)
    c.drawString(sx + 3 * mm, y2 - sub_h + 3 * mm, DATA["dependents"])

    # 区画3: 配偶者 / 配偶者の扶養義務（横2分割）
    y3 = y - sub_h * 2
    half_w = side_w / 2
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(sx, y3 - label_h, half_w, label_h, fill=1, stroke=1)
    c.rect(sx + half_w, y3 - label_h, half_w, label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 8.5)
    c.drawString(sx + 2 * mm, y3 - label_h + 1.7 * mm, "配偶者")
    c.drawString(sx + half_w + 2 * mm, y3 - label_h + 1.7 * mm, "配偶者の扶養義務")
    c.rect(sx, y3 - sub_h, half_w, sub_h - label_h)
    c.rect(sx + half_w, y3 - sub_h, half_w, sub_h - label_h)
    c.setFont(FONT_REG, 10)
    c.drawCentredString(sx + half_w / 2, y3 - sub_h + 3 * mm, DATA["spouse"])
    c.drawCentredString(sx + half_w * 1.5, y3 - sub_h + 3 * mm, DATA["spouse_support"])

    y -= block_h + 2 * mm

    # ===== 本人希望記入欄 =====
    wish_label_h = 5 * mm
    wish_body_h = 14 * mm
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(MARGIN_L, y - wish_label_h, CONTENT_W, wish_label_h, fill=1, stroke=1)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT_BOLD, 8.5)
    c.drawString(MARGIN_L + 2 * mm, y - wish_label_h + 1.5 * mm,
                 "本人希望記入欄（特に給料・職種・勤務時間・勤務地・その他についての希望などがあれば記入）")
    y -= wish_label_h
    c.rect(MARGIN_L, y - wish_body_h, CONTENT_W, wish_body_h)
    c.setFont(FONT_REG, 10)
    c.drawString(MARGIN_L + 3 * mm, y - 5 * mm, DATA["wish"])

    c.showPage()
    c.save()
    print(f"生成完了: {OUTPUT}")


if __name__ == "__main__":
    draw_resume()
