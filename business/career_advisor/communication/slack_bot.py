"""
Slack AI Agent — Claude + Google Workspace + LINE + Salesforce 連携

【セットアップ手順】
1. pip install -r requirements.txt
2. cp .env.example .env  → API キーを記入
3. Google Cloud Console でプロジェクトを作成し、以下の API を有効化:
     - Google Calendar API
     - Gmail API
     - Google Docs API
4. OAuth 2.0 クライアント ID を作成（種類: デスクトップアプリ）→ credentials.json をダウンロード
5. credentials.json をこのディレクトリに置く
6. python main.py → ブラウザが開き Google 認証（初回のみ）

【Slack App 設定】(https://api.slack.com/apps)
- Socket Mode: 有効化 → App-Level Token (connections:write) を発行
- Bot Token Scopes: app_mentions:read, channels:history, im:history, im:write, chat:write
- Event Subscriptions → Subscribe to bot events:
    app_mention, message.im

【LINE 設定】(https://developers.line.biz/)
- Messaging API チャンネルを作成
- Channel Secret と Channel access token を取得 → .env に記入
- Webhook URL: ngrok の URL + /callback（起動時にコンソールに表示）

【Salesforce 設定】
- ユーザー名・パスワード・セキュリティトークンを .env に記入
- セキュリティトークン: Salesforce → 設定 → 個人情報 → セキュリティトークンのリセット
"""

import os
import base64
import json
import time
import threading
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText

from dotenv import load_dotenv
import anthropic
from anthropic import beta_tool
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import Flask, request as flask_request, abort

# LINE SDK (オプション)
try:
    from linebot.v3 import WebhookHandler
    from linebot.v3.exceptions import InvalidSignatureError
    from linebot.v3.messaging import (
        Configuration as LineConfiguration,
        ApiClient as LineApiClient,
        MessagingApi,
        ReplyMessageRequest,
        PushMessageRequest,
        TextMessage as LineTextMessage,
    )
    from linebot.v3.webhooks import MessageEvent, TextMessageContent
    _LINE_SDK_OK = True
except ImportError:
    _LINE_SDK_OK = False

# Salesforce SDK (オプション)
try:
    from simple_salesforce import Salesforce
    _SF_SDK_OK = True
except ImportError:
    _SF_SDK_OK = False

# ngrok (オプション)
try:
    from pyngrok import ngrok as _ngrok
    _NGROK_OK = True
except ImportError:
    _NGROK_OK = False

# Stock Agent (オプション)
try:
    from stock_agent import start_stock_scheduler
    _STOCK_OK = True
except ImportError:
    _STOCK_OK = False

# Notion SDK (オプション)
try:
    from notion_client import Client as NotionClient
    _NOTION_SDK_OK = True
except ImportError:
    _NOTION_SDK_OK = False

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "../config")
load_dotenv(os.path.join(_CONFIG_DIR, ".env"))


# ─── Google 認証 ────────────────────────────────────────────────────────────────

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

_CREDENTIALS_FILE = os.path.join(_CONFIG_DIR, "credentials.json")
_TOKEN_FILE = os.path.join(_CONFIG_DIR, "token.json")


