#!/usr/bin/env python3
"""
InterviewMasterAgent — 究極の面接対策エージェント

機能:
  - 入力テキストから「新卒」「中途」を自動判別
  - 5W1H（事実の解像度）＆ MECE（論理の網羅性）で監査
  - 全カテゴリ（志望動機/ガクチカ/自己PR/失敗経験/実績/キャリアビジョン）対応
  - 新卒 → ポテンシャル評価レポート
  - 中途 → 即戦力・再現性評価レポート
  - BaseAgent 継承 / PII_DETECTOR で安全出力
"""

from __future__ import annotations

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_agent import BaseAgent
from google_docs_helper import create_student_feedback_doc

# ──────────────────────────────────────────────
# システムプロンプト（究極の面接対策エージェント）
# ──────────────────────────────────────────────

_SYSTEM_PROMPT = """
# Role
あなたは、世界トップクラスの戦略コンサルティングファームの採用パートナーであり、
かつ数々のエグゼクティブを成功に導いてきた「伝説のヘッドハンター」です。
5W1Hによる「事実の解像度」と、MECEによる「論理の美しさ」を絶対的な基準とし、
候補者の回答を内定レベルまで引き上げます。

# Mission
1. 入力内容から【属性（新卒/中途）】と【質問カテゴリ】を自動判別する。
2. 「5W1H」と「MECE」の観点でロジック監査を行い、致命的な欠陥を特定する。
3. 属性に合わせた評価重心（新卒：ポテンシャル、中途：再現性）で添削を行う。

# Evaluation Logic（監査アルゴリズム）

## 1. 事実の解像度（5W1H監査）
- When/Where: 状況設定の曖昧さ。
- Who: 役割、関係者、対象の不明瞭さ。
- What/How: 行動プロセスの具体性（「頑張った」等の抽象語は厳禁）。
- Why: 意思決定の根拠（なぜその手段を選んだか）。

## 2. 論理の網羅性（MECE監査）
- 重複の排除: 同じ概念の繰り返しを統合する。
- 漏れの補完: 3C（市場・競合・自社）や自己分析の視点の抜けを指摘する。
- 構造化: 結論に対し、根拠が論理的に独立して並んでいるか。

## 3. カテゴリ別・絶対評価基準
- 【ガクチカ/実績】: STAR形式の遵守、数字による定量化、独自の介在価値。
- 【志望動機】: 競合比較（なぜ他社でないか）、ビジョン接続、入社後の具体的貢献イメージ。
- 【失敗経験】: 自責思考の有無、学びの抽象化、再発防止の仕組み化（再現性）。
- 【強み・弱み】: 客観的評価、弱みの制御（セルフマネジメント）。
- 【中途専用】: スキルの転用性、転職理由の妥当性と前向きな変換。
"""

# ──────────────────────────────────────────────
# 出力テンプレート（新卒）
# ──────────────────────────────────────────────

_TEMPLATE_STUDENT = """
# 出力形式（新卒・学生用）— この形式を厳守すること

## 🎓 【学生向け】ポテンシャル評価レポート

### 1. 総合評価
- **判定**: [合格 / 補欠 / 不合格]
- **スコア**: [0-100]点
- **面接官の総評**:
  > あなたの最大の強みは〇〇ですが、〇〇という点で成長の余地があります。

### 2. ロジック監査（5W1H & MECE）
- **5W1Hの不足**:
  - [ ] When/Where: [具体的にどこが足りないか]
  - [ ] Who: [役割が不明確な箇所]
  - [ ] How/Why: [行動の根拠をより深く]
- **MECE診断**:
  - [ ] 漏れ: [追加すべき視点]
  - [ ] ダブり: [整理すべき重複箇所]

### 3. 戦略的アドバイス
- **【プロの視点】**: ここを直せば内定が近付くという決定的なポイント。
- **【深掘り質問】**: 本番で必ず聞かれるキラークエスチョン（3問）。

### 4. ブラッシュアップ回答例（Before/After）
**Before（元の回答の問題点）:**
[問題のある箇所を引用・指摘]

**After（ピラミッド構造で整理された理想回答）:**
[内定レベルに引き上げた完成形]
"""

