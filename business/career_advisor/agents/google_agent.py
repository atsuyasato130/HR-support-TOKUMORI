#!/usr/bin/env python3
"""
Googleエージェント

機能:
  - Gmail: 未読メール取得・返信案生成・送信
  - Google Sheets: データ読み取り・書き込み
  - Google Docs: ドキュメント読み取り・追記
  - Google Calendar: 予定確認（将来実装）

使い方:
  python3 google_agent.py
  from agents.google_agent import run
"""

from __future__ import annotations

import os
import base64
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import anthropic
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

# utils/ をパスに追加
sys.path.insert(0, os.path.join(BASE, "utils"))

CREDENTIALS_FILE = os.path.join(BASE, "../config/credentials.json")
TOKEN_FILE        = os.path.join(BASE, "../config/token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
]

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_GMAIL_REPLY_SYSTEM = """あなたはプロフェッショナルなメールアシスタントです。
受け取ったメールに対して、丁寧で自然な返信文を日本語で作成してください。
HR（人材紹介）業界のキャリアアドバイザーとして適切なトーンを保ってください。
返信文のみを出力し、説明や前置きは不要です。"""


# ──────────────────────────────────────────────
# Google 認証
# ──────────────────────────────────────────────

def _get_google_creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def _get_gmail_service():
    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=_get_google_creds())


def _get_sheets_service():
    from googleapiclient.discovery import build
    return build("sheets", "v4", credentials=_get_google_creds())


def _get_docs_service():
    from googleapiclient.discovery import build
    return build("docs", "v1", credentials=_get_google_creds())


# ──────────────────────────────────────────────
# Gmail 機能
# ──────────────────────────────────────────────

def _extract_body(payload: dict) -> str:
    """メール本文を再帰的に取得"""
    if "parts" in payload:
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text
    elif payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def get_unread_emails(max_results: int = 10) -> list[dict]:
    """未読メールを取得"""
    service = _get_gmail_service()
    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=max_results,
    ).execute()

    messages = result.get("messages", [])
    emails = []

    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        body = _extract_body(detail["payload"])

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(件名なし)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "body": body,
            "thread_id": detail.get("threadId"),
        })

    return emails


def generate_gmail_reply(email: dict, instruction: str = "") -> str:
    """Claude でメール返信案を生成"""
    prompt = f"""以下のメールへの返信を作成してください。

--- 受信メール ---
差出人: {email['from']}
件名: {email['subject']}
日時: {email['date']}

{email['body']}
---
"""
    if instruction:
        prompt += f"\n返信の方針: {instruction}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_GMAIL_REPLY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def send_gmail_reply(original: dict, reply_body: str) -> None:
    """メールを返信送信"""
    service = _get_gmail_service()
    msg = MIMEMultipart()
    msg["To"] = original["from"]
    msg["Subject"] = "Re: " + original["subject"].lstrip("Re: ")
    msg["In-Reply-To"] = original["id"]
    msg["References"] = original["id"]
    msg.attach(MIMEText(reply_body, "plain", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId="me",
        body={"raw": raw, "threadId": original["thread_id"]},
    ).execute()


# ──────────────────────────────────────────────
# Google Sheets 機能
# ──────────────────────────────────────────────

def read_sheet(spreadsheet_id: str, range_: str) -> list[list]:
    """スプレッドシートの範囲を読み取る"""
    service = _get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_,
    ).execute()
    return result.get("values", [])


def write_sheet(spreadsheet_id: str, range_: str, values: list[list]) -> None:
    """スプレッドシートに値を書き込む"""
    service = _get_sheets_service()
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        body={"values": values},
    ).execute()


def append_sheet(spreadsheet_id: str, range_: str, values: list[list]) -> None:
    """スプレッドシートに行を追記する"""
    service = _get_sheets_service()
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()


# ──────────────────────────────────────────────
# Google Docs 機能
# ──────────────────────────────────────────────

def read_doc(doc_id: str) -> str:
    """Googleドキュメントのテキストを取得"""
    service = _get_docs_service()
    doc = service.documents().get(documentId=doc_id).execute()

    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            for pe in element["paragraph"].get("elements", []):
                text_parts.append(pe.get("textRun", {}).get("content", ""))

    return "".join(text_parts)


def append_to_doc(doc_id: str, text: str) -> None:
    """Googleドキュメントにテキストを追記"""
    service = _get_docs_service()

    # 現在のドキュメントの末尾を取得
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    requests = [{
        "insertText": {
            "location": {"index": end_index},
            "text": "\n" + text,
        }
    }]
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()


# ──────────────────────────────────────────────
# Gmail CLIモード
# ──────────────────────────────────────────────

