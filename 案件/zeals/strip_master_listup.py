"""01_サマリーの全数式から「COUNTIFS('02_マスター'!$K:$K,...)+」の部分だけを
括弧の対応を数えて正確に除去し、SUMIFS('04_日次入力'!$E:$E,...) だけを残す。
ListUp集計を「日次入力のみ」に変更するための一括置換。他のセルには一切触れない。
"""
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SHEET_NAME = "01_サマリー"
MARKER = "COUNTIFS('02_マスター'!$K:$K,"


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def strip_master_countifs(formula):
    """formula内の最初のMARKER出現について、対応する閉じ括弧までを特定し、
    直後が '+SUMIFS' ならその COUNTIFS(...)+  をまるごと削除する。
    複数回出現する場合は繰り返し処理する(通常は1回のみのはず)。
    """
    changed = False
    while True:
        idx = formula.find(MARKER)
        if idx == -1:
            break
        open_idx = formula.find("(", idx)
        depth = 0
        i = open_idx
        while i < len(formula):
            if formula[i] == "(":
                depth += 1
            elif formula[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        close_idx = i
        rest = formula[close_idx + 1:]
        if not rest.startswith("+SUMIFS"):
            # 想定外パターン: 安全のためここでは何もせず終了
            break
        formula = formula[:idx] + formula[close_idx + 2:]
        changed = True
    return formula, changed


def main():
    svc = get_service()
    meta = svc.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[f"'{SHEET_NAME}'!A1:AJ180"],
        includeGridData=True,
        fields="sheets(data(rowData(values(userEnteredValue.formulaValue))))",
    ).execute()
    rows = meta["sheets"][0]["data"][0]["rowData"]

    updates = []
    unexpected = []
    for ridx, row in enumerate(rows):
        for cidx, cell in enumerate(row.get("values", [])):
            f = cell.get("userEnteredValue", {}).get("formulaValue")
            if f and MARKER in f:
                new_f, changed = strip_master_countifs(f)
                if changed:
                    col_letter = colnum_to_letter(cidx)
                    updates.append({"range": f"'{SHEET_NAME}'!{col_letter}{ridx+1}",
                                     "values": [[new_f]]})
                else:
                    unexpected.append((ridx + 1, cidx + 1, f))

    print(f"置換対象: {len(updates)}件 / 想定外パターン: {len(unexpected)}件")
    for u in unexpected[:10]:
        print("要確認:", u)

    if unexpected:
        print("想定外パターンがあるため書き込みを中止します。内容を確認してください。")
        return

    # 100件ずつ分割してbatchUpdate
    for i in range(0, len(updates), 100):
        chunk = updates[i:i + 100]
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"valueInputOption": "USER_ENTERED", "data": chunk},
        ).execute()
        print(f"書き込み完了: {i}〜{i+len(chunk)}")


def colnum_to_letter(idx0):
    n = idx0 + 1
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


if __name__ == "__main__":
    main()
