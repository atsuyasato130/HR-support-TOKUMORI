#!/usr/bin/env python3
"""DOTZ本番SS(003_000_03採用進捗管理・69名)を新テンプレ「DOTZ 採用管理シート」へ移管する。
正本=~/.claude/plans/curious-orbiting-tide.md Stage1-3。

構成:
  - 10_候補者マスタ / 11_面接スケジュール へ標準スキーマで書き込み(ダッシュボード/レポートが使う部分)
  - 新設タブ「99_DOTZ選考詳細アーカイブ」へ、旧学生ID対照＋全136列の生データをそのまま保存(全移管・素通し)
"""
import os
import re
import string
import warnings

warnings.filterwarnings("ignore")
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE = "/Users/atsuyasato130/Claude AI"
TOK = os.path.join(BASE, "tokumori/agents/hr_support/config/token_sheets.json")

SRC_SS = "1TTvSxomKhrZ5OghBcQ-x-iGGsM2lwnkejFd6g1fzefA"
SRC_SHEET = "003_000_03採用進捗管理"
SRC_MAX_COL = 136
SRC_DATA_START_ROW = 11

DST_SS = "1ZDEYNXQyx-PumO61APfYkEcwZyA9Nnrzn6bjN9Ev9ag"
MASTER_SHEET = "10_候補者マスタ"
IV_SHEET = "11_面接スケジュール"
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
IV_COLS = [
    "interview_id", "candidate_id", "候補者名", "区分", "職種", "ステージ",
    "予定日時", "面接URL", "面接官", "形式", "ステータス", "結果", "評点", "評価メモ",
    "総合点", "評価明細", "判定",
]

# ステータスコード(C列)の接頭辞 -> (フェーズ名, 結果種別)
STATUS_CODE_PHASE = {
    "説明選考会": "説明選考会",
    "1次面接": "一次面接",
    "カジュアル面談": "カジュアル面談",
    "2次面接": "二次面接",
    "1dayインターン": "1dayインターン",
    "最終面接": "最終面接",
}
RESULT_TO_STATUS = {
    "不合格": "見送り",
    "合格": "進行中",
    "調整中": "進行中",
    "調整済": "進行中",
    "調整済み": "進行中",
}

# フェーズブロック定義: (フェーズ名, 参加/確定日列, 面接官列, 総合評価列, MEMO列, 面接日程候補列)
PHASE_BLOCKS = [
    ("説明選考会", "AW", None, None, "BD", None),
    ("一次面接", "BH", "BJ", "BK", None, "BG"),
    ("カジュアル面談", "BW", "BY", None, "CA", None),
    ("1dayインターン", "CG", "CI", "CJ", None, "CF"),
    ("二次面接", "CU", "CW", "CX", None, None),
    ("最終面接", "DI", "DL", "DM", None, None),
]

SCORE_MAP = {"S": "S", "A": "A", "B": "B", "C": "C", "D": "D", "Ａ": "A", "Ｂ": "B", "Ｃ": "C", "Ｄ": "D", "Ｓ": "S"}


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


def col_index(letter):
    n = 0
    for ch in letter:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1  # 0-indexed


def fetch_header_map(sv):
    rng = "'%s'!A7:%s10" % (SRC_SHEET, col_letter(SRC_MAX_COL))
    resp = sv.spreadsheets().values().get(spreadsheetId=SRC_SS, range=rng).execute()
    rows = resp.get("values", [])
    while len(rows) < 4:
        rows.append([])
    r7, r10 = rows[0], rows[3]

    def get(row, i):
        return row[i] if i < len(row) else ""

    banners = {}
    fields = {}
    for i in range(SRC_MAX_COL):
        letter = col_letter(i + 1)
        banners[letter] = get(r7, i).strip()
        fields[letter] = get(r10, i).strip()
    return banners, fields


def fetch_data_rows(sv):
    rng = "'%s'!A%d:%s2000" % (SRC_SHEET, SRC_DATA_START_ROW, col_letter(SRC_MAX_COL))
    resp = sv.spreadsheets().values().get(spreadsheetId=SRC_SS, range=rng).execute()
    rows = resp.get("values", [])
    out = []
    for r in rows:
        # B列(タイムスタンプ)が実データの唯一の信頼できる目印(他列は数式で空文字を返す行が続くため)
        if not r or len(r) < 2 or not str(r[1]).strip():
            continue
        r = list(r) + [""] * (SRC_MAX_COL - len(r))
        out.append(r)
    return out


def cell(row, letter):
    v = row[col_index(letter)]
    return "" if str(v).startswith("#") else v  # 数式エラー(#REF!等)は空扱い


def is_checked(v):
    return str(v).strip().upper() == "TRUE"


def parse_status_code(code):
    m = re.match(r"^[a-zA-Z]\.(.+?)_(.+)$", code.strip())
    if not m:
        return None, None
    phase_raw, result_raw = m.group(1).strip(), m.group(2).strip()
    phase = STATUS_CODE_PHASE.get(phase_raw, phase_raw)
    status = RESULT_TO_STATUS.get(result_raw, "進行中")
    return phase, status


