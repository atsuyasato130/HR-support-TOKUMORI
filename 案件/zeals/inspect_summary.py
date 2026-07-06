"""01_サマリーのシートID・マージ範囲・KPIヒーロー行を特定する。読み取り専用。"""
import json
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def main():
    svc = get_service()
    meta = svc.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields="sheets(properties(sheetId,title,gridProperties),merges)",
    ).execute()

    for sheet in meta["sheets"]:
        props = sheet["properties"]
        if props["title"] == "01_サマリー":
            print("sheetId:", props["sheetId"])
            print("gridProperties:", props.get("gridProperties"))
            merges = sheet.get("merges", [])
            print(f"merge数: {len(merges)}")
            for m in merges:
                print(m)


if __name__ == "__main__":
    main()
