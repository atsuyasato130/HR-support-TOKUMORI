# STATUS_REPORT.md — HR Support AI Agent プロジェクト現状レポート

> **対象読者**: このプロジェクトを引き継ぐ戦略AI（軍師）または開発者
> **作成日**: 2026-03-12
> **プロジェクトパス**: `/Users/atsuyasato/AI agent（HRsupport事業）/`

---

## 1. プロジェクト全体像

### 目的
新卒・中途学生の就職支援業務を自動化するマルチエージェントAIシステム。
キャリアアドバイザー（CA）が行う「面談録 → Salesforce登録 → LINE送信 → Slack共有」という一連の業務フローをAIで代行する。

### エントリポイント
```
career_advisor/main.py   # オーケストレーター（自然言語ルーティング）
```

### ディレクトリ構造

```
AI agent（HRsupport事業）/
├── career_advisor/
│   ├── main.py                     # オーケストレーター（Claude自動ルーティング）
│   ├── requirements.txt
│   ├── agents/                     # 全エージェント（9種）
│   │   ├── coaching_agent.py       # ES・面接・就活軸深掘り（338行）
│   │   ├── salesforce_agent.py     # SF自動登録・更新（1,423行・最大規模）
│   │   ├── notion_agent.py         # 企業紹介文生成（439行）
│   │   ├── slack_agent.py          # 選考進捗Slack共有
│   │   ├── line_agent.py           # Lステップメッセージ生成（6シーン）
│   │   ├── tldv_agent.py           # tldv議事録取得・分析
│   │   ├── report_agent.py         # 学生所感レポート生成
│   │   ├── google_agent.py         # Gmail・Sheets・Docs連携
│   │   ├── supporter_agent.py      # システムガイド・使い方サポート
│   │   └── google_docs_helper.py
│   └── utils/
│       ├── tldv_client.py          # tldv APIクライアント（203行）
│       └── sheets_client.py        # Google Sheets連携・学生検索
├── integrations/
│   ├── mcp_salesforce_notion.py    # MCPサーバー（Claude Code用・JSON-RPC over stdio）
│   ├── kanrikun_client.py          # 採用一括かんりくん API（未稼働）
│   └── kanrikun_sync.py
├── config/
│   ├── .env                        # 全APIキー（本番環境）
│   ├── .env.example
│   ├── credentials.json            # Google OAuth2認証情報
│   ├── token.json                  # Google認証トークン（キャッシュ）
│   └── processed_email_ids.json
├── communication/
│   ├── slack_bot.py                # Slack自動応答ボット（スタンドアロン）
│   └── gmail_agent.py              # Gmail自動応答（google_agent.pyに統合済み）
├── lstep/
│   ├── reply_agent.py              # LINE自動応答ボット
│   ├── webhook_server.py           # LINE Webhook受信サーバー
│   └── requirements.txt
├── scheduling/
│   └── interview_scheduler.py      # 面談スケジューリング（実験的）
├── tools/
│   └── stock_monitor.py            # 株価アラート（本プロジェクトとは独立）
├── docs/
│   ├── system_diagram.md           # Mermaidフローチャート
│   └── slack_post_draft.md
├── web/                            # Next.js フロントエンド（未稼働）
├── logs/                           # ログ出力ディレクトリ
└── generate_resume_pdf.py          # PDF生成ツール（実験的）
```

---

## 2. アーキテクチャ設計

### 自然言語ルーティング（main.py）

```
ユーザー入力
  │
  ▼
Claude (claude-sonnet-4-6) で入力を分析
  │
  ├─ エージェントキー確定（AGENT_REGISTRY lookup）
  │    ↓ フォールバック: キーワードマッチング
  │
  ▼
対応エージェントを起動
  │
  ├─ 複合タスク: tldv → salesforce → slack と連鎖実行可能
  └─ /エージェントキー 記法で直接起動も可能
```

### AGENT_REGISTRY（ルーティングテーブル）

| キー | 役割 |
|------|------|
| `coaching` | ES・面接対策 / 就活軸深掘り |
| `salesforce` | tldv→SF自動登録 / 更新 |
| `notion` | 企業紹介文生成 |
| `slack` | 選考進捗共有 |
| `line` | Lステップメッセージ生成 |
| `tldv` | 議事録取得・分析 |
| `report` | 学生所感レポート生成 |
| `google` | Gmail・Sheets・Docs |
| `supporter` | システムガイド |

---

## 3. 実装済み機能（詳細）

### ① coaching_agent.py — 学生コーチング

