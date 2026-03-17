#!/usr/bin/env python3
"""
Slack Reply Agent
- DM・メンションを確認して返信案を生成
- 確認後に送信する CLI ツール
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../config/.env"))

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import anthropic


# ─── Slack クライアント ────────────────────────────────────

_client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
_bot_user_id = None


def get_bot_user_id() -> str:
    global _bot_user_id
    if not _bot_user_id:
        res = _client.auth_test()
        _bot_user_id = res["user_id"]
    return _bot_user_id


def get_username(user_id: str, cache: dict = {}) -> str:
    if user_id not in cache:
        try:
            info = _client.users_info(user=user_id)
            cache[user_id] = info["user"].get("real_name") or info["user"].get("name", user_id)
        except Exception:
            cache[user_id] = user_id
    return cache[user_id]


# ─── メッセージ取得 ────────────────────────────────────────

def get_dm_messages(limit: int = 30) -> list[dict]:
    """DM（IM）チャンネルの未返信メッセージを取得"""
    bot_id = get_bot_user_id()
    messages = []

    try:
        # DM チャンネル一覧
        res = _client.conversations_list(types="im", limit=50)
        for ch in res.get("channels", []):
            ch_id = ch["id"]
            user_id = ch.get("user", "")
            if user_id == bot_id:
                continue

            # 最近のメッセージを取得
            history = _client.conversations_history(channel=ch_id, limit=10)
            msgs = history.get("messages", [])
            if not msgs:
                continue

            # 最新メッセージがこちらからの送信でなければ返信候補
            latest = msgs[0]
            if latest.get("bot_id") or latest.get("user") == bot_id:
                continue

            ts = float(latest.get("ts", 0))
            dt = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M")
            username = get_username(user_id)

            messages.append({
                "type": "dm",
                "channel_id": ch_id,
                "channel_name": f"DM: {username}",
                "user_id": user_id,
                "username": username,
                "ts": latest["ts"],
                "thread_ts": latest.get("thread_ts", latest["ts"]),
                "text": latest.get("text", ""),
                "date": dt,
                "history": msgs[:5],
            })

    except SlackApiError as e:
        print(f"Slack API エラー: {e}")

    return messages


def get_mention_messages(limit: int = 20) -> list[dict]:
    """@メンションされたメッセージを取得"""
    bot_id = get_bot_user_id()
    messages = []

    try:
        # アクティビティフィード（mentions）は search.messages API で取得
        res = _client.search_messages(
            query=f"<@{bot_id}>",
            count=limit,
            sort="timestamp",
            sort_dir="desc",
        )
        matches = res.get("messages", {}).get("matches", [])
        for m in matches:
            channel = m.get("channel", {})
            ts = float(m.get("ts", 0))
            dt = datetime.fromtimestamp(ts).strftime("%m/%d %H:%M")
            username = get_username(m.get("user", ""))

            messages.append({
                "type": "mention",
                "channel_id": channel.get("id", ""),
                "channel_name": f"#{channel.get('name', '不明')}",
                "user_id": m.get("user", ""),
                "username": username,
                "ts": m["ts"],
                "thread_ts": m.get("thread_ts", m["ts"]),
                "text": m.get("text", ""),
                "date": dt,
                "history": [],
            })

    except SlackApiError as e:
        # search API は特定のプランでのみ使用可能
        print(f"メンション検索スキップ（{e.response['error']}）")

    return messages


# ─── 返信案生成 ───────────────────────────────────────────

def generate_slack_reply(msg: dict, instruction: str = "") -> str:
    client = anthropic.Anthropic()

    # 会話履歴を整形
    history_text = ""
    if msg.get("history"):
        lines = []
        for m in reversed(msg["history"]):
            user = get_username(m.get("user", "bot")) if m.get("user") else "bot"
            lines.append(f"{user}: {m.get('text', '')}")
        history_text = "\n".join(lines)

    prompt = f"""以下の Slack メッセージへの返信を作成してください。

チャンネル: {msg['channel_name']}
送信者: {msg['username']}
日時: {msg['date']}

--- 会話履歴 ---
{history_text or msg['text']}
---
"""
    if instruction:
        prompt += f"\n返信の方針: {instruction}"

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        system=(
            "あなたはプロフェッショナルなビジネスアシスタントです。"
            "Slack メッセージへの自然で簡潔な返信を日本語で作成してください。"
            "返信文のみを出力し、説明や前置きは不要です。"
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


# ─── 返信送信 ─────────────────────────────────────────────

def send_slack_reply(msg: dict, reply_text: str):
    _client.chat_postMessage(
        channel=msg["channel_id"],
        text=reply_text,
        thread_ts=msg["thread_ts"] if msg["type"] == "mention" else None,
    )


# ─── メイン CLI ───────────────────────────────────────────

def main():
    print("Slack Reply Agent を起動中...\n")

    print("DM・メンションを取得中...")
    dm_msgs = get_dm_messages(limit=20)
    mention_msgs = get_mention_messages(limit=10)

    all_msgs = dm_msgs + mention_msgs

    if not all_msgs:
        print("返信が必要なメッセージはありません。")
        return

    print(f"\n要確認メッセージ: {len(all_msgs)} 件\n")
    for i, m in enumerate(all_msgs):
        tag = "【DM】" if m["type"] == "dm" else "【メンション】"
        print(f"[{i}] {tag} {m['channel_name']}  {m['date']}")
        print(f"     {m['username']}: {m['text'][:80]}")
        print()

    # 返信するメッセージを選択
    while True:
        choice = input("返信するメッセージの番号（q で終了）: ").strip()
        if choice.lower() == "q":
            return
        if choice.isdigit() and 0 <= int(choice) < len(all_msgs):
            selected = all_msgs[int(choice)]
            break
        print("無効な入力です。")

    print(f"\n--- {selected['channel_name']} ---")
    if selected.get("history"):
        for m in reversed(selected["history"]):
            user = get_username(m.get("user", "bot")) if m.get("user") else "bot"
            print(f"{user}: {m.get('text', '')}")
    print()

    instruction = input("返信の方針（空欄でも OK）: ").strip()

    print("\nClaude が返信案を生成中...")
    reply = generate_slack_reply(selected, instruction)

    print(f"\n{'─'*50}")
    print("【返信案】")
    print(f"{'─'*50}")
    print(reply)
    print(f"{'─'*50}")

    while True:
        action = input(
            "\n操作:\n  [s] 送信\n  [e] 編集\n  [r] 再生成\n  [q] キャンセル\n> "
        ).strip().lower()

        if action == "s":
            send_slack_reply(selected, reply)
            print("\n返信を送信しました！")
            break
        elif action == "e":
            print("返信文を入力（空行2回で確定）:")
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
            print(f"\n【編集後】\n{reply}")
        elif action == "r":
            new_instruction = input("再生成の方針: ").strip()
            print("\n再生成中...")
            reply = generate_slack_reply(selected, new_instruction or instruction)
            print(f"\n{'─'*50}\n{reply}\n{'─'*50}")
        elif action == "q":
            print("キャンセルしました。")
            break


if __name__ == "__main__":
    main()
