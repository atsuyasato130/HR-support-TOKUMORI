# architecture_master.md — 帝国の設計書（最上位行動指針）

> **この文書はすべての作業の前に参照せよ。コード変更・エージェント追加・設定変更のたびに必ず更新せよ。**
> 最終更新: 2026-03-18 (100+ Agent Governance 追加)

---

## 0. システム全体像

```
/Users/atsuyasato/Claude AI/
├── private/life_supporter/          ← 帝国兵站部（非接触・聖域）
└── AI agent（HRsupport事業）/
    └── business/career_advisor/     ← 帝国本陣（エントリポイント: main.py）
```

**目的**: CA（キャリアアドバイザー）の業務フロー「面談録 → SF登録 → LINE → Slack共有」をAIで全自動化する。

**起動**:
```bash
cd "/Users/atsuyasato/Claude AI/AI agent（HRsupport事業）/business/career_advisor"
python3 main.py
```

---

## 0.5 Micro-Workers アーキテクチャ（2026-03-18 追加）

### 設計思想

100エージェント体制を支えるための**分業型アーキテクチャ**。
コンテキスト消費を最小化し、各ワーカーは単一責務のみを持つ。

### 4ロール定義

| ロール | 兵種 | 責務 | LLM | ファイル |
|--------|------|------|-----|---------|
| WATCHER | 哨戒兵 | 外部変更を検知しIDのみ出力 | ✗ | `workers/notion_watcher.py` |
| PARSER | 選別兵 | 生データから最小フィールド抽出 | ✗ | `workers/notion_page_parser.py` |
| PROCESSOR | 策士兵 | マッピング・推論・命令生成 | △ | `workers/sf_field_mapper.py` |
| EXECUTOR | 突撃兵 | API書き込みのみ（ロジックなし） | ✗ | `workers/sf_bulk_executor.py` |

### Stateless Handover（バケツリレー）原則

```
[WATCHER]              [PARSER]              [PROCESSOR]           [EXECUTOR]
notion_watcher.py  →  notion_page_parser.py  →  sf_field_mapper.py  →  sf_bulk_executor.py
       ↓                      ↓                        ↓                      ↓
 state/watcher_queue  →  state/parser_queue  →  state/processor_queue  →  state/executor_results
（notion_page_id のみ）  （抽出フィールドJSON）    （SF更新命令JSON）         （実行結果JSON）
```

- **禁止**: エージェント間で生テキスト・APIレスポンス全体を渡すこと
- **許可**: IDと最小限のJSON（100行以内）のみをステートファイル経由で渡す
- ステートファイル場所: `business/career_advisor/state/`

### パイプライン一括実行

```bash
# Notion変更をSFに全同期
python3 agents/workers/sf_bulk_executor.py --run-pipeline --full-scan

# 差分のみ（前回実行以降）
python3 agents/workers/sf_bulk_executor.py --run-pipeline

# dry-run確認
python3 agents/workers/sf_bulk_executor.py --run-pipeline --dry-run
```

### 既存エージェントとの関係

```
agents/              ← 既存モノリシックエージェント（対話CLIとして継続稼働）
agents/workers/      ← Micro-Workers（バッチ処理・自動化に特化）
agents/base_agent.py ← 既存エージェントの親クラス（PII検知・ノウハウ保存）
agents/base_worker.py← Micro-Workerの親クラス（4ロール定義・StateManager連携）
```

既存エージェントはモノリシック構造のまま残す。
`workers/` は非対話バッチ処理専用。将来的には既存エージェントも段階的に分解可能。

### 選考進捗 → Slack 通知パイプライン（2026-04-22 再設計）

WATCHER が検知したイベントを DISPATCHER が consume して Slack に配信する形式に統一。
固定メンション・チャンネルID・SFフィールド名・しきい値は全て `config/domain_hr.json` 経由。

