#!/usr/bin/env python3
"""
LINEエージェント

統合内容:
  - Lステップ文章生成（6シーン: リマインド / ES催促 / 面接後フォロー /
                        クロージング / 初回接触 / その他）
  - 企業紹介文生成（Notion連携）← notion_agent.py に委譲

使い方:
  python3 line_agent.py
  from agents.line_agent import run
"""

from __future__ import annotations

import os
import subprocess
import anthropic
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "../config/.env"))

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM_PROMPT = """あなたはキャリアアドバイザーのLINE文章作成アシスタントです。

【文章スタイルのルール】
- LINEらしい自然な改行・テンポ感を意識する（長文NG）
- 絵文字は使わない（コピペ先でズレが出る場合があるため）
- 学生名は「{name}さん」の形で冒頭に入れる
- 丁寧語ベース。フレンドリーだが馴れ馴れしくない
- 具体的な日時・企業名などの情報は [  ] で明示してプレースホルダーにする
- 文末は「よろしくお願いします」「お待ちしております」など適切に締める
- 出力は文章のみ（タイトルや説明は不要）

【絶対にやってはいけないこと】
- 「〜ですよね！」「〜ですね！」のような過度な感嘆符
- 「頑張ってください！」のような空虚な励まし
- 200文字を超える一段落の文章
"""

# ──────────────────────────────────────────────
# シーン定義
# ──────────────────────────────────────────────

SCENES = {
    "1": {
        "label": "説明会・面接のリマインド",
        "questions": [
            ("student_name", "学生の名前 > "),
            ("event_type", "イベント種別（例: 会社説明会・一次面接・最終面接） > "),
            ("company", "企業名 > "),
            ("datetime", "日時（例: 3月5日(水) 14:00〜） > "),
            ("location", "場所・形式（例: オンライン / 東京本社） > "),
            ("note", "補足（任意。例: 持参物・服装・URL） > "),
        ],
        "prompt_template": lambda d: f"""
以下の条件でリマインドLINEを作成してください。

【学生名】{d['student_name']}
【イベント】{d['event_type']}
【企業名】{d['company']}
【日時】{d['datetime']}
【場所・形式】{d['location']}
【補足】{d['note'] or 'なし'}

明日・当日が近いことを伝え、確認・準備を促す文章にしてください。
「既読・確認できたら返信ください」など簡単なアクションを添えてください。
""",
    },
    "2": {
        "label": "ESの提出催促・締切確認",
        "questions": [
            ("student_name", "学生の名前 > "),
            ("company", "企業名 > "),
            ("deadline", "締切日（例: 3月10日 23:59） > "),
            ("status", "現在の状況（例: まだ着手中・ほぼ完成・未確認） > "),
        ],
        "prompt_template": lambda d: f"""
以下の条件でES提出を促すLINEを作成してください。

【学生名】{d['student_name']}
【企業名】{d['company']}
【締切】{d['deadline']}
【現在の状況】{d['status'] or '未確認'}

焦らせすぎず、でもしっかり行動を促す文章にしてください。
「添削したいのでできたら送って」という言葉も自然に入れてください。
""",
    },
    "3": {
        "label": "面接後のフォロー",
        "questions": [
            ("student_name", "学生の名前 > "),
            ("company", "企業名 > "),
            ("stage", "選考段階（例: 一次面接・最終面接） > "),
            ("result", "状況（例: 結果待ち / 通過 / 次の選考が決まった） > "),
            ("feeling", "学生の感触（例: 手ごたえあり / 不安そう / 不明） > "),
        ],
        "prompt_template": lambda d: f"""
以下の条件で面接後フォローのLINEを作成してください。

【学生名】{d['student_name']}
【企業名】{d['company']}
【選考段階】{d['stage']}
【状況】{d['result']}
【学生の感触】{d['feeling'] or '不明'}

お疲れさまの言葉 + 結果・次のステップを確認する内容にしてください。
不安な場合は「何かあればいつでも話しましょう」など寄り添う一言も添えてください。
""",
    },
    "4": {
        "label": "クロージング（内定承諾の背中押し）",
        "questions": [
            ("student_name", "学生の名前 > "),
            ("company", "内定先企業名 > "),
            ("deadline", "承諾期限（例: 3月15日） > "),
            ("concern", "学生の懸念・迷いポイント（任意） > "),
            ("advisor_message", "CAとして伝えたいこと・方針（任意） > "),
        ],
        "prompt_template": lambda d: f"""
以下の条件でクロージングのLINEを作成してください。

【学生名】{d['student_name']}
【内定企業】{d['company']}
【承諾期限】{d['deadline']}
【学生の懸念】{d['concern'] or '特になし'}
【CAからのメッセージ方針】{d['advisor_message'] or '特になし'}

内定承諾への背中を押す内容にしてください。
プレッシャーをかけすぎず、学生の気持ちに寄り添いながら「一緒に考えましょう」という姿勢を出してください。
面談のオファーも入れてください。
""",
    },
    "5": {
        "label": "初回接触・自己紹介",
        "questions": [
            ("student_name", "学生の名前 > "),
            ("advisor_name", "CAの名前 > "),
            ("source", "どこで知り合ったか（例: 合同説明会・スカウト・紹介） > "),
            ("next_action", "次のアクション（例: 面談日程の調整） > "),
        ],
        "prompt_template": lambda d: f"""
以下の条件で初回接触のLINEを作成してください。

【学生名】{d['student_name']}
【CAの名前】{d['advisor_name']}
【出会いのきっかけ】{d['source']}
【次のアクション】{d['next_action']}

キャリアアドバイザーとして、フレンドリーかつプロフェッショナルな自己紹介にしてください。
「これからよろしくお願いします」という温かみのある締めにしてください。
""",
    },
    "6": {
        "label": "その他（自由入力）",
        "questions": [
            ("student_name", "学生の名前（任意） > "),
            ("purpose", "メッセージの目的・内容を自由に入力 > "),
        ],
        "prompt_template": lambda d: f"""
以下の目的でLINEメッセージを作成してください。

【学生名】{d['student_name'] or '（名前なし）'}
【目的・内容】{d['purpose']}

キャリアアドバイザーとして適切なトーンで作成してください。
""",
    },
}


