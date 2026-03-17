#!/usr/bin/env python3
"""
Lステップ Webhook サーバー

L-stepのWebhook転送機能からメッセージを受信してmessages.jsonに保存する。

起動方法:
  python3 webhook_server.py

ngrok で外部公開（別ターミナルで）:
  ngrok http 5000
  → 発行されたURL（例: https://xxxx.ngrok-free.app/webhook）を
    Lステップ管理画面のWebhook転送URLに設定する
"""

import os
import json
import hmac
import hashlib
import base64
from datetime import datetime
from flask import Flask, request, abort
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../config/.env"))

app = Flask(__name__)

MESSAGES_FILE = os.path.join(os.path.dirname(__file__), "messages.json")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")


# ─── メッセージ管理 ────────────────────────────────────────

def load_messages() -> list:
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_messages(messages: list):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


# ─── 署名検証 ─────────────────────────────────────────────

def verify_signature(body: bytes, signature: str) -> bool:
    """LINE Webhook 署名を検証する（LINE_CHANNEL_SECRET が設定されている場合のみ）"""
    if not LINE_CHANNEL_SECRET:
        return True
    digest = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


# ─── Webhook エンドポイント ────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data()

    if LINE_CHANNEL_SECRET and not verify_signature(body, signature):
        print("[WARN] 署名検証失敗 - 不正なリクエスト")
        abort(403)

    try:
        data = json.loads(body.decode("utf-8"))
    except Exception:
        abort(400)

    messages = load_messages()
    new_count = 0

    for event in data.get("events", []):
        # テキストメッセージのみ処理
        if event.get("type") != "message":
            continue
        msg = event.get("message", {})
        if msg.get("type") != "text":
            continue

        source = event.get("source", {})
        user_id = source.get("userId", "")
        ts = event.get("timestamp", 0)

        entry = {
            "id": f"{user_id}_{ts}",
            "userId": user_id,
            "displayName": "",  # L-stepのWebhookにはdisplayNameが含まれない
            "text": msg.get("text", ""),
            "timestamp": datetime.fromtimestamp(ts / 1000).isoformat(),
            "replied": False,
            "reply_text": None,
            "replied_at": None,
        }

        # 重複チェック（同じIDが既に存在する場合はスキップ）
        if any(m["id"] == entry["id"] for m in messages):
            continue

        messages.append(entry)
        new_count += 1
        print(f"[受信] {entry['timestamp']} | {user_id}: {entry['text'][:80]}")

    if new_count > 0:
        save_messages(messages)
        print(f"  → {new_count} 件保存しました。")

    return "OK", 200


@app.route("/health", methods=["GET"])
def health():
    """動作確認用エンドポイント"""
    count = len([m for m in load_messages() if not m.get("replied")])
    return {"status": "ok", "unreplied": count}, 200


# ─── 起動 ─────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Lステップ Webhook サーバー起動")
    print("  受信エンドポイント: http://localhost:5000/webhook")
    print("  ヘルスチェック    : http://localhost:5000/health")
    print("=" * 50)
    print()
    if not LINE_CHANNEL_SECRET:
        print("[INFO] LINE_CHANNEL_SECRET 未設定 → 署名検証スキップ")
    app.run(host="0.0.0.0", port=5000, debug=False)
