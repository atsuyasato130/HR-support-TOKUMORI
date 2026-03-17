#!/usr/bin/env python3
"""
Google Sheets API セットアップ確認スクリプト

実行方法:
  python3 career_advisor/setup_google_sheets.py

このスクリプトは:
  1. 接続テストを行う
  2. シートのヘッダー（列名）を表示する
  3. SHEET_TO_SF_MAPPING に未対応の列名を表示する
"""

from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "utils"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../config/.env"))

SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1JEJRXCz2Xaj6etdjUYzYt3DR4YPQukNRWoeAVZy9gIU/edit"
SPREADSHEET_ID = "1JEJRXCz2Xaj6etdjUYzYt3DR4YPQukNRWoeAVZy9gIU"


def main():
    print("\n" + "=" * 60)
    print("  Google Sheets 接続テスト")
    print("=" * 60)

    # 認証方法を確認
    token_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "../config/token.json")
    )
    creds_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if os.path.exists(token_path):
        print(f"\n✅ 認証方式: OAuth2 トークン ({token_path})")
    elif creds_path and os.path.exists(creds_path):
        import json
        with open(creds_path) as f:
            creds_data = json.load(f)
        sa_email = creds_data.get("client_email", "不明")
        print(f"\n✅ 認証方式: サービスアカウント ({sa_email})")
    else:
        print("\n❌ 認証情報が見つかりません。")
        print("  config/token.json または GOOGLE_SERVICE_ACCOUNT_JSON の設定が必要です。")
        return

    try:
        from sheets_client import fetch_sheet_headers, fetch_sheet_as_records, SHEET_TO_SF_MAPPING  # type: ignore
    except ImportError as e:
        print(f"\n❌ sheets_client のインポートに失敗: {e}")
        print("  pip install gspread google-auth を実行してください")
        return

    print(f"\nスプレッドシートに接続中...")
    print(f"  ID: {SPREADSHEET_ID}")

    try:
        headers = fetch_sheet_headers(SPREADSHEET_ID)
    except Exception as e:
        print(f"\n❌ 接続失敗: {e}")
        print("\n考えられる原因:")
        print("  - Google Sheets API が有効化されていない")
        print("  - トークンの有効期限切れ / スコープ不足")
        print("  - スプレッドシートへのアクセス権限なし")
        return

    print(f"\n✅ 接続成功！シートのヘッダー（列名）:")
    for i, h in enumerate(headers, 1):
        mapped = SHEET_TO_SF_MAPPING.get(h, "（マッピング未設定）")
        status = "✅" if h in SHEET_TO_SF_MAPPING and SHEET_TO_SF_MAPPING[h] else "⚠️ "
        print(f"  [{i:2d}] {status} {h:30s} → {mapped or '別処理'}")

    # 未マッピング列の確認
    unmapped = [h for h in headers
                if h not in SHEET_TO_SF_MAPPING and h]
    if unmapped:
        print(f"\n⚠️  以下の列はマッピングが未設定です（sheets_client.py の SHEET_TO_SF_MAPPING に追加が必要）:")
        for h in unmapped:
            print(f"  - {h}")

    # データ件数確認
    try:
        records = fetch_sheet_as_records(SPREADSHEET_ID)
        print(f"\n📊 データ件数: {len(records)} 行")
        if records:
            print("  最新1件のサンプル:")
            for k, v in list(records[-1].items())[:5]:
                if v:
                    print(f"    {k}: {v}")
    except Exception as e:
        print(f"\n[警告] データ取得失敗: {e}")


if __name__ == "__main__":
    main()