**ES・面接対策**
- ガクチカ / 挫折経験 / 自己PR / 志望動機の対話形式深掘り
- 深掘り質問（最優先3つ + 追い質問）→ ES 300字 / 500字を自動生成

**就活軸深掘り**
- 3つの軸を構造化（概要・詳細・背景・原体験・判断基準）
- 全軸統合まとめ表示

---

### ② salesforce_agent.py — Salesforce連携（最大規模：1,423行）

**入力方式（3種）**
- tldv URL → API取得（Businessプランのみ）
- .txt ファイル読み込み
- テキスト貼り付け

**SF登録フロー（必須順序）**

```
① tldv議事録テキスト → Claude API で学生情報をJSON抽出
      （学生名・大学・就活軸・ガクチカ・希望業界等）
   ↓
② search_student_in_spreadsheet
      スプレッドシートID: 1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc
      電話番号・メール・カナ名・生年月日・高校名を補完
   ↓
③ Account 新規作成（create_salesforce_record）
   or 既存レコード更新（update_salesforce_record）
   ↓
④ Task（活動記録）を必ず作成（log_sf_meeting）
      ← ここを省略すると面談履歴がSFに残らない
```

**新規登録時の固定フィールド**
```python
"Status__pc":                   "支援中",
"Phase__pc":                    "初回面談済",
"CS_keiyu__c":                  "なし",
"Field27__c":                   "直紹介対象",
"OfficialLineRegistration__pc": True,
"RecordTypeId":                 "0122w000001Ry2hAAC",  # 新卒
```

**大学名登録（2フィールド必須）**
```python
# 片方だけでは SF 上で大学名が表示されないことがある
fields["UniversityName__pc"] = "横浜市立大学"       # 自由記述テキスト
fields["Field26__c"] = find_university_id(sf, name)  # CustomObject1__c の参照型ID
# SOQL: SELECT Id, Name FROM CustomObject1__c WHERE Name LIKE '%横浜市立%' LIMIT 1
```

---

### ③ notion_agent.py — 企業紹介文生成（439行）

**処理フロー**
```
search_notion で企業ページID取得
  ↓
read_notion_page で企業情報取得
  ↓
Claude で「おすすめポイント」を自動生成
  ↓
フォーマット整形して出力
```

**出力フォーマット**
```
━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 企業名
🌐 https://...
📋 事業概要: ...
🔄 選考フロー: ...
✨ おすすめポイント
  ▶ ポイント1
  ▶ ポイント2
📅 説明会日程（未来の日程・最大7件）
━━━━━━━━━━━━━━━━━━━━━━━━━
```

- 複数企業の一括処理（カンマ区切り / 改行入力）
- Notion DB ID: `5cdbd39197f94db7b7e275d317166bfd`

---

### ④ slack_agent.py — 選考進捗Slack共有

- Salesforce の pipeline データを Slack スレッドへ投稿
- 学生スレッドを「📍マーカー」で自動検索
- ステータス → 絵文字マッピング（例: `🎤説明会参加予定` / `✅通過` / `❌NG`）
- 活動中社数・内定社数・NG/辞退社数を自動集計
- 対象チャンネル: `C0A2YSANGKS`, `C0A4SJDDUV9`

---

### ⑤ line_agent.py — Lステップメッセージ生成（6シーン）

| シーン | 内容 |
|--------|------|
| 1 | 説明会・面接リマインド |
| 2 | ES提出催促・締切確認 |
| 3 | 面接後フォロー |
| 4 | クロージング（内定承諾の背中押し）|
| 5 | 初回接触・自己紹介 |
| 6 | その他（自由入力）|

- 複数パターン生成対応
- 絵文字なし / LINEらしい改行・テンポ感 / プレースホルダー `[ ]` 形式

---

### ⑥ tldv_agent.py — 議事録取得・分析

**3入力方式**
1. URL → tldv API 呼び出し（要Businessプラン）
2. .txt ファイル読み込み
3. テキスト直接貼り付け

**表示・分析**
- ミーティング情報 / ハイライト / 全文トランスクリプト
- Claude 自由質問（就活軸整理・CA評価・学生情報構造化）

---

### ⑦ report_agent.py — 学生所感レポート生成

**入力**: 学生名 / 大学 / 面談日 / 面談時間 / CA名 / 面談メモ

**出力フォーマット（6セクション）**
1. 基本情報
2. 第一印象・コミュニケーション
3. 就活状況・志望軸
4. 強み・懸念点
5. CAコメント・支援方針
6. 次のアクション

