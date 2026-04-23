# STATUS_REPORT.md — Tokumori 現状レポート

> **対象読者**: このプロジェクトを引き継ぐ戦略AI（軍師）または開発者
> **作成日**: 2026-03-12 / **最終更新**: 2026-04-22
> **リポジトリ**: `/Users/atsuyasato/Claude AI/ai-empire/`
> **プライベート領域**: `/Users/atsuyasato/Claude AI/private/`（リポジトリ外・完全分離）
> **ローカルダッシュボード**: http://localhost:8889（launchd 自動起動）
> **統合管理スプレッドシート**: https://docs.google.com/spreadsheets/d/1g8PzcuPuUTTdO-kcSh4niuwfLw6d8zN8JQMZCrmyuH8/edit

---

## 1. プロジェクト全体像

### 目的
HRsupport事業の業務自動化を起点に、全社AIエンパイア（Tokumori）として拡張。
49体のAIエージェントがHRsupport / RPO / Sales / 人事 / 経営管理 / 組織管理 / 品質管理 / 経営戦略の8BUを横断して稼働・開発中。

### ダッシュボード起動
```bash
# 通常はlaunchd自動起動（PC再起動後も自動復旧）
# 手動起動が必要な場合:
bash "/Users/atsuyasato/Claude AI/ai-empire/start_dashboard.sh"
# または
launchctl start com.aiempire.dashboard

# 動作確認
open http://localhost:8889
```

### HRsupportエージェント起動
```bash
cd "/Users/atsuyasato/Claude AI/ai-empire/agents/hr_support"
python3 main.py
```

---

## 2. ディレクトリ構造（2026-04-04 確定）

```
/Users/atsuyasato/Claude AI/
├── private/                      ← プライベート専用（ai-empire/と完全分離）
│   └── life_supporter/
└── ai-empire/                    ← 全社AIエンパイア
    ├── CLAUDE.md                 ← Claude Code 全体指示
    ├── STATUS_REPORT.md          ← このファイル
    ├── config -> agents/hr_support/config/   ← symlink（token.json等）
    ├── core/                     ← 経営OS中枢
    │   ├── digital_twin/
    │   └── infrastructure/       ← supervisor.md + monitoring/
    ├── intelligence/             ← 知性層
    │   ├── advisors/             ← 仮想メンター10名
    │   └── board/                ← 仮想取締役会9名
    ├── agents/                   ← 全エージェント（BU別フラット構成）
    │   ├── executive/            ← 経営戦略層（5体）
    │   ├── hr_support/           ← HRsupport事業（メイン・多数稼働）
    │   │   ├── agents/           ← サブエージェント群
    │   │   │   ├── chuto/        ← 中途支援サブOrch
    │   │   │   ├── shinsotsu/    ← 新卒支援サブOrch
    │   │   │   ├── ca/           ← CAエージェント
    │   │   │   ├── ra/           ← RAエージェント
    │   │   │   ├── lg/           ← LGエージェント（インターン生）
    │   │   │   ├── google_suite/ ← Gmail/GDrive/GSheets グループ
    │   │   │   ├── messaging/    ← LINE/Slack グループ
    │   │   │   └── workers/      ← ワーカーエージェント群
    │   │   └── _deprecated/      ← 旧フラットファイル20個（参照用）
    │   ├── rpo/                  ← RPO事業
    │   │   └── cs/
    │   ├── sales/                ← Sales事業
    │   │   ├── fs/
    │   │   └── is/
    │   ├── hr_dept/              ← 人事部門
    │   ├── management/           ← 経営管理
    │   ├── organization/         ← 組織管理層（4体）
    │   └── quality/              ← 品質管理層（4体）
    ├── dashboard/                ← FastAPI管理ダッシュボード（port 8889）
    │   ├── app.py
    │   ├── db.py
    │   ├── migrate.py            ← DB初期化・シード（46体/50エッジ）
    │   ├── routes/
    │   └── templates/index.html
    ├── knowledge/                ← 全社ドメイン知識
    │   ├── hr_support/
    │   │   ├── AGENT_MANIFEST.json   ← 全46体カタログ（v3.0）
    │   │   └── architecture_master.md
    │   └── rpo/
    ├── intelligence/
    ├── integrations/             ← MCP設定（.mcp.json）
    ├── utils/
    │   └── dashboard_logger.py   ← Update_Log記録CLI
    ├── lib/
    ├── scripts/
    ├── logs/
    └── tokumo/                   ← Next.js Webアプリ（独立管理）
```

