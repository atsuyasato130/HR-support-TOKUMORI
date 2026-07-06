#!/usr/bin/env python3
"""
研修アセット（スプレッドシート＋全Slidesデッキ＋全Formsテスト）に閲覧権限を一括付与する。
前提: GCPプロジェクト 711363726261 で Drive API を有効化しておくこと
  → https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=711363726261

使い方:
  python3 share_assets.py                      # 既定: tokumori.co.jp ドメインに reader
  SHARE_MODE=anyone python3 share_assets.py     # リンクを知る全員に reader
  SHARE_MODE=emails EMAILS="a@x,b@y" python3 share_assets.py  # 指定メールに reader
"""
import json
import os
import time
import warnings

warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
DOMAIN = os.environ.get("DOMAIN", "tokumori.co.jp")
MODE = os.environ.get("SHARE_MODE", "domain")
EMAILS = [e.strip() for e in os.environ.get("EMAILS", "").split(",") if e.strip()]
EDITORS = [e.strip() for e in os.environ.get("EDITORS", "").split(",") if e.strip()]


def file_ids():
    ids = {}
    ids["スプレッドシート(研修ハブ)"] = open(os.path.join(BASE, ".ca_sheet_id")).read().strip()
    sm = json.load(open(os.path.join(BASE, ".slide_map.json")))
    fm = json.load(open(os.path.join(BASE, ".forms_map.json")))
    for mid, pid in sm.items():
        ids["Slides:%s" % mid] = pid
    for mid, fid in fm.items():
        ids["Forms:%s" % mid] = fid
    # INCLUDE_ADMIN=1 で管理ダッシュボードも対象に含める
    adm = os.path.join(BASE, ".admin_sheet_id")
    if os.environ.get("INCLUDE_ADMIN") and os.path.exists(adm):
        ids["管理ダッシュボード"] = open(adm).read().strip()
    return ids


def perm_body():
    perms = []
    if MODE == "anyone":
        perms.append({"type": "anyone", "role": "reader"})
    elif MODE == "emails":
        perms += [{"type": "user", "role": "reader", "emailAddress": e} for e in EMAILS]
    else:
        perms.append({"type": "domain", "role": "reader", "domain": DOMAIN})
    # 個別の編集者(writer)を追加付与（EDITORS環境変数・カンマ区切り）
    perms += [{"type": "user", "role": "writer", "emailAddress": e} for e in EDITORS]
    return perms


def main():
    creds = Credentials.from_authorized_user_file(TOK)
    if not creds.valid:
        creds.refresh(Request())
    dr = build("drive", "v3", credentials=creds)
    ids = file_ids()
    bodies = perm_body()
    print("mode=%s / targets=%d files / perms/file=%d" % (MODE, len(ids), len(bodies)))
    ok = 0
    fail = 0
    for name, fid in ids.items():
        for body in bodies:
            for attempt in range(5):
                try:
                    dr.permissions().create(
                        fileId=fid, body=body, sendNotificationEmail=False,
                        supportsAllDrives=True, fields="id",
                    ).execute()
                    ok += 1
                    break
                except HttpError as e:
                    if "429" in str(e) or "rateLimit" in str(e):
                        time.sleep(10)
                        continue
                    print("  FAIL %s (%s): %s" % (name, fid, str(e)[:160]))
                    fail += 1
                    break
        time.sleep(0.2)
    print("DONE granted=%d fail=%d" % (ok, fail))


if __name__ == "__main__":
    main()
