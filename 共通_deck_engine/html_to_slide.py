#!/usr/bin/env python3
"""HTMLの図解を高解像度PNG化してGoogle Slidesに貼り込む再利用ツール（ハイブリッド方式）。

狙い: 複雑な図はHTML/CSSで高品質に作り→画像化→編集可能なGoogle Slidesに挿入。
Slidesの器(テキスト/構成/共有/編集)はそのまま、図だけHTML品質に引き上げる。図は画像だが
データ/HTMLから一発再生成できる。

フロー: ①ローカルGoogle Chrome --headless で HTML→PNG(高DPI) ②Driveにアップ(anyone reader)
       ③Slides APIで createImage(フルブリード) → Slides URL を返す。
使い方: python3 html_to_slide.py <html_path> [board_w board_h]
  env SLIDE_ID=<既存プレゼンID再利用> / TITLE=<新規プレゼン名> / DPI=2
"""
import os
import sys
import time
import uuid
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
EMU = 914400
PW, PH = 9144000, 5143500  # 10in x 5.625in (16:9)


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def render_png(html_path, w, h, dpi):
    png = "/tmp/h2s_%s.png" % uuid.uuid4().hex[:6]
    os.system('"%s" --headless=new --disable-gpu --hide-scrollbars '
              '--force-device-scale-factor=%s --window-size=%d,%d '
              '--screenshot=%s "file://%s" 2>/dev/null' % (CHROME, dpi, w, h, png, html_path))
    time.sleep(1)
    if not os.path.exists(png):
        raise RuntimeError("Chromeでの画像化に失敗: %s" % png)
    return png


def render_png_fromstr(html_str, w, h, dpi):
    hp = "/tmp/h2s_%s.html" % uuid.uuid4().hex[:6]
    open(hp, "w", encoding="utf-8").write(html_str)
    return render_png(hp, w, h, dpi)


def upload_drive(dr, png):
    meta = {"name": "diagram_%s.png" % uuid.uuid4().hex[:6]}
    media = MediaFileUpload(png, mimetype="image/png")
    f = dr.files().create(body=meta, media_body=media, fields="id").execute()
    fid = f["id"]
    dr.permissions().create(fileId=fid, body={"type": "anyone", "role": "reader"},
                            fields="id").execute()
    return fid


def insert_image(html_path, board_w=1280, board_h=720, slide_id=None, title=None, dpi=2):
    c = creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)

    png = render_png(html_path, board_w, board_h, dpi)
    fid = upload_drive(dr, png)
    # Slides createImage が取得できる画像URL（Driveの直リンク）
    img_url = "https://drive.google.com/uc?export=download&id=%s" % fid

    if slide_id:
        pid = slide_id
        pres = slides.presentations().get(presentationId=pid).execute()
        delr = [{"deleteObject": {"objectId": s["objectId"]}} for s in pres.get("slides", [])]
    else:
        pres = slides.presentations().create(
            body={"title": title or "図解スライド｜Tokumori"}).execute()
        pid = pres["presentationId"]
        delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]

    nonce = "h" + uuid.uuid4().hex[:5]
    sid = nonce + "sld1"
    reqs = delr + [
        {"createSlide": {"objectId": sid, "slideLayoutReference": {"predefinedLayout": "BLANK"}, "insertionIndex": 0}},
        {"createImage": {"objectId": nonce + "img1", "url": img_url,
                         "elementProperties": {"pageObjectId": sid,
                             "size": {"width": {"magnitude": PW, "unit": "EMU"}, "height": {"magnitude": PH, "unit": "EMU"}},
                             "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0, "unit": "EMU"}}}},
    ]
    slides.presentations().batchUpdate(presentationId=pid, body={"requests": reqs}).execute()

    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("挿入完了:", url)
    print("  画像Drive ID:", fid, "/ PNG:", png, "/ DPI:", dpi)
    return pid, url


def insert_many(html_paths, title=None, slide_id=None, board_w=1280, board_h=720, dpi=2):
    """複数のHTMLスライドを1つのGoogle Slidesに画像として束ねる（資料＝複数枚）。"""
    c = creds()
    slides = build("slides", "v1", credentials=c)
    dr = build("drive", "v3", credentials=c)
    if slide_id:
        pid = slide_id
        pres = slides.presentations().get(presentationId=pid).execute()
        delr = [{"deleteObject": {"objectId": s["objectId"]}} for s in pres.get("slides", [])]
    else:
        pres = slides.presentations().create(body={"title": title or "資料｜Tokumori"}).execute()
        pid = pres["presentationId"]
        delr = [{"deleteObject": {"objectId": pres["slides"][0]["objectId"]}}]
    slides.presentations().batchUpdate(presentationId=pid, body={"requests": delr}).execute()

    for i, hp in enumerate(html_paths):
        png = render_png(hp, board_w, board_h, dpi)
        fid = upload_drive(dr, png)
        img_url = "https://drive.google.com/uc?export=download&id=%s" % fid
        n = "h%s%d" % (uuid.uuid4().hex[:4], i)
        sid = n + "sld"
        slides.presentations().batchUpdate(presentationId=pid, body={"requests": [
            {"createSlide": {"objectId": sid, "slideLayoutReference": {"predefinedLayout": "BLANK"}, "insertionIndex": i}},
            {"createImage": {"objectId": n + "img", "url": img_url,
                             "elementProperties": {"pageObjectId": sid,
                                 "size": {"width": {"magnitude": PW, "unit": "EMU"}, "height": {"magnitude": PH, "unit": "EMU"}},
                                 "transform": {"scaleX": 1, "scaleY": 1, "translateX": 0, "translateY": 0, "unit": "EMU"}}}},
        ]}).execute()
        print("  slide %d/%d inserted (%s)" % (i + 1, len(html_paths), os.path.basename(hp)))
    url = "https://docs.google.com/presentation/d/%s/edit" % pid
    print("資料 完成:", url, "/", len(html_paths), "枚")
    return pid, url


if __name__ == "__main__":
    hp = sys.argv[1] if len(sys.argv) > 1 else "/tmp/industry_map.html"
    bw = int(sys.argv[2]) if len(sys.argv) > 2 else 1280
    bh = int(sys.argv[3]) if len(sys.argv) > 3 else 720
    insert_image(hp, bw, bh, slide_id=os.environ.get("SLIDE_ID"),
                 title=os.environ.get("TITLE"), dpi=int(os.environ.get("DPI", "2")))