```
[WATCHER] sf_record_watcher (launchd 60分)
    ↓ state/sf_changes_queue.json（append）
[DISPATCHER] sf_change_dispatcher (launchd 10分)
    ├─ SlackSentLog で idempotency チェック
    ├─ SlackThreadIndex で学生スレッド解決（索引キャッシュ＋search_messages フォールバック）
    ├─ SlackOwnerResolver で Owner → Slack User ID 解決
    └─ 3回失敗で DLQ（state/sf_changes_deadletter.json）→ unfound_dm_user へ DM

[SCHEDULED NOTIFIER]
  ├─ sf_patrol_agent                 (launchd 毎朝08:00) — 説明会当日リマインド
  ├─ followup_alert_notifier         (launchd 毎朝08:30) — 14日未接触 TOP10
  └─ weekly_digest_notifier          (launchd 月08:30)   — 週次KPI + Claude所見

[SUPPORT]
  ├─ utils/slack_thread_index.py     (launchd 毎朝03:00) — 学生スレッド索引再構築
  ├─ utils/slack_owner_resolver.py   — SF OwnerId → Slack User
  ├─ utils/domain_config.py          — domain_hr.json 読み込みキャッシュ
  └─ state/slack_sent_log.py         — 送信履歴（90日TTL）
```

**重複排除キー**: `{event_type}:{student_id}:{changed_at}`  
**設定ファイル**: `config/domain_hr.json` の `notification` / `watcher` / `sf_fields` / `dedupe` セクション  
**メンション規則**: `supervisor_ids` は常時メンション（現在は佐藤・渡邊の2名）、担当CAは `ca_slack_mapping[sf_owner_id]` で解決、スレッド主はスレッド投稿時に自動追加。

---

## 0.6 100+ Agent Governance（2026-03-18 追加）

### 目的

エージェント数が100を超えても無秩序にならないよう、命名・登録・共通化の3ルールを強制する。

### ディレクトリ構成（Governance 追加後）

```
business/
├── agents/
│   ├── registry.json          ← ★ 統合レジストリ（全エージェントの単一ソース）
│   ├── _registry_schema.json  ← JSONSchema バリデーション定義
│   └── name_validator.py      ← 命名規則チェッカー（新エージェント追加時に実行）
├── lib/
│   ├── __init__.py
│   ├── api_clients.py         ← Notion / SF / Slack / Anthropic 薄いラッパー
│   ├── validators.py          ← ピックリスト・フィールド値バリデーション
│   ├── state_io.py            ← state/ ファイル読み書き統一 API
│   └── registry_loader.py     ← registry.json ロード・検索・重複チェック
└── career_advisor/            ← 既存エージェント本体（変更なし）
    └── knowledge/
        └── AGENT_MANIFEST.json ← v2.0: canonical_id 追加・registry.json へ参照
```

### 命名規則 — `[Domain]_[Role]_[Target]`

| ロール | 意味 | 例 |
|--------|------|----|
| `watcher` | 外部変更検知のみ・LLM不使用 | `hr_watcher_notion_company` |
| `parser` | 最小フィールド抽出・LLM不使用 | `hr_parser_notion_page` |
| `processor` | 推論・マッピング・LLM可 | `hr_processor_sf_mapper` |
| `executor` | API書き込みのみ・ロジックなし | `hr_executor_sf_bulk` |
| `orchestrator` | 複数Workerを束ねる制御 | `hr_orchestrator_post_interview` |

### Iron Rules（絶対守護原則）

1. **registry.json 未登録のエージェントを本番稼働させてはならない**
2. **新エージェント作成前に `name_validator.py --check` を実行し、重複検証を必ず行う**
3. **Worker 内に API通信・バリデーション・状態読み書きロジックを直書きしない → `business/lib/` を使う**
4. **`business/lib/` モジュールを worker から `from business.lib.xxx import yyy` で参照する**

### 新エージェント追加フロー

```bash
# 1. 命名チェック（重複・規則違反を検出）
python3 business/agents/name_validator.py --check hr_executor_new_target

# 2. registry.json に追記（必須フィールド: id / domain / role / target / canonical_name / ...）
# → _registry_schema.json に従うこと

# 3. 全件再検証
python3 business/agents/name_validator.py --check-all

# 4. knowledge/AGENT_MANIFEST.json に canonical_id を追記
# 5. architecture_master.md §0.6 のエージェント数を更新
# 6. スプレッドシート Agent_Registry タブを更新
```

### 現在の登録状況（2026-03-18 時点）