保存先: `career_advisor/reports/`

---

### ⑧ google_agent.py — Google連携

- **Gmail**: 未読取得 → Claude で返信案生成 → 送信
- **Google Sheets**: セル読取・書込・追記
- **Google Docs**: テキスト読取・末尾追記
- 認証: OAuth2（`config/credentials.json` + `config/token.json`）

---

### ⑨ supporter_agent.py — システムガイド

- 全エージェントの機能・使い方を自然言語で案内
- 「〇〇したい」→ どのエージェントを使うべきかを提案
- 新機能追加時の設計アドバイス

---

## 4. ユーティリティ詳細

### tldv_client.py（203行）

```python
extract_meeting_id(url_or_id: str) -> str
get_meeting(meeting_id, api_key) -> dict         # メタデータ
get_transcript(meeting_id, api_key) -> list      # 文字起こし（[MM:SS] Speaker: Text 形式）
get_highlights(meeting_id, api_key) -> list      # ハイライト
fetch_all(url_or_id, api_key) -> dict            # 全データ一括取得

# カスタム例外
TldvApiKeyError  # APIキー未設定 or Businessプラン未加入
TldvApiError     # API呼び出し失敗（タイムアウト / 404 / 403 等）
```

### sheets_client.py（250行+）

```python
get_sheets_client() -> gspread.Spreadsheet

search_student_in_sheet(
    spreadsheet_id: str,
    name: str,
    name_col_candidates: list | None = None,
    meeting_date: str | None = None,
) -> dict | None
# 複数ヒット時は面談日に最も近い行を優先

map_sheet_row_to_sf_fields(row: dict) -> dict
# Salesforce フィールドへのマッピング:
# "お名前を教えてください" → LastName + FirstName
# "フリガナを教えてください" → KanaLastName__pc + KanaFirstName__pc
# "生年月日を教えてください" → seinengappi__c
# "大学名を教えてください" → UniversityName__pc
# "メールアドレス" → PersonEmail
# "電話番号" → PersonMobilePhone
```

---

## 5. 技術スタック

### 言語・フレームワーク
- **Python 3.9**（`str | None` 型ヒント不可 → `from __future__ import annotations` を全ファイルに必要）
- **Next.js**（web/ ディレクトリ、現在未稼働）

### 主要ライブラリ（career_advisor/requirements.txt）

| ライブラリ | バージョン | 用途 |
|------------|-----------|------|
| `anthropic` | >=0.40.0 | Claude API（GPT推論エンジン） |
| `python-dotenv` | >=1.0.0 | 環境変数管理 |
| `simple-salesforce` | >=1.12.0 | Salesforce REST API |
| `requests` | >=2.31.0 | tldv API / HTTP汎用 |
| `gspread` | >=6.0.0 | Google Sheets |
| `google-auth` | >=2.0.0 | Google OAuth2 |
| `notion-client` | >=2.2.0 | Notion API |
| `httpx` | （MCP内で直接使用） | Notion DB query（notion-client v3の非対応対策） |

### 外部サービス・API

| サービス | 環境変数 | 状態 |
|---------|---------|------|
| Anthropic Claude API | `ANTHROPIC_API_KEY` | ✅ 稼働中 |
| Salesforce（本番） | `SF_USERNAME` / `SF_PASSWORD` / `SF_SECURITY_TOKEN` | ✅ 稼働中 |
| Notion | `NOTION_API_KEY` | ✅ 稼働中 |
| Slack Bot | `SLACK_BOT_TOKEN` / `SLACK_USER_TOKEN` / `SLACK_APP_TOKEN` | ✅ 稼働中 |
| Google OAuth2 | `config/credentials.json` | ✅ 稼働中 |
| tldv API | `TLDV_API_KEY` | ⏸ Businessプラン必要（現Pro） |
| LINE Messaging API | `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` | ⏸ 未設定 |
| Lステップ API | `LSTEP_API_ENDPOINT` / `LSTEP_API_TOKEN` | ⏸ 未設定 |
| 採用一括かんりくん | `KANRIKUN_CLIENT_ID` / `KANRIKUN_CLIENT_SECRET` | ⏸ 未設定 |

### モデル
- **推論**: `claude-sonnet-4-6`（全エージェント共通）
- Claudeは「ルーティング」「情報抽出（JSON）」「文章生成」の3役を担う

---

## 6. Salesforce オブジェクト・フィールド仕様

