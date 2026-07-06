#!/usr/bin/env python3
"""コンサル級「密な1枚図解」生成エンジン（第一弾＝業界マップ）。

build_slides.py の Deck プリミティブ（slide/rect/text/fit_size・色・フォント・safe_bu）を再利用し、
編集可能な Google Slides として“密な1枚”インフォグラフィックを生成する。
最終ゴール＝メンバー＆Cowork から仕様で呼べる再利用ツール（Stage2-3）。本ファイルはその土台。

使い方: python3 build_infographic.py   → 業界マップ（新規スタンドアロンSlides）を作成しURLを出力。
env SHARE=0130atsuya@gmail.com,... で編集共有先を指定（既定=本人＋tokumoriドメイン閲覧）。
"""
import json
import os
import uuid
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import build_slides as bs
from build_slides import (RED, REDD, INK, SUB, WHITE, PANEL, RULE, FAINT, LRED,
                          DISP, HEAD, BODY, MONO, IN, PW, PH, MX, CW, safe_bu)

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


# ===== 再利用「密図解」部品 =====
def headline(dk, sid, kicker, title, subtitle):
    dk.text(sid, MX, int(0.26 * IN), CW - int(2.7 * IN), int(0.22 * IN),
            [(kicker, {"size": 9.5, "color": RED, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX, int(0.46 * IN), CW - int(2.7 * IN), int(0.5 * IN),
            [(title, {"size": 23, "color": INK, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(23, 15))
    dk.rect(sid, MX, int(1.0 * IN), int(0.66 * IN), int(0.045 * IN), fill=RED)
    dk.text(sid, MX, int(1.07 * IN), CW - int(2.7 * IN), int(0.24 * IN),
            [(subtitle, {"size": 11, "color": SUB, "font": BODY})], valign="MIDDLE", fit=(11, 8.5))


def legend_box(dk, sid, rows, w=int(2.45 * IN), h=int(0.86 * IN)):
    x = PW - MX - w
    y = int(0.3 * IN)
    dk.rect(sid, x, y, w, h, fill=PANEL, line=RULE, lw=1, round=True)
    dk.text(sid, x + int(0.16 * IN), y + int(0.08 * IN), w - int(0.3 * IN), int(0.2 * IN),
            [("【凡例】", {"size": 8.5, "color": SUB, "bold": True, "font": MONO})])
    yy = y + int(0.3 * IN)
    for runs in rows:
        dk.text(sid, x + int(0.16 * IN), yy, w - int(0.3 * IN), int(0.22 * IN), runs, valign="MIDDLE")
        yy += int(0.24 * IN)


def keytakeaway(dk, sid, text, y=int(4.62 * IN), h=int(0.5 * IN)):
    dk.rect(sid, MX, y, CW, h, fill=LRED, round=True)
    dk.rect(sid, MX, y, int(0.08 * IN), h, fill=RED)
    dk.text(sid, MX + int(0.24 * IN), y, int(1.5 * IN), h,
            [("KEY TAKEAWAY", {"size": 10, "color": RED, "bold": True, "font": MONO})], valign="MIDDLE")
    dk.text(sid, MX + int(1.78 * IN), y, CW - int(2.0 * IN), h,
            [(text, {"size": 11, "color": INK, "font": BODY})], valign="MIDDLE", fit=(11, 8.5))


def cluster_header(dk, sid, x, y, w, label):
    dk.rect(sid, x, y + int(0.24 * IN), w, 9525, fill=RED)  # 細い赤下線
    dk.text(sid, x, y, w, int(0.24 * IN),
            [(label, {"size": 10, "color": RED, "bold": True, "font": HEAD})], valign="MIDDLE", fit=(10, 8))


# ===== 業界マップ =====
def pop_color(p):
    return RED if p == "高" else (INK if p in ("中〜高", "中") else SUB)


def pop_bold(p):
    return p in ("高", "中〜高")


def growth_mark(g):
    return ("▲", RED) if g == "拡大" else (("▼", SUB) if g == "縮小" else ("▬", SUB))


# 列幅が狭いので長い業界名は短縮表示（≤8全角目安）
NAME_SHORT = {
    "その他金融（カード/リース/フィンテック）": "その他金融", "保険（生保・損保）": "保険",
    "医療・介護・教育サービス": "医療・介護・教育", "鉄道・運輸（旅客）": "鉄道・運輸",
    "旅行・ホテル・レジャー": "旅行・ホテル", "電力・ガス・エネルギー": "電力・ガス",
    "SIer・システム開発": "SIer・開発", "SaaS・スタートアップ": "SaaS・新興", "SES・客先常駐": "SES",
    "電機・電子・精密": "電機・精密", "医薬品・医療機器": "医薬・医療機器", "機械・重工・プラント": "機械・重工",
    "その他メーカー（化粧品・日用品）": "その他メーカー", "百貨店・スーパー・コンビニ": "百貨店・小売",
    "外食・フードサービス": "外食・フード", "陸運・倉庫・3PL": "陸運・倉庫",
    "不動産（デベロッパー）": "不動産デベ", "住宅・ハウスメーカー": "住宅・ハウス",
    "公務員・公的機関": "公務員・公的", "建設・ゼネコン": "建設・ゼネコン",
}
COMP_SHORT = {"SES・客先常駐": "中小SES多数", "公務員・公的機関": "各府省庁・自治体"}


def build_industry_map():
    c = creds()
    slides = build("slides", "v1", credentials=c)
    drive = build("drive", "v3", credentials=c)
    IND = json.load(open(os.path.join(BASE, "data_ca_training.json"), encoding="utf-8"))["INDUSTRIES"]
    MKT = json.load(open(os.path.join(BASE, "data_industry_market.json"), encoding="utf-8"))["MARKET"]

    idf = os.path.join(BASE, ".imap_id")
    if os.path.exists(idf):
        pid = open(idf).read().strip()
        pres = slides.presentations().get(presentationId=pid).execute()
        delr = [{"deleteObject": {"objectId": s["objectId"]}} for s in pres.get("slides", [])]
    else:
        pres = slides.presentations().create(body={"title": "業界マップ｜Tokumori（36業界 × 人気度 × 成長性）"}).execute()
        pid = pres["presentationId"]
        open(idf, "w").write(pid)
        delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]

    dk = bs.Deck(total=1, nonce="ix" + uuid.uuid4().hex[:4])
    sid = dk.slide()
    headline(dk, sid, "INDUSTRY MAP ・ 業界理解", "日本の主要36業界マップ",
             "人気度 × 成長性で全体像をつかむ ／ 10カテゴリ・36業界")
    legend_box(dk, sid, [
        [("人気度  ", {"size": 8.5, "color": SUB, "font": MONO}),
         ("高", {"size": 8.5, "color": RED, "bold": True, "font": HEAD}),
         (" / 中 / ", {"size": 8.5, "color": INK, "font": HEAD}),
         ("低", {"size": 8.5, "color": SUB, "font": HEAD})],
        [("成長  ", {"size": 8.5, "color": SUB, "font": MONO}),
         ("▲拡大", {"size": 8.5, "color": RED, "bold": True, "font": BODY}),
         (" ▬横ばい ▼縮小", {"size": 8.5, "color": SUB, "font": BODY})],
    ])

    # カテゴリ→業界index
    by_cat = {}
    for i, ind in enumerate(IND):
        by_cat.setdefault(ind[1], []).append(i)
    COLMAP = [["商社", "金融"], ["サービス"], ["IT", "小売"], ["メーカー"],
              ["広告マスコミ", "物流・運輸"], ["不動産・建設", "官公庁"]]

    ncol = len(COLMAP)
    cgap = int(0.13 * IN)
    colw = (CW - cgap * (ncol - 1)) // ncol
    map_top = int(1.42 * IN)
    head_h = int(0.26 * IN)
    chip_h = int(0.33 * IN)
    clu_gap = int(0.07 * IN)
    arr_w = int(0.22 * IN)

    for ci, cats in enumerate(COLMAP):
        x = MX + ci * (colw + cgap)
        y = map_top
        for cat in cats:
            cluster_header(dk, sid, x, y, colw, cat)
            y += head_h
            for idx in by_cat.get(cat, []):
                ind = IND[idx]
                name = NAME_SHORT.get(ind[0], ind[0])
                comp = COMP_SHORT.get(ind[0], ind[4].split("、")[0].split("/")[0].split("（")[0][:11])
                pop = ind[8] if len(ind) > 8 else "中"
                g = MKT[idx].get("成長ランク", "横ばい") if idx < len(MKT) else "横ばい"
                gl, gc = growth_mark(g)
                dk.text(sid, x, y, colw - arr_w, int(0.2 * IN),
                        [(name, {"size": 9, "color": pop_color(pop), "bold": pop_bold(pop), "font": HEAD})],
                        valign="MIDDLE", fit=(9, 6.5))
                dk.text(sid, x + colw - arr_w, y, arr_w, int(0.2 * IN),
                        [(gl, {"size": 9, "color": gc, "bold": True, "font": BODY})], align="END", valign="MIDDLE")
                dk.text(sid, x, y + int(0.18 * IN), colw, int(0.15 * IN),
                        [(comp, {"size": 6.5, "color": SUB, "font": MONO})], fit=(6.5, 5))
                y += chip_h
            y += clu_gap

    keytakeaway(dk, sid,
                "拡大業界（IT・金融・先端メーカー・エンタメ）と横ばい/縮小（マスコミ・住宅）に二極化。"
                "“人気＝成長”ではない（マスコミは人気高×縮小／SESは人気低×拡大）。志望は人気でなく“成長性 × 自分の適性”で選ぶ。")
    dk.text(sid, MX, PH - int(0.32 * IN), CW, int(0.2 * IN),
            [("出典：data_ca_training／industry_market（矢野経済研究所・経産省・各社IR 等, 2023-2025）。人気度=就活人気の概観。配布前に最新値を要確認。",
              {"size": 7, "color": SUB, "font": MONO})], valign="MIDDLE")

    safe_bu(slides, pid, delr + dk.reqs)

    # 共有（本人=編集／tokumoriドメイン=閲覧・通知なし）
    editors = [e.strip() for e in os.environ.get("SHARE", "0130atsuya@gmail.com,atsuya_sato@tokumori.co.jp").split(",") if e.strip()]
    for em in editors:
        try:
            drive.permissions().create(fileId=pid, body={"type": "user", "role": "writer", "emailAddress": em},
                                       sendNotificationEmail=False, fields="id").execute()
        except Exception as e:
            print("share note:", em, str(e)[:80])
    try:
        drive.permissions().create(fileId=pid, body={"type": "domain", "role": "reader", "domain": "tokumori.co.jp"},
                                   sendNotificationEmail=False, fields="id").execute()
    except Exception as e:
        print("domain share note:", str(e)[:80])

    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("業界マップ 作成:", pid)
    print("URL:", url)
    print("要素数:", len(dk.reqs), "/ 業界:", len(IND))
    return pid, url


if __name__ == "__main__":
    build_industry_map()