| ロール | 件数 | エージェント |
|--------|------|------------|
| watcher | 2 | hr_watcher_notion_company, hr_watcher_tldv |
| parser | 2 | hr_parser_notion_page, hr_parser_notion |
| processor | 4 | hr_processor_sf_mapper, hr_processor_coaching, hr_processor_report, hr_processor_supporter, hr_processor_interview |
| executor | 4 | hr_executor_sf_bulk, hr_executor_salesforce, hr_executor_slack, hr_executor_line, hr_executor_google |
| orchestrator | 1 | hr_orchestrator_post_interview |
| **合計** | **15** | |

---

## 1. アーキテクチャ原則

### 自然言語ルーティング（main.py）

```
ユーザー入力
  ↓
Claude (claude-sonnet-4-6) でルーティング判断（JSON出力）
  ↓ フォールバック: キーワードスコアリング
  ↓
AGENT_REGISTRY から対象エージェントを起動
  ↓（複合タスク時）
連鎖実行: tldv → salesforce → slack 等
```

**エージェント追加手順（Governance版・4ステップ）:**
1. `business/agents/name_validator.py --check [canonical_name]` で命名・重複チェック
2. `business/agents/registry.json` に登録
3. `main.py` の `AGENT_REGISTRY` に1行追記
4. `supporter_agent.py` の `SYSTEM_KNOWLEDGE` を更新

### domain_hr.json — 業界転用の鍵

```json
// 業界を変えるにはこのファイルを差し替えるだけ
{
  "domain": "hr",
  "entity": { "label": "学生", "counterpart_label": "企業", "session_label": "面談" },
  "crm": { "platform": "salesforce", "object_type": "Account" },
  "portability": {
    "real_estate": "entity.label='顧客', crm.object_type='Opportunity'",
    "consulting": "entity.label='クライアント'"
  }
}
```

---

## 2. 秘伝のタレ — Salesforce独自仕様

### 必須登録フロー（順序絶対厳守）

```
① tldv議事録テキスト → Claude API で学生情報JSON抽出
      学生名・大学・就活軸・ガクチカ・希望業界等
   ↓
② search_student_in_spreadsheet()
      スプレッドシートID: 1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc
      → 電話・メール・カナ名・生年月日・高校名を補完
   ↓
③ Account 新規作成 or 既存更新
      search_account(sf, email) で既存確認 → なければ create
   ↓
④ Task（活動記録）を必ず作成 ← 省略厳禁！面談履歴がSFに残らなくなる
      log_sf_meeting(account_id, ...)
```

### RecordType

| 種別 | RecordTypeId |
|------|-------------|
| 新卒学生 | `0122w000001Ry2hAAC` |
| 中途学生 | `0122w000001Ry2cAAC` |
| クライアント企業 | `0122w000001RweZAAS` |

> **重要**: Lead / Opportunity は存在しない。学生・クライアントともに Account（PersonAccount）を使用。

### 新規登録固定フィールド（新卒）

```python
"Status__pc":                   "支援中",
"Phase__pc":                    "初回面談済",
"CS_keiyu__c":                  "なし",
"Field27__c":                   "直紹介対象",
"OfficialLineRegistration__pc": True,
"RecordTypeId":                 "0122w000001Ry2hAAC",
```

### 大学名登録（2フィールド必須）

```python
# 片方だけでは SF 上で大学名が表示されないことがある
fields["UniversityName__pc"] = "横浜市立大学"        # 自由記述テキスト
fields["Field26__c"] = find_university_id(sf, name)  # CustomObject1__c 参照型ID

# 検索SOQL（完全一致 → 部分一致フォールバック）
# SELECT Id, Name FROM CustomObject1__c WHERE Name = '横浜市立大学' LIMIT 1
# SELECT Id, Name FROM CustomObject1__c WHERE Name LIKE '%横浜市立%' LIMIT 1
```

### 主要カスタムフィールド早見表

| API名 | ラベル | 型 | 有効値 |
|-------|--------|-----|--------|
| `Status__pc` | ステータス | picklist | 支援中 / 支援終了 等 |
| `Phase__pc` | 状況 | picklist | 初回面談済 / 送客済 等 |
| `GraduationYears__pc` | 卒業年度 | picklist | 23卒〜30卒（**不明時デフォルト: 27卒**） |
| `Field19__c` | 学科区分 | picklist | 文系 / 機電 / 化生 / 建築 / 情報 / その他 |
| `Field31__c` | ガクチカレベル | multipicklist | S(起業) / A(長期IS) / B(留学・立上) / C(リーダー) / D(メンバー) |
| `HopeIndustry__pc` | 希望業界 | multipicklist | コンサル・シンクタンク / 金融 / IT・通信 等 |
| `ReportPerson__c` | 紹介者 | picklist | 熊谷穂澄 / 宮内佑一郎 / 佐藤篤也 等 |
| `Field12__c` | 就活の軸 | textarea | 自由記述 |
| `Field13__c` | ガクチカ | textarea | 自由記述 |
| `Field26__c` | 大学名（参照型） | reference | CustomObject1__c（IDプレフィックス `a0T`） |

