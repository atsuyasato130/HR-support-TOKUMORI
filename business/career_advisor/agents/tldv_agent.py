#!/usr/bin/env python3
"""
tldvエージェント

機能:
  - tldv議事録の取得・表示・分析
  - 入力方法: URL / ファイル(.txt) / テキスト貼り付け
  - Claudeによる自由分析（就活軸整理・CA評価など）

使い方:
  python3 tldv_agent.py
  from agents.tldv_agent import run, load_transcript
"""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime
import anthropic
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

sys.path.insert(0, os.path.join(BASE, "utils"))
from tldv_client import (  # type: ignore
    fetch_all, format_transcript_text,
    TldvApiKeyError, TldvApiError,
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
TLDV_API_KEY = os.environ.get("TLDV_API_KEY", "")

_ANALYSIS_SYSTEM = """あなたはHR（人材紹介）業界の専門家アシスタントです。
tldvの面談議事録をもとに、ユーザーの質問に丁寧かつ具体的に答えてください。

対応可能な分析:
- 学生のコミュニケーション力・論理性・熱量の評価
- 就活軸の整理・言語化
- 就活軸に基づく企業マッチング候補の提示
- キャリアアドバイザーの面談クオリティフィードバック
- 学生情報の構造化（氏名・大学・希望職種・就活状況等）

現時点ではユーザーの自由な質問に答えてください。"""


# ──────────────────────────────────────────────
# 議事録読み込み
# ──────────────────────────────────────────────

def load_from_url(url: str) -> dict:
    if not TLDV_API_KEY:
        raise TldvApiKeyError(
            "TLDV_API_KEY が未設定です。\n"
            "tldv Businessプランが必要です。\n"
            "config/.env に TLDV_API_KEY=xxx を設定してください。"
        )
    print("\ntldv APIからデータを取得中...")
    return fetch_all(url, TLDV_API_KEY)


def load_from_file(filepath: str) -> dict:
    filepath = filepath.strip().strip("'\"")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"ファイルが見つかりません: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    filename = os.path.splitext(os.path.basename(filepath))[0]
    return {
        "meeting_id": None,
        "meeting": {"name": filename, "happenedAt": None, "duration": None},
        "transcript": [],
        "highlights": [],
        "transcript_text": text,
        "highlights_text": "",
    }


def load_from_paste() -> dict:
    print("\n議事録テキストを貼り付けてください（空行2回で確定）:")
    lines = []
    blank_count = 0
    while True:
        line = input()
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
            lines.append(line)
        else:
            blank_count = 0
            lines.append(line)
    text = "\n".join(lines).strip()
    return {
        "meeting_id": None,
        "meeting": {"name": "（手動入力）", "happenedAt": None, "duration": None},
        "transcript": [],
        "highlights": [],
        "transcript_text": text,
        "highlights_text": "",
    }


def load_transcript(source: str | None = None) -> dict | None:
    """
    オーケストレーターからも呼べる共通ローダー。
    source: tldv URL文字列 or ファイルパス or None（インタラクティブ選択）
    """
    if source:
        if source.startswith("http"):
            try:
                return load_from_url(source)
            except (TldvApiKeyError, TldvApiError) as e:
                print(f"[tldv] {e}")
                return None
        elif os.path.exists(source):
            return load_from_file(source)
        else:
            # テキストとして扱う
            return {
                "meeting_id": None,
                "meeting": {"name": "（テキスト入力）", "happenedAt": None, "duration": None},
                "transcript": [],
                "highlights": [],
                "transcript_text": source,
                "highlights_text": "",
            }
    return None


# ──────────────────────────────────────────────
# 表示
# ──────────────────────────────────────────────

def display_meeting(data: dict):
    m = data.get("meeting", {})
    name = m.get("name") or "（タイトルなし）"
    happened_at = m.get("happenedAt") or "─"
    duration = m.get("duration")
    participants = m.get("participants") or m.get("attendees") or []

    print("\n" + "=" * 60)
    print("  【tldv ミーティング詳細】")
    print("=" * 60)
    print(f"\n■ ミーティング情報")
    print(f"  タイトル : {name}")
    print(f"  日時     : {happened_at}")
    if duration:
        mins = int(duration) // 60 if str(duration).isdigit() else duration
        print(f"  時間     : {mins}分")
    if participants:
        names = [p.get("name") or p.get("email", "") for p in participants if isinstance(p, dict)]
        print(f"  参加者   : {' / '.join(filter(None, names)) or '─'}")

    if data.get("highlights_text"):
        print(f"\n■ AIハイライト・要約")
        print(data["highlights_text"])

    if data.get("transcript_text"):
        print(f"\n■ 全文トランスクリプト")
        print("─" * 60)
        print(data["transcript_text"])
        print("─" * 60)


# ──────────────────────────────────────────────
# Claude 分析
# ──────────────────────────────────────────────

def run_analysis(data: dict):
    transcript = data.get("transcript_text", "")
    highlights = data.get("highlights_text", "")
    m = data.get("meeting", {})

    context = f"【ミーティング情報】\nタイトル: {m.get('name', '─')}\n日時: {m.get('happenedAt', '─')}\n\n"
    if highlights:
        context += f"【AIハイライト】\n{highlights}\n\n"
    if transcript:
        context += f"【トランスクリプト】\n{transcript}"

    messages = []

    print("\n" + "─" * 60)
    print("Claude に質問してください。（終了: q）")
    print("例: 「学生の就活軸を整理して」「CAの質問の質を評価して」「学生情報を構造化して」")
    print("─" * 60)

    while True:
        question = input("\nあなた > ").strip()
        if question.lower() in ("q", "quit", "終了"):
            break
        if not question:
            continue

        messages.append({"role": "user", "content": f"{context}\n\n---\n質問: {question}"})

        print("\nClaude > ", end="", flush=True)
        response_text = ""

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_ANALYSIS_SYSTEM,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                response_text += text

        print("\n")
        messages.append({"role": "assistant", "content": response_text})
        if len(messages) > 2:
            messages[0] = {"role": "user", "content": question}


# ──────────────────────────────────────────────
# ファイル保存 / クリップボード
# ──────────────────────────────────────────────

def save_to_file(data: dict) -> str:
    reports_dir = os.path.join(BASE, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    m = data.get("meeting", {})
    name = (m.get("name") or "tldv").replace(" ", "_").replace("　", "_")
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{date_str}_{name}_tldv.txt"
    filepath = os.path.join(reports_dir, filename)

    content_parts = [f"タイトル: {m.get('name', '─')}", f"日時: {m.get('happenedAt', '─')}"]
    if data.get("highlights_text"):
        content_parts += ["\n■ ハイライト", data["highlights_text"]]
    if data.get("transcript_text"):
        content_parts += ["\n■ トランスクリプト", data["transcript_text"]]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(content_parts))

    return filepath


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"[ERROR] クリップボードコピー失敗: {e}")
        return False


