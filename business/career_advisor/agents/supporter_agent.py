#!/usr/bin/env python3
"""
サポーターエージェント（システムガイド）

機能:
  - 全エージェントの機能・使い方を日本語でわかりやすく説明
  - 「〇〇がしたい」→ どのエージェントを使えばいいか案内
  - 新機能追加時にどのエージェントを拡張すべきか提案
  - ファイル構成・アーキテクチャの説明
  - チームメンバーへのマニュアルとして機能

使い方:
  python3 supporter_agent.py
  from agents.supporter_agent import run
"""

from __future__ import annotations

import os
import anthropic
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE, "config/.env"))

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ──────────────────────────────────────────────
# システム知識ベース（常に最新を保つこと）
# ──────────────────────────────────────────────

SYSTEM_KNOWLEDGE = """
=================================================
HR支援AIエージェントシステム — 完全ガイド
=================================================

【システム概要】
キャリアアドバイザー（CA）の業務を自動化・効率化するマルチエージェントシステム。
自然言語で指示するだけで、適切なエージェントが自動実行される。

【起動方法】
  cd "/Users/atsuyasato/Claude AI/AI agent（HRsupport事業）/business/career_advisor"
  python3 main.py

---

【エージェント一覧】

■ coaching_agent（学生コーチング）
  ファイル: career_advisor/agents/coaching_agent.py
  機能:
    - ES・面接対策: ガクチカ/挫折/自己PR/志望動機を対話形式で深掘り → ES文章（300字/500字）生成
    - 就活軸深掘り: 就活軸を会話で言語化（概要・詳細・原体験・判断基準）
  使うタイミング:
    - 「ES作ってあげたい」「ガクチカの壁打ちしたい」「就活軸を整理したい」
  将来追加予定: クロージングプラン（内定承諾に向けた対話）

■ salesforce_agent（Salesforceエージェント）
  ファイル: career_advisor/agents/salesforce_agent.py
  機能:
    - tldv議事録テキスト → 学生情報をClaudeで自動抽出
    - 新規学生のAccount（新卒RecordType）を作成 + Task登録
    - 既存学生の情報更新・選考進捗更新 + Task追記
    - Google Sheetsと連携して不足情報を補完
  使うタイミング:
    - 「面談後にSFに登録したい」「tldvの内容をSalesforceに記録したい」
  重要情報:
    - RecordType新卒: 0122w000001Ry2hAAC
    - 固定項目: Status__pc=支援中, Phase__pc=初回面談済, CS_keiyu__c=なし, Field27__c=直紹介対象

■ notion_agent（Notionエージェント）
  ファイル: career_advisor/agents/notion_agent.py
  機能:
    - 企業紹介文生成: Notion企業DB → LINE送信用紹介文（複数企業一括対応）
    - おすすめポイントをClaudeが自動生成
  DB情報:
    - 企業DB ID: 5cdbd39197f94db7b7e275d317166bfd
    - フィールド: 企業名/HP/事業概要/選考フロー/説明会日程
  使うタイミング:
    - 「企業紹介文を作りたい」「〇〇社の紹介文を生成したい」
  将来追加予定: 企業DB検索、企業ページ更新、企業レコメンド

■ slack_agent（Slackエージェント）
  ファイル: career_advisor/agents/slack_agent.py
  機能:
    - 選考進捗Slack共有: SalesforceのpipelineデータをSlackスレッドに投稿
    - 学生のSlackスレッドを自動検索（📍マーカーで判定）
  使うタイミング:
    - 「〇〇さんの選考進捗をSlackに共有したい」「進捗レポートを投稿したい」
  設定:
    - SLACK_BOT_TOKEN, SLACK_USER_TOKEN が必要
    - 対象チャンネル: C0A2YSANGKS, C0A4SJDDUV9
  将来追加予定: 任意チャンネルへのメッセージ送信、週次レポート自動投稿

■ line_agent（LINEエージェント）
  ファイル: career_advisor/agents/line_agent.py
  機能:
    - Lステップ文章生成: 6シーン別のLINEメッセージを複数パターン生成
      ① 説明会・面接リマインド
      ② ES提出催促・締切確認
      ③ 面接後フォロー
      ④ クロージング（内定承諾背中押し）
      ⑤ 初回接触・自己紹介
      ⑥ その他（自由入力）
    - 企業紹介文生成（notion_agentへ委譲）
  使うタイミング:
    - 「学生にLINE送りたい」「リマインドメッセージを作りたい」「Lステップに貼る文章が欲しい」
  将来追加予定: 一括送信、複数学生へのバッチ生成

■ tldv_agent（tldvエージェント）
  ファイル: career_advisor/agents/tldv_agent.py
  機能:
    - tldv議事録の取得・表示（URL/ファイル/テキスト貼り付け）
    - Claudeによる自由分析（就活軸整理・CA評価・学生情報構造化など）
  注意:
    - tldv APIはBusinessプランのみ（現在Proプランのため未使用）
    - ファイル/テキスト貼り付けで代用可能
  使うタイミング:
    - 「tldvの内容を確認したい」「議事録を分析したい」
  将来追加予定: 自動要約、学生評価スコアリング

■ report_agent（レポートエージェント）
  ファイル: career_advisor/agents/report_agent.py
  機能:
    - 学生所感レポート生成: 面談メモ → 定型フォーマットの所感レポート
      フォーマット: 基本情報/第一印象/就活状況/強み・懸念点/CAコメント/次のアクション
    - クリップボードコピー or ファイル保存（career_advisor/reports/）
  使うタイミング:
    - 「所感を書きたい」「面談メモから所感レポートを作りたい」
  将来追加予定: 週次CAサマリー、CA面談クオリティフィードバック

■ google_agent（Googleエージェント）
  ファイル: career_advisor/agents/google_agent.py
  機能:
    - Gmail: 未読メール取得 → Claudeで返信案生成 → 送信
    - Google Sheets: セル読み取り・書き込み・追記
    - Google Docs: ドキュメント読み取り・追記
  認証:
    - config/credentials.json と config/token.json が必要
    - 初回起動時にブラウザでGoogle認証が必要
  使うタイミング:
    - 「メールに返信したい」「スプレッドシートのデータを確認したい」
  将来追加予定: Google Calendar、Google Drive、Google Forms

■ supporter_agent（サポーターエージェント）← このファイル
  ファイル: career_advisor/agents/supporter_agent.py
  機能:
    - システム全体の説明・案内
    - 「〇〇したい」→ どのエージェントを使うか提案
    - 新機能追加時の設計アドバイス
    - チームメンバーへのマニュアル

---

【ファイル構成】

business/career_advisor/
├── main.py                    ← オーケストレーター（自然言語でエージェントを自動選択）
├── agents/
│   ├── coaching_agent.py      ← 学生コーチング（ES・面接・就活軸）
│   ├── salesforce_agent.py    ← Salesforce操作（tldv→SF自動登録）
│   ├── notion_agent.py        ← Notion操作（企業DB・紹介文生成）
│   ├── slack_agent.py         ← Slack操作（選考進捗共有）
│   ├── line_agent.py          ← LINE操作（Lステップ文章生成）
│   ├── tldv_agent.py          ← tldv議事録取得・分析
│   ├── report_agent.py        ← レポート生成（所感レポート）
│   ├── google_agent.py        ← Google全般（Gmail・Sheets・Docs）
│   └── supporter_agent.py     ← システムガイド（このファイル）
├── utils/
│   ├── tldv_client.py         ← tldv APIクライアント
│   ├── sheets_client.py       ← Google Sheetsクライアント
│   └── google_docs_helper.py  ← Google Docsヘルパー
├── config/
│   ├── .env                   ← APIキー（ANTHROPIC/SF/NOTION/SLACK/GOOGLE等）
│   ├── credentials.json       ← Google OAuth2認証情報
│   └── token.json             ← Googleアクセストークン（認証後自動生成）
└── reports/                   ← 生成レポートの保存先

business/career_advisor/integrations/
└── mcp_salesforce_notion.py   ← MCPサーバー（Claude Codeから直接ツール使用）

business/career_advisor/communication/
├── slack_bot.py               ← Slack AIボット（受信メッセージへの自動応答）
└── process_one_email.py       ← Gmail処理

business/career_advisor/lstep/
└── reply_agent.py             ← LINEメッセージへの自動応答ボット

---

【自然言語でよく使う指示例とエージェントの対応】

「tldvをSFに登録して」        → tldv_agent + salesforce_agent（連鎖実行）
「面談後の所感を作って」      → report_agent
「選考進捗をSlackに共有して」 → slack_agent
「企業紹介文を作って」        → notion_agent
「LINEメッセージを作って」    → line_agent
「ES対策をしたい」            → coaching_agent (ES・面接モード)
「就活軸を整理したい」        → coaching_agent (就活軸モード)
「メールに返信したい」        → google_agent (Gmailモード)
「使い方を教えて」            → supporter_agent（このエージェント）

---

【新機能を追加したいとき】

1. 既存エージェントに追加できる場合:
   - SF系の新機能 → salesforce_agent.py に run() のモード追加
   - LINE系の新機能 → line_agent.py に新シーン追加
   - Google系の新機能 → google_agent.py に新関数追加
   - Notion系の新機能 → notion_agent.py に新モード追加

2. 新エージェントが必要な場合:
   - business/career_advisor/agents/ に新しい xxx_agent.py を作成
   - main.py の AGENT_REGISTRY に追加（自動でオーケストレーターが認識）
   - このファイル（supporter_agent.py）のSYSTEM_KNOWLEDGEを更新

3. 確認のコツ:
   - 各エージェントの run() 関数の docstring に「将来追加予定」が記載されている
   - どのエージェントに追加すべか迷ったら、このサポーターエージェントに質問

---

【よくあるエラーと対処】

Salesforce接続エラー:
  → config/.env の SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN を確認

Notion APIエラー:
  → config/.env の NOTION_API_KEY を確認
  → NOTION_DB_ID (5cdbd39197f94db7b7e275d317166bfd) が正しいか確認

Google認証エラー:
  → config/credentials.json が存在するか確認
  → python3 google_agent.py を単独起動してブラウザ認証を完了させる

tldv APIエラー:
  → Businessプランのみ対応（現在Proプランのためファイル/テキスト貼り付けで代用）
  → config/.env の TLDV_API_KEY を確認

Slack投稿エラー:
  → SLACK_BOT_TOKEN（投稿用）と SLACK_USER_TOKEN（検索用）を確認
  → Slackアプリの権限（chat:write, search:read）を確認

=================================================
"""

