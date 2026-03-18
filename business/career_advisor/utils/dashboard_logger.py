#!/usr/bin/env python3
"""
dashboard_logger.py — 統合管理ダッシュボード Update_Log 更新ユーティリティ

【使い方】
    from utils.dashboard_logger import log_update

    log_update(
        icon="🔧 修正",
        summary="依頼内容の1〜2行要約",
        targets="変更したファイル / タブ名",
        details="①変更点A ②変更点B ③変更点C",
    )

【仕様】
    - 新エントリは Row5（列ヘッダー直下）に insert_rows で挿入（最新が常に上）
    - Row2 の統計バー（総更新回数・最終更新日時）を自動更新
    - 日時は YYYY/MM/DD HH:MM 形式で自動付与

【アイコン早見表】
    🆕 新規作成 / ➕ 機能追加 / 🔧 修正
    🎨 UI変更  / 🔄 更新     / 📋 設定変更
"""

from __future__ import annotations

import json
import os
import sys
import warnings
import datetime

warnings.filterwarnings("ignore")

_CAREER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _CAREER_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_CAREER_DIR, "config", ".env"))

import gspread
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SPREADSHEET_ID = "1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8"
SHEET_NAME = "Update_Log"
DATA_START_ROW = 5  # 行1: タイトル / 行2: 統計 / 行3: 空 / 行4: 列ヘッダー / 行5〜: データ


def _get_sheet() -> gspread.Worksheet:
    token_path = os.path.join(_CAREER_DIR, "config", "token.json")
    with open(token_path) as f:
        td = json.load(f)
    creds = Credentials(
        token=td.get("token"),
        refresh_token=td.get("refresh_token"),
        token_uri=td.get("token_uri"),
        client_id=td.get("client_id"),
        client_secret=td.get("client_secret"),
        scopes=td.get("scopes"),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    client = gspread.authorize(creds)
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(SHEET_NAME)


def log_update(
    icon: str,
    summary: str,
    targets: str,
    details: str,
    status: str = "✅ 完了",
) -> int:
    """
    Update_Log に1行追記する（最新エントリが常に先頭 Row5 に入る）。

    Returns:
        新しいエントリの連番
    """
    ws = _get_sheet()
    all_rows = ws.get_all_values()

    # 現在のデータ行から最大連番を取得
    data_rows = [r for r in all_rows[DATA_START_ROW - 1:] if any(c.strip() for c in r)]
    current_max = max((int(r[0]) for r in data_rows if r[0].isdigit()), default=0)
    new_num = current_max + 1

    # 現在日時（YYYY/MM/DD HH:MM）
    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")

    # Row5 に insert（既存データが1行ずつ下にシフトする）
    new_row = [str(new_num), now, icon, summary, targets, details, status]
    ws.insert_rows([new_row], row=DATA_START_ROW)

    # 統計バー（Row2）を更新
    _update_stats(ws)

    print(f"✅ Update_Log #{new_num} 記録完了 ({now})")
    return new_num


def _update_stats(ws: gspread.Worksheet) -> None:
    """Row2 の統計バー（総更新回数・最終更新日時）を再計算して更新する。"""
    all_rows = ws.get_all_values()
    data_rows = [r for r in all_rows[DATA_START_ROW - 1:] if any(c.strip() for c in r)]

    if not data_rows:
        return

    latest_num = max((int(r[0]) for r in data_rows if r[0].isdigit()), default=0)
    # Row5 は最新エントリなのでそこから日時を取得
    latest_date = data_rows[0][1][:10] if data_rows else ""

    # アイコン別カウント（G列の既存テキストを維持しつつ最終2列だけ更新）
    current_stat = all_rows[1] if len(all_rows) > 1 else [""] * 7
    new_stat = [
        f"📊 総更新回数: {latest_num}回",
        f"最終更新: {latest_date}",
        current_stat[2] if len(current_stat) > 2 else "",
        current_stat[3] if len(current_stat) > 3 else "",
        current_stat[4] if len(current_stat) > 4 else "",
        current_stat[5] if len(current_stat) > 5 else "",
        current_stat[6] if len(current_stat) > 6 else "",
    ]
    ws.update("A2:G2", [new_stat])


if __name__ == "__main__":
    # テスト実行
    n = log_update(
        icon="🔧 修正",
        summary="dashboard_logger.py 動作テスト",
        targets="utils/dashboard_logger.py",
        details="①insert_rows方式でRow5挿入 ②統計バー自動更新 ③日時自動付与",
        status="✅ 完了",
    )
    print(f"エントリ #{n} を書き込みました")
