#!/usr/bin/env python3
"""
MCP Server — Salesforce + Notion
Claude Code から直接 Salesforce / Notion を操作できるようにする MCP サーバー。
Python 3.9 対応 (mcp ライブラリ不要・JSON-RPC over stdio を手実装)

起動方法 (Claude Code が自動実行):
  claude mcp add salesforce-notion -- /usr/bin/python3 /path/to/mcp_server.py
"""

import json
import os
import sys

# .env を手動で読み込む（dotenv を使わずに）
_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/.env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ─── Salesforce ───────────────────────────────────────────────────────────────

def _get_sf():
    from simple_salesforce import Salesforce  # type: ignore
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


def _sf_search(soql_query: str) -> str:
    try:
        sf = _get_sf()
        result = sf.query(soql_query)
        records = result.get("records", [])
        if not records:
            return "該当レコードがありません。"
        rows = [
            " | ".join(f"{k}: {v}" for k, v in r.items() if k != "attributes")
            for r in records
        ]
        return f"{len(records)} 件:\n" + "\n".join(rows)
    except Exception as exc:
        return f"Salesforce エラー: {exc}"


def _sf_update(object_type: str, record_id: str, fields_json: str) -> str:
    try:
        sf = _get_sf()
        fields = json.loads(fields_json)
        getattr(sf, object_type).update(record_id, fields)
        return f"{object_type} (ID: {record_id}) を更新しました。変更内容: {fields}"
    except Exception as exc:
        return f"Salesforce エラー: {exc}"


def _sf_create(object_type: str, fields_json: str) -> str:
    try:
        sf = _get_sf()
        fields = json.loads(fields_json)
        result = getattr(sf, object_type).create(fields)
        return f"{object_type} を作成しました。新規 ID: {result['id']}"
    except Exception as exc:
        return f"Salesforce エラー: {exc}"


def _sf_log_meeting(
    account_id: str,
    student_name: str,
    meeting_date: str,
    summary: str,
    next_actions: str = "",
    duration: str = "",
    advisor_name: str = "",
    is_second_or_later: bool = False,
) -> str:
    """面談活動記録（Task）をSalesforceに作成する"""
    try:
        sf = _get_sf()
        prefix = "2回目以降面談" if is_second_or_later else "面談"
        subject = f"{prefix} - {student_name} ({meeting_date})"

        desc_parts = []
        if is_second_or_later:
            desc_parts.append("【2回目以降の面談】")
        if summary:
            desc_parts.append(f"【面談内容】\n{summary}")
        if next_actions:
            desc_parts.append(f"【次のアクション】\n{next_actions}")
        if duration:
            desc_parts.append(f"【面談時間】{duration}")
        if advisor_name:
            desc_parts.append(f"【担当CA】{advisor_name}")

        fields = {
            "Subject": subject,
            "Description": "\n\n".join(desc_parts),
            "ActivityDate": meeting_date,
            "Status": "Completed",
            "WhatId": account_id,
        }
        result = sf.Task.create(fields)
        return f"活動記録（Task）を作成しました。Task ID: {result['id']}  件名: {subject}"
    except Exception as exc:
        return f"Salesforce Task作成エラー: {exc}"


def _sf_summary(object_type: str, conditions: str = "") -> str:
    try:
        sf = _get_sf()
        where = f" WHERE {conditions}" if conditions else ""
        result = sf.query(f"SELECT COUNT(Id) cnt FROM {object_type}{where}")
        count = result["records"][0]["cnt"]
        cond = f"（条件: {conditions}）" if conditions else ""
        return f"{object_type} の件数{cond}: {count} 件"
    except Exception as exc:
        return f"Salesforce エラー: {exc}"


# ─── Notion ───────────────────────────────────────────────────────────────────

def _get_notion():
    from notion_client import Client  # type: ignore
    return Client(auth=os.environ.get("NOTION_API_KEY", ""))


def _prop_to_str(prop: dict) -> str:
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
    if pt in ("url", "email", "phone_number"):
        return prop.get(pt, "") or ""
    if pt == "people":
        return ", ".join(p.get("name", "") for p in prop.get("people", []))
    return ""


