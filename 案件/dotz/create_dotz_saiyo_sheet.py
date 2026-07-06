#!/usr/bin/env python3
"""クリーン白紙雛形（採用管理シート_雛形）をコピーして「DOTZ 採用管理シート」を新規作成する。

参照: ~/.claude/plans/curious-orbiting-tide.md Stage1-1
"""
import os
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato130/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
TEMPLATE_ID = "1QsZ0h8hqsLrJQiIPtockzmyEmqpQLczVb2nIhy8G8KI"
NEW_TITLE = "DOTZ 採用管理シート"


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def main():
    c = creds()
    dr = build("drive", "v3", credentials=c)
    copy = dr.files().copy(
        fileId=TEMPLATE_ID,
        body={"name": NEW_TITLE},
        fields="id,name",
    ).execute()
    nid = copy["id"]
    print("created:", copy["name"], nid)
    print("url: https://docs.google.com/spreadsheets/d/%s/edit" % nid)


if __name__ == "__main__":
    main()
