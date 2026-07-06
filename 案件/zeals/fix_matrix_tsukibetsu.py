"""01_月別サマリーの媒体×職種マトリクス(行39-52)を正しいテンプレートロジックで再構築する。
コピー&行削除の結果、セレクタ参照と職種フィルタ参照が両方#REF!→$I$37に誤って
一括置換されてしまっていたため、正しい形へ作り直す。
"""
import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CONFIG_DIR = os.path.expanduser("~/Claude AI/tokumori/agents/hr_support/config")
TOKEN = os.path.join(CONFIG_DIR, "token_sheets.json")
SPREADSHEET_ID = "1I23o6blrxkXiJ_aK3CEtMHn-q7b2LgNe8U3wpzpET8U"
SHEET_NAME = "01_月別サマリー"

M = "'02_マスター'"
D = "'04_日次入力'"
START, END = "$AE$2", "$AF$2"
SELECTOR = "$I$37"
HEADER_ROW = 38
DATA_FIRST_ROW = 39
DATA_LAST_ROW = 50  # 39,40 実媒体 + 41-50 空きスロット(12スロット)
TOTAL_ROW = 52
NSH = 7  # 職種スロット数(B..H)

# (COUNTIFS列, SUMIFS列) : ListUpのみmasterなし
STAGE_COLS = [
    (None, "E"),   # ListUp
    ("L", "F"),    # 送付
    ("M", "G"),    # 返信
    ("O", "H"),    # 面談
    ("P", "I"),    # 採用
]


def col_a1(idx0):
    n = idx0 + 1
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def get_service():
    creds = Credentials.from_authorized_user_file(TOKEN)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("sheets", "v4", credentials=creds)


def cnt_expr(si, mref=None, sref=None):
    mcol, dcol = STAGE_COLS[si]
    mc = ""
    dc = ""
    if mref is not None:
        mc += f",{M}!$A:$A,{mref}"
        dc += f",{D}!$B:$B,{mref}"
    if sref is not None:
        mc += f",{M}!$G:$G,{sref}"
        dc += f",{D}!$C:$C,{sref}"
    daily = f'SUMIFS({D}!${dcol}:${dcol},{D}!$A:$A,">="&{START},{D}!$A:$A,"<="&{END}{dc})'
    if mcol is None:
        return f"({daily})"
    master = f'COUNTIFS({M}!${mcol}:${mcol},">="&{START},{M}!${mcol}:${mcol},"<="&{END}{mc})'
    return f"({master}+{daily})"


def choose_expr(mref=None, sref=None):
    exprs = [cnt_expr(si, mref=mref, sref=sref) for si in range(5)]
    inner = ",".join(exprs)
    return f'CHOOSE(MATCH({SELECTOR},{{"ListUp";"送付";"返信";"面談";"採用"}},0),{inner})'


def main():
    svc = get_service()
    updates = []

    # データ行(媒体×職種セル) B..H(NSH=7列) + I列(行計)
    for rr in range(DATA_FIRST_ROW, DATA_LAST_ROW + 1):
        mref = f"$A{rr}"
        for j in range(NSH):
            col = col_a1(1 + j)  # B..H
            sref = f"{col}${HEADER_ROW}"
            formula = f'=IF(OR({mref}="",{sref}=""),"",{choose_expr(mref=mref, sref=sref)})'
            updates.append({"range": f"'{SHEET_NAME}'!{col}{rr}", "values": [[formula]]})
        # I列 = 行計(媒体のみ絞り込み、職種フィルタなし)
        formula_tot = f'=IF({mref}="","",{choose_expr(mref=mref)})'
        updates.append({"range": f"'{SHEET_NAME}'!I{rr}", "values": [[formula_tot]]})

    # 計行(TOTAL_ROW): 各職種列(B..H)は媒体フィルタなし、I列は完全合計
    for j in range(NSH):
        col = col_a1(1 + j)
        sref = f"{col}${HEADER_ROW}"
        formula = f"={choose_expr(sref=sref)}"
        updates.append({"range": f"'{SHEET_NAME}'!{col}{TOTAL_ROW}", "values": [[formula]]})
    updates.append({"range": f"'{SHEET_NAME}'!I{TOTAL_ROW}", "values": [[f"={choose_expr()}"]]})

    print(f"更新セル数: {len(updates)}")
    for i in range(0, len(updates), 100):
        chunk = updates[i:i + 100]
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"valueInputOption": "USER_ENTERED", "data": chunk},
        ).execute()
    print("完了")


if __name__ == "__main__":
    main()