def _notion_search(query: str, filter_type: str = "page") -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。.env に設定してください。"
    try:
        notion = _get_notion()
        params: dict = {"query": query, "page_size": 10}
        if filter_type in ("page", "database"):
            params["filter"] = {"value": filter_type, "property": "object"}
        res = notion.search(**params)
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
                title = "".join(t["plain_text"] for t in r.get("title", []))
                rows.append(f"[DB] {title or '（タイトルなし）'}  ID: {r['id']}")
        return "\n".join(rows)
    except Exception as exc:
        return f"Notion エラー: {exc}"


def _notion_read_db(database_id: str, filter_json: str = "{}") -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        import httpx as _httpx
        headers = {
            "Authorization": f"Bearer {os.environ['NOTION_API_KEY']}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        payload: dict = {"page_size": 30}
        filt = json.loads(filter_json)
        if filt:
            payload["filter"] = filt
        r = _httpx.post(
            f"https://api.notion.so/v1/databases/{database_id}/query",
            headers=headers, json=payload, timeout=15
        )
        r.raise_for_status()
        pages = r.json().get("results", [])
        if not pages:
            return "レコードが見つかりませんでした。"
        rows = []
        for page in pages:
            cells = [
                f"{k}: {_prop_to_str(v)}"
                for k, v in page.get("properties", {}).items()
                if _prop_to_str(v)
            ]
            rows.append(f"ID:{page['id']}  " + " | ".join(cells))
        return f"{len(pages)} 件:\n" + "\n".join(rows)
    except Exception as exc:
        return f"Notion エラー: {exc}"


def _notion_read_page(page_id: str) -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        notion = _get_notion()
        page = notion.pages.retrieve(page_id=page_id)
        lines = []
        # すべてのプロパティを表示
        for k, v in page.get("properties", {}).items():
            val = _prop_to_str(v)
            if val:
                lines.append(f"{k}: {val}")
        # ブロック本文
        blocks = notion.blocks.children.list(block_id=page_id, page_size=100)
        for b in blocks.get("results", []):
            bt = b.get("type", "")
            rich = b.get(bt, {}).get("rich_text", [])
            text = "".join(r.get("plain_text", "") for r in rich)
            if text:
                lines.append(text)
        return "\n".join(lines)[:4000] if lines else "（内容なし）"
    except Exception as exc:
        return f"Notion エラー: {exc}"


def _notion_update_page(page_id: str, properties_json: str) -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        notion = _get_notion()
        props = json.loads(properties_json)
        page = notion.pages.update(page_id=page_id, properties=props)
        return f"Notion ページを更新しました。\nURL: {page.get('url', '')}\nID: {page['id']}"
    except Exception as exc:
        return f"Notion エラー: {exc}"


def _notion_archive_page(page_id: str) -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        notion = _get_notion()
        notion.pages.update(page_id=page_id, archived=True)
        return f"Notion ページをアーカイブ（削除）しました。ID: {page_id}"
    except Exception as exc:
        return f"Notion アーカイブエラー: {exc}"


def _notion_create_page(database_id: str, properties_json: str, content: str = "") -> str:
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        notion = _get_notion()
        props = json.loads(properties_json)
        body: dict = {"parent": {"database_id": database_id}, "properties": props}
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
        page = notion.pages.create(**body)
        return f"Notion ページを作成しました。\nURL: {page.get('url', '')}\nID: {page['id']}"
    except Exception as exc:
        return f"Notion エラー: {exc}"


def _notion_create_child_page(parent_page_id: str, title: str, blocks_json: str = "[]") -> str:
    """通常ページの子ページとして議事録等を作成する。blocks_json は Notion ブロック配列の JSON。"""
    if not os.environ.get("NOTION_API_KEY"):
        return "NOTION_API_KEY が未設定です。"
    try:
        notion = _get_notion()
        blocks = json.loads(blocks_json)
        body: dict = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            },
        }
        # Notion API: max 100 children per request; split if needed
        first_batch = blocks[:100]
        if first_batch:
            body["children"] = first_batch
        page = notion.pages.create(**body)
        page_id = page["id"]
        # Append remaining blocks
        remaining = blocks[100:]
        if remaining:
            import httpx
            token = os.environ["NOTION_API_KEY"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            }
            for i in range(0, len(remaining), 100):
                batch = remaining[i:i + 100]
                httpx.patch(
                    f"https://api.notion.com/v1/blocks/{page_id}/children",
                    headers=headers,
                    json={"children": batch},
                    timeout=30,
                )
        return f"Notion 子ページを作成しました。\nURL: {page.get('url', '')}\nID: {page_id}"
    except Exception as exc:
        return f"Notion エラー: {exc}"


