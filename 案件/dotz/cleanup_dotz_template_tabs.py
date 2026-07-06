#!/usr/bin/env python3
"""DOTZ採用管理シートのタブ整理: README統合→2タブ削除、重複4タブを非表示化。
正本: ~/.claude/plans/curious-orbiting-tide.md (DOTZ 雛形タブの整理・重複統合)
"""
import os
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato130/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
DST_SS = "1ZDEYNXQyx-PumO61APfYkEcwZyA9Nnrzn6bjN9Ev9ag"

DELETE_TABS = ["プルダウン整理（DOTZ）", "エントリーフォーム一覧（DOTZ）"]
HIDE_TABS = ["20_統合ダッシュボード", "02_選考設計・社内体制", "03_採用目標・月別ファネル", "04_エントリー目標管理"]

README_APPEND = [
    [],
    ["", "■ DOTZ固有の外部リンク・参考資料"],
    ["", "エントリー用Googleフォーム", "フォームURL", "反映先（本番シート）"],
    ["", "格納先フォルダ", "https://drive.google.com/drive/folders/1-BZOvUYGyot20GcvovC8wDERew9t4IA-?usp=sharing", ""],
    ["", "エージェント", "https://forms.gle/SmhGRKq6AiZh4qKUA",
     "https://docs.google.com/spreadsheets/d/1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA/edit?gid=1298747705"],
    ["", "スカウト（B層）", "https://forms.gle/THahHbdUcaGxyMc8A",
     "https://docs.google.com/spreadsheets/d/1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA/edit?gid=1354372652"],
    ["", "スカウト（A層）", "https://forms.gle/RXTFTtiKagxLoXSS7",
     "https://docs.google.com/spreadsheets/d/1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA/edit?gid=1354372652"],
    ["", "スカウト（S層）", "https://forms.gle/5CHLqZDEnGh8BzSa6",
     "https://docs.google.com/spreadsheets/d/1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA/edit?gid=1493946497"],
    [],
    ["", "本番シートのステータスコード対照表（a〜γ・早期選考1〜25）は、移行元(003_000_03採用進捗管理)の解読専用データのため"
     "ここには転記していません。必要な場合は本番シートの「プルダウン整理」タブを参照してください。"],
    ["", "▸ 本番シート プルダウン整理",
     "https://docs.google.com/spreadsheets/d/1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA/edit?gid=2014251138"],
]


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)

    meta = sv.spreadsheets().get(spreadsheetId=DST_SS, fields="sheets.properties").execute()
    by_title = {sh["properties"]["title"]: sh["properties"] for sh in meta["sheets"]}

    readme = by_title["00_README"]
    last_row = sv.spreadsheets().values().get(
        spreadsheetId=DST_SS, range="'00_README'!A1:A2000"
    ).execute().get("values", [])
    start = len(last_row) + 2
    sv.spreadsheets().values().update(
        spreadsheetId=DST_SS, range="'00_README'!A%d" % start,
        valueInputOption="USER_ENTERED", body={"values": README_APPEND},
    ).execute()
    print("README updated, appended at row", start)

    requests = []
    for title in HIDE_TABS:
        if title in by_title:
            requests.append({
                "updateSheetProperties": {
                    "properties": {"sheetId": by_title[title]["sheetId"], "hidden": True},
                    "fields": "hidden",
                }
            })
        else:
            print("WARN: hide target not found:", title)
    for title in DELETE_TABS:
        if title in by_title:
            requests.append({"deleteSheet": {"sheetId": by_title[title]["sheetId"]}})
        else:
            print("WARN: delete target not found:", title)

    if requests:
        sv.spreadsheets().batchUpdate(spreadsheetId=DST_SS, body={"requests": requests}).execute()
        print("applied", len(requests), "requests (hide+delete)")

    print("DONE")


if __name__ == "__main__":
    main()