# ──────────────────────────────────────────────
# 入力ソース選択（インタラクティブ）
# ──────────────────────────────────────────────

def select_input_source() -> dict:
    api_status = "（APIキー設定済み）" if TLDV_API_KEY else "（※Businessプランのみ）"

    print("\n【入力方法を選択】\n")
    print(f"  [1] tldv URL / ミーティングID {api_status}")
    print("  [2] エクスポートファイル（.txt）のパスを入力")
    print("  [3] テキストを貼り付け")
    print("  [q] 終了")

    while True:
        choice = input("\n番号を入力 > ").strip().lower()

        if choice == "q":
            return {}

        if choice == "1":
            url = input("tldv URL または ミーティングID > ").strip()
            if not url:
                print("URLを入力してください。")
                continue
            try:
                return load_from_url(url)
            except TldvApiKeyError as e:
                print(f"\n[APIキーエラー] {e}")
                print("\n[2] ファイル入力 または [3] テキスト貼り付け に切り替えますか？ [y/n]")
                if input("> ").strip().lower() == "y":
                    continue
                return {}
            except TldvApiError as e:
                print(f"\n[APIエラー] {e}")
                return {}

        if choice == "2":
            filepath = input("ファイルパス > ").strip()
            try:
                return load_from_file(filepath)
            except FileNotFoundError as e:
                print(f"\n[エラー] {e}")
                continue

        if choice == "3":
            return load_from_paste()

        print("1・2・3・q のいずれかを入力してください。")


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None, source: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'view' | 'analyze' | None（メニュー表示）
    source: tldv URL / ファイルパス / テキスト文字列（省略時はインタラクティブ）

    将来追加予定:
      - 自動要約（面談後に自動でハイライトを整理）
      - 学生評価スコアリング
    """
    print("\n" + "=" * 60)
    print("  tldvエージェント")
    print("  議事録の詳細表示・Claude分析")
    print("=" * 60)

    while True:
        if source:
            data = load_transcript(source)
            source = None  # 2回目以降はインタラクティブ
        else:
            data = select_input_source()

        if not data:
            print("終了します。")
            break

        if not data.get("transcript_text"):
            print("コンテンツが空です。")
            continue

        display_meeting(data)

        while True:
            print("\n操作を選択してください:")
            print("  [s] ファイルに保存（career_advisor/reports/）")
            print("  [c] トランスクリプトをクリップボードにコピー")
            print("  [a] Claude に分析させる")
            print("  [n] 別の議事録を開く")
            print("  [q] 終了")

            action = input("\n> ").strip().lower()

            if action == "s":
                filepath = save_to_file(data)
                print(f"保存しました: {filepath}")

            elif action == "c":
                if copy_to_clipboard(data["transcript_text"]):
                    print("クリップボードにコピーしました。")

            elif action == "a":
                run_analysis(data)

            elif action == "n":
                break

            elif action == "q":
                print("終了します。")
                return

            else:
                print("s・c・a・n・q のいずれかを入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
