#!/usr/bin/env python3
"""
キャリアアドバイザー支援システム — オーケストレーター

使い方:
  python3 main.py

機能:
  自然言語で指示するだけで、Claudeが適切なエージェントを自動選択・実行。
  複合タスク（例: tldv → SF登録 → Slack共有）も自動で連鎖実行。
  /エージェント名 で直接起動も可能。
"""

from __future__ import annotations

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))

import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../config/.env"))

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ──────────────────────────────────────────────
# エージェントレジストリ
# （エージェント追加時はここに1行追記するだけ）
# ──────────────────────────────────────────────

AGENT_REGISTRY = {
    "coaching": {
        "name": "学生コーチング",
        "desc": "ES・面接対策 / 就活軸深掘り",
        "module": "coaching_agent",
        "keywords": [
            "es", "面接", "ガクチカ", "自己pr", "志望動機", "挫折", "就活軸", "コーチング",
            "壁打ち", "es対策", "面接対策", "強み", "ストーリー",
        ],
    },
    "salesforce": {
        "name": "Salesforce",
        "desc": "tldv議事録 → SF登録・更新",
        "module": "salesforce_agent",
        "keywords": [
            "salesforce", "sf", "セールスフォース", "登録", "記録", "更新", "account",
            "面談記録", "sf登録",
        ],
    },
    "notion": {
        "name": "Notion",
        "desc": "企業DB・企業紹介文生成",
        "module": "notion_agent",
        "keywords": [
            "notion", "ノーション", "企業紹介文", "企業紹介", "企業db", "企業データベース",
            "紹介文", "おすすめポイント",
        ],
    },
    "slack": {
        "name": "Slack",
        "desc": "選考進捗Slack共有",
        "module": "slack_agent",
        "keywords": [
            "slack", "スラック", "選考進捗", "進捗", "共有", "投稿", "スレッド",
        ],
    },
    "line": {
        "name": "LINE",
        "desc": "Lステップ文章生成 / 企業紹介文",
        "module": "line_agent",
        "keywords": [
            "line", "ライン", "lステップ", "lstep", "メッセージ", "リマインド",
            "催促", "クロージング", "初回接触",
        ],
    },
    "tldv": {
        "name": "tldv",
        "desc": "議事録取得・Claude分析",
        "module": "tldv_agent",
        "keywords": [
            "tldv", "議事録", "文字起こし", "トランスクリプト", "面談録音", "分析",
        ],
    },
    "report": {
        "name": "レポート",
        "desc": "学生所感レポート生成",
        "module": "report_agent",
        "keywords": [
            "所感", "レポート", "面談メモ", "所感レポート", "フォーマット",
        ],
    },
    "google": {
        "name": "Google",
        "desc": "Gmail・Sheets・Docs",
        "module": "google_agent",
        "keywords": [
            "gmail", "メール", "mail", "google", "スプレッドシート", "sheets",
            "docs", "ドキュメント", "グーグル",
        ],
    },
    "supporter": {
        "name": "サポーター",
        "desc": "使い方・システムガイド",
        "module": "supporter_agent",
        "keywords": [
            "使い方", "ヘルプ", "help", "説明", "ガイド", "サポート",
            "どうやって", "教えて", "わからない", "何ができる", "機能",
        ],
    },
    "interview_master": {
        "name": "面接マスター添削",
        "desc": "新卒/中途を自動判別し、5W1H・MECEで内定レベルまで添削",
        "module": "interview_master_agent",
        "keywords": [
            "面接対策", "添削", "es添削", "志望動機添削", "ガクチカ添削",
            "自己pr添削", "失敗経験", "キャリアビジョン", "実績", "中途",
            "即戦力", "再現性", "ポテンシャル", "内定", "mece", "5w1h",
        ],
    },
}

# ──────────────────────────────────────────────
# Claude によるルーティング
# ──────────────────────────────────────────────