# ─── Slack ────────────────────────────────────────────────────────────────────

def _slack_send(channel: str, text: str) -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return "SLACK_BOT_TOKEN が未設定です。"
    try:
        from slack_sdk import WebClient  # type: ignore
        client = WebClient(token=token)
        res = client.chat_postMessage(channel=channel, text=text)
        return f"Slack に送信しました。チャンネル: {channel}  ts: {res['ts']}"
    except Exception as exc:
        return f"Slack エラー: {exc}"


def _slack_channels() -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return "SLACK_BOT_TOKEN が未設定です。"
    try:
        from slack_sdk import WebClient  # type: ignore
        client = WebClient(token=token)
        res = client.conversations_list(limit=50, types="public_channel,private_channel")
        channels = res.get("channels", [])
        if not channels:
            return "チャンネルが見つかりませんでした。"
        rows = [f"#{c['name']}  ID:{c['id']}  メンバー数:{c.get('num_members', '?')}" for c in channels]
        return f"{len(channels)} 件:\n" + "\n".join(rows)
    except Exception as exc:
        return f"Slack エラー: {exc}"


def _slack_messages(channel: str, limit: int = 20) -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return "SLACK_BOT_TOKEN が未設定です。"
    try:
        from slack_sdk import WebClient  # type: ignore
        client = WebClient(token=token)
        res = client.conversations_history(channel=channel, limit=limit)
        messages = res.get("messages", [])
        if not messages:
            return "メッセージがありませんでした。"
        rows = [f"[{m.get('ts', '')}] {m.get('text', '')}" for m in messages]
        return f"{len(messages)} 件:\n" + "\n".join(rows)
    except Exception as exc:
        return f"Slack エラー: {exc}"


# ─── Google (Gmail) ────────────────────────────────────────────────────────────

def _get_gmail_service():
    import pickle
    from google.oauth2.credentials import Credentials  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
    from googleapiclient.discovery import build  # type: ignore

    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/token.json")
    creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/credentials.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            return None, "Google OAuth トークンが無効です。再認証が必要です。"
    return build("gmail", "v1", credentials=creds), None


def _gmail_send(to: str, subject: str, body: str) -> str:
    try:
        import base64
        from email.mime.text import MIMEText
        service, err = _get_gmail_service()
        if err:
            return err
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"メールを送信しました。宛先: {to}  件名: {subject}"
    except Exception as exc:
        return f"Gmail エラー: {exc}"