### 評価フィールド（2026-04-12 追加） — PersonAccount / Contact.__c

> **デプロイ先は Contact オブジェクト**（PersonAccount の __pc は Contact の __c）
> fullName = label = 長テキスト の restricted=true ピックリスト（JobHuntingProficiency 形式）

| Account 表示名 | Contact API名 | ラベル | 値形式 |
|---------------|--------------|--------|--------|
| `ThinkingSkill__pc` | `ThinkingSkill__c` | 思考力 | S〜D：長テキスト基準付き |
| `Character__pc` | `Character__c` | 人格 | S〜D：長テキスト基準付き |
| `Execution__pc` | `Execution__c` | 実行力 | S〜D：長テキスト基準付き |
| `InterpersonalSkill__pc` | `InterpersonalSkill__c` | 対人力 | S〜D：長テキスト基準付き |
| `JobHuntingProficiency__pc` | `JobHuntingProficiency__c` | 就活習熟度 | S〜D：長テキスト基準付き |

### パイプライン転記フィールド（2026-04-12 追加） — Account

| API名 | ラベル | 型 | 転記元 | 転記フロー |
|-------|--------|-----|--------|-----------|
| `LatestYomiAccuracy__c` | ヨミ確度（最新） | Text(10) | `pipeline__c.GfaAccuracy__c` | PipelineSummary_UpdateAccount |
| `LatestPipelineStatus__c` | 選考進捗（最新） | Text(50) | `pipeline__c.Status__c` | PipelineSummary_UpdateAccount |

### 面談回数フィールド — Account

| API名 | ラベル | 型 |
|-------|--------|-----|
| `FollowMeetingCount__c` | フォロー面談回数 | Number |
| `ClosingMeetingCount__c` | クロージング面談回数 | Number |

### Activity（Task/Event）追加フィールド（2026-04-20 追加）

> Activity 共通定義は Task と Event の両方に反映される。運用基盤整備（ヨミ管理・フォロー追跡）の一環として追加。

| API名 | ラベル | 型 | 用途 |
|-------|--------|-----|------|
| `NextActionDate__c` | 次回アクション日 | Date | 面談後の次回フォロー予定日を記録。未来日で検索してフォロー漏れ防止 |
| `MeetingSubtype__c` | 面談サブ種別 | Picklist（restricted） | `初回 / フォロー / クロージング / その他`。既存 `MeetingType__c`（通信手段）と別軸 |

**既存の併用フィールド**:
- `FollowNextAction__c`（次のアクション, Text）: 次回アクションの**内容**を記録
- `MeetingType__c`（面談種別, Picklist）: 通信手段（面談/電話/LINE/その他）。**段階とは別軸**なので併用
- `FollowStatus__c` / `MotivationChange__c` / `ClosingStatus__c` 等: 面談後評価系フィールド

### 未デプロイの運用基盤提案（2026-04-20）

以下は準備済みだがデプロイ待ち。運用が定着してから有効化する：

| 提案 | ファイル | 状態 |
|------|---------|------|
| pipeline__c Validation Rule（二次面接以降で見込計上月必須、最終面接以降でヨミ確度必須） | `tools/sf_pipeline_validation_rules.py` | スクリプト作成済み・デプロイ保留 |
| ヨミ自動補完 Flow（内定日 → 見込計上月 翌月1日自動セット） | `tools/sf_yomi_autofill_flow.xml` + `docs/sf_yomi_flow_setup.md` | XML+手順書あり・手動デプロイ推奨 |

### デプロイ済みフロー（2026-04-12 時点）

| フロー名 | オブジェクト | トリガー | 機能 |
|---------|------------|---------|------|
| `PipelineSummary_UpdateAccount` | pipeline__c | CreateAndUpdate（After Save） | ヨミ確度・選考進捗をAccountへ転記 |
| `MeetingRecord_SubjectAutoSet` | — | — | 面談記録の件名自動設定（要確認） |
| `MeetingRecord_CountUpdate` | — | — | 面談回数カウント（要確認） |