---

## 3. エージェント構成（49体）

### BU別一覧

<!-- SYNC:BU_TABLE_START -->
| BU | Orch | サブ/職種 | Executor/Processor 等 | 計 |
|---|---|---|---|---|
| HRsupport | 1 | 5 | 17 | 23 |
| RPO | 1 | 1 | 0 | 2 |
| Sales | 1 | 2 | 0 | 3 |
| 人事 | 1 | 0 | 3 | 4 |
| 経営管理 | 1 | 0 | 2 | 3 |
| 組織管理 | 0 | 0 | 4 | 4 |
| 品質管理 | 0 | 0 | 4 | 4 |
| 経営戦略 | 0 | 0 | 5 | 5 |
| 全体 | 1 | 0 | 0 | 1 |
| **合計** | **6** | **8** | **35** | **49** |
<!-- SYNC:BU_TABLE_END -->

### ステータス
- **稼働中（active）**: HRsupport 22体（Notion/SF/Google Suite/Messaging/tldv/coaching/report/interview等）
- **開発中（dev）**: RPO/Sales/人事/経営管理/組織管理/品質管理/経営戦略（24体）

### 権限グループ（エージェントではなくセキュリティ分類）
- **CA業務**: 社員 / 業務委託で権限を分離予定
- **LG業務**: インターン生向け権限（閲覧制限あり）
- **CS（RPO）**: 社員 / 業務委託
- **FS / IS（Sales）**: 社員 / 業務委託

---

## 4. ダッシュボード仕様（port 8889）

### タブ構成
| タブ | 内容 |
|---|---|
| Overview | KPIサマリー・エージェントマップ・KPI手動記録 |
| Agents | 全エージェント一覧・詳細・ログ |
| KPI | 時間削減・ROI計算 |
| Intel | 実行ログ・エージェント別サマリー |
| Guide | セキュリティレベル定義・マトリクス |
| Roadmap | フェーズ別開発ロードマップ |
| Map（3ビュー） | 階層マップ / 事業マップ / 組織図 |

### Map タブの3ビュー
- **hierarchy（デフォルト）**: vis-network 固定座標グラフ。メンバーノード→オーケストレーター→サブエージェントの依頼フロー表示
- **business**: BU別タイルグリッド
- **org（組織図）**: ORG_STRUCTURE定数によるBU→部門→職種→雇用形態の4階層ツリー

### launchd 自動起動
```
~/Library/LaunchAgents/com.aiempire.dashboard.plist
- RunAtLoad: true（ログイン時自動起動）
- KeepAlive.Crashed: true（クラッシュ時自動再起動）
- ログ: ai-empire/logs/dashboard_stdout.log / dashboard_stderr.log
```

---

## 5. HRsupport 実装済み機能

### 主要エージェント（稼働中）

| canonical_id | 機能 | 状態 |
|---|---|---|
| hr_orchestrator_post_interview | HRsupportオーケストレーター（面談後フルサポート・並列実行） | ✅ |
| hr_executor_salesforce | tldv議事録→SF登録・更新・Task作成 | ✅ |
| hr_parser_notion | 企業紹介文生成（Notion→LINE納品） | ✅ |
| hr_messaging_slack | 選考進捗Slack共有 | ✅ |
| hr_messaging_line | LINEメッセージ生成（6シーン） | ✅ |
| hr_watcher_tldv | tldv議事録取得・分析 | ⚠️ Businessプラン要 |
| hr_processor_report | 学生所感レポート生成 | ✅ |
| hr_executor_google / 子3体 | Gmail/GDrive/GSheets | ✅ |
| hr_processor_coaching | ES・面接対策 / 就活軸深掘り | ✅ |
| hr_processor_interview | 面接マスター（5W1H×MECE） | ✅ |
| hr_processor_supporter | システムガイド | ✅ |
| hr_watcher_notion_company | Notion企業DB差分監視 | ✅ |
| hr_parser_notion_page | Notionページパーサー | ✅ |
| hr_processor_sf_mapper | SF→Notionフィールドマッパー | ✅ |
| hr_executor_sf_bulk | SF一括書き込みエグゼキューター | ✅ |

