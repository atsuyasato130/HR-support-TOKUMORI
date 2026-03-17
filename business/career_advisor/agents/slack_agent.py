#!/usr/bin/env python3
"""
Slackエージェント

機能:
  - 選考進捗Slack共有（Salesforce pipeline → Slackスレッド投稿）
  - 将来: 任意チャンネルへのメッセージ送信、スレッド検索

使い方:
  python3 slack_agent.py
  from agents.slack_agent import run
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

SF_RECORDTYPE_SHINSOTSU = "0122w000001Ry2hAAC"

_STUDENT_THREAD_CHANNELS = ["C0A2YSANGKS", "C0A4SJDDUV9"]

_STATUS_EMOJI: dict = {
    "002": "🎤", "003": "🎤", "004": "❌", "005": "📝",
    "006": "❌", "007": "❌", "008": "📅", "009": "✅",
    "010": "❌", "011": "❌", "012": "📅", "013": "✅",
    "014": "❌", "015": "❌", "016": "📅", "017": "✅",
    "018": "❌", "019": "❌", "020": "📅", "021": "✅",
    "022": "❌", "023": "❌", "024": "🎉", "025": "🏆",
    "026": "💔", "027": "💔",
}

_ACTIVE_CODES = {"002", "003", "005", "008", "009", "012", "013", "016", "017", "020", "021"}
_OFFER_CODES  = {"024", "025"}
_NG_CODES     = {"004", "006", "007", "010", "011", "014", "015", "018", "019", "022", "023", "026", "027"}


# ──────────────────────────────────────────────
# Salesforce
# ──────────────────────────────────────────────

def _get_sf():
    from simple_salesforce import Salesforce  # type: ignore
    return Salesforce(
        username=os.environ["SF_USERNAME"],
        password=os.environ["SF_PASSWORD"],
        security_token=os.environ["SF_SECURITY_TOKEN"],
        domain=os.environ.get("SF_DOMAIN", "login"),
    )


def _search_student(sf, full_name: str) -> dict | None:
    if not full_name:
        return None
    parts = re.split(r"[\s　]+", full_name.strip())
    name_keyword = "%".join(p for p in parts if p)
    try:
        soql = (
            f"SELECT Id, Name, PersonEmail, Status__pc, Phase__pc "
            f"FROM Account WHERE Name LIKE '%{name_keyword}%' "
            f"AND RecordTypeId = '{SF_RECORDTYPE_SHINSOTSU}' LIMIT 3"
        )
        result = sf.query(soql)
        records = result.get("records", [])
        if not records:
            return None
        if len(records) == 1:
            r = records[0]
        else:
            print(f"\n  {len(records)}件のレコードが見つかりました:")
            for i, r in enumerate(records, 1):
                print(f"  [{i}] {r['Name']} | {r.get('PersonEmail', '─')} | 状況: {r.get('Phase__pc', '─')}")
            while True:
                sel = input("  番号を選択（0=キャンセル）> ").strip()
                if sel == "0":
                    return None
                if sel.isdigit() and 1 <= int(sel) <= len(records):
                    r = records[int(sel) - 1]
                    break
                print("  有効な番号を入力してください。")
        return {"id": r["Id"], "name": r["Name"]}
    except Exception as e:
        print(f"  [検索エラー] {e}")
        return None


def _fetch_pipelines(sf, account_id: str) -> list:
    soql = (
        f"SELECT Id, Name, Status__c, Company__c, Company__r.Name, "
        f"Sanka_Check__c, First__c, Second__c, Third__c, Last__c "
        f"FROM pipeline__c WHERE JobApplicant__c = '{account_id}'"
    )
    result = sf.query(soql)
    return result.get("records", [])


# ──────────────────────────────────────────────
# メッセージ整形
# ──────────────────────────────────────────────

def _status_code(status: str) -> str:
    return status[:3] if status else ""


def _status_emoji(status: str) -> str:
    code = _status_code(status)
    return _STATUS_EMOJI.get(code, "📌")


def _format_date(date_str: str | None) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%m/%d")
    except Exception:
        return date_str[:10]


def _relevant_date(pipeline: dict, status: str) -> str:
    code = _status_code(status)
    if code in {"008", "009", "010", "011"}:
        return _format_date(pipeline.get("First__c"))
    elif code in {"012", "013", "014", "015"}:
        return _format_date(pipeline.get("Second__c"))
    elif code in {"016", "017", "018", "019"}:
        return _format_date(pipeline.get("Third__c"))
    elif code in {"020", "021", "022", "023", "024", "025"}:
        return _format_date(pipeline.get("Last__c"))
    return ""


def format_progress_message(student_name: str, pipelines: list) -> str:
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    lines = [
        f"📊 *選考進捗レポート — {student_name} さん*",
        f"_更新: {now}_",
        "",
    ]

    if not pipelines:
        lines.append("選考記録がありません。")
        return "\n".join(lines)

    active_count = offer_count = ng_count = 0

    for p in pipelines:
        company = (p.get("Company__r") or {}).get("Name") or p.get("Name", "─")
        status = p.get("Status__c") or ""
        emoji = _status_emoji(status)
        status_label = status[4:] if len(status) > 4 else status
        date_str = _relevant_date(p, status)
        date_part = f" ({date_str})" if date_str else ""
        lines.append(f"🏢 *{company}*　{emoji} {status_label}{date_part}")

        code = _status_code(status)
        if code in _OFFER_CODES:
            offer_count += 1
        elif code in _NG_CODES:
            ng_count += 1
        elif code in _ACTIVE_CODES:
            active_count += 1

    total = len(pipelines)
    lines.append("")
    lines.append(
        f"合計: {total}社（活動中: {active_count}社 / 内定: {offer_count}社 / NG/辞退: {ng_count}社）"
    )
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Slack スレッド検索
# ──────────────────────────────────────────────

def _normalize_name(name: str) -> str:
    return name.replace(" ", "").replace("\u3000", "")


def _text_contains_student(text: str, normalized_name: str) -> bool:
    for marker in ["📍", ":round_pushpin:"]:
        idx = text.find(marker)
        while idx != -1:
            after = text[idx + len(marker):]
            after_normalized = after.replace(" ", "").replace("\u3000", "")
            if after_normalized.startswith(normalized_name):
                return True
            idx = text.find(marker, idx + 1)
    return False


def _build_name_variants(student_name: str) -> list:
    normalized = _normalize_name(student_name)
    variants = list({normalized, student_name})
    for split in range(2, min(4, len(normalized))):
        head, tail = normalized[:split], normalized[split:]
        variants.append(head + " " + tail)
        variants.append(head + "\u3000" + tail)
    return variants


def find_student_thread(student_name: str) -> dict | None:
    user_token = os.environ.get("SLACK_USER_TOKEN", "")
    if not user_token:
        print("  [警告] SLACK_USER_TOKEN が設定されていません。スレッド検索をスキップします。")
        return None

    normalized = _normalize_name(student_name)
    search_names = _build_name_variants(student_name)

    try:
        from slack_sdk import WebClient
        uc = WebClient(token=user_token)
        seen_ts: set = set()

        for channel_id in _STUDENT_THREAD_CHANNELS:
            for name in search_names:
                try:
                    res = uc.search_messages(
                        query=f"{name} in:<#{channel_id}>",
                        count=20,
                        sort="timestamp",
                        sort_dir="desc",
                    )
                except Exception as e:
                    print(f"  [検索エラー] {name} in {channel_id}: {e}")
                    continue
                matches = res.get("messages", {}).get("matches", [])
                for m in matches:
                    ts = m.get("ts", "")
                    thread_ts = m.get("thread_ts", ts) or ts
                    if thread_ts in seen_ts:
                        continue
                    seen_ts.add(thread_ts)
                    if _text_contains_student(m.get("text", ""), normalized):
                        print(f"  スレッド発見: 📍{student_name} in {channel_id}")
                        return {
                            "channel": m.get("channel", {}).get("id", channel_id),
                            "thread_ts": thread_ts,
                        }
        return None
    except Exception as e:
        print(f"  [Slack検索エラー] {e}")
        return None


def post_to_slack(thread: dict, message: str) -> None:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    bot_token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not bot_token:
        raise RuntimeError("SLACK_BOT_TOKEN が設定されていません。")

    client = WebClient(token=bot_token)
    try:
        client.chat_postMessage(
            channel=thread["channel"],
            text=message,
            thread_ts=thread.get("thread_ts"),
        )
    except SlackApiError as e:
        raise RuntimeError(f"Slack投稿エラー: {e}") from e


def send_message(channel: str, message: str, thread_ts: str | None = None) -> None:
    """任意チャンネルにメッセージを送信"""
    thread = {"channel": channel, "thread_ts": thread_ts}
    post_to_slack(thread, message)


# ──────────────────────────────────────────────
# 選考進捗共有モード
# ──────────────────────────────────────────────

def _run_progress_share():
    print("\n選考進捗Slack共有を開始します。\n")

    student_name = input("学生名を入力してください > ").strip()
    if not student_name:
        print("名前が入力されていません。終了します。")
        return

    print("\nSalesforceに接続中...")
    try:
        sf = _get_sf()
    except Exception as e:
        print(f"[エラー] Salesforce接続失敗: {e}")
        return

    print(f"  '{student_name}' を検索中...")
    student = _search_student(sf, student_name)
    if not student:
        print("  学生レコードが見つかりませんでした。")
        return

    print(f"  見つかりました: {student['name']} (ID: {student['id']})")

    print("\n選考進捗を取得中...")
    pipelines = _fetch_pipelines(sf, student["id"])
    print(f"  {len(pipelines)}件の選考レコードを取得しました。")

    message = format_progress_message(student["name"], pipelines)

    print(f"\n{'─'*60}")
    print("【投稿プレビュー】")
    print(f"{'─'*60}")
    print(message)
    print(f"{'─'*60}")

    print("\nSlackスレッドを検索中...")
    thread = find_student_thread(student["name"])

    if not thread:
        print("  スレッドが見つかりませんでした。")
        channel_id = input("  チャンネルID（スキップは空欄）> ").strip()
        if channel_id:
            thread_ts = input("  スレッドts（なければ空欄）> ").strip() or None
            thread = {"channel": channel_id, "thread_ts": thread_ts}
        else:
            print("キャンセルしました。")
            return

    while True:
        action = input(
            "\n操作:\n  [s] 送信\n  [r] メッセージを再確認\n  [q] キャンセル\n> "
        ).strip().lower()

        if action == "s":
            try:
                post_to_slack(thread, message)
                print("\n選考進捗をSlackに投稿しました！")
            except Exception as e:
                print(f"\n[エラー] {e}")
            break
        elif action == "r":
            print(f"\n{'─'*60}")
            print(message)
            print(f"{'─'*60}")
        elif action == "q":
            print("キャンセルしました。")
            break
        else:
            print("無効な入力です。")


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'progress' | None（メニュー表示）

    将来追加予定:
      - 'send': 任意チャンネルへのメッセージ送信
      - 'search': スレッド検索
      - 'report': 週次レポートの自動投稿
    """
    if mode == "progress":
        _run_progress_share()
        return

    print("\n" + "=" * 55)
    print("  Slackエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. 選考進捗をSlackスレッドに投稿")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_progress_share()
            break
        elif choice == "q":
            break
        else:
            print("1 または q を入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
