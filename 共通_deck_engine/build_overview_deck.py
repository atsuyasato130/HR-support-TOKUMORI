#!/usr/bin/env python3
"""概要資料（サービス/採用ピッチ）クリーン版サンプル＝corporateテーマの実証。

脱AIリファイン済みの build_slides.Deck を theme="corporate"（見出し明朝・余白広め・ブランド赤1アクセント）で使い、
HPやピッチで使える“見やすい”サービス概要を生成。図はハイブリッド（HTML/SVG→PNG→Slides画像）で1枚。
※数値は出典付きの市場データのみ。自社実績は載せない（サンプルで虚偽を作らない）。
"""
import os
import uuid
import warnings

warnings.filterwarnings("ignore")
from googleapiclient.discovery import build

import build_slides as bs
import html_to_slide as H
from build_slides import IN, PH, MX, CW

bs.set_theme("corporate")

# ---- ハイブリッド図：サービス全体像（4ステップ・スマート＝細線/番号/赤1アクセント）。1280x360 ----
FONTS = ('<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&'
         'family=Shippori+Mincho+B1:wght@800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet"/>')

STEPS = [("01", "母集団形成", "媒体・スカウト・リファラルを設計し候補者を集める"),
         ("02", "選考設計", "要件定義から面接フローまでKPIで可視化"),
         ("03", "面談・クロージング", "キャリアに伴走し、納得した意思決定を支援"),
         ("04", "定着・活躍支援", "入社後フォローで早期離職を防ぎ戦力化")]


def fig_service_flow():
    cards = ""
    n = len(STEPS)
    for i, (num, title, desc) in enumerate(STEPS):
        x = 40 + i * 305
        accent = (i == 2)  # 主役＝面談・クロージング（Tokumoriの中核）に赤1アクセント
        bd = "#AF322C" if accent else "#E6E3E1"
        nc = "#AF322C" if accent else "#B3ABA5"
        cards += (
            f'<g transform="translate({x},60)">'
            f'<rect x="0" y="0" width="270" height="200" rx="16" fill="#fff" stroke="{bd}" stroke-width="{1.6 if accent else 1}"/>'
            f'<text x="22" y="56" font-family="IBM Plex Mono" font-size="22" font-weight="500" fill="{nc}">{num}</text>'
            f'<line x1="22" y1="72" x2="50" y2="72" stroke="{nc}" stroke-width="2"/>'
            f'<text x="22" y="112" font-family="Shippori Mincho B1" font-size="22" font-weight="800" fill="#1A1714">{title}</text>'
            f'<text x="22" y="150" font-family="Noto Sans JP" font-size="13.5" fill="#6B6B6B"><tspan x="22" dy="0">{desc[:13]}</tspan><tspan x="22" dy="22">{desc[13:]}</tspan></text>'
            f'</g>')
        if i < n - 1:
            ax = 40 + i * 305 + 270
            cards += (f'<line x1="{ax+4}" y1="160" x2="{ax+27}" y2="160" stroke="#C7BFB9" stroke-width="1.5" marker-end="url(#ov_ar)"/>')
    return ('<!DOCTYPE html><html><head><meta charset="utf-8"/>' + FONTS +
            '<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;height:360px;background:#fff;}svg{display:block;}</style>'
            '</head><body><svg width="1280" height="360" viewBox="0 0 1280 360">'
            '<defs><marker id="ov_ar" markerWidth="9" markerHeight="9" refX="6" refY="4.5" orient="auto">'
            '<path d="M0,0 L9,4.5 L0,9 Z" fill="#C7BFB9"/></marker></defs>' + cards + '</svg></body></html>')