def _gmail_read(max_results: int = 10, query: str = "") -> str:
    try:
        import base64
        service, err = _get_gmail_service()
        if err:
            return err
        params = {"userId": "me", "maxResults": max_results}
        if query:
            params["q"] = query
        res = service.users().messages().list(**params).execute()
        messages = res.get("messages", [])
        if not messages:
            return "メールが見つかりませんでした。"
        rows = []
        for m in messages[:max_results]:
            detail = service.users().messages().get(userId="me", id=m["id"], format="metadata",
                                                    metadataHeaders=["Subject", "From", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
            rows.append(f"[{headers.get('Date', '')}] From: {headers.get('From', '')}  件名: {headers.get('Subject', '')}")
        return f"{len(rows)} 件:\n" + "\n".join(rows)
    except Exception as exc:
        return f"Gmail エラー: {exc}"


# ─── Google Docs / Sheets ─────────────────────────────────────────────────────

def _get_google_creds():
    from google.oauth2.credentials import Credentials  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore

    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../config/token.json")
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            return None, "Google OAuth トークンが無効です。再認証が必要です。"
    return creds, None


def _gdocs_read(doc_id: str) -> str:
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=doc_id).execute()
        title = doc.get("title", "（タイトルなし）")
        lines = []
        for elem in doc.get("body", {}).get("content", []):
            para = elem.get("paragraph")
            if para:
                text = "".join(
                    r.get("textRun", {}).get("content", "")
                    for r in para.get("elements", [])
                )
                if text.strip():
                    lines.append(text.rstrip("\n"))
            table = elem.get("table")
            if table:
                for row in table.get("tableRows", []):
                    cells = []
                    for cell in row.get("tableCells", []):
                        cell_text = ""
                        for c in cell.get("content", []):
                            p = c.get("paragraph")
                            if p:
                                cell_text += "".join(
                                    r.get("textRun", {}).get("content", "")
                                    for r in p.get("elements", [])
                                ).strip()
                        cells.append(cell_text)
                    lines.append(" | ".join(cells))
        return f"タイトル: {title}\n\n" + "\n".join(lines)
    except Exception as exc:
        return f"Google Docs エラー: {exc}"


def _gsheets_create(title: str, sheets_json: str) -> str:
    """sheets_json: JSON array of {name: str, rows: [[cell, ...]]}"""
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        sheets_data = json.loads(sheets_json)
        service = build("sheets", "v4", credentials=creds)
        body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": s["name"]}} for s in sheets_data],
        }
        spreadsheet = service.spreadsheets().create(body=body).execute()
        ss_id = spreadsheet["spreadsheetId"]
        ss_url = spreadsheet["spreadsheetUrl"]
        for sheet in sheets_data:
            rows = sheet.get("rows", [])
            if not rows:
                continue
            range_name = f"'{sheet['name']}'!A1"
            service.spreadsheets().values().update(
                spreadsheetId=ss_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": rows},
            ).execute()
        return f"スプレッドシートを作成しました。\nURL: {ss_url}\nID: {ss_id}"
    except Exception as exc:
        return f"Google Sheets エラー: {exc}"


def _gsheets_search_student(spreadsheet_id: str, name: str, meeting_date: str = "") -> str:
    """Lステップスプレッドシートから学生を氏名（またはカナ）で検索し個人情報を返す"""
    try:
        _utils = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../career_advisor/utils")
        if _utils not in sys.path:
            sys.path.insert(0, _utils)
        from sheets_client import search_student_in_sheet  # type: ignore

        row = search_student_in_sheet(
            spreadsheet_id, name,
            meeting_date=meeting_date or None,
        )

        # カナでフォールバック検索（引数がカナ表記の場合も対応）
        if not row:
            row = search_student_in_sheet(
                spreadsheet_id, name,
                name_col_candidates=["フリガナを教えてください", "フリガナ", "氏名（カナ）", "カナ氏名"],
                meeting_date=meeting_date or None,
            )

        if not row:
            return f"「{name}」はスプレッドシートに見つかりませんでした。"

        # 重要フィールドを先頭に表示
        priority = [
            "お名前を教えてください",
            "フリガナを教えてください",
            "電話番号",
            "メールアドレス",
            "生年月日を教えてください",
            "大学名を教えてください",
            "学部を教えてください",
            "学科を教えてください",
            "高校名を教えてください",
            "卒業年度を教えてください",
            "性別を教えてください",
            "在住エリアを教えてください",
            "回答日時",
        ]
        lines = []
        shown = set()
        for key in priority:
            val = row.get(key, "")
            if val:
                lines.append(f"{key}: {val}")
            shown.add(key)
        for k, v in row.items():
            if k not in shown and v:
                lines.append(f"{k}: {v}")

        return "\n".join(lines) if lines else "シートにデータが見つかりませんでした。"
    except EnvironmentError as exc:
        return f"Google認証エラー: {exc}"
    except Exception as exc:
        return f"スプレッドシート検索エラー: {exc}"


