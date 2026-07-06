#!/usr/bin/env python3
"""本番SSの静的参照タブ(分類表/エージェント連携チェックリスト/エントリーフォーム/プルダウン整理/リマインド設定)を
新テンプレへ値のみコピーする。
"""
import os
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato130/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
SRC_SS = "1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA"
DST_SS = "1ZDEYNXQyx-PumO61APfYkEcwZyA9Nnrzn6bjN9Ev9ag"

TABS = [
    ("分類表", "分類表（大学群6区分・DOTZ）"),
    ("エージェント連携チェックリスト", "エージェント連携チェックリスト（DOTZ）"),
    ("エントリーフォーム", "エントリーフォーム一覧（DOTZ）"),
    ("プルダウン整理", "プルダウン整理（DOTZ）"),
    ("リマインド設定", "リマインド設定（DOTZ・参考保存）"),
]


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def ensure_sheet(sv, title):
    meta = sv.spreadsheets().get(spreadsheetId=DST_SS, fields="sheets.properties").execute()
    for sh in meta["sheets"]:
        if sh["properties"]["title"] == title:
            return sh["properties"]["sheetId"]
    resp = sv.spreadsheets().batchUpdate(
        spreadsheetId=DST_SS,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)
    for src_name, dst_name in TABS:
        data = sv.spreadsheets().values().get(
            spreadsheetId=SRC_SS, range="'%s'!A1:Z2000" % src_name
        ).execute().get("values", [])
        if not data:
            print(src_name, "-> empty, skip")
            continue
        ensure_sheet(sv, dst_name)
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A1" % dst_name,
            valueInputOption="USER_ENTERED", body={"values": data},
        ).execute()
        print(src_name, "->", dst_name, "rows:", len(data))
    print("DONE")


if __name__ == "__main__":
    main()
