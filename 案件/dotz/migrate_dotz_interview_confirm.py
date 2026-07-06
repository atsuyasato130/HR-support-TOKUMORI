#!/usr/bin/env python3
"""本番「面接スケジュール」(確定日時・Zoom URL・ステータス)を、新テンプレ11_面接スケジュールへ反映する。
003_000_03由来の生データより正確なため、一致する行は上書き・無ければ追加。
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
IV_SHEET = "11_面接スケジュール"
ARCHIVE_SHEET = "99_DOTZ選考詳細アーカイブ"

IV_COLS = [
    "interview_id", "candidate_id", "候補者名", "区分", "職種", "ステージ",
    "予定日時", "面接URL", "面接官", "形式", "ステータス", "結果", "評点", "評価メモ",
    "総合点", "評価明細", "判定",
]
STAGE_MAP = {"1次面接": "一次面接", "2次面接": "二次面接"}
STATUS_MAP = {"予定": "予定", "実施済": "実施済", "キャンセル": "キャンセル"}


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)

    arch = sv.spreadsheets().values().get(
        spreadsheetId=DST_SS, range="'%s'!A2:B2000" % ARCHIVE_SHEET
    ).execute().get("values", [])
    old_to_new = {r[1].strip(): r[0].strip() for r in arch if len(r) > 1 and r[1].strip()}
    print("old->new id map size:", len(old_to_new))

    src = sv.spreadsheets().values().get(
        spreadsheetId=SRC_SS, range="'面接スケジュール'!A2:H200"
    ).execute().get("values", [])
    print("production 面接スケジュール rows:", len(src))

    iv = sv.spreadsheets().values().get(
        spreadsheetId=DST_SS, range="'%s'!A1:Q2000" % IV_SHEET
    ).execute().get("values", [])
    header, iv_rows = iv[0], iv[1:]
    h = {name: i for i, name in enumerate(header)}
    max_iv = 0
    for r in iv_rows:
        if r and str(r[0]).startswith("IV-2026-"):
            try:
                max_iv = max(max_iv, int(r[0].split("-")[-1]))
            except ValueError:
                pass

    updated, appended, skipped = 0, 0, 0
    updates = {}  # row_index (0-based in iv_rows) -> new row values
    new_rows = []
    for r in src:
        if not r or not r[0].strip():
            continue
        r = list(r) + [""] * (8 - len(r))
        old_id, stage_raw = (r[0].split("|", 1) + [""])[:2]
        old_id = old_id.strip()
        stage = STAGE_MAP.get(stage_raw.strip(), stage_raw.strip())
        cid = old_to_new.get(old_id)
        if not cid:
            skipped += 1
            continue
        match_idx = None
        for i, row in enumerate(iv_rows):
            row_ext = list(row) + [""] * (len(header) - len(row))
            if row_ext[h["candidate_id"]].strip() == cid and row_ext[h["ステージ"]].strip() == stage:
                match_idx = i
                break
        if match_idx is not None:
            row_ext = list(iv_rows[match_idx]) + [""] * (len(header) - len(iv_rows[match_idx]))
            row_ext[h["予定日時"]] = r[4]
            row_ext[h["面接URL"]] = r[5]
            row_ext[h["面接官"]] = r[6] or row_ext[h["面接官"]]
            row_ext[h["ステータス"]] = STATUS_MAP.get(r[7].strip(), r[7].strip())
            updates[match_idx] = row_ext
            updated += 1
        else:
            max_iv += 1
            new = {k: "" for k in IV_COLS}
            new["interview_id"] = "IV-2026-%04d" % max_iv
            new["candidate_id"] = cid
            new["候補者名"] = r[2]
            new["区分"] = "新卒"
            new["ステージ"] = stage
            new["予定日時"] = r[4]
            new["面接URL"] = r[5]
            new["面接官"] = r[6]
            new["ステータス"] = STATUS_MAP.get(r[7].strip(), r[7].strip())
            new_rows.append([new[k] for k in IV_COLS])
            appended += 1

    print("updated:", updated, "appended:", appended, "skipped(no id map):", skipped)

    for idx, row_ext in updates.items():
        sheet_row = idx + 2
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A%d" % (IV_SHEET, sheet_row),
            valueInputOption="USER_ENTERED", body={"values": [row_ext]},
        ).execute()

    if new_rows:
        start = len(iv_rows) + 2
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A%d" % (IV_SHEET, start),
            valueInputOption="USER_ENTERED", body={"values": new_rows},
        ).execute()

    print("DONE")


if __name__ == "__main__":
    main()
