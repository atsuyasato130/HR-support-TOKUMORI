#!/usr/bin/env python3
"""
レポートエージェント

機能:
  - 面談後の学生所感レポート生成（面談メモ → 定型フォーマット）
  - 将来: 週次サマリー、CA活動レポート生成

使い方:
  python3 report_agent.py
  from agents.report_agent import run
"""

from __future__ import annotations

import os
import subprocess
from datetime import date
import anthropic
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM_PROMPT = """あなたはキャリアアドバイザー（CA）のアシスタントです。
面談メモをもとに、社内共有・管理用の「学生所感レポート」を作成します。

【出力ルール】
- 定型フォーマット（指定された見出し構成）を必ず守る
- 箇条書きを活用して読みやすくする
- 主観・印象は明確に「CA所見」として書く
- ネガティブな点も率直に記載（社内資料なので正確さ優先）
- 具体的な言葉・エピソードをメモから引用して根拠を示す
- 次のアクションは「誰が・何を・いつまでに」を明確にする
- 出力はフォーマットのみ（余計な説明・前置き不要）
"""


# ──────────────────────────────────────────────
# 情報収集
# ──────────────────────────────────────────────

def _collect_info() -> dict:
    print("\n" + "="*55)
    print("  学生情報を入力してください")
    print("="*55 + "\n")

    today = date.today().strftime("%Y/%m/%d")

    data: dict = {}
    data["student_name"]  = input("学生名 > ").strip()
    data["university"]    = input("大学・学部（例: 〇〇大学 経済学部 3年） > ").strip()
    data["date"]          = input(f"面談日（デフォルト: {today}）> ").strip() or today
    data["duration"]      = input("面談時間（例: 30分・60分） > ").strip() or "未記録"
    data["advisor_name"]  = input("担当CA名 > ").strip()
    data["meeting_type"]  = input("面談形式（例: オンライン・対面・電話） > ").strip() or "未記録"

    print("\n" + "─"*55)
    print("面談メモを入力してください。")
    print("（話した内容・気になった点・学生の発言など自由に）")
    print("（空行2回で確定）")
    print("─"*55)

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
    data["memo"] = "\n".join(lines).strip()

    return data


# ──────────────────────────────────────────────
# 所感レポート生成
# ──────────────────────────────────────────────

def generate_report(data: dict) -> str:
    prompt = f"""以下の面談メモをもとに「学生所感レポート」を作成してください。

【面談情報】
- 学生名: {data['student_name']}
- 大学・学年: {data['university']}
- 面談日: {data['date']}
- 面談時間: {data['duration']}
- 担当CA: {data['advisor_name']}
- 面談形式: {data['meeting_type']}

【面談メモ】
{data['memo']}

---

以下のフォーマットで所感レポートを作成してください:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
学生所感レポート
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ 基本情報
- 学生名: {data['student_name']}
- 大学・学年: {data['university']}
- 面談日: {data['date']}  面談時間: {data['duration']}
- 担当CA: {data['advisor_name']}  形式: {data['meeting_type']}

■ 第一印象・コミュニケーション
（コミュニケーション能力・話し方・積極性・態度など、面談メモから読み取れる内容を記載）

■ 就活状況・志望軸
（現在の就活の進め方・志望業界・企業の方向性・軸など）

■ 強み・懸念点
【強み】
（メモから読み取れる学生の強みを具体的に）
【懸念点・課題】
（CAとして感じた懸念、改善が必要な点）

■ CAコメント・支援方針
（この学生にどう関わるべきか、CA所見・方針を簡潔に）

■ 次のアクション
（具体的なTO DOを「誰が・何を・いつまでに」形式で。情報が不足していれば「要確認」と記載）
- CA:
- 学生:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    print("\n所感レポートを生成中...\n")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


# ──────────────────────────────────────────────
# 出力・保存
# ──────────────────────────────────────────────

def _copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"[ERROR] クリップボードコピー失敗: {e}")
        return False


def _save_to_file(text: str, student_name: str, meeting_date: str) -> str:
    reports_dir = os.path.join(BASE, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    safe_name = student_name.replace(" ", "_").replace("　", "_")
    safe_date = meeting_date.replace("/", "-")
    filename = f"{safe_date}_{safe_name}_所感.txt"
    filepath = os.path.join(reports_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    return filepath


# ──────────────────────────────────────────────
# 所感レポート作成モード
# ──────────────────────────────────────────────

def _run_impression():
    print("\n" + "="*55)
    print("  所感フォーマット作成エージェント")
    print("  面談メモ → 学生所感レポートを自動生成")
    print("="*55)

    while True:
        data = _collect_info()

        if not data["memo"]:
            print("\n面談メモが入力されていません。再入力してください。")
            continue

        report = generate_report(data)

        print("\n" + "="*55)
        print(report)
        print("="*55)

        while True:
            print("\n操作を選択してください:")
            print("  [c] クリップボードにコピー")
            print("  [s] ファイルに保存（career_advisor/reports/ に保存）")
            print("  [b] 両方（コピー＋ファイル保存）")
            print("  [r] 再生成")
            print("  [n] 新しい学生の所感を作る")
            print("  [q] 終了")

            action = input("\n> ").strip().lower()

            if action in ("c", "b"):
                if _copy_to_clipboard(report):
                    print("クリップボードにコピーしました。")

            if action in ("s", "b"):
                filepath = _save_to_file(report, data["student_name"], data["date"])
                print(f"ファイルに保存しました: {filepath}")

            if action in ("c", "s", "b"):
                break

            elif action == "r":
                print("\n再生成中...")
                report = generate_report(data)
                print("\n" + "="*55)
                print(report)
                print("="*55)

            elif action == "n":
                break

            elif action == "q":
                print("終了します。")
                return

            else:
                print("無効な入力です。")

        if action == "q":
            break


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'impression' | None（メニュー表示）

    将来追加予定:
      - 'weekly': 週次CAサマリーレポート生成
      - 'ca_review': CA面談クオリティフィードバックレポート
      - 'batch': 複数学生の所感を一括生成
    """
    if mode == "impression":
        _run_impression()
        return

    print("\n" + "=" * 55)
    print("  レポートエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. 学生所感レポート生成")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_impression()
            break
        elif choice == "q":
            break
        else:
            print("1 または q を入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
