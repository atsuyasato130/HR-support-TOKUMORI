#!/usr/bin/env python3
"""スマート図解ギャラリーを生成→PNG→新規Slides挿入→共有。"""
import subprocess
import warnings

warnings.filterwarnings("ignore")
from googleapiclient.discovery import build

import build_smart_gallery  # noqa: F401  (実行で /tmp/smart.html 生成)
import html_to_slide as H

pid, url = H.insert_image("/tmp/smart.html", 1280, 720,
                          title="【スマート図解】洗練版ギャラリー｜Tokumori", dpi=2)

dr = build("drive", "v3", credentials=H.creds())
for b in [{"type": "user", "role": "writer", "emailAddress": "atsuya_sato@tokumori.co.jp"},
          {"type": "domain", "role": "reader", "domain": "tokumori.co.jp"}]:
    try:
        dr.permissions().create(fileId=pid, body=b, sendNotificationEmail=False, fields="id").execute()
    except Exception as e:
        print("share note:", str(e)[:60])
print("SMART GALLERY:", url)
