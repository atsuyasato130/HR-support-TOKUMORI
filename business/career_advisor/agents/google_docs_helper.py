#!/usr/bin/env python3
"""
Google Docs 保存ヘルパー

ES添削・面接対策の結果を指定のGoogleドキュメントに追記する。
ドキュメントIDは career_advisor/gdoc_id.json に保存し、2回目以降は同じドキュメントに追記する。
"""

import os
import json
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 既存トークンのパス（email_agent と共用）
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CREDS_PATH = os.path.join(_BASE, "slack_ai_agent", "credentials.json")
TOKEN_PATH = os.path.join(_BASE, "slack_ai_agent", "token.json")

# ドキュメントIDの保存先
DOC_ID_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gdoc_id.json")
DOC_TITLE = "ES・面接対策 添削記録"


def _docs_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("docs", "v1", credentials=creds)


def get_or_create_doc() -> str:
    """ドキュメントIDをキャッシュから読み込むか、新規作成して返す。"""
    if os.path.exists(DOC_ID_FILE):
        with open(DOC_ID_FILE) as f:
            data = json.load(f)
        doc_id = data.get("doc_id", "")
        if doc_id:
            return doc_id

    # 新規ドキュメント作成
    service = _docs_service()
    doc = service.documents().create(body={"title": DOC_TITLE}).execute()
    doc_id = doc["documentId"]

    with open(DOC_ID_FILE, "w") as f:
        json.dump({"doc_id": doc_id}, f, ensure_ascii=False, indent=2)

    print(f"\n📄 Googleドキュメントを新規作成しました")
    print(f"   https://docs.google.com/document/d/{doc_id}/edit")
    return doc_id


def append_to_doc(doc_id: str, header: str, es_text: str, feedback: str):
    """
    ドキュメント末尾にセクションを追記する。

    Args:
        doc_id:   GoogleドキュメントのID
        header:   セクション見出し（例: "ES添削 | 自己PR | ○○会社"）
        es_text:  入力されたES本文
        feedback: Claudeのフィードバック全文
    """
    service = _docs_service()

    # ドキュメント末尾インデックスを取得
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    separator = "━" * 48

    content = (
        f"\n\n{separator}\n"
        f"【{header}】  {now}\n"
        f"{separator}\n\n"
        f"＜ES・回答本文＞\n{es_text}\n\n"
        f"＜フィードバック＞\n{feedback}\n"
    )

    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": content,
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()


def save_result(header: str, es_text: str, feedback: str):
    """添削結果をGoogleドキュメントに保存する（呼び出し用ショートカット）。"""
    try:
        doc_id = get_or_create_doc()
        append_to_doc(doc_id, header, es_text, feedback)
        print(f"\n✅ Googleドキュメントに保存しました")
        print(f"   https://docs.google.com/document/d/{doc_id}/edit\n")
    except Exception as e:
        print(f"\n⚠️  Googleドキュメントへの保存に失敗しました: {e}\n")


def _drive_service():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    return build("drive", "v3", credentials=creds)


def share_doc(doc_id: str, email: str) -> None:
    """
    GoogleドキュメントをメールアドレスにWriterとして共有する。

    Args:
        doc_id : 共有するドキュメントのID
        email  : 共有先Googleアカウントのメールアドレス
    """
    service = _drive_service()
    service.permissions().create(
        fileId=doc_id,
        body={
            "type": "user",
            "role": "writer",
            "emailAddress": email,
        },
        sendNotificationEmail=True,
    ).execute()


def create_student_feedback_doc(
    student_name: str,
    category: str,
    es_text: str,
    feedback: str,
    share_email: str = "",
) -> str:
    """
    学生1人分の添削フィードバックをまとめた新規Googleドキュメントを作成する。

    Args:
        student_name : 学生名（ドキュメントタイトルに使用）
        category     : カテゴリ（例: ガクチカ / 志望動機）
        es_text      : 添削対象の元テキスト
        feedback     : 添削フィードバック全文
        share_email  : 共有先メールアドレス（指定時はDrive権限を付与）

    Returns:
        作成したドキュメントのURL
    """
    service = _docs_service()

    now = datetime.now().strftime("%Y-%m-%d")
    title = f"【添削】{student_name}_{category}_{now}"

    # ドキュメント新規作成
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]

    separator = "━" * 48
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = (
        f"{title}\n"
        f"作成日時: {created_at}\n\n"
        f"{separator}\n"
        f"■ 元のテキスト\n"
        f"{separator}\n\n"
        f"{es_text}\n\n"
        f"{separator}\n"
        f"■ フィードバック\n"
        f"{separator}\n\n"
        f"{feedback}\n"
    )

    end_index = doc["body"]["content"][-1]["endIndex"] - 1
    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": content,
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    # メールアドレスが指定されていれば権限付与
    if share_email:
        try:
            share_doc(doc_id, share_email)
        except Exception as e:
            print(f"⚠️  共有に失敗しました（ドキュメントは作成済み）: {e}")

    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return url
