#!/usr/bin/env python3
"""ハイブリッド・スライドのデモ：ダニング＝クルーガー曲線（A2 slide26 相当）。

正しいハイブリッド＝「図解はHTML/SVGの高品質画像／タイトル・本文・POINTはネイティブの編集可能テキスト」。
- 図(滑らかな曲線)＝HTML/SVG→PNG→Driveへ→Slidesに画像挿入（中央の作図ゾーン）
- 文字(kicker/タイトル/POINT/フッター)＝build_slides の Deck で**ネイティブ編集可能テキスト**（ブランド統一サイズ）
brand.py トークン共有でトンマナ一致。
"""
import os
import uuid
import warnings

warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

import build_slides as bs
import html_to_slide as H
from build_slides import IN, PW, PH, MX, CW

TOK = H.TOK

# ---- 図解(HTML/SVG)：ダニング＝クルーガー曲線。1280x300 ----
FIG = """<!DOCTYPE html><html><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@500;700;900&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet"/>
<style>*{margin:0;box-sizing:border-box;}html,body{width:1280px;height:300px;background:#fff;font-family:"Noto Sans JP",sans-serif;}
svg{display:block;}.lab{font-size:18px;font-weight:700;fill:#1A1714;}.sub{font-size:15px;fill:#7C736D;font-family:"IBM Plex Mono",monospace;}
.stg{font-size:18px;font-weight:900;}</style></head><body>
<svg width="1280" height="300" viewBox="0 0 1280 300">
  <!-- 軸 -->
  <line x1="80" y1="252" x2="1210" y2="252" stroke="#D9D2CE" stroke-width="2"/>
  <line x1="80" y1="30" x2="80" y2="252" stroke="#D9D2CE" stroke-width="2"/>
  <!-- 曲線(赤・滑らか) -->
  <path d="M110,214 C200,120 255,52 300,52 C355,52 470,214 560,214 C665,214 770,150 855,134 C985,116 1085,100 1175,100"
        fill="none" stroke="#AF322C" stroke-width="4.5" stroke-linecap="round"/>
  <!-- 節目ドット -->
  <circle cx="300" cy="52" r="6" fill="#AF322C"/><circle cx="560" cy="214" r="6" fill="#AF322C"/>
  <circle cx="855" cy="134" r="6" fill="#AF322C"/><circle cx="1175" cy="100" r="6" fill="#AF322C"/>
  <!-- 段階ラベル -->
  <text x="300" y="38" class="stg" fill="#AF322C" text-anchor="middle">①馬鹿の山</text>
  <text x="560" y="238" class="stg" fill="#7A211C" text-anchor="middle">②絶望の谷</text>
  <text x="855" y="118" class="stg" fill="#1A1714" text-anchor="middle">③啓蒙の坂</text>
  <text x="1175" y="84" class="stg" fill="#1A1714" text-anchor="middle">④継続の台地</text>
  <!-- 軸ラベル -->
  <text x="70" y="44" class="sub" text-anchor="end">高い</text>
  <text x="70" y="250" class="sub" text-anchor="end">低い</text>
  <text x="40" y="145" class="lab" text-anchor="middle" transform="rotate(-90 40 145)">自信</text>
  <text x="95" y="278" class="sub">無知</text>
  <text x="1205" y="278" class="sub" text-anchor="end">専門家 →（経験・学習）</text>
</svg></body></html>"""


def main():
    c = H.creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)

    # 図をPNG化→Drive
    open("/tmp/fig_dunning.html", "w", encoding="utf-8").write(FIG)
    png = H.render_png("/tmp/fig_dunning.html", 1280, 300, 2)
    fid = H.upload_drive(dr, png)
    img_url = "https://drive.google.com/uc?export=download&id=%s" % fid

    # ネイティブ文字＋図画像でスライド合成
    pres = slides.presentations().create(body={"title": "【ハイブリッド版】ダニング＝クルーガー（A2 s26）｜Tokumori"}).execute()
    pid = pres["presentationId"]
    delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]
    dk = bs.Deck(total=1, nonce="hy" + uuid.uuid4().hex[:4])
    sid = dk.slide()
    dk.mark(sid)
    dk.kicker(sid, "図解 ・ 自己認知")
    dk.head_title(sid, "ダニング＝クルーガー効果の曲線")
    # 図解(HTML画像)を作図ゾーンに
    imgW = CW
    imgH = CW * 300 // 1280
    dk.reqs.append({"createImage": {"objectId": dk._id("im"), "url": img_url,
        "elementProperties": {"pageObjectId": sid,
            "size": {"width": {"magnitude": imgW, "unit": "EMU"}, "height": {"magnitude": imgH, "unit": "EMU"}},
            "transform": {"scaleX": 1, "scaleY": 1, "translateX": MX, "translateY": int(1.55 * IN), "unit": "EMU"}}}})
    dk.callout(sid, "POINT", "能力が低いほど自信過剰（馬鹿の山）→学ぶほど無知に気づき急落（絶望の谷）→経験で回復。谷で辞めないことが本物。")
    dk.footer(sid, "A2 社会人マインド")
    bs.safe_bu(slides, pid, delr + dk.reqs)

    for b in [{"type": "user", "role": "writer", "emailAddress": "0130atsuya@gmail.com"},
              {"type": "user", "role": "writer", "emailAddress": "atsuya_sato@tokumori.co.jp"},
              {"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}]:
        try:
            dr.permissions().create(fileId=pid, body=b, sendNotificationEmail=False, fields="id").execute()
        except Exception as e:
            print("share note", str(e)[:50])
    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("ハイブリッド版 完成:", url)
    return pid, url


if __name__ == "__main__":
    main()