def _gsheets_read(spreadsheet_id: str, sheet_name: str, range_a1: str) -> str:
    """指定範囲のセル値を2次元JSON配列で返す"""
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("sheets", "v4", credentials=creds)
        range_name = f"'{sheet_name}'!{range_a1}" if sheet_name else range_a1
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
        ).execute()
        values = result.get("values", [])
        return json.dumps(values, ensure_ascii=False)
    except Exception as exc:
        return f"Google Sheets 読み取りエラー: {exc}"


def _gdocs_create(title: str, content: str) -> str:
    """Google ドキュメントを新規作成してテキストを挿入する"""
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().create(body={"title": title}).execute()
        doc_id = doc["documentId"]
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
        if content:
            service.documents().batchUpdate(
                documentId=doc_id,
                body={"requests": [{"insertText": {"location": {"index": 1}, "text": content}}]},
            ).execute()
        return f"Google ドキュメントを作成しました。\nURL: {doc_url}\nID: {doc_id}"
    except Exception as exc:
        return f"Google Docs 作成エラー: {exc}"


def _gsheets_format(spreadsheet_id: str, sheet_name: str, requests_json: str) -> str:
    """シート名からシートIDを自動解決してbatchUpdateでフォーマットを適用する。
    requests_json内の __SHEET_ID__ は実際のシートIDに置換される。"""
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("sheets", "v4", credentials=creds)
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        for s in spreadsheet.get("sheets", []):
            if s["properties"]["title"] == sheet_name:
                sheet_id = s["properties"]["sheetId"]
                break
        if sheet_id is None:
            return f"シート '{sheet_name}' が見つかりません"
        requests_str = requests_json.replace("__SHEET_ID__", str(sheet_id))
        requests = json.loads(requests_str)
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()
        return f"フォーマットを適用しました。シート: {sheet_name} (ID: {sheet_id})"
    except Exception as exc:
        return f"Google Sheets フォーマットエラー: {exc}"


def _gsheets_add_tab(spreadsheet_id: str, tab_name: str) -> str:
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("sheets", "v4", credentials=creds)
        body = {"requests": [{"addSheet": {"properties": {"title": tab_name}}}]}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
        return f"タブを作成しました: {tab_name}"
    except Exception as exc:
        if "already exists" in str(exc):
            return f"タブ既存: {tab_name}"
        return f"Google Sheets タブ作成エラー: {exc}"


def _gsheets_update(spreadsheet_id: str, sheet_name: str, range_a1: str, values_json: str) -> str:
    try:
        from googleapiclient.discovery import build  # type: ignore
        creds, err = _get_google_creds()
        if err:
            return err
        service = build("sheets", "v4", credentials=creds)
        values = json.loads(values_json)
        range_name = f"'{sheet_name}'!{range_a1}"
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            body={"values": values},
        ).execute()
        return f"スプレッドシートを更新しました。シート: {sheet_name}  範囲: {range_a1}"
    except Exception as exc:
        return f"Google Sheets エラー: {exc}"