### SF変更作業ツール

| ファイル | 用途 |
|---------|------|
| `tools/sf_deployer.py` | 共通デプロイライブラリ（フィールド作成・FLS・レイアウト） |
| `tools/sf_qa_checker.py` | デプロイ後QAチェック（フィールド/ピックリスト/レイアウト/FLS） |
| `knowledge/hr_support/sf_change_rules.md` | SF変更の鉄則・副作用チェックリスト |

### Task（活動記録）仕様

```python
task = {
    "WhatId": account_id,   # Account に紐付け（必須）
    "WhoId": None,          # PersonAccountでは使わない
    "Subject": "...",
    "Description": "...",
    "ActivityDate": "YYYY-MM-DD",
    "Status": "Completed",
    # "Type" フィールドは存在しない → 使用不可
}
```

---

## 3. 5W1H × MECE 監査ロジック（interview_master_agent）

### 評価の2軸

**① 事実の解像度（5W1H）**
- When/Where: 状況設定の曖昧さ
- Who: 役割・関係者の不明瞭さ
- What/How: 「頑張った」等の抽象語は厳禁・行動プロセスの具体性
- Why: なぜその手段を選んだかの根拠

**② 論理の網羅性（MECE）**
- 重複排除: 同じ概念の繰り返しを統合
- 漏れ補完: 3C（市場・競合・自社）・自己分析視点の抜けを指摘
- 構造化: 結論に対し根拠が論理的に独立しているか

### カテゴリ別評価基準

| カテゴリ | 基準 |
|----------|------|
| ガクチカ | STAR形式・数字による定量化・独自の介在価値 |
| 志望動機 | 競合比較・ビジョン接続・入社後の具体的貢献 |
| 失敗経験 | 自責思考・学びの抽象化・再発防止の仕組み化（再現性） |
| 強み/弱み | 客観的評価・弱みのセルフマネジメント |
| 中途専用 | スキル転用性・転職理由の妥当性と前向き変換 |

### 出力形式（新卒 / 中途 / LINE用で自動分岐）

| 形式 | 対象 | 特徴 |
|------|------|------|
| 新卒レポート | 学生 | スコア0-100 / 合格判定 / Before→After |
| 中途レポート | 社会人 | Shortlist/Pending/Reject / 3C+キャリア一貫性 |
| LINE送信用 | 学生 | 友達口調・絵文字多用・4行段落制限 |

**Google Docs自動生成**: `create_student_feedback_doc()` で学生と共有URLを自動生成・編集権限付与

---

## 4. 面談後フルサポート並列アーキテクチャ（post_interview_full_support_agent）

### KV要約プロトコル（トークン70〜90%削減）

```
議事録全文 → Claude でKV形式に圧縮
STU: 姓|名|大学名|学部|卒業年度|学科区分
EXP: ガクチカ1|ガクチカ2|ガクチカ3
MOT: 就活軸1|就活軸2|就活軸3
ACT: 次のアクション1|次のアクション2
COM: 選考企業1|選考企業2
STA: 初回/2回目|Phase
ADV: CA名|面談日YYYY-MM-DD|面談時間
IND: 志望業界1|志望業界2
```

### 4並列処理フロー

```
Transcript → KV抽出 → enrich_from_sheet（Sheet補完）
                ↓
    ┌─────────────────────────────────┐
    │ ThreadPoolExecutor × 4並列      │
    ├──────────┬────────┬──────┬──────┤
    │SF Write  │Notion  │LINE  │Slack │
    │Account   │企業DB  │下書き│通知  │
    │+Task     │自動補完│生成  │      │
    └──────────┴────────┴──────┴──────┘
                ↓
    Summary → archive_intelligence() → @secure_output（PII洗浄）
```

### Notion自動補完フィールド

```python
_NOTION_FILL_TARGETS = {
    "事業概要":   "事業内容・ビジネスモデル（3〜5文）",
    "選考フロー": "ES → 一次面接 → … 形式",
    "USP":        "独自の強み・差別化ポイント（3点）",
    "ペルソナ":   "求める学生像（2〜3文）",
}
```

---

