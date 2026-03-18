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

## 5. BaseAgent — 全エージェント共通基盤

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