# ─── ツール定義 ───────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "search_salesforce",
        "description": "Salesforce の顧客・リード・商談・ケースを SOQL で検索する。例: SELECT Id, Name, Email FROM Contact WHERE Name LIKE '%田中%'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "soql_query": {"type": "string", "description": "SOQL クエリ文字列"}
            },
            "required": ["soql_query"],
        },
    },
    {
        "name": "update_salesforce_record",
        "description": "Salesforce の既存レコード（商談・連絡先・リードなど）を更新する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "description": "例: Opportunity, Contact, Lead, Account"},
                "record_id": {"type": "string", "description": "18桁の Salesforce レコード ID"},
                "fields_json": {"type": "string", "description": "更新フィールドの JSON。例: '{\"StageName\": \"Closed Won\", \"CloseDate\": \"2025-03-31\"}'"},
            },
            "required": ["object_type", "record_id", "fields_json"],
        },
    },
    {
        "name": "create_salesforce_record",
        "description": "Salesforce に新規レコードを作成する（リード・連絡先・商談など）",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "description": "例: Lead, Contact, Opportunity, Account"},
                "fields_json": {"type": "string", "description": "フィールドの JSON。例: '{\"LastName\": \"田中\", \"Company\": \"株式会社テスト\", \"Email\": \"tanaka@test.com\"}'"},
            },
            "required": ["object_type", "fields_json"],
        },
    },
    {
        "name": "log_sf_meeting",
        "description": "Salesforceに面談活動記録（Task）を作成する。SF登録・更新後に必ず呼び出すこと。初回面談・2回目以降どちらにも対応。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "学生のSalesforce Account ID（18桁）"},
                "student_name": {"type": "string", "description": "学生氏名（例: 戀塚 美咲）"},
                "meeting_date": {"type": "string", "description": "面談日（YYYY-MM-DD形式）"},
                "summary": {"type": "string", "description": "面談内容の要約（200字程度）"},
                "next_actions": {"type": "string", "description": "次のアクション（箇条書き、改行区切り）"},
                "duration": {"type": "string", "description": "面談時間（例: 60分）"},
                "advisor_name": {"type": "string", "description": "担当CA名"},
                "is_second_or_later": {"type": "boolean", "description": "2回目以降の面談の場合 true（デフォルト: false）"},
            },
            "required": ["account_id", "student_name", "meeting_date", "summary"],
        },
    },
    {
        "name": "get_salesforce_summary",
        "description": "Salesforce のオブジェクト件数を集計する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "description": "例: Opportunity, Lead, Contact"},
                "conditions": {"type": "string", "description": "WHERE 句（省略可）。例: \"StageName = 'Closed Won' AND CloseDate = THIS_MONTH\""},
            },
            "required": ["object_type"],
        },
    },
    {
        "name": "search_notion",
        "description": "Notion 全体を検索してページやデータベースを探す",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "検索キーワード"},
                "filter_type": {"type": "string", "description": "'page' または 'database'（省略可）", "enum": ["page", "database"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_notion_database",
        "description": "Notion データベースのレコード一覧を取得する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "Notion データベース ID (search_notion で取得)"},
                "filter_json": {"type": "string", "description": "フィルター条件の JSON（省略可）"},
            },
            "required": ["database_id"],
        },
    },
    {
        "name": "read_notion_page",
        "description": "Notion ページの内容（テキスト）を読み取る",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Notion ページ ID"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "create_notion_child_page",
        "description": "通常の Notion ページ配下に子ページ（議事録など）を作成する。blocks_json に Notion ブロック配列（JSON）を渡すとリッチな書式で作成できる。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "parent_page_id": {"type": "string", "description": "親ページ ID"},
                "title": {"type": "string", "description": "ページタイトル"},
                "blocks_json": {"type": "string", "description": "Notion ブロック配列の JSON（省略時は空ページ）"},
            },
            "required": ["parent_page_id", "title"],
        },
    },
    {
        "name": "create_notion_page",
        "description": "Notion データベースに新しいページ（レコード）を作成する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string", "description": "親データベース ID"},
                "properties_json": {"type": "string", "description": "プロパティの JSON。例: '{\"名前\": {\"title\": [{\"text\": {\"content\": \"田中太郎\"}}]}}'"},
                "content": {"type": "string", "description": "ページ本文テキスト（省略可）"},
            },
            "required": ["database_id", "properties_json"],
        },
    },
    {
        "name": "archive_notion_page",
        "description": "Notion のページをアーカイブ（削除）する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "アーカイブする Notion ページ ID"},
            },
            "required": ["page_id"],
        },
    },
    {
        "name": "update_notion_page",
        "description": "Notion の既存ページのプロパティを更新する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "更新対象の Notion ページ ID"},
                "properties_json": {"type": "string", "description": "更新するプロパティの JSON。例: '{\"事業概要\": {\"rich_text\": [{\"text\": {\"content\": \"新しい概要\"}}]}}'"},
            },
            "required": ["page_id", "properties_json"],
        },
    },
    {
        "name": "send_slack_message",
        "description": "Slack の指定チャンネルにメッセージを送信する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "チャンネル名（#general）またはチャンネル ID"},
                "text": {"type": "string", "description": "送信するメッセージ本文"},
            },
            "required": ["channel", "text"],
        },
    },
    {
        "name": "get_slack_channels",
        "description": "Slack のチャンネル一覧を取得する",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_slack_messages",
        "description": "Slack チャンネルの最近のメッセージを取得する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "description": "チャンネル ID（get_slack_channels で取得）"},
                "limit": {"type": "integer", "description": "取得件数（デフォルト: 20）"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "read_google_doc",
        "description": "Google Docs のドキュメントを読み取りテキストで返す",
        "inputSchema": {
            "type": "object",
            "properties": {
                "doc_id": {"type": "string", "description": "Google Doc の ID（URLの /d/ 以降の部分）"},
            },
            "required": ["doc_id"],
        },
    },
    {
        "name": "search_student_in_spreadsheet",
        "description": "Lステップスプレッドシートから学生を氏名で検索し、電話番号・メールアドレス・生年月日・フリガナなどの個人情報を返す。SF新規登録前に必ず呼び出して情報を補完すること。スプレッドシートID: 1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "スプレッドシートID（省略時はLステップ標準シートを使用）"},
                "name": {"type": "string", "description": "検索する学生の氏名（フルネーム、漢字またはカナ）"},
                "meeting_date": {"type": "string", "description": "面談日（YYYY-MM-DD形式、複数ヒット時の絞り込みに使用、省略可）"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "read_google_spreadsheet",
        "description": "Google スプレッドシートの指定範囲を読み取り、2次元JSON配列で返す。シート名と範囲（A1記法）を指定する。例: sheet_name='Sheet1', range_a1='A1:Z100'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "スプレッドシート ID（URLの /d/ 以降の部分）"},
                "sheet_name": {"type": "string", "description": "シート名（タブ名）。省略時は先頭シート"},
                "range_a1": {"type": "string", "description": "A1記法の範囲。例: A1:Z100、J1:Z200"},
            },
            "required": ["spreadsheet_id", "range_a1"],
        },
    },
    {
        "name": "create_google_spreadsheet",
        "description": "Google スプレッドシートを新規作成し複数シートにデータを書き込む",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "スプレッドシートのタイトル"},
                "sheets_json": {
                    "type": "string",
                    "description": 'JSON配列。例: [{"name":"Sheet1","rows":[["A","B"],["1","2"]]}]',
                },
            },
            "required": ["title", "sheets_json"],
        },
    },
    {
        "name": "format_google_spreadsheet",
        "description": "Google スプレッドシートにbatchUpdateでフォーマット（背景色・文字色・罫線・列幅・マージ等）を適用する。requests_json内の __SHEET_ID__ は自動でシートIDに置換される。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "スプレッドシート ID"},
                "sheet_name": {"type": "string", "description": "対象シート名（タブ名）"},
                "requests_json": {"type": "string", "description": "Google Sheets batchUpdate requests の JSON配列。シートIDは __SHEET_ID__ と書けば自動置換される。"},
            },
            "required": ["spreadsheet_id", "sheet_name", "requests_json"],
        },
    },
    {
        "name": "create_google_doc",
        "description": "Google ドキュメントを新規作成してテキストを書き込む",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "ドキュメントのタイトル"},
                "content": {"type": "string", "description": "本文テキスト（改行は\\nで表現）"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "add_sheet_tab",
        "description": "既存の Google スプレッドシートに新しいタブ（シート）を追加する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "スプレッドシート ID"},
                "tab_name": {"type": "string", "description": "作成するタブ名"},
            },
            "required": ["spreadsheet_id", "tab_name"],
        },
    },
    {
        "name": "update_google_spreadsheet",
        "description": "既存の Google スプレッドシートのセルを更新する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "スプレッドシート ID"},
                "sheet_name": {"type": "string", "description": "シート名"},
                "range_a1": {"type": "string", "description": "A1 記法の範囲。例: A1"},
                "values_json": {"type": "string", "description": 'JSON 2次元配列。例: [["A","B"],["1","2"]]'},
            },
            "required": ["spreadsheet_id", "sheet_name", "range_a1", "values_json"],
        },
    },
    {
        "name": "send_gmail",
        "description": "Gmail でメールを送信する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "宛先メールアドレス"},
                "subject": {"type": "string", "description": "件名"},
                "body": {"type": "string", "description": "本文"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "read_gmail",
        "description": "Gmail の受信トレイを取得する",
        "inputSchema": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "取得件数（デフォルト: 10）"},
                "query": {"type": "string", "description": "検索クエリ（例: 'from:test@example.com is:unread'）"},
            },
            "required": [],
        },
    },
]