def cover_corp(dk, title, sub, meta):
    sid = dk.slide()
    dk.rect(sid, 0, 0, int(0.12 * IN), PH, fill=bs.RED)  # 左の赤レール（ブランド）
    dk.mark(sid)
    dk.text(sid, MX + int(0.42 * IN), int(0.4 * IN), CW, int(0.26 * IN),
            [("TOKUMORI ・ HR PARTNER", {"size": 10, "color": bs.SUB, "bold": True, "font": bs.MONO})], valign="MIDDLE")
    dk.text(sid, MX, int(1.85 * IN), CW, int(1.5 * IN),
            [(title, {"size": 46, "color": bs.INK, "bold": True, "font": bs.DISP})], valign="MIDDLE", fit=(46, 28))
    dk.rect(sid, MX, int(3.18 * IN), int(1.0 * IN), int(0.05 * IN), fill=bs.RED)
    dk.text(sid, MX, int(3.42 * IN), CW, int(0.6 * IN),
            [(sub, {"size": 16, "color": bs.SUB, "font": bs.BODY})])
    dk.text(sid, MX, PH - int(0.7 * IN), CW, int(0.3 * IN),
            [(meta, {"size": 10, "color": bs.SUB, "font": bs.MONO})], valign="MIDDLE")
    return sid


def cta_corp(dk, big, lines, contact):
    sid = dk.slide()
    dk.rect(sid, 0, 0, int(0.12 * IN), PH, fill=bs.RED)
    dk.mark(sid)
    dk.text(sid, MX + int(0.42 * IN), int(0.4 * IN), CW, int(0.26 * IN),
            [("LET'S WORK TOGETHER", {"size": 10, "color": bs.SUB, "bold": True, "font": bs.MONO})], valign="MIDDLE")
    dk.text(sid, MX, int(1.5 * IN), CW, int(1.1 * IN),
            [(big, {"size": 36, "color": bs.INK, "bold": True, "font": bs.DISP})], valign="MIDDLE", fit=(36, 22))
    y = int(2.85 * IN)
    for ln in lines:
        dk.rect(sid, MX + int(0.02 * IN), y + int(0.12 * IN), int(0.1 * IN), int(0.1 * IN), fill="B8AFA9")
        dk.text(sid, MX + int(0.32 * IN), y, CW - int(0.32 * IN), int(0.42 * IN),
                [(ln, {"size": 14, "color": bs.INK, "font": bs.BODY})], valign="MIDDLE")
        y += int(0.52 * IN)
    dk.rect(sid, MX, int(4.35 * IN), CW, int(0.62 * IN), fill=bs.PANEL, line=bs.RULE, lw=1, round=True)
    dk.rect(sid, MX, int(4.35 * IN), int(0.06 * IN), int(0.62 * IN), fill=bs.RED)
    dk.text(sid, MX + int(0.28 * IN), int(4.35 * IN), CW - int(0.56 * IN), int(0.62 * IN),
            [("お問い合わせ  ", {"size": 12, "color": bs.RED, "bold": True, "font": bs.BODY}),
             (contact, {"size": 12, "color": bs.INK, "font": bs.MONO})], valign="MIDDLE")
    return sid