def _run_gmail():
    print("\nGmail エージェントを起動中...\n")

    try:
        service_check = _get_gmail_service()  # noqa: F841
    except Exception as e:
        print(f"[エラー] Google認証失敗: {e}")
        return

    print("Gmail に接続しました。未読メールを取得中...\n")

    emails = get_unread_emails(max_results=10)

    if not emails:
        print("未読メールはありません。")
        return

    print(f"未読メール: {len(emails)} 件\n")
    for i, email in enumerate(emails):
        print(f"[{i}] {email['subject']}  (From: {email['from']})")

    while True:
        choice = input("\n返信するメールの番号を入力（q で終了）: ").strip()
        if choice.lower() == "q":
            print("終了します。")
            return
        if choice.isdigit() and 0 <= int(choice) < len(emails):
            selected = emails[int(choice)]
            break
        print("無効な入力です。")

    print(f"\n{'='*60}")
    print(f"[{choice}] {selected['subject']}")
    print(f"    From : {selected['from']}")
    print(f"    Date : {selected['date']}")
    print(f"{'='*60}")
    print(selected["body"][:500] + ("..." if len(selected["body"]) > 500 else ""))

    instruction = input("\n返信の方針・補足を入力（空欄でも OK）: ").strip()

    print("\nClaude が返信案を生成中...")
    reply = generate_gmail_reply(selected, instruction)

    print(f"\n{'─'*60}")
    print("【返信案】")
    print(f"{'─'*60}")
    print(reply)
    print(f"{'─'*60}")

    while True:
        action = input(
            "\n操作を選択してください:\n"
            "  [s] このまま送信\n"
            "  [e] 手動で編集\n"
            "  [r] Claude に再生成させる\n"
            "  [q] キャンセル\n"
            "> "
        ).strip().lower()

        if action == "s":
            send_gmail_reply(selected, reply)
            print("\n返信を送信しました！")
            break
        elif action == "e":
            print("返信文を入力してください（空行2回で確定）:")
            lines = []
            empty_count = 0
            while empty_count < 2:
                line = input()
                if line == "":
                    empty_count += 1
                else:
                    empty_count = 0
                lines.append(line)
            reply = "\n".join(lines[:-2])
            print("\n【編集後の返信】")
            print(reply)
        elif action == "r":
            new_instruction = input("再生成の方針を入力: ").strip()
            print("\nClaude が再生成中...")
            reply = generate_gmail_reply(selected, new_instruction or instruction)
            print(f"\n{'─'*60}")
            print("【新しい返信案】")
            print(f"{'─'*60}")
            print(reply)
            print(f"{'─'*60}")
        elif action == "q":
            print("キャンセルしました。")
            break
        else:
            print("無効な入力です。")


# ──────────────────────────────────────────────
# Sheets CLIモード
# ──────────────────────────────────────────────

def _run_sheets():
    print("\nGoogle Sheets エージェントを起動中...\n")

    spreadsheet_id = input("スプレッドシートID（URLの /d/ 以降）> ").strip()
    if not spreadsheet_id:
        print("IDが入力されていません。終了します。")
        return

    while True:
        print("\n【操作を選択】")
        print("  [r] セル範囲を読み取る")
        print("  [w] セル範囲に書き込む")
        print("  [a] 行を末尾に追記する")
        print("  [q] 終了")

        action = input("\n> ").strip().lower()

        if action == "q":
            break

        range_ = input("範囲（例: Sheet1!A1:D10）> ").strip()

        if action == "r":
            try:
                values = read_sheet(spreadsheet_id, range_)
                print(f"\n取得データ ({len(values)}行):")
                for row in values:
                    print(row)
            except Exception as e:
                print(f"[エラー] {e}")

        elif action in ("w", "a"):
            print("値を入力してください（行ごと、カンマ区切り、空行で終了）:")
            rows = []
            while True:
                line = input("> ").strip()
                if not line:
                    break
                rows.append([v.strip() for v in line.split(",")])
            if not rows:
                print("入力がありません。")
                continue
            try:
                if action == "w":
                    write_sheet(spreadsheet_id, range_, rows)
                    print("書き込みました。")
                else:
                    append_sheet(spreadsheet_id, range_, rows)
                    print("追記しました。")
            except Exception as e:
                print(f"[エラー] {e}")

        else:
            print("無効な入力です。")


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'gmail' | 'sheets' | 'docs' | None（メニュー表示）

    将来追加予定:
      - 'calendar': Google Calendar 予定確認・作成
      - 'drive': Google Drive ファイル管理
      - 'forms': Google Forms 回答取得
    """
    if mode == "gmail":
        _run_gmail()
        return
    if mode == "sheets":
        _run_sheets()
        return

    print("\n" + "=" * 55)
    print("  Googleエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. Gmail（未読メール確認・返信）")
    print("  2. Google Sheets（データ読み取り・書き込み）")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_gmail()
            break
        elif choice == "2":
            _run_sheets()
            break
        elif choice == "q":
            break
        else:
            print("1・2・q のいずれかを入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
