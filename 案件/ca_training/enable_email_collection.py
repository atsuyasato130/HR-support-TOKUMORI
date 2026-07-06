#!/usr/bin/env python3
"""全フォーム(.forms_map.json)でメール収集(VERIFIED)を有効化する。

フォームを再作成すると収集設定が外れるため、再作成後に再実行する。
collect_results.py が回答とメールを照合できる前提を整える。
env FORMS=C7,A1 で対象を限定（既定は全フォーム）。
"""
import json
import os
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")


def main():
    c = Credentials.from_authorized_user_file(TOK)
    if not c.valid:
        c.refresh(Request())
    forms = build("forms", "v1", credentials=c)
    fmap = json.load(open(os.path.join(BASE, ".forms_map.json"), encoding="utf-8"))
    only = os.environ.get("FORMS")
    mids = only.split(",") if only else list(fmap.keys())
    ok = fail = 0
    for mid in mids:
        fid = fmap.get(mid)
        if not fid:
            continue
        try:
            forms.forms().batchUpdate(formId=fid, body={"requests": [
                {"updateSettings": {"settings": {"emailCollectionType": "VERIFIED"},
                                    "updateMask": "emailCollectionType"}}]}).execute()
            ok += 1
        except Exception as e:
            print("FAIL", mid, str(e)[:120])
            fail += 1
    print("メール収集ON(VERIFIED): 成功%d / 失敗%d / 対象%d" % (ok, fail, len(mids)))


if __name__ == "__main__":
    main()
