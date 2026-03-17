#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
履歴書PDF生成スクリプト - 新谷咲希
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, Image
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os

PHOTO_PATH = os.path.join(os.path.dirname(__file__), 'photo.png')

# ── フォント登録 ──────────────────────────────────────────
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))   # ゴシック
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))       # 明朝

FONT_GOTHIC = 'HeiseiKakuGo-W5'
FONT_MINCHO = 'HeiseiMin-W3'

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '新谷咲希_履歴書.pdf')

# ── スタイル定義 ──────────────────────────────────────────
def style(name, font=FONT_GOTHIC, size=10, leading=None, align=TA_LEFT, color=colors.black):
    return ParagraphStyle(
        name,
        fontName=font,
        fontSize=size,
        leading=leading or size * 1.5,
        textColor=color,
        alignment=align,
    )

S_TITLE    = style('title',    size=16, align=TA_CENTER)
S_DATE     = style('date',     size=9,  align=TA_RIGHT)
S_HEADER   = style('header',   size=8)
S_BODY     = style('body',     size=9,  leading=14)
S_BODY_SM  = style('body_sm',  size=8,  leading=12)
S_LABEL    = style('label',    size=8,  color=colors.HexColor('#333333'))
S_CENTER   = style('center',   size=9,  align=TA_CENTER)
S_SECTION  = style('section',  size=9,  align=TA_CENTER)
S_PR       = style('pr',       size=8.5, leading=14)


def cell(text, s=None, bold=False):
    """Paragraph ヘルパー"""
    if s is None:
        s = S_BODY
    return Paragraph(text, s)