## 5. 議事録入力フォールバックフロー（2026-04-06 追加）

### 背景・問題

`hr_watcher_tldv`（tldv自動取得エージェント）は tldv Businessプランが必要なため停止中。
これにより「SF登録 → LINE → Slack」の後続パイプラインが手動介入を要していた。

### 解決策: 3入力ルート統合

`agents/transcript_input.py`（TranscriptInput モジュール）が3つの入力ルートを統一管理する。

```
入力A（tldv API）   : tldv URL/ID → API取得（Businessプランのみ動作）
      ↓ 失敗時フォールバック
入力C（スクレイピング）: tldv録画URL → HTMLフェッチ + パース試行
      ↓ 取得不完全または失敗時フォールバック
入力B（テキストペースト）: 議事録テキストをターミナルに直接貼り付け（常に利用可能）
      ↓
後続パイプライン（post_interview_full_support_agent）
  KV抽出 → SF登録（Account+Task）→ Notion補完 → LINE下書き → Slack通知
```

### 起動方法（main.py）

| 入力形式 | 動作 |
|----------|------|
| tldv URL を直接入力（`https://app.tldv.io/...`） | URL自動検知 → フォールバックパイプライン起動 |
| 自然言語「議事録を貼り付ける」等 | キーワードルーティング → `transcript` エージェント起動 |
| `/transcript` コマンド | 入力方法選択メニュー → パイプライン起動 |

### 主要ファイル

| ファイル | 役割 |
|----------|------|
| `agents/hr_support/agents/transcript_input.py` | 3入力ルート統合モジュール（TranscriptInput） |
| `agents/hr_support/main.py` | URL自動検知・`transcript` エージェント登録 |
| `agents/hr_support/_deprecated/post_interview_full_support_agent.py` | 後続パイプライン本体 |

### 入力C（スクレイピング）の制限事項

tldv は React SPA のため静的 HTML にはトランスクリプトが含まれないことが多い。
スクレイピングで取れる情報: OGP概要・埋め込みJSON-LD・data属性のみ。
**実運用では入力B（テキストペースト）を推奨。** CA が tldv から手動コピーして貼り付ける。

### 設計原則

- 既存 `hr_orchestrator_post_interview` の構造を破壊しない
- `run_workflow(transcript)` を外部から呼び出すだけ — 疎結合
- tldv API が復旧（Businessプラン更新）した場合、入力Aが自動的に優先される
- `TLDV_API_KEY` が `.env` に設定されている場合のみ入力Aを試行

---

## 5.5 BaseAgent — 全エージェント共通基盤

```python
class BaseAgent:
    # PII検出対象
    PII_DETECTOR = {
        "email", "phone_jp", "postal_code", "birthdate",
        "name_label", "line_id", "my_number"
    }

    @secure_output          # execute()の戻り値を自動PII洗浄
    def execute(self) -> str:
        ...

    def archive_intelligence(self, content: str):
        # セッション出力 → Claude洗浄 → Markdown保存
        # 保存先: knowledge/company/ or knowledge/personal/（profile別）
```

マスキング形式: `[EMAIL_MASKED]`, `[PHONE_JP_MASKED]`

---

## 6. MCPサーバー（integrations/mcp_salesforce_notion.py）

**登録方法**: `.mcp.json`（プロジェクトルート）で `hr-support` として登録済。

| カテゴリ | ツール数 | 主要ツール |
|----------|---------|-----------|
| Salesforce | 5 | search, update, create, log_meeting, summary |
| Notion | 7 | search, read_db, read_page, create, update, archive |
| Slack | 3 | send, channels, messages |
| Gmail | 2 | send, read |
| Sheets/Docs | 5 | search_student, read, create, update, format |

**パス解決**: `integrations/` から `../config/` = `career_advisor/config/` ✓

---

## 7. 動的同期ルール（知能の常時最新化義務）

### 更新トリガーと対応ドキュメント

| 変更内容 | 更新対象 |
|----------|---------|
| エージェント追加/変更 | `knowledge/architecture_master.md` §§1-5 + `AGENT_MANIFEST.json` + `supporter_agent.py` |
| SFフィールド追加 | 本文書 §2「主要カスタムフィールド早見表」 |
| MCPツール追加 | 本文書 §6 + `settings.local.json` 許可リスト |
| ダッシュボード変更 | `Update_Log`（`dashboard_logger.py`で記録） |
| ディレクトリ変更 | `CLAUDE.md` + `STATUS_REPORT.md` + memory/ |