# ──────────────────────────────────────────────
# 出力テンプレート（中途）
# ──────────────────────────────────────────────

_TEMPLATE_CAREER = """
# 出力形式（中途・社会人用）— この形式を厳守すること

## 💼 【中途向け】即戦力・再現性評価レポート

### 1. エグゼクティブ・サマリー
- **判定**: [Shortlist / Pending / Reject]
- **スコア**: [0-100]点
- **評価の要諦**:
  > 経験の厚みは十分ですが、他社での「再現性」の証明において論理が甘い箇所があります。

### 2. 定量・論理監査レポート
- **実績の具体性 (5W1H)**:
  - 数字の根拠、予算規模、自身の介在価値を5W1Hで精査した結果。
- **構造化の美しさ (MECE)**:
  - 市場・競合・自社の3Cバランスや、キャリアの一貫性の監査。

### 3. 戦略的アドバイス
- **【スキルの転用性】**: 前職の経験をどう現職の利益に変えるかの論理補強。
- **【転職理由の再定義】**: ネガティブな要因を、志望先への貢献意欲へ変換する策。
- **【圧迫・深掘り質問】**: 実績の信憑性を試す鋭い質問（3問）。

### 4. プロ推奨の回答構成案
**Before（元の回答の問題点）:**
[問題のある箇所を引用・指摘]

**After（論理的に非の打ち所がない、洗練された職務経歴/志望動機の構成例）:**
[内定レベルに引き上げた完成形]
"""

# ──────────────────────────────────────────────
# LINE出力テンプレート（新卒・砕けた口調）
# ──────────────────────────────────────────────

_LINE_TEMPLATE_STUDENT = """
# 出力形式（LINE送信用・学生向け）— この形式を厳守すること

■ トーン・ルール（絶対厳守）
・敬語・丁寧語は一切使わない。友達に話すような砕けた口調で書く
・語尾例：「〜だよ！」「〜じゃん！」「〜しよ！」「〜だね」「〜だと思う！」
・絵文字で各セクションを区切る（多用OK）
・1段落は最大4行。長くなるなら箇条書きに
・冒頭挨拶（「お疲れ様」等）は不要。すぐ本題へ
・添削後の文章は「そのままコピーして使えるレベル」まで仕上げる

■ 出力フォーマット（この順番で出力）

📝【{カテゴリ}添削】

━━━━━━━━━━━━━
✅ ここ良かった！
━━━━━━━━━━━━━
（強みや伝わっている部分を2〜3点。具体的に褒める）

━━━━━━━━━━━━━
🔧 ここ直すともっと刺さる！
━━━━━━━━━━━━━
（5W1H・MECEの観点で2〜4点。「〇〇が足りないから、□□追加すると一気に強くなるよ！」形式）

━━━━━━━━━━━━━
❓ 面接で絶対聞かれる質問（3問）
━━━━━━━━━━━━━
（深掘りキラークエスチョン。「答えられる？」と問いかけながら提示）

━━━━━━━━━━━━━
✏️ 完成版（300字）
━━━━━━━━━━━━━
（そのままESに使える完成形。数字・行動・結果・学びが入っている）

━━━━━━━━━━━━━
✏️ 完成版（500字）
━━━━━━━━━━━━━
（より詳細なバージョン。ストーリーと熱意が伝わる完成形）

━━━━━━━━━━━━━
💬 一言コメント
━━━━━━━━━━━━━
（1〜2文。前向きに締める。「あなた」と呼ぶ）
"""

# ──────────────────────────────────────────────
# LINE出力テンプレート（中途・プロフェッショナル口調）
# ──────────────────────────────────────────────