### RecordType
| 種別 | RecordTypeId |
|------|-------------|
| 新卒学生 | `0122w000001Ry2hAAC` |
| 中途学生 | `0122w000001Ry2cAAC` |
| クライアント企業 | `0122w000001RweZAAS` |

> **重要**: Lead / Opportunity オブジェクトは**存在しない**。学生・クライアントともに Account（PersonAccount）を使用。

### PersonAccount 主要カスタムフィールド（`__pc` サフィックス）

| フィールドAPI | ラベル | 型 |
|---|---|---|
| `Status__pc` | ステータス | picklist（支援中 / 支援終了 等） |
| `Phase__pc` | 状況 | picklist（初回面談済 / 送客済 等） |
| `OfficialLineRegistration__pc` | 公式LINE登録 | boolean |
| `InterviewDate__pc` | FS面談日 | date |
| `InterviewExpectedDate__pc` | FS面談予定日 | date |
| `GraduationYears__pc` | 卒業年度 | picklist（27卒 / 28卒 等） |
| `DesiredOccupation__pc` | 希望職種 | multipicklist |
| `KanaFirstName__pc` | 名カナ | string |
| `KanaLastName__pc` | 姓カナ | string |
| `koukomei__pc` | 高校名 | string |
| `UniversityName__pc` | 大学名（自由記述） | string |
| `Field17__c` | 学部 | string |
| `gakka__c` | 学科 | string |
| `Field12__c` | 就活の軸 | textarea |
| `Field13__c` | ガクチカ | textarea |
| `Field15__c` | 現状の選考企業 | textarea |
| `Field22__c` | サークル・団体 | textarea |
| `Field21__c` | 直紹介メモ | textarea |
| `Field19__c` | 学科区分 | picklist（文系 / 機電 / 化生 / 建築 / 情報 / その他） |
| `Field31__c` | ガクチカレベル | multipicklist（S〜D） |
| `Field26__c` | 大学名（参照型） | reference → `CustomObject1__c`（IDプレフィックス `a0T`） |
| `ReportPerson__c` | 紹介者 | picklist |
| `seinengappi__c` | 生年月日 | date |
| `HopeIndustry__pc` | 希望業界 | multipicklist |
| `JobSearchAxisThree__pc` | 就活の軸（3つ） | textarea |
| `WantedThreeCompanies__pc` | 行きたい企業（3つ） | textarea |
| `FutureDreamAndLifeMission__pc` | 将来の夢・人生のミッション | textarea |

### Task（活動記録）仕様

```python
# 正しい紐付け方
task = {
    "WhatId": account_id,    # Account に紐付け（必須）
    "WhoId": None,           # 使わない（PersonAccount では Contact ロールなし）
    "Subject": "...",
    "Description": "...",
    "ActivityDate": "YYYY-MM-DD",
    "Status": "Completed",
    # "Type" フィールドは存在しないため使用不可
}
```

---

## 7. MCPサーバー仕様（integrations/mcp_salesforce_notion.py）

Claude Code から Salesforce / Notion / Slack / Gmail / Spreadsheet を直接操作可能にする **JSON-RPC over stdio** 実装。

### 実装済みツール

```
Salesforce:
  search_salesforce(soql_query)
  update_salesforce_record(object_type, record_id, fields_json)
  create_salesforce_record(object_type, fields_json)
  log_sf_meeting(account_id, student_name, meeting_date, summary, next_actions, advisor_name, is_second_or_later)
  get_salesforce_summary()

Notion:
  search_notion(query)
  read_notion_database(database_id)   # httpx 直接呼び出し（notion-client v3の query 非対応のため）
  read_notion_page(page_id)           # 全プロパティ＋ブロックを返す
  update_notion_page(page_id, properties)
  create_notion_page(parent_id, properties)

Slack:
  send_slack_message(channel, text)
  get_slack_channels()
  get_slack_messages(channel_id, limit)

Gmail:
  send_gmail(to, subject, body)
  read_gmail(max_results)

Spreadsheet:
  search_student_in_spreadsheet(name, meeting_date)
  update_google_spreadsheet(spreadsheet_id, range, values)
  create_google_spreadsheet(title)
```

---

## 8. 設計思想・共通ルール

### コード共通ルール
- **Python 3.9 対応**: 型ヒントに `X | Y` 記法は使用不可。`from __future__ import annotations` を必ずファイル先頭に追加すること
- **Claude API の役割**: 「ルーティング判断」「情報のJSON抽出」「文章生成」の3つに集約
- **エージェント追加手順**: `AGENT_REGISTRY` に1行追記 + `supporter_agent.py` の `SYSTEM_KNOWLEDGE` を更新