def norm_score(v):
    v = str(v or "").strip()
    return SCORE_MAP.get(v, v if v in ("S", "A", "B", "C", "D") else "")


def build_master_row(row, cid):
    m = {k: "" for k in MASTER_COLS}
    m["candidate_id"] = cid
    m["区分"] = "新卒"
    m["チャネル"] = cell(row, "H")
    sei, mei = cell(row, "I"), cell(row, "J")
    m["氏名"] = (sei + " " + mei).strip()
    m["連絡先"] = cell(row, "Q")
    m["電話番号"] = cell(row, "R")
    m["大学"] = cell(row, "M")
    m["学部"] = cell(row, "O")
    m["高校名"] = cell(row, "P")
    m["応募日"] = cell(row, "B")

    code = cell(row, "C")
    phase, status = parse_status_code(code)
    if phase:
        m["現ステージ"] = phase
        m["ステータス"] = status
    else:
        m["現ステージ"] = "応募"
        m["ステータス"] = "進行中"
    if is_checked(cell(row, "G")):
        m["ステータス"] = "辞退"
    eb = cell(row, "EB").strip()
    if eb and eb.upper() not in ("TRUE", "FALSE"):
        m["内定日"] = eb
        m["ステータス"] = "内定"
    if is_checked(cell(row, "DW")):
        m["ステータス"] = "承諾"
    return m


def build_interview_rows(row, cid, name):
    out = []
    for phase, date_col, who_col, score_col, memo_col, sched_col in PHASE_BLOCKS:
        date_v = cell(row, date_col).strip()
        sched_v = cell(row, sched_col).strip() if sched_col else ""
        if not date_v and not sched_v:
            continue
        iv = {k: "" for k in IV_COLS}
        iv["candidate_id"] = cid
        iv["候補者名"] = name
        iv["区分"] = "新卒"
        iv["ステージ"] = phase
        iv["予定日時"] = date_v or sched_v
        iv["面接官"] = cell(row, who_col) if who_col else ""
        iv["評点"] = norm_score(cell(row, score_col)) if score_col else ""
        iv["評価メモ"] = cell(row, memo_col) if memo_col else ""
        iv["ステータス"] = "実施済" if date_v else "予定"
        out.append(iv)
    return out


def build_archive_header(banners, fields):
    header = ["candidate_id", "旧学生ID"]
    seen = {}
    cols = []
    for i in range(SRC_MAX_COL):
        letter = col_letter(i + 1)
        f = fields[letter]
        if not f:
            continue
        b = banners[letter]
        label = ("%s_%s" % (b, f)) if b else f
        n = seen.get(label, 0)
        seen[label] = n + 1
        if n:
            label = "%s(%d)" % (label, n + 1)
        header.append(label)
        cols.append(letter)
    return header, cols


def ensure_sheet(sv, title):
    meta = sv.spreadsheets().get(spreadsheetId=DST_SS, fields="sheets.properties").execute()
    for sh in meta["sheets"]:
        if sh["properties"]["title"] == title:
            return sh["properties"]["sheetId"]
    resp = sv.spreadsheets().batchUpdate(
        spreadsheetId=DST_SS,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()
    return resp["replies"][0]["addSheet"]["properties"]["sheetId"]


def main():
    c = creds()
    sv = build("sheets", "v4", credentials=c)

    banners, fields = fetch_header_map(sv)
    data_rows = fetch_data_rows(sv)
    print("production data rows:", len(data_rows))

    master_out, iv_out, archive_out = [], [], []
    for i, row in enumerate(data_rows):
        cid = "C-2026-%04d" % (i + 1)
        m = build_master_row(row, cid)
        master_out.append([m[k] for k in MASTER_COLS])
        ivs = build_interview_rows(row, cid, m["氏名"])
        for j, iv in enumerate(ivs):
            iv["interview_id"] = "IV-2026-%04d" % (len(iv_out) + 1)
            iv_out.append([iv[k] for k in IV_COLS])

        arch_header, arch_cols = build_archive_header(banners, fields)
        arch_row = [cid, cell(row, "EF")] + [cell(row, lt) for lt in arch_cols]
        archive_out.append(arch_row)

    print("master rows:", len(master_out))
    print("interview rows:", len(iv_out))

    sv.spreadsheets().values().update(
        spreadsheetId=DST_SS, range="'%s'!A2" % MASTER_SHEET,
        valueInputOption="USER_ENTERED", body={"values": master_out},
    ).execute()
    if iv_out:
        sv.spreadsheets().values().update(
            spreadsheetId=DST_SS, range="'%s'!A2" % IV_SHEET,
            valueInputOption="USER_ENTERED", body={"values": iv_out},
        ).execute()

    ensure_sheet(sv, ARCHIVE_SHEET)
    arch_header, _ = build_archive_header(banners, fields)
    sv.spreadsheets().values().update(
        spreadsheetId=DST_SS, range="'%s'!A1" % ARCHIVE_SHEET,
        valueInputOption="USER_ENTERED", body={"values": [arch_header] + archive_out},
    ).execute()

    print("DONE")


if __name__ == "__main__":
    main()
