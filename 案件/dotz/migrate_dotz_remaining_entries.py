#!/usr/bin/env python3
"""DOTZ本番「エントリーマスター」(196件)のうち、既にATS移行済みの69件を除いた
残り約127件を新テンプレの10_候補者マスタへ追加する。
正本: ~/.claude/plans/curious-orbiting-tide.md (未移行タブ・全エントリーの追加移管)
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
MASTER_SHEET = "10_候補者マスタ"
ARCHIVE_SHEET = "99_DOTZ選考詳細アーカイブ"

MASTER_COLS = [
    "candidate_id", "区分", "職種", "チャネル",
    "氏名", "性別", "生年月日", "連絡先", "電話番号", "大学", "学部", "学科", "高校名",
    "応募日", "現ステージ", "ステータス",
    "見送り辞退理由", "競合先", "採用担当RC", "ネクストアクション", "NA期限",
    "次回面接日時", "次回面接URL", "次回面接官", "内定日", "承諾日", "入社日",
    "履歴書リンク", "履歴書回収日", "職務経歴書リンク", "職務経歴書回収日", "サンクス送信日", "評価メモ",
    "面接回数", "直近面接日", "直近面接官", "直近フェーズ", "総合評価", "最新評価",
]


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)

    entry_rows = sv.spreadsheets().values().get(
        spreadsheetId=SRC_SS, range="'エントリーマスター'!A2:P2000"
    ).execute().get("values", [])
    entry_rows = [r for r in entry_rows if r and len(r) > 10 and str(r[10]).strip()]
    print("entryMaster rows:", len(entry_rows))

    def norm_key(name, univ):
        return "".join(str(name).split()).lower() + "|" + "".join(str(univ).split()).lower()

    existing = sv.spreadsheets().values().get(
        spreadsheetId=DST_SS, range="'%s'!A2:J1000" % MASTER_SHEET
    ).execute().get("values", [])
    existing_keys = set()
    existing_emails = set()
    max_id = 0
    for r in existing:
        r = list(r) + [""] * (10 - len(r))
        if r[7].strip():
            existing_emails.add(r[7].strip().lower())
        if r[4].strip() and r[9].strip():
            existing_keys.add(norm_key(r[4], r[9]))  # 氏名|大学
        if r[0].startswith("C-2026-"):
            try:
                max_id = max(max_id, int(r[0].split("-")[-1]))
            except ValueError:
                pass
    print("existing candidates:", len(existing), "max_id:", max_id, "keys:", len(existing_keys))

    archive_header = sv.spreadsheets().values().get(
        spreadsheetId=DST_SS, range="'%s'!A1:ZZ1" % ARCHIVE_SHEET
    ).execute().get("values", [[]])[0]

    new_master, new_archive = [], []
    for r in entry_rows:
        r = list(r) + [""] * (16 - len(r))
        email = r[10].strip().lower()
        name = (r[3] + r[4]).strip()
        univ = r[8].strip()
        key = norm_key(r[3] + " " + r[4], univ) if name and univ else None
        if email and email in existing_emails:
            continue
        if key and key in existing_keys:
            continue
        if email:
            existing_emails.add(email)
        if key:
            existing_keys.add(key)
        max_id += 1
        cid = "C-2026-%04d" % max_id
        m = {k: "" for k in MASTER_COLS}
        m["candidate_id"] = cid
        m["区分"] = "新卒"
        m["チャネル"] = r[1] or r[2]
        m["氏名"] = (r[3] + " " + r[4]).strip()
        m["連絡先"] = r[10]
        m["電話番号"] = r[11]
        m["大学"] = r[8]
        m["学部"] = r[9]
        m["応募日"] = r[0]
        m["現ステージ"] = "応募"
        m["ステータス"] = "進行中"
        new_master.append([m[k] for k in MASTER_COLS])

        arch_row = [""] * len(archive_header)
        arch_row[0] = cid
        arch_row[archive_header.index("タイムスタンプ")] = r[0] if "タイムスタンプ" in archive_header else ""
        new_archive.append(arch_row)

    print("new candidates to add:", len(new_master))

    if new_master:
        start = len(existing) + 2
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A%d" % (MASTER_SHEET, start),
            valueInputOption="USER_ENTERED", body={"values": new_master},
        ).execute()

        arch_existing = sv.spreadsheets().values().get(
            spreadsheetId=DST_SS, range="'%s'!A2:A2000" % ARCHIVE_SHEET
        ).execute().get("values", [])
        astart = len(arch_existing) + 2
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A%d" % (ARCHIVE_SHEET, astart),
            valueInputOption="USER_ENTERED", body={"values": new_archive},
        ).execute()

    print("DONE")


if __name__ == "__main__":
    main()
