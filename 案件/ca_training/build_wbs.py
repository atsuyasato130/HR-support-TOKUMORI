#!/usr/bin/env python3
"""WBS（作業分解・進捗管理）タブを 雛形＋各メンバーのコピー に作成/更新する。

build_training_hub_v2 の SM / reqs_for / build_wbs を再利用し、**WBSタブのみ**を書き換える（他タブは不変）。
- 対象 = 雛形(.ca_sheet_id) ＋ 管理SSの受講者名簿(F列URL)から各メンバーのコピーSS。
- env TARGET=hub|members|all（既定all） / ONLY=<ssid,...> で対象限定。
雛形に対しては「WBSタブ追加のみ」で全体リビルドはしない。
"""
import os
import re
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build as gbuild

import build_training_hub_v2 as bh

BASE = "/Users/atsuyasato/Claude AI"
TOK = bh.TOK


def creds():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    return c


def ensure_wbs_tab(sv, ssid):
    m = sv.spreadsheets().get(spreadsheetId=ssid,
        fields="sheets(properties(sheetId,title,index))").execute()
    tabs = {s["properties"]["title"]: s["properties"]["sheetId"] for s in m["sheets"]}
    if "WBS" not in tabs:
        idx = None
        for s in m["sheets"]:
            if s["properties"]["title"] == "進捗管理":
                idx = s["properties"]["index"] + 1
        props = {"title": "WBS"}
        if idx is not None:
            props["index"] = idx
        sv.spreadsheets().batchUpdate(spreadsheetId=ssid,
            body={"requests": [{"addSheet": {"properties": props}}]}).execute()
        m = sv.spreadsheets().get(spreadsheetId=ssid,
            fields="sheets(properties(sheetId,title))").execute()
        tabs = {s["properties"]["title"]: s["properties"]["sheetId"] for s in m["sheets"]}
    return tabs


def member_ssids(sv):
    admid = open(os.path.join(BASE, ".admin_sheet_id")).read().strip()
    ros = sv.spreadsheets().values().get(
        spreadsheetId=admid, range="受講者名簿!A2:G").execute().get("values", [])
    out = []
    for r in ros:
        nm = r[1] if len(r) > 1 else ""
        url = r[5] if len(r) > 5 else ""
        mm = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url or "")
        if mm:
            out.append((nm or "(無名)", mm.group(1)))
    return out


def build_one(sv, ssid, label):
    tabs = ensure_wbs_tab(sv, ssid)
    if "研修ホーム" not in tabs:
        print("  skip(研修ホームなし):", label, ssid)
        return False
    wbs_id = tabs["WBS"]
    # 既存の条件付き書式を削除（reqs_for はCFを消さないため、再描画前に全消去）
    meta = sv.spreadsheets().get(spreadsheetId=ssid,
        fields="sheets(properties(sheetId),conditionalFormats)").execute()
    ncf = 0
    for s in meta["sheets"]:
        if s["properties"]["sheetId"] == wbs_id:
            ncf = len(s.get("conditionalFormats", []))
    dels = [{"deleteConditionalFormatRule": {"sheetId": wbs_id, "index": 0}} for _ in range(ncf)]
    sm = bh.SM(wbs_id)
    bh.build_wbs(sm, {"研修ホーム": tabs["研修ホーム"]})
    sv.spreadsheets().batchUpdate(spreadsheetId=ssid,
        body={"requests": dels + bh.reqs_for(sm)}).execute()
    print("  WBS作成:", label, ssid, "(旧CF削除 %d)" % ncf)
    return True


def main():
    sv = gbuild("sheets", "v4", credentials=creds())
    target = os.environ.get("TARGET", "all")
    only = os.environ.get("ONLY")
    todo = []
    if only:
        for sid in only.split(","):
            todo.append(("ONLY", sid.strip()))
    else:
        if target in ("hub", "all"):
            todo.append(("雛形", bh.SSID))
        if target in ("members", "all"):
            todo += member_ssids(sv)
    print("対象:", len(todo))
    ok = 0
    for label, sid in todo:
        try:
            if build_one(sv, sid, label):
                ok += 1
        except Exception as e:
            print("  FAIL", label, sid, str(e)[:160])
    print("DONE WBS built:", ok, "/", len(todo))


if __name__ == "__main__":
    main()