_ROUTING_SYSTEM = (
    "あなたはHR支援AIエージェントシステムのルーターです。\n"
    "ユーザーの指示を読み取り、どのエージェントを実行すべきかをJSONで返してください。\n\n"
    "【利用可能なエージェント】\n"
    + json.dumps(
        {k: {"name": v["name"], "desc": v["desc"]} for k, v in AGENT_REGISTRY.items()},
        ensure_ascii=False, indent=2
    )
    + """

【出力形式】（JSONのみ。説明・前置き不要）
{
  "agents": ["agent_key1", "agent_key2"],
  "reason": "選択理由を一言で"
}

【判断ルール】
- 複合タスク（「tldvをSFに登録して」）は複数エージェントを配列で返す
- 順番は実行順（例: tldv → salesforce → slack）
- 「使い方」「何ができる」「教えて」→ supporter
- 「ES」「ガクチカ」「自己PR」「就活軸」→ coaching
- 「所感」「面談メモ」→ report
- 「企業紹介文」「Notion」→ notion
- 「Slack」「進捗共有」→ slack
- 「LINE」「Lステップ」「リマインド」→ line
- 「SF登録」「tldv」が両方 → [tldv, salesforce]
- 「メール」「Gmail」→ google
- 不明な場合 → supporter
"""
)


def _route_by_ai(user_input: str) -> list[str]:
    """Claude でルーティング決定。失敗時はキーワードマッチにフォールバック。"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system=_ROUTING_SYSTEM,
            messages=[{"role": "user", "content": user_input}],
        )
        text = response.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            agents = data.get("agents", [])
            reason = data.get("reason", "")
            valid = [a for a in agents if a in AGENT_REGISTRY]
            if valid:
                names = " → ".join(AGENT_REGISTRY[a]["name"] for a in valid)
                print(f"\n  実行: [{names}]  ({reason})")
                return valid
    except Exception:
        pass
    return _route_by_keywords(user_input)


def _route_by_keywords(user_input: str) -> list[str]:
    """キーワードマッチによるフォールバックルーティング"""
    lowered = user_input.lower()
    scores: dict[str, int] = {}
    for key, agent in AGENT_REGISTRY.items():
        score = sum(1 for kw in agent["keywords"] if kw in lowered)
        if score > 0:
            scores[key] = score

    if not scores:
        return ["supporter"]

    if "tldv" in scores and "salesforce" in scores:
        return ["tldv", "salesforce"]

    return [max(scores, key=scores.get)]


# ──────────────────────────────────────────────
# エージェント実行
# ──────────────────────────────────────────────

def _run_agent(agent_key: str):
    agent_info = AGENT_REGISTRY.get(agent_key)
    if not agent_info:
        print(f"  [ERROR] エージェント '{agent_key}' が見つかりません。")
        return

    try:
        mod = __import__(agent_info["module"])
        mod.run()
    except ImportError as e:
        print(f"  [ERROR] モジュール読み込み失敗: {e}")
    except KeyboardInterrupt:
        print("\n\n  メインメニューに戻ります。")


# ──────────────────────────────────────────────
# メインループ
# ──────────────────────────────────────────────

def _print_header():
    print("\n" + "=" * 60)
    print("  キャリアアドバイザー支援システム")
    print("=" * 60)
    print("\n  自然言語で指示してください:")
    print("    「tldvをSFに登録して」")
    print("    「田中さんの進捗をSlackに共有して」")
    print("    「ES対策をしたい」")
    print("    「使い方を教えて」")
    print("\n  直接起動:")
    for key, agent in AGENT_REGISTRY.items():
        print(f"    /{key:<12} {agent['name']} — {agent['desc']}")
    print("\n  /quit または q で終了")
    print("=" * 60)


def main():
    _print_header()

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n終了します。")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "/quit", "終了"):
            print("終了します。")
            break

        # 直接エージェント指定（/coaching など）
        if user_input.startswith("/"):
            key = user_input[1:].lower().strip()
            if key in AGENT_REGISTRY:
                _run_agent(key)
            else:
                print(f"  エージェント '{key}' が見つかりません。")
                print(f"  利用可能: {', '.join('/' + k for k in AGENT_REGISTRY)}")
            continue

        # AI ルーティング → エージェント実行
        agents = _route_by_ai(user_input)

        if len(agents) == 1:
            _run_agent(agents[0])
        else:
            names = " → ".join(AGENT_REGISTRY[a]["name"] for a in agents)
            print(f"\n  複合タスク実行: {names}")
            for agent_key in agents:
                print(f"\n{'─'*60}")
                print(f"  {AGENT_REGISTRY[agent_key]['name']} を実行します")
                print(f"{'─'*60}")
                _run_agent(agent_key)


if __name__ == "__main__":
    main()