_LINE_TEMPLATE_CAREER = """
# 出力形式（LINE送信用・中途向け）— この形式を厳守すること

■ トーン・ルール
・丁寧だが簡潔。「〜ですね」「〜ましょう」程度の柔らかさ
・難しい用語は使わず、読みやすく
・絵文字で各セクションを区切る
・1段落は最大4行

■ 出力フォーマット

💼【{カテゴリ}添削レポート】

━━━━━━━━━━━━━
✅ 評価できるポイント
━━━━━━━━━━━━━
（強みと再現性が伝わっている部分を2〜3点）

━━━━━━━━━━━━━
🔧 強化すべきポイント
━━━━━━━━━━━━━
（5W1H・再現性・スキル転用性の観点で2〜4点）

━━━━━━━━━━━━━
❓ 想定される深掘り質問（3問）
━━━━━━━━━━━━━
（圧迫気味の鋭い質問。事前に準備が必要なもの）

━━━━━━━━━━━━━
✏️ 改善後の回答例
━━━━━━━━━━━━━
（論理的で非の打ち所がない完成形）

━━━━━━━━━━━━━
💬 総評
━━━━━━━━━━━━━
（1〜2文。前向きに締める）
"""

# ──────────────────────────────────────────────
# 属性判別 + 添削実行
# ──────────────────────────────────────────────

def review(
    text: str,
    attribute: str = "auto",
    category: str = "auto",
    line_mode: bool = False,
    client=None,
) -> str:
    """
    面接回答・ESテキストを受け取り、添削レポートを返す。

    Args:
        text      : 添削対象テキスト
        attribute : "新卒" / "中途" / "auto"（自動判別）
        category  : "志望動機" / "ガクチカ" / "自己PR" / "失敗経験" / "実績" / "キャリアビジョン" / "auto"
        line_mode : True の場合 LINE送信向けフォーマットで出力（新卒は砕けた口調）
        client    : anthropic.Anthropic インスタンス（Noneなら内部生成）

    Returns:
        添削レポート文字列
    """
    import anthropic as _anthropic
    from dotenv import load_dotenv

    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(_BASE_DIR, "config", ".env"))

    _client = client or _anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # テンプレート選択（line_mode で分岐）
    if attribute == "新卒":
        template = _LINE_TEMPLATE_STUDENT if line_mode else _TEMPLATE_STUDENT
        attr_hint = "この回答者は【新卒・学生】です。"
    elif attribute == "中途":
        template = _LINE_TEMPLATE_CAREER if line_mode else _TEMPLATE_CAREER
        attr_hint = "この回答者は【中途・社会人】です。"
    else:
        if line_mode:
            template = (
                "入力内容から属性を自動判別し、新卒なら学生用LINE、中途なら中途用LINEテンプレートで出力してください。\n\n"
                + _LINE_TEMPLATE_STUDENT
                + "\n\n"
                + _LINE_TEMPLATE_CAREER
            )
        else:
            template = (
                "入力内容から属性を自動判別し、以下のいずれかのテンプレートで出力してください。\n\n"
                + _TEMPLATE_STUDENT
                + "\n\n"
                + _TEMPLATE_CAREER
            )
        attr_hint = "入力内容から【新卒/中途】を自動判別してください。"

    category_hint = (
        f"カテゴリは【{category}】です。" if category != "auto"
        else "入力内容からカテゴリ（志望動機/ガクチカ/自己PR/失敗経験/実績/キャリアビジョン）を自動判別してください。"
    )

    system = _SYSTEM_PROMPT.strip() + "\n\n" + template.strip()

    user_msg = (
        f"{attr_hint}\n{category_hint}\n\n"
        "--- 添削対象テキスト ---\n"
        f"{text}\n"
        "--- ここまで ---"
    )

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text.strip()


# ──────────────────────────────────────────────
# InterviewMasterAgent クラス（BaseAgent 継承）
# ──────────────────────────────────────────────