_SUPPORTER_SYSTEM = f"""あなたはHR支援AIエージェントシステムのサポーターです。
チームメンバーがシステムの使い方・機能・ファイル構成について質問したときに、
わかりやすく・正確に・丁寧に答えてください。

以下がシステムの完全なガイドです。この情報をもとに答えてください：

{SYSTEM_KNOWLEDGE}

【回答スタイル】
- 初心者にもわかりやすい言葉で説明する
- 「〇〇したい場合は△△エージェントを使ってください」と具体的に案内する
- 新機能の追加提案がある場合は「どのファイルのどこに追加すればよいか」まで答える
- ファイルパスを示すときは具体的な絶対パスで答える
- わからないことは「確認が必要です」と正直に伝える
"""

_OPENING = """こんにちは！HR支援AIエージェントシステムのサポーターです。

以下についてお答えできます：
  ・各エージェントの機能・使い方
  ・「〇〇したい」→ どのエージェントを使うか
  ・ファイル構成・アーキテクチャの説明
  ・新機能追加時の設計アドバイス

何でも聞いてください！（終了: q）"""


# ──────────────────────────────────────────────
# 対話モード
# ──────────────────────────────────────────────

def _run_chat():
    messages = [{"role": "assistant", "content": _OPENING}]

    print("\n" + "=" * 60)
    print("  システムサポーターエージェント")
    print("  使い方・機能・構成について何でも答えます")
    print("=" * 60)
    print(f"\nサポーター > {_OPENING}\n")

    while True:
        user_input = input("あなた > ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("q", "quit", "終了"):
            print("\nお疲れ様でした！")
            break

        messages.append({"role": "user", "content": user_input})

        print("\nサポーター > ", end="", flush=True)
        response_text = ""

        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=_SUPPORTER_SYSTEM,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                print(text, end="", flush=True)
                response_text += text

        print("\n")
        messages.append({"role": "assistant", "content": response_text})


def _show_guide():
    """ガイドをそのまま表示"""
    print(SYSTEM_KNOWLEDGE)


# ──────────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────────

def run(mode: str | None = None):
    """
    オーケストレーターから呼ばれるエントリポイント。
    mode: 'chat' | 'guide' | None（メニュー表示）
    """
    if mode == "chat":
        _run_chat()
        return
    if mode == "guide":
        _show_guide()
        return

    print("\n" + "=" * 55)
    print("  システムサポーターエージェント")
    print("=" * 55)
    print("\n【メニュー】\n")
    print("  1. 質問する（チャット形式）")
    print("  2. 完全ガイドを表示")
    print("  q. 終了\n")

    while True:
        choice = input("番号を入力 > ").strip().lower()
        if choice == "1":
            _run_chat()
            break
        elif choice == "2":
            _show_guide()
            break
        elif choice == "q":
            break
        else:
            print("1・2・q のいずれかを入力してください。")


def main():
    run()


if __name__ == "__main__":
    main()