def main():
    c = H.creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)

    # ハイブリッド図を先にPNG化→Drive（URLを先に得る）
    png = H.render_png_fromstr(fig_service_flow(), 1280, 360, 2)
    fid = H.upload_drive(dr, png)
    fig_url = "https://drive.google.com/uc?export=download&id=%s" % fid

    pres = slides.presentations().create(body={"title": "TOKUMORI ｜ サービス概要（サンプル・corporate）"}).execute()
    pid = pres["presentationId"]
    delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]

    dk = bs.Deck(total=7, nonce="ov" + uuid.uuid4().hex[:4])
    dk.tag = "サービス概要"

    # 1. 表紙
    cover_corp(dk, "採用を、データで強くする。",
               "母集団形成から定着まで——人とデータで伴走するHRパートナー。",
               "SERVICE OVERVIEW ・ 2026 ・ 株式会社TOKUMORI")
    # 2. 課題
    dk.content("ISSUE ・ 採用の現場で起きていること", "“採れない・続かない”は構造の問題", [
        "母集団形成が難しく、要件に合う候補者に出会えない",
        "選考が属人化し、どこで落ちているかが見えない",
        "面接官・人事の工数が逼迫し、対応スピードが落ちる",
        "入社後のミスマッチで早期離職が起きる",
    ], callout=("POINT", "個々の頑張りでなく、母集団〜定着までを“仕組み”で設計し直すことが要る。"))
    # 3. 市場データ（出典付）
    dk.statcards("DATA ・ 労働市場の前提", "数字が示す、採用の難度", [
        ("33.8%", "大卒3年以内離職率", "厚労省 2024"),
        ("1.2倍", "新卒求人倍率の高止まり", "リクルートWS 2025"),
        ("55.2%", "企業のAI業務利用率(日本)", "総務省 2025"),
    ], note="出典は各調査の公表値。数値は編集してご利用いただけます。")
    # 4. 提供価値
    dk.cards("VALUE ・ 提供価値", "3つの強みで、採用を前に進める", [
        ("RPO伴走", "母集団〜クロージング", "要件定義から母集団形成・面談・クロージングまで、採用プロセスを実働で代行・伴走する。"),
        ("データ基盤", "KPIを可視化", "Salesforce／スプレッドシートで歩留まりとKPIを可視化し、意思決定を速くする。"),
        ("AI活用", "工数を圧縮", "候補者リサーチ・紹介文・レポート作成をAIで自動化し、人は対人業務に集中する。"),
    ])
    # 5. サービス全体像（ハイブリッド図）
    sid = dk.slide()
    dk.mark(sid); dk.kicker(sid, "FLOW ・ サービス全体像"); dk.head_title(sid, "母集団形成から定着まで、一気通貫")
    imgH = CW * 360 // 1280
    dk.reqs.append({"createImage": {"objectId": dk._id("im"), "url": fig_url,
        "elementProperties": {"pageObjectId": sid,
            "size": {"width": {"magnitude": CW, "unit": "EMU"}, "height": {"magnitude": imgH, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": MX, "translateY": int(1.7 * IN), "unit": "EMU"}}}})
    dk.callout(sid, "POINT", "中核は“面談・クロージング”。候補者の納得を引き出すことが、定着と活躍の起点になる。")
    dk.footer(sid)
    # 6. 導入の流れ
    dk.flow("ONBOARDING ・ 導入の流れ", "最短2週間で、運用を立ち上げる", [
        ("1", "お問い合わせ", "現状と課題を共有"),
        ("2", "課題ヒアリング", "要件・KPIを定義"),
        ("3", "設計", "母集団・選考フロー設計"),
        ("4", "運用・伴走", "実働で採用を前進"),
    ], "立ち上げ後は週次でKPIをレビューし、母集団・歩留まりを継続改善します。")
    # 7. CTA
    cta_corp(dk, "採用の“仕組み化”を、一緒に。",
             ["まずは現状のKPIと課題を30分でヒアリングします",
              "母集団〜定着まで、必要な範囲だけ伴走可能です",
              "データ基盤・AI活用の導入支援も承ります"],
             "atsuya_sato@tokumori.co.jp ／ 株式会社TOKUMORI")

    bs.safe_bu(slides, pid, delr + dk.reqs)

    for b in [{"type": "user", "role": "writer", "emailAddress": "0130atsuya@gmail.com"},
              {"type": "user", "role": "writer", "emailAddress": "atsuya_sato@tokumori.co.jp"},
              {"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}]:
        try:
            dr.permissions().create(fileId=pid, body=b, sendNotificationEmail=False, fields="id").execute()
        except Exception as e:
            print("share note:", str(e)[:60])
    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("OVERVIEW(corporate):", url, "/", dk.page, "pages")
    return pid, url


if __name__ == "__main__":
    main()
