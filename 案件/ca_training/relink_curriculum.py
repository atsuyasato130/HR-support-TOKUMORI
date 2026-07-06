#!/usr/bin/env python3
"""
カリキュラム一覧の「教材リンク(J)」「確認テスト(K)」を、.slide_map.json / .forms_map.json から復元する。
ハブ再構築でJ/K列がクリアされた後に実行する軽量スクリプト（valuesのbatchUpdate1回）。
"""
import json, os, warnings
warnings.filterwarnings("ignore")
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE="/Users/atsuyasato/Claude AI"
TOK="/Users/atsuyasato/Claude AI/tokumori/agents/hr_support/config/token_sheets.json"
SSID=open(os.path.join(BASE,".ca_sheet_id")).read().strip()
sm=json.load(open(os.path.join(BASE,".slide_map.json"))) if os.path.exists(os.path.join(BASE,".slide_map.json")) else {}
fm=json.load(open(os.path.join(BASE,".forms_map.json"))) if os.path.exists(os.path.join(BASE,".forms_map.json")) else {}

creds=Credentials.from_authorized_user_file(TOK)
if not creds.valid: creds.refresh(Request())
sv=build("sheets","v4",credentials=creds); forms=build("forms","v1",credentials=creds)
vals=sv.spreadsheets().values().get(spreadsheetId=SSID,range="カリキュラム一覧!B6:B100").execute().get("values",[])
rowof={r[0]:6+i for i,r in enumerate(vals) if r}
data=[]
for mid,pid in sm.items():
    if mid in rowof:
        url="https://docs.google.com/presentation/d/%s/edit"%pid
        data.append({"range":"カリキュラム一覧!J%d"%rowof[mid],"values":[['=HYPERLINK("%s","スライドを開く")'%url]]})
for mid,fid in fm.items():
    if mid in rowof:
        try: uri=forms.forms().get(formId=fid).execute().get("responderUri")
        except Exception: uri="https://docs.google.com/forms/d/%s/viewform"%fid
        data.append({"range":"カリキュラム一覧!K%d"%rowof[mid],"values":[['=HYPERLINK("%s","テストを受ける")'%uri]]})
sv.spreadsheets().values().batchUpdate(spreadsheetId=SSID,body={"valueInputOption":"USER_ENTERED","data":data}).execute()
print("relinked cells:",len(data),"| slides:",len(sm),"forms:",len(fm))
