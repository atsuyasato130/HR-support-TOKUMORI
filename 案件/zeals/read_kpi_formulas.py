"""KPIヒーロー各箱(旧アンカー列)の実際の数式をFORMULAレンダリングで取得する。
新しいアンカー列へ移設する前に、既存の数式を壊さず保存するため。読み取り専用。
"""
import json
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
OUT = os.path.expanduser("~/Claude AI/scratch_zeals/kpi_hero_formulas.json")

OLD_COLS = ["A", "H", "O", "V", "AC"]  # old c0 = 0,7,14,21,28 (0-indexed) -> A1表記


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def main():
    svc = get_service()
    ranges = []
    # 全体: label=row5(1-idx), value=row6, subtitle=row8
    for row in (5, 6, 8):
        for col in OLD_COLS:
            ranges.append(f"'01_サマリー'!{col}{row}")
    # 月別: label=row54, value=row55, subtitle=row57
    for row in (54, 55, 57):
        for col in OLD_COLS:
            ranges.append(f"'01_サマリー'!{col}{row}")

    resp = svc.spreadsheets().values().batchGet(
        spreadsheetId=SPREADSHEET_ID, ranges=ranges, valueRenderOption="FORMULA",
    ).execute()

    result = {}
    for r, vr in zip(ranges, resp["valueRanges"]):
        values = vr.get("values", [[""]])
        result[r] = values[0][0] if values and values[0] else ""

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    for k, v in result.items():
        print(f"{k}: {v!r}")


if __name__ == "__main__":
    main()