def _get_google_creds() -> Credentials:
    creds = None
    if os.path.exists(_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(_TOKEN_FILE, GOOGLE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "credentials.json が見つかりません。\n"
                    "Google Cloud Console → APIs & Services → Credentials から\n"
                    "OAuth 2.0 クライアント ID (デスクトップ) を作成してダウンロードしてください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_FILE, GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return creds


_creds  = _get_google_creds()
_cal    = build("calendar", "v3", credentials=_creds)
_gmail  = build("gmail",    "v1", credentials=_creds)
_docs   = build("docs",     "v1", credentials=_creds)
_sheets = build("sheets",   "v4", credentials=_creds)


# ─── Google Calendar ツール ─────────────────────────────────────────────────────

@beta_tool
def list_calendar_events(max_results: int = 10) -> str:
    """Google Calendar の直近の予定を一覧表示する。

    Args:
        max_results: 取得する予定の最大件数（1〜50）。デフォルトは 10。
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        res = _cal.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = res.get("items", [])
        if not events:
            return "直近の予定はありません。"
        rows = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            rows.append(f"{start}  {e.get('summary', '（タイトルなし）')}  [id: {e['id']}]")
        return "\n".join(rows)
    except HttpError as err:
        return f"Calendar API エラー: {err}"


@beta_tool
def create_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
) -> str:
    """Google Calendar に新しい予定を作成する。

    Args:
        title: 予定のタイトル。
        start_datetime: 開始日時（RFC 3339 形式）例: '2025-03-01T10:00:00+09:00'
        end_datetime:   終了日時（RFC 3339 形式）例: '2025-03-01T11:00:00+09:00'
        description: 予定の説明（任意）。
    """
    try:
        body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_datetime},
            "end":   {"dateTime": end_datetime},
        }
        ev = _cal.events().insert(calendarId="primary", body=body).execute()
        return f"予定を作成しました: 「{ev['summary']}」 (id: {ev['id']})"
    except HttpError as err:
        return f"Calendar API エラー: {err}"


# ─── Gmail ツール ───────────────────────────────────────────────────────────────

def _decode_body(payload: dict) -> str:
    """メール本文（text/plain）を再帰的に抽出する。"""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
            deeper = _decode_body(part)
            if deeper:
                return deeper
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return ""


@beta_tool
def list_emails(query: str = "is:unread", max_results: int = 10) -> str:
    """Gmail のメールを検索して一覧表示する。

    Args:
        query: Gmail 検索クエリ。例: 'is:unread', 'from:boss@example.com', 'subject:会議'。
               デフォルトは 'is:unread'（未読メール）。
        max_results: 取得する件数（1〜50）。デフォルトは 10。
    """
    try:
        res = _gmail.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        msgs = res.get("messages", [])
        if not msgs:
            return f"「{query}」に一致するメールはありません。"
        rows = []
        for m in msgs:
            detail = _gmail.users().messages().get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            h = {hdr["name"]: hdr["value"] for hdr in detail["payload"]["headers"]}
            rows.append(
                f"id:{m['id']}  "
                f"From:{h.get('From', '?')}  "
                f"Subject:{h.get('Subject', '（件名なし）')}  "
                f"Date:{h.get('Date', '?')}"
            )
        return "\n".join(rows)
    except HttpError as err:
        return f"Gmail API エラー: {err}"


@beta_tool
def read_email(email_id: str) -> str:
    """メールの本文を取得する。

    Args:
        email_id: list_emails で取得した Gmail メッセージ ID。
    """
    try:
        msg = _gmail.users().messages().get(
            userId="me", id=email_id, format="full"
        ).execute()
        h = {hdr["name"]: hdr["value"] for hdr in msg["payload"]["headers"]}
        body = _decode_body(msg["payload"])
        return (
            f"From: {h.get('From', '?')}\n"
            f"Subject: {h.get('Subject', '（件名なし）')}\n"
            f"Date: {h.get('Date', '?')}\n\n"
            + (body[:3000] or "（本文なし）")
        )
    except HttpError as err:
        return f"Gmail API エラー: {err}"


@beta_tool
def send_email(to: str, subject: str, body: str) -> str:
    """Gmail でメールを送信する。

    Args:
        to: 宛先メールアドレス（例: 'someone@example.com'）。
        subject: 件名。
        body: 本文（プレーンテキスト）。
    """
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["to"]      = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        _gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"メールを送信しました → 宛先: '{to}'  件名: '{subject}'"
    except HttpError as err:
        return f"Gmail API エラー: {err}"


# ─── Google Docs ツール ─────────────────────────────────────────────────────────

@beta_tool
def create_google_doc(title: str, content: str) -> str:
    """Google ドキュメントを新規作成してテキストを挿入する。

    Args:
        title: ドキュメントのタイトル。
        content: 挿入するテキスト内容。
    """
    try:
        doc = _docs.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        _docs.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
        ).execute()
        url = f"https://docs.google.com/document/d/{doc_id}"
        return f"Google ドキュメントを作成しました: 「{title}」\n{url}"
    except HttpError as err:
        return f"Docs API エラー: {err}"


@beta_tool
def read_google_doc(document_id: str) -> str:
    """Google ドキュメントの内容を読み取る。

    Args:
        document_id: ドキュメント ID（URL の /document/d/{ここ}/ の部分）。
    """
    try:
        doc = _docs.documents().get(documentId=document_id).execute()
        parts = []
        for el in doc.get("body", {}).get("content", []):
            if "paragraph" in el:
                for run in el["paragraph"].get("elements", []):
                    if "textRun" in run:
                        parts.append(run["textRun"]["content"])
        text = "".join(parts)[:4000]
        return f"タイトル: {doc.get('title', '（タイトルなし）')}\n\n{text}"
    except HttpError as err:
        return f"Docs API エラー: {err}"


# ─── Google Sheets ツール ────────────────────────────────────────────────────────

@beta_tool
def read_sheet(spreadsheet_id: str, range_notation: str) -> str:
    """Google スプレッドシートのデータを読み取る。

    Args:
        spreadsheet_id: スプレッドシート ID（URL の /spreadsheets/d/{ここ}/ の部分）。
        range_notation: 読み取る範囲（例: 'Sheet1!A1:D10', 'シート1!A:C', 'Sheet1'）。
    """
    try:
        result = _sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
        ).execute()
        values = result.get("values", [])
        if not values:
            return "データが見つかりませんでした。"
        rows = ["\t".join(str(c) for c in row) for row in values]
        return f"{len(values)} 行のデータ:\n" + "\n".join(rows[:100])
    except HttpError as err:
        return f"Sheets API エラー: {err}"


@beta_tool
def write_sheet(spreadsheet_id: str, range_notation: str, values_json: str) -> str:
    """Google スプレッドシートのセルにデータを書き込む（上書き）。

    Args:
        spreadsheet_id: スプレッドシート ID。
        range_notation: 書き込む範囲（例: 'Sheet1!A1', 'シート1!A2:C5'）。
        values_json: 書き込むデータ（2次元配列の JSON 文字列）。
                     例: '[["名前", "売上", "日付"], ["田中", 100000, "2025-03-01"]]'
    """
    try:
        values = json.loads(values_json)
        result = _sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        return f"{result.get('updatedCells', '?')} セルを書き込みました。"
    except HttpError as err:
        return f"Sheets API エラー: {err}"


@beta_tool
def append_to_sheet(spreadsheet_id: str, range_notation: str, values_json: str) -> str:
    """Google スプレッドシートの末尾に行を追加する。

    Args:
        spreadsheet_id: スプレッドシート ID。
        range_notation: 追加先シート範囲（例: 'Sheet1!A:Z', 'シート1'）。
        values_json: 追加するデータ（2次元配列の JSON 文字列）。
                     例: '[["2025-03-01", "田中太郎", "成約", 500000]]'
    """
    try:
        values = json.loads(values_json)
        result = _sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
        updated = result.get("updates", {}).get("updatedCells", "?")
        return f"行を追加しました（更新セル数: {updated}）。"
    except HttpError as err:
        return f"Sheets API エラー: {err}"


@beta_tool
def create_spreadsheet(title: str, sheet_names: str = "Sheet1") -> str:
    """Google スプレッドシートを新規作成する。

    Args:
        title: スプレッドシートのタイトル。
        sheet_names: カンマ区切りのシート名（例: 'Sheet1,Sheet2,Sheet3'）。デフォルトは 'Sheet1'。
    """
    try:
        sheets = [
            {"properties": {"title": name.strip()}}
            for name in sheet_names.split(",")
        ]
        ss = _sheets.spreadsheets().create(
            body={"properties": {"title": title}, "sheets": sheets}
        ).execute()
        ss_id = ss["spreadsheetId"]
        url = f"https://docs.google.com/spreadsheets/d/{ss_id}"
        return f"スプレッドシートを作成しました: 「{title}」\nURL: {url}\nID: {ss_id}"
    except HttpError as err:
        return f"Sheets API エラー: {err}"


# ─── Notion ツール ───────────────────────────────────────────────────────────────

_NOTION_ENABLED = _NOTION_SDK_OK and bool(os.environ.get("NOTION_API_KEY"))
_notion = NotionClient(auth=os.environ.get("NOTION_API_KEY", "")) if _NOTION_ENABLED else None


def _notion_block_to_text(block: dict) -> str:
    """Notion ブロックをプレーンテキストに変換する。"""
    bt = block.get("type", "")
    rich = block.get(bt, {}).get("rich_text", [])
    text = "".join(r.get("plain_text", "") for r in rich)
    prefix = {
        "heading_1": "# ", "heading_2": "## ", "heading_3": "### ",
        "bulleted_list_item": "・", "numbered_list_item": "1. ",
        "to_do": "☐ ", "quote": "> ",
    }.get(bt, "")
    return prefix + text if text else ""


def _prop_to_str(prop: dict) -> str:
    """Notion プロパティ値を文字列に変換する。"""
    pt = prop.get("type", "")
    if pt == "title":
        return "".join(r["plain_text"] for r in prop.get("title", []))
    if pt == "rich_text":
        return "".join(r["plain_text"] for r in prop.get("rich_text", []))
    if pt == "number":
        return str(prop.get("number", ""))
    if pt == "select":
        sel = prop.get("select")
        return sel["name"] if sel else ""
    if pt == "multi_select":
        return ", ".join(s["name"] for s in prop.get("multi_select", []))
    if pt == "date":
        d = prop.get("date")
        return d["start"] if d else ""
    if pt == "checkbox":
        return "✓" if prop.get("checkbox") else "✗"
    if pt == "url":
        return prop.get("url", "") or ""
    if pt == "email":
        return prop.get("email", "") or ""
    if pt == "phone_number":
        return prop.get("phone_number", "") or ""
    if pt == "people":
        return ", ".join(p.get("name", "") for p in prop.get("people", []))
    if pt == "relation":
        return f"（{len(prop.get('relation', []))}件のリレーション）"
    if pt == "formula":
        f = prop.get("formula", {})
        return str(f.get(f.get("type", ""), ""))
    return ""


@beta_tool
def search_notion(query: str, filter_type: str = "page") -> str:
    """Notion 全体を検索する。

    Args:
        query: 検索キーワード。
        filter_type: 検索対象（'page' または 'database'）。デフォルトは 'page'。
    """
    if not _NOTION_ENABLED:
        return "Notion 連携が未設定です。.env に NOTION_API_KEY を設定してください。"
    try:
        params: dict = {"query": query, "page_size": 10}
        if filter_type in ("page", "database"):
            params["filter"] = {"value": filter_type, "property": "object"}
        res = _notion.search(**params)
        results = res.get("results", [])
        if not results:
            return f"「{query}」に一致するものが見つかりませんでした。"
        rows = []
        for r in results:
            obj = r.get("object", "")
            if obj == "page":
                props = r.get("properties", {})
                title = ""
                for p in props.values():
                    if p.get("type") == "title":
                        title = _prop_to_str(p)
                        break
                rows.append(f"[ページ] {title or '（タイトルなし）'}  ID: {r['id']}")
            elif obj == "database":
                title_list = r.get("title", [])
                title = "".join(t["plain_text"] for t in title_list)
                rows.append(f"[データベース] {title or '（タイトルなし）'}  ID: {r['id']}")
        return "\n".join(rows)
    except Exception as err:
        return f"Notion API エラー: {err}"


@beta_tool
def read_notion_database(database_id: str, filter_json: str = "{}") -> str:
    """Notion データベースのレコード一覧を取得する。

    Args:
        database_id: データベース ID（Notion URL の末尾 32 文字 / ハイフン区切り）。
        filter_json: Notion フィルター条件の JSON 文字列（省略可）。
                     例（ステータスが「対応中」）:
                     '{"property":"ステータス","select":{"equals":"対応中"}}'
    """
    if not _NOTION_ENABLED:
        return "Notion 連携が未設定です。.env に NOTION_API_KEY を設定してください。"
    try:
        params: dict = {"database_id": database_id, "page_size": 30}
        filter_obj = json.loads(filter_json)
        if filter_obj:
            params["filter"] = filter_obj
        res = _notion.databases.query(**params)
        pages = res.get("results", [])
        if not pages:
            return "レコードが見つかりませんでした。"
        rows = []
        for page in pages:
            props = page.get("properties", {})
            cells = []
            for name, prop in props.items():
                val = _prop_to_str(prop)
                if val:
                    cells.append(f"{name}: {val}")
            rows.append(f"ID:{page['id']}  " + " | ".join(cells))
        return f"{len(pages)} 件:\n" + "\n".join(rows)
    except Exception as err:
        return f"Notion API エラー: {err}"


@beta_tool
def read_notion_page(page_id: str) -> str:
    """Notion ページの本文テキストを取得する。

    Args:
        page_id: ページ ID（search_notion や read_notion_database で取得した ID）。
    """
    if not _NOTION_ENABLED:
        return "Notion 連携が未設定です。.env に NOTION_API_KEY を設定してください。"
    try:
        page = _notion.pages.retrieve(page_id=page_id)
        props = page.get("properties", {})
        title = ""
        for p in props.values():
            if p.get("type") == "title":
                title = _prop_to_str(p)
                break

        blocks = _notion.blocks.children.list(block_id=page_id, page_size=100)
        lines = [f"タイトル: {title}\n"]
        for b in blocks.get("results", []):
            line = _notion_block_to_text(b)
            if line:
                lines.append(line)
        return "\n".join(lines)[:4000]
    except Exception as err:
        return f"Notion API エラー: {err}"


@beta_tool
def create_notion_page(database_id: str, properties_json: str, content: str = "") -> str:
    """Notion データベースに新しいページ（レコード）を作成する。

    Args:
        database_id: 親データベースの ID。
        properties_json: プロパティの JSON 文字列。
                         タイトル例: '{"名前": {"title": [{"text": {"content": "田中太郎"}}]}}'
                         テキスト例: '{"備考": {"rich_text": [{"text": {"content": "メモ"}}]}}'
        content: ページ本文のテキスト（省略可）。
    """
    if not _NOTION_ENABLED:
        return "Notion 連携が未設定です。.env に NOTION_API_KEY を設定してください。"
    try:
        properties = json.loads(properties_json)
        body: dict = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        if content:
            body["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                    },
                }
            ]
        page = _notion.pages.create(**body)
        page_url = page.get("url", "")
        return f"Notion ページを作成しました。\nURL: {page_url}\nID: {page['id']}"
    except Exception as err:
        return f"Notion API エラー: {err}"


# ─── LINE ツール ────────────────────────────────────────────────────────────────

_LINE_ENABLED = _LINE_SDK_OK and bool(os.environ.get("LINE_CHANNEL_SECRET"))

if _LINE_ENABLED:
    _line_handler = WebhookHandler(os.environ["LINE_CHANNEL_SECRET"])
    _line_config  = LineConfiguration(
        access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    )
else:
    _line_handler = None
    _line_config  = None


@beta_tool
def send_line_message(user_id: str, message: str) -> str:
    """LINE ユーザーにプッシュメッセージを送信する。

    Args:
        user_id: LINE ユーザーID（U + 32文字の英数字、例: 'Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'）。
        message: 送信するメッセージ本文（プレーンテキスト）。
    """
    if not _LINE_ENABLED:
        return "LINE 連携が未設定です。.env に LINE_CHANNEL_SECRET と LINE_CHANNEL_ACCESS_TOKEN を設定してください。"
    try:
        with LineApiClient(_line_config) as api_client:
            MessagingApi(api_client).push_message(
                PushMessageRequest(
                    to=user_id,
                    messages=[LineTextMessage(text=message)],
                )
            )
        return f"LINE メッセージを送信しました → ユーザーID: {user_id}"
    except Exception as err:
        return f"LINE API エラー: {err}"


# ─── Salesforce ツール ──────────────────────────────────────────────────────────

_SF_ENABLED = _SF_SDK_OK and bool(os.environ.get("SF_USERNAME"))


def _get_sf():
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


@beta_tool
def search_salesforce(soql_query: str) -> str:
    """Salesforce のレコードを SOQL クエリで検索する。

    Args:
        soql_query: SOQL クエリ文字列。
                    例: "SELECT Id, Name, Email FROM Contact WHERE Name LIKE '%田中%'"
                    例: "SELECT Id, Name, StageName, Amount FROM Opportunity WHERE StageName = 'Prospecting'"
    """
    if not _SF_ENABLED:
        return "Salesforce 連携が未設定です。.env に SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN を設定してください。"
    try:
        sf = _get_sf()
        result = sf.query(soql_query)
        records = result.get("records", [])
        if not records:
            return "該当するレコードが見つかりませんでした。"
        rows = []
        for r in records:
            row = " | ".join(f"{k}: {v}" for k, v in r.items() if k != "attributes")
            rows.append(row)
        return f"{len(records)} 件見つかりました:\n" + "\n".join(rows)
    except Exception as err:
        return f"Salesforce エラー: {err}"


@beta_tool
def update_salesforce_record(object_type: str, record_id: str, fields_json: str) -> str:
    """Salesforce の既存レコードを更新する。

    Args:
        object_type: オブジェクト種別（例: 'Opportunity', 'Account', 'Lead', 'Contact', 'Case'）。
        record_id: Salesforce レコード ID（18桁の英数字）。
        fields_json: 更新するフィールドと値の JSON 文字列。
                     例: '{"StageName": "Closed Won", "CloseDate": "2025-03-31"}'
                     例: '{"Amount": 500000, "Description": "契約更新"}'
    """
    if not _SF_ENABLED:
        return "Salesforce 連携が未設定です。.env に SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN を設定してください。"
    try:
        sf = _get_sf()
        fields = json.loads(fields_json)
        getattr(sf, object_type).update(record_id, fields)
        return f"{object_type} (ID: {record_id}) を更新しました。変更内容: {fields}"
    except Exception as err:
        return f"Salesforce エラー: {err}"


@beta_tool
def create_salesforce_record(object_type: str, fields_json: str) -> str:
    """Salesforce に新規レコードを作成する。

    Args:
        object_type: オブジェクト種別（例: 'Lead', 'Contact', 'Account', 'Opportunity'）。
        fields_json: フィールドと値の JSON 文字列。
                     例 (Lead): '{"LastName": "田中", "FirstName": "太郎", "Email": "tanaka@example.com", "Company": "株式会社テスト"}'
                     例 (Contact): '{"LastName": "鈴木", "FirstName": "花子", "AccountId": "001xxxxxxxxxxxxxxx"}'
    """
    if not _SF_ENABLED:
        return "Salesforce 連携が未設定です。.env に SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN を設定してください。"
    try:
        sf = _get_sf()
        fields = json.loads(fields_json)
        result = getattr(sf, object_type).create(fields)
        return f"{object_type} を作成しました。新規 ID: {result['id']}"
    except Exception as err:
        return f"Salesforce エラー: {err}"


@beta_tool
def get_salesforce_summary(object_type: str, conditions: str = "") -> str:
    """Salesforce のレコード件数を集計する。

    Args:
        object_type: 集計するオブジェクト種別（例: 'Opportunity', 'Lead', 'Account', 'Case'）。
        conditions: WHERE 句の条件（省略可）。
                    例: "StageName = 'Closed Won' AND CloseDate = THIS_MONTH"
                    例: "CreatedDate = THIS_WEEK"
    """
    if not _SF_ENABLED:
        return "Salesforce 連携が未設定です。.env に SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN を設定してください。"
    try:
        sf = _get_sf()
        where = f" WHERE {conditions}" if conditions else ""
        result = sf.query(f"SELECT COUNT(Id) cnt FROM {object_type}{where}")
        count = result["records"][0]["cnt"]
        cond_str = f"（条件: {conditions}）" if conditions else ""
        return f"{object_type} の件数{cond_str}: {count} 件"
    except Exception as err:
        return f"Salesforce エラー: {err}"


# ─── Slack 操作ツール ─────────────────────────────────────────────────────────────
# （_slack_client は後で Slack Bot セクションで再定義するが、ツール参照のためここで先行初期化）

_slack_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])


@beta_tool
def list_slack_channels(limit: int = 30) -> str:
    """参加しているSlackチャンネルの一覧を取得する。

    Args:
        limit: 取得件数（最大200）。デフォルトは30。
    """
    try:
        res = _slack_client.conversations_list(
            types="public_channel,private_channel",
            limit=limit,
            exclude_archived=True,
        )
        channels = res.get("channels", [])
        if not channels:
            return "チャンネルが見つかりませんでした。"
        rows = []
        for ch in channels:
            members = f"（{ch.get('num_members', '?')}人）" if "num_members" in ch else ""
            rows.append(f"#{ch['name']}{members}  ID: {ch['id']}")
        return "\n".join(rows)
    except Exception as err:
        return f"Slack API エラー: {err}"


@beta_tool
def read_slack_channel(channel_id: str, limit: int = 20) -> str:
    """Slackチャンネルの最近のメッセージを取得する。

    Args:
        channel_id: チャンネルID（list_slack_channels で取得。例: 'C012AB3CD'）。
        limit: 取得するメッセージ数（最大100）。デフォルトは20。
    """
    try:
        res = _slack_client.conversations_history(channel=channel_id, limit=limit)
        messages = res.get("messages", [])
        if not messages:
            return "メッセージが見つかりませんでした。"
        _user_cache: dict = {}
        def get_username(uid: str) -> str:
            if uid not in _user_cache:
                try:
                    info = _slack_client.users_info(user=uid)
                    _user_cache[uid] = info["user"].get("real_name") or info["user"].get("name", uid)
                except Exception:
                    _user_cache[uid] = uid
            return _user_cache[uid]
        rows = []
        for m in reversed(messages):
            ts = datetime.fromtimestamp(float(m.get("ts", 0))).strftime("%m/%d %H:%M")
            user = get_username(m.get("user", "")) if m.get("user") else "bot"
            text = m.get("text", "").replace("\n", " ")[:200]
            rows.append(f"[{ts}] {user}: {text}")
        return "\n".join(rows)
    except Exception as err:
        return f"Slack API エラー: {err}"


@beta_tool
def post_to_slack(channel_id: str, message: str) -> str:
    """任意のSlackチャンネルまたはユーザーにメッセージを投稿する。

    Args:
        channel_id: チャンネルID（例: 'C012AB3CD'）またはユーザーID（例: 'U012AB3CD'）。
        message: 送信するメッセージ本文。
    """
    try:
        res = _slack_client.chat_postMessage(channel=channel_id, text=message)
        return f"メッセージを投稿しました（ts: {res['ts']}）。"
    except Exception as err:
        return f"Slack API エラー: {err}"


@beta_tool
def get_slack_thread(channel_id: str, thread_ts: str, limit: int = 20) -> str:
    """Slackのスレッド内のメッセージを取得する。

    Args:
        channel_id: チャンネルID。
        thread_ts: スレッドの親メッセージのタイムスタンプ（例: '1234567890.123456'）。
        limit: 取得するメッセージ数。デフォルトは20。
    """
    try:
        res = _slack_client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=limit,
        )
        messages = res.get("messages", [])
        if not messages:
            return "スレッドが見つかりませんでした。"
        rows = []
        for m in messages:
            ts = datetime.fromtimestamp(float(m.get("ts", 0))).strftime("%m/%d %H:%M")
            user = m.get("user", "bot")
            text = m.get("text", "").replace("\n", " ")[:200]
            rows.append(f"[{ts}] {user}: {text}")
        return "\n".join(rows)
    except Exception as err:
        return f"Slack API エラー: {err}"


# ─── Claude エージェント ─────────────────────────────────────────────────────────

_claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

TOOLS = [
    list_calendar_events,
    create_calendar_event,
    list_emails,
    read_email,
    send_email,
    create_google_doc,
    read_google_doc,
    read_sheet,
    write_sheet,
    append_to_sheet,
    create_spreadsheet,
    search_notion,
    read_notion_database,
    read_notion_page,
    create_notion_page,
    send_line_message,
    search_salesforce,
    update_salesforce_record,
    create_salesforce_record,
    get_salesforce_summary,
    list_slack_channels,
    read_slack_channel,
    post_to_slack,
    get_slack_thread,
]

_integrations = ["Google Calendar", "Gmail", "Google Docs", "Google Sheets"]
if _LINE_ENABLED:
    _integrations.append("LINE")
if _SF_ENABLED:
    _integrations.append("Salesforce")
if _NOTION_ENABLED:
    _integrations.append("Notion")
if _STOCK_OK:
    _integrations.append("株価監視")

SYSTEM_PROMPT = (
    "あなたは役立つ AI アシスタントです。以下のツールを使えます：\n"
    "- Google Calendar：予定の確認・作成\n"
    "- Gmail：メールの一覧・読み取り・送信\n"
    "- Google Docs：ドキュメントの作成・読み取り\n"
    "- Google Sheets：スプレッドシートの読み取り・書き込み・行追加・新規作成\n"
    "- Notion：ページ・データベースの検索・読み取り・新規ページ作成\n"
    "- LINE：ユーザーへのプッシュメッセージ送信\n"
    "- Salesforce：顧客・リード・商談の検索・作成・更新・集計\n"
    "- Slack：チャンネル一覧・メッセージ読み取り・投稿・スレッド取得\n\n"
    "常に日本語で回答してください。"
    "ツールを呼び出す前に、何をするか一言添えてください。"
    "複数のツールを組み合わせて複雑なタスクを達成することができます。"
)

# Slack スレッド ID / LINE ユーザー ID → 会話履歴
_histories: dict[str, list[dict]] = {}


def run_agent(user_message: str, thread_id: str) -> str:
    """Claude エージェントを実行して最終テキスト応答を返す。"""
    history = _histories.get(thread_id, [])
    history.append({"role": "user", "content": user_message})

    runner = _claude.beta.messages.tool_runner(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=history,
    )

    final_text = ""
    for msg in runner:
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                final_text = block.text

    if final_text:
        history.append({"role": "assistant", "content": final_text})
    _histories[thread_id] = history[-40:]

    return final_text or "申し訳ありません、応答を生成できませんでした。"


# ─── 企業紹介文コマンド ──────────────────────────────────────────────────────────

import re as _re
import urllib.request as _urllib_req
import urllib.error as _urllib_err

_NOTION_DB_ID = "5cdbd391-97f9-4db7-b7e2-75d317166bfd"
_LSTEP_ENDPOINT = os.environ.get("LSTEP_API_ENDPOINT", "")
_LSTEP_TOKEN    = os.environ.get("LSTEP_API_TOKEN", "")
_LSTEP_PARAM    = os.environ.get("LSTEP_MESSAGE_PARAM", "message_text")


def _notion_raw(method: str, path: str, body=None) -> dict:
    url  = f"https://api.notion.com/v1{path}"
    data = json.dumps(body).encode() if body else None
    req  = _urllib_req.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {os.environ.get('NOTION_API_KEY', '')}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method=method,
    )
    try:
        with _urllib_req.urlopen(req) as r:
            return json.loads(r.read())
    except _urllib_err.HTTPError as e:
        return {"error": e.read().decode()}


def _fetch_company(company_name: str):
    """会社名の部分一致でNotionから企業情報を取得する。"""
    r = _notion_raw("POST", f"/databases/{_NOTION_DB_ID}/query", {
        "filter": {"property": "会社名", "title": {"contains": company_name}},
        "page_size": 1,
    })
    pages = r.get("results", [])
    if not pages:
        return None
    p = pages[0]
    props = p["properties"]

    def rt(k):
        return "".join(x.get("plain_text", "") for x in props.get(k, {}).get("rich_text", []))

    def ms(k):
        return ", ".join(i.get("name", "") for i in props.get(k, {}).get("multi_select", []))

    def title(k):
        return "".join(x.get("plain_text", "") for x in props.get(k, {}).get("title", []))

    def url(k):
        return props.get(k, {}).get("url") or ""

    return {
        "name":        title("会社名"),
        "url":         url("ウェブサイト"),
        "gyokai":      ms("業界"),
        "shokushu":    ms("職種"),
        "phase":       ms("企業フェーズ"),
        "kinmu":       ms("勤務地"),
        "gakureki":    ms("学歴：要件"),
        "jigyou":      rt("事業内容"),
        "senkou":      rt("選考フロー"),
        "setsumeikai": rt("説明会日程"),
        "miryoku":     rt("学生へ伝える魅力ポイント"),
        "saiyo":       rt("採用要件"),
    }


def _generate_recommend_points(info: dict) -> str:
    """Claudeでおすすめポイントを生成する。"""
    prompt = f"""以下の企業情報をもとに、就活生向けのおすすめポイントを生成してください。

企業名：{info['name']}
事業内容：{info['jigyou']}
選考フロー：{info['senkou']}
HP：{info['url']}

今の就活生のトレンド（成長環境・裁量・安定性・福利厚生・社風・リモートなど）を踏まえ、
企業情報から読み取れる具体的な魅力を3〜5点挙げてください。
各ポイントは「▶ 」で始め、1〜2文で完結させてください。
絵文字は使わず、ポイントのみ出力してください。"""
    try:
        resp = _claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception:
        return "▶ 詳細はお問い合わせください"


def _build_intro_text(info: dict) -> str:
    """Pattern A（区切り線 + 絵文字）で企業紹介テキストを組み立てる。"""
    recommend = _generate_recommend_points(info)

    parts = [
        "━━━━━━━━━━━━━━━━━━",
        f"🏢 {info['name']}",
        "━━━━━━━━━━━━━━━━━━",
        "",
        "🌐 HP",
        info["url"] or "ー",
        "",
        "📋 事業概要",
        (info["jigyou"] or "ー").strip(),
        "",
        "🔄 選考フロー",
        (info["senkou"] or "ー").strip(),
        "",
        "✨ おすすめポイント",
        recommend,
        "",
        "📅 説明会・選考案内",
        (info["setsumeikai"] or "ー").strip(),
    ]
    return "\n".join(parts)


def _send_to_lstep(message: str) -> str:
    """LステップAPIでメッセージを送信する。"""
    if not _LSTEP_ENDPOINT or not _LSTEP_TOKEN:
        return "Lステップ APIが未設定です（.env の LSTEP_API_ENDPOINT / LSTEP_API_TOKEN を設定してください）"
    try:
        import urllib.parse
        data = urllib.parse.urlencode({_LSTEP_PARAM: message}).encode()
        req = _urllib_req.Request(
            _LSTEP_ENDPOINT,
            data=data,
            headers={
                "Authorization": f"Bearer {_LSTEP_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with _urllib_req.urlopen(req, timeout=10) as r:
            return f"送信完了（ステータス: {r.status}）"
    except Exception as e:
        return f"送信エラー: {e}"


def _handle_intro_command(raw_names: str, channel: str, thread_ts: str) -> None:
    """紹介文コマンドをバックグラウンドで処理する（複数企業対応）。"""
    companies = _split_companies(raw_names)
    label = "、".join(companies)

    result = _slack_client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"⏳ 「{label}」の紹介文を生成中...",
    )
    placeholder_ts = result["ts"]

    found = []
    not_found = []
    for name in companies:
        info = _fetch_company(name)
        if info:
            found.append((info["name"], _build_intro_text(info)))
        else:
            not_found.append(name)

    if not found:
        _slack_client.chat_update(
            channel=channel,
            ts=placeholder_ts,
            text=f"❌ {' / '.join(not_found)} が直紹介DBに見つかりませんでした。企業名を確認してください。",
        )
        return

    # 1社目でplaceholderを更新、2社目以降は新規メッセージで返信
    for i, (name, intro_text) in enumerate(found):
        lstep_status = ""
        if _LSTEP_ENDPOINT and _LSTEP_TOKEN:
            lstep_result = _send_to_lstep(intro_text)
            lstep_status = f"\n\n✅ Lステップ送信: {lstep_result}"

        msg = (
            f"*企業紹介文 — {name}*\n"
            f"下記をコピーしてLステップから送信してください。\n\n"
            f"```\n{intro_text}\n```"
            + lstep_status
        )

        if i == 0:
            _slack_client.chat_update(channel=channel, ts=placeholder_ts, text=msg)
        else:
            _slack_client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=msg)

    if not_found:
        _slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"⚠️ 見つからなかった企業: {' / '.join(not_found)}",
        )


# ─── Slack Bot ───────────────────────────────────────────────────────────────────

_slack_app = App(token=os.environ["SLACK_BOT_TOKEN"])
# _slack_client は上の「Slack 操作ツール」セクションで初期化済み

# 紹介文コマンドのパターン: 「紹介文企業名」「紹介文 企業名」「企業名 紹介文」「企業名の紹介文」すべて対応
# 「紹介文 企業名」「紹介文企業名」→ 先頭に紹介文がある場合のみ
# 「企業名の紹介文」「企業名の紹介文を作って」→ の紹介文 が含まれる場合
_INTRO_PATTERN = _re.compile(r"^紹介文\s*(.+)|(.+?)の紹介文")


def _intro_company_name(m: _re.Match) -> str:
    """マッチオブジェクトから企業名（複数可）の文字列を取り出す。"""
    return (m.group(1) or m.group(2) or "").strip()


def _split_companies(text: str) -> list:
    """「、」「,」「/」「・」「と」で複数企業名を分割する。"""
    names = _re.split(r"[、，,/・]|(?<=[\u3040-\u30FF\u4E00-\u9FFF\w])と(?=[\u3040-\u30FF\u4E00-\u9FFF\w])", text.strip())
    return [n.strip() for n in names if n.strip()]


def _reply_in_background(
    channel: str, thread_ts: str, user_text: str, placeholder_ts: str
) -> None:
    """バックグラウンドスレッドで Claude を呼び出し、Slack のメッセージを更新する。"""
    try:
        text = run_agent(user_text, thread_ts)
    except Exception as exc:
        text = f"❌ エラーが発生しました: {exc}"
    _slack_client.chat_update(channel=channel, ts=placeholder_ts, text=text)


@_slack_app.event("app_mention")
def on_mention(event, say):
    """@メンションに応答する。"""
    channel   = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    raw_text  = event.get("text", "")
    user_text = raw_text.split(">", 1)[-1].strip() if ">" in raw_text else raw_text.strip()

    # 紹介文コマンドを優先処理
    m = _INTRO_PATTERN.search(user_text)
    if m:
        company_name = _intro_company_name(m)
        threading.Thread(
            target=_handle_intro_command,
            args=(company_name, channel, thread_ts),
            daemon=True,
        ).start()
        return

    result = say(text="⏳ 処理中...", thread_ts=thread_ts)
    threading.Thread(
        target=_reply_in_background,
        args=(channel, thread_ts, user_text, result["ts"]),
        daemon=True,
    ).start()


@_slack_app.event("message")
def on_dm(event, say):
    """ダイレクトメッセージに応答する。"""
    if event.get("channel_type") != "im" or event.get("bot_id"):
        return

    channel   = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    user_text = event.get("text", "").strip()
    if not user_text:
        return

    # 紹介文コマンドを優先処理
    m = _INTRO_PATTERN.search(user_text)
    if m:
        company_name = _intro_company_name(m)
        threading.Thread(
            target=_handle_intro_command,
            args=(company_name, channel, thread_ts),
            daemon=True,
        ).start()
        return

    result = say(text="⏳ 処理中...", thread_ts=thread_ts)
    threading.Thread(
        target=_reply_in_background,
        args=(channel, thread_ts, user_text, result["ts"]),
        daemon=True,
    ).start()


# ─── LINE Webhook (Flask) ────────────────────────────────────────────────────────

_flask_app = Flask(__name__)


@_flask_app.route("/callback", methods=["POST"])
def line_callback():
    """LINE Webhook エンドポイント。"""
    if not _LINE_ENABLED:
        abort(404)
    signature = flask_request.headers.get("X-Line-Signature", "")
    body = flask_request.get_data(as_text=True)
    try:
        _line_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


if _LINE_ENABLED:
    @_line_handler.add(MessageEvent, message=TextMessageContent)
    def handle_line_message(event):
        """LINE メッセージを受信して Claude に処理させる。"""
        user_id    = event.source.user_id
        user_text  = event.message.text
        reply_token = event.reply_token

        # まず「処理中」を返信（reply_token は 30 秒で失効するため即時応答）
        try:
            with LineApiClient(_line_config) as api_client:
                MessagingApi(api_client).reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[LineTextMessage(text="⏳ 処理中...")],
                    )
                )
        except Exception:
            pass

        # Claude の応答をバックグラウンドで生成してプッシュ通知
        threading.Thread(
            target=_push_line_response,
            args=(user_id, user_text),
            daemon=True,
        ).start()


def _push_line_response(user_id: str, user_text: str) -> None:
    """Claude の応答を生成して LINE にプッシュ送信する。"""
    try:
        text = run_agent(user_text, f"line_{user_id}")
    except Exception as exc:
        text = f"❌ エラーが発生しました: {exc}"
    if _LINE_ENABLED:
        try:
            with LineApiClient(_line_config) as api_client:
                MessagingApi(api_client).push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[LineTextMessage(text=text)],
                    )
                )
        except Exception as err:
            print(f"LINE push エラー: {err}")


def _start_flask(port: int = 5000) -> None:
    """Flask サーバーをバックグラウンドスレッドで起動する。"""
    _flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


# ─── Gmail 企業メール → Slack 自動通知 ─────────────────────────────────────────────

# 企業からのメールを幅広くキャッチするクエリ（時間フィルタは agent1_gmail_fetch で動的付与）
_SELECTION_QUERY_BASE = (
    "(subject:選考 OR subject:面接 OR subject:内定 OR subject:採用 OR subject:不採用 "
    "OR subject:お見送り OR subject:辞退 OR subject:日程 OR subject:合否 OR subject:案内 "
    "OR subject:欠席 OR subject:キャンセル OR subject:結果 OR subject:説明会 "
    "OR subject:インターン OR subject:選考会) "
    "-from:@circus-group.jp -from:circus-group.jp"
)

# 送信者除外リスト（ドメイン・表示名どちらでも一致したらスキップ）
_EXCLUDED_SENDER_PATTERNS = [
    "circus-group.jp",
    "circus agent",
    "circus-agent",
    "circusagent",
]


def _is_excluded_sender(sender: str) -> bool:
    """送信者が除外対象かどうか判定（大文字小文字・表示名・ドメイン問わず）。"""
    sender_lower = sender.lower()
    return any(pattern in sender_lower for pattern in _EXCLUDED_SENDER_PATTERNS)


# 返信・転送メールの件名プレフィックス（これらで始まる件名はスキップ）
_REPLY_SUBJECT_PREFIXES = ("re:", "re：", "fw:", "fw：", "fwd:", "fwd：")


def _is_reply_email(subject: str) -> bool:
    """返信・転送メール（Re:/Fw: 等で始まる件名）かどうか判定。"""
    return subject.strip().lower().startswith(_REPLY_SUBJECT_PREFIXES)


# 除外する件名パターン（circus AGENTなどの社内システム自動通知）
_EXCLUDED_SUBJECT_PATTERNS = [
    "【選考連絡】",
]


def _is_excluded_subject(subject: str) -> bool:
    """除外対象の件名パターンを含むか判定。"""
    return any(pattern in subject for pattern in _EXCLUDED_SUBJECT_PATTERNS)


_processed_email_ids: set = set()
_PROCESSED_IDS_FILE = os.path.join(os.path.dirname(__file__), "../config/processed_email_ids.json")


def _load_processed_ids_from_file() -> None:
    """起動時に処理済みIDをファイルから読み込む（直近24時間分のみ）。"""
    global _processed_email_ids
    if not os.path.exists(_PROCESSED_IDS_FILE):
        return
    try:
        with open(_PROCESSED_IDS_FILE) as f:
            data = json.load(f)
        cutoff = time.time() - 86400  # 24時間より古いIDは捨てる
        loaded = {k for k, v in data.items() if v > cutoff}
        _processed_email_ids.update(loaded)
        print(f"[企業メール通知] 処理済みID {len(loaded)} 件をファイルから復元")
    except Exception as e:
        print(f"[企業メール通知] 処理済みID読み込みエラー: {e}")


def _save_processed_id(email_id: str) -> None:
    """処理済みIDをファイルに保存する（24時間超のエントリは自動削除）。"""
    try:
        if os.path.exists(_PROCESSED_IDS_FILE):
            with open(_PROCESSED_IDS_FILE) as f:
                data = json.load(f)
        else:
            data = {}
        data[email_id] = time.time()
        cutoff = time.time() - 86400
        data = {k: v for k, v in data.items() if v > cutoff}
        with open(_PROCESSED_IDS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[企業メール通知] 処理済みID保存エラー: {e}")


# 学生スレッドを検索するSlackチャンネル（順番に検索）
_STUDENT_THREAD_CHANNELS = ["C0A2YSANGKS", "C0A4SJDDUV9"]

# メール種別と絵文字・CAネクストアクションのマッピング
_EMAIL_TYPE_CONFIG = {
    "欠席連絡":     {"icon": "🚫", "action_hint": "辞退か欠席かを確認し、リスケ日程を回収する"},
    "日程確定":     {"icon": "📅", "action_hint": "確定した日程を学生に転送して案内する"},
    "合否連絡":     {"icon": "📊", "action_hint": "学生に合否を共有し、次のステップの日程調整を行う"},
    "辞退確認":     {"icon": "⚠️",  "action_hint": "辞退意思を確認し、リスケ希望であれば日程を回収する"},
    "次回選考案内": {"icon": "➡️",  "action_hint": "学生に次回選考の詳細を共有し、日程調整を行う"},
    "その他":       {"icon": "📨", "action_hint": "メール内容を確認して適切に対応する"},
}

# ─── ② スペース正規化ヘルパー ──────────────────────────────────────────────────


def _normalize_name(name: str) -> str:
    """名前から半角・全角スペースを除去して正規化する。"""
    return name.replace(" ", "").replace("\u3000", "")


def _text_contains_student(text: str, normalized_name: str) -> bool:
    """テキスト内に📍+学生名（スペース正規化）が含まれるか確認する。"""
    for marker in ["📍", ":round_pushpin:"]:
        idx = text.find(marker)
        while idx != -1:
            after = text[idx + len(marker):]
            after_normalized = after.replace(" ", "").replace("\u3000", "")
            if after_normalized.startswith(normalized_name):
                return True
            idx = text.find(marker, idx + 1)
    return False


# ─── ③ スレッド未発見バッファ（2時間ごとにバッチDM） ───────────────────────────

_unfound_notifications: list = []
_last_unfound_dm_time = None  # datetime


def _add_unfound_notification(student_name: str, email_type: str, subject: str) -> None:
    """スレッド未発見の通知をバッファに積む。"""
    _unfound_notifications.append({
        "student_name": student_name,
        "email_type": email_type,
        "subject": subject,
        "detected_at": datetime.now(),
    })
    print(f"[企業メール通知] 未発見バッファ追加: {student_name} ({email_type})")


def _flush_unfound_notifications() -> None:
    """バッファ内の未発見通知をまとめて佐藤篤也へDM送信しバッファをクリアする。"""
    global _last_unfound_dm_time
    if not _unfound_notifications:
        return
    lines = [f"📋 *スレッド未発見メール（{len(_unfound_notifications)}件）*\n"]
    for n in _unfound_notifications:
        detected_str = n["detected_at"].strftime("%m/%d %H:%M")
        lines.append(
            f"• 👤 {n['student_name']} | {n['email_type']} | {detected_str}\n"
            f"  📧 {n['subject']}"
        )
    msg = "\n".join(lines)
    try:
        _slack_client.chat_postMessage(channel="U08SGGC5QR4", text=msg)
        print(f"[企業メール通知] 未発見通知バッチ送信完了: {len(_unfound_notifications)}件")
        _unfound_notifications.clear()
        _last_unfound_dm_time = datetime.now()
    except Exception as e:
        print(f"[企業メール通知] 未発見通知送信エラー: {e}")


def _extract_email_info(subject: str, body: str, sender: str):
    """Claude Haiku でメールを詳細解析し、Slackだけで内容把握できる情報を返す。"""
    prompt = f"""採用支援会社（キャリアアドバイザー）に届いた企業からのメールを詳細に解析してください。

差出人: {sender}
件名: {subject}
本文: {body[:1500]}

以下のJSON形式のみで返してください（余計な説明は不要）：
{{
  "student_name": "田中太郎",
  "company": "サイバーエージェント",
  "email_type": "合否連絡",
  "details": "【結果】書類選考通過\\n【次回選考】一次面接\\n【日時】2025年4月10日(木) 14:00〜15:00\\n【場所】渋谷オフィス or Zoom（URL別途送付）\\n【持ち物】履歴書・職務経歴書",
  "next_action": "田中さんに書類選考通過・一次面接の日程を転送し、参加可否と不明点がないか確認してください。",
  "student_message": "【ご連絡】サイバーエージェント様より書類選考通過のご連絡をいただきました！\\n\\n次回は一次面接となります。\\n■ 日時：4/10(木) 14:00〜15:00\\n■ 場所：渋谷オフィス\\n\\n参加できそうでしょうか？ご不明点があればいつでもご連絡ください。"
}}

フィールドの定義:
- student_name: メール内の学生名（敬称なし）。不明な場合は null
- company: 企業名（差出人のドメインからも推測可）
- email_type: 以下から最も近いものを1つ
  「欠席連絡」「日程確定」「合否連絡」「辞退確認」「次回選考案内」「その他」
- details: メールに書かれた重要情報をすべて箇条書きで整理。GmailなしでCAが内容を把握できるよう以下を含める
  - 合否・結果（通過/内定/お見送りなど）
  - 日時・場所・Zoom URL・オンライン会議リンク
  - 日程調整ツールのURL（調整さん・Calendly・SPIR・Doodleなど）がある場合はそのまま記載
  - 次回選考の種別・準備事項・持ち物
  - 期日・締め切り（回答期限、日程回答期限など）
  - 欠席・辞退の理由（記載があれば）
  - その他メールに記載の重要事項
  ※ 情報がない項目は省略。改行は\\nで表現。URL は省略せず完全な形で記載。
- next_action: CAが今すぐ取るべき具体的アクション（1〜2文）
  - 欠席連絡・辞退確認 → 辞退か否か確認し、リスケ希望なら候補日を回収
  - 日程確定 → 確定日時・場所・注意事項を学生に転送
  - 合否連絡・次回選考案内 → 結果を学生に共有し、次回に向けた日程・準備を調整
  - その他 → メール内容に応じた適切なアクション
- student_message: ⑥ LステップでそのままLINE送信できる文章（学生向け・敬語・コピペ用）
  - 企業名と結果を明確に記載、日時・場所など重要情報を漏れなく含める
  - お見送りの場合: ねぎらいの一言 + 今後のサポート継続の意思を添える
  - 改行は\\nで表現
- 採用・選考に無関係なメール（営業・ニュースレター等）の場合: {{"student_name": null}}"""

    body_data = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body_data,
        headers={
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = json.loads(r.read())["content"][0]["text"].strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1:
                return None
            info = json.loads(text[start:end])
            return info if info.get("student_name") else None
    except Exception as e:
        print(f"[企業メール通知] 解析エラー: {e}")
        return None


def _build_name_variants(student_name: str) -> list:
    """学生名のスペースバリエーション一覧を生成する。
    スペースなし・半角スペース・全角スペースを苗字2〜3文字区切りで生成。
    """
    normalized = _normalize_name(student_name)
    variants = list({normalized, student_name})
    for split in range(2, min(4, len(normalized))):
        head, tail = normalized[:split], normalized[split:]
        variants.append(head + " " + tail)       # 半角スペース
        variants.append(head + "\u3000" + tail)  # 全角スペース
    return variants


def _find_student_thread(student_name: str):
    """search.messages で「📍学生名」スレッドを検索する。
    C0A2YSANGKS → C0A4SJDDUV9 の順に検索し、最初に見つかったスレッドを返す。
    名前バリエーション: スペースなし・半角/全角スペースを苗字2〜3文字区切りで試行。
    """
    user_token = os.environ.get("SLACK_USER_TOKEN", "")
    if not user_token:
        return None

    normalized = _normalize_name(student_name)
    search_names = _build_name_variants(student_name)

    try:
        from slack_sdk import WebClient as _WC
        uc = _WC(token=user_token)
        seen_ts: set = set()

        # チャンネルを優先順に検索
        for channel_id in _STUDENT_THREAD_CHANNELS:
            for name in search_names:
                try:
                    # 📍絵文字はSlack検索インデックスで正常に扱われない場合があるため
                    # 名前のみで検索し、_text_contains_student で📍の有無を確認する
                    res = uc.search_messages(
                        query=f"{name} in:<#{channel_id}>",
                        count=20,
                        sort="timestamp",
                        sort_dir="desc",
                    )
                except Exception as e:
                    print(f"[Agent2] 検索エラー ({name} in {channel_id}): {e}")
                    continue
                matches = res.get("messages", {}).get("matches", [])
                print(f"[Agent2] 検索: '{name}' in {channel_id} → {len(matches)} 件")
                for m in matches:
                    ts = m.get("ts", "")
                    # スレッド返信の場合は thread_ts（親メッセージ）を使う
                    thread_ts = m.get("thread_ts", ts) or ts
                    if thread_ts in seen_ts:
                        continue
                    seen_ts.add(thread_ts)
                    if _text_contains_student(m.get("text", ""), normalized):
                        print(f"[Agent2] スレッド発見: 📍{student_name} in {channel_id}")
                        return {
                            "channel": m.get("channel", {}).get("id", channel_id),
                            "thread_ts": thread_ts,
                            "creator": m.get("user", ""),
                        }
        return None
    except Exception as e:
        print(f"[企業メール通知] Slackスレッド検索エラー: {e}")
        return None


def _post_email_notification(thread: dict, info: dict, raw_subject: str) -> None:
    """スレッドに企業メール通知とCAネクストアクションを投稿する。"""
    email_type = info.get("email_type", "その他")
    config = _EMAIL_TYPE_CONFIG.get(email_type, _EMAIL_TYPE_CONFIG["その他"])
    icon = config["icon"]

    details         = info.get("details", "")
    next_action     = info.get("next_action", config["action_hint"])
    student_message = info.get("student_message", "")

    # スレッドを立てた人 + 佐藤篤也 の両方をメンション（重複しない）
    _SATO_ID = "U08SGGC5QR4"
    creator = thread.get("creator", "")
    mention_ids = []
    if creator:
        mention_ids.append(creator)
    if _SATO_ID not in mention_ids:
        mention_ids.append(_SATO_ID)
    mention_line = " ".join(f"<@{uid}>" for uid in mention_ids) + "\n"

    line_section = (
        f"\n━━━━━━━━━━━━━━━━━━\n"
        f"📱 *Lステップ送信文（コピー用）*\n```\n{student_message}\n```"
    ) if student_message else ""

    msg = (
        f"{mention_line}"
        f"{icon} *企業からメールが届きました*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏢 企業: {info.get('company', '不明')}\n"
        f"👤 学生: {info.get('student_name', '不明')}\n"
        f"📋 種別: {email_type}\n"
        f"📧 件名: {raw_subject}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 *メール内容*\n{details}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ *CAネクストアクション*\n{next_action}"
        f"{line_section}"
    )
    try:
        # ユーザートークンで投稿（ボットが未参加チャンネルにも投稿可能）
        from slack_sdk import WebClient as _WC
        uc = _WC(token=os.environ.get("SLACK_USER_TOKEN", ""))
        uc.chat_postMessage(
            channel=thread["channel"],
            thread_ts=thread["thread_ts"],
            text=msg,
        )
        print(f"[企業メール通知] 投稿完了: {info.get('student_name')} / {email_type}")
    except Exception as e:
        print(f"[企業メール通知] 投稿エラー: {e}")


# ─── ⑦ 5エージェント分業システム ────────────────────────────────────────────────
#
#  Agent 1: Gmail検索エージェント   — 受信トレイ + 迷惑メールから未処理メールを収集
#  Agent 2: Slack通知エージェント   — スレッドを検索して担当CAへメンション投稿
#  Agent 3: 文章添削エージェント    — CA向けネクストアクション・学生向け文章を品質チェック
#  Agent 4: 漏れ通知エージェント    — スレッド未発見分を2時間ごとにバッチDM
#  Agent 5: Lステップ文章生成エージェント — 学生向けLINEメッセージをテンプレート生成
#  オーケストレーター              — 各エージェントをパイプライン形式で呼び出す
# ─────────────────────────────────────────────────────────────────────────────────


def agent1_gmail_fetch() -> list:
    """【Agent 1: Gmail検索エージェント】
    受信トレイ + 迷惑メールから直近2時間以内の未処理メールを取得して返す。
    戻り値: [{"id", "subject", "sender", "body"}, ...]
    """
    # 2時間以内 = 現在のUNIXタイムスタンプ - 7200秒
    two_hours_ago = int(time.time()) - 7200
    two_hour_query = _SELECTION_QUERY_BASE + f" after:{two_hours_ago}"

    emails = []
    for query in [two_hour_query, "in:spam " + two_hour_query]:
        try:
            res = _gmail.users().messages().list(
                userId="me", q=query, maxResults=10
            ).execute()
        except Exception as e:
            print(f"[Agent1] Gmail取得エラー: {e}")
            continue

        for msg in res.get("messages", []):
            email_id = msg["id"]
            if email_id in _processed_email_ids:
                continue
            _processed_email_ids.add(email_id)
            _save_processed_id(email_id)
            try:
                detail = _gmail.users().messages().get(
                    userId="me", id=email_id, format="full"
                ).execute()
                headers = detail.get("payload", {}).get("headers", [])
                sender = next((h["value"] for h in headers if h["name"] == "From"), "")
                # 除外対象の送信者は通知しない（クエリ除外の二重保険）
                if _is_excluded_sender(sender):
                    print(f"[Agent1] 除外対象の送信者をスキップ: {sender}")
                    continue
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
                # 返信・転送メール（Re:/Fw:）はスキップ
                if _is_reply_email(subject):
                    print(f"[Agent1] 返信メールをスキップ: {subject}")
                    continue
                # 社内システム自動通知（【選考連絡】等）はスキップ
                if _is_excluded_subject(subject):
                    print(f"[Agent1] 除外対象の件名をスキップ: {subject}")
                    continue
                emails.append({
                    "id": email_id,
                    "subject": subject,
                    "sender":  sender,
                    "body":    _decode_body(detail.get("payload", {})),
                })
            except Exception:
                continue
    return emails


def agent2_slack_notifier(info: dict, subject: str, sender: str = "") -> bool:
    """【Agent 2: Slack通知エージェント】
    📍学生名スレッドを検索して担当CAにメンション + メール内容を投稿する。
    スレッドが見つかった場合True、未発見の場合Falseを返す。
    """
    # 除外対象の送信者はSlack通知をブロック
    if sender and _is_excluded_sender(sender):
        print(f"[Agent2] 除外対象の送信者をブロック: {sender}")
        return True  # Trueを返してAgent4（漏れ通知）に流さない

    student_name = info.get("student_name", "")
    thread = _find_student_thread(student_name)
    if not thread:
        print(f"[Agent2] スレッド未発見: 📍{student_name}")
        return False
    _post_email_notification(thread, info, subject)
    return True


def agent3_proofreader(info: dict) -> dict:
    """【Agent 3: 文章添削エージェント】
    CAネクストアクションと学生向けメッセージをClaudeで品質チェック・添削する。
    Claude API利用不可の場合はinfoをそのまま返す（スキップ）。
    """
    try:
        prompt = (
            f"以下のCAアクションとLステップ文を確認し、より自然に添削してJSON形式で返してください。\n"
            f"企業:{info.get('company','')} / 学生:{info.get('student_name','')} / 種別:{info.get('email_type','')}\n"
            f"詳細: {info.get('details','')[:300]}\n"
            f"CAアクション現在: {info.get('next_action','')}\n"
            f"LINE文現在: {info.get('student_message','')}\n"
            f"JSON: {{\"next_action\": \"...\", \"student_message\": \"...\"}}"
        )
        body_data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 800,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body_data,
            headers={
                "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            text = json.loads(r.read())["content"][0]["text"].strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if start != -1:
                refined = json.loads(text[start:end])
                if refined.get("next_action"):
                    info["next_action"] = refined["next_action"]
                if refined.get("student_message"):
                    info["student_message"] = refined["student_message"]
                print(f"[Agent3] 添削完了: {info.get('student_name')}")
    except Exception as e:
        print(f"[Agent3] 添削スキップ: {e}")
    return info


def agent4_unfound_notifier(student_name: str, email_type: str, subject: str) -> None:
    """【Agent 4: 漏れ通知エージェント】
    スレッド未発見のメールをバッファに積む。2時間ごとにバッチDMで佐藤に通知。
    """
    _add_unfound_notification(student_name, email_type, subject)


def agent5_line_writer(company: str, email_type: str, details: str, student_name: str) -> str:
    """【Agent 5: Lステップ文章生成エージェント】
    Claude API不要のテンプレートで学生向けLINEメッセージを生成する。
    Claude抽出済みの場合はそちらを優先するため、フォールバック用として使用。
    """
    detail_summary = details[:200] if details else ""
    templates = {
        "合否連絡": (
            f"【ご連絡】{company}様より選考結果のご連絡をいただきました。\n\n"
            f"{detail_summary}\n\n"
            f"ご不明点があればいつでもご連絡ください。"
        ),
        "日程確定": (
            f"【日程確定】{company}様より面接日程が確定しましたのでご連絡します。\n\n"
            f"{detail_summary}\n\n"
            f"ご準備をよろしくお願いします！"
        ),
        "欠席連絡": (
            f"【ご確認】{company}様より欠席の連絡を受け取りました。\n"
            f"リスケをご希望の場合は、ご都合の良い候補日をお知らせください。"
        ),
        "辞退確認": (
            f"【ご確認】{company}様より辞退確認のご連絡をいただきました。\n"
            f"現在のお気持ちをお聞かせいただけますでしょうか。"
        ),
        "次回選考案内": (
            f"【次回選考】{company}様より次回選考のご案内が届きました。\n\n"
            f"{detail_summary}\n\n"
            f"ご参加可能でしょうか？"
        ),
    }
    return templates.get(
        email_type,
        f"【ご連絡】{company}様よりメールが届きました。\n\n{detail_summary}"
    )


def _run_email_pipeline(email_data: dict) -> None:
    """【オーケストレーター】5エージェントをパイプライン形式で実行する。
    Agent1(取得済み) → Claude解析 → Agent5(LINE文) → Agent3(添削) → Agent2(通知) / Agent4(漏れ)
    """
    subject = email_data["subject"]
    sender  = email_data["sender"]
    body    = email_data["body"]

    # circus-group.jp からのメールは最終段階でも除外（二重保険）
    if "circus-group.jp" in sender:
        print(f"[pipeline] circus-group.jp をスキップ: {sender}")
        return

    # 返信メール（件名が Re: で始まる）はスキップ
    if _re.match(r"^Re\s*:", subject, _re.IGNORECASE):
        print(f"[pipeline] 返信メールをスキップ: {subject}")
        return

    # Claude でメール解析（student_message も生成）
    info = _extract_email_info(subject, body, sender)
    if not info:
        return  # 選考無関係メール → スキップ

    student_name = info.get("student_name", "")
    email_type   = info.get("email_type", "その他")
    print(f"[pipeline] Agent1→解析完了: {student_name} / {email_type}")

    # Agent 5: student_messageがなければテンプレートで補完
    if not info.get("student_message"):
        info["student_message"] = agent5_line_writer(
            info.get("company", ""),
            email_type,
            info.get("details", ""),
            student_name,
        )
        print(f"[Agent5] LINE文をテンプレートで生成: {student_name}")

    # Agent 3: 文章添削（Claude API有効時のみ実行）
    info = agent3_proofreader(info)

    # Agent 2: Slack通知
    success = agent2_slack_notifier(info, subject, sender)

    if not success:
        # Agent 4: 漏れ通知バッファに積む
        agent4_unfound_notifier(student_name, email_type, subject)


def _check_new_selection_emails() -> None:
    """Agent1でGmailを取得し、各メールをパイプラインで処理する。"""
    emails = agent1_gmail_fetch()
    for email_data in emails:
        try:
            _run_email_pipeline(email_data)
        except Exception as e:
            print(f"[pipeline] エラー: {e}")


def _gmail_selection_polling() -> None:
    """1分ごとにGmailをチェックするバックグラウンドスレッド。"""
    print("[企業メール通知] Gmail監視を開始しました（1分間隔）")
    # 再起動時の重複通知防止: ファイルから処理済みIDを復元
    _load_processed_ids_from_file()
    # 起動時の既存メールはスキップ（通知しない）— 2時間以内の既存メールを対象
    try:
        two_hours_ago = int(time.time()) - 7200
        init_query = _SELECTION_QUERY_BASE + f" after:{two_hours_ago}"
        for init_q in [init_query, "in:spam " + init_query]:
            res = _gmail.users().messages().list(
                userId="me", q=init_q, maxResults=50
            ).execute()
            for m in res.get("messages", []):
                _processed_email_ids.add(m["id"])
        print(f"[企業メール通知] 既存メール {len(_processed_email_ids)} 件をスキップ済みとしてマーク（直近2時間）")
    except Exception as e:
        print(f"[企業メール通知] 初期化エラー: {e}")

    while True:
        time.sleep(60)
        try:
            _check_new_selection_emails()
        except Exception as e:
            print(f"[企業メール通知] ポーリングエラー: {e}")

        # ③ 2時間ごとに未発見通知をバッチ送信
        now = datetime.now()
        if _unfound_notifications and (
            _last_unfound_dm_time is None
            or (now - _last_unfound_dm_time).total_seconds() >= 7200
        ):
            try:
                _flush_unfound_notifications()
            except Exception as e:
                print(f"[企業メール通知] 未発見バッチ送信エラー: {e}")


# ─── 起動 ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    LINE_PORT = int(os.environ.get("LINE_WEBHOOK_PORT", "5000"))

    # LINE が有効な場合のみ Flask + ngrok を起動
    if _LINE_ENABLED:
        threading.Thread(target=_start_flask, args=(LINE_PORT,), daemon=True).start()

    if _LINE_ENABLED and _NGROK_OK:
        tunnel = _ngrok.connect(LINE_PORT)
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = "https://" + public_url[7:]
        print(f"\n📱 LINE Webhook URL: {public_url}/callback")
        print("   ↑ この URL を LINE Developers の Webhook URL に設定してください\n")
    elif _LINE_ENABLED:
        print(f"\n📱 LINE Webhook: localhost:{LINE_PORT}/callback")
        print("   ※ 外部公開には ngrok などが必要です\n")

    # 株価監視スケジューラを起動
    if _STOCK_OK:
        start_stock_scheduler(_gmail)

    # Gmail 選考結果監視スレッドを起動
    threading.Thread(target=_gmail_selection_polling, daemon=True).start()

    enabled = ", ".join(_integrations)
    print(f"🤖 Slack AI Agent を起動しています... 連携: {enabled} (停止: Ctrl+C)")
    SocketModeHandler(_slack_app, os.environ["SLACK_APP_TOKEN"]).start()
