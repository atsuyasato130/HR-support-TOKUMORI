#!/usr/bin/env python3
"""
特定のメールを1回だけパイプライン処理するスクリプト。
久米川美空さんの説明会メールなど、ボットが取り逃したメールを手動処理する。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# slack_bot のヘルパー関数を使う（Bolt app は起動しない）
import slack_bot as bot

def find_and_process_email(keyword: str):
    """Gmail から keyword を含むメールを検索して pipeline 処理する。"""
    # 直近24時間を検索
    import time
    since = int(time.time()) - 86400
    query = f"subject:{keyword} after:{since}"
    print(f"[手動処理] Gmail検索: {query}")

    try:
        res = bot._gmail.users().messages().list(
            userId="me", q=query, maxResults=5
        ).execute()
    except Exception as e:
        print(f"[手動処理] Gmail検索エラー: {e}")
        return

    messages = res.get("messages", [])
    if not messages:
        print(f"[手動処理] '{keyword}' に一致するメールが見つかりませんでした")
        return

    print(f"[手動処理] {len(messages)} 件ヒット")
    for msg in messages:
        email_id = msg["id"]
        try:
            detail = bot._gmail.users().messages().get(
                userId="me", id=email_id, format="full"
            ).execute()
            headers = detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            sender  = next((h["value"] for h in headers if h["name"] == "From"), "")
            body    = bot._decode_body(detail.get("payload", {}))
            print(f"  件名: {subject}")
            print(f"  差出人: {sender}")
            yn = input("  このメールを処理しますか？ [y/n]: ").strip().lower()
            if yn != "y":
                continue
            email_data = {"id": email_id, "subject": subject, "sender": sender, "body": body}
            bot._run_email_pipeline(email_data)
            # 処理済みIDをファイルに保存（ボットの次回起動時に重複しないよう）
            bot._save_processed_id(email_id)
            print(f"[手動処理] 完了: {subject}")
        except Exception as e:
            print(f"[手動処理] エラー: {e}")

if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "説明会"
    find_and_process_email(keyword)