def _handle_tool(name: str, args: dict) -> str:
    if name == "search_salesforce":
        return _sf_search(args["soql_query"])
    elif name == "update_salesforce_record":
        return _sf_update(args["object_type"], args["record_id"], args["fields_json"])
    elif name == "create_salesforce_record":
        return _sf_create(args["object_type"], args["fields_json"])
    elif name == "log_sf_meeting":
        return _sf_log_meeting(
            args["account_id"],
            args["student_name"],
            args["meeting_date"],
            args["summary"],
            args.get("next_actions", ""),
            args.get("duration", ""),
            args.get("advisor_name", ""),
            args.get("is_second_or_later", False),
        )
    elif name == "get_salesforce_summary":
        return _sf_summary(args["object_type"], args.get("conditions", ""))
    elif name == "search_notion":
        return _notion_search(args["query"], args.get("filter_type", "page"))
    elif name == "read_notion_database":
        return _notion_read_db(args["database_id"], args.get("filter_json", "{}"))
    elif name == "read_notion_page":
        return _notion_read_page(args["page_id"])
    elif name == "create_notion_child_page":
        return _notion_create_child_page(
            args["parent_page_id"],
            args["title"],
            args.get("blocks_json", "[]"),
        )
    elif name == "create_notion_page":
        return _notion_create_page(
            args["database_id"],
            args["properties_json"],
            args.get("content", ""),
        )
    elif name == "archive_notion_page":
        return _notion_archive_page(args["page_id"])
    elif name == "update_notion_page":
        return _notion_update_page(args["page_id"], args["properties_json"])
    elif name == "send_slack_message":
        return _slack_send(args["channel"], args["text"])
    elif name == "get_slack_channels":
        return _slack_channels()
    elif name == "get_slack_messages":
        return _slack_messages(args["channel"], args.get("limit", 20))
    elif name == "search_student_in_spreadsheet":
        ss_id = args.get("spreadsheet_id") or "1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc"
        return _gsheets_search_student(ss_id, args["name"], args.get("meeting_date", ""))
    elif name == "format_google_spreadsheet":
        return _gsheets_format(args["spreadsheet_id"], args["sheet_name"], args["requests_json"])
    elif name == "create_google_doc":
        return _gdocs_create(args["title"], args.get("content", ""))
    elif name == "add_sheet_tab":
        return _gsheets_add_tab(args["spreadsheet_id"], args["tab_name"])
    elif name == "read_google_spreadsheet":
        return _gsheets_read(args["spreadsheet_id"], args.get("sheet_name", ""), args["range_a1"])
    elif name == "read_google_doc":
        return _gdocs_read(args["doc_id"])
    elif name == "create_google_spreadsheet":
        return _gsheets_create(args["title"], args["sheets_json"])
    elif name == "update_google_spreadsheet":
        return _gsheets_update(args["spreadsheet_id"], args["sheet_name"], args["range_a1"], args["values_json"])
    elif name == "send_gmail":
        return _gmail_send(args["to"], args["subject"], args["body"])
    elif name == "read_gmail":
        return _gmail_read(args.get("max_results", 10), args.get("query", ""))
    else:
        return f"Unknown tool: {name}"


# ─── MCP JSON-RPC ループ ────────────────────────────────────────────────────────

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {})

        # Notification（id なし）は返答不要
        if req_id is None:
            continue

        if method == "initialize":
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "hr-support-mcp", "version": "2.0.0"},
                },
            })

        elif method == "tools/list":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            try:
                result_text = _handle_tool(tool_name, tool_args)
            except Exception as exc:
                result_text = f"エラー: {exc}"
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": result_text}]},
            })

        elif method == "ping":
            _send({"jsonrpc": "2.0", "id": req_id, "result": {}})

        else:
            _send({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            })


if __name__ == "__main__":
    main()