### セキュリティ
- 全APIキーは `config/.env` で管理（`.gitignore` 対象）
- Google認証トークンは `config/token.json` にキャッシュ（OAuth2フロー自動更新）
- PIIマスキング: 現状は特定のマスキング処理は未実装（スプレッドシート内個人情報をSFに転記する設計）

### エラーハンドリング
- tldv: カスタム例外 `TldvApiKeyError` / `TldvApiError` でプラン不足を明示
- Notion DB query: notion-client v3 の制約を httpx 直接呼び出しで回避
- 大学名検索: `LIKE '%キーワード%'` での部分一致を使用（完全一致で見つからない場合のフォールバック）

---

## 9. 実装状況サマリー

| 機能 | 実装状態 | 備考 |
|------|---------|------|
| coaching_agent | ✅ 完全実装 | ES・就活軸ともに対話形式で完結 |
| salesforce_agent | ✅ 完全実装 | 全フロー完成（1,423行・最大規模）|
| notion_agent | ✅ 完全実装 | 企業紹介文・複数企業一括処理対応 |
| slack_agent | ✅ 完全実装 | 選考進捗共有・スレッド自動検索 |
| line_agent | ✅ 完全実装 | 6シーン対応・複数パターン生成 |
| tldv_agent | ✅ 完全実装 | 3入力方式・Claude自由分析対応 |
| report_agent | ✅ 完全実装 | 定型フォーマット生成・ファイル保存 |
| google_agent | ✅ 完全実装 | Gmail・Sheets・Docs全機能 |
| supporter_agent | ✅ 完全実装 | 完全なシステムガイド |
| MCPサーバー | ✅ 完全実装 | Claude Code連携 18ツール |
| tldv API連携 | ⏸ 未使用 | Businessプラン要（現在Proプラン）|
| LINE Messaging API | ⏸ 未設定 | `LINE_CHANNEL_ACCESS_TOKEN` 未設定 |
| Lステップ API | ⏸ 未設定 | エンドポイント・トークン未取得 |
| 採用かんりくん API | ⏸ 未設定 | `KANRIKUN_CLIENT_ID` 未設定 |
| Next.js フロントエンド | ⏸ 未稼働 | `web/` ディレクトリに存在するが未連携 |

---

## 10. 進行中タスクと技術的課題

### 現在直面しているボトルネック

| 課題 | 詳細 | 回避策 |
|------|------|--------|
| tldv API が使えない | Businessプランのみ対応（現Pro）| .txt ファイル or テキスト貼り付けで代替 |
| LINE Messaging API 未連携 | トークン未設定 | line_agent は「文章生成のみ」として稼働中 |
| Lステップ直送信 不可 | APIエンドポイント未取得 | 生成文章をコピペして手動送信 |
| Notion クエリ制限 | notion-client v3 の query 非対応 | MCP内で httpx 直接呼び出しにより解決済み |
| 大学名2フィールド問題 | UniversityName__pc と Field26__c の両方が必要 | salesforce_agent 内で両方セットする実装済み |

### 次に実装予定（優先度順）

1. **クロージング支援強化** — coaching_agent への「内定承諾判断サポート」シーン追加
2. **LINE直送信** — Lステップ API 取得後に line_agent へ送信機能実装
3. **tldv Businessプラン移行後** — URL入力フローの完全自動化
4. **採用かんりくん連携** — 送客後の進捗自動取り込み
5. **Next.js フロントエンド** — CAが操作するWebダッシュボード

---

## 11. 典型的なユースケース（業務フロー例）

### 面談後の典型フロー

```
1. CA が面談終了
   ↓
2. main.py 起動 → 「salesforce」エージェント選択
   ↓
3. tldv議事録テキスト（or .txt ファイル）を貼り付け
   ↓
4. Claude が学生情報をJSON抽出
   ↓
5. スプレッドシートから個人情報（電話・メール・カナ・生年月日）を自動補完
   ↓
6. Salesforce に PersonAccount を新規作成
   ↓
7. Task（活動記録）を自動作成
   ↓
8. 「report」エージェントで所感レポート生成
   ↓
9. 「line」エージェントでフォローLINEメッセージ生成
   ↓
10. 「slack」エージェントで選考進捗を社内Slackに共有
```

---

*このレポートは `career_advisor/` 以下の全ソースコード・`config/.env`・`integrations/` をスキャンして生成されました。*
