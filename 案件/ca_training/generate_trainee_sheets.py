#!/usr/bin/env python3
"""管理SSの受講者名簿から、新卒“個人用”研修シートを自動生成する（GAS不要・私のトークンで実行）。

各行（氏名＋メールあり・URL未設定）について:
  1) 研修ハブ(.ca_sheet_id)を丸ごと複製（中身ごとコピー）
  2) 命名規則「【新卒研修】{氏名}（{配属}）」で誰のシートか一目で分かるように
  3) 権限を “管理者＋本人のみ” に設定（本人＝編集権限／ドメイン共有なし＝非公開）
  4) 生成URLを名簿のF列へ書き戻し、ステータスが空なら「受講中」に

env:
  MANAGERS  カンマ区切り（既定: atsuya_sato@tokumori.co.jp,shun_watanabe@tokumori.co.jp）
  SEND_NOTIFY=1 で本人にGoogle通知メールを送る（既定OFF）
  DRY=1 で生成せず対象だけ表示
"""
import os
import time
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
MANAGERS = [e.strip() for e in os.environ.get(
    "MANAGERS", "atsuya_sato@tokumori.co.jp,shun_watanabe@tokumori.co.jp").split(",") if e.strip()]
NOTIFY = bool(os.environ.get("SEND_NOTIFY"))
DRY = bool(os.environ.get("DRY"))


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def grant(dr, fid, email, role, notify):
    for attempt in range(5):
        try:
            dr.permissions().create(
                fileId=fid, body={"type": "user", "role": role, "emailAddress": email},
                sendNotificationEmail=notify, supportsAllDrives=True, fields="id").execute()
            return True
        except HttpError as e:
            if "429" in str(e) or "rateLimit" in str(e):
                time.sleep(8)
                continue
            print("    grant FAIL %s: %s" % (email, str(e)[:120]))
            return False
    return False


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)
    dr = build("drive", "v3", credentials=c)
    hub = open(os.path.join(BASE, ".ca_sheet_id")).read().strip()
    admid = open(os.path.join(BASE, ".admin_sheet_id")).read().strip()

    rows = sv.spreadsheets().values().get(
        spreadsheetId=admid, range="受講者名簿!A2:G").execute().get("values", [])
    targets = []
    for i, r in enumerate(rows):
        name = (r[1] if len(r) > 1 else "").strip()
        mail = (r[2] if len(r) > 2 else "").strip()
        team = (r[3] if len(r) > 3 else "").strip()
        url = (r[5] if len(r) > 5 else "").strip()
        if name and mail and not url:
            targets.append((i + 2, name, mail, team))   # 行番号(1始まり), 氏名, メール, 配属

    print("対象:", len(targets), "件 / managers=%s / notify=%s" % (MANAGERS, NOTIFY))
    for rownum, name, mail, team in targets:
        title = "【新卒研修】%s%s" % (name, ("（%s）" % team if team else ""))
        print(" -", title, "<", mail, ">")
        if DRY:
            continue
        copy = dr.files().copy(fileId=hub, body={"title": title, "name": title},
                               supportsAllDrives=True, fields="id").execute()
        nid = copy["id"]
        grant(dr, nid, mail, "writer", NOTIFY)        # 本人＝編集
        for mgr in MANAGERS:
            grant(dr, nid, mgr, "writer", False)       # 管理者＝編集
        nurl = "https://docs.google.com/spreadsheets/d/%s/edit" % nid
        body = {"values": [[nurl]]}
        sv.spreadsheets().values().update(
            spreadsheetId=admid, range="受講者名簿!F%d" % rownum,
            valueInputOption="USER_ENTERED", body=body).execute()
        # ステータスが空なら「受講中」
        st = (rows[rownum - 2][6] if len(rows[rownum - 2]) > 6 else "").strip()
        if not st:
            sv.spreadsheets().values().update(
                spreadsheetId=admid, range="受講者名簿!G%d" % rownum,
                valueInputOption="USER_ENTERED", body={"values": [["受講中"]]}).execute()
        time.sleep(0.4)

    print("DONE generated=%d (DRY=%s)" % (0 if DRY else len(targets), DRY))


if __name__ == "__main__":
    main()