---

## 6. MCP サーバー

### 接続設定
```json
// integrations/.mcp.json（プロジェクトルート基準）
{
  "mcpServers": {
    "hr-support": {
      "command": "python3",
      "args": ["agents/hr_support/integrations/mcp_salesforce_notion.py"]
    }
  }
}
```

### 実装済みツール（28個）
```
Salesforce (5): search_salesforce, update/create_salesforce_record, log_sf_meeting, get_salesforce_summary
Notion (7):    search/read_notion_database/page, create_notion_child/page, archive/update_notion_page
Slack (3):     send_slack_message, get_slack_channels/messages
Gmail (2):     send_gmail, read_gmail
GSheets (6):   search_student_in_spreadsheet, read/create/format/update_google_spreadsheet, add_sheet_tab
GDocs (2):     read_google_doc, create_google_doc
GSlides (2):   read_google_slides, update_google_slides
Notion Users(1): get_notion_users
```

---

## 7. Salesforce オブジェクト・フィールド仕様

### RecordType
| 種別 | RecordTypeId |
|---|---|
| 新卒学生 | `0122w000001Ry2hAAC` |
| 中途学生 | `0122w000001Ry2cAAC` |
| クライアント企業 | `0122w000001RweZAAS` |

> Account（PersonAccount）のみ使用。Lead / Opportunity は存在しない。

### SF登録フロー（必須順序）
```
① tldv議事録テキスト → Claude API でJSON抽出
② search_student_in_spreadsheet（スプレッドシートID: 1xSF3m1MyeZT60VBnECNyi8qqHZPqAX5mZlniPF2Eodc）
③ Account 新規作成 or 既存レコード更新
④ Task（活動記録）を必ず作成 ← 省略すると面談履歴がSFに残らない
```

### 新規登録時の固定フィールド
```python
"Status__pc": "支援中", "Phase__pc": "初回面談済",
"CS_keiyu__c": "なし", "Field27__c": "直紹介対象",
"OfficialLineRegistration__pc": True,
"RecordTypeId": "0122w000001Ry2hAAC",  # 新卒
```

---

## 8. 技術スタック

| 領域 | 技術 |
|---|---|
| バックエンド | Python 3.9 / FastAPI / SQLite |
| フロントエンド | Jinja2 / vis-network.js / Vanilla JS |
| AIモデル | claude-sonnet-4-6 |
| 外部API | Anthropic / Salesforce / Notion / Slack / Google OAuth2 / tldv |
| インフラ | macOS launchd（自動起動） / uvicorn（port 8889） |
| 設定管理 | python-dotenv / `config/.env`（symlink先: agents/hr_support/config/） |

---

## 9. 手動対応が必要な残タスク

```bash
# 空ディレクトリの削除（Claude Codeからは実行不可）
rmdir "/Users/atsuyasato/Claude AI/ai-empire/agents/business"
rm -rf "/Users/atsuyasato/Claude AI/ai-empire/advisors"
rm -rf "/Users/atsuyasato/Claude AI/ai-empire/board"
```

---

## 10. 外部サービス接続状態

| サービス | 環境変数 | 状態 |
|---|---|---|
| Anthropic Claude API | `ANTHROPIC_API_KEY` | ✅ 稼働中 |
| Salesforce（本番） | `SF_USERNAME` / `SF_PASSWORD` / `SF_SECURITY_TOKEN` | ✅ 稼働中 |
| Notion | `NOTION_API_KEY` | ✅ 稼働中 |
| Slack Bot | `SLACK_BOT_TOKEN` 等 | ✅ 稼働中 |
| Google OAuth2 | `config/credentials.json` + `token.json` | ✅ 稼働中 |
| tldv API | `TLDV_API_KEY` | ⚠️ Businessプラン必要（現Pro） |
| LINE Messaging API | `LINE_CHANNEL_ACCESS_TOKEN` | ⏸ 未設定 |
| Lステップ API | `LSTEP_API_ENDPOINT` | ⏸ 未設定 |

---

*このレポートは 2026-04-04 のディレクトリ整理後に全面更新されました。*
*次の更新タイミング: 新BU稼働開始時 / 大規模リファクタリング時*