def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=12*mm,
        rightMargin=12*mm,
        topMargin=10*mm,
        bottomMargin=10*mm,
    )

    W = A4[0] - 24*mm  # 使用可能幅

    elements = []

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ① タイトル行
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    title_data = [
        [cell('履　歴　書', S_TITLE),
         cell('２０２６年　３月６日現在', S_DATE)],
    ]
    title_table = Table(title_data, colWidths=[W * 0.65, W * 0.35])
    title_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(title_table)
    elements.append(HRFlowable(width=W, thickness=1, color=colors.black, spaceAfter=2))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ② 個人情報ブロック（単一テーブル・隙間なし）
    # JIS規格: 写真 縦4cm×横3cm、氏名3行の右に配置
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4列構成: [ラベル(C0) | メイン内容(C1) | サブ(C2) | 写真(C3)]
    # C0+C1+C2+C3 = W
    PH_W = 30*mm
    PH_H = 40*mm
    C0 = 28*mm       # ラベル列
    C2 = 40*mm       # サブ列（性別・E-mailアドレス）
    C1 = W - C0 - C2 - PH_W  # メイン内容列 ≈ 88mm

    # 行高さ: rows 0-2 の合計 = PH_H = 40mm
    R0 = 10*mm   # ふりがな
    R1 = 20*mm   # 氏名
    R2 = 10*mm   # 生年月日
    R3 =  8*mm   # 住所ふりがな
    R4 = 14*mm   # 現住所
    R5 =  9*mm   # 電話/E-mail
    R6 =  9*mm   # 連絡先

    # 写真コンテンツ準備（LANCZOS高解像度）
    from PIL import Image as PILImage
    import io
    if os.path.exists(PHOTO_PATH):
        pil_img = PILImage.open(PHOTO_PATH).convert('RGB')
        target_px = (int(PH_W / mm * 11.81), int(PH_H / mm * 11.81))  # 300dpi相当
        pil_img = pil_img.resize(target_px, PILImage.LANCZOS)
        buf = io.BytesIO()
        pil_img.save(buf, format='PNG', dpi=(300, 300))
        buf.seek(0)
        photo_content = Image(buf, width=PH_W - 2, height=PH_H - 2)
    else:
        photo_content = cell('写真\n貼付欄', ParagraphStyle('ph', fontName=FONT_GOTHIC,
                fontSize=9, alignment=TA_CENTER, leading=14))

    S_NAME_BIG = ParagraphStyle('name_big', fontName=FONT_GOTHIC,
                                fontSize=16, leading=22, alignment=TA_LEFT)

    info_data = [
        # row 0: ふりがな ／ 写真(C3)はSPANで rows 0-2 を占有
        [cell('ふりがな', S_LABEL), cell('にいや　さき', S_BODY_SM), '', photo_content],
        # row 1: 氏名
        [cell('氏　　名', S_LABEL), cell('新谷　咲希', S_NAME_BIG), '', ''],
        # row 2: 生年月日
        [cell('生年月日', S_LABEL),
         cell('2005年　3月　1日　（満　21　歳）', S_BODY_SM),
         cell('性別　女', S_BODY_SM), ''],
        # row 3: 住所ふりがな（C1-C3 をSPAN）
        [cell('ふりがな', S_LABEL),
         cell('おかやまけんおかやましきたくつしまふくいいちょうめはちのさんのにいいちいちさんごうしつ', S_BODY_SM),
         '', ''],
        # row 4: 現住所（C1-C3 をSPAN）
        [cell('現住所\n〒700-0080', S_LABEL),
         cell('岡山県岡山市北区津島福居1丁目8-3-2　113号室', S_BODY),
         '', ''],
        # row 5: 電話 / E-mail（4列そのまま使用）
        [cell('電話', S_LABEL), cell('080-3373-0557', S_BODY),
         cell('E-mail', S_LABEL), cell('yuu692383@gmail.com', S_BODY_SM)],
        # row 6: 連絡先（C1-C3 をSPAN）
        [cell('連絡先\n〒　　－', S_LABEL),
         cell('（現住所以外に連絡を希望する場合のみ記入）', S_BODY_SM),
         '', ''],
    ]

    info_table = Table(
        info_data,
        colWidths=[C0, C1, C2, PH_W],
        rowHeights=[R0, R1, R2, R3, R4, R5, R6],
    )
    info_table.setStyle(TableStyle([
        # 外枠 + 内格子
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, colors.grey),
        # ── セル結合 ──
        ('SPAN', (3, 0), (3, 2)),    # 写真: col3 × rows 0-2
        ('SPAN', (1, 0), (2, 0)),    # ふりがな内容: cols 1-2 × row 0
        ('SPAN', (1, 1), (2, 1)),    # 氏名内容: cols 1-2 × row 1
        ('SPAN', (1, 3), (3, 3)),    # 住所ふりがな内容: cols 1-3 × row 3
        ('SPAN', (1, 4), (3, 4)),    # 現住所内容: cols 1-3 × row 4
        ('SPAN', (1, 6), (3, 6)),    # 連絡先内容: cols 1-3 × row 6
        # ── ラベル列の背景 ──
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('BACKGROUND', (2, 5), (2, 5), colors.HexColor('#f0f0f0')),  # E-mail ラベル
        # ── 共通パディング・揃え ──
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 3),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        # ── 写真セル ──
        ('ALIGN',         (3, 0), (3, 0), 'CENTER'),
        ('LEFTPADDING',   (3, 0), (3, 0), 1),
        ('RIGHTPADDING',  (3, 0), (3, 0), 1),
        ('TOPPADDING',    (3, 0), (3, 0), 1),
        ('BOTTOMPADDING', (3, 0), (3, 0), 1),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 2*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ③ 学歴・職歴テーブル
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    YW, MW, CW = 14*mm, 10*mm, W - 24*mm
    hist_header = [cell('年', S_CENTER), cell('月', S_CENTER), cell('学　歴・職　歴', S_SECTION)]
    hist_rows = [
        hist_header,
        ['', '', cell('学　歴', S_SECTION)],
        [cell('2023', S_CENTER), cell('3', S_CENTER),
         cell('長崎県立長崎北高等学校　卒業', S_BODY)],
        [cell('2023', S_CENTER), cell('4', S_CENTER),
         cell('岡山大学経済学部経済学科　入学', S_BODY)],
        ['', '', cell('現在、同大学第三学年　在籍中', S_BODY)],
        ['', '', ''],
        ['', '', cell('職　歴', S_SECTION)],
        [cell('2023', S_CENTER), cell('7', S_CENTER),
         cell('イタリアンレストランゾーナイタリア　アルバイト入社', S_BODY)],
        [cell('2024', S_CENTER), cell('9', S_CENTER),
         cell('イタリアンレストランゾーナイタリア　アルバイト退職', S_BODY)],
        [cell('2024', S_CENTER), cell('10', S_CENTER),
         cell('博多天ぷらたかお　アルバイト入社', S_BODY)],
        ['', '', cell('現在、博多天ぷらたかおに在職中', S_BODY)],
        ['', '', ''],
        ['', '', cell('以上', S_CENTER)],
        ['', '', ''],
    ]
    row_h = 8*mm
    hist_table = Table(
        hist_rows,
        colWidths=[YW, MW, CW],
        rowHeights=[row_h] * len(hist_rows),
    )
    hist_table.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#e8e8e8')),
        ('BACKGROUND',    (0, 1), (-1, 1),  colors.HexColor('#f4f4f4')),
        ('BACKGROUND',    (0, 6), (-1, 6),  colors.HexColor('#f4f4f4')),
        ('ALIGN',         (0, 0), (1, -1),  'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (2, 0), (2, -1),  4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('FONTNAME',      (0, 0), (-1, -1), FONT_GOTHIC),
    ]))
    elements.append(hist_table)
    elements.append(Spacer(1, 2*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ④ 免許・資格テーブル
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    lic_rows = [
        [cell('年', S_CENTER), cell('月', S_CENTER), cell('免　許・資　格', S_SECTION)],
        [cell('2024', S_CENTER), cell('3', S_CENTER),
         cell('普通自動車第一種運転免許　取得', S_BODY)],
        ['', '', ''],
        ['', '', ''],
    ]
    lic_table = Table(
        lic_rows,
        colWidths=[YW, MW, CW],
        rowHeights=[row_h] * len(lic_rows),
    )
    lic_table.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID',     (0, 0), (-1, -1), 0.3, colors.grey),
        ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#e8e8e8')),
        ('ALIGN',         (0, 0), (1, -1),  'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',   (2, 0), (2, -1),  4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('FONTNAME',      (0, 0), (-1, -1), FONT_GOTHIC),
    ]))
    elements.append(lic_table)
    elements.append(Spacer(1, 2*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⑤ 志望動機・通勤時間・扶養欄
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MOTIVE_W = W * 0.72
    RIGHT_W  = W - MOTIVE_W

    motive_text = (
        '【志望動機】\n'
        '志望理由は人の選択の質を高めることができるからです。'
        '医療の専門性を持ち、クライアントと求職者の間に介在することで、'
        '双方が納得できる質の高い選択肢を提案できると考えています。'
        'また、人が健康に暮らしていく中で不可欠な医療に携わることで、'
        '働く人だけではなく、その先で医療を受ける患者の生活にも'
        '価値を届けることができる点に魅力を感じています。'
    )

    right_info = [
        [cell('通勤時間', S_LABEL)],
        [cell('約　　　時間　　　分', S_BODY_SM)],
        [cell('扶養家族（配偶者を除く）', S_LABEL)],
        [cell('０人', S_BODY)],
        [cell('配偶者', S_LABEL)],
        [cell('有・無', S_BODY)],
        [cell('配偶者の扶養義務', S_LABEL)],
        [cell('有・無', S_BODY)],
    ]
    right_table = Table(right_info, colWidths=[RIGHT_W],
                        rowHeights=[6*mm] * len(right_info))
    right_table.setStyle(TableStyle([
        ('BOX',          (0, 0), (-1, -1), 0.5, colors.black),
        ('INNERGRID',    (0, 0), (-1, -1), 0.3, colors.grey),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',   (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 1),
        ('FONTSIZE',     (0, 0), (-1, -1), 8),
        ('FONTNAME',     (0, 0), (-1, -1), FONT_GOTHIC),
        ('BACKGROUND',   (0, 0), (-1, 0), colors.HexColor('#f4f4f4')),
        ('BACKGROUND',   (0, 2), (-1, 2), colors.HexColor('#f4f4f4')),
        ('BACKGROUND',   (0, 4), (-1, 4), colors.HexColor('#f4f4f4')),
        ('BACKGROUND',   (0, 6), (-1, 6), colors.HexColor('#f4f4f4')),
    ]))

    motive_para = Paragraph(motive_text, S_PR)
    motive_cell = Table([[motive_para]], colWidths=[MOTIVE_W - 4],
                        rowHeights=[48*mm])
    motive_cell.setStyle(TableStyle([
        ('BOX',         (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',  (0, 0), (-1, -1), 3),
    ]))

    motive_row = Table(
        [[motive_cell, right_table]],
        colWidths=[MOTIVE_W, RIGHT_W],
    )
    motive_row.setStyle(TableStyle([
        ('LEFTPADDING',  (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING',   (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(motive_row)
    elements.append(Spacer(1, 2*mm))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ⑥ 自己PR・学生時代に力を入れたこと
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pr_text = (
        '【自己PR】\n'
        '私の強みは、主体的に行動し、周囲を巻き込みながら改善を実現できることです。'
        'イタリアンレストランでのアルバイトでは、ノンアルコールカクテルのマニュアルに'
        '味の課題を感じ、より良い商品を提供したいと考えました。そこで社員の方に相談し、'
        '同僚とともに配合を試行錯誤しながら新しいレシピを提案しました。'
        '結果としてそのレシピが採用され、お客様からも好評をいただくことができました。'
        'その後、新たな環境に挑戦するため、大型ショッピングモール内の天ぷら専門店へ'
        '職場を変えました。客層や業務の流れが大きく異なる環境でしたが、'
        '前職で培った接客の基礎を活かしながら積極的に学び、早い段階で案内業務を'
        '任されるようになりました。全体を見て状況判断し、スタッフ間で連携しながら'
        '対応する中で、変化に適応する力も磨くことができました。'
        'このように私は、自ら考え行動し、どんな環境でも周囲と協力して成果を出すことができます。\n\n'
        '【学生時代に力を入れたこと】\n'
        '学生時代最も打ち込んだのは部活動の競技かるたです。'
        '高校入学時から約6年間かるたを続けてきました。'
        '６年間続ける中で「自分の課題を解決できないだけでなく、'
        '大学から始めた同期や後輩に実力で抜かれていく」という苦しい経験がありました。'
        'しかし、そこでやめるのではなく、自分の課題を再設定するきっかけに変えました。'
        'まず、先輩からのアドバイスや試合動画から真の課題を見つけ、'
        '課題に対して新しいルーティンを設定しました。'
        'これを練習で積みかさねた結果、目標であった2025年4月の兵庫大会にて'
        '昇段することができました。この経験から地道な努力を続ける継続力と'
        '課題を見直すことの大切さを改めて自覚し、自分の自信につなげることができました。'
    )

    pr_para = Paragraph(pr_text, S_PR)
    pr_table = Table([[pr_para]], colWidths=[W], rowHeights=[68*mm])
    pr_table.setStyle(TableStyle([
        ('BOX',         (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',(0, 0), (-1, -1), 4),
    ]))
    elements.append(pr_table)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PDF 出力
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    doc.build(elements)
    print(f'✅ PDF生成完了: {OUTPUT_PATH}')


if __name__ == '__main__':
    build_pdf()