# ──────────────────────────────────────────────
# メッセージ生成
# ──────────────────────────────────────────────

def _generate_message(prompt: str, variation: int = 1) -> str:
    full_prompt = prompt
    if variation > 1:
        full_prompt += "\n\n※パターン1とは異なる表現・切り口で作成してください。"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": full_prompt}],
    )
    return response.content[0].text.strip()


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except Exception as e:
        print(f"\n[ERROR] クリップボードコピー失敗: {e}")
        return False


# ──────────────────────────────────────────────
# シーン実行
# ──────────────────────────────────────────────

def _run_scene(scene_key: str):
    scene = SCENES[scene_key]
    print(f"\n{'='*55}")
    print(f"  {scene['label']}")
    print(f"{'='*55}\n")

    data = {}
    for key, question in scene["questions"]:
        val = input(question).strip()
        data[key] = val

    count_input = input("\n生成パターン数（1〜3、デフォルト: 2） > ").strip()
    count = int(count_input) if count_input.isdigit() and 1 <= int(count_input) <= 3 else 2

    prompt = scene["prompt_template"](data)

    print(f"\n文章を生成中...\n{'─'*55}")

    messages = []
    for i in range(1, count + 1):
        msg = _generate_message(prompt, i)
        messages.append(msg)
        print(f"\n【パターン{i}】\n{'─'*40}")
        print(msg)
        print()

    while True:
        print(f"{'─'*55}")
        options = [f"  [{i}] パターン{i}をコピー" for i in range(1, len(messages) + 1)]
        options.append("  [e] 手動で編集して使う")
        options.append("  [r] 再生成")
        options.append("  [q] 終了")
        print("\n".join(options))

        action = input("\n> ").strip().lower()

        if action.isdigit() and 1 <= int(action) <= len(messages):
            selected = messages[int(action) - 1]
            if copy_to_clipboard(selected):
                print("\nクリップボードにコピーしました。")
                print("Lステップのトーク画面に貼り付けてください。")
            break

        elif action == "e":
            print("\n使いたい文章を入力してください（空行2回で確定）:")
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
            edited = "\n".join(lines).strip()
            if copy_to_clipboard(edited):
                print("\nクリップボードにコピーしました。")
            break

        elif action == "r":
            print("\n再生成中...\n" + "─"*55)
            messages = []
            for i in range(1, count + 1):
                msg = _generate_message(prompt, i)
                messages.append(msg)
                print(f"\n【パターン{i}】\n{'─'*40}")
                print(msg)
                print()

        elif action == "q":
            break
        else:
            print("無効な入力です。")


# ──────────────────────────────────────────────
# Lステップ文章生成モード
# ──────────────────────────────────────────────

def _run_lstep():
    print("\n" + "="*55)
    print("  Lステップ文章生成（キャリアアドバイザー版）")
    print("="*55)

    while True:
        print("\n【シーンを選択】\n")
        for key, scene in SCENES.items():
            print(f"  {key}. {scene['label']}")
        print("  q. 終了\n")

        choice = input("番号を入力 > ").strip().lower()

        if choice == "q":
            print("終了します。")
            break
        elif choice in SCENES:
            _run_scene(choice)
        else:
            print("1〜6 または q を入力してください。")


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'lstep' | 'intro'（企業紹介文はnotion_agentへ委譲） | None（メニュー表示）

    将来追加予定:
      - 'reminder': 説明会・面接リマインドの一括送信
      - 'batch': 複数学生への一括メッセージ生成
    """
    if mode == "lstep":
        _run_lstep()
        return
    if mode == "intro":
        # 企業紹介文はnotion_agentが担当
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from notion_agent import run as notion_run  # type: ignore
        notion_run(mode="intro")
        return

    print("\n" + "=" * 55)
    print("  LINEエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. Lステップ文章生成（リマインド / ES催促 / フォロー 等）")
    print("  2. 企業紹介文生成（Notion → LINE用）")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_lstep()
            break
        elif choice == "2":
            run(mode="intro")
            break
        elif choice == "q":
            break
        else:
            print("1・2・q のいずれかを入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