**原則**: コード・設定・ドキュメントは1秒の乖離も許さない。

---

## 8. エージェント11体レジストリ

| キー | 名前 | モジュール | ステータス |
|------|------|----------|-----------|
| `coaching` | 学生コーチング | coaching_agent | ✅ |
| `salesforce` | Salesforce | salesforce_agent | ✅ 最重要 |
| `notion` | Notion | notion_agent | ✅ |
| `slack` | Slack | slack_agent | ✅ |
| `line` | LINE | line_agent | ✅ |
| `tldv` | tldv | tldv_agent | ⚠️ Businessプラン要 |
| `report` | レポート | report_agent | ✅ |
| `google` | Google | google_agent | ✅ |
| `supporter` | サポーター | supporter_agent | ✅ |
| `interview_master` | 面接マスター | interview_master_agent | ✅ |
| `post_interview_full_support` | 面談後フルサポート | post_interview_full_support_agent | ✅ |

---

## 8.5. Sales Development（インサイドセールス管理ツール） (2026-04-23 追加)

**対象事業**: HR support のBDR/アウトバウンドテレアポチーム向け
**経緯**: DATAZORA/KIJI導入を検討した結果、**SFで自社構築**する方針を確定
**設計書**: `ai-empire/docs/hr_is_tool_design.md`
**本番org**: App Launcher → 「Sales Development」

### 構成要素

| 種別 | 名前 | 内容 |
|---|---|---|
| CustomObject | `Sales_Development__c` | 31フィールド（都道府県・業種3階層・被保険者数・事業タグ・ステータス・アポ率） |
| CustomTab | `Sales_Development__c` | Custom58: Target icon |
| CustomApplication | `Sales_Development` | App Launcherから起動 |
| Apex | `SalesDevelopmentController` + Test | 動的検索 / Kanban / 1クリック操作 |
| LWC | `sdAdvancedSearch` | 複数条件検索UI（AppPage） |
| LWC | `sdKanban` | ステータス別Kanban DnD（AppPage） |
| LWC | `sdQuickActions` | 1クリック記録ボタン（RecordPage） |
| FlexiPage | `SalesDevelopment_AppPage` | 検索+Kanban配置 |
| FlexiPage | `SalesDevelopment_RecordPage` | QuickActions+Detail配置 |
| ListView | 8プリセット | All / My Untouched / Today Call / Followup / Appointment Won / High Score / Target Match / Kansai |

### デプロイスクリプト（`agents/hr_support/tools/`）

```bash
python3 tools/sd_schema_deploy.py       # Object + Fields + ListView + Tab + App + FLS
python3 tools/sd_deploy_apex_lwc.py     # Apex + LWC 3種
python3 tools/sd_flexipage_deploy.py    # FlexiPage 2種
python3 tools/sd_dummy_data_seed.py     # ダミー10社
python3 tools/sd_activate_record_page.py # Activation手順表示
```

### デザインシステム
`globalKpiDashboard`のデザイン言語を踏襲:
- カラー: #0176d3（blue）/ #2e844a（green）/ #c3760d（amber）/ #181818（text）/ #687076（muted）/ #dde2e8（border）
- フォント: 'Hiragino Sans', 'Yu Gothic UI', sans-serif

### 次フェーズ（未実装）
後続で `hr_is_tool_design.md` のPhase 2-4 を実装:
- Cloud Run + gBizINFO/年金機構/マイナビ/PRTimes/firecrawl スクレイピング基盤
- Supabase Postgres データ統合層
- Lead Scoring 自動計算
- 人事異動Webhook → Task自動生成
- MiiTel 1クリック架電連携

---

## 9. ダッシュボード自動更新

**スプレッドシートID**: `1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8`

```python
# 正しい記録方法（append_row 禁止・insert_rows で Row5 に挿入）
from utils.dashboard_logger import log_update
log_update(icon="🔧 修正", summary="...", targets="...", details="...")
```

**更新対象タブ**: Update_Log / Agent_Registry / Integration_Matrix / Dev_Roadmap / Main_Map

---

*このファイルはシステムの「最上位行動指針」である。すべての変更はここに反映されなければならない。*
