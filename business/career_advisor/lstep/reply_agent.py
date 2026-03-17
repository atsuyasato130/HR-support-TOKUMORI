#!/usr/bin/env python3
"""
Lステップ 返信エージェント

messages.json に保存された未返信LINEメッセージを一覧表示し、
Claude が返信案を生成 → クリップボードにコピー → Lステップのトーク画面に貼り付けて送信。

使い方:
  python3 reply_agent.py

事前準備:
  webhook_server.py を起動してメッセージを受信しておく
"""

import os
import json
import subprocess
import anthropic
from datetime import datetime
from dotenv import load_dotenv

BASE = os.path.dirname(__file__)
load_dotenv(os.path.join(BASE, "../config/.env"))

MESSAGES_FILE = os.path.join(BASE, "messages.json")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


# ─── メッセージ管理 ────────────────────────────────────────

def load_messages() -> list:
    if not os.path.exists(MESSAGES_FILE):
        return []
    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_messages(messages: list):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


# ─── AI 返信生成 ──────────────────────────────────────────

def generate_reply(user_text: str, instruction: str = "") -> str:
    prompt = f"""LINEで届いたメッセージへの返信を作成してください。

--- 受信メッセージ ---
{user_text}
---"""
    if instruction:
        prompt += f"\n\n返信の方針・補足: {instruction}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "あなたはLINEの返信アシスタントです。"
            "届いたメッセージに対して、自然で丁寧な返信文を日本語で作成してください。"
            "返信文のみを出力し、説明や前置きは不要です。"
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ─── クリップボードコピー ──────────────────────────────────

def copy_to_clipboard(text: str) -> bool:
    """テキストをMacのクリップボードにコピーする（pbcopy使用）。"""
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"\n[ERROR] クリップボードコピー失敗: {e}")
        return False


# ─── 表示ヘルパー ─────────────────────────────────────────

def display_message(m: dict):
    print(f"\n{'='*60}")
    print(f"  送信者  : {m.get('displayName') or m['userId']}")
    print(f"  受信日時: {m['timestamp']}")
    print(f"{'='*60}")
    print(m["text"])
    print(f"{'='*60}")


# ─── メイン CLI ────────────────────────────────────────────

def main():
    print("Lステップ 返信エージェントを起動中...\n")

    messages = load_messages()
    pending = [m for m in messages if not m.get("replied")]

    if not pending:
        print("未返信メッセージはありません。")
        return

    print(f"未返信メッセージ: {len(pending)} 件\n")
    for i, m in enumerate(pending):
        name = m.get("displayName") or m["userId"]
        text_preview = m["text"][:50] + ("..." if len(m["text"]) > 50 else "")
        print(f"  [{i}] {m['timestamp']} | {name}: {text_preview}")

    # 返信するメッセージを選択
    while True:
        choice = input("\n返信するメッセージ番号を入力（q で終了）: ").strip()
        if choice.lower() == "q":
            print("終了します。")
            return
        if choice.isdigit() and 0 <= int(choice) < len(pending):
            selected = pending[int(choice)]
            break
        print("無効な入力です。")

    display_message(selected)

    # 返信方針の入力（任意）
    instruction = input("\n返信の方針・補足（空欄でも OK）: ").strip()

    print("\nClaude が返信案を生成中...")
    reply = generate_reply(selected["text"], instruction)

    # 確認・編集ループ
    while True:
        print(f"\n{'─'*60}")
        print("【返信案】")
        print(f"{'─'*60}")
        print(reply)
        print(f"{'─'*60}")

        action = input(
            "\n操作を選択してください:\n"
            "  [c] クリップボードにコピー\n"
            "  [e] 手動で編集\n"
            "  [r] Claude に再生成させる\n"
            "  [q] スキップして終了\n"
            "> "
        ).strip().lower()

        if action == "c":
            if copy_to_clipboard(reply):
                print("\nクリップボードにコピーしました。")
                print("Lステップ管理画面 > トーク > 該当ユーザーを開いて貼り付けてください。")
                sent = input("\n送信できたら [y]、やり直す場合は [n]: ").strip().lower()
                if sent == "y":
                    for m in messages:
                        if m["id"] == selected["id"]:
                            m["replied"] = True
                            m["reply_text"] = reply
                            m["replied_at"] = datetime.now().isoformat()
                    save_messages(messages)
                    print("返信済みとしてマークしました。")
                    break

        elif action == "e":
            print("返信文を入力してください（入力完了後、空行を2回押してください）:")
            lines = []
            empty_count = 0
            while empty_count < 2:
                line = input()
                if line == "":
                    empty_count += 1
                else:
                    empty_count = 0
                lines.append(line)
            reply = "\n".join(lines[:-2])  # 末尾の空行2つを除去

        elif action == "r":
            new_instruction = input("再生成の方針を入力: ").strip()
            print("\nClaude が再生成中...")
            reply = generate_reply(selected["text"], new_instruction or instruction)

        elif action == "q":
            print("スキップしました。")
            break

        else:
            print("無効な入力です。")


if __name__ == "__main__":
    main()