class InterviewMasterAgent(BaseAgent):
    """
    究極の面接対策エージェント。

    新卒・中途を自動判別し、5W1H & MECE で監査した
    プロレベルの添削レポートを出力する。
    """

    agent_key = "interview_master"
    agent_name = "面接マスター添削"
    agent_desc = "新卒/中途を自動判別し、5W1H・MECEで内定レベルまで添削"

    CATEGORIES = ["志望動機", "ガクチカ", "自己PR", "失敗経験", "実績", "キャリアビジョン"]
    ATTRIBUTES = ["auto（自動判別）", "新卒", "中途"]

    def run(self) -> Optional[str]:
        """CLIインタラクティブ添削モード"""
        print("\n" + "=" * 60)
        print("  面接マスター添削エージェント")
        print("  5W1H & MECE で内定レベルまで引き上げます")
        print("=" * 60)

        # 属性選択
        print("\n【属性を選択してください】")
        for i, attr in enumerate(self.ATTRIBUTES, 1):
            print(f"  {i}. {attr}")
        attr_input = input("\n選択（1-3）> ").strip()
        attr_map = {"1": "auto", "2": "新卒", "3": "中途"}
        attribute = attr_map.get(attr_input, "auto")

        # カテゴリ選択
        print("\n【カテゴリを選択してください】")
        print("  0. auto（自動判別）")
        for i, cat in enumerate(self.CATEGORIES, 1):
            print(f"  {i}. {cat}")
        cat_input = input("\n選択（0-6）> ").strip()
        cat_map = {str(i): cat for i, cat in enumerate(self.CATEGORIES, 1)}
        cat_map["0"] = "auto"
        category = cat_map.get(cat_input, "auto")

        # 学生名・メールアドレス入力
        student_name = input("\n学生名を入力してください（Doc生成に使用）> ").strip()
        if not student_name:
            student_name = "学生"

        student_email = input("学生のメールアドレス（Googleアカウント）を入力してください（スキップ: Enter）> ").strip()

        # 出力形式選択
        print("\n【出力形式を選択してください】")
        print("  1. 詳細レポート（内部確認・コンサル向け）")
        print("  2. LINE送信用（学生に直接送れる形式）")
        mode_input = input("\n選択（1-2）> ").strip()
        line_mode = mode_input == "2"

        # テキスト入力
        print(f"\n添削するテキストを貼り付けてください。")
        print("（入力完了後、空行で Enter を2回押してください）")
        print("-" * 60)

        lines = []
        empty_count = 0
        while True:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)

        text = "\n".join(lines).strip()
        if not text:
            print("テキストが入力されませんでした。")
            return None

        mode_label = "LINE送信用" if line_mode else "詳細レポート"
        print(f"\n⏳ 添削中（属性: {attribute} / カテゴリ: {category} / {mode_label}）...\n")

        try:
            report = review(
                text=text,
                attribute=attribute,
                category=category,
                line_mode=line_mode,
                client=self._client,
            )
            print("\n" + "=" * 60)
            print(report)
            print("=" * 60)

            # Google Doc 自動生成（毎回実行）
            print("\n⏳ Googleドキュメントを生成中...")
            try:
                doc_url = create_student_feedback_doc(
                    student_name=student_name,
                    category=category if category != "auto" else "ES添削",
                    es_text=text,
                    feedback=report,
                    share_email=student_email,
                )
                print(f"\n📄 ドキュメントを作成しました")
                print(f"   {doc_url}")
                if student_email:
                    print(f"   ✅ {student_email} に編集権限を付与しました")
                else:
                    print(f"\n💡 このURLを学生に共有してください。")
            except Exception as doc_err:
                print(f"\n⚠️  Doc生成に失敗しました（フィードバック本文は上記の通りです）: {doc_err}")

            # 連続添削
            while True:
                cont = input("\n続けて添削する？（y / n）> ").strip().lower()
                if cont != "y":
                    break
                return self.run()

            return report

        except Exception as exc:
            print(f"\n❌ エラーが発生しました: {exc}")
            return None


def main() -> None:
    InterviewMasterAgent().execute()


if __name__ == "__main__":
    main()
