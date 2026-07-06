#!/usr/bin/env python3
"""本番DOTZシート(003_000_03採用進捗管理)の136列ヘッダー(行7-10)を機械的に整列して出力する。
移行スクリプト作成前の調査用（書き込みは一切行わない）。
"""
import os
import string
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato130/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")
SS_ID = "1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA"
SHEET = "003_000_03採用進捗管理"
MAX_COLS = 136


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def col_letter(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = string.ascii_uppercase[r] + s
    return s


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)
    rng = "'%s'!A7:%s10" % (SHEET, col_letter(MAX_COLS))
    resp = sv.spreadsheets().values().get(spreadsheetId=SS_ID, range=rng).execute()
    rows = resp.get("values", [])
    while len(rows) < 4:
        rows.append([])
    r7, r8, r9, r10 = rows[0], rows[1], rows[2], rows[3]

    def get(row, i):
        return row[i] if i < len(row) else ""

    print("col\tbanner(r7)\tnote(r8)\tsub(r9)\tfield(r10)")
    for i in range(MAX_COLS):
        letter = col_letter(i + 1)
        b, n, s, f = get(r7, i), get(r8, i), get(r9, i), get(r10, i)
        print("%s\t%s\t%s\t%s\t%s" % (letter, b, n, s, f))


if __name__ == "__main__":
    main()
